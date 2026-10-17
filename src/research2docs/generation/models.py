"""Bounded generation contracts; citation existence is not semantic verification."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from research2docs.core.models import EditorialGoals, Record, SourcePassage


class GenerationLimits(Record):
    timeout_seconds: float = Field(default=180.0, ge=1, le=600)
    context_tokens: int = Field(default=32768, ge=8192, le=65536)
    output_tokens: int = Field(default=4096, ge=512, le=8192)
    max_prompt_bytes: int = Field(default=24000, ge=2000, le=48000)
    max_response_bytes: int = Field(default=262144, ge=4096, le=1048576)
    evidence_passages: int = Field(default=8, ge=1, le=20)


class GenerationRequest(Record):
    goals: EditorialGoals
    query: str = Field(min_length=1, max_length=2000)


class GeneratedBlock(Record):
    text: str = Field(min_length=1, max_length=5000)
    citations: list[str] = Field(max_length=8)
    review_note: str = Field(max_length=1000)


class GeneratedSection(Record):
    kind: str = Field(min_length=1, max_length=100)
    heading: str = Field(min_length=1, max_length=200)
    blocks: list[GeneratedBlock] = Field(min_length=1, max_length=10)


class GeneratedContent(Record):
    sections: list[GeneratedSection] = Field(min_length=1, max_length=8)
    limitations: list[str] = Field(max_length=10)


class EvidenceItem(Record):
    alias: str
    passage: SourcePassage


class SavedDraft(Record):
    draft_id: UUID
    project_id: UUID
    revision_id: UUID
    run_id: UUID
    title: str
    goals: EditorialGoals
    created_at: datetime
    model: str
    model_digest: str
    prompt_version: str
    prompt_sha256: str
    query: str
    content: GeneratedContent
    evidence: list[EvidenceItem]
    warnings: list[str]
    status: Literal["unreviewed"] = "unreviewed"
    revision_number: int = Field(default=1, ge=1)
    parent_revision_id: UUID | None = None
    origin: Literal["generation", "manual", "section_regeneration"] = "generation"
    revision_note: str = Field(default="", max_length=5000)
