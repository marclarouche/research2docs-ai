"""Document Studio: forms and plain-text draft/evidence presentation only."""

import streamlit as st

from research2docs.core.models import Audience, DocumentType, EditorialGoals
from research2docs.generation.models import GenerationRequest, SavedDraft
from research2docs.services.workspace_service import WorkspaceService
from ui.editorial import edit_panel, revision_picker


def show_draft(draft: SavedDraft) -> None:
    st.subheader("Saved unreviewed draft")
    st.text(draft.title)
    st.warning(
        "UNREVIEWED AI DRAFT · All content requires review. Citations do not establish factual support."
    )
    for warning in draft.warnings:
        st.text(warning)
    st.text(
        f"Model: {draft.model} · Prompt: {draft.prompt_version} · Saved: {draft.created_at.isoformat()}"
    )
    st.caption(f"Draft: {draft.draft_id} · Revision: {draft.revision_id} · Run: {draft.run_id}")
    for section in draft.content.sections:
        st.subheader(section.kind.replace("_", " ").title())
        st.text(section.heading)
        for block in section.blocks:
            st.text(block.text)
            st.caption(
                "References: " + (", ".join(block.citations) or "None · Requires verification")
            )
            if block.review_note:
                st.text("Review note: " + block.review_note)
    if draft.content.limitations:
        st.subheader("Model-reported limitations · Unassessed")
        for note in draft.content.limitations:
            st.text(note)
    with st.expander("Inspect supplied evidence"):
        for item in draft.evidence:
            st.text(f"{item.alias} · Passage {item.passage.passage_id}")
            st.text(
                f"Page: {item.passage.page or 'Unavailable'} · Section: {item.passage.section or 'Unavailable'}"
            )
            st.text(item.passage.text)
    st.caption(
        "The saved draft warnings describe generation-time checks. Evidence Review shows subsequent assessments."
    )
    with st.expander("Generation provenance"):
        st.json(
            {
                "model_digest": draft.model_digest,
                "prompt_sha256": draft.prompt_sha256,
                "goals": draft.goals.model_dump(mode="json"),
                "retrieval_query": draft.query,
            }
        )


def studio(workspace: WorkspaceService, project_id: str) -> None:
    st.subheader("Document Studio")
    project = workspace.projects.reopen(project_id)
    st.caption(
        "Each generation saves a new draft, initial revision and claim ledger. Use the editorial workspace for revisions and Evidence Review for decisions."
    )
    st.text(
        "Selected local model: " + (workspace.selected_model() or "None · Select one in Settings")
    )
    with st.form(f"generation_{project_id}"):
        goals = project.goals
        kind = st.selectbox(
            "Output type",
            list(DocumentType),
            index=list(DocumentType).index(goals.document_type),
            format_func=lambda v: v.value.replace("_", " ").title(),
        )
        audience = st.selectbox(
            "Intended audience",
            list(Audience),
            index=list(Audience).index(goals.audience),
            format_func=lambda v: v.value.replace("_", " ").title(),
        )
        custom = st.text_input("Custom audience", value=goals.custom_audience, max_chars=500)
        title = st.text_input(
            "Draft working title", value=goals.working_title or project.title, max_chars=200
        )
        count = st.number_input(
            "Target word count",
            min_value=100,
            max_value=10000,
            value=goals.approximate_words,
            step=100,
        )
        depth = st.selectbox(
            "Draft technical depth",
            ["introductory", "moderate", "detailed"],
            index=["introductory", "moderate", "detailed"].index(goals.technical_depth),
        )
        instructions = st.text_area(
            "Additional editorial instructions", value=goals.instructions, max_chars=5000
        )
        query = st.text_area(
            "Research question / evidence search",
            max_chars=2000,
            help="Keyword retrieval selects evidence before generation. No matching passages means no inference.",
        )
        submitted = st.form_submit_button("Generate and save unreviewed draft")
    if submitted:
        request = GenerationRequest(
            goals=EditorialGoals.model_validate(
                {
                    "document_type": kind,
                    "audience": audience,
                    "custom_audience": custom,
                    "working_title": title,
                    "approximate_words": count,
                    "technical_depth": depth,
                    "instructions": instructions,
                }
            ),
            query=query,
        )
        with st.spinner("Generating locally and checking draft structure and citation references…"):
            draft = workspace.generation.generate(project_id, request)
        st.session_state[f"draft_{project_id}"] = str(draft.draft_id)
        st.success("Unreviewed draft saved locally.")
    drafts = workspace.generation.list_drafts(project_id)
    if drafts:
        ids = [str(d.draft_id) for d in drafts]
        labels = {str(d.draft_id): f"{d.title} · {d.created_at.isoformat()}" for d in drafts}
        key = f"draft_{project_id}"
        if st.session_state.get(key) not in ids:
            st.session_state.pop(key, None)
        selected = st.selectbox("Saved drafts", ids, format_func=labels.__getitem__, key=key)
        revision = revision_picker(workspace, project_id, selected, prefix="studio")
        show_draft(revision)
        edit_panel(workspace, project_id, revision)
    else:
        st.info("No drafts saved for this project yet.")
