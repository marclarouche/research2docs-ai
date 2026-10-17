import socket
from pathlib import Path

from streamlit.testing.v1 import AppTest

from research2docs.core.config import Settings
from research2docs.core.models import ProjectInput
from research2docs.services.workspace_service import WorkspaceService

ROOT = Path(__file__).resolve().parents[2]


def test_ui_create_edit_reopen_without_network(tmp_path, monkeypatch):
    monkeypatch.setenv("RESEARCH2DOCS_DATA_DIR", str(tmp_path / "store"))

    def forbidden(*args, **kwargs):
        raise AssertionError("No startup network")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    at = AppTest.from_file(str(ROOT / "ui/app.py"), default_timeout=30).run()
    assert not at.exception
    next(w for w in at.text_input if w.label == "Project title").set_value("Fictional research")
    next(w for w in at.button if w.label == "Create project").click().run()
    assert not at.exception
    assert at.radio[0].value == "Project Workspace"
    next(w for w in at.text_input if w.label == "Project title").set_value("Revised title")
    next(w for w in at.button if w.label == "Save project").click().run()
    assert not at.exception
    second = AppTest.from_file(str(ROOT / "ui/app.py"), default_timeout=30).run()
    assert not second.exception
    assert "Revised title" in second.selectbox[0].options
    for view in [
        "Source Explorer",
        "Document Studio",
        "Evidence Review",
        "Export Center",
        "Settings",
    ]:
        second.radio[0].set_value(view).run()
        assert not second.exception


def test_ui_stale_save_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("RESEARCH2DOCS_DATA_DIR", str(tmp_path))
    workspace = WorkspaceService(Settings(data_dir=str(tmp_path)))
    p = workspace.projects.create(ProjectInput(title="Original"))
    at = AppTest.from_file(str(ROOT / "ui/app.py"), default_timeout=30).run()
    at.radio[0].set_value("Project Workspace").run()
    workspace.projects.edit(p.project_id, ProjectInput(title="Other session"), 1)
    next(w for w in at.text_input if w.label == "Project title").set_value("Stale overwrite")
    next(w for w in at.button if w.label == "Save project").click().run()
    assert not at.exception
    assert any("another session" in w.value for w in at.error)
    assert workspace.projects.reopen(p.project_id).title == "Other session"


def test_ui_model_selection_refreshes_saved_preference(tmp_path, monkeypatch):
    from research2docs.generation.ollama_client import LocalModel, OllamaClient

    monkeypatch.setenv("RESEARCH2DOCS_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(
        OllamaClient,
        "models",
        lambda self: [LocalModel(name="local:latest", digest="fixture", size_bytes=1)],
    )
    monkeypatch.setattr(OllamaClient, "_request", lambda *args: {"details": {"family": "fixture"}})
    at = AppTest.from_file(str(ROOT / "ui/app.py"), default_timeout=30).run()
    at.radio[0].set_value("Settings").run()
    next(w for w in at.button if w.label == "Check local Ollama").click().run()
    next(w for w in at.button if w.label == "Save model selection").click().run()
    assert not at.exception
    assert any(w.value == "Saved model selection: local:latest" for w in at.text)


def test_ui_import_search_and_inspect_source(tmp_path, monkeypatch):
    from io import BytesIO

    import streamlit

    monkeypatch.setenv("RESEARCH2DOCS_DATA_DIR", str(tmp_path))
    workspace = WorkspaceService(Settings(data_dir=str(tmp_path)))
    workspace.projects.create(ProjectInput(title="Source UI fixture"))

    class Upload(BytesIO):
        name = "ui-guide.md"

    monkeypatch.setattr(
        streamlit,
        "file_uploader",
        lambda *args, **kwargs: [Upload(b"# UI reference\n\nUI_EVIDENCE is a fictional value.\n")],
    )
    at = AppTest.from_file(str(ROOT / "ui/app.py"), default_timeout=30).run()
    at.radio[0].set_value("Project Workspace").run()
    next(w for w in at.button if w.label == "Import and index sources").click().run()
    assert not at.exception
    assert any("Imported and indexed" in w.value for w in at.success)
    at.radio[0].set_value("Source Explorer").run()
    next(w for w in at.text_input if w.label == "Search source passages").set_value("UI_EVIDENCE")
    next(w for w in at.button if w.label == "Search passages").click().run()
    assert not at.exception
    assert any("UI_EVIDENCE" in w.value for w in at.code)
    assert any("Passage ID:" in w.value for w in at.text)


def test_import_form_can_submit_and_reports_empty_selection(tmp_path, monkeypatch):
    monkeypatch.setenv("RESEARCH2DOCS_DATA_DIR", str(tmp_path))
    workspace = WorkspaceService(Settings(data_dir=str(tmp_path)))
    workspace.projects.create(ProjectInput(title="Import form fixture"))
    at = AppTest.from_file(str(ROOT / "ui/app.py"), default_timeout=30).run()
    at.radio[0].set_value("Project Workspace").run()
    button = next(w for w in at.button if w.label == "Import and index sources")
    assert not button.disabled
    button.click().run()
    assert not at.exception
    assert any("between 1 and 10" in error.value for error in at.error)
