# Source ingestion and retrieval — Phase 2

Import, extraction, indexing and search are ordinary Python services, independent of Streamlit and Ollama. Source documents are untrusted data; relevance is not verification. Generation and semantic claim review are not implemented.

## Supported formats

| Format | Detection / extraction | Evidence locations and limitations |
|---|---|---|
| TXT | Strict UTF-8, optional BOM; reject binary controls and PDF/ZIP signatures | Exact BOM-free decoded text, including CRLF/whitespace; no encoding guessing |
| Markdown | UTF-8 plus markdown-it CommonMark token maps; no HTML rendering | Exact decoded source sections split at parsed headings; fenced headings stay code; Markdown syntax remains in excerpts |
| Local HTML | Recognizable HTML tags, strict UTF-8, Beautiful Soup's local `html.parser` | Heading/text-node order, flattened text; scripts/styles/head/frames/objects/forms excluded; no CSS layout, JavaScript or URL fetching |
| DOCX | ZIP signature, required package parts, bounded verified decompression, python-docx body order | Heading sections and flattened table rows; headers, footers, comments, tracked changes, images and nested layouts can be incomplete |
| Text-based PDF | PDF signature plus PyMuPDF parsing; encrypted files rejected | One-based page references and sorted existing text; visual reading order may differ, no OCR; empty pages warned, all-empty documents rejected |

Filename extensions are allowlisted, but signatures, encoding, package structure and parser validity are also checked. TXT and Markdown share a text encoding and cannot always be distinguished by a magic signature; the chosen supported extension supplies the interpretation after text checks. HTML is never treated as a URL or rendered as unsafe HTML. DOCX package entries are read from bytes, not extracted to their filenames. Traversal, symlink entries, encrypted ZIP parts, macros, duplicate names, XML DTD/entity declarations and excessive expansion are rejected.

Source metadata includes filename, available title and author, supplied HTTP(S) URL label, import UTC time, type and SHA-256. Missing authors remain absent; title falls back to the filename stem. Title/author display metadata is bounded and truncation is warned. Manually supplied metadata has validated length limits. URLs are labels only; credentials and non-HTTP(S) schemes are rejected and no URL is fetched.

## Stable evidence

A source UUID derives from its byte SHA-256, independently of filename/project. Byte-identical content is skipped within a project, preserving the first source metadata, timestamp and passages even when the file is renamed. The same bytes can be independently imported into other projects; all persistence and retrieval relationships include project identity.

Section UUIDs include source identity, extraction version/method and original section order. Passage UUIDs include section identity, chunk settings, exact offsets and a slice digest. Whole section boundaries never mix. Default passages are up to 4,000 Unicode characters with up to 200 characters of overlap, preferring paragraph boundaries in the latter half of a window. IDs remain stable for identical bytes and the same extraction output/settings; parser/library upgrades can change extraction and hence passage IDs.

Every passage stores its exact text, source ID, section ID, original passage ordering, extraction method and half-open section character offsets. Metadata preserves page/heading/section locator. TXT/Markdown sections reference BOM-free decoded positions; other offsets refer to extracted text, not binary-file coordinates. Immutable extracted sections are saved separately and each retrieved passage is checked against its exact persisted section slice and location. Truncating, trimming or reconstructing a quote is not part of ingestion.

## Atomic persistence and FTS5

A single SQLite transaction inserts source metadata, extracted sections, passages, warnings and FTS5 entries. Failure rolls back the entire file, preserving earlier imports. Each file in a batch is independent; results explicitly report successes, duplicate skips and rejected files. Batches are limited to 10 files. Limits are checked again in the write transaction so concurrent imports cannot bypass per-project capacity checks.

Sources are searchable immediately after commit; no manual index build or model is needed. Search uses up to 64 quoted Unicode terms joined by OR. Underscores remain token characters, preserving identifiers such as `RESEARCH_READY`. User SQL/FTS operators are treated as terms, never executed as syntax. Queries are limited to 2,000 characters; final limits are 1–20 hits. Results are project-filtered, sorted by ascending FTS5 BM25 and passage UUID for ties. The FTS5 corpus statistics are shared across projects, so unrelated project content can affect ranking scores/order; no calibrated confidence or project-independent score is claimed. Returned passages always come from the selected project and are re-resolved from authoritative storage.

Original uploads are not retained after processing. Keep originals for reparsing and visual comparison. Saved extracted sections cannot recover omitted original content. Source deletion/replacement and evidence lifecycle across drafts are not Phase 2 features.

## Resource controls

Defaults in operator TOML: 10 MiB/file; 100 sources/project; 1,000,000 extracted characters/file; 10,000,000 characters/project (counted on nonoverlapping sections); 2,000 sections; 500 PDF pages; 2,000 ZIP entries; 40 MiB expanded DOCX; 3,000 passages/file. DOCX parts over 1 MiB with compression ratios over 200 are rejected.

Parsing runs in one fixed isolated Python interpreter command, using application-generated temporary filenames rather than source filenames. Temporary input/config/result files are removed on normal completion and handled failures. Parser stdout/stderr are discarded to avoid leaking content. Results are capped at 12 MiB. The parent imposes a 20-second wall timeout and samples resident memory every approximately 20 ms, killing and reaping the worker above the 1 GiB threshold. The worker applies a 10-second CPU limit and 12 MiB file-write limit. Linux additionally applies an address-space limit; macOS rejects that facility, so resident-memory monitoring is used there. Sampling can overshoot between checks. `psutil` and its typing stubs were added specifically for this cross-platform resident-memory monitor.

A Python audit hook denies worker socket connections, DNS resolution and new command processes. The launcher alone imports subprocess and invokes the current interpreter with fixed arguments; there are no source/model-selected commands. These controls reduce parser failure impact; they are **not an OS filesystem/network sandbox**, a strict instantaneous RSS ceiling, or a guarantee against native parser compromise. Current workers require POSIX; unsupported platforms fail closed. Parser/worker failure never reaches the database as a successful import.

[Security](SECURITY.md) · [Data model](DATA_MODEL.md) · [Tests](TEST_PLAN.md)
