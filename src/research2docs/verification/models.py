"""Typed review contracts. Automated assessments never grant human verification."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from research2docs.core.models import AssessmentStatus, Claim, Record, SourcePassage


class VerificationLimits(Record):
    retrieval_passages: int = Field(default=8, ge=1, le=20)


class QuoteReference(Record):
    alias: str = Field(min_length=1, max_length=8)
    quote: str = Field(min_length=1, max_length=4000)


class AssessmentReply(Record):
    status: Literal[
        "source_supported",
        "partially_supported",
        "unsupported",
        "conflicting_evidence",
        "potentially_outdated",
    ]
    explanation: str = Field(min_length=1, max_length=3000)
    supporting: list[QuoteReference] = Field(max_length=8)
    contradictory: list[QuoteReference] = Field(max_length=8)
    temporal: list[QuoteReference] = Field(max_length=4)
    uncertain: bool


class CheckedQuote(Record):
    passage_id: UUID
    quote: str
    start: int = Field(ge=0)
    end: int = Field(ge=1)


class ClaimUnit(Record):
    claim: Claim
    draft_id: UUID
    section_index: int = Field(ge=0)
    block_index: int = Field(ge=0)
    text_sha256: str
    cited_passages: list[UUID]
    citation_state: Literal["valid", "missing"]
    version: int = Field(ge=0)
    state: Literal["not_assessed", "completed", "inconclusive"]
    review_flags: list[str]
    supporting: list[CheckedQuote] = Field(default_factory=list)
    contradictory: list[CheckedQuote] = Field(default_factory=list)
    temporal: list[CheckedQuote] = Field(default_factory=list)
    assessment_id: UUID | None = None
    human_evidence: list[UUID] = Field(default_factory=list)
    automated_assessment: AssessmentStatus | None = None
    model: str | None = None
    model_digest: str | None = None
    prompt_sha256: str | None = None


class Ledger(Record):
    project_id: UUID
    draft_id: UUID
    revision_id: UUID
    content_sha256: str
    created_at: datetime
    units: list[ClaimUnit]


class AssessmentEvidence(Record):
    alias: str
    passage: SourcePassage
    source_title: str
    filename: str
