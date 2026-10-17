"""Atomic source/section/passage/FTS persistence; exact stored evidence is authoritative."""

import json
import sqlite3
from uuid import UUID

from pydantic import ValidationError

from research2docs.core.errors import IngestionError, InputError, ProjectNotFound, StorageError
from research2docs.core.models import SourceDocument, SourcePassage, utc_now
from research2docs.ingestion.models import ImportLimits, ImportResult, SourceSummary, StoredSection
from research2docs.storage.database import Database


def identifier(value: str | UUID) -> UUID:
    try:
        return UUID(value) if isinstance(value, str) else value
    except ValueError:
        raise InputError("Choose a valid saved source or project.") from None


def read_source(row: sqlite3.Row) -> SourceDocument:
    try:
        result = SourceDocument.model_validate_json(row["metadata_json"])
        if (
            str(result.project_id) != row["project_id"]
            or str(result.source_id) != row["source_id"]
            or result.filename != row["filename"]
            or result.sha256 != row["sha256"]
        ):
            raise ValueError("Inconsistent metadata")
        return result
    except (ValueError, ValidationError):
        raise StorageError(
            "Saved source metadata is inconsistent. Restore a valid backup."
        ) from None


class SourceRepository:
    def __init__(self, database: Database):
        self.database = database

    def list_sources(self, project_id: UUID) -> list[SourceSummary]:
        with self.database.session() as connection:
            rows = connection.execute(
                "SELECT * FROM source_documents WHERE project_id=? ORDER BY source_id",
                (str(project_id),),
            ).fetchall()
            result = []
            for row in rows:
                source = read_source(row)
                counts = connection.execute(
                    "SELECT (SELECT count(*) FROM source_passages WHERE project_id=? AND source_id=?), "
                    "(SELECT count(*) FROM source_sections WHERE project_id=? AND source_id=?)",
                    (
                        str(project_id),
                        str(source.source_id),
                        str(project_id),
                        str(source.source_id),
                    ),
                ).fetchone()
                result.append(
                    SourceSummary(
                        source=source,
                        passages=counts[0],
                        sections=counts[1],
                        warnings=self.warnings(project_id, source.source_id),
                    )
                )
        return result

    def warnings(self, project_id: UUID, source_id: UUID) -> list[str]:
        # Import diagnostics are stored separately from bibliographic metadata.
        with self.database.session() as connection:
            row = connection.execute(
                "SELECT warnings_json FROM source_imports WHERE project_id=? AND source_id=?",
                (str(project_id), str(source_id)),
            ).fetchone()
        try:
            value = json.loads(row[0]) if row else []
            if not isinstance(value, list) or not all(isinstance(w, str) for w in value):
                raise ValueError("Invalid warnings")
            return value
        except ValueError:
            raise StorageError("Saved import diagnostics are inconsistent.") from None

    def find_hash(self, project_id: UUID, digest: str) -> SourceDocument | None:
        with self.database.session() as connection:
            row = connection.execute(
                "SELECT * FROM source_documents WHERE project_id=? AND sha256=?",
                (str(project_id), digest),
            ).fetchone()
        return None if row is None else read_source(row)

    def save(
        self,
        source: SourceDocument,
        sections: list[StoredSection],
        passages: list[SourcePassage],
        warnings: list[str],
        limits: ImportLimits,
    ) -> ImportResult:
        by_section = {section.section_id: section for section in sections}
        if (
            not sections
            or not passages
            or len(passages) > limits.max_passages
            or len(sections) > limits.max_sections
            or sum(len(section.text) for section in sections) > limits.max_text_chars
            or [p.ordinal for p in passages] != list(range(len(passages)))
            or any(
                s.project_id != source.project_id or s.source_id != source.source_id
                for s in sections
            )
        ):
            raise IngestionError("passage_limit")
        for passage in passages:
            section = by_section.get(passage.section_id) if passage.section_id is not None else None
            if (
                section is None
                or passage.project_id != source.project_id
                or passage.source_id != source.source_id
                or section.project_id != source.project_id
                or section.source_id != source.source_id
                or passage.char_end is None
                or passage.char_end > len(section.text)
                or passage.char_start >= passage.char_end
                or passage.page != section.page
                or passage.heading != section.heading
                or passage.section != section.locator
                or not passage.text.strip()
                or section.text[passage.char_start : passage.char_end] != passage.text
            ):
                raise IngestionError("invalid_passage_slice")
        with self.database.session(write=True) as connection:
            project = str(source.project_id)
            if (
                connection.execute(
                    "SELECT 1 FROM projects WHERE project_id=?", (project,)
                ).fetchone()
                is None
            ):
                raise ProjectNotFound("Choose a saved project before importing documents.")
            duplicate = connection.execute(
                "SELECT * FROM source_documents WHERE project_id=? AND sha256=?",
                (project, source.sha256),
            ).fetchone()
            if duplicate is not None:
                return ImportResult(
                    filename=source.filename,
                    accepted=True,
                    duplicate=True,
                    source_id=read_source(duplicate).source_id,
                    reason="duplicate_content",
                    warnings=["identical_content_already_saved_metadata_unchanged"],
                )
            count = connection.execute(
                "SELECT count(*) FROM source_documents WHERE project_id=?", (project,)
            ).fetchone()[0]
            existing_chars = sum(
                len(row[0])
                for row in connection.execute(
                    "SELECT text FROM source_sections WHERE project_id=?", (project,)
                )
            )
            if (
                count >= limits.max_sources
                or existing_chars + sum(len(s.text) for s in sections) > limits.max_project_chars
            ):
                raise IngestionError(
                    "project_limit", "This import exceeds the project's source or text limit."
                )
            connection.execute(
                "INSERT INTO source_documents VALUES (?, ?, ?, ?, ?)",
                (
                    project,
                    str(source.source_id),
                    source.filename,
                    source.sha256,
                    source.model_dump_json(),
                ),
            )
            for section in sections:
                connection.execute(
                    "INSERT INTO source_sections VALUES (?, ?, ?, ?, ?)",
                    (
                        project,
                        str(section.section_id),
                        str(source.source_id),
                        section.text,
                        section.model_dump_json(exclude={"text"}),
                    ),
                )
            for passage in passages:
                connection.execute(
                    "INSERT INTO source_passages VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        project,
                        str(passage.passage_id),
                        str(source.source_id),
                        passage.text,
                        passage.ordinal,
                        passage.model_dump_json(exclude={"text"}),
                        passage.extraction_method,
                    ),
                )
                connection.execute(
                    "INSERT INTO passage_fts (project_id, passage_id, text) VALUES (?, ?, ?)",
                    (project, str(passage.passage_id), passage.text),
                )
            connection.execute(
                "INSERT INTO source_imports VALUES (?, ?, ?)",
                (project, str(source.source_id), json.dumps(warnings)),
            )
            connection.execute(
                "UPDATE projects SET updated_at=? WHERE project_id=?",
                (utc_now().isoformat(), project),
            )
        return ImportResult(
            filename=source.filename,
            accepted=True,
            source_id=source.source_id,
            passages=len(passages),
            warnings=warnings,
            reason="imported",
        )

    def passages(self, project_id: UUID, source_id: UUID) -> list[SourcePassage]:
        with self.database.session() as connection:
            rows = connection.execute(
                "SELECT passage_id FROM source_passages WHERE project_id=? AND source_id=? ORDER BY ordinal",
                (str(project_id), str(source_id)),
            ).fetchall()
        return [self.resolve(project_id, UUID(row[0])) for row in rows]

    def resolve(self, project_id: UUID, passage_id: UUID) -> SourcePassage:
        with self.database.session() as connection:
            row = connection.execute(
                "SELECT * FROM source_passages WHERE project_id=? AND passage_id=?",
                (str(project_id), str(passage_id)),
            ).fetchone()
            if row is None:
                raise InputError("Passage not found in the selected project.")
            try:
                data = json.loads(row["locator_json"])
                data["text"] = row["text"]
                passage = SourcePassage.model_validate_json(json.dumps(data))
                if (
                    passage.project_id != project_id
                    or passage.passage_id != passage_id
                    or str(passage.source_id) != row["source_id"]
                    or passage.ordinal != row["ordinal"]
                    or passage.extraction_method != row["extraction_method"]
                ):
                    raise ValueError("Inconsistent passage")
                section_row = connection.execute(
                    "SELECT * FROM source_sections WHERE project_id=? AND section_id=?",
                    (str(project_id), str(passage.section_id)),
                ).fetchone()
                if section_row is None:
                    raise ValueError("Missing section")
                location = json.loads(section_row["metadata_json"])
                location["text"] = section_row["text"]
                section = StoredSection.model_validate_json(json.dumps(location))
                if (
                    section.project_id != project_id
                    or section.source_id != passage.source_id
                    or str(section.section_id) != section_row["section_id"]
                    or str(section.source_id) != section_row["source_id"]
                    or passage.char_end is None
                    or passage.char_end > len(section.text)
                    or section.text[passage.char_start : passage.char_end] != passage.text
                    or section.page != passage.page
                    or section.heading != passage.heading
                    or section.locator != passage.section
                ):
                    raise ValueError("Invalid exact slice")
                return passage
            except (ValueError, TypeError, ValidationError):
                raise StorageError(
                    "Saved passage evidence is inconsistent. Restore a valid backup."
                ) from None
