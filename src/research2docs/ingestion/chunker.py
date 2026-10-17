"""Stable exact windows into persisted extracted sections, never across locations."""

import hashlib
from uuid import NAMESPACE_URL, UUID, uuid5

from research2docs.core.errors import IngestionError
from research2docs.core.models import SourcePassage
from research2docs.ingestion.models import (
    EXTRACTION_VERSION,
    ImportLimits,
    ParsedSource,
    StoredSection,
)


def source_identity(digest: str) -> UUID:
    return uuid5(NAMESPACE_URL, "research2docs:source:sha256:" + digest)


def passages(
    project_id: UUID, source_id: UUID, parsed: ParsedSource, limits: ImportLimits
) -> tuple[list[StoredSection], list[SourcePassage]]:
    sections: list[StoredSection] = []
    result: list[SourcePassage] = []
    for item in parsed.sections:
        section_id = uuid5(
            source_id, f"{EXTRACTION_VERSION}:{parsed.extraction_method}:{item.ordinal}"
        )
        section = StoredSection(
            **item.model_dump(), section_id=section_id, source_id=source_id, project_id=project_id
        )
        sections.append(section)
        start = 0
        while start < len(item.text):
            end = min(start + limits.passage_chars, len(item.text))
            if end < len(item.text):
                boundary = item.text.rfind("\n\n", start + limits.passage_chars // 2, end)
                if boundary > start:
                    end = boundary + 2
            text = item.text[start:end]
            if text.strip():
                digest = hashlib.sha256(text.encode()).hexdigest()
                passage_id = uuid5(
                    section_id,
                    f"chars:{limits.passage_chars}:{limits.overlap_chars}:{start}:{end}:{digest}",
                )
                result.append(
                    SourcePassage(
                        passage_id=passage_id,
                        source_id=source_id,
                        project_id=project_id,
                        section_id=section_id,
                        text=text,
                        char_start=start,
                        char_end=end,
                        ordinal=len(result),
                        heading=item.heading,
                        page=item.page,
                        section=item.locator,
                        extraction_method=parsed.extraction_method,
                    )
                )
                if len(result) > limits.max_passages:
                    raise IngestionError("passage_limit")
            if end == len(item.text):
                break
            start = max(start + 1, end - limits.overlap_chars)
    if not result:
        raise IngestionError("no_extractable_text")
    return sections, result
