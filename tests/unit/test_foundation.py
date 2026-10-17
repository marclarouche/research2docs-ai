import sqlite3
from uuid import uuid4

import pytest
from pydantic import ValidationError

from research2docs.core.config import OllamaSettings, load_settings
from research2docs.core.diagnostics import record_event
from research2docs.core.errors import (
    ConfigurationError,
    InputError,
    ProjectNotFound,
    RevisionConflict,
    SchemaError,
    StorageError,
)
from research2docs.core.models import (
    AssessmentStatus,
    Audience,
    Claim,
    EditorialGoals,
    Project,
    ProjectInput,
    utc_now,
)
from research2docs.services.project_service import ProjectService
from research2docs.storage.database import Database
from research2docs.storage.repositories import ProjectRepository


def service(path):
    return ProjectService(ProjectRepository(Database(path)))


def test_create_edit_and_restart_preserve_goals_and_sql_text(tmp_path):
    first = service(tmp_path)
    project = first.create(
        ProjectInput(
            title="Research'); DROP TABLE projects; --", description="<script>untrusted</script>"
        )
    )
    goals = EditorialGoals(
        audience=Audience.CUSTOM, custom_audience="Technical editors", approximate_words=800
    )
    edited = first.edit(project.project_id, ProjectInput(title="Updated", goals=goals), 1)
    reopened = service(tmp_path).reopen(str(project.project_id))
    assert reopened == edited
    assert reopened.version == 2 and reopened.created_at == project.created_at
    assert reopened.goals.custom_audience == "Technical editors"
    assert len(service(tmp_path).list()) == 1
    assert not (tmp_path / "untrusted").exists()


def test_stale_editor_cannot_overwrite_other_session(tmp_path):
    a = service(tmp_path)
    b = service(tmp_path)
    p = a.create(ProjectInput(title="Original"))
    a.edit(p.project_id, ProjectInput(title="Accepted edit"), 1)
    with pytest.raises(RevisionConflict):
        b.edit(p.project_id, ProjectInput(title="Stale edit"), 1)
    assert b.reopen(p.project_id).title == "Accepted edit"


@pytest.mark.parametrize("identifier", ["../../outside", "file:/tmp/private.db", "not-an-id"])
def test_project_identifiers_are_data_not_paths(tmp_path, identifier):
    with pytest.raises(InputError):
        service(tmp_path).reopen(identifier)
    assert list(tmp_path.iterdir()) == [tmp_path / "research2docs.sqlite3"]


def test_unknown_project_and_invalid_project_fields(tmp_path):
    with pytest.raises(ProjectNotFound):
        service(tmp_path).reopen(uuid4())
    for title in ["", "  ", "x" * 201]:
        with pytest.raises(ValidationError):
            ProjectInput(title=title)
    with pytest.raises(ValidationError):
        EditorialGoals(audience=Audience.CUSTOM)
    with pytest.raises(ValidationError):
        ProjectInput(title="ok", command="execute")


def test_migration_reopen_no_duplicates_and_foreign_keys(tmp_path):
    db = Database(tmp_path)
    p = ProjectRepository(db).create(Project(title="Saved"))
    Database(tmp_path)
    with db.session() as conn:
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert conn.execute("SELECT count(*) FROM schema_migrations").fetchone()[0] == 5
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 5
    with pytest.raises(StorageError), db.session(write=True) as conn:
        conn.execute(
            "INSERT INTO drafts VALUES (?, ?, ?, ?, ?)",
            (str(uuid4()), str(uuid4()), "orphan", "{}", utc_now().isoformat()),
        )
    assert ProjectRepository(Database(tmp_path)).get(p.project_id).title == "Saved"


def test_rollback_and_unknown_schema_do_not_destroy_projects(tmp_path):
    repo = ProjectRepository(Database(tmp_path))
    p = repo.create(Project(title="Keep me"))
    with pytest.raises(RuntimeError), repo.database.session(write=True) as conn:
        conn.execute("UPDATE projects SET title=?", ("Rollback",))
        raise RuntimeError("Controlled transaction failure")
    assert repo.get(p.project_id).title == "Keep me"
    with repo.database.session(write=True) as conn:
        conn.execute("PRAGMA user_version=99")
    before = repo.database.path.read_bytes()
    with pytest.raises(SchemaError):
        Database(tmp_path)
    assert repo.database.path.read_bytes() == before


def test_unrecognized_existing_database_is_not_rebuilt(tmp_path):
    path = tmp_path / "research2docs.sqlite3"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE external_data (value TEXT)")
    with pytest.raises(SchemaError):
        Database(tmp_path)
    with sqlite3.connect(path) as conn:
        assert conn.execute('SELECT name FROM sqlite_master WHERE type="table"').fetchall() == [
            ("external_data",)
        ]


def test_changed_migration_history_is_rejected(tmp_path):
    db = Database(tmp_path)
    with db.session(write=True) as conn:
        conn.execute("UPDATE schema_migrations SET checksum='changed'")
    with pytest.raises(SchemaError):
        Database(tmp_path)


def test_symlink_database_and_diagnostics_cannot_write_outside_root(tmp_path):
    outside = tmp_path / "outside"
    outside.write_text("unchanged")
    root = tmp_path / "data"
    root.mkdir()
    (root / "research2docs.sqlite3").symlink_to(outside)
    with pytest.raises(StorageError):
        Database(root)
    (root / "diagnostics.log").symlink_to(outside)
    with pytest.raises(StorageError):
        record_event(root, "ollama_checked")
    assert outside.read_text() == "unchanged"


def test_bounded_settings_and_operator_storage_override(tmp_path, monkeypatch):
    (tmp_path / "config").mkdir()
    p = tmp_path / "config/research2docs.toml"
    p.write_text('[ollama]\nhost="localhost"\n')
    s = load_settings(tmp_path)
    assert s.ollama.host == "127.0.0.1"
    assert s.data_dir == str(tmp_path / "data")
    monkeypatch.setenv("RESEARCH2DOCS_DATA_DIR", str(tmp_path / "other"))
    assert load_settings(tmp_path).data_dir == str(tmp_path / "other")
    p.write_text("x" * 32769)
    with pytest.raises(ConfigurationError):
        load_settings(tmp_path)


@pytest.mark.parametrize(
    "host",
    [
        "example.com",
        "192.0.2.1",
        "169.254.169.254",
        "127.0.0.1.evil",
        "http://127.0.0.1",
        "user@localhost",
    ],
)
def test_nonloopback_hosts_rejected(host):
    with pytest.raises(ValidationError):
        OllamaSettings(host=host)


def test_human_verified_cannot_be_model_self_attestation():
    with pytest.raises(ValidationError):
        Claim(
            claim_id=uuid4(),
            revision_id=uuid4(),
            project_id=uuid4(),
            text="Claim",
            explanation="Model says true",
            assessment=AssessmentStatus.HUMAN_VERIFIED,
            assessment_method="model",
            assessed_at=utc_now(),
        )


def test_diagnostics_only_log_event_codes(tmp_path):
    record_event(tmp_path, "project_saved")
    text = (tmp_path / "diagnostics.log").read_text()
    assert text.endswith(" project_saved\n")
    assert len(text.splitlines()) == 1


def test_failed_initial_migration_is_atomic_and_can_retry(tmp_path, monkeypatch):
    from research2docs.storage import database

    statements = database.MIGRATION_1
    monkeypatch.setattr(database, "MIGRATION_1", (*statements, "CREATE TABLE projects (bad TEXT)"))
    with pytest.raises(StorageError):
        Database(tmp_path)
    with sqlite3.connect(tmp_path / "research2docs.sqlite3") as conn:
        assert conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall() == []
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 0
    monkeypatch.setattr(database, "MIGRATION_1", statements)
    assert service(tmp_path).list() == []


def test_evidence_foreign_keys_do_not_link_other_projects(tmp_path):
    db = Database(tmp_path)
    repo = ProjectRepository(db)
    a = repo.create(Project(title="A"))
    b = repo.create(Project(title="B"))
    source = str(uuid4())
    passage = str(uuid4())
    draft = str(uuid4())
    revision = str(uuid4())
    claim = str(uuid4())
    with db.session(write=True) as conn:
        conn.execute(
            "INSERT INTO source_documents VALUES (?,?,?,?,?)",
            (str(a.project_id), source, "fixture.txt", "a" * 64, "{}"),
        )
        conn.execute(
            "INSERT INTO source_passages VALUES (?,?,?,?,?,?,?)",
            (str(a.project_id), passage, source, "Fictional evidence", 0, "{}", "fixture"),
        )
        conn.execute(
            "INSERT INTO drafts VALUES (?,?,?,?,?)",
            (str(b.project_id), draft, "Draft", "{}", utc_now().isoformat()),
        )
        conn.execute(
            "INSERT INTO revisions VALUES (?,?,?,?,?,?)",
            (str(b.project_id), revision, draft, 1, "Draft text", utc_now().isoformat()),
        )
        conn.execute(
            "INSERT INTO claims VALUES (?,?,?,?,?,?)",
            (str(b.project_id), claim, revision, "Claim", "unsupported", "{}"),
        )
    with pytest.raises(StorageError), db.session(write=True) as conn:
        conn.execute(
            "INSERT INTO evidence_links VALUES (?,?,?,?)",
            (str(b.project_id), claim, passage, "supporting"),
        )
