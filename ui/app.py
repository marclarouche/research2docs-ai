"""Phase 6 presentation. All processing and persistence goes through services."""

from pathlib import Path

import streamlit as st
from pydantic import ValidationError

from research2docs.core.config import load_settings
from research2docs.core.errors import Research2DocsError
from research2docs.core.models import Audience, DocumentType, EditorialGoals, ProjectInput
from research2docs.generation.ollama_client import OllamaStatus
from research2docs.services.workspace_service import WorkspaceService
from ui.evidence_review import review
from ui.exports import export_center
from ui.source_views import explorer, import_panel
from ui.studio import studio

ROOT = Path(__file__).resolve().parents[1]
VIEWS = [
    "Dashboard",
    "Project Workspace",
    "Source Explorer",
    "Document Studio",
    "Evidence Review",
    "Export Center",
    "Settings",
]
LATER: dict[str, str] = {}


def main() -> None:
    st.set_page_config(page_title="Research2Docs AI", page_icon="📚", layout="wide")
    st.title("Research2Docs AI")
    st.caption("Technical research → audience-focused documentation → inspectable evidence")
    st.info(
        "Phase 6 · Research, draft, inspect evidence, revise, record human decisions and export locally. Review flags remain visible."
    )
    try:
        workspace = WorkspaceService(load_settings(ROOT))
        projects = workspace.projects.list()
    except Research2DocsError as error:
        st.error(str(error))
        return
    if "next_view" in st.session_state:
        st.session_state.view = st.session_state.pop("next_view")
    view = st.sidebar.radio("Workspace", VIEWS, key="view")
    ids = [str(project.project_id) for project in projects]
    titles = {str(project.project_id): project.title for project in projects}
    if "next_project" in st.session_state:
        st.session_state.project_id = st.session_state.pop("next_project")
    if st.session_state.get("project_id") not in ids:
        st.session_state.pop("project_id", None)
    selected_id = (
        st.sidebar.selectbox(
            "Active project", ids, format_func=titles.__getitem__, key="project_id"
        )
        if ids
        else None
    )
    st.sidebar.caption("Local disk storage · No cloud inference or automatic model downloads")
    if notice := st.session_state.pop("notice", None):
        st.success(notice)
    if view in LATER:
        st.subheader(view)
        st.info(LATER[view])
        return
    try:
        if view == "Dashboard":
            st.subheader("Your research workspace")
            summary = workspace.summary()
            a, b, c = st.columns(3)
            a.metric("Saved projects", summary.projects)
            b.metric("Saved drafts", summary.drafts)
            c.metric("Unresolved claim records", summary.unresolved_claims)
            st.caption(
                "Automated assessments require human review. Decisions apply only to the revision reviewed."
            )
            if projects:
                st.dataframe(
                    [
                        {
                            "Title": p.title,
                            "Updated": p.updated_at.isoformat(),
                            "Version": p.version,
                        }
                        for p in projects
                    ],
                    hide_index=True,
                )
                if st.button("Open selected project"):
                    st.session_state.next_view = "Project Workspace"
                    st.rerun()
            else:
                st.write("Start a project to save your research purpose and editorial goals.")
            st.subheader("Create a research project")
            with st.form("create_project"):
                title = st.text_input("Project title", max_chars=200)
                description = st.text_area("Research purpose", max_chars=10000)
                submitted = st.form_submit_button("Create project")
            if submitted:
                project = workspace.projects.create(
                    ProjectInput(title=title, description=description)
                )
                st.session_state.next_project = str(project.project_id)
                st.session_state.next_view = "Project Workspace"
                st.session_state.notice = "Project saved locally."
                st.rerun()
            show_ollama(workspace)
        elif view == "Project Workspace":
            st.subheader("Project Workspace")
            if not selected_id:
                st.info("Create a project on the Dashboard first.")
                return
            project = workspace.projects.reopen(selected_id)
            st.text(project.title)
            st.caption(f"Project {project.project_id} · Saved version {project.version}")
            # Capture the version when this form was rendered, not from the fresh submit rerun.
            if st.session_state.get("editing_project") != selected_id:
                st.session_state.editing_project = selected_id
                st.session_state.editing_version = project.version
            if st.button("Reload saved project"):
                st.session_state.editing_project = None
                st.session_state.pop("edit_form_key", None)
                st.session_state.form_generation = st.session_state.get("form_generation", 0) + 1
                st.rerun()
            form_key = f"edit_{selected_id}_{st.session_state.get('form_generation', 0)}"
            with st.form(form_key):
                title = st.text_input("Project title", value=project.title, max_chars=200)
                description = st.text_area(
                    "Research purpose", value=project.description, max_chars=10000
                )
                kind = st.selectbox(
                    "Document type",
                    list(DocumentType),
                    index=list(DocumentType).index(project.goals.document_type),
                    format_func=lambda item: item.value.replace("_", " ").title(),
                )
                audience = st.selectbox(
                    "Audience",
                    list(Audience),
                    index=list(Audience).index(project.goals.audience),
                    format_func=lambda item: item.value.replace("_", " ").title(),
                )
                custom = st.text_input(
                    "Custom audience description", project.goals.custom_audience, max_chars=500
                )
                working = st.text_input("Working title", project.goals.working_title, max_chars=200)
                words = st.number_input(
                    "Approximate word count",
                    min_value=100,
                    max_value=10000,
                    value=project.goals.approximate_words,
                    step=100,
                )
                depths = ["introductory", "moderate", "detailed"]
                depth = st.selectbox(
                    "Technical depth",
                    depths,
                    index=depths.index(project.goals.technical_depth),
                    format_func=str.title,
                )
                instructions = st.text_area(
                    "Editorial instructions", project.goals.instructions, max_chars=5000
                )
                saved = st.form_submit_button("Save project")
            st.caption("Saved goals provide the defaults for Document Studio.")
            if saved:
                goals = EditorialGoals.model_validate(
                    {
                        "document_type": kind,
                        "audience": audience,
                        "custom_audience": custom,
                        "working_title": working,
                        "approximate_words": words,
                        "technical_depth": depth,
                        "instructions": instructions,
                    }
                )
                updated = workspace.projects.edit(
                    selected_id,
                    ProjectInput(title=title, description=description, goals=goals),
                    st.session_state.editing_version,
                )
                st.session_state.editing_version = updated.version
                st.session_state.notice = "Project changes saved."
                st.rerun()
            import_panel(workspace, selected_id)
        elif view == "Source Explorer":
            if not selected_id:
                st.info("Create a project on the Dashboard first.")
            else:
                explorer(workspace, selected_id)
        elif view == "Document Studio":
            if not selected_id:
                st.info("Create a project on the Dashboard first.")
            else:
                studio(workspace, selected_id)
        elif view == "Evidence Review":
            if not selected_id:
                st.info("Create a project on the Dashboard first.")
            else:
                review(workspace, selected_id)
        elif view == "Export Center":
            if not selected_id:
                st.info("Create a project on the Dashboard first.")
            else:
                export_center(workspace, selected_id)
        elif view == "Settings":
            st.subheader("Local settings")
            st.text("Storage: " + workspace.settings.data_dir)
            st.caption(
                "Set RESEARCH2DOCS_DATA_DIR before starting to open a different local workspace. Existing data is not moved."
            )
            st.text(f"Ollama: {workspace.settings.ollama.host}:{workspace.settings.ollama.port}")
            st.text("Saved model selection: " + (workspace.selected_model() or "None"))
            show_ollama(workspace, select=True)
    except ValidationError:
        st.error(
            "Review the fields. Supply a nonblank title, valid lengths and a custom audience description when selected."
        )
    except Research2DocsError as error:
        st.error(str(error))


def show_ollama(workspace: WorkspaceService, *, select: bool = False) -> None:
    st.subheader("Local Ollama")
    if st.button("Check local Ollama"):
        st.session_state.ollama_status = workspace.check_ollama().model_dump_json()
    if raw := st.session_state.get("ollama_status"):
        status = OllamaStatus.model_validate_json(raw)
        st.text(status.message)
        st.caption("Last requested check; check again after changing models or restarting Ollama.")
        if status.available:
            st.text(f"Installed local model candidates: {len(status.models)}")
            if select and status.models:
                name = st.selectbox("Local model", [model.name for model in status.models])
                if st.button("Save model selection"):
                    workspace.select_model(name)
                    st.session_state.notice = (
                        "Local model selection saved. No inference was started."
                    )
                    st.rerun()
    else:
        st.caption("Not checked in this session. Project management works without Ollama.")


if __name__ == "__main__":
    main()
