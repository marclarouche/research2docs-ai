"""Project repository: parameterized SQL and optimistic edits within transactions."""

import json
from uuid import UUID

from pydantic import ValidationError

from research2docs.core.errors import ProjectNotFound, RevisionConflict, StorageError
from research2docs.core.models import Project, WorkspaceSummary
from research2docs.storage.database import Database


def decode_project(row: dict[str, object]) -> Project:
    try:
        data = dict(row)
        data["goals"] = json.loads(str(data.pop("goals_json")))
        return Project.model_validate_json(json.dumps(data))
    except (ValueError, ValidationError):
        raise StorageError("Saved project data is invalid. Restore a valid backup.") from None


class ProjectRepository:
    def __init__(self, database: Database):
        self.database = database

    def create(self, project: Project) -> Project:
        with self.database.session(write=True) as connection:
            connection.execute(
                "INSERT INTO projects VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    str(project.project_id),
                    project.title,
                    project.description,
                    project.goals.model_dump_json(),
                    project.version,
                    project.created_at.isoformat(),
                    project.updated_at.isoformat(),
                ),
            )
        return project

    def list(self) -> list[Project]:
        with self.database.session() as connection:
            rows = connection.execute(
                "SELECT * FROM projects ORDER BY updated_at DESC, project_id"
            ).fetchall()
        return [decode_project(dict(row)) for row in rows]

    def get(self, project_id: UUID) -> Project:
        with self.database.session() as connection:
            row = connection.execute(
                "SELECT * FROM projects WHERE project_id=?", (str(project_id),)
            ).fetchone()
        if row is None:
            raise ProjectNotFound("Project not found. Reopen a saved project from the dashboard.")
        return decode_project(dict(row))

    def update(self, project: Project, expected_version: int) -> Project:
        with self.database.session(write=True) as connection:
            changed = connection.execute(
                "UPDATE projects SET title=?, description=?, goals_json=?, updated_at=?, "
                "version=version+1 WHERE project_id=? AND version=?",
                (
                    project.title,
                    project.description,
                    project.goals.model_dump_json(),
                    project.updated_at.isoformat(),
                    str(project.project_id),
                    expected_version,
                ),
            ).rowcount
            if changed != 1:
                if (
                    connection.execute(
                        "SELECT 1 FROM projects WHERE project_id=?", (str(project.project_id),)
                    ).fetchone()
                    is None
                ):
                    raise ProjectNotFound("Project not found. Reopen from the dashboard.")
                raise RevisionConflict(
                    "This project changed in another session. Reopen before saving."
                )
        return self.get(project.project_id)

    def summary(self) -> WorkspaceSummary:
        with self.database.session() as connection:
            return WorkspaceSummary(
                projects=connection.execute("SELECT count(*) FROM projects").fetchone()[0],
                drafts=connection.execute("SELECT count(*) FROM drafts").fetchone()[0],
                unresolved_claims=connection.execute(
                    "SELECT count(*) FROM claims WHERE assessment <> 'human_verified'"
                ).fetchone()[0],
            )

    def model_preference(self) -> str | None:
        with self.database.session() as connection:
            row = connection.execute(
                "SELECT value FROM app_preferences WHERE key='selected_model'"
            ).fetchone()
        return None if row is None else str(row[0])

    def save_model_preference(self, name: str) -> None:
        with self.database.session(write=True) as connection:
            connection.execute(
                "INSERT INTO app_preferences VALUES ('selected_model', ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (name,),
            )
