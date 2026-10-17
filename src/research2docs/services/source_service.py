"""Validated byte imports, stable evidence creation and bounded full-text search."""

import hashlib
import re
from pathlib import Path
from uuid import UUID

from research2docs.core.errors import IngestionError, InputError
from research2docs.core.models import SourceDocument, SourcePassage, utc_now
from research2docs.ingestion.chunker import passages, source_identity
from research2docs.ingestion.models import (
    ImportLimits,
    ImportMetadata,
    ImportResult,
    SearchHit,
    SourceSummary,
    SourceType,
)
from research2docs.ingestion.runner import extract
from research2docs.storage.repositories import ProjectRepository
from research2docs.storage.source_repository import SourceRepository, identifier

FORMATS: dict[str, SourceType] = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".md": "markdown",
    ".markdown": "markdown",
    ".txt": "txt",
    ".html": "html",
    ".htm": "html",
}


def validate_filename(filename: str) -> SourceType:
    if (
        not filename
        or len(filename) > 200
        or filename in {".", ".."}
        or any(c in filename for c in "/\\:")
        or any(ord(c) < 32 for c in filename)
    ):
        raise IngestionError(
            "unsafe_filename", "Use a plain filename without directory components."
        )
    kind = FORMATS.get(Path(filename).suffix.lower())
    if kind is None:
        raise IngestionError(
            "unsupported_type", "Supported files: text PDF, DOCX, Markdown, TXT and local HTML."
        )
    return kind


def query_expression(query: str) -> str:
    if not query.strip() or len(query) > 2000:
        raise InputError("Enter a search question or term of at most 2,000 characters.")
    terms = list(dict.fromkeys(re.findall(r"\w+", query, re.UNICODE)))
    if not terms or len(terms) > 64:
        raise InputError("Use between 1 and 64 searchable words or identifiers.")
    return " OR ".join('"' + term + '"' for term in terms)


class SourceService:
    def __init__(
        self, sources: SourceRepository, projects: ProjectRepository, limits: ImportLimits
    ):
        self.repository = sources
        self.projects = projects
        self.limits = limits

    def import_document(
        self,
        project_id: str | UUID,
        data: bytes,
        filename: str,
        metadata: ImportMetadata | None = None,
    ) -> ImportResult:
        project = self.projects.get(identifier(project_id))
        kind = validate_filename(filename)
        if not isinstance(data, bytes):
            raise InputError("Supply document bytes, not a file path.")
        if not data or len(data) > self.limits.max_file_bytes:
            raise IngestionError(
                "file_size_limit", "The file is empty or exceeds the configured upload size."
            )
        digest = hashlib.sha256(data).hexdigest()
        if existing := self.repository.find_hash(project.project_id, digest):
            return ImportResult(
                filename=filename,
                accepted=True,
                duplicate=True,
                source_id=existing.source_id,
                warnings=["identical_content_already_saved_metadata_unchanged"],
                reason="duplicate_content",
            )
        parsed = extract(data, kind, self.limits)
        options = metadata or ImportMetadata()
        source = SourceDocument(
            source_id=source_identity(digest),
            project_id=project.project_id,
            filename=filename,
            title=options.title or parsed.title or Path(filename).stem,
            author=options.author or parsed.author,
            source_type=kind,
            imported_at=utc_now(),
            sha256=digest,
            supplied_url=options.supplied_url,
        )
        sections, chunks = passages(project.project_id, source.source_id, parsed, self.limits)
        return self.repository.save(source, sections, chunks, parsed.warnings, self.limits)

    def list_sources(self, project_id: str | UUID) -> list[SourceSummary]:
        project = self.projects.get(identifier(project_id))
        return self.repository.list_sources(project.project_id)

    def search(self, project_id: str | UUID, query: str, *, limit: int = 5) -> list[SearchHit]:
        project = self.projects.get(identifier(project_id))
        expression = query_expression(query)
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 20:
            raise InputError("Choose a search limit between 1 and 20.")
        with self.repository.database.session() as connection:
            rows = connection.execute(
                "SELECT passage_fts.passage_id, bm25(passage_fts) AS score, d.* "
                "FROM passage_fts JOIN source_passages p ON p.project_id=passage_fts.project_id "
                "AND p.passage_id=passage_fts.passage_id JOIN source_documents d "
                "ON d.project_id=p.project_id AND d.source_id=p.source_id "
                "WHERE passage_fts MATCH ? AND passage_fts.project_id=? "
                "ORDER BY score ASC, passage_fts.passage_id ASC LIMIT ?",
                (expression, str(project.project_id), limit),
            ).fetchall()
        from research2docs.storage.source_repository import read_source

        return [
            SearchHit(
                rank=index + 1,
                score=float(row["score"]),
                source=read_source(row),
                passage=self.repository.resolve(project.project_id, UUID(row["passage_id"])),
            )
            for index, row in enumerate(rows)
        ]

    def import_batch(
        self,
        project_id: str | UUID,
        files: list[tuple[str, bytes]],
        metadata: ImportMetadata | None = None,
    ) -> list[ImportResult]:
        from research2docs.core.errors import Research2DocsError

        self.projects.get(identifier(project_id))
        if not 1 <= len(files) <= 10:
            raise InputError("Select between 1 and 10 documents for one batch.")
        if metadata is not None and metadata.title and len(files) != 1:
            raise InputError("A title override applies to a single file only.")
        results = []
        for filename, data in files:
            try:
                results.append(self.import_document(project_id, data, filename, metadata))
            except Research2DocsError as error:
                results.append(
                    ImportResult(
                        filename=filename[:200],
                        accepted=False,
                        reason=error.reason
                        if isinstance(error, IngestionError)
                        else "storage_or_project_failure",
                        warnings=[str(error)],
                    )
                )
        return results

    def source_passages(self, project_id: str | UUID, source_id: str | UUID) -> list[SourcePassage]:
        project = self.projects.get(identifier(project_id))
        return self.repository.passages(project.project_id, identifier(source_id))

    def resolve_passage(self, project_id: str | UUID, passage_id: str | UUID) -> SourcePassage:
        project = self.projects.get(identifier(project_id))
        return self.repository.resolve(project.project_id, identifier(passage_id))
