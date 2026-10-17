"""Deterministic ledger, scoped retrieval and conservative AI-assisted assessment."""

import hashlib
import json
import re
from uuid import UUID, uuid4

from pydantic import ValidationError

from research2docs.core.errors import Research2DocsError, RevisionConflict, VerificationError
from research2docs.core.models import AssessmentStatus, utc_now
from research2docs.generation.models import GenerationLimits
from research2docs.generation.ollama_client import OllamaClient
from research2docs.services.generation_service import GenerationService
from research2docs.services.source_service import SourceService
from research2docs.storage.repositories import ProjectRepository
from research2docs.storage.source_repository import identifier
from research2docs.storage.verification_repository import VerificationRepository
from research2docs.verification.models import (
    AssessmentEvidence,
    AssessmentReply,
    CheckedQuote,
    ClaimUnit,
    Ledger,
    QuoteReference,
    VerificationLimits,
)
from research2docs.verification.prompts import PROMPT_VERSION, messages, schema


class VerificationService:
    def __init__(
        self,
        repository: VerificationRepository,
        generation: GenerationService,
        sources: SourceService,
        projects: ProjectRepository,
        ollama: OllamaClient,
        generation_limits: GenerationLimits,
        limits: VerificationLimits,
    ):
        self.repository, self.generation, self.sources = repository, generation, sources
        self.projects, self.ollama = projects, ollama
        self.generation_limits, self.limits = generation_limits, limits

    def ledger(
        self, project_id: str | UUID, draft_id: str | UUID, *, revision_id: str | UUID | None = None
    ) -> Ledger:
        draft = self.generation.reopen(project_id, draft_id, revision_id=revision_id)
        ledger = self.repository.ensure(draft)
        # Exact excerpt resolution is checked on every inspection, including reopened records.
        for unit in ledger.units:
            for passage_id in unit.human_evidence:
                self.sources.resolve_passage(draft.project_id, passage_id)
            for quote in [*unit.supporting, *unit.contradictory, *unit.temporal]:
                passage = self.sources.resolve_passage(draft.project_id, quote.passage_id)
                if passage.text[quote.start : quote.end] != quote.quote:
                    raise VerificationError(
                        "Saved assessment excerpt no longer matches its source."
                    )
        return ledger

    def evidence(self, project_id: UUID, unit: ClaimUnit) -> tuple[list[AssessmentEvidence], bool]:
        sources = {
            item.source.source_id: item.source for item in self.sources.list_sources(project_id)
        }
        passages = [self.sources.resolve_passage(project_id, pid) for pid in unit.cited_passages]
        # Bounded deterministic term selection for long/compound prose blocks.
        terms = list(dict.fromkeys(re.findall(r"\w+", unit.claim.text, re.UNICODE)))[:64]
        query = " ".join(terms)[:2000]
        if query:
            for hit in self.sources.search(project_id, query, limit=self.limits.retrieval_passages):
                if hit.passage.passage_id not in {p.passage_id for p in passages}:
                    passages.append(hit.passage)
        packed: list[AssessmentEvidence] = []
        omitted = False
        limit = self.generation_limits
        for passage in passages:
            source = sources[passage.source_id]
            candidate = [
                *packed,
                AssessmentEvidence(
                    alias=f"E{len(packed) + 1}",
                    passage=passage,
                    source_title=source.title,
                    filename=source.filename,
                ),
            ]
            size = len(
                json.dumps(
                    {"messages": messages(unit, candidate), "format": schema()}, ensure_ascii=False
                ).encode()
            )
            if size <= min(
                limit.max_prompt_bytes, limit.context_tokens - limit.output_tokens - 2048
            ):
                packed = candidate
            else:
                omitted = True
        return packed, omitted

    @staticmethod
    def check_quotes(
        refs: list[QuoteReference], evidence: list[AssessmentEvidence]
    ) -> list[CheckedQuote]:
        mapping = {e.alias: e.passage for e in evidence}
        if len({r.alias for r in refs}) != len(refs):
            raise VerificationError(
                "Assessment repeated an evidence reference. Result was not saved."
            )
        checked = []
        for ref in refs:
            passage = mapping.get(ref.alias)
            if passage is None or not ref.quote.strip() or ref.quote not in passage.text:
                raise VerificationError(
                    "Assessment cited an unknown passage or nonmatching excerpt. Result was not saved."
                )
            start = passage.text.index(ref.quote)
            checked.append(
                CheckedQuote(
                    passage_id=passage.passage_id,
                    quote=ref.quote,
                    start=start,
                    end=start + len(ref.quote),
                )
            )
        return checked

    def assess(
        self,
        project_id: str | UUID,
        draft_id: str | UUID,
        claim_id: str | UUID,
        *,
        expected_version: int,
        revision_id: str | UUID | None = None,
    ) -> ClaimUnit:
        if (
            not isinstance(expected_version, int)
            or isinstance(expected_version, bool)
            or expected_version < 0
        ):
            raise VerificationError("Supply the displayed nonnegative assessment version.")
        draft = self.generation.reopen(project_id, draft_id, revision_id=revision_id)
        ledger = self.ledger(project_id, draft_id, revision_id=draft.revision_id)
        unit = next((u for u in ledger.units if u.claim.claim_id == identifier(claim_id)), None)
        if unit is None:
            raise VerificationError("Claim not found in the selected draft revision.")
        if unit.version != expected_version or unit.claim.human_review != "pending":
            raise RevisionConflict("This claim changed. Reopen before assessing.")
        name = self.projects.model_preference()
        if not name:
            raise VerificationError("Choose and save an installed local model in Settings first.")
        evidence, omitted = self.evidence(draft.project_id, unit)
        assessment_id = uuid4()
        prompt = messages(unit, evidence)
        prompt_hash = hashlib.sha256(
            json.dumps({"messages": prompt, "format": schema()}, sort_keys=True).encode()
        ).hexdigest()
        limits = self.generation_limits
        self.repository.start(
            draft.project_id,
            draft.revision_id,
            unit.claim.claim_id,
            assessment_id,
            {
                "model": name,
                "prompt_version": PROMPT_VERSION,
                "prompt_sha256": prompt_hash,
                "claim_text_sha256": unit.text_sha256,
                "expected_version": expected_version,
                "parameters": {
                    "temperature": 0,
                    "seed": 0,
                    "context_tokens": limits.context_tokens,
                    "output_tokens": limits.output_tokens,
                    "timeout_seconds": limits.timeout_seconds,
                },
                "evidence": [e.model_dump(mode="json") for e in evidence],
            },
        )
        try:
            supporting: list[CheckedQuote] = []
            contradictory: list[CheckedQuote] = []
            temporal: list[CheckedQuote] = []
            status = AssessmentStatus.UNSUPPORTED
            state = "inconclusive"
            explanation = (
                "No source passages fit the assessment evidence budget. Human review is required."
            )
            digest = None
            method = "deterministic-no-evidence:1.0"
            if evidence:
                model = self.ollama.validate_selection(name, context=limits.context_tokens)
                digest = model.digest
                raw = self.ollama.generate(
                    name,
                    prompt,
                    schema(),
                    timeout=limits.timeout_seconds,
                    max_bytes=limits.max_response_bytes,
                    context=limits.context_tokens,
                    output=limits.output_tokens,
                )
                try:
                    reply = AssessmentReply.model_validate_json(raw)
                except (ValidationError, ValueError, RecursionError):
                    raise VerificationError(
                        "Model returned invalid assessment data. Previous results were preserved."
                    ) from None
                supporting = self.check_quotes(reply.supporting, evidence)
                contradictory = self.check_quotes(reply.contradictory, evidence)
                temporal = self.check_quotes(reply.temporal, evidence)
                if {q.passage_id for q in supporting} & {q.passage_id for q in contradictory}:
                    raise VerificationError(
                        "Assessment assigned contradictory roles to the same passage. Review is required."
                    )
                status = AssessmentStatus(reply.status)
                if (
                    status in {AssessmentStatus.SOURCE_SUPPORTED, AssessmentStatus.PARTIAL}
                    and not supporting
                ):
                    raise VerificationError(
                        "A supported assessment requires an exact supporting excerpt."
                    )
                if status == AssessmentStatus.SOURCE_SUPPORTED and contradictory:
                    raise VerificationError(
                        "A fully supported assessment cannot silently retain contradictory evidence."
                    )
                if status == AssessmentStatus.UNSUPPORTED and supporting and not reply.uncertain:
                    raise VerificationError("Assessment support and status are inconsistent.")
                if status == AssessmentStatus.CONFLICTING:
                    by_id = {e.passage.passage_id: e.passage.source_id for e in evidence}
                    if (
                        not supporting
                        or not contradictory
                        or len({by_id[q.passage_id] for q in [*supporting, *contradictory]}) < 2
                    ):
                        raise VerificationError(
                            "Conflicting evidence requires excerpts from different source documents."
                        )
                if status == AssessmentStatus.OUTDATED and (
                    not temporal
                    or not any(
                        re.search(
                            r"\b(?:19|20)\d{2}\b|\bversion\s+\d|\bv\d+\.\d", q.quote, re.IGNORECASE
                        )
                        for q in temporal
                    )
                ):
                    raise VerificationError(
                        "A temporal concern requires an explicit source date or version excerpt."
                    )
                explanation = reply.explanation
                if not explanation.strip():
                    raise VerificationError("Assessment explanation is blank.")
                if reply.uncertain:
                    status = AssessmentStatus.UNSUPPORTED
                    explanation = (
                        "Inconclusive AI assessment; human review required. " + explanation
                    )
                else:
                    state = "completed"
                method = PROMPT_VERSION
            flags = list(unit.review_flags)
            for flag in [
                "AI-assisted support is not independent verification.",
                "Retrieval may omit relevant or conflicting evidence.",
            ]:
                if flag not in flags:
                    flags.append(flag)
            if (
                omitted
                and "Some candidate passages were omitted to fit the context budget." not in flags
            ):
                flags.append("Some candidate passages were omitted to fit the context budget.")
            claim = unit.claim.model_copy(
                update={
                    "assessment": status,
                    "explanation": explanation,
                    "assessment_method": method,
                    "assessed_at": utc_now(),
                }
            )
            updated = ClaimUnit.model_validate_json(
                unit.model_copy(
                    update={
                        "claim": claim,
                        "automated_assessment": status,
                        "version": expected_version + 1,
                        "state": state,
                        "supporting": supporting,
                        "contradictory": contradictory,
                        "temporal": temporal,
                        "assessment_id": assessment_id,
                        "model": name if evidence else None,
                        "model_digest": digest,
                        "prompt_sha256": prompt_hash,
                        "review_flags": flags,
                    }
                ).model_dump_json()
            )
            # Recheck canonical revision and all packed authoritative passages after the model returns.
            self.generation.reopen(project_id, draft_id, revision_id=draft.revision_id)
            for item in evidence:
                if (
                    self.sources.resolve_passage(draft.project_id, item.passage.passage_id)
                    != item.passage
                ):
                    raise VerificationError(
                        "Source evidence changed during assessment. Retry after reopening."
                    )
            return self.repository.publish(draft, updated, expected_version)
        except Research2DocsError:
            self.repository.fail(draft.project_id, assessment_id)
            raise
