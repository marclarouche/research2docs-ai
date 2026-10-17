"""Validated explicit editorial actions; never exposed as model tools."""

from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from research2docs.core.models import Label, Record
from research2docs.generation.models import GeneratedContent


class RevisionEdit(Record):
    title: Label
    content: GeneratedContent
    editor: Label
    note: str = Field(min_length=1, max_length=5000)

    @model_validator(mode="after")
    def nonblank(self) -> "RevisionEdit":
        if not self.note.strip():
            raise ValueError("Revision note is required")
        return self


class HumanReview(Record):
    reviewer: Label
    action: Literal["accepted", "rejected", "reopened"]
    rationale: str = Field(min_length=1, max_length=5000)
    reviewed_passages: list[UUID] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def valid_review(self) -> "HumanReview":
        if not self.rationale.strip():
            raise ValueError("Review rationale is required")
        if len(set(self.reviewed_passages)) != len(self.reviewed_passages):
            raise ValueError("Duplicate passage")
        if self.action == "accepted" and not self.reviewed_passages:
            raise ValueError("Acceptance needs reviewed source passages")
        return self
