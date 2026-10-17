"""Append-only revisions and explicit human decisions with optimistic checks."""

from uuid import UUID, uuid4

from pydantic import ValidationError

from research2docs.core.errors import RevisionConflict, StorageError
from research2docs.core.models import AssessmentStatus, utc_now
from research2docs.editorial.models import HumanReview
from research2docs.generation.models import SavedDraft
from research2docs.storage.database import Database
from research2docs.storage.verification_repository import VerificationRepository
from research2docs.verification.models import ClaimUnit


class EditorialRepository:
    def __init__(self, database: Database):
        self.database = database

    def append(
        self,
        base: SavedDraft,
        revision: SavedDraft,
        editor: str,
        *,
        regeneration_run: UUID | None = None,
    ) -> SavedDraft:
        with self.database.session(write=True) as c:
            head = c.execute(
                "SELECT revision_id FROM draft_heads WHERE project_id=? AND draft_id=?",
                (str(base.project_id), str(base.draft_id)),
            ).fetchone()
            if head is None or head[0] != str(base.revision_id):
                raise RevisionConflict(
                    "Draft changed in another session. Reload the latest revision before saving."
                )
            current = c.execute(
                "SELECT content FROM revisions WHERE project_id=? AND revision_id=?",
                (str(base.project_id), str(base.revision_id)),
            ).fetchone()
            if current is None or current[0] != base.content.model_dump_json():
                raise RevisionConflict("The base revision changed. Reopen before saving.")
            c.execute(
                "INSERT INTO revisions VALUES (?,?,?,?,?,?)",
                (
                    str(revision.project_id),
                    str(revision.revision_id),
                    str(revision.draft_id),
                    revision.revision_number,
                    revision.content.model_dump_json(),
                    revision.created_at.isoformat(),
                ),
            )
            c.execute(
                "INSERT INTO generated_drafts VALUES (?,?,?)",
                (str(revision.project_id), str(revision.revision_id), revision.model_dump_json()),
            )
            c.execute(
                "INSERT INTO revision_events VALUES (?,?,?,?,?,?,?)",
                (
                    str(revision.project_id),
                    str(revision.revision_id),
                    str(base.revision_id),
                    editor,
                    revision.revision_note,
                    revision.origin,
                    revision.created_at.isoformat(),
                ),
            )
            VerificationRepository.initialize(c, revision)
            c.execute(
                "UPDATE draft_heads SET revision_id=? WHERE project_id=? AND draft_id=?",
                (str(revision.revision_id), str(base.project_id), str(base.draft_id)),
            )
            if regeneration_run is not None:
                count = c.execute(
                    "UPDATE generation_runs SET status='completed',revision_id=? WHERE project_id=? AND run_id=? AND status='started'",
                    (str(revision.revision_id), str(revision.project_id), str(regeneration_run)),
                ).rowcount
                if count != 1:
                    raise StorageError("Regeneration run changed. Revision was not saved.")
        return revision

    def decide(
        self, draft: SavedDraft, unit: ClaimUnit, review: HumanReview, expected_version: int
    ) -> ClaimUnit:
        event_id = uuid4()
        now = utc_now()
        baseline = unit.automated_assessment or unit.claim.assessment
        if baseline == AssessmentStatus.HUMAN_VERIFIED:
            baseline = AssessmentStatus.UNSUPPORTED
        status = AssessmentStatus.HUMAN_VERIFIED if review.action == "accepted" else baseline
        human = "pending" if review.action == "reopened" else review.action
        claim = unit.claim.model_copy(
            update={
                "assessment": status,
                "human_review": human,
                "human_rationale": "" if human == "pending" else review.rationale,
            }
        )
        flags = [flag for flag in unit.review_flags if flag != "Human review pending."]
        if review.action == "reopened":
            flags.append("Human review pending.")
        updated = ClaimUnit.model_validate_json(
            unit.model_copy(
                update={
                    "claim": claim,
                    "version": unit.version + 1,
                    "automated_assessment": baseline,
                    "review_flags": flags,
                    "human_evidence": review.reviewed_passages
                    if review.action == "accepted"
                    else [],
                }
            ).model_dump_json()
        )
        with self.database.session(write=True) as c:
            row = c.execute(
                "SELECT payload_json FROM claim_units WHERE project_id=? AND claim_id=?",
                (str(unit.claim.project_id), str(unit.claim.claim_id)),
            ).fetchone()
            revision = c.execute(
                "SELECT content FROM revisions WHERE project_id=? AND revision_id=?",
                (str(draft.project_id), str(draft.revision_id)),
            ).fetchone()
            if row is None or revision is None or revision[0] != draft.content.model_dump_json():
                raise RevisionConflict(
                    "Claim revision changed. Reload before recording a decision."
                )
            try:
                current = ClaimUnit.model_validate_json(row[0])
            except (ValueError, ValidationError):
                raise StorageError("Saved claim is invalid.") from None
            if current.version != expected_version or current.claim.text != unit.claim.text:
                raise RevisionConflict("This claim changed. Reload before recording a decision.")
            c.execute(
                "UPDATE claims SET assessment=?,assessment_json=? WHERE project_id=? AND claim_id=?",
                (status.value, claim.model_dump_json(), str(claim.project_id), str(claim.claim_id)),
            )
            c.execute(
                "UPDATE claim_units SET payload_json=? WHERE project_id=? AND claim_id=?",
                (updated.model_dump_json(), str(claim.project_id), str(claim.claim_id)),
            )
            import json

            payload = {
                "review": review.model_dump(mode="json"),
                "before": unit.model_dump(mode="json"),
                "after": updated.model_dump(mode="json"),
            }
            c.execute(
                "INSERT INTO human_review_events VALUES (?,?,?,?,?,?)",
                (
                    str(claim.project_id),
                    str(event_id),
                    str(claim.claim_id),
                    review.action,
                    json.dumps(payload),
                    now.isoformat(),
                ),
            )
            if review.action != "reopened":
                c.execute(
                    "INSERT INTO editorial_decisions VALUES (?,?,?,?,?,?,?)",
                    (
                        str(claim.project_id),
                        str(event_id),
                        str(claim.claim_id),
                        review.reviewer,
                        review.action,
                        review.rationale,
                        now.isoformat(),
                    ),
                )
        return updated
