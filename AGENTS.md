# Research2Docs AI contributor instructions

Preserve the supplied `prd.md`, `codex-prompt.md` and `how-2-demo.md`. Read docs/PRD.md and codex-prompt.md. The user authorized Phase 2 on October 17, 2026: bounded PDF/DOCX/Markdown/TXT/local-HTML ingestion, preserved metadata and exact evidence passages, stable IDs, source persistence, FTS5 retrieval and Source Explorer. Preserve Phase 1 data with additive checked migrations. The Phase 3 authorization below permits generation; the Phase 4 authorization below permits claim assessment; editorial revisions and exports still need separate authorization.

The user authorized Phase 3 on October 17, 2026: local structured generation, five versioned templates, audience profiles and persisted unreviewed drafts. Validate returned citation aliases against supplied persisted passages. Claim assessment is authorized below; editorial revisions and exports remain later phases.

Core/services must work without Streamlit. Documents and model responses are untrusted data; never execute them, fetch their URLs or use their contents as filesystem paths. Do not log source contents or raw model responses. Enforce fixed application filenames beneath operator-configured storage, literal loopback networking, bounded responses, no redirects/proxies/cloud fallback, and no automatic model pulls. Bind Streamlit to 127.0.0.1, disable telemetry and UI stack traces.

Use Python 3.12 and uv.lock. Run pytest, Ruff, strict mypy, pip-audit and Gitleaks; report actual results and unresolved findings. Never invent verification, performance, certification or human-review results. Keep databases, environments, exports, logs and caches out of Git. Do not overwrite existing projects on startup. Apply versioned migrations transactionally and reject unknown schema versions.

The user authorized Phase 4 on October 17, 2026: deterministic claim/citation ledger, AI-assisted support assessment, revision-bound evidence relationships and Evidence Review. Automated assessment must never mark human verified. Human decisions, editing/revisions, section regeneration and exports remain later phases.

The user authorized Phase 5 on October 17, 2026: immutable edited revisions, explicit human decisions with reviewer/rationale/evidence, evidence inspection and local single-section regeneration. Never fabricate a human decision. New revisions require fresh assessments; preserve historical decisions. Exports remain Phase 6.

The user authorized Phase 6 on October 17, 2026, followed by a complete walkthrough, and explicitly identified github.md for commit/push. Implement safe Markdown/DOCX/HTML/JSON exports, preserve unresolved review status and exact evidence, run final hardening/end-to-end checks, and commit/push to the named remote without force.
