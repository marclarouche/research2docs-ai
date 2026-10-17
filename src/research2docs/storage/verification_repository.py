"""Revision-bound ledgers and transactional, optimistic assessment publication."""

import json
import sqlite3
from uuid import UUID

from pydantic import ValidationError

from research2docs.core.errors import RevisionConflict, StorageError, VerificationError
from research2docs.core.models import utc_now
from research2docs.generation.models import SavedDraft
from research2docs.storage.database import Database
from research2docs.verification.extraction import content_hash, extract_ledger
from research2docs.verification.models import ClaimUnit, Ledger


class VerificationRepository:
    def __init__(self, database: Database):
        self.database = database

    @staticmethod
    def initialize(connection: sqlite3.Connection, draft: SavedDraft) -> None:
        row = connection.execute(
            "SELECT payload_json FROM verification_ledgers WHERE project_id=? AND revision_id=?",
            (str(draft.project_id), str(draft.revision_id)),
        ).fetchone()
        if row is not None:
            try:
                ledger = Ledger.model_validate_json(row[0])
            except (ValueError, ValidationError):
                raise StorageError("Saved claim ledger is invalid.") from None
            if ledger.content_sha256 != content_hash(draft):
                raise VerificationError(
                    "Draft content changed. A new revision and assessment are required."
                )
            return
        ledger = extract_ledger(draft)
        units = ledger.units
        header = ledger.model_copy(update={"units": []})
        connection.execute(
            "INSERT INTO verification_ledgers VALUES (?,?,?)",
            (str(draft.project_id), str(draft.revision_id), header.model_dump_json()),
        )
        for unit in units:
            claim = unit.claim
            connection.execute(
                "INSERT INTO claims VALUES (?,?,?,?,?,?)",
                (
                    str(claim.project_id),
                    str(claim.claim_id),
                    str(claim.revision_id),
                    claim.text,
                    claim.assessment.value,
                    claim.model_dump_json(),
                ),
            )
            connection.execute(
                "INSERT INTO claim_units VALUES (?,?,?,?,?,?)",
                (
                    str(claim.project_id),
                    str(claim.claim_id),
                    str(claim.revision_id),
                    unit.section_index,
                    unit.block_index,
                    unit.model_dump_json(),
                ),
            )

    def ensure(self, draft: SavedDraft) -> Ledger:
        with self.database.session(write=True) as connection:
            self.initialize(connection, draft)
        return self.get(draft)

    def get(self, draft: SavedDraft) -> Ledger:
        with self.database.session() as connection:
            row = connection.execute(
                "SELECT payload_json FROM verification_ledgers WHERE project_id=? AND revision_id=?",
                (str(draft.project_id), str(draft.revision_id)),
            ).fetchone()
            rows = connection.execute(
                "SELECT u.payload_json, c.assessment_json FROM claim_units u JOIN claims c "
                "ON u.project_id=c.project_id AND u.claim_id=c.claim_id WHERE u.project_id=? AND u.revision_id=? "
                "ORDER BY u.section_index,u.block_index",
                (str(draft.project_id), str(draft.revision_id)),
            ).fetchall()
        if row is None:
            raise VerificationError("Initialize the claim ledger for this draft first.")
        try:
            ledger = Ledger.model_validate_json(row[0])
            units = [ClaimUnit.model_validate_json(item[0]) for item in rows]
            if any(
                json.loads(item[1]) != unit.claim.model_dump(mode="json")
                for item, unit in zip(rows, units, strict=True)
            ):
                raise ValueError
            ledger.units = units
        except (ValueError, ValidationError):
            raise StorageError("Saved claim ledger data is inconsistent.") from None
        expected = extract_ledger(draft)
        if (
            ledger.content_sha256 != expected.content_sha256
            or ledger.project_id != draft.project_id
            or ledger.revision_id != draft.revision_id
            or ledger.draft_id != draft.draft_id
            or len(units) != len(expected.units)
        ):
            raise VerificationError(
                "Draft content changed. A new revision and assessment are required."
            )
        for unit, original in zip(units, expected.units, strict=True):
            if (
                unit.claim.claim_id != original.claim.claim_id
                or unit.claim.text != original.claim.text
                or unit.claim.revision_id != draft.revision_id
                or unit.claim.project_id != draft.project_id
                or unit.text_sha256 != original.text_sha256
                or unit.cited_passages != original.cited_passages
                or unit.section_index != original.section_index
                or unit.block_index != original.block_index
            ):
                raise VerificationError(
                    "Claim text or evidence changed. Reassessment in a new revision is required."
                )
        return ledger

    def start(
        self,
        project_id: UUID,
        revision_id: UUID,
        claim_id: UUID,
        assessment_id: UUID,
        payload: dict[str, object],
    ) -> None:
        with self.database.session(write=True) as connection:
            connection.execute(
                "INSERT INTO assessment_runs VALUES (?,?,?,?,?,?,?)",
                (
                    str(project_id),
                    str(assessment_id),
                    str(revision_id),
                    str(claim_id),
                    "started",
                    utc_now().isoformat(),
                    json.dumps(payload),
                ),
            )

    def fail(self, project_id: UUID, assessment_id: UUID) -> None:
        with self.database.session(write=True) as connection:
            connection.execute(
                "UPDATE assessment_runs SET status='failed' WHERE project_id=? AND assessment_id=? AND status='started'",
                (str(project_id), str(assessment_id)),
            )

    def publish(self, draft: SavedDraft, unit: ClaimUnit, expected_version: int) -> ClaimUnit:
        claim = unit.claim
        with self.database.session(write=True) as connection:
            row = connection.execute(
                "SELECT payload_json FROM claim_units WHERE project_id=? AND claim_id=?",
                (str(claim.project_id), str(claim.claim_id)),
            ).fetchone()
            revision = connection.execute(
                "SELECT content FROM revisions WHERE project_id=? AND revision_id=?",
                (str(draft.project_id), str(draft.revision_id)),
            ).fetchone()
            if row is None or revision is None or revision[0] != draft.content.model_dump_json():
                raise RevisionConflict("Draft revision changed. Reopen before assessment.")
            current = ClaimUnit.model_validate_json(row[0])
            if current.version != expected_version or current.text_sha256 != unit.text_sha256:
                raise RevisionConflict(
                    "This claim changed in another session. Reopen before assessing."
                )
            connection.execute(
                "UPDATE claims SET assessment=?, assessment_json=? WHERE project_id=? AND claim_id=?",
                (
                    claim.assessment.value,
                    claim.model_dump_json(),
                    str(claim.project_id),
                    str(claim.claim_id),
                ),
            )
            connection.execute(
                "UPDATE claim_units SET payload_json=? WHERE project_id=? AND claim_id=?",
                (unit.model_dump_json(), str(claim.project_id), str(claim.claim_id)),
            )
            connection.execute(
                "DELETE FROM evidence_links WHERE project_id=? AND claim_id=?",
                (str(claim.project_id), str(claim.claim_id)),
            )
            for relation, quotes in [
                ("supporting", unit.supporting),
                ("contradictory", unit.contradictory),
            ]:
                for passage_id in {quote.passage_id for quote in quotes}:
                    connection.execute(
                        "INSERT INTO evidence_links VALUES (?,?,?,?)",
                        (str(claim.project_id), str(claim.claim_id), str(passage_id), relation),
                    )
            run = connection.execute(
                "SELECT payload_json FROM assessment_runs WHERE project_id=? AND assessment_id=?",
                (str(claim.project_id), str(unit.assessment_id)),
            ).fetchone()
            payload = json.loads(run[0]) if run is not None else {}
            payload["result"] = unit.model_dump(mode="json")
            changed = connection.execute(
                "UPDATE assessment_runs SET status='completed',payload_json=? "
                "WHERE project_id=? AND assessment_id=? AND status='started'",
                (json.dumps(payload), str(claim.project_id), str(unit.assessment_id)),
            ).rowcount
            if changed != 1:
                raise StorageError("Assessment run changed. Result was not saved.")
        return unit
