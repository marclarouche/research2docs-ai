import hashlib
import sqlite3

import pytest

from research2docs.core.config import Settings
from research2docs.core.errors import StorageError
from research2docs.core.models import Project
from research2docs.services.workspace_service import WorkspaceService
from research2docs.storage import database
from research2docs.storage.database import Database
from research2docs.storage.migrations import MIGRATION_1


def make_phase1(path):
    project = Project(title="Preserved Phase 1 project", description="Existing editorial metadata")
    with sqlite3.connect(path) as conn:
        conn.execute(
            "CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, checksum TEXT NOT NULL, applied_at TEXT NOT NULL)"
        )
        for statement in MIGRATION_1:
            conn.execute(statement)
        conn.execute(
            "INSERT INTO schema_migrations VALUES (1,?,?)",
            (
                hashlib.sha256("\n".join(MIGRATION_1).encode()).hexdigest(),
                project.created_at.isoformat(),
            ),
        )
        conn.execute("PRAGMA user_version=1")
        conn.execute(
            "INSERT INTO projects VALUES (?,?,?,?,?,?,?)",
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
        conn.execute("INSERT INTO app_preferences VALUES ('selected_model','local:latest')")
    return project


def test_phase1_migrates_without_changing_project_or_model(tmp_path):
    project = make_phase1(tmp_path / "research2docs.sqlite3")
    workspace = WorkspaceService(Settings(data_dir=str(tmp_path)))
    assert workspace.projects.reopen(project.project_id) == project
    assert workspace.selected_model() == "local:latest"
    with workspace.database.session() as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 5
        assert conn.execute("SELECT count(*) FROM schema_migrations").fetchone()[0] == 5
        assert conn.execute("SELECT name FROM sqlite_master WHERE name='passage_fts'").fetchone()
    assert workspace.sources.import_document(
        project.project_id, b"UPGRADE_EVIDENCE source", "upgrade.txt"
    ).accepted
    assert workspace.sources.search(project.project_id, "UPGRADE_EVIDENCE")


def test_phase2_upgrade_failure_rolls_back_to_valid_phase1(tmp_path, monkeypatch):
    project = make_phase1(tmp_path / "research2docs.sqlite3")
    actual = database.MIGRATION_2
    monkeypatch.setattr(database, "MIGRATION_2", (*actual, "CREATE TABLE projects (bad TEXT)"))
    with pytest.raises(StorageError):
        Database(tmp_path)
    with sqlite3.connect(tmp_path / "research2docs.sqlite3") as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 1
        assert conn.execute("SELECT title FROM projects").fetchone()[0] == project.title
        assert (
            conn.execute("SELECT name FROM sqlite_master WHERE name='passage_fts'").fetchone()
            is None
        )
    monkeypatch.setattr(database, "MIGRATION_2", actual)
    assert (
        WorkspaceService(Settings(data_dir=str(tmp_path))).projects.reopen(project.project_id)
        == project
    )
