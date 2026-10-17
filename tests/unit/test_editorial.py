"""Phase 5 fixtures record fictional test decisions, never real human approvals."""

import json
from uuid import uuid4

import pytest
from pydantic import ValidationError
from test_verification import assess, first
from test_verification import review_fixture as _shared_review_fixture

from research2docs.core.errors import (
    GenerationError,
    InputError,
    Research2DocsError,
    RevisionConflict,
    StorageError,
)
from research2docs.core.models import AssessmentStatus, ProjectInput
from research2docs.editorial.models import HumanReview, RevisionEdit
from research2docs.services.workspace_service import WorkspaceService


@pytest.fixture(name="review_fixture")
def editorial_fixture(tmp_path, monkeypatch):
    return _shared_review_fixture.__wrapped__(tmp_path, monkeypatch)


def edited(draft, text="Edited fictional MFA statement."):
    content = draft.content.model_copy(deep=True)
    content.sections[0].blocks[0].text = text
    return RevisionEdit(
        title=draft.title,
        content=content,
        editor="Fictional Test Editor",
        note="Controlled test revision.",
    )


def human(unit, action="accepted"):
    return HumanReview(
        reviewer="Fictional Test Reviewer",
        action=action,
        rationale="Controlled test review rationale.",
        reviewed_passages=unit.cited_passages[:1] if action == "accepted" else [],
    )


def decide(w, p, d, unit, action="accepted"):
    return w.editorial.decide(
        p.project_id,
        d.draft_id,
        d.revision_id,
        unit.claim.claim_id,
        human(unit, action),
        expected_version=unit.version,
    )


def test_revision_history_preserves_old_content_claims_and_decisions(review_fixture):
    w, p, d, _ = review_fixture
    assessed = assess(w, p, d)
    accepted = decide(w, p, d, assessed)
    revision = w.editorial.save(p.project_id, d.draft_id, d.revision_id, edited(d))
    assert revision.draft_id == d.draft_id and revision.revision_number == 2
    assert revision.parent_revision_id == d.revision_id and revision.origin == "manual"
    assert w.generation.reopen(p.project_id, d.draft_id) == revision
    assert w.generation.reopen(p.project_id, d.draft_id, revision_id=d.revision_id) == d
    assert len(w.generation.list_drafts(p.project_id)) == 1
    assert [r.revision_number for r in w.editorial.history(p.project_id, d.draft_id)] == [2, 1]
    old = w.verification.ledger(p.project_id, d.draft_id, revision_id=d.revision_id)
    current = w.verification.ledger(p.project_id, d.draft_id)
    assert (
        old.units[0] == accepted
        and old.units[0].claim.assessment == AssessmentStatus.HUMAN_VERIFIED
    )
    assert all(
        u.claim.human_review == "pending" and u.state == "not_assessed" for u in current.units
    )
    assert not {u.claim.claim_id for u in old.units} & {u.claim.claim_id for u in current.units}
    assert all(not u.supporting and not u.human_evidence for u in current.units)
    assert w.summary().drafts == 1


def test_accept_reject_reopen_preserve_human_and_automated_history(review_fixture):
    w, p, d, _ = review_fixture
    before = assess(w, p, d)
    accepted = decide(w, p, d, before)
    assert (
        accepted.claim.human_review == "accepted"
        and accepted.claim.assessment == AssessmentStatus.HUMAN_VERIFIED
    )
    assert accepted.automated_assessment == before.claim.assessment
    assert accepted.human_evidence and "Human review pending." not in accepted.review_flags
    with pytest.raises(RevisionConflict):
        w.verification.assess(
            p.project_id, d.draft_id, accepted.claim.claim_id, expected_version=accepted.version
        )
    rejected = decide(w, p, d, accepted, "rejected")
    assert (
        rejected.claim.assessment == before.claim.assessment
        and rejected.claim.human_review == "rejected"
    )
    reopened = decide(w, p, d, rejected, "reopened")
    assert reopened.claim.human_review == "pending" and reopened.claim.human_rationale == ""
    assert reopened.version == before.version + 3 and not reopened.human_evidence
    assert "Human review pending." in reopened.review_flags
    after = assess(w, p, d, reopened)
    assert after.claim.human_review == "pending"
    history = w.editorial.review_history(
        p.project_id, d.draft_id, d.revision_id, before.claim.claim_id
    )
    assert len(history) == 3 and all("Fictional Test Reviewer" in h for h in history)
    with w.database.session() as c:
        assert c.execute("SELECT count(*) FROM editorial_decisions").fetchone()[0] == 2
        assert c.execute("SELECT count(*) FROM human_review_events").fetchone()[0] == 3


@pytest.mark.parametrize(
    "data",
    [
        {
            "reviewer": "",
            "rationale": "Reason",
            "action": "accepted",
            "reviewed_passages": [uuid4()],
        },
        {"reviewer": "Name", "rationale": "  ", "action": "rejected"},
        {"reviewer": "Name", "rationale": "Reason", "action": "accepted"},
    ],
)
def test_human_decision_requires_explicit_identity_rationale_and_evidence(data):
    with pytest.raises(ValidationError):
        HumanReview(**data)


def test_stale_revision_and_human_forms_never_overwrite(review_fixture):
    w, p, d, _ = review_fixture
    unit = first(w, p, d)
    decide(w, p, d, unit)
    with pytest.raises(RevisionConflict):
        decide(w, p, d, unit, "rejected")
    revision = w.editorial.save(p.project_id, d.draft_id, d.revision_id, edited(d))
    with pytest.raises(RevisionConflict):
        w.editorial.save(p.project_id, d.draft_id, d.revision_id, edited(d, "Stale overwrite."))
    assert w.generation.reopen(p.project_id, d.draft_id) == revision


def test_citation_project_and_revision_scope_are_enforced(review_fixture):
    w, p, d, _ = review_fixture
    invalid = edited(d)
    invalid.content.sections[0].blocks[0].citations = ["E999"]
    with pytest.raises(GenerationError):
        w.editorial.save(p.project_id, d.draft_id, d.revision_id, invalid)
    other = w.projects.create(ProjectInput(title="Other"))
    source = w.sources.import_document(other.project_id, b"Other evidence.", "other.txt")
    pid = w.sources.source_passages(other.project_id, source.source_id)[0].passage_id
    unit = first(w, p, d)
    with pytest.raises(Research2DocsError) as error:
        w.editorial.decide(
            p.project_id,
            d.draft_id,
            d.revision_id,
            unit.claim.claim_id,
            HumanReview(
                reviewer="Test", action="accepted", rationale="Test only.", reviewed_passages=[pid]
            ),
            expected_version=0,
        )
    assert not isinstance(error.value, AssertionError)
    assert first(w, p, d).claim.human_review == "pending"
    with pytest.raises(GenerationError):
        w.editorial.history(other.project_id, d.draft_id)


def test_revision_transaction_failure_preserves_head_and_history(review_fixture):
    w, p, d, _ = review_fixture
    with w.database.session(write=True) as c:
        c.execute(
            "CREATE TRIGGER reject_revision BEFORE INSERT ON claim_units BEGIN SELECT RAISE(ABORT,'fixture'); END"
        )
    with pytest.raises(StorageError):
        w.editorial.save(p.project_id, d.draft_id, d.revision_id, edited(d))
    assert w.generation.reopen(p.project_id, d.draft_id) == d
    assert len(w.editorial.history(p.project_id, d.draft_id)) == 1


def test_human_event_failure_rolls_back_claim_and_decision(review_fixture):
    w, p, d, _ = review_fixture
    unit = first(w, p, d)
    with w.database.session(write=True) as c:
        c.execute(
            "CREATE TRIGGER reject_review BEFORE INSERT ON human_review_events BEGIN SELECT RAISE(ABORT,'fixture'); END"
        )
    with pytest.raises(StorageError):
        decide(w, p, d, unit)
    assert first(w, p, d) == unit
    with w.database.session() as c:
        assert c.execute("SELECT count(*) FROM editorial_decisions").fetchone()[0] == 0


def regeneration_mock(w, monkeypatch, *, invalid=False):
    calls = []

    def generate(name, messages, schema, **kwargs):
        calls.append((messages, schema))
        payload = json.loads(messages[1]["content"])
        return json.dumps(
            {
                "kind": "wrong" if invalid else payload["section_kind"],
                "heading": "Regenerated heading",
                "blocks": [
                    {
                        "text": "Regenerated fictional MFA explanation.",
                        "citations": [payload["evidence"][0]["alias"]],
                        "review_note": "Requires fresh review.",
                    }
                ],
            }
        )

    monkeypatch.setattr(w.ollama, "generate", generate)
    return calls


def test_regeneration_changes_only_requested_section_and_preserves_aliases(
    review_fixture, monkeypatch
):
    w, p, d, _ = review_fixture
    calls = regeneration_mock(w, monkeypatch)
    revision = w.editorial.regenerate(
        p.project_id,
        d.draft_id,
        d.revision_id,
        1,
        editor="Fictional Test Editor",
        note="Controlled regeneration.",
    )
    assert revision.origin == "section_regeneration" and revision.revision_number == 2
    assert revision.content.sections[0] == d.content.sections[0]
    assert revision.content.sections[2:] == d.content.sections[2:]
    assert revision.content.sections[1] != d.content.sections[1]
    assert revision.evidence[: len(d.evidence)] == d.evidence
    assert revision.content.limitations == d.content.limitations
    assert revision.run_id != d.run_id and revision.prompt_version == "section-regeneration:1.0"
    assert len(calls) == 1 and "UNTRUSTED DATA" in calls[0][0][0]["content"]
    assert all(
        u.state == "not_assessed" for u in w.verification.ledger(p.project_id, d.draft_id).units
    )
    with w.database.session() as c:
        assert (
            c.execute(
                "SELECT status FROM generation_runs WHERE run_id=?", (str(revision.run_id),)
            ).fetchone()[0]
            == "completed"
        )


def test_invalid_regeneration_preserves_latest_revision_and_marks_run_failed(
    review_fixture, monkeypatch
):
    w, p, d, _ = review_fixture
    regeneration_mock(w, monkeypatch, invalid=True)
    with pytest.raises(GenerationError):
        w.editorial.regenerate(
            p.project_id, d.draft_id, d.revision_id, 0, editor="Test", note="Controlled test"
        )
    assert w.generation.reopen(p.project_id, d.draft_id) == d
    with w.database.session() as c:
        assert (
            c.execute("SELECT status FROM generation_runs ORDER BY rowid DESC LIMIT 1").fetchone()[
                0
            ]
            == "failed"
        )


def test_noop_edit_does_not_create_revision(review_fixture):
    w, p, d, _ = review_fixture
    with pytest.raises(InputError):
        w.editorial.save(
            p.project_id,
            d.draft_id,
            d.revision_id,
            RevisionEdit(title=d.title, content=d.content, editor="Test", note="No change test."),
        )


def test_history_and_decisions_reopen_in_new_workspace(review_fixture):
    w, p, d, _ = review_fixture
    unit = decide(w, p, d, first(w, p, d))
    revision = w.editorial.save(p.project_id, d.draft_id, d.revision_id, edited(d))
    reopened = WorkspaceService(w.settings)
    assert reopened.generation.reopen(p.project_id, d.draft_id) == revision
    assert (
        reopened.verification.ledger(p.project_id, d.draft_id, revision_id=d.revision_id).units[0]
        == unit
    )
    assert (
        len(
            reopened.editorial.review_history(
                p.project_id, d.draft_id, d.revision_id, unit.claim.claim_id
            )
        )
        == 1
    )


def test_ui_revision_save_and_historical_selection(review_fixture, monkeypatch):
    from pathlib import Path

    from streamlit.testing.v1 import AppTest

    w, p, d, _ = review_fixture
    monkeypatch.setenv("RESEARCH2DOCS_DATA_DIR", w.settings.data_dir)
    app = str(Path(__file__).resolve().parents[2] / "ui/app.py")
    at = AppTest.from_file(app, default_timeout=30).run()
    at.radio[0].set_value("Document Studio").run()
    next(v for v in at.text_input if v.label == "Editor name").set_value("Fictional Test Editor")
    next(v for v in at.text_area if v.label == "Revision note / reason").set_value(
        "Controlled UI test change."
    )
    next(v for v in at.text_area if v.label == "Block 1 text").set_value(
        "UI edited fictional explanation."
    )
    next(b for b in at.button if b.label == "Save as new revision").click().run()
    assert not at.exception and not at.error
    latest = w.generation.reopen(p.project_id, d.draft_id)
    assert (
        latest.revision_number == 2
        and latest.content.sections[0].blocks[0].text == "UI edited fictional explanation."
    )
    next(v for v in at.selectbox if v.label == "Saved revision").set_value(str(d.revision_id)).run()
    assert not at.exception and any("Historical revision selected" in v.value for v in at.info)
    assert w.generation.reopen(p.project_id, d.draft_id, revision_id=d.revision_id) == d


def test_ui_human_review_requires_own_confirmation_and_reopens(review_fixture, monkeypatch):
    from pathlib import Path

    from streamlit.testing.v1 import AppTest

    w, p, d, _ = review_fixture
    monkeypatch.setenv("RESEARCH2DOCS_DATA_DIR", w.settings.data_dir)
    at = AppTest.from_file(
        str(Path(__file__).resolve().parents[2] / "ui/app.py"), default_timeout=30
    ).run()
    at.radio[0].set_value("Evidence Review").run()
    next(b for b in at.button if b.label == "Record human decision").click().run()
    assert not at.exception and any("Confirm your own review" in v.value for v in at.error)
    next(v for v in at.text_input if v.label == "Reviewer name").set_value("Fictional UI Reviewer")
    next(v for v in at.text_area if v.label == "Human review rationale").set_value(
        "Controlled fixture review only."
    )
    pid = first(w, p, d).cited_passages[0]
    next(v for v in at.multiselect if v.label == "Passages you reviewed").set_value([pid])
    at.checkbox[0].check()
    next(b for b in at.button if b.label == "Record human decision").click().run()
    assert not at.exception and not at.error
    assert first(w, p, d).claim.assessment == AssessmentStatus.HUMAN_VERIFIED
    assert any(v.value == "Human review: accepted" for v in at.text)
    assert any("Fictional UI Reviewer" in v.value for v in at.text)


def test_concurrent_regeneration_cannot_replace_newer_edit(review_fixture, monkeypatch):
    w, p, d, _ = review_fixture
    regeneration_mock(w, monkeypatch)
    original = w.ollama.generate

    def competing(*args, **kwargs):
        w.editorial.save(
            p.project_id, d.draft_id, d.revision_id, edited(d, "Concurrent accepted edit.")
        )
        return original(*args, **kwargs)

    monkeypatch.setattr(w.ollama, "generate", competing)
    with pytest.raises(RevisionConflict):
        w.editorial.regenerate(
            p.project_id, d.draft_id, d.revision_id, 0, editor="Test", note="Controlled conflict."
        )
    assert (
        w.generation.reopen(p.project_id, d.draft_id).content.sections[0].blocks[0].text
        == "Concurrent accepted edit."
    )
    with w.database.session() as c:
        assert (
            c.execute("SELECT status FROM generation_runs ORDER BY rowid DESC LIMIT 1").fetchone()[
                0
            ]
            == "failed"
        )


def test_schema5_upgrade_and_failure_preserve_old_revisions(review_fixture, monkeypatch):
    from research2docs.storage import database

    w, p, d, _ = review_fixture
    with w.database.session(write=True) as c:
        for table in ["human_review_events", "revision_events", "draft_heads"]:
            c.execute(f"DROP TABLE {table}")
        c.execute("DELETE FROM schema_migrations WHERE version=5")
        c.execute("PRAGMA user_version=4")
    actual = database.MIGRATION_5
    monkeypatch.setattr(database, "MIGRATION_5", (*actual, "CREATE TABLE projects(bad TEXT)"))
    with pytest.raises(StorageError):
        database.Database(w.database.root)
    with w.database.session() as c:
        assert c.execute("PRAGMA user_version").fetchone()[0] == 4
        assert not c.execute("SELECT name FROM sqlite_master WHERE name='draft_heads'").fetchone()
    monkeypatch.setattr(database, "MIGRATION_5", actual)
    reopened = WorkspaceService(w.settings)
    assert reopened.generation.reopen(p.project_id, d.draft_id) == d
    assert (
        reopened.verification.ledger(p.project_id, d.draft_id).units
        == w.verification.ledger(p.project_id, d.draft_id).units
    )


def test_fresh_process_reopens_revision_and_human_history(review_fixture):
    import subprocess
    import sys

    w, p, d, _ = review_fixture
    decide(w, p, d, first(w, p, d))
    revision = w.editorial.save(p.project_id, d.draft_id, d.revision_id, edited(d))
    code = """
import sys,socket,builtins
original=builtins.__import__
def no_ui(name,*a,**k):
 if name.split('.')[0]=='streamlit': raise AssertionError('UI')
 return original(name,*a,**k)
builtins.__import__=no_ui
socket.socket.connect=lambda *a,**k: (_ for _ in ()).throw(AssertionError('Network'))
from research2docs.core.config import Settings
from research2docs.services.workspace_service import WorkspaceService
w=WorkspaceService(Settings(data_dir=sys.argv[1]))
assert w.generation.reopen(sys.argv[2],sys.argv[3]).revision_number==2
old=w.verification.ledger(sys.argv[2],sys.argv[3],revision_id=sys.argv[4]).units[0]
assert old.claim.human_review=='accepted' and old.human_evidence
assert w.editorial.review_history(sys.argv[2],sys.argv[3],sys.argv[4],old.claim.claim_id)
print('reopened')
"""
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            code,
            w.settings.data_dir,
            str(p.project_id),
            str(revision.draft_id),
            str(d.revision_id),
        ],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "reopened"


def test_regeneration_aliases_remain_unique_after_budget_omissions(review_fixture, monkeypatch):
    w, p, d, _ = review_fixture
    w.sources.import_document(
        p.project_id, ("BIGLABEL " + "FleetDemo MFA " * 300).encode(), "large.txt"
    )
    w.sources.import_document(
        p.project_id, b"SMALLLABEL FleetDemo MFA fictional note.", "small.txt"
    )
    big = w.sources.search(p.project_id, "BIGLABEL")[0]
    small = w.sources.search(p.project_id, "SMALLLABEL")[0]
    regeneration_mock(w, monkeypatch)
    monkeypatch.setattr(w.sources, "search", lambda *a, **k: [big, small])
    w.generation.limits.max_prompt_bytes = 4000
    one = w.editorial.regenerate(
        p.project_id, d.draft_id, d.revision_id, 0, editor="Test", note="Controlled omission."
    )
    assert "E4" in [e.alias for e in one.evidence] and "E3" not in [e.alias for e in one.evidence]
    w.sources.import_document(p.project_id, b"NEXTLABEL FleetDemo MFA next note.", "next.txt")
    # Resolve the new passage directly because retrieval is deliberately controlled in this test.
    source = next(
        s.source for s in w.sources.list_sources(p.project_id) if s.source.filename == "next.txt"
    )
    from research2docs.ingestion.models import SearchHit

    hit = SearchHit(
        rank=1,
        score=0.0,
        source=source,
        passage=w.sources.source_passages(p.project_id, source.source_id)[0],
    )
    monkeypatch.setattr(w.sources, "search", lambda *a, **k: [hit])
    two = w.editorial.regenerate(
        p.project_id,
        d.draft_id,
        one.revision_id,
        0,
        editor="Test",
        note="Controlled next regeneration.",
    )
    aliases = [e.alias for e in two.evidence]
    assert len(aliases) == len(set(aliases)) and "E5" in aliases
