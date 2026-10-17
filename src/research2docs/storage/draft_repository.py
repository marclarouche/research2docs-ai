"""Atomic initial drafts and generation provenance, scoped to each project."""

import json
from uuid import UUID

from pydantic import ValidationError

from research2docs.core.errors import GenerationError, StorageError
from research2docs.core.models import GenerationRun
from research2docs.generation.models import SavedDraft
from research2docs.storage.database import Database
from research2docs.storage.verification_repository import VerificationRepository


class DraftRepository:
    def __init__(self, database: Database):
        self.database = database

    def start(self, run: GenerationRun) -> None:
        with self.database.session(write=True) as connection:
            connection.execute(
                "INSERT INTO generation_runs VALUES (?,?,?,?,?,?,?,?)",
                (
                    str(run.project_id),
                    str(run.run_id),
                    None,
                    run.model,
                    run.prompt_version,
                    json.dumps(run.parameters),
                    run.started_at.isoformat(),
                    run.status,
                ),
            )

    def fail(self, project_id: UUID, run_id: UUID) -> None:
        with self.database.session(write=True) as connection:
            connection.execute(
                "UPDATE generation_runs SET status='failed' WHERE project_id=? AND run_id=? AND status='started'",
                (str(project_id), str(run_id)),
            )

    def save(self, draft: SavedDraft) -> SavedDraft:
        with self.database.session(write=True) as connection:
            connection.execute(
                "INSERT INTO drafts VALUES (?,?,?,?,?)",
                (
                    str(draft.project_id),
                    str(draft.draft_id),
                    draft.title,
                    draft.goals.model_dump_json(),
                    draft.created_at.isoformat(),
                ),
            )
            connection.execute(
                "INSERT INTO revisions VALUES (?,?,?,?,?,?)",
                (
                    str(draft.project_id),
                    str(draft.revision_id),
                    str(draft.draft_id),
                    1,
                    draft.content.model_dump_json(),
                    draft.created_at.isoformat(),
                ),
            )
            connection.execute(
                "INSERT INTO generated_drafts VALUES (?,?,?)",
                (str(draft.project_id), str(draft.revision_id), draft.model_dump_json()),
            )
            connection.execute(
                "INSERT INTO draft_heads VALUES (?,?,?)",
                (str(draft.project_id), str(draft.draft_id), str(draft.revision_id)),
            )
            VerificationRepository.initialize(connection, draft)
            changed = connection.execute(
                "UPDATE generation_runs SET status='completed', revision_id=? "
                "WHERE project_id=? AND run_id=? AND status='started'",
                (str(draft.revision_id), str(draft.project_id), str(draft.run_id)),
            ).rowcount
            if changed != 1:
                raise StorageError("Generation run changed. The draft was not saved.")
        return draft

    def list_drafts(self, project_id: UUID) -> list[SavedDraft]:
        with self.database.session() as connection:
            rows = connection.execute(
                "SELECT g.payload_json FROM generated_drafts g JOIN draft_heads h ON g.project_id=h.project_id "
                "AND g.revision_id=h.revision_id WHERE g.project_id=? ORDER BY g.rowid DESC",
                (str(project_id),),
            ).fetchall()
        try:
            return [SavedDraft.model_validate_json(row[0]) for row in rows]
        except (ValueError, ValidationError):
            raise StorageError("Saved draft data is invalid. Restore a valid backup.") from None

    def history(self, project_id: UUID, draft_id: UUID) -> list[SavedDraft]:
        with self.database.session() as connection:
            rows = connection.execute(
                "SELECT g.payload_json FROM generated_drafts g JOIN revisions r "
                "ON g.project_id=r.project_id AND g.revision_id=r.revision_id WHERE r.project_id=? AND r.draft_id=? "
                "ORDER BY r.number DESC",
                (str(project_id), str(draft_id)),
            ).fetchall()
        try:
            return [SavedDraft.model_validate_json(row[0]) for row in rows]
        except (ValueError, ValidationError):
            raise StorageError("Saved revision history is invalid.") from None

    def get(
        self, project_id: UUID, draft_id: UUID, *, revision_id: UUID | None = None
    ) -> SavedDraft:
        for draft in self.history(project_id, draft_id):
            if revision_id is None or draft.revision_id == revision_id:
                if draft.project_id != project_id or draft.draft_id != draft_id:
                    raise StorageError("Saved revision identity is inconsistent.")
                return draft
        raise GenerationError("Draft revision not found in this project.")
