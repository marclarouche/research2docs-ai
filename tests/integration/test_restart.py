import os
import subprocess
import sys
from pathlib import Path

from research2docs.core.config import Settings
from research2docs.core.models import ProjectInput
from research2docs.services.workspace_service import WorkspaceService


def test_fresh_process_reopens_without_streamlit(tmp_path):
    project = WorkspaceService(Settings(data_dir=str(tmp_path))).projects.create(
        ProjectInput(title="Restart fixture")
    )
    program = """import sys
sys.modules['streamlit']=None
from research2docs.core.config import Settings
from research2docs.services.workspace_service import WorkspaceService
project=WorkspaceService(Settings(data_dir=sys.argv[1])).projects.reopen(sys.argv[2])
assert project.title=='Restart fixture'
print('reopened')
"""
    result = subprocess.run(
        [sys.executable, "-c", program, str(tmp_path), str(project.project_id)],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
        env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[2] / "src")},
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "reopened"


def test_fresh_process_reopens_source_and_fts_without_streamlit(tmp_path):
    workspace = WorkspaceService(Settings(data_dir=str(tmp_path)))
    project = workspace.projects.create(ProjectInput(title="Source restart fixture"))
    workspace.sources.import_document(
        project.project_id, b"RESTART_EVIDENCE stays on disk.", "restart.txt"
    )
    program = """import sys
sys.modules['streamlit']=None
from research2docs.core.config import Settings
from research2docs.services.workspace_service import WorkspaceService
workspace=WorkspaceService(Settings(data_dir=sys.argv[1]))
hits=workspace.sources.search(sys.argv[2],'RESTART_EVIDENCE')
assert len(hits)==1
assert workspace.sources.resolve_passage(sys.argv[2],hits[0].passage.passage_id)==hits[0].passage
print('source-reopened')
"""
    result = subprocess.run(
        [sys.executable, "-c", program, str(tmp_path), str(project.project_id)],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
        env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[2] / "src")},
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "source-reopened"
