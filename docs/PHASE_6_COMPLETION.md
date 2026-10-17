# Research2Docs AI Phase 6 completion

Completed October 17, 2026. All six implementation phases are working: project/source persistence, local structured generation, provisional support assessment, editorial revisions/human decisions and four safe export formats. The user authorized the final commit/push to the repository in `github.md` and a complete walkthrough.

## Delivered

Phase 6 adds `exporting/models.py`, `renderers.py`, `services/export_service.py`, `ui/exports.py`, export/complete-flow tests, the export contract and full walkthrough. Export Center prepares a selected historical/current revision in Markdown, editable DOCX, standalone HTML or a versioned JSON evidence manifest. Filenames are fixed UUID/revision values; services return bounded bytes instead of accepting output paths. There are no later-phase placeholder views.

Readable output retains the draft label, unresolved count, warnings, citation aliases, current claim ledger, exact supporting/contradictory/temporal excerpts, full evidence passages/source metadata, human decision history and generation provenance. JSON includes the exact revision, claim versions, authoritative evidence, stored assessment/candidate/decision/revision history and generation-run parameters. Exports never verify content or change a decision. Snapshot version checks reject racing review changes; the UI invalidates prepared downloads when it observes changed selections/status.

HTML uses a fixed autoescaped template and restrictive CSP without active links/scripts/images/forms. Markdown escapes dynamic markup and safely fences passages. DOCX has editable text/styles and no generated macros/external relationships/embedded files. XML-invalid controls are visible U+ labels in readable formats and remain exact in JSON. Repeated exports are byte-reproducible, including canonical DOCX ZIP timestamps/order.

## Actual verification

| Check | Result |
|---|---|
| Final deterministic pytest | **211 passed**, 1 optional discovery test deselected; 5 existing upstream SWIG deprecation warnings |
| Strict mypy | Passed, 49 source/UI files |
| Ruff lint / formatting | Passed |
| Dependency integrity | `pip check` passed; no dependencies changed in Phases 5–6 |
| pip-audit | No known vulnerabilities across 75 entries; unpublished local package skipped as not on PyPI |
| Gitleaks | Exit 0, no leaks in the final publishable source snapshot; runtime data, exports, environments and caches excluded |
| Four-format exports | Exact revision/source IDs, unresolved flags, evidence/history/provenance, repeatable bytes and inert markup checked |
| Concurrency / bounds | Racing review snapshot rejection, stale prepared download invalidation, history/output limits and project scope checked |
| Controlled complete workflow | Five-format imports, generation/assessment, fictional fixture decision, edit, section regeneration, exports and reopen passed |
| Existing smoke script | Project lifecycle and five-format import/search/exact PDF page 2/reopen passed |
| Real local demo | Installed Qwen generation, assessment and one-section regeneration; browser edit; all four exports; original history retained |
| DOCX visual QA | Final six-page sample rendered with bundled LibreOffice/renderer; every page visually inspected; title-border defect corrected and re-rendered |
| Browser download | Revision-3 DOCX downloaded to the user's Downloads folder and matched the rendered sample byte-for-byte |

Controlled reviewer names/decisions are fictional test data, not actual approvals. No human decision was created in the live demo. The existing project/source data and original three user documents were preserved. The live demo has one draft with revisions 1–3: original generation/assessment, selected-section regeneration, and a manual fictional-heading edit. New revision claims remain pending.

The app runs on loopback port 8503 using `/private/tmp/research2docs-phase1-demo`; that temporary storage is demonstration data and may be cleaned by the OS. Important work should use persistent operator-selected storage and backups. Only Research2Docs was restarted; KnowledgeBridge was not changed. Sample exports, rendering PNG/PDF intermediates, backups and tool reports remain Git-ignored. The original supplied `prd.md`, `codex-prompt.md` and `how-2-demo.md` remain byte-identical. The original PRD's broader roadmap is preserved, not a claim that unrequested future features were built.

## Security decisions and residual limits

Source/model/editor text remains untrusted data. There is no model execution/tool access, source URL fetch, proxy/redirect/cloud fallback, automatic model pull, arbitrary export path or raw source/model logging. Parser workers and inference/export inputs are bounded. Current schema is 5; migrations are checked/additive and unknown schemas fail without rebuilding data. Revision/head/claim concurrency and exact evidence checks protect ordinary workflow integrity, not malicious same-user database modification.

Support assessment remains AI-assisted, source-relative and fallible. Retrieval can miss counterevidence; compound prose-block claims can conceal missing details; source dates/version excerpts establish only a provisional temporal concern. Human verification is a self-reported named editorial judgment, not authenticated identity, independent truth or certification. Every new revision resets all claim assessments/decisions. Generation-time warnings remain historically preserved.

Export limits are 2,000 selected-revision audit records, 8 MiB stored audit JSON, 16 MiB manifest, one million evidence characters and 32 MiB output bytes. Exceeding a bound fails without silently dropping history. The existing context/deadline/output caps apply to inference; disconnecting cannot guarantee server cancellation. There is no global concurrency cap, automatic retry/recovery/pruning, conflict merge, OCR, web scraping, source replacement/deletion or public hosting. Local storage/exports are unencrypted. Tested host: Intel macOS/Python 3.12; cross-platform deployment and every possible exported layout are not independently verified.

Follow [the complete walkthrough](WALKTHROUGH.md). Details: [export contract](EXPORTS.md), [editorial workflow](EDITORIAL.md), [verification methodology](VERIFICATION.md), [security](SECURITY.md), [test plan](TEST_PLAN.md). Audit JSON is `/private/tmp/research2docs-phase6-audit.json`; local screenshots/scan reports and the rendered sample are under ignored `outputs`.

The final repository is `https://github.com/marclarouche/research2docs-ai`. Commit/push completion is verified separately in the task response; no force push or fabricated human decision is part of this release.
