"""Explicit editorial actions preserve history and invalidate revision assessments."""

import hashlib
import json
from uuid import UUID, uuid4

from pydantic import ValidationError

from research2docs.core.errors import (
    GenerationError,
    InputError,
    Research2DocsError,
    RevisionConflict,
)
from research2docs.core.models import GenerationRun, utc_now
from research2docs.editorial.models import HumanReview, RevisionEdit
from research2docs.generation.models import EvidenceItem, GeneratedSection, SavedDraft
from research2docs.generation.prompts import SYSTEM, template
from research2docs.services.generation_service import GenerationService
from research2docs.services.verification_service import VerificationService
from research2docs.storage.editorial_repository import EditorialRepository
from research2docs.storage.source_repository import identifier
from research2docs.verification.models import ClaimUnit


class EditorialService:
    def __init__(
        self,
        repository: EditorialRepository,
        generation: GenerationService,
        verification: VerificationService,
    ):
        self.repository, self.generation, self.verification = repository, generation, verification

    def history(self, project_id: str | UUID, draft_id: str | UUID) -> list[SavedDraft]:
        latest = self.generation.reopen(project_id, draft_id)
        return self.generation.repository.history(latest.project_id, latest.draft_id)

    def save(
        self,
        project_id: str | UUID,
        draft_id: str | UUID,
        base_revision_id: str | UUID,
        edit: RevisionEdit,
    ) -> SavedDraft:
        edit = RevisionEdit.model_validate_json(edit.model_dump_json())
        base = self.generation.reopen(project_id, draft_id, revision_id=base_revision_id)
        self.generation.validate(edit.content, base.goals.document_type, base.evidence)
        if edit.content == base.content and edit.title == base.title:
            raise InputError("No content or title changes to save.")
        revision = SavedDraft.model_validate_json(
            base.model_copy(
                update={
                    "revision_id": uuid4(),
                    "revision_number": base.revision_number + 1,
                    "parent_revision_id": base.revision_id,
                    "created_at": utc_now(),
                    "origin": "manual",
                    "revision_note": edit.note,
                    "title": edit.title,
                    "content": edit.content,
                    "warnings": list(
                        dict.fromkeys(
                            [
                                *base.warnings,
                                "Edited revision requires fresh claim assessments and human review.",
                            ]
                        )
                    ),
                }
            ).model_dump_json()
        )
        return self.repository.append(base, revision, edit.editor)

    def decide(
        self,
        project_id: str | UUID,
        draft_id: str | UUID,
        revision_id: str | UUID,
        claim_id: str | UUID,
        review: HumanReview,
        *,
        expected_version: int,
    ) -> ClaimUnit:
        review = HumanReview.model_validate_json(review.model_dump_json())
        if (
            not isinstance(expected_version, int)
            or isinstance(expected_version, bool)
            or expected_version < 0
        ):
            raise InputError("Supply the displayed nonnegative claim version.")
        draft = self.generation.reopen(project_id, draft_id, revision_id=revision_id)
        ledger = self.verification.ledger(project_id, draft_id, revision_id=draft.revision_id)
        unit = next((u for u in ledger.units if u.claim.claim_id == identifier(claim_id)), None)
        if unit is None:
            raise InputError("Claim is not in the selected revision.")
        if unit.version != expected_version:
            raise RevisionConflict("This claim changed. Reload before recording a decision.")
        for pid in review.reviewed_passages:
            self.generation.sources.resolve_passage(draft.project_id, pid)
        return self.repository.decide(draft, unit, review, expected_version)

    def review_history(
        self,
        project_id: str | UUID,
        draft_id: str | UUID,
        revision_id: str | UUID,
        claim_id: str | UUID,
    ) -> list[str]:
        ledger = self.verification.ledger(project_id, draft_id, revision_id=revision_id)
        cid = identifier(claim_id)
        if not any(u.claim.claim_id == cid for u in ledger.units):
            raise InputError("Claim is not in this revision.")
        with self.repository.database.session() as c:
            rows = c.execute(
                "SELECT action,payload_json,created_at FROM human_review_events WHERE project_id=? AND claim_id=? ORDER BY rowid",
                (str(ledger.project_id), str(cid)),
            ).fetchall()
        return [
            row[2]
            + " · "
            + row[0]
            + " · "
            + json.loads(row[1])["review"]["reviewer"]
            + " · "
            + json.loads(row[1])["review"]["rationale"]
            for row in rows
        ]

    def regenerate(
        self,
        project_id: str | UUID,
        draft_id: str | UUID,
        base_revision_id: str | UUID,
        section_index: int,
        *,
        editor: str,
        note: str,
        instructions: str = "",
    ) -> SavedDraft:
        base = self.generation.reopen(project_id, draft_id, revision_id=base_revision_id)
        validation = RevisionEdit(title=base.title, content=base.content, editor=editor, note=note)
        if (
            not isinstance(section_index, int)
            or isinstance(section_index, bool)
            or not 0 <= section_index < len(base.content.sections)
            or len(instructions) > 5000
        ):
            raise InputError("Choose a saved section and instructions of at most 5,000 characters.")
        latest = self.generation.reopen(project_id, draft_id)
        if latest.revision_id != base.revision_id:
            raise RevisionConflict("Regenerate from the latest saved revision.")
        name = self.generation.projects.model_preference()
        if not name:
            raise GenerationError("Select an installed local model in Settings first.")
        section = base.content.sections[section_index]
        schema = GeneratedSection.model_json_schema()
        schema["properties"]["kind"]["enum"] = [section.kind]
        candidates = list(base.evidence)
        for hit in self.generation.sources.search(base.project_id, base.query, limit=8):
            if (
                hit.passage.passage_id not in {e.passage.passage_id for e in candidates}
                and len(candidates) < 40
            ):
                candidates.append(
                    EvidenceItem(
                        alias=f"E{max(int(e.alias[1:]) for e in candidates) + 1}",
                        passage=hit.passage,
                    )
                )

        def prompt(evidence: list[EvidenceItem]) -> list[dict[str, str]]:
            return [
                {
                    "role": "system",
                    "content": SYSTEM
                    + "\nRegenerate ONLY the requested section as one section JSON object. Never return or modify other sections.",
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "goals": base.goals.model_dump(mode="json"),
                            "format_instruction": template(base.goals.document_type)["instruction"],
                            "section_kind": section.kind,
                            "previous_section": section.model_dump(mode="json"),
                            "editorial_preferences": instructions,
                            "evidence": [
                                {
                                    "alias": e.alias,
                                    "text": e.passage.text,
                                    "page": e.passage.page,
                                    "section": e.passage.section,
                                }
                                for e in evidence
                            ],
                        },
                        ensure_ascii=False,
                    ),
                },
            ]

        limits = self.generation.limits
        evidence: list[EvidenceItem] = []
        for item in candidates:
            trial = [*evidence, item]
            size = len(
                json.dumps(
                    {"messages": prompt(trial), "format": schema}, ensure_ascii=False
                ).encode()
            )
            if size <= min(
                limits.max_prompt_bytes, limits.context_tokens - limits.output_tokens - 2048
            ):
                evidence = trial
        if not evidence:
            raise GenerationError(
                "No evidence fits the section prompt. Shorten the section or request."
            )
        messages = prompt(evidence)
        prompt_hash = hashlib.sha256(
            json.dumps({"messages": messages, "format": schema}, sort_keys=True).encode()
        ).hexdigest()
        run = GenerationRun(
            run_id=uuid4(),
            project_id=base.project_id,
            model=name,
            prompt_version="section-regeneration:1.0",
            parameters={
                "section_index": section_index,
                "parent_revision_id": str(base.revision_id),
                "prompt_sha256": prompt_hash,
                "temperature": 0,
                "seed": 0,
                "context_tokens": limits.context_tokens,
                "output_tokens": limits.output_tokens,
                "supplied_passage_ids": json.dumps([str(e.passage.passage_id) for e in evidence]),
            },
            started_at=utc_now(),
            status="started",
        )
        self.generation.repository.start(run)
        try:
            model = self.generation.ollama.validate_selection(name, context=limits.context_tokens)
            raw = self.generation.ollama.generate(
                name,
                messages,
                schema,
                timeout=limits.timeout_seconds,
                max_bytes=limits.max_response_bytes,
                context=limits.context_tokens,
                output=limits.output_tokens,
            )
            try:
                replacement = GeneratedSection.model_validate_json(raw)
            except (ValidationError, ValueError, RecursionError):
                raise GenerationError(
                    "Model returned invalid section content. No revision was saved."
                ) from None
            if replacement.kind != section.kind or any(
                not set(b.citations) <= {e.alias for e in evidence} for b in replacement.blocks
            ):
                raise GenerationError(
                    "Model changed the section type or invented a citation. No revision was saved."
                )
            content = base.content.model_copy(deep=True)
            content.sections[section_index] = replacement
            merged = list(base.evidence) + [
                e
                for e in evidence
                if e.passage.passage_id not in {b.passage.passage_id for b in base.evidence}
            ]
            self.generation.validate(content, base.goals.document_type, merged)
            for item in evidence:
                if (
                    self.generation.sources.resolve_passage(
                        base.project_id, item.passage.passage_id
                    )
                    != item.passage
                ):
                    raise GenerationError("Source evidence changed. Reopen before regenerating.")
            revision = SavedDraft.model_validate_json(
                base.model_copy(
                    update={
                        "revision_id": uuid4(),
                        "revision_number": base.revision_number + 1,
                        "parent_revision_id": base.revision_id,
                        "created_at": utc_now(),
                        "origin": "section_regeneration",
                        "revision_note": note,
                        "content": content,
                        "evidence": merged,
                        "run_id": run.run_id,
                        "model": name,
                        "model_digest": model.digest,
                        "prompt_version": run.prompt_version,
                        "prompt_sha256": prompt_hash,
                        "warnings": list(
                            dict.fromkeys(
                                [
                                    *base.warnings,
                                    "Regenerated revision requires fresh assessments and human review.",
                                    *(
                                        [
                                            "Some candidate passages were omitted from the regeneration prompt."
                                        ]
                                        if len(evidence) < len(candidates)
                                        else []
                                    ),
                                ]
                            )
                        ),
                    }
                ).model_dump_json()
            )
            return self.repository.append(
                base, revision, validation.editor, regeneration_run=run.run_id
            )
        except Research2DocsError:
            self.generation.repository.fail(base.project_id, run.run_id)
            raise
