# CODEX MASTER DEVELOPMENT PROMPT

## Project: Research2Docs AI v1.0

You are a senior Python software engineer, application security architect, and AI systems developer.

Your assignment is to design and implement **Research2Docs AI**, a local-first AI technical research and content transformation application.

The application demonstrates professional technical writing capabilities by transforming technical research papers, specifications, manuals, and reference material into structured, audience-specific documentation while preserving source citations and flagging unsupported claims.

This is a real, functioning software project, not a mockup.

## 1. Product mission

Build a local application that allows a technical writer to:

1. Create a research project.
2. Import multiple source documents.
3. Extract and index technical content.
4. Select a document type and intended audience.
5. Generate a structured document using a local Ollama model.
6. Inspect supporting evidence for factual claims.
7. Identify unsupported, ambiguous, conflicting, or potentially outdated statements.
8. Edit and review generated content.
9. Preserve revisions and editorial decisions.
10. Export finished documents and evidence records.

The application's central principle is:

**Never invent a source, citation, statistic, quotation, standard, technical requirement, or verification result.**

When available documentation does not support a claim, explicitly mark the claim as requiring verification.

## 2. Core architecture

Use Python 3.12 or later, with compatible stable dependency releases.

Use the following components:

* Streamlit for the local browser interface.
* Ollama for local LLM inference.
* Pydantic v2 for typed models and structured validation.
* SQLite for persistent project data.
* SQLite FTS5 for local passage retrieval.
* PyMuPDF for text-based PDF extraction.
* python-docx for DOCX extraction and export.
* markdown-it-py for Markdown parsing.
* Beautiful Soup for local HTML parsing.
* Jinja2 for controlled HTML export.
* pytest for testing.
* Ruff and mypy for code quality.
* pip-audit and Gitleaks for security checks.

Use an src-based Python package structure.

CRITICAL ARCHITECTURAL REQUIREMENT:

The complete research, ingestion, generation, verification, persistence, and export engine must function independently of Streamlit.

Streamlit is strictly the presentation layer.

Do not import Streamlit inside core or service modules.

Do not place business logic directly inside Streamlit pages.

All application capabilities should be accessible through ordinary Python service interfaces.

Do not introduce FastAPI, a vector database, cloud infrastructure, or a background queue unless a concrete requirement makes them necessary.

## 3. Local-first requirements

The application must operate without an internet connection after its dependencies and local Ollama models have been installed.

Do not integrate cloud LLM APIs.

Do not add telemetry, analytics, remote logging, automatic web retrieval, or cloud fallback behavior.

Use a configurable Ollama loopback endpoint, defaulting to localhost.

Provide local model discovery and model selection.

Gracefully handle unavailable models, context limits, invalid structured responses, inference errors, and Ollama connection failures.

The application must never silently switch to a remote service.

## 4. Source ingestion

Implement import support for:

* PDF, text-based only.
* DOCX.
* Markdown.
* TXT.
* Local HTML.

Do not implement OCR or web scraping in v1.

Create a deterministic ingestion pipeline.

Preserve source metadata when available, including filename, title, author, import time, source type, optional manually supplied URL, and SHA-256 hash.

Every extracted passage must have:

* A stable passage ID.
* Parent source ID.
* Text.
* Page or section locator when available.
* Extraction method.
* Original ordering.
* Optional heading information.

Use persisted passage records as the authoritative evidence source.

Reject unsupported or malformed files safely.

Place limits on file size, total extracted text, processing time, and resource consumption.

Do not trust filename extensions alone.

## 5. Document generation

Implement five output types:

1. Technical explainer.
2. Step-by-step tutorial.
3. FAQ.
4. Instructional guide.
5. Executive technical brief.

Create a separate versioned prompt template for each type.

The user must be able to specify:

* Document type.
* Intended audience.
* Working title.
* Approximate word count.
* Technical depth.
* Additional editorial instructions.

Supported audiences:

* General public.
* Beginner technical.
* Intermediate technical.
* Advanced technical.
* Executive.
* Custom audience.

Generate content using retrieved, source-grounded evidence.

Use Pydantic schemas to validate structured model responses.

Do not allow the model to fabricate or create authoritative source IDs.

The application must validate every returned citation against stored passages.

When an output cannot be supported, include an explicit warning rather than silently inventing an explanation.

For tutorials, do not invent commands, procedural steps, prerequisites, or expected results that are not supported by the source material without clearly marking them for review.

## 6. Claim verification engine

This is the application's most important feature.

Implement a structured claim ledger.

Each factual claim should have:

* Unique claim ID.
* Claim text.
* Draft and revision reference.
* Supporting passage IDs.
* Contradictory passage IDs, if present.
* Assessment status.
* Explanation of assessment.
* Human review status and rationale.
* Assessment method and timestamp.

Support these assessment categories:

* Source-supported.
* Partially supported.
* Unsupported.
* Conflicting evidence.
* Potentially outdated.
* Human verified.

A source-supported status means the source material appears to support the claim. It does not establish that the claim is objectively true.

Implement deterministic citation validation first.

Then implement AI-assisted semantic support assessment.

Never treat an LLM's confidence statement as proof of factual correctness.

When the system cannot reach a reliable assessment, default to requiring human review.

Preserve unresolved warnings when saving or exporting drafts.

The claim ledger must link back to actual source passages and allow a reviewer to inspect the evidence.

When a claim is materially edited, invalidate its prior automated assessment and require reassessment.

## 7. Research and retrieval

Use SQLite FTS5 for deterministic full-text retrieval.

Build a local passage index when documents are imported.

Retrieve relevant passages before constructing generation prompts.

Maintain passage IDs throughout retrieval, generation, and verification.

Do not assume that retrieved passages are authoritative merely because they appear relevant.

The model must distinguish between retrieved source statements and its own interpretations.

Avoid a complex agent framework.

Use straightforward service orchestration with explicit steps and typed results.

## 8. Editorial interface

Build a professional, clean Streamlit application with the following sections:

### Dashboard
Display existing projects, recent drafts, unresolved verification issues, and local Ollama status.

### Project Workspace
Create projects, edit metadata, manage imported sources, and configure editorial goals.

### Source Explorer
Show indexed documents, extracted passages, source locations, and search results.

### Document Studio
Choose document type, audience, title, length, and technical depth. Generate and revise structured documents.

### Evidence Review
Show claim statuses, supporting excerpts, conflicting evidence, and reviewer decisions.

### Export Center
Export Markdown, DOCX, HTML, and a JSON evidence manifest.

### Settings
Select local model, configure local storage, and manage application preferences.

Use Streamlit session state only for temporary interface state.

Persist important project data and editorial changes through application services backed by SQLite.

## 9. Persistence and versioning

Design a relational SQLite schema for projects, source documents, source passages, drafts, revisions, claims, evidence links, editorial decisions, and generation runs.

Enable foreign keys.

Use transactions for multi-record updates.

Use schema migrations rather than silently rebuilding existing databases.

Do not automatically delete project data during startup.

Store generation metadata, including model identifier, prompt template version, relevant parameters, and timestamp.

Document the schema in docs/DATA_MODEL.md.

## 10. Exports

Implement:

* Markdown.
* DOCX.
* HTML.
* JSON evidence manifest.

Use safe, deterministic formatting.

Preserve citations and distinguish unresolved verification flags from reviewed claims.

Ensure DOCX exports remain editable.

Avoid rendering untrusted raw HTML.

Do not mark a draft as fully verified simply because it was exported.

## 11. Security requirements

Apply defensive secure-development practices consistent with OWASP guidance.

Specifically:

* Treat every imported document as untrusted data.
* Defend against direct and indirect prompt injection.
* Separate application instructions from source text.
* Never execute model-generated commands.
* Never follow operational instructions embedded in source documents.
* Validate uploaded file types and content.
* Enforce local project-directory boundaries.
* Prevent directory traversal and arbitrary file writes.
* Escape or sanitize HTML where appropriate.
* Validate structured model output.
* Restrict network activity to authorized local endpoints.
* Use safe temporary-file handling.
* Apply reasonable upload and resource limits.
* Never log full document contents by default.
* Avoid exposing internal stack traces to users.
* Keep troubleshooting logs locally, with sensitive information excluded or redacted.
* Audit dependencies and scan for committed secrets.

Create docs/SECURITY.md describing threats, trust boundaries, mitigations, residual risks, and the local deployment security model.

Do not claim the product is formally certified or independently audited.

## 12. Error handling

Create typed internal exceptions.

Show user-friendly messages such as:

"Unable to process this document. Review the file and try again."

"Ollama is unavailable. Verify that the service is running."

"Insufficient source evidence was found to support this statement."

Write diagnostic information to local logs without exposing unnecessary sensitive content.

Never silently discard failed document parsing, generation, or validation steps.

## 13. Testing requirements

Use pytest.

Provide deterministic unit tests without requiring a running Ollama server.

Mock model responses for AI-dependent unit tests.

Create test fixtures for source documents and claim evidence.

Tests must cover:

* Project persistence.
* Source extraction.
* Stable passage identifiers.
* Citation integrity.
* Invalid citation rejection.
* Unsupported claim detection.
* Conflicting source evidence.
* Prompt injection attempts.
* Malformed documents.
* File path traversal.
* Model unavailability.
* Invalid model responses.
* Editorial revision handling.
* Export integrity.
* Database persistence across restarts.

Create an optional local Ollama integration test, clearly separated from the normal unit test suite.

Tests must not depend on external network services.

## 14. Development documentation

Maintain:

* README.md.
* docs/PRD.md.
* docs/ARCHITECTURE.md.
* docs/DATA_MODEL.md.
* docs/SECURITY.md.
* docs/TEST_PLAN.md.

The README must explain installation, Ollama configuration, launching Streamlit, supported file types, known limitations, testing, and how to reproduce a complete demonstration.

Use realistic, clearly labeled example data.

Never invent customer deployments, independent audits, performance benchmarks, or regulatory approvals.

## 15. Implementation strategy

Build this application incrementally.

### Phase 1: Foundation

Create the repository structure, dependency configuration, typed domain models, configuration management, SQLite persistence, basic Streamlit shell, and automated tests.

### Phase 2: Document ingestion

Implement supported file parsers, metadata extraction, stable passage IDs, source storage, and FTS5 retrieval.

### Phase 3: AI transformation

Implement Ollama connectivity, structured generation, audience profiles, document templates, and working drafts.

### Phase 4: Claim verification

Implement claim extraction, evidence relationships, citation validation, review statuses, and support assessment.

### Phase 5: Editorial workspace

Implement saved revisions, human verification decisions, source evidence inspection, and section regeneration.

### Phase 6: Export and hardening

Implement supported exports, security tests, end-to-end testing, and final documentation.

Every phase must result in working, testable code.

Avoid placeholder features that appear functional but have no real implementation.

## 16. Immediate first assignment

Begin implementing Phase 1 now.

First inspect the repository to determine whether any existing files need to be preserved.

Then:

1. Establish the recommended repository structure.
2. Configure the Python project and dependencies.
3. Implement Pydantic domain models.
4. Implement configuration management.
5. Establish the SQLite schema and migration mechanism.
6. Implement functional project creation, listing, editing, and reopening.
7. Build the initial Streamlit dashboard and project workspace.
8. Add a local Ollama connectivity check.
9. Add deterministic unit tests.
10. Create the initial development documentation.

Run the available tests and static checks.

Fix failures introduced by your implementation.

Do not claim tests passed unless they were actually executed successfully.

Provide a concise completion report containing:

* Files created or modified.
* Features implemented.
* Tests executed and their results.
* Security decisions.
* Known limitations.
* Remaining requirements.
* Recommended next implementation step.

Do not implement later phases before the foundational architecture is working and tested.

**Begin coding Phase 1.**