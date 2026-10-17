# Phase 5 editorial workflow

`WorkspaceService.editorial` provides ordinary Python APIs for revision history, explicit human decisions, manual editing and local single-section regeneration. The UI is a presentation layer; exports remain Phase 6.

## Revisions

`history(project_id, draft_id)` lists revisions newest first. `generation.reopen(..., revision_id=...)` and `verification.ledger(..., revision_id=...)` resolve a particular historical revision; omitting the revision selects the latest saved one. Document Studio and Evidence Review have revision selectors.

`save(project, draft, base_revision, RevisionEdit)` requires a nonblank editor name, revision reason, title and valid structured document. All citation aliases must resolve to the saved exact evidence. It appends a new revision and ledger atomically, advances the draft head and retains the previous revision unchanged. No-op saves are rejected. The base must still be the latest revision; stale forms cannot overwrite accepted work. Document Studio edits one section's heading/blocks/citations/review notes and document title at a time; the service accepts a complete validated structured document.

Every new revision resets **all** claim units to not-assessed/pending, including unchanged blocks. This conservative policy avoids carrying decisions across context changes. Application-derived claim IDs include the new revision ID, so prior assessments/human decisions remain attached to historical claims. Previous warnings are retained; generation-time length/method warnings describe the original run, not a fresh measurement of every edited revision. No claim-merging or automatic semantic equivalence is assumed.

## Human review

`decide(..., revision_id, claim_id, HumanReview, expected_version=...)` records an explicit accepted, rejected or reopened decision. All actions require a reviewer name and substantive nonblank rationale. Acceptance additionally requires one or more real project-scoped passage IDs selected by the reviewer. The UI requires confirmation that the user is recording their own review of the exact claim/revision and offers full passage inspection, including additional project sources.

Accepted decisions mark that claim Human verified with accepted human status and rationale. This is an editor's recorded judgment of source support, not independent external verification, authenticated reviewer identity or objective truth. The automated status, model/excerpts and earlier warnings remain preserved separately in current/history data. Human-reviewed passage references are distinguished from automated supporting excerpts. Rejecting preserves the automated category but marks human review rejected. Reopening returns review to pending and restores the automated category, clearing the current accepted passage selection while retaining it in immutable history.

The displayed claim version must match at publication. Human decisions and AI assessment share the version counter, preventing a competing model response or stale form from replacing a newer decision. AI assessment cannot overwrite an accepted/rejected review; explicitly reopen first. A human action does not edit the draft prose. Decisions on historical revisions remain historical and do not approve the latest revision. No model response has access to the human-decision service as a tool.

Human decisions are self-reported local records. The application does not establish the identity, expertise or actual diligence of the named reviewer. Controlled test fixture decisions are not real human approvals; demonstrations must not invent an acceptance on the user's behalf.

## Section regeneration

`regenerate(..., base_revision, section_index, editor=..., note=..., instructions=...)` invokes the selected installed local Ollama model for **one** section. It requires a current base revision, editor and reason. A fixed `section-regeneration:1.0` policy separates system rules from JSON containing the existing section, editorial preferences and exact source passages. Model output must match a one-section schema, retain the requested section kind and cite only evidence supplied to that run. No command or document instruction is executed.

Existing evidence aliases retain their mapping; newly retrieved passages receive fresh aliases. Up to eight additional FTS candidates are considered, with a total candidate cap of 40; whole passages are packed inside the existing generation budgets. Omission is warned. Existing text may itself exceed the prompt budget, in which case regeneration fails safely before inference. The existing 600-second deadline, response cap, context/model validation and no-tools/no-redirect/no-cloud/no-pull policies apply.

Only the selected section is replaced; other sections and document limitations are copied unchanged. A successful response atomically appends a revision, fresh claim ledger, editorial event and completed generation run. Invalid JSON/citations/kind, model failure, source mismatch or a concurrent edit preserves the current draft and records a failed run. No automatic repair/retry occurs. Reassessment and fresh human review are required for the new revision.

## Storage and limits

Schema 5 adds `draft_heads`, backfilled from each draft's latest existing revision; `revision_events`, recording parent/editor/reason/origin/time; and `human_review_events`, recording action and before/after snapshots plus reviewed references. Accepted/rejected actions also append the existing `editorial_decisions` table. Initial generation writes its head with the initial revision. Draft lists show one current entry per draft, while history preserves all revisions and previous generation/assessment runs.

Local storage is unencrypted and excluded from Git. There is no reviewer authentication, multi-user authorization, automatic conflict merge, section diff view, undo deletion, source replacement/deletion or export in Phase 5. Historical content is immutable through these services; review records append but can change the current claim status through explicit later decisions. Same-user database tampering is outside this integrity guarantee. A timed-out model may continue server-side computation. Revision/decision history can grow with use; no automatic retention/deletion is performed.
