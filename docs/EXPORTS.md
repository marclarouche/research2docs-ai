# Phase 6 export contract

`WorkspaceService.exports.export(project, draft, format, revision_id=...)` returns validated export bytes and a fixed UUID/revision-derived filename. Supported formats are `markdown`, `docx`, `html` and `json`. No title, source filename, URL or model content becomes a filesystem path. The application writes no arbitrary export destination: Export Center serves a local browser download. Prepared downloads are discarded from the visible UI if the selected revision/format or claim versions change.

## Evidence and review preservation

Exports always carry a draft label, selected revision identity, original warnings, claim statuses and unresolved human-review flags. Readable formats include the document, per-block citation aliases/status, current claim ledger, supporting/contradictory/temporal excerpts, exact evidence passages, source filenames/titles/authors/hash/import/page/section metadata, human decision history and generation provenance. Reference URLs are inert labels. No export promotes support, approves a claim or changes a stored review decision.

The JSON manifest is version 1.0 and preserves the exact saved draft, claim ledger, authoritative passages, source metadata, stored assessment-run histories and candidate evidence, human decision before/after records, and revision-event metadata for the selected revision. Other revisions remain in the app's revision history and require their own export. The manifest includes revision/claim IDs and versions so a saved output can be identified as a specific snapshot. It is an evidence record, not cryptographically signed or independently verified proof.

Canonical revision content and exact quote/passage integrity are checked through the existing services. During preparation, the export compares current saved claim versions against the captured ledger and reads its assessment/human history in one database snapshot. A racing review change fails safely instead of mixing results. Changes after snapshot preparation do not retroactively update a downloaded file. The UI invalidates a cached prepared download when it observes a later version.

## Inert rendering

Markdown escapes generated markup and uses dynamically long code fences for exact source passages; filenames and citation IDs remain ordinary displayed text. HTML uses a fixed Jinja2 template with autoescaping and a restrictive meta Content Security Policy. It contains no scripts, images, active source links, embedded content or forms. DOCX uses ordinary editable paragraphs/styles and text; no macros, external relationships, generated fields or embedded files are added. Invalid XML control characters become visible U+ labels in readable output; JSON retains the exact original string. Text-based layout does not reconstruct source visual layout.

DOCX uses black headings, an editable title style, letter pages and readable paragraph spacing. The stock title border is removed. ZIP member timestamps/order and document metadata are fixed to produce byte-reproducible repeated exports from the same records. Markdown, HTML and JSON formatting is likewise deterministic. Export determinism does not imply model determinism or factual correctness.

## Resource bounds and limitations

The exporter rejects selected-revision histories exceeding 2,000 run/decision records or 8 MiB of stored history JSON, a final manifest exceeding 16 MiB, more than one million evidence characters, and output bytes above 32 MiB. It fails instead of silently omitting audit data. Extremely long or complex content may require a smaller revision/source scope. The layout of every possible future document is not guaranteed; inspect important exports in the receiving application. The supplied six-page fictional DOCX was rendered using the bundled renderer and visually checked.

Local exports may contain unencrypted source content, reviewer names/rationales and local model identifiers. Downloads remain under the user's control and are not uploaded by the app. Export Center does not add document signing, external fact-checking, authentication, access controls or cloud storage. The app is intended for one trusted local OS user on loopback; network deployment is not part of this release.
