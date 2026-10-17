"""Evidence Review presents service-owned claim records and exact inert evidence."""

import streamlit as st

from research2docs.editorial.models import HumanReview
from research2docs.services.workspace_service import WorkspaceService
from ui.editorial import revision_picker


def review(workspace: WorkspaceService, project_id: str) -> None:
    st.subheader("Evidence Review")
    st.warning(
        "AI-assisted source support is not independent verification. Every claim still requires human review."
    )
    st.caption(
        "Review units cover every prose block. A block may contain multiple claims; full support must cover all of them. Headings and model review notes are not separately assessed."
    )
    drafts = workspace.generation.list_drafts(project_id)
    if not drafts:
        st.info("Generate a draft in Document Studio first.")
        return
    mapping = {str(d.draft_id): d for d in drafts}
    draft_id = st.selectbox(
        "Draft to assess",
        list(mapping),
        format_func=lambda key: mapping[key].title,
        key=f"review_draft_{project_id}",
    )
    draft = revision_picker(workspace, project_id, draft_id, prefix="review")
    ledger = workspace.verification.ledger(project_id, draft_id, revision_id=draft.revision_id)
    a, b, c = st.columns(3)
    a.metric("Review units", len(ledger.units))
    b.metric("Awaiting assessment", sum(u.state == "not_assessed" for u in ledger.units))
    c.metric("Human review pending", sum(u.claim.human_review == "pending" for u in ledger.units))
    st.text(f"Draft {draft.draft_id} · Revision {draft.revision_id}")
    st.text(
        "Model for next assessment: " + (workspace.selected_model() or "None · Select in Settings")
    )
    st.dataframe(
        [
            {
                "Unit": index + 1,
                "Status": u.claim.assessment.value
                if u.state != "not_assessed" or u.claim.human_review != "pending"
                else "not_assessed",
                "Citations": u.citation_state,
                "Human review": u.claim.human_review,
                "Text": u.claim.text[:180],
            }
            for index, u in enumerate(ledger.units)
        ],
        hide_index=True,
    )
    by_id = {str(u.claim.claim_id): u for u in ledger.units}
    labels = {
        str(u.claim.claim_id): f"{i + 1} · {u.claim.text[:100]}" for i, u in enumerate(ledger.units)
    }
    claim_id = st.selectbox(
        "Claim / prose block",
        list(by_id),
        format_func=labels.__getitem__,
        key=f"review_claim_{draft.revision_id}",
    )
    unit = by_id[claim_id]
    version_key = f"assessment_version_{claim_id}"
    if version_key not in st.session_state:
        st.session_state[version_key] = unit.version
    if st.button("Reload claim assessment"):
        st.session_state[version_key] = unit.version
        st.rerun()
    if st.button("Assess selected claim locally"):
        with st.spinner("Comparing the claim with local source passages…"):
            updated = workspace.verification.assess(
                project_id,
                draft_id,
                claim_id,
                expected_version=st.session_state[version_key],
                revision_id=draft.revision_id,
            )
        st.session_state[version_key] = updated.version
        st.session_state.notice = "Assessment saved. Human review remains pending."
        st.rerun()
    st.subheader("Claim text")
    st.text(unit.claim.text)
    st.text(f"Claim ID: {unit.claim.claim_id} · Version: {unit.version}")
    st.text(
        "Assessment: "
        + (
            "Not yet assessed"
            if unit.state == "not_assessed" and unit.claim.human_review == "pending"
            else unit.claim.assessment.value.replace("_", " ").title()
        )
    )
    st.text("Assessment state: " + unit.state)
    if unit.claim.human_review == "pending":
        st.warning("Provisional source assessment · Human review is still required.")
    else:
        st.info(
            "Human editorial decision recorded for this exact revision. Inspect the rationale and history."
        )
    st.text("Human review: " + unit.claim.human_review)
    st.text("Assessment explanation · AI-generated when using the support-assessment method")
    st.text(unit.claim.explanation)
    st.text("Human rationale: " + (unit.claim.human_rationale or "No human decision recorded."))
    st.text(
        f"Method: {unit.claim.assessment_method} · Timestamp: {unit.claim.assessed_at.isoformat()}"
    )
    for flag in unit.review_flags:
        st.text(flag)
    source_map = {s.source.source_id: s.source for s in workspace.sources.list_sources(project_id)}
    for label, quotes in [
        ("Supporting excerpts", unit.supporting),
        ("Contradictory excerpts", unit.contradictory),
        ("Temporal excerpts", unit.temporal),
    ]:
        st.subheader(label)
        if not quotes:
            st.text("None recorded.")
        for quote in quotes:
            passage = workspace.sources.resolve_passage(project_id, quote.passage_id)
            source = source_map[passage.source_id]
            st.text(source.title + " · " + source.filename)
            st.text(
                f"Passage {passage.passage_id} · Page {passage.page or 'unavailable'} · Section {passage.section or 'unavailable'}"
            )
            st.text(f"Exact excerpt · passage characters [{quote.start}, {quote.end})")
            st.text(quote.quote)
            with st.expander("Full stored passage · " + str(passage.passage_id)):
                st.text(passage.text)
    with st.expander("Original draft citations and unresolved warnings"):
        st.text("Original citation check: " + unit.citation_state)
        for pid in unit.cited_passages:
            st.text(str(pid))
            st.text(workspace.sources.resolve_passage(project_id, pid).text)
        for warning in draft.warnings:
            st.text(warning)
    with st.expander("Assessment provenance"):
        st.json(
            {
                "assessment_id": str(unit.assessment_id) if unit.assessment_id else None,
                "model": unit.model,
                "model_digest": unit.model_digest,
                "prompt_sha256": unit.prompt_sha256,
                "claim_text_sha256": unit.text_sha256,
                "revision_content_sha256": ledger.content_sha256,
            }
        )
    st.subheader("Record an explicit human decision")
    st.caption(
        "Accept means you reviewed the selected passages and accept source support for this exact claim/revision. It is not independent external verification."
    )
    passage_ids = list(
        dict.fromkeys(
            [
                *unit.cited_passages,
                *unit.human_evidence,
                *[q.passage_id for q in [*unit.supporting, *unit.contradictory, *unit.temporal]],
            ]
        )
    )
    extra_source = st.selectbox(
        "Additional source to inspect for human review",
        [None, *source_map],
        format_func=lambda sid: (
            "Use existing claim references" if sid is None else source_map[sid].title
        ),
        key=f"human_source_{claim_id}",
    )
    if extra_source is not None:
        extra = workspace.sources.source_passages(project_id, extra_source)
        passage_ids = list(dict.fromkeys([*passage_ids, *[p.passage_id for p in extra]]))
        with st.expander("Inspect additional source passages"):
            for passage in extra:
                st.text(str(passage.passage_id))
                st.text(passage.text)
    with st.form(f"human_review_{claim_id}_{unit.version}"):
        reviewer = st.text_input("Reviewer name", max_chars=200)
        action = st.selectbox("Review decision", ["accepted", "rejected", "reopened"])
        rationale = st.text_area("Human review rationale", max_chars=5000)
        selected = st.multiselect("Passages you reviewed", passage_ids, format_func=str)
        confirmed = st.checkbox("I am recording my own review of this exact claim and revision.")
        submitted = st.form_submit_button("Record human decision")
    if submitted:
        if not confirmed:
            st.error("Confirm your own review before recording a human decision.")
        else:
            updated = workspace.editorial.decide(
                project_id,
                draft_id,
                draft.revision_id,
                claim_id,
                HumanReview.model_validate(
                    {
                        "reviewer": reviewer,
                        "action": action,
                        "rationale": rationale,
                        "reviewed_passages": selected,
                    }
                ),
                expected_version=st.session_state[version_key],
            )
            st.session_state[version_key] = updated.version
            st.session_state.notice = "Human editorial decision recorded for this revision."
            st.rerun()
    for pid in unit.human_evidence:
        with st.expander("Human-reviewed passage · " + str(pid)):
            st.text(workspace.sources.resolve_passage(project_id, pid).text)
    with st.expander("Human decision history"):
        for event in workspace.editorial.review_history(
            project_id, draft_id, draft.revision_id, claim_id
        ):
            st.text(event)
