"""Ordinary Python Phase 2 demonstration. No Streamlit or Ollama required."""

from pathlib import Path
from tempfile import TemporaryDirectory

from research2docs.core.config import Settings
from research2docs.core.models import Audience, EditorialGoals, ProjectInput
from research2docs.services.workspace_service import WorkspaceService


def main() -> None:
    with TemporaryDirectory(prefix="research2docs-demo-") as folder:
        settings = Settings(data_dir=str(Path(folder)))
        app = WorkspaceService(settings)
        project = app.projects.create(
            ProjectInput(
                title="Fictional technical research", description="Foundation demonstration only."
            )
        )
        edited = app.projects.edit(
            project.project_id,
            ProjectInput(
                title="Fictional editorial project",
                goals=EditorialGoals(audience=Audience.BEGINNER, approximate_words=800),
            ),
            project.version,
        )
        reopened = WorkspaceService(settings).projects.reopen(project.project_id)
        assert reopened == edited and reopened.version == 2
        print("Project creation, editing, listing and reopening passed in temporary storage.")
        assert len(app.projects.list()) == 1
        folder = Path(__file__).resolve().parents[1] / "samples/fictional_research"
        names = [
            "overview.md",
            "notes.txt",
            "reference.html",
            "workflow.docx",
            "troubleshooting.pdf",
        ]
        results = app.sources.import_batch(
            project.project_id, [(name, (folder / name).read_bytes()) for name in names]
        )
        assert all(result.accepted for result in results)
        restored = WorkspaceService(settings)
        assert len(restored.sources.list_sources(project.project_id)) == 5
        hits = restored.sources.search(project.project_id, "RESEARCH_READY", limit=20)
        assert any(hit.source.source_type == "pdf" and hit.passage.page == 2 for hit in hits)
        print("Five-format import, FTS5 search, exact PDF page-2 evidence and reopen passed.")


if __name__ == "__main__":
    main()
