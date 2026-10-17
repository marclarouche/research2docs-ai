# Security — Phases 1–2

Research2Docs AI is a local, single-user development application. It is not certified or independently audited. Its privacy boundary is the OS account and trusted local storage, not an authenticated network service.

## Trust boundaries and mitigations

- The browser is served on `127.0.0.1`, with Streamlit telemetry and detailed UI exception display disabled. Keep the loopback binding; there is no authentication, role model or multiuser access control.
- Operator TOML is limited to 32 KiB, parsed without execution and validated by Pydantic. Unknown fields, invalid ports and nonloopback hosts are rejected. `localhost` is canonicalized to a literal loopback address, avoiding external name resolution. Storage override is an explicit trusted operator action, not document-supplied data.
- Project IDs are parsed UUIDs and used only as SQL parameters. Project titles and editorial text are data, never commands, paths or HTML. UI values use text widgets/tables, not unsafe HTML rendering.
- The database has a fixed application filename beneath the selected root, restrictive database permissions on the tested macOS host, short transactions, FK checks, migration checksums and optimistic edit versions. Database/diagnostic symlinks are rejected. No source-driven file write or project deletion is exposed.
- Ollama requests use the standard HTTP client directly, with fixed discovery paths and literal loopback destinations. No environment proxy support, redirect following, cloud fallback, model pull or inference path exists. Read size and socket timeouts are bounded. Malformed/oversized responses, unknown model choices and known cloud metadata are rejected; users see safe messages.
- Diagnostics contain only timestamps and fixed event codes. They are local, bounded to approximately 64 KiB plus one backup, and contain no project titles, source excerpts, raw model output or exception strings. Logging errors are surfaced rather than silently discarded. Other application services return typed safe failures without remote logs.
- Databases, logs, model traces, environments, exports and caches are ignored by Git. pip-audit checks installed dependencies; Gitleaks scans the publishable source snapshot. Findings and scan scope are recorded in the completion report.

## Source ingestion boundary

Phase 2 accepts byte uploads for PDF/DOCX/Markdown/TXT/local HTML. Filename paths and unsupported types are rejected; content signatures/structure/encoding are checked. ZIP expansion/entry/path/encryption/macro/XML-declaration limits apply before python-docx extraction. HTML scripts and embedded active elements are not rendered or fetched. Text-based PDF extraction does not invoke OCR or execute PDF actions.

The fixed parser subprocess uses a private temporary directory, generated filenames, a wall watchdog, CPU/file limits and parent RSS monitoring. Linux additionally has an address-space limit; macOS uses sampled RSS because its address-space setter rejects these bounds. Worker Python sockets, DNS and child-command creation are audit-denied. stdout/stderr are discarded; errors return allowlisted codes. Timeout/memory tests verify child kill and reap. An actual child-process test verifies Python socket/DNS/command denial. These are scoped defenses, not a native-code exploit or OS filesystem/network sandbox guarantee.

Atomic imports enforce project quotas and preserve previous data on parser, limit or SQL failure. Source IDs derive from content; passage IDs are application-owned, and returned text must exactly match stored section slices and locators. Search parameters are bounded and quoted as terms; SQL is parameterized. Search results are scoped to the selected project. Source URL metadata is never fetched. Original binaries are not retained after temporary parsing; extracted content and indexes are local unencrypted sensitive data and remain Git-ignored.

## Unimplemented attack surfaces

There is no generation, semantic assessment, revision editing or export renderer. Prompt-injection resilience of a language model, factual support/entailment, stale draft citations and HTML/DOCX export safety are **not verified**. Inert-source tests demonstrate data handling and unchanged canaries, not immunity to model prompt injection. Later phases must implement those boundaries before enabling their UI.

## Residual risks

Local data and diagnostics are unencrypted. Same-user malware, malicious backups, tampered database files, denial of service, browser extensions and a compromised local Ollama server are outside a secure sandbox guarantee. Directory and file checks do not defend against every filesystem race by a hostile same-user process. Socket timeouts bound inactivity, not total elapsed time against a deliberately trickling server. The separate Ollama process has its own network permissions; rejecting advertised cloud metadata is not an OS network firewall. Large project counts have no pagination in Phase 1. Runtime data must be backed up carefully with the app stopped.

No release quality, model suitability, source truth, license clearance, regulatory compliance or security certification follows from passing tests. Review dependency and third-party distribution obligations before public release. Report specific reproducible issues with non-sensitive steps; never attach private research or credentials to a public issue.


## Phase 3 generation trust boundary

Versioned application templates and the fixed system message are separate from JSON-encoded editorial preferences and untrusted source evidence. Separation reduces instruction ambiguity but cannot guarantee an LLM ignores indirect prompt injection. The model has no tools, execution path, source URL fetcher, arbitrary write target or authority to mark content verified. Prose and headings display as plain text, so HTML/Markdown links are inert. All content is labeled unreviewed; empty citation arrays receive an explicit verification warning.

Only supplied aliases may appear in citation arrays. The application maps them to actual project-scoped persisted passages, rejects invented/duplicate references and rechecks exact evidence before commit and on reopen. This validates citation existence, not entailment, source authority, completeness or truth. No claim support scores, human verification or fabricated ledger entries are produced in Phase 3.

Inference uses fixed loopback chat requests, local model metadata/context checks, no redirects/proxies, bounded prompts/responses and finite socket/deadline reads. Cloud-backed catalog/show entries are rejected. The installed Ollama service remains trusted: a malicious or reconfigured server could proxy requests despite earlier metadata checks. Model computation may continue server-side after a client timeout; there is no global job queue/concurrency cap or server cancellation guarantee. Seed/temperature settings do not guarantee identical model output. Drafts, evidence snapshots and editorial settings are local unencrypted data, excluded from Git. Failed raw responses and source contents are not logged.


## Phase 4 assessment boundary

Claim candidates come directly from exact saved draft blocks with application-derived IDs. The model receives only a separate JSON evidence envelope and cannot select an authoritative ID, execute instructions, fetch a URL or return Human verified. Returned aliases, exact excerpts/offsets, source scope and category prerequisites are validated. Unknown references, fake quotes, duplicate roles, model confidence fields and unsupported human status are rejected; failures preserve the current result. Dynamic explanations, headings and excerpts use plain text presentation. Human statuses remain pending, including AI-supported results.

A matching quote is not entailment. Source text can still inject misleading semantic decisions, quotes can omit context and FTS can miss conflicting sources. The UI exposes full passages and preserves limitations/missing-citation flags. Revision/text hashes and optimistic versions prevent accidental stale assessment reuse and competing result overwrites; they are not protection against a malicious same-user process modifying the database. Source dates/version strings justify only a provisional temporal flag, not authority or currentness. Existing loopback, resource, output, no-logging and trusted-server limits continue to apply. Assessment payloads are unencrypted local data and excluded from Git.


## Phase 5 editorial boundary

Human verification requires an explicit service action with reviewer, rationale and real selected project passages; the UI additionally requires own-review confirmation. AI schemas still reject human_verified. Reopening/rejection preserves history and restores the automated category; accepted/rejected records cannot be silently overwritten by inference. This is local self-reported review, not authenticated identity, expertise, external verification or formal approval. Do not manufacture live human decisions during agent demonstrations.

Revision publication compares the expected head and canonical base content. Claim decisions compare the displayed version, sharing concurrency control with model assessments. New revisions reset all claim assessments/decisions; unchanged blocks do not inherit approval. Prior snapshots and events remain available. Section regeneration uses one-section typed output, supplied-alias checks, preserved alias mapping, bounded whole evidence and existing loopback transport. Other sections are copied exactly; no source/model-generated command executes. Dynamic edits, reviewer names, rationales and history render as inert text. History growth, unencrypted local storage and malicious same-user modification remain limitations.


## Phase 6 export boundary

Exports return bytes under application-generated UUID/revision filenames and accept no output paths. HTML autoescapes every dynamic value in a fixed template and disables active/network content with CSP; no source link, image, script, form or iframe is generated. Markdown escapes dynamic markup and uses long code fences. DOCX adds only editable text/styles, with no macros, external relationships or embedded content. Control characters unsafe for XML are displayed as labels in readable output while JSON preserves originals. Exact claims/evidence/review flags remain present and no export changes a verification decision.

Snapshot version checks prevent mixing a ledger with concurrently changed review history. The prepared-download UI invalidates an observed stale revision/claim snapshot; a previously downloaded file remains a historical record. Audit/output bounds fail safely without silently dropping history. Local exports can include private source/reviewer information and are unencrypted. No automatic upload, sharing, signing, authenticated human identity, external fact check or public hosting is provided. Repeated deterministic exports prove reproducibility of formatting, not truth. Final checks and residual deployment limits are reported in the Phase 6 completion document.
