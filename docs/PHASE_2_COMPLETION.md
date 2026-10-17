# Research2Docs AI — Phase 2 completion

Completed October 17, 2026 in `/Users/cyberlifecoach/Projects/research2docs-ai`. Phase 2 source ingestion, persisted evidence and full-text retrieval are implemented. No Phase 3 generation, semantic verification, editorial revision or document export workflow was added.

## Delivered

- Byte-based imports for text PDF, DOCX, UTF-8 Markdown/TXT and local UTF-8 HTML, with content/signature/package/encoding validation beyond extension checks.
- Preserved available title/author, original filename, manual reference URL label, import UTC timestamp, content SHA-256, extraction method and source location. Unknown authors remain absent; bounded metadata truncation is warned.
- Content-derived source IDs, deterministic section/passage IDs, exact immutable extracted sections and character slices; heading/page boundaries are preserved. Duplicate byte content within a project retains its first metadata and evidence records, even after filename changes.
- Atomic source/sections/passages/diagnostics/FTS5 import. Batch results explicitly identify accepted, duplicate and rejected files. Project quotas are checked inside the write transaction.
- Bounded quoted-term FTS5 search, project-scoped results, BM25 plus stable-ID tie breaking, and exact stored-passage resolution. Retrieval is neither source authority nor factual verification.
- Functional Project Workspace import/inventory and Source Explorer metadata, search, page/section and exact passage inspection. No model is needed for these operations.
- Additive checked schema 1→2 migration, preserving existing project/editorial metadata and model preferences. Migration 1 SQL remains unchanged; failed upgrades roll back.
- Original fictional five-format Orion Archive samples and a non-overwriting sample generator.

Key new files: `ingestion/models.py`, `parsers.py`, `chunker.py`, `worker.py`, `runner.py`; `storage/source_repository.py`; `services/source_service.py`; `ui/source_views.py`; ingestion/parser/migration/security/UI/restart tests; `docs/INGESTION.md`; and `samples/fictional_research`. Updated configuration/models/errors, workspace composition, migration/database code, UI shell, packaging/lockfile and development documentation. Original `prd.md`, `codex-prompt.md` and `how-2-demo.md` are preserved.

## Resource and security choices

Parser execution is one fixed current-interpreter command with private, application-generated temporary input/config/result paths. Source filenames and content never become commands or filesystem targets. The worker has CPU/file limits and Python audit denial of sockets, DNS and child commands; the parent imposes a wall watchdog and sampled RSS threshold, killing and reaping violations. Linux also uses RLIMIT_AS. The host's macOS address-space setter rejects that limit, so `psutil` was added for parent-side resident-memory monitoring, with typing stubs in the development group. Sampling can overshoot; this is not an OS sandbox or instantaneous memory ceiling.

Defaults are 10 MiB/file, 100 sources/project, 1M extracted characters/file, 10M/project, 2,000 sections/ZIP entries, 500 PDF pages, 40 MiB expanded DOCX, 3,000 passages, 20-second wall / 10-second CPU / 1 GiB sampled RSS limits and 12 MiB worker result/file output cap. These are per-file/worker bounds, not a global concurrent-session resource budget. Native parser stdout/stderr are discarded; errors are fixed/allowlisted safe codes. DOCX traversal/DTD/entity/macro/encryption/expansion checks run before parsing; HTML is flattened without active content rendering or URL requests. Original binaries are not retained after temporary processing; extracted evidence remains unencrypted local data.

## Actual verification

| Check | Result |
|---|---|
| Deterministic pytest | **92 passed, 1 optional Ollama test deselected**, five upstream SWIG deprecation warnings |
| Strict mypy | Passed, 27 source/UI files |
| Ruff lint / formatting | Passed |
| `uv sync --locked --group dev --offline` after dependency setup | Passed; 78-package lock, 75 installed entries |
| pip check | No broken requirements |
| pip-audit | No known vulnerabilities; unpublished local `research2docs-ai` skipped as not on PyPI |
| Gitleaks | Exit 0, no leaks found in the final publishable-source snapshot; no runtime database, source imports, environments, traces or caches included |
| Five-format worker integration | All five accepted, indexed, searched and reopened; PDF page 2 and DOCX table warning checked |
| Stable evidence / integrity | Exact whitespace/CRLF/Unicode slices, repeated-import IDs, rename duplicate behavior, wrong-project resolution and altered passage rejection passed |
| Atomicity / upgrade | FTS failure rolls back source records; failed migration 2 preserves schema 1; valid upgrade preserves project/model rows |
| Resource / hostile input | Real child timeout and RSS kill-and-reap; actual socket/DNS/command audit denial; malformed/disguised text, ZIP traversal/DTD/entity/macros/expansion/ratio, encrypted/all-empty PDFs and limits passed |
| UI | Create/save/reopen/stale-form tests preserved; import/search/inspect and enabled-submit/empty-batch validation passed |
| Fresh process | Saved sources and FTS reopen with Streamlit imports blocked |

The existing demo storage at `/private/tmp/research2docs-phase1-demo` upgraded from schema 1 to 2 with its original project and model preference unchanged. A separate fictional Phase 2 project was used for live browser uploads/search: all five files imported into 10 passages, and the PDF's exact page-2 marker was inspected. The Phase 1 project was not replaced. A local backup was taken before upgrade/fixture refinement. Existing source-free Phase 1 data was preserved, and no startup cleanup or database rebuild was introduced.

Live checks caught a form-submit button disabled by a buffered file-uploader value; it now submits normally and the service reports an empty batch safely, with regression coverage. HTML extraction was also refined to exclude DOCTYPE/head artifacts from body evidence, with a regression test. The long-running Phase 1 Streamlit process needed a restart to load changed configuration classes; only Research2Docs on port 8503 was restarted. Restart the server after code/config upgrades rather than relying on cached modules.

## Reproduce and limits

Follow README and [ingestion methodology](INGESTION.md). Import the five fictional source files (exclude their README), inspect per-file warnings, open Source Explorer and search `RESEARCH_READY`; inspect the PDF marker on page 2. Screenshots and local tool reports are under Git-ignored `outputs`. Audit JSON is `/private/tmp/research2docs-phase2-audit.json`. These are controlled development checks, not a human benchmark, model evaluation, independent audit or certification.

Text/PDF visual order and DOCX/HTML layout interpretation remain limited. No OCR, source URL retrieval, generation, semantic support decisions, revision invalidation, source replacement/deletion or exports are exposed. Shared FTS corpus statistics can change ranking when another project's content changes; results remain project-filtered. Tampering by a malicious same-user process, native parser compromise and global resource exhaustion across many concurrent sessions are outside the containment guarantee. Workers currently require POSIX; the tested host is Intel macOS, not independently verified cross-platform deployment.

**Next authorized step to request: Phase 3**, local structured transformation with audience profiles, versioned prompts and persisted drafts. Phase 3 has not started. No commit, remote configuration or push was requested for this phase.
