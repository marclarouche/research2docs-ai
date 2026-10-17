"""Prepare bounded local downloads and invalidate stale review snapshots."""

import streamlit as st

from research2docs.exporting.models import ExportFormat
from research2docs.services.workspace_service import WorkspaceService
from ui.editorial import revision_picker


def export_center(workspace: WorkspaceService, project_id: str) -> None:
    st.subheader("Export Center")
    st.warning(
        "Exports retain draft labels, citations and unresolved review flags. Export does not verify a document."
    )
    drafts = workspace.generation.list_drafts(project_id)
    if not drafts:
        st.info("Generate a draft in Document Studio first.")
        return
    mapping = {str(d.draft_id): d for d in drafts}
    selected = st.selectbox(
        "Draft to export",
        list(mapping),
        format_func=lambda key: mapping[key].title,
        key=f"export_draft_{project_id}",
    )
    draft = revision_picker(workspace, project_id, selected, prefix="export")
    ledger = workspace.verification.ledger(project_id, selected, revision_id=draft.revision_id)
    unresolved = sum(u.claim.human_review != "accepted" for u in ledger.units)
    st.text(
        f"Revision {draft.revision_number} · {draft.origin} · {unresolved} of {len(ledger.units)} review units unresolved"
    )
    formats: dict[str, ExportFormat] = {
        "Markdown": "markdown",
        "Editable Word document": "docx",
        "Standalone HTML": "html",
        "JSON evidence manifest": "json",
    }
    label = st.selectbox("Export format", list(formats))
    kind = formats[label]
    st.caption(
        "The JSON manifest includes exact passages, current claims, saved assessment history and recorded human decisions. Readable formats include source metadata and exact evidence excerpts. Reference URLs remain inert labels."
    )
    if st.button("Prepare export"):
        output = workspace.exports.export(project_id, selected, kind, revision_id=draft.revision_id)
        st.session_state.prepared_export = {
            "filename": output.filename,
            "mime": output.mime_type,
            "data": output.data,
            "revision_id": str(output.revision_id),
            "claim_versions": output.claim_versions,
            "format": kind,
        }
        st.success("Draft export prepared. Review status has not changed.")
    cached = st.session_state.get("prepared_export")
    versions = {str(u.claim.claim_id): u.version for u in ledger.units}
    if cached:
        if (
            cached["revision_id"] == str(draft.revision_id)
            and cached["format"] == kind
            and cached["claim_versions"] == versions
        ):
            st.text(cached["filename"])
            st.download_button(
                "Download prepared export",
                data=cached["data"],
                file_name=cached["filename"],
                mime=cached["mime"],
                on_click="ignore",
            )
        else:
            st.info("Selection or review status changed. Prepare a fresh export to download it.")
