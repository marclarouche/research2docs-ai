# Research2Docs AI — Phase 3 completion

Implemented October 17, 2026. Phase 3 adds local structured transformation and persisted unreviewed drafts. Claim assessment, human editorial decisions, revision editing, section regeneration and exports remain Phases 4–6.

## Delivered

- Local Ollama structured chat, revalidated installed/local model selection and context checks, fixed schema request, no tools, downloads, redirects, proxies or cloud fallback.
- Five separately versioned packaged templates and distinct ordered-section schemas: explainer, tutorial, FAQ, instructional guide and executive brief.
- Six explicit audience profiles, custom audience description, working title, approximate word count, technical depth and editorial instructions.
- Project-scoped FTS retrieval, whole-passage prompt packing, separate instruction/data messages and bounded inference.
- Strict structured-response validation; invented, foreign or repeated citation aliases and malformed, truncated or incorrectly structured output are rejected. Supplied aliases resolve to real exact persisted passages.
- Document Studio generation, saved-draft selection, inert text presentation, unreviewed labels, per-block references/review notes, evidence inspection and generation provenance.
- Atomic new draft / revision 1 / structured artifact / completed run persistence. Safe handled failures mark runs failed without partial drafts. New generations never overwrite a previous draft.
- Additive schema 2→3 migration preserving projects, preferences, sources, passages and FTS; migrations 1 and 2 unchanged.

Key additions are `generation/models.py`, `prompts.py`, five `generation/templates/*.json`, `services/generation_service.py`, `storage/draft_repository.py`, `ui/studio.py` and generation/transport/schema-3 tests. Existing Ollama client, workspace composition, settings, migration loader, UI shell, package-data configuration and development documentation were updated. The original input documents remain byte-identical.

## Verification

The full deterministic suite passed **137 tests**, with one optional discovery test deselected and five existing upstream SWIG deprecation warnings. This includes a regression confirming model-authored heading/prose markup is displayed as inert text. Ruff and strict mypy passed (32 source/UI files), and the existing five-format smoke script passed. No dependencies were added or changed; `pip check` reports no broken requirements. Gitleaks exited 0 with no leaks in the publishable source snapshot. pip-audit checked 75 dependency entries and reported no known vulnerabilities; the unpublished local package is not on PyPI and was skipped. The environment did not expose `uv` on PATH in this phase, so no fresh sync is claimed; existing locked installed dependencies were used.

Checks cover all formats/audiences, malformed output, invented references, source scope, exact snapshot resolution, no-evidence/model/budget preflight, citation-free warnings, run failure and transactional rollback, fresh-process reopen without Streamlit, UI generation/reopen, local model/context checks, response cap, truncation/redirect rejection, socket cleanup and deadlines. A real socket-pair test verifies the deadline interrupts slow-drip HTTP headers without an external network service.

A real local `qwen3-vl:4b-instruct` run on fictional Orion Archive material completed, saving a four-section explainer with eight supplied passages. It reopened successfully in the browser with unreviewed labels and evidence references. Draft ID: `1e47d324-1e64-4193-a249-6932cf2a0b7b`. This is an operational check, not a benchmark or factual-support evaluation.

The live database was backed up to ignored `work/phase3-before-upgrade.sqlite3`. After upgrade, every existing project, preference, source, section, passage, import-warning and FTS row compared equal to the backup. The earlier Phase 1 and Phase 2 projects were preserved. Only Research2Docs on port 8503 was restarted.

## Security and limits

Source text and model responses remain untrusted. Prompt separation cannot guarantee resistance to indirect injection; no model instruction is executed. Dynamic model headings and prose render as plain text. Citation existence is checked, but semantic support, source authority, truth and audience fidelity are not. Every draft remains unreviewed, with explicit missing-citation/length/budget warnings where applicable.

Defaults: 32,768 context tokens, 4,096 output tokens, eight retrieved passages, 24,000 prompt bytes, 256 KiB response bytes and 180-second inference deadline. UTF-8 bytes are a conservative token proxy, not the model tokenizer. Long word targets can exceed the output budget; truncated responses are rejected. There is no automatic repair/retry or global concurrent-job limit. A timeout disconnects the client but may leave Ollama computing. The local Ollama server is trusted not to proxy or swap models after discovery. Interrupted runs can remain started; no background recovery is implied. Local drafts/evidence remain unencrypted and Git-ignored.

See [generation methodology](GENERATION.md), [security](SECURITY.md), [data model](DATA_MODEL.md) and [test plan](TEST_PLAN.md). Local audit JSON is `/private/tmp/research2docs-phase3-audit.json`; screenshots and redacted secret-scan reports are in ignored `outputs`.

Next phase: **Phase 4 claim verification**, requiring separate authorization. No Phase 4 support assessment or fabricated claim ledger was added. No commit or push was requested or performed.
