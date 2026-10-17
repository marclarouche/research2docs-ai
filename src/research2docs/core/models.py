"""Typed foundation contracts. Later-phase entities are contracts, not working features."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Label = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50000)]


def utc_now() -> datetime:
    return datetime.now(UTC)


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, validate_assignment=True)


class DocumentType(StrEnum):
    EXPLAINER = "technical_explainer"
    TUTORIAL = "step_by_step_tutorial"
    FAQ = "faq"
    GUIDE = "instructional_guide"
    BRIEF = "executive_technical_brief"


class Audience(StrEnum):
    PUBLIC = "general_public"
    BEGINNER = "beginner_technical"
    INTERMEDIATE = "intermediate_technical"
    ADVANCED = "advanced_technical"
    EXECUTIVE = "executive"
    CUSTOM = "custom"


class AssessmentStatus(StrEnum):
    SOURCE_SUPPORTED = "source_supported"
    PARTIAL = "partially_supported"
    UNSUPPORTED = "unsupported"
    CONFLICTING = "conflicting_evidence"
    OUTDATED = "potentially_outdated"
    HUMAN_VERIFIED = "human_verified"


class EditorialGoals(Record):
    document_type: DocumentType = DocumentType.EXPLAINER
    audience: Audience = Audience.INTERMEDIATE
    custom_audience: str = Field(default="", max_length=500)
    working_title: str = Field(default="", max_length=200)
    approximate_words: int = Field(default=1000, ge=100, le=10000)
    technical_depth: Literal["introductory", "moderate", "detailed"] = "moderate"
    instructions: str = Field(default="", max_length=5000)

    @model_validator(mode="after")
    def check_custom(self) -> "EditorialGoals":
        if self.audience == Audience.CUSTOM and not self.custom_audience.strip():
            raise ValueError("Custom audience needs a description")
        return self


class ProjectInput(Record):
    title: Label
    description: str = Field(default="", max_length=10000)
    goals: EditorialGoals = Field(default_factory=EditorialGoals)


class Project(ProjectInput):
    project_id: UUID = Field(default_factory=uuid4)
    version: int = Field(default=1, ge=1)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class SourceDocument(Record):
    source_id: UUID
    project_id: UUID
    filename: Label
    title: Label
    author: str | None = Field(default=None, max_length=500)
    source_type: Literal["pdf", "docx", "markdown", "txt", "html"]
    imported_at: datetime
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    supplied_url: str | None = Field(default=None, max_length=2000)


class SourcePassage(Record):
    passage_id: UUID
    source_id: UUID
    project_id: UUID
    text: str = Field(min_length=1, max_length=50000)
    section_id: UUID | None = None
    char_start: int = Field(default=0, ge=0)
    char_end: int | None = Field(default=None, ge=1)
    ordinal: int = Field(ge=0)
    page: int | None = Field(default=None, ge=1)
    section: str | None = Field(default=None, max_length=500)
    heading: str | None = Field(default=None, max_length=500)
    extraction_method: Label


class DocumentDraft(Record):
    draft_id: UUID
    project_id: UUID
    title: Label
    goals: EditorialGoals
    created_at: datetime


class DraftRevision(Record):
    revision_id: UUID
    draft_id: UUID
    project_id: UUID
    number: int = Field(ge=1)
    content: Text
    created_at: datetime


class Claim(Record):
    claim_id: UUID
    revision_id: UUID
    project_id: UUID
    text: str = Field(min_length=1, max_length=50000)
    assessment: AssessmentStatus = AssessmentStatus.UNSUPPORTED
    explanation: Text
    assessment_method: Label
    assessed_at: datetime
    human_review: Literal["pending", "accepted", "rejected"] = "pending"
    human_rationale: str = Field(default="", max_length=5000)

    @model_validator(mode="after")
    def human_status(self) -> "Claim":
        if not self.text.strip():
            raise ValueError("Claim text cannot be blank")
        if self.human_review != "pending" and not self.human_rationale.strip():
            raise ValueError("Human decisions require rationale")
        if self.assessment == AssessmentStatus.HUMAN_VERIFIED and self.human_review != "accepted":
            raise ValueError("Human verified requires an accepted human decision")
        return self


class ClaimEvidence(Record):
    claim_id: UUID
    passage_id: UUID
    project_id: UUID
    relation: Literal["supporting", "contradictory"]


class EditorialDecision(Record):
    decision_id: UUID
    claim_id: UUID
    project_id: UUID
    reviewer: Label
    decision: Literal["accepted", "rejected"]
    rationale: Text
    created_at: datetime


class GenerationRun(Record):
    run_id: UUID
    project_id: UUID
    revision_id: UUID | None = None
    model: Label
    prompt_version: Label
    parameters: dict[str, str | int | float | bool]
    started_at: datetime
    status: Literal["started", "completed", "failed"]


class WorkspaceSummary(Record):
    projects: int
    drafts: int
    unresolved_claims: int
