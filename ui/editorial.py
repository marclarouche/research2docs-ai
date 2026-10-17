"""Revision editing/regeneration forms; all writes go through editorial services."""

import streamlit as st

from research2docs.editorial.models import RevisionEdit
from research2docs.generation.models import SavedDraft
from research2docs.services.workspace_service import WorkspaceService


def revision_picker(
    workspace: WorkspaceService, project_id: str, draft_id: str, *, prefix: str
) -> SavedDraft:
    history = workspace.editorial.history(project_id, draft_id)
    mapping = {str(d.revision_id): d for d in history}
    key = f"{prefix}_revision_{draft_id}"
    if f"next_{key}" in st.session_state:
        st.session_state[key] = st.session_state.pop(f"next_{key}")
    if st.session_state.get(key) not in mapping:
        st.session_state.pop(key, None)
    selected = st.selectbox(
        "Saved revision",
        list(mapping),
        format_func=lambda key: (
            f"Revision {mapping[key].revision_number} · {mapping[key].origin} · {mapping[key].created_at.isoformat()}"
        ),
        key=key,
    )
    return workspace.generation.reopen(project_id, draft_id, revision_id=selected)


def edit_panel(workspace: WorkspaceService, project_id: str, draft: SavedDraft) -> None:
    latest = workspace.generation.reopen(project_id, draft.draft_id)
    is_latest = latest.revision_id == draft.revision_id
    st.subheader("Editorial workspace")
    st.text(
        f"Revision {draft.revision_number} · {draft.origin} · Note: {draft.revision_note or 'Initial generation'}"
    )
    if st.button("Open latest revision"):
        st.session_state[f"next_studio_revision_{draft.draft_id}"] = str(latest.revision_id)
        st.rerun()
    if not is_latest:
        st.info("Historical revision selected. Open the latest revision to edit or regenerate.")
        return
    section_index = st.selectbox(
        "Section to edit",
        list(range(len(draft.content.sections))),
        format_func=lambda i: draft.content.sections[i].kind.replace("_", " ").title(),
        key=f"section_{draft.revision_id}",
    )
    section = draft.content.sections[section_index]
    with st.form(f"edit_revision_{draft.revision_id}_{section_index}"):
        editor = st.text_input("Editor name", max_chars=200)
        note = st.text_area("Revision note / reason", max_chars=5000)
        title = st.text_input("Revision title", value=draft.title, max_chars=200)
        heading = st.text_input("Section heading", value=section.heading, max_chars=200)
        edited = []
        for index, block in enumerate(section.blocks):
            text = st.text_area(f"Block {index + 1} text", value=block.text, max_chars=5000)
            cites = st.multiselect(
                f"Block {index + 1} citations",
                [e.alias for e in draft.evidence],
                default=block.citations,
            )
            review_note = st.text_area(
                f"Block {index + 1} review note", value=block.review_note, max_chars=1000
            )
            edited.append(
                block.model_copy(
                    update={"text": text, "citations": cites, "review_note": review_note}
                )
            )
        saved = st.form_submit_button("Save as new revision")
    if saved:
        content = draft.content.model_copy(deep=True)
        content.sections[section_index] = section.model_copy(
            update={"heading": heading, "blocks": edited}
        )
        result = workspace.editorial.save(
            project_id,
            draft.draft_id,
            draft.revision_id,
            RevisionEdit(title=title, content=content, editor=editor, note=note),
        )
        st.session_state[f"next_studio_revision_{draft.draft_id}"] = str(result.revision_id)
        st.session_state.notice = (
            "New revision saved. Claim assessments and human decisions require fresh review."
        )
        st.rerun()
    with st.form(f"regenerate_{draft.revision_id}_{section_index}"):
        regen_editor = st.text_input("Regeneration editor name", max_chars=200)
        regen_note = st.text_area("Regeneration reason", max_chars=5000)
        instructions = st.text_area("Section regeneration instructions", max_chars=5000)
        regenerate = st.form_submit_button("Regenerate selected section locally")
    if regenerate:
        with st.spinner("Regenerating only the selected section locally…"):
            result = workspace.editorial.regenerate(
                project_id,
                draft.draft_id,
                draft.revision_id,
                section_index,
                editor=regen_editor,
                note=regen_note,
                instructions=instructions,
            )
        st.session_state[f"next_studio_revision_{draft.draft_id}"] = str(result.revision_id)
        st.session_state.notice = (
            "Regenerated section saved in a new revision. Fresh review is required."
        )
        st.rerun()
    st.caption(
        "Each save preserves earlier revisions and decisions. All claims in a new revision reset to pending, including unchanged blocks."
    )
