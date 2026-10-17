# Data model — schema 5

The database is `research2docs.sqlite3` beneath the operator-selected data directory. `PRAGMA foreign_keys=ON` applies to every connection. `PRAGMA user_version` and a SHA-256-checked `schema_migrations` row identify the schema. Fresh creation is atomic. Reopen never clears, migrates backwards or rebuilds unknown existing data. Future schema changes require a new version and migration, not edits to an already-used migration.

| Table | Key / relationship | Current use |
|---|---|---|
| schema_migrations | version, SQL checksum, applied_at | Checked on initialization |
| projects | UUID project_id, title, description, goals_json, version, created_at, updated_at | Create/list/read/edit |
| app_preferences | selected_model key and string value | Validated local selection |
| source_documents | (project_id, source_id), project FK; unique per-project SHA-256 | Phase 2 import/search |
| source_passages | (project_id, passage_id), source composite FK; unique source ordinal | Phase 2 import/search |
| drafts | (project_id, draft_id), project FK, title/goals/time | Phase 3 initial drafts / runs |
| revisions | (project_id, revision_id), draft composite FK; unique draft number | Phase 3 initial revision; editing in Phase 5 |
| claims | (project_id, claim_id), revision composite FK, text/status/assessment metadata | Phase 4 assessment / evidence |
| evidence_links | (project_id, claim_id, passage_id, relation), composite claim and passage FKs | Phase 4 assessment / evidence |
| editorial_decisions | (project_id, decision_id), claim composite FK, reviewer/decision/rationale/time | Phase 5 append-only decisions |
| generation_runs | (project_id, run_id), optional revision composite FK, model/prompt/parameters/status/time | Phase 3 initial drafts / runs |

Phase 3 writes initial drafts/revisions and generation runs. Phase 4 writes claims and evidence links; Phase 5 appends human decision records. Source tables now have import/read/search services. These tables now back the corresponding implemented workflows. Dashboard draft/claim counts query actual rows, which are zero in an ordinary Phase 1 workspace. Document Studio lists saved drafts per project.

Editorial goals are typed JSON with document type, audience/custom description, working title, approximate words, depth and instructions. IDs are application-generated UUIDs; timestamps are UTC. Project version starts at 1 and increments atomically. An UPDATE must match the displayed version; stale edits raise a typed conflict and preserve the accepted edit. Project title duplicates are allowed; IDs distinguish projects.

Source metadata will carry filename/title/author/type/import time/optional user-supplied URL/hash. Passage locator JSON will carry section/page/heading and stable identity inputs. Source metadata URLs are labels, never fetch instructions. JSON columns are constrained to valid JSON, and service/domain validation must enforce their future field schemas. Composite foreign keys prevent cross-project evidence links. No cascading destructive startup cleanup is defined.

Assessment categories distinguish source support from truth and retain unresolved status. A human-verified domain record requires an accepted human decision and rationale; the editorial service validates records against persisted evidence and revision identity. These model-level checks are not a functioning semantic verifier. No Phase 1 claim edits or human-review workflow is exposed.

## Additive migration 2

Migration 1 SQL is unchanged. Migration 2 adds `source_sections` (project/section/source IDs, exact text and locator metadata), `source_imports` (per-source warning codes), and the `passage_fts` FTS5 virtual table (project ID, passage ID and searchable text). Existing passage rows are indexed during migration; Phase 1 exposed no source-import service. No existing project, editorial-goal or model-preference record is rewritten. Checksum history is validated before upgrade; all pending DDL and index changes commit together or roll back.

New source metadata serializes the typed SourceDocument. Passage locator JSON records section ID, half-open offsets, page/heading/locator, extraction method and all identities; passage text remains a separate authoritative field. Exact sections are retained independently of overlapping windows. Imports write source, sections, passages, diagnostics and FTS entries in one transaction. Per-project source/text limits are checked inside that transaction; project metadata versions are not bumped by source import, but project updated time advances. Source UUIDs are content-derived, and composite project keys prevent cross-project evidence resolution.

FTS is a retrieval index, not authoritative evidence. Search joins index IDs to selected-project stored sources/passages and revalidates exact section slices. FTS corruption is not a forensic tamper-detection guarantee. No source deletion, replacement or generated-draft mutation is exposed in this phase. See [ingestion](INGESTION.md) for encoding, identity, overlap, location and duplicate policies.

## Additive migration 3

Migration 3 adds `generated_drafts`, keyed by `(project_id, revision_id)` with a revision FK and validated JSON payload. It preserves migrations 1 and 2 unchanged. The payload stores bounded structured sections/blocks, editorial settings, retrieval query, model name/digest, template version, SHA-256 of the prompt/schema, exact supplied passage snapshots and alias mapping, warnings and `unreviewed` status. Canonical passages remain authoritative and are re-resolved before save and on reopen.

Generation records a `started` run before model validation/inference. Safe handled failures mark it `failed`; process interruption can leave `started`, which is not a resumable job. Success inserts a new draft, initial revision number 1, structured artifact and completed run in one transaction. No existing draft is overwritten and there is no revision-edit service yet. Generation parameters include deterministic request settings, prompt hash and evidence count. Raw invalid model output and exception details are not persisted. Draft content is structured JSON in the existing revision content column. No claims or verification decisions are fabricated.

## Additive migration 4

Migration 4 leaves migrations 1–3 unchanged and adds `verification_ledgers` (revision FK and header/hash JSON), `claim_units` (claim/revision FKs, unique section/block position, typed exact-text/assessment metadata) and `assessment_runs` (claim/revision FKs, started/completed/failed, start time and provenance/result JSON). Existing project/source/draft data is not rewritten. Older drafts acquire derived ledgers on first review; new draft publication creates claims and ledgers in the same transaction.

Existing `claims` rows mirror the typed current claim assessment; `evidence_links` contain checked supporting/contradictory passage relationships. Original draft citations are stored separately from inferred support. Exact supporting/contradictory/temporal quotes and offsets reside in the claim-unit payload. Temporal references have no invented support relation. Current units hold an optimistic assessment version; publication checks the version and canonical revision content, atomically replaces only that claim's evidence links and completes an append-only run record. Historical run payloads retain prior results and the candidate evidence used. Human-review fields remain pending/empty in Phase 4. See [methodology](VERIFICATION.md).

## Additive migration 5

Migrations 1–4 remain unchanged. `draft_heads` holds the current revision for each project/draft and backfills from existing highest revision numbers. Initial generation inserts its head transactionally. Draft lists join the head; revision history joins all `generated_drafts` snapshots to `revisions`, ordered by number. SavedDraft has compatible defaults for initial revision number/origin and optional parent/reason metadata, so older JSON is not rewritten.

`revision_events` stores revision/parent FKs, editor, reason, origin and timestamp. A manual save or section regeneration appends revision/content/artifact/event/ledger and atomically advances the head only if the expected base is current. Section regeneration additionally completes its generation run in the same transaction. Historical snapshots remain unchanged. New revision claim IDs are distinct and start pending, including unchanged prose.

`human_review_events` stores claim FK, accepted/rejected/reopened action, timestamp and JSON before/after snapshots plus typed reviewer/rationale/selected-passage input. Accepted/rejected actions also append `editorial_decisions`; reopen events retain history without inventing an accepted/rejected row. ClaimUnit retains the automated category separately and the current human-reviewed passage IDs. Exact project passage resolution and optimistic claim versions apply. Automated evidence links remain distinguishable from human-reviewed references in the unit/event payload. No new AI support is inferred from a human action. See [editorial workflow](EDITORIAL.md).

## Phase 6 exports

Exports add no database tables or mutation API. A manifest references a selected revision, its current claim versions and exact authoritative evidence, plus stored assessment/human/revision event history. Preparation checks claim versions again inside its audit read snapshot. Downloaded files do not subsequently change when the database changes. Draft labels and unresolved flags remain visible. Runtime export bytes, sample artifacts and rendering reports are Git-ignored.
