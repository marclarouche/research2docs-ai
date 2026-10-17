# Test plan

## Normal deterministic suite

Run `uv run pytest -q -p no:cacheprovider`. All storage is temporary; no installed model or external service is required. Coverage includes:

- Project create/edit/list/reopen, UTC metadata, editorial goals and fresh-process persistence with Streamlit blocked.
- Optimistic edits across sessions, transaction rollback, first-migration rollback/retry, idempotent initialization, changed migration checksum and unknown schema rejection without destructive rebuilding.
- Foreign keys and cross-project evidence relationships in the foundational schema.
- Bounded TOML, endpoint rejection, malformed model catalogs, response limits, redirect refusal, model selection persistence, cloud metadata rejection and safe service-unavailable errors.
- Project IDs as values rather than paths, database/log symlink rejection, inert hostile text and absence of Streamlit/execution imports in the engine.
- Streamlit Dashboard/Workspace creation, saving and reopening; stale form rejection; honest future-phase sections; Settings. These use [Streamlit AppTest](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest).

## Optional local integration

Run `uv run pytest -q -o addopts='' -m ollama` with an existing local Ollama service. This performs read-only model discovery. It does not generate content, pull a model or certify model quality. Discovery and model-selection UI should also be manually checked on loopback.

## Tooling and publication checks

Run Ruff lint and formatting, strict mypy, pip consistency, and pip-audit using README commands. Run Gitleaks with redacted results against an exact publishable-source snapshot, excluding ignored runtime content. Preserve tool versions and actual exit codes. Keep user-supplied original files intact and compare the PRD copy to the original. Inspect a live UI screenshot for readable labels and clear phase boundaries. A real fresh-process engine smoke checks operation without the Streamlit package being importable.

## Later acceptance work

Phase 2 tests now cover five-format worker imports, stable exact identities/slices, duplicate preservation, PDF pages, DOCX tables/ZIP/DTD/entity/macro/expansion limits, UTF-8/content mismatches, project/search boundaries, atomic source/FTS rollback, migration 1→2 rollback/preservation, real worker timeout/RSS kill-and-reap, socket/command audit denial, restart persistence and source UI import/search/inspection. Phase 3 must add malformed structured inference and local model failure tests; Phase 4 citation/support/conflict and injection evaluation; Phase 5 revision invalidation and human decisions; Phase 6 warning-preserving Markdown/DOCX/HTML/JSON exports and end-to-end offline checks. Do not report those as covered merely because Phase 1 domain models or tables exist. All human review and semantic quality results require actual evidence.


## Phase 3 checks

Deterministic mocked inference covers all five schema/template formats and six audiences, exact evidence snapshots, saved provenance, empty citations and explicit warnings, no evidence/model preflight, budget rejection, invented references, malformed/extra/overlong/incorrect-section responses, failed run records and atomic draft rollback. A fresh interpreter reopens a saved draft while Streamlit imports are blocked. AppTest generates, saves and reopens a draft without a running model.

Transport tests verify fixed chat endpoint/options, finite read deadline, byte cap, incomplete/truncated/wrong-model/tool responses, redirects and failures, cleanup and local model revalidation. Migration tests upgrade populated schema 2 without changing project/source/FTS records and roll back a failed schema 3 upgrade. Existing ingestion, parser, resource and project tests remain required. Real local inference is a separate manual/optional check using clearly fictional sources; it is not a factual-support benchmark.


## Phase 4 checks

Controlled mocked assessments cover exhaustive/stable prose-block extraction; all five automated categories; exact evidence/offset resolution; missing citations; conservative uncertainty; scope; invented aliases/quotes; duplicate references; rejected human_verified/confidence; no evidence/context budget; conflicting documents; explicit temporal basis; malformed/inference failures; transactional rollback; concurrency; revision fingerprint invalidation; fresh-process reopen without Streamlit/network; legacy initialization and schema 4 migration rollback. AppTest covers assessment/reopen, inert model markup and stale form rejection. These fixture tests verify policy and persistence, not semantic-model accuracy. A separate real local fictional-source assessment checks operation and is reported honestly.


## Phase 5 checks

Controlled fixtures verify edited/history/current revision reads, all-claim invalidation, preserved old automated/human results, explicit named acceptance with real passages, rejection/reopen semantics, mandatory rationale/evidence, claim/project scope, stale edits/decisions, atomic revision/human-event rollback, single-section regeneration with stable aliases, invalid response/concurrent regeneration failure, no-op rejection, schema 5 migration rollback and fresh-process history reopening without Streamlit/network. AppTest covers revision save/history and human own-review confirmation/acceptance. Fixture reviewer identities are fictional test data, not actual human approvals. Real local regeneration on the fictional demo is reported separately.


## Phase 6 checks

Tests exercise all four formats, repeatable bytes, preserved citations/status/warnings/source metadata, exact JSON evidence and human/assessment history, selected historical revisions, inert Markdown/HTML/OOXML, no external DOCX relationships/macros, fixed filenames despite hostile titles, bounded audit history, no export network dependency, concurrent-review snapshot rejection, XML-invalid control character labeling and stale prepared-download invalidation. A controlled complete flow imports five formats, assesses/decides, edits/regenerates and exports/reopens without external services. Fictional fixture decisions are not actual human approvals. A real six-page DOCX is rendered by the bundled renderer and every page inspected; real local generation/assessment/regeneration/browser edit and export are separately reported.
