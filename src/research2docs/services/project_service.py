"""Ordinary Python project operations; no UI imports or session state."""

from uuid import UUID

from pydantic import ValidationError

from research2docs.core.errors import InputError
from research2docs.core.models import Project, ProjectInput, utc_now
from research2docs.storage.repositories import ProjectRepository


class ProjectService:
    def __init__(self, repository: ProjectRepository):
        self.repository = repository

    def create(self, details: ProjectInput) -> Project:
        return self.repository.create(Project(**details.model_dump()))

    def list(self) -> list[Project]:
        return self.repository.list()

    def reopen(self, project_id: str | UUID) -> Project:
        try:
            identifier = UUID(project_id) if isinstance(project_id, str) else project_id
        except ValueError:
            raise InputError("Choose a valid saved project.") from None
        return self.repository.get(identifier)

    def edit(self, project_id: str | UUID, details: ProjectInput, expected_version: int) -> Project:
        if isinstance(expected_version, bool) or expected_version < 1:
            raise InputError("Reopen the project before editing.")
        current = self.reopen(project_id)
        try:
            updated = Project(
                **details.model_dump(),
                project_id=current.project_id,
                version=current.version,
                created_at=current.created_at,
                updated_at=utc_now(),
            )
        except ValidationError:
            raise InputError("Review the project fields and try again.") from None
        return self.repository.update(updated, expected_version)
