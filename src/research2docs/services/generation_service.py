"""Retrieve → bounded prompt → local structured response → validate → atomic unreviewed draft."""

import hashlib
import json
from uuid import UUID, uuid4

from pydantic import ValidationError

from research2docs.core.errors import GenerationError, Research2DocsError
from research2docs.core.models import GenerationRun, utc_now
from research2docs.generation.models import (
    EvidenceItem,
    GeneratedContent,
    GenerationLimits,
    GenerationRequest,
    SavedDraft,
)
from research2docs.generation.ollama_client import OllamaClient
from research2docs.generation.prompts import messages, output_schema, template
from research2docs.services.source_service import SourceService
from research2docs.storage.draft_repository import DraftRepository
from research2docs.storage.repositories import ProjectRepository
from research2docs.storage.source_repository import identifier


class GenerationService:
    def __init__(
        self,
        drafts: DraftRepository,
        sources: SourceService,
        projects: ProjectRepository,
        ollama: OllamaClient,
        limits: GenerationLimits,
    ):
        self.repository, self.sources, self.projects = drafts, sources, projects
        self.ollama, self.limits = ollama, limits

    def list_drafts(self, project_id: str | UUID) -> list[SavedDraft]:
        project = self.projects.get(identifier(project_id))
        return self.repository.list_drafts(project.project_id)

    def reopen(
        self, project_id: str | UUID, draft_id: str | UUID, *, revision_id: str | UUID | None = None
    ) -> SavedDraft:
        project = self.projects.get(identifier(project_id))
        draft = self.repository.get(
            project.project_id,
            identifier(draft_id),
            revision_id=identifier(revision_id) if revision_id is not None else None,
        )
        with self.repository.database.session() as connection:
            revision = connection.execute(
                "SELECT content,draft_id FROM revisions WHERE project_id=? AND revision_id=?",
                (str(project.project_id), str(draft.revision_id)),
            ).fetchone()
        if (
            revision is None
            or revision[0] != draft.content.model_dump_json()
            or revision[1] != str(draft.draft_id)
        ):
            raise GenerationError(
                "Saved draft content differs from its revision. A new revision and assessment are required."
            )
        # Re-resolve every saved evidence snapshot, not a model-authored passage.
        for evidence in draft.evidence:
            if (
                self.sources.resolve_passage(project.project_id, evidence.passage.passage_id)
                != evidence.passage
            ):
                raise GenerationError("Saved evidence no longer matches its authoritative passage.")
        self.validate(draft.content, draft.goals.document_type, draft.evidence)
        return draft

    @staticmethod
    def validate(content: GeneratedContent, kind: object, evidence: list[EvidenceItem]) -> None:
        from research2docs.core.models import DocumentType

        if not isinstance(kind, DocumentType):
            raise GenerationError("Choose a supported document type.")
        if [section.kind for section in content.sections] != template(kind)["sections"]:
            raise GenerationError(
                "Model returned an invalid document structure. No draft was saved."
            )
        allowed = {item.alias for item in evidence}
        if any(
            not set(block.citations) <= allowed or len(block.citations) != len(set(block.citations))
            for section in content.sections
            for block in section.blocks
        ):
            raise GenerationError("Model returned an invalid citation. No draft was saved.")
        if sum(
            len(b.text) + len(b.review_note) for s in content.sections for b in s.blocks
        ) > 50000 or any(len(note) > 2000 for note in content.limitations):
            raise GenerationError("Model draft exceeded the content limit. No draft was saved.")

    def generate(self, project_id: str | UUID, request: GenerationRequest) -> SavedDraft:
        # Revalidate mutable caller input before use.
        request = GenerationRequest.model_validate_json(request.model_dump_json())
        project = self.projects.get(identifier(project_id))
        hits = self.sources.search(
            project.project_id, request.query, limit=self.limits.evidence_passages
        )
        if not hits:
            raise GenerationError(
                "No matching source evidence. Import sources or revise the research question."
            )
        name = self.projects.model_preference()
        if not name:
            raise GenerationError("Choose and save an installed local model in Settings first.")
        schema = output_schema(request.goals.document_type)
        evidence: list[EvidenceItem] = []
        for hit in hits:
            candidate = [
                *evidence,
                EvidenceItem(alias=f"E{len(evidence) + 1}", passage=hit.passage),
            ]
            size = len(
                json.dumps(
                    {"messages": messages(request, candidate), "format": schema}, ensure_ascii=False
                ).encode()
            )
            # UTF-8 bytes are a conservative token proxy, plus output and framing reserve.
            if size <= min(
                self.limits.max_prompt_bytes,
                self.limits.context_tokens - self.limits.output_tokens - 2048,
            ):
                evidence = candidate
        if not evidence:
            raise GenerationError(
                "Evidence and editorial settings exceed the prompt budget. Shorten the request."
            )
        prompt = messages(request, evidence)
        prompt_hash = hashlib.sha256(
            json.dumps({"messages": prompt, "format": schema}, sort_keys=True).encode()
        ).hexdigest()
        spec = template(request.goals.document_type)
        run = GenerationRun(
            run_id=uuid4(),
            project_id=project.project_id,
            model=name,
            prompt_version=spec["version"],
            started_at=utc_now(),
            status="started",
            parameters={
                "temperature": 0,
                "seed": 0,
                "context_tokens": self.limits.context_tokens,
                "output_tokens": self.limits.output_tokens,
                "prompt_sha256": prompt_hash,
                "evidence_passages": len(evidence),
                "timeout_seconds": self.limits.timeout_seconds,
            },
        )
        self.repository.start(run)
        try:
            model = self.ollama.validate_selection(name, context=self.limits.context_tokens)
            raw = self.ollama.generate(
                name,
                prompt,
                schema,
                timeout=self.limits.timeout_seconds,
                max_bytes=self.limits.max_response_bytes,
                context=self.limits.context_tokens,
                output=self.limits.output_tokens,
            )
            try:
                content = GeneratedContent.model_validate_json(raw)
            except (ValidationError, ValueError, RecursionError):
                raise GenerationError(
                    "Model returned invalid structured content. No draft was saved."
                ) from None
            self.validate(content, request.goals.document_type, evidence)
            for item in evidence:
                if (
                    self.sources.resolve_passage(project.project_id, item.passage.passage_id)
                    != item.passage
                ):
                    raise GenerationError(
                        "Source evidence changed during generation. Retry the request."
                    )
            warnings = [
                "Unreviewed AI draft. Citation existence has been checked; factual support has not been assessed."
            ]
            uncited = sum(
                not block.citations for section in content.sections for block in section.blocks
            )
            if uncited:
                warnings.append(
                    f"{uncited} content blocks have no source citations and require verification."
                )
            if len(evidence) < len(hits):
                warnings.append("Some retrieved passages were omitted to fit the prompt budget.")
            words = sum(
                len(block.text.split()) for section in content.sections for block in section.blocks
            )
            if (
                not request.goals.approximate_words * 0.7
                <= words
                <= request.goals.approximate_words * 1.3
            ):
                warnings.append(
                    f"Draft has approximately {words} words; target was {request.goals.approximate_words}."
                )
            return self.repository.save(
                SavedDraft(
                    draft_id=uuid4(),
                    revision_id=uuid4(),
                    run_id=run.run_id,
                    project_id=project.project_id,
                    title=request.goals.working_title.strip() or project.title,
                    goals=request.goals,
                    created_at=utc_now(),
                    model=name,
                    model_digest=model.digest,
                    prompt_version=spec["version"],
                    prompt_sha256=prompt_hash,
                    query=request.query,
                    content=content,
                    evidence=evidence,
                    warnings=warnings,
                )
            )
        except Research2DocsError:
            self.repository.fail(project.project_id, run.run_id)
            raise
