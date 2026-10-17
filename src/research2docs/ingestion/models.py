"""Bounded import contracts and exact extracted-source locations."""

from typing import Literal
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from research2docs.core.models import Record, SourceDocument, SourcePassage

SourceType = Literal["pdf", "docx", "markdown", "txt", "html"]
EXTRACTION_VERSION = "extract-1"


class ImportLimits(Record):
    max_file_bytes: int = Field(default=10485760, ge=128, le=10485760)
    max_sources: int = Field(default=100, ge=1, le=1000)
    max_text_chars: int = Field(default=1000000, ge=100, le=2000000)
    max_project_chars: int = Field(default=10000000, ge=100, le=20000000)
    max_sections: int = Field(default=2000, ge=1, le=10000)
    max_pdf_pages: int = Field(default=500, ge=1, le=1000)
    max_zip_entries: int = Field(default=2000, ge=3, le=5000)
    max_zip_expanded_bytes: int = Field(default=41943040, ge=1024, le=83886080)
    max_passages: int = Field(default=3000, ge=1, le=10000)
    passage_chars: int = Field(default=4000, ge=100, le=8000)
    overlap_chars: int = Field(default=200, ge=0, le=1000)
    parser_seconds: float = Field(default=20.0, ge=0.1, le=60)
    cpu_seconds: int = Field(default=10, ge=1, le=30)
    memory_bytes: int = Field(default=1073741824, ge=268435456, le=2147483648)

    @model_validator(mode="after")
    def overlap(self) -> "ImportLimits":
        if self.overlap_chars >= self.passage_chars:
            raise ValueError("Overlap must be smaller than a passage")
        return self


class ImportMetadata(Record):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    author: str | None = Field(default=None, min_length=1, max_length=500)
    supplied_url: str | None = Field(default=None, max_length=2000)

    @field_validator("supplied_url")
    @classmethod
    def label_only(cls, value: str | None) -> str | None:
        if value is None:
            return None
        parts = urlsplit(value)
        if (
            parts.scheme not in {"http", "https"}
            or not parts.hostname
            or parts.username is not None
            or parts.password is not None
            or any(ord(c) < 32 for c in value)
        ):
            raise ValueError("Use a plain HTTP(S) reference URL without credentials")
        return value


class ExtractedSection(Record):
    text: str = Field(min_length=1, max_length=2000000)
    ordinal: int = Field(ge=0)
    heading: str | None = Field(default=None, max_length=500)
    page: int | None = Field(default=None, ge=1)
    locator: str = Field(min_length=1, max_length=500)


class ParsedSource(Record):
    source_type: SourceType
    title: str | None = Field(default=None, max_length=200)
    author: str | None = Field(default=None, max_length=500)
    sections: list[ExtractedSection] = Field(max_length=10000)
    warnings: list[str] = Field(default_factory=list, max_length=1100)
    extraction_method: str
    extraction_version: str = EXTRACTION_VERSION


class StoredSection(ExtractedSection):
    section_id: UUID
    source_id: UUID
    project_id: UUID


class SourceSummary(Record):
    source: SourceDocument
    passages: int
    sections: int
    warnings: list[str]


class ImportResult(Record):
    filename: str
    accepted: bool
    duplicate: bool = False
    source_id: UUID | None = None
    passages: int = 0
    warnings: list[str] = Field(default_factory=list)
    reason: str


class SearchHit(Record):
    rank: int
    score: float
    source: SourceDocument
    passage: SourcePassage
