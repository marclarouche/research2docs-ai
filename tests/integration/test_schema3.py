import hashlib
import sqlite3

import pytest

from research2docs.core.config import Settings
from research2docs.core.errors import StorageError
from research2docs.core.models import ProjectInput
from research2docs.services.workspace_service import WorkspaceService
from research2docs.storage import database
from research2docs.storage.migrations import MIGRATION_1, MIGRATION_2


def test_schema2_preserves_projects_sources_and_fts(tmp_path):
    path = tmp_path / "research2docs.sqlite3"
    # Construct original schema 2, then save rows through phase-3 services without upgrade.
    with sqlite3.connect(path) as c:
        c.execute(
            "CREATE TABLE schema_migrations(version INTEGER PRIMARY KEY, checksum TEXT NOT NULL, applied_at TEXT NOT NULL)"
        )
        for n, migration in [(1, MIGRATION_1), (2, MIGRATION_2)]:
            for statement in migration:
                c.execute(statement)
            c.execute(
                "INSERT INTO schema_migrations VALUES (?,?,?)",
                (n, hashlib.sha256("\n".join(migration).encode()).hexdigest(), "fixture"),
            )
        c.execute("PRAGMA user_version=2")
    # Use a database handle without calling initialization to populate schema 2.
    db = object.__new__(database.Database)
    db.root = tmp_path
    db.path = path
    from research2docs.core.models import Project
    from research2docs.storage.repositories import ProjectRepository

    project = ProjectRepository(db).create(Project(title="Preserve schema 2"))
    ProjectRepository(db).save_model_preference("fixture:latest")
    from research2docs.ingestion.models import ImportLimits
    from research2docs.services.source_service import SourceService
    from research2docs.storage.source_repository import SourceRepository

    service = SourceService(SourceRepository(db), ProjectRepository(db), ImportLimits())
    service.import_document(
        project.project_id, b"SCHEMA_THREE evidence survives migration.", "test.txt"
    )
    project = ProjectRepository(db).get(project.project_id)
    before = service.search(project.project_id, "SCHEMA_THREE")[0].passage
    w = WorkspaceService(Settings(data_dir=str(tmp_path)))
    assert w.projects.reopen(project.project_id) == project
    assert w.sources.search(project.project_id, "SCHEMA_THREE")[0].passage == before
    assert w.selected_model() == "fixture:latest"
    with w.database.session() as c:
        assert c.execute("PRAGMA user_version").fetchone()[0] == 5


def test_schema3_failure_rolls_back_without_rebuild(tmp_path, monkeypatch):
    w = WorkspaceService(Settings(data_dir=str(tmp_path)))
    p = w.projects.create(ProjectInput(title="Preserved"))
    with w.database.session(write=True) as c:
        for table in ["human_review_events", "revision_events", "draft_heads"]:
            c.execute(f"DROP TABLE {table}")
        c.execute("DELETE FROM schema_migrations WHERE version=5")
        for table in ["assessment_runs", "claim_units", "verification_ledgers"]:
            c.execute(f"DROP TABLE {table}")
        c.execute("DELETE FROM schema_migrations WHERE version=4")
        c.execute("DROP TABLE generated_drafts")
        c.execute("DELETE FROM schema_migrations WHERE version=3")
        c.execute("PRAGMA user_version=2")
    monkeypatch.setattr(
        database, "MIGRATION_3", (*database.MIGRATION_3, "CREATE TABLE projects(bad TEXT)")
    )
    with pytest.raises(StorageError):
        database.Database(tmp_path)
    with sqlite3.connect(w.database.path) as c:
        assert c.execute("PRAGMA user_version").fetchone()[0] == 2
        assert c.execute("SELECT title FROM projects").fetchone()[0] == p.title
        assert not c.execute(
            "SELECT name FROM sqlite_master WHERE name='generated_drafts'"
        ).fetchone()
