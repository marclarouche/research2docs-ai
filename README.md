# Research2Docs AI

A local technical research and editorial workbench, built incrementally. **All six phases are implemented:** persistent projects, five-format ingestion, exact evidence passages, FTS5 retrieval, local structured draft generation and revision-bound claim assessment. Saved editorial revisions, explicit human decisions and section regeneration are available. Markdown, editable DOCX, standalone HTML and a JSON evidence manifest are available. AI-assisted support is not independent verification; claims require human review, recorded explicitly for each revision.

## Install and run

Use Python **3.12**, Git and [uv](https://docs.astral.sh/uv/). From this repository:

```sh
uv python install 3.12
uv sync --locked --group dev
uv run streamlit run ui/app.py --server.address 127.0.0.1 --server.port 8503
```

Open [Research2Docs AI](http://127.0.0.1:8503). Port 8503 keeps the app separate from the KnowledgeBridge demo on 8502. Setup requires downloads unless cached. Project operations run without internet or Ollama after installation. No startup model request occurs.

Import and full-text search work without a model. Start your installed Ollama service separately, then use **Check local Ollama** on Dashboard or Settings. Discovery uses the local [model catalog API](https://docs.ollama.com/api/tags). Settings can validate and save a local model selection, using [model metadata](https://github.com/ollama/ollama/blob/main/docs/api.md#show-model-information); saving a selection starts no inference or model download. Document Studio performs inference only after you select Generate. Discovery is not an inference/model-quality assessment.

## Demonstrate the current application

1. On Dashboard create **Fictional Research**, with a short research purpose.
2. In Project Workspace change the title, document type, intended audience, working title, approximate word count, depth and editorial instructions. Save.
3. Refresh or restart the application and reopen the project. Your data remains saved.
4. Open the same project in two sessions. Save an edit in one, then attempt an edit from the stale form in the other. The latter is rejected. Use **Reload saved project** to get fresh data before retrying.
5. In Settings choose **Check local Ollama**. If available, select a discovered local model and **Save model selection**. An unavailable service does not block project management.
6. In **Project Workspace → Source documents**, choose the five files from `samples/fictional_research` (exclude its README). Leave optional metadata blank, then select **Import and index sources**. Each file reports its own result and extraction warnings.
7. Open **Source Explorer**, search `RESEARCH_READY`, and inspect the stored source/passages. The PDF marker is on page 2. Expand Source metadata for title, author, SHA-256, import time and reference URL label. Reimporting an identical file skips it without changing the stored metadata.
8. Open **Document Studio**. Select an output type and audience, set the working title, target words and depth, and enter `RESEARCH_READY Orion Archive readiness verification limitations` as the research question. Select **Generate and save unreviewed draft**. This invokes the selected installed model locally; no model is downloaded.
9. Inspect the saved sections, review warnings and reference aliases. Expand **Inspect supplied evidence** to read each exact stored passage. Reopen the app and select the saved draft; it persists with its generation metadata.
10. Open **Evidence Review**, select the saved draft and a claim/prose block, then choose **Assess selected claim locally**. Inspect the proposed category, explanation, exact supporting/contradictory/temporal excerpts and their full source passages. Reopen to confirm results persist.
11. All generated text remains **unreviewed**. Citation checks establish references exist; AI support assessment is provisional and source-relative. Use the human-review form to record your own accepted/rejected/reopened decision with reviewer name, rationale and reviewed passages. **Reload claim assessment** refreshes a stale form before reassessment.

For an ordinary-Python engine demonstration without Streamlit or Ollama:

```sh
uv run python scripts/smoke_test.py
```

The script uses temporary storage and does not change the normal workspace.

12. In Document Studio select a saved revision. Under **Editorial workspace**, choose a section, enter your editor name and revision reason, edit its text/citations, then **Save as new revision**. Earlier content and decisions remain available in the revision selector. All claims in the new revision reset for review.
13. To regenerate a section, use the separate regeneration form with an editor name, reason and instructions. The installed model replaces only the selected section in a new revision; inspect and reassess the result.

## Storage and configuration

Operator settings live in `config/research2docs.toml`. The default database is Git-ignored `data/research2docs.sqlite3`. To open a separate local workspace:

```sh
RESEARCH2DOCS_DATA_DIR="$PWD/work/demo" uv run streamlit run ui/app.py --server.address 127.0.0.1 --server.port 8503
```

The override selects storage; it does not move or delete existing data. Stop the app before backing up the database and any SQLite journal files together. Local storage is unencrypted. Project IDs are UUIDs passed as SQL values, never filesystem paths. The app uses a fixed database filename, foreign keys, checked migrations, transactions and optimistic project versions. Unknown or inconsistent schema history is rejected, never silently rebuilt.

The Ollama endpoint accepts literal loopback IPs or `localhost` (canonicalized to `127.0.0.1`). No remote hosts, proxy routing, redirects or cloud fallback are used. Bound responses and socket timeouts apply. Local diagnostic files contain timestamps and fixed event codes only, with no source text or raw exception details. See [security](docs/SECURITY.md) for limits.

## Checks

```sh
uv run pytest -q -p no:cacheprovider
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run python -m pip check
uv run pip-audit --progress-spinner off
```

Normal tests use fixtures and temporary storage; they do not require a running model or external services. Optional read-only local integration:

```sh
uv run pytest -q -o addopts='' -m ollama
```

Install Gitleaks separately from its official distribution, then run `uv run python scripts/scan_secrets.py`. It copies the publishable current source to a temporary snapshot and runs Gitleaks with redacted output. Ignored environments, user data, outputs and caches are excluded. This covers the current source snapshot, not uncommitted history or ignored runtime data. See [test plan](docs/TEST_PLAN.md) and [final report](docs/PHASE_6_COMPLETION.md) for actual results; the [Phase 1 report](docs/PHASE_1_COMPLETION.md) remains historical.

## Scope and next steps

Supported imports: text-based PDF, DOCX, UTF-8 Markdown/TXT and local UTF-8 HTML. No OCR, automatic web retrieval or web scraping. Imports parse in bounded temporary workers; extracted sections/passages, metadata and the full-text index commit atomically. Original binaries are not retained. Review [ingestion methodology and limits](docs/INGESTION.md) before using important documents.

Schema 5 upgrades earlier schemas additively and preserves existing project/model data. Back up local data with the app stopped before upgrades. Migration 2 adds extracted sections, import warnings and FTS5 records; migration 3 adds structured draft artifacts; migration 4 adds claim ledgers and assessment-run records; migration 5 adds draft heads and editorial history. No source replacement/deletion is exposed; revisions preserve prior evidence and decisions.

Final implementation and verification: [Phase 6 report](docs/PHASE_6_COMPLETION.md). Phase 5: [report](docs/PHASE_5_COMPLETION.md). Phase 4: [historical report](docs/PHASE_4_COMPLETION.md). Phase 3: [historical report](docs/PHASE_3_COMPLETION.md). Phase 2: [historical report](docs/PHASE_2_COMPLETION.md).

Phase 3 implements Ollama generation and five versioned document templates; Phase 4 implements provisional claim assessment; Phase 5 implements editorial revisions/review and section regeneration; Phase 6 implements exports and final hardening. The immediate assignment's six-phase plan governs work; the original PRD's longer roadmap remains preserved.

[Architecture](docs/ARCHITECTURE.md) · [Data model](docs/DATA_MODEL.md) · [Security](docs/SECURITY.md) · [Test plan](docs/TEST_PLAN.md) · [Original PRD](docs/PRD.md)

Original `prd.md`, `codex-prompt.md` and `how-2-demo.md` are preserved. The suggested NIST-based finished-product demonstration is future work; no real-source research, factual verification, regulatory approval or independent audit is claimed. Third-party licenses, including PyMuPDF distribution obligations, require review before distribution. No project license has been invented on the owner's behalf.

## Generation limits

See [generation methodology](docs/GENERATION.md). Default context is 32,768 tokens with up to 4,096 output tokens, eight retrieved passages, a 24,000-byte prompt budget, 256 KiB response cap and 180-second inference deadline. Model metadata must report adequate context. A conservative UTF-8 byte budget reserves output and framing space; this is not the model's tokenizer or a guarantee of semantic coverage. Overlarge, truncated, malformed or invented-citation responses are rejected without saving a draft. Long word-count targets may exceed output limits; actual length differences are warned. There is no automatic repair or background retry.

## Claim assessment boundary

[Verification methodology](docs/VERIFICATION.md) explains exhaustive prose-block review units, exact citation/excerpt checks, additional project-scoped retrieval, five automated support categories and immutable run history. New drafts and revisions receive ledgers atomically; older drafts initialize on first review. Human verified requires an explicit named human decision, rationale and selected real source passages. Compound blocks, missing source dates, retrieval gaps and indirect prompt injection remain limitations. No model confidence value is proof.

## Editorial review

See [editorial methodology](docs/EDITORIAL.md) for immutable revision history, optimistic conflicts, human decision records and single-section regeneration. All claims reset on a new revision; historical decisions do not transfer automatically. Human verification records are self-reported editorial judgments, not external proof or authenticated reviewer identities. No automatic history pruning or merging occurs.

## Complete walkthrough and exports

Follow [the full walkthrough](docs/WALKTHROUGH.md) from import through generation, assessment, your own human review, revisions and export. The app includes no later-phase placeholder screens. Export Center prepares a selected revision in four formats, preserves unresolved flags and provides a local download with a fixed safe filename. See [export contract](docs/EXPORTS.md) for snapshot consistency, deterministic formatting and size limits. Export does not verify content. The DOCX remains editable; the JSON manifest retains exact evidence and review history.
