"""Snapshot a selected revision and return bounded exports; never accept a file path."""

import json
from typing import Any
from uuid import UUID

from research2docs.core.errors import ExportError
from research2docs.exporting.models import ExportFile, ExportFormat
from research2docs.exporting.renderers import (
    MAX_EXPORT_BYTES,
    blocks,
    docx_document,
    html_document,
    json_manifest,
    markdown,
)
from research2docs.services.editorial_service import EditorialService


class ExportService:
    def __init__(self, editorial: EditorialService):
        self.editorial = editorial

    def manifest(
        self, project_id: str | UUID, draft_id: str | UUID, *, revision_id: str | UUID | None = None
    ) -> dict[str, Any]:
        generation = self.editorial.generation
        draft = generation.reopen(project_id, draft_id, revision_id=revision_id)
        ledger = self.editorial.verification.ledger(
            project_id, draft_id, revision_id=draft.revision_id
        )
        passage_ids = {e.passage.passage_id for e in draft.evidence}
        for unit in ledger.units:
            passage_ids.update(unit.human_evidence)
            passage_ids.update(
                q.passage_id for q in [*unit.supporting, *unit.contradictory, *unit.temporal]
            )
        sources = {
            s.source.source_id: s.source for s in generation.sources.list_sources(draft.project_id)
        }
        with self.editorial.repository.database.session() as c:
            rows = c.execute(
                "SELECT claim_id,version_data.payload_json FROM claim_units version_data WHERE project_id=? AND revision_id=?",
                (str(draft.project_id), str(draft.revision_id)),
            ).fetchall()
            saved = {row[0]: json.loads(row[1])["version"] for row in rows}
            if saved != {str(u.claim.claim_id): u.version for u in ledger.units}:
                raise ExportError(
                    "Review changed while preparing the export. Refresh and export again."
                )
            run = c.execute(
                "SELECT * FROM generation_runs WHERE project_id=? AND run_id=?",
                (str(draft.project_id), str(draft.run_id)),
            ).fetchone()
            if run is None:
                raise ExportError("Generation provenance is missing for this revision.")
            generation_run = dict(run)
            generation_run["parameters"] = json.loads(generation_run.pop("parameters_json"))
            counts = c.execute(
                "SELECT count(*),coalesce(sum(length(payload_json)),0) FROM assessment_runs WHERE project_id=? AND revision_id=?",
                (str(draft.project_id), str(draft.revision_id)),
            ).fetchone()
            reviews = c.execute(
                "SELECT count(*),coalesce(sum(length(h.payload_json)),0) FROM human_review_events h JOIN claims c "
                "ON h.project_id=c.project_id AND h.claim_id=c.claim_id WHERE c.project_id=? AND c.revision_id=?",
                (str(draft.project_id), str(draft.revision_id)),
            ).fetchone()
            if counts[0] + reviews[0] > 2000 or counts[1] + reviews[1] > 8 * 1024 * 1024:
                raise ExportError("Revision audit history exceeds the bounded export limit.")
            assessments = [
                {
                    "assessment_id": r[0],
                    "status": r[1],
                    "started_at": r[2],
                    "payload": json.loads(r[3]),
                }
                for r in c.execute(
                    "SELECT assessment_id,status,started_at,payload_json FROM assessment_runs WHERE project_id=? AND revision_id=? ORDER BY rowid",
                    (str(draft.project_id), str(draft.revision_id)),
                )
            ]
            decisions = [
                {"event_id": r[0], "action": r[1], "created_at": r[2], "payload": json.loads(r[3])}
                for r in c.execute(
                    "SELECT h.event_id,h.action,h.created_at,h.payload_json FROM human_review_events h JOIN claims c "
                    "ON h.project_id=c.project_id AND h.claim_id=c.claim_id WHERE c.project_id=? AND c.revision_id=? ORDER BY h.rowid",
                    (str(draft.project_id), str(draft.revision_id)),
                )
            ]
            events = [
                dict(row)
                for row in c.execute(
                    "SELECT * FROM revision_events WHERE project_id=? AND revision_id=?",
                    (str(draft.project_id), str(draft.revision_id)),
                )
            ]
        # Historical candidate passages and human-reviewed references remain auditable too.
        for run in assessments:
            for item in run["payload"].get("evidence", []):
                passage = generation.sources.resolve_passage(
                    draft.project_id, UUID(item["passage"]["passage_id"])
                )
                if passage.model_dump(mode="json") != item["passage"]:
                    raise ExportError(
                        "Historical assessment evidence no longer matches its source."
                    )
                passage_ids.add(passage.passage_id)
        for event in decisions:
            for pid in event["payload"]["review"]["reviewed_passages"]:
                passage_ids.add(UUID(pid))
        evidence = []
        for pid in sorted(passage_ids, key=str):
            passage = generation.sources.resolve_passage(draft.project_id, pid)
            evidence.append(
                {
                    "passage": passage.model_dump(mode="json"),
                    "source": sources[passage.source_id].model_dump(mode="json"),
                }
            )
        # Avoid pathological document rendering allocations even if the full JSON audit is within its bound.
        if sum(len(e["passage"]["text"]) for e in evidence) > 1000000:
            raise ExportError(
                "Revision evidence exceeds the one-million-character readable export bound."
            )
        manifest = {
            "manifest_version": "1.0",
            "export_status": "draft",
            "review_boundary": "Source support and human editorial judgments do not establish objective truth.",
            "draft": draft.model_dump(mode="json"),
            "ledger": ledger.model_dump(mode="json"),
            "evidence": evidence,
            "generation_run": generation_run,
            "assessment_history": assessments,
            "human_decisions": decisions,
            "revision_events": events,
        }
        if len(json_manifest(manifest)) > 16 * 1024 * 1024:
            raise ExportError("Evidence manifest exceeds the bounded export size.")
        return manifest

    def export(
        self,
        project_id: str | UUID,
        draft_id: str | UUID,
        format: ExportFormat,
        *,
        revision_id: str | UUID | None = None,
    ) -> ExportFile:
        if format not in {"markdown", "html", "docx", "json"}:
            raise ExportError("Choose a supported export format.")
        manifest = self.manifest(project_id, draft_id, revision_id=revision_id)
        draft = self.editorial.generation.reopen(
            project_id, draft_id, revision_id=manifest["draft"]["revision_id"]
        )
        parts = blocks(manifest)
        if format == "json":
            data = json_manifest(manifest)
            extension = "json"
            mime = "application/json"
        elif format == "markdown":
            data = markdown(parts)
            extension = "md"
            mime = "text/markdown"
        elif format == "html":
            data = html_document(parts)
            extension = "html"
            mime = "text/html"
        else:
            data = docx_document(parts, draft.created_at)
            extension = "docx"
            mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if len(data) > MAX_EXPORT_BYTES:
            raise ExportError("Export exceeded the configured output bound.")
        return ExportFile(
            revision_id=draft.revision_id,
            claim_versions={
                str(u["claim"]["claim_id"]): u["version"] for u in manifest["ledger"]["units"]
            },
            filename=f"research2docs-{draft.draft_id}-r{draft.revision_number}-{str(draft.revision_id)[:8]}.{extension}",
            mime_type=mime,
            data=data,
        )
