"""Deterministic, exhaustive prose-block review units; no model-created claim text."""

import hashlib
from typing import Literal
from uuid import uuid5

from research2docs.core.errors import VerificationError
from research2docs.core.models import Claim, utc_now
from research2docs.generation.models import SavedDraft
from research2docs.verification.models import ClaimUnit, Ledger

EXTRACTION_VERSION = "prose-blocks:1.0"


def content_hash(draft: SavedDraft) -> str:
    return hashlib.sha256(draft.content.model_dump_json().encode()).hexdigest()


def extract_ledger(draft: SavedDraft) -> Ledger:
    aliases = {e.alias: e.passage for e in draft.evidence}
    if len(aliases) != len(draft.evidence) or any(
        e.passage.project_id != draft.project_id for e in draft.evidence
    ):
        raise VerificationError("Saved draft evidence mapping is invalid.")
    units = []
    now = utc_now()
    for section_index, section in enumerate(draft.content.sections):
        for block_index, block in enumerate(section.blocks):
            if not block.text.strip():
                raise VerificationError("Saved draft has an empty content block. Review its data.")
            if len(set(block.citations)) != len(block.citations) or any(
                alias not in aliases for alias in block.citations
            ):
                raise VerificationError(
                    "A draft citation does not resolve to its supplied evidence."
                )
            digest = hashlib.sha256(block.text.encode()).hexdigest()
            claim_id = uuid5(
                draft.revision_id, f"{EXTRACTION_VERSION}:{section_index}:{block_index}:{digest}"
            )
            state: Literal["valid", "missing"] = "valid" if block.citations else "missing"
            units.append(
                ClaimUnit(
                    claim=Claim(
                        claim_id=claim_id,
                        revision_id=draft.revision_id,
                        project_id=draft.project_id,
                        text=block.text,
                        explanation="Citation references exist; semantic support has not been assessed."
                        if block.citations
                        else "No original citation was supplied. Human review is required.",
                        assessment_method="deterministic-citations:1.0",
                        assessed_at=now,
                    ),
                    draft_id=draft.draft_id,
                    section_index=section_index,
                    block_index=block_index,
                    text_sha256=digest,
                    cited_passages=[aliases[a].passage_id for a in block.citations],
                    citation_state=state,
                    version=0,
                    state="not_assessed",
                    review_flags=["Human review pending."]
                    + ([] if block.citations else ["Original draft block has no citation."]),
                )
            )
    return Ledger(
        project_id=draft.project_id,
        draft_id=draft.draft_id,
        revision_id=draft.revision_id,
        content_sha256=content_hash(draft),
        created_at=now,
        units=units,
    )
