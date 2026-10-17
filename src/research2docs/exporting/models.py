from typing import Literal
from uuid import UUID

from pydantic import Field

from research2docs.core.models import Record


class ExportFile(Record):
    revision_id: UUID
    claim_versions: dict[str, int]
    filename: str
    mime_type: str
    data: bytes = Field(max_length=33554432)


ExportFormat = Literal["markdown", "docx", "html", "json"]
