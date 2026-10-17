"""Composition boundary available to UI, tests and ordinary Python callers."""

from pathlib import Path

from research2docs.core.config import Settings
from research2docs.core.diagnostics import record_event
from research2docs.core.models import WorkspaceSummary
from research2docs.generation.ollama_client import OllamaClient, OllamaStatus
from research2docs.services.editorial_service import EditorialService
from research2docs.services.export_service import ExportService
from research2docs.services.generation_service import GenerationService
from research2docs.services.project_service import ProjectService
from research2docs.services.source_service import SourceService
from research2docs.services.verification_service import VerificationService
from research2docs.storage.database import Database
from research2docs.storage.draft_repository import DraftRepository
from research2docs.storage.editorial_repository import EditorialRepository
from research2docs.storage.repositories import ProjectRepository
from research2docs.storage.source_repository import SourceRepository
from research2docs.storage.verification_repository import VerificationRepository


class WorkspaceService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.database = Database(Path(settings.data_dir))
        self.repository = ProjectRepository(self.database)
        self.projects = ProjectService(self.repository)
        self.sources = SourceService(
            SourceRepository(self.database), self.repository, settings.ingestion
        )
        self.ollama = OllamaClient(settings.ollama)
        self.generation = GenerationService(
            DraftRepository(self.database),
            self.sources,
            self.repository,
            self.ollama,
            settings.generation,
        )

        self.verification = VerificationService(
            VerificationRepository(self.database),
            self.generation,
            self.sources,
            self.repository,
            self.ollama,
            settings.generation,
            settings.verification,
        )

        self.editorial = EditorialService(
            EditorialRepository(self.database), self.generation, self.verification
        )

        self.exports = ExportService(self.editorial)

    def summary(self) -> WorkspaceSummary:
        return self.repository.summary()

    def check_ollama(self) -> OllamaStatus:
        status = self.ollama.status()
        record_event(self.database.root, "ollama_checked")
        return status

    def selected_model(self) -> str | None:
        return self.repository.model_preference()

    def select_model(self, name: str) -> None:
        selected = self.ollama.validate_selection(name)
        self.repository.save_model_preference(selected.name)
        record_event(self.database.root, "model_selected")
