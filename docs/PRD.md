Research2Docs AI
AI Technical Research & Content Transformation Studio
Transforms source material, research papers, and technical specifications into structured explainers, tutorials, FAQs, and audience-specific content, preserving source references and flagging claims requiring verification.
Demonstrates: Research, instructional writing, complex subject explanation, content strategy, editorial judgment.

esearch2Docs AI PRD
Project 5 of 5 | Technical Writing & AI Portfolio Series
Product Requirements Document (PRD) v1.0 | Proposed implementation
AI Technical Research & Content Transformation Studio
Turning complex technical source material into accurate, accessible, and traceable documentation.
Research2Docs AI will be the final application in your five-project technical writing portfolio. I recommend positioning it as an AI-assisted technical research and editorial workbench, rather than another general-purpose content generator.
The distinguishing feature should be that it does more than rewrite material. It analyzes technical documents, identifies important claims, preserves source references, adapts explanations for different audiences, and flags statements that cannot be adequately supported.
This project can showcase five professional competencies: technical research, instructional design, complex subject explanation, content strategy, and editorial judgment.
We should also follow the local-first approach established for your other AI projects: Python, Ollama, a simple Streamlit interface, and an independent processing engine that could eventually support a native desktop application.
Part 1. Product Requirements Document
1. Product overview
Attribute	Specification
Product name	Research2Docs AI
Version	1.0
Category	Technical research and documentation
Deployment	Local-first desktop-hosted web application
AI backend	Ollama, local models
Primary interface	Streamlit
Primary language	Python
Storage	Local SQLite and project files
Intended users	Technical writers, researchers, educators, cybersecurity professionals
Network requirement	No internet required for core operations
Licensing	Portfolio demonstration, initially
Development cost	No recurring API or hosting fees required
2. Problem statement
Technical writers frequently receive information scattered across lengthy specifications, research papers, implementation guides, white papers, and standards documents.
Producing useful documentation from these sources requires several distinct activities.
The writer must identify relevant information, reconcile overlapping or conflicting statements, determine what is supported by evidence, translate technical language for the intended reader, and organize everything into an appropriate instructional format.
Generic AI writing assistants can accelerate drafting, but they may omit important qualifications, misinterpret specifications, produce unsupported conclusions, or generate citations that do not exist.
Research2Docs AI addresses this problem through source-grounded transformation and human editorial oversight.
It is not intended to replace the technical writer. It is designed to make the research, drafting, and verification process more transparent and repeatable.
3. Product objectives
The v1 application shall:
1. Accept and analyze multiple technical source documents within a project.
2. Extract relevant concepts, factual statements, definitions, and technical procedures.
3. Produce five types of structured technical content.
4. Transform the same research for audiences with different knowledge levels.
5. Maintain traceable relationships between generated claims and source material.
6. Identify unsupported, ambiguous, conflicting, or potentially outdated claims.
7. Provide a human editorial review workflow.
8. Export professional documentation while retaining citations and unresolved verification warnings.
9. Operate locally without requiring cloud AI services.
10. Preserve saved projects and revision history across application restarts.
4. Target users
User	Primary use case
Technical writer	Transform complex specifications into understandable documentation
Cybersecurity analyst	Explain technical vulnerabilities, controls, and mitigation processes
GRC professional	Convert regulatory and framework material into educational guidance
Software developer	Create tutorials and FAQs from implementation documentation
Researcher	Synthesize and explain research findings
Instructor	Adapt technical information into learning material
5. Functional requirements
FR-01. Project management and source ingestion
Users shall be able to create, rename, reopen, archive, and delete local research projects.
Supported input formats for v1:
Format	Requirement
PDF	Required, text-based
DOCX	Required
Markdown	Required
TXT	Required
HTML	Required, local files
Web URL	Future release
Scanned PDF with OCR	Future release
The application shall preserve a source record containing the filename, available document title, author metadata if present, source URL if supplied manually, import timestamp, and SHA-256 content hash.
Source identifiers must remain stable, even when sources are removed from an active project or the original filename changes.
When bibliographic metadata is incomplete, the application must not fabricate an author, publisher, publication date, or DOI.
Acceptance criteria: A user can import at least five supported documents into one project, review extraction results, and reopen the project without losing its source metadata.
FR-02. Research extraction and source indexing
The research engine shall process imported material and extract readable text while preserving source locations.
It shall identify document headings, sections, paragraphs, definitions, relevant technical claims, and potential procedural steps.
PDF citations should use page numbers where extraction permits. DOCX, Markdown, and text citations should use stable section or paragraph locators wherever possible.
Extracted passages shall receive permanent IDs and be stored separately from AI-generated interpretations.
Acceptance criteria: A generated statement can reference a stored source passage, and the user can inspect that passage in a source evidence panel.
FR-03. Content transformation engine
Five document types will be included in v1.

Technical explainer
Defines a concept, explains its importance, describes the mechanism, and provides examples, implications, and limitations.



Step-by-step tutorial
Produces prerequisites, ordered instructions, expected results, troubleshooting guidance, and validation steps. Missing procedural details must be flagged.



Frequently asked questions
Creates questions and concise, evidence-grounded answers, with source references.



Instructional guide
Produces learning objectives, conceptual explanations, examples, knowledge checks, and a conclusion.



Executive technical brief
Summarizes technical findings, operational implications, risks, limitations, and recommended next steps without overstating evidence.



Each output type must have a separate, version-controlled prompt template and structured output schema.
Users shall be able to select a content format, word-count target, document title, audience, and level of technical detail.
FR-04. Audience adaptation
The application shall support the following audience profiles:
Audience	Writing treatment
General public	Everyday language and clearly explained concepts
Beginner technical	Basic terminology and additional context
Intermediate technical	Practical details with some assumed foundational knowledge
Advanced technical	Detailed mechanisms, precise terminology, and assumptions
Executive	Concise explanations focused on impact, decisions, and limitations
Custom	User-defined background, terminology, and learning objectives
Critical editorial requirement: Changing the intended audience must not silently change the underlying factual meaning.
A beginner explanation can simplify terminology, but it should not remove safety warnings, technical limitations, or material qualifications.
FR-05. Claim verification and evidence mapping
This is the most important functional requirement and the principal differentiator.
Research2Docs AI shall maintain a structured claim ledger.
Each meaningful factual claim in generated output shall have a corresponding verification record.
Proposed claim review panel
Claim C-014
“The proposed process requires annual independent security assessments.”
Needs verification
Source S-003, section 4.2

The passage discusses periodic assessments but does not explicitly establish an annual requirement.

Human editorial review required


Claim assessment statuses:
Status	Meaning
Source-supported	Evidence passage appears to directly support the claim
Partially supported	Some elements are supported, but qualifications or details are missing
Unsupported	No adequate evidence found in the provided source collection
Conflicting evidence	Two or more sources disagree materially
Potentially outdated	The claim is time-sensitive and the available source may no longer be current
Human verified	An editor reviewed and accepted the claim, with a recorded rationale
A source-supported status is not an independent confirmation of truth. It only means the supplied documentation supports the statement.
The application must never claim to have verified a statement against external sources unless an actual external verification mechanism was used.
The assessment engine shall use both deterministic rules and AI-assisted evaluation. It shall reject invalid passage references, flag missing citations, and present questionable claims for human review.
All claim statuses should include an explanation and, where applicable, supporting and contradictory passages.
Acceptance criteria: Every generated draft has a claim ledger, no citation points to a nonexistent source passage, and unsupported claims remain visibly flagged until reviewed.
FR-06. Source comparison
The application shall compare source passages addressing the same topic.
It should identify potential agreement, disagreement, missing information, and differences in publication dates.
For example, if an older standard and a newer standard specify different requirements, the application should surface the discrepancy without assuming which document is authoritative.
FR-07. Editorial workbench
Users shall be able to review a generated document and manually revise its content.
Required capabilities include saving draft revisions, displaying source citations, inspecting supporting passages, reviewing claim flags, resolving flags with an explanation, and regenerating a selected section.
A human-edited claim must be rechecked if its meaning changes. Previously accepted verification decisions must not automatically carry over to materially revised claims.
FR-08. Document export
The application shall support:
Format	v1
Markdown	Required
Microsoft Word DOCX	Required
HTML	Required
PDF	Future release
JSON evidence manifest	Required
The JSON evidence manifest will preserve the source inventory, content hashes, claim ledger, citation relationships, verification decisions, model identifier, and generation timestamp.
Exports must not quietly remove unresolved verification flags. The user should be able to export a visibly labeled draft containing them.
FR-09. Local AI management
The application shall discover locally installed Ollama models, allow the user to select a model, test model connectivity, and report configuration errors.
Model execution shall occur locally through a configurable loopback endpoint.
No external API key shall be required.
FR-10. Project and revision persistence
Projects, imported-source metadata, extracted passages, drafts, revision history, and claim review records shall survive restarts.
SQLite transactions shall protect against partially saved edits. Atomic file-writing practices should be used for exported artifacts.
6. Nonfunctional requirements
Security: Bind the application and model service to loopback by default, prevent path traversal, sanitize displayed HTML, limit file sizes, validate uploads by content, and prevent arbitrary execution of source-supplied instructions.
Privacy: No telemetry, advertising SDKs, automatic web requests, or cloud model fallbacks.
Reliability: Errors shall be presented as useful non-sensitive messages. Detailed exceptions belong in local diagnostic logs.
Maintainability: Research and generation logic must remain independent of Streamlit.
Testability: Extraction, evidence matching, claim validation, transformations, persistence, and exports must have automated tests.
Accessibility: Use readable contrast, descriptive labels, navigable controls, and visible status indicators that do not rely on color alone.
Licensing: Verify third-party dependency licenses and distribution obligations before public release.
7. Out-of-scope functionality for v1
To keep the final portfolio project achievable, I recommend excluding autonomous internet research, external search engine integration, collaborative multiuser editing, cloud LLM services, fine-tuning, live document synchronization, automated publishing, and regulatory compliance certification.
These are possible enhancements, not requirements for demonstrating professional technical writing skills.
8. Primary user workflow
1

Create research project

Project metadata and editorial objective

2

Import technical sources

PDF, DOCX, Markdown, TXT, HTML

3

Extract and index

Retain source passages and stable locators

4

Choose content and audience

Format, knowledge level, length and tone

5

Generate grounded draft

Local Ollama model

6

Validate evidence

Claim ledger, citations, conflicts and warnings

7

Human editorial review

Revise and document decisions

8

Export deliverables

DOCX, Markdown, HTML and evidence JSON


9. Definition of done
Research2Docs AI v1 will be considered complete when a user can import several technical documents, generate a structured and audience-appropriate article or tutorial, inspect the evidence supporting its claims, correct unsupported assertions, save the project, and export the completed document with an accompanying evidence manifest.
It must also pass the automated test suite and complete a documented end-to-end demonstration without internet access.

Part 2. Recommended Technical Stack
I recommend Python + Streamlit + Ollama + SQLite, using the same broad architectural pattern as DocAudit AI and KnowledgeBridge AI.
This provides continuity across your portfolio while making it easier to maintain, test, and demonstrate the applications.
1. Technology selection
Component	Technology	Purpose
Programming language	Python 3.12+	Primary development
UI	Streamlit	Local browser interface
AI runtime	Ollama	Local inference
LLM client	Ollama Python SDK	Model communication
Data validation	Pydantic v2	Structured models and AI output validation
PDF extraction	PyMuPDF	Text and page references
Word extraction	python-docx	DOCX input
Markdown processing	markdown-it-py	Markdown parsing
HTML parsing	Beautiful Soup	Local HTML input
Text retrieval	SQLite FTS5	Local full-text search
Persistence	SQLite	Project and review data
Word export	python-docx	Editable DOCX generation
HTML export	Jinja2	Controlled rendering
HTTP client	httpx	Local Ollama connectivity
Testing	pytest	Unit and integration testing
Code quality	Ruff	Linting and formatting
Type checking	mypy	Static checks
Dependency auditing	pip-audit	Python dependency vulnerability checks
Secret detection	Gitleaks	Repository secret scanning
The capabilities of Streamlit, PyMuPDF, and Pydantic are supported by their documentation. 

Streamlit Docs
+2



For v1, SQLite FTS5 should be sufficient for document retrieval. This avoids a vector database dependency and makes the application easier to distribute. Semantic embeddings could be added later if evaluation shows they materially improve retrieval quality.
2. Suggested AI model strategy
Rather than hard-coding a particular model, I recommend an Ollama model-selection interface.
The application can maintain three configurable roles:
Role	Responsibility
Research model	Extract concepts, summarize passages, and identify candidate claims
Writing model	Transform evidence into structured content
Verification model	Assess whether claims are adequately supported
All three roles can initially use the same local model.
Separate models should remain optional because running several concurrently could unnecessarily increase memory consumption.
Model choices and performance benchmarks should be established through actual testing on your development hardware. I do not have a verified benchmark demonstrating which model performs best for this exact workflow.
3. Proposed system architecture
Streamlit User Interface
Projects, sources, editor, review, export

Application Service Layer
Workflow orchestration, validation and persistence

Document Ingestion
Parsing and indexing


Research Engine
Retrieval and source mapping


Transformation Engine
Draft generation


Evidence Validator
Claims and citations




Ollama
Local LLM


SQLite
Projects and evidence



Export Layer
Markdown, DOCX, HTML, JSON


The key architectural decision is to make Streamlit a replaceable presentation layer, not the application itself.
The underlying Python services must work through ordinary method calls without Streamlit installed. This preserves the option of replacing the interface with a native application in the future.
4. Core data model
I recommend these primary entities:
Entity	Purpose
Project	Research project and editorial settings
SourceDocument	Imported document, metadata, and hash
SourcePassage	Extracted text with stable locator
ResearchNote	Extracted concept or observation
DocumentDraft	Generated document and parameters
DraftRevision	Saved content snapshot
Claim	Individual factual assertion
ClaimEvidence	Relationship between a claim and passages
ReviewDecision	Human editorial decision and rationale
GenerationRun	Model, prompt version, and generation metadata
Relationships should support multiple sources per project, multiple drafts per project, multiple revisions per draft, and multiple evidence passages per claim.
Every revision should preserve its associated claim assessments. Updating a document should not silently overwrite an earlier verification record.
5. Research integrity pipeline
I recommend a staged process rather than one large prompt that asks an LLM to do everything.
Stage A: Deterministic extraction
Parse the source and assign stable source IDs, passage IDs, and location metadata.



Stage B: Evidence retrieval
Select relevant passages using full-text retrieval and optional user-selected source sections.



Stage C: Structured drafting
Generate the requested document type with explicit passage references and claim records.



Stage D: Evidence validation
Verify that references exist, assess claim support, and identify contradictory or missing evidence.



Stage E: Human review and export
Preserve editorial decisions and generate documentation and evidence records.



A particularly important technical constraint: the LLM should never be the authoritative source of citation identifiers.
The system should give the model a restricted set of valid passage IDs and independently validate every citation it returns. A real ID alone is insufficient: the content of that passage must also support the attributed claim.
6. Security design
This is a local application, but local execution does not eliminate security risks.
Imported research material should be treated as untrusted data. PDFs, DOCX files, and HTML documents can contain instructions aimed at manipulating an AI system.
For example, an imported document could contain text telling the model to ignore its verification rules or insert an unsupported statement into the final report.
OWASP explicitly addresses indirect prompt injection through external content and emphasizes trust boundaries and downstream validation. 

OWASP Foundation
+1



The implementation should enforce:
1. No execution of instructions contained in research documents.
2. No model-controlled shell, filesystem, network, or tool access.
3. Strict source ID validation and constrained file access.
4. File-type validation, resource limits, and safe temporary-file handling.
5. Safe rendering of document and AI-generated HTML.
6. No sensitive document text in routine diagnostic logs.
7. No automatic cloud model fallback or internet retrieval.
8. Dependency auditing, secret scanning, and secure configuration defaults.
9. Generic user-facing error messages, with sanitized local diagnostic logs.
10. Explicit user control over permanent deletion of project content.
7. Suggested repository layout
research2docs-ai/
├── README.md
├── LICENSE
├── pyproject.toml
├── .gitignore
├── .env.example
├── .streamlit/
│   └── config.toml
├── docs/
│   ├── PRD.md
│   ├── ARCHITECTURE.md
│   ├── SECURITY.md
│   ├── DATA_MODEL.md
│   └── TEST_PLAN.md
├── src/
│   └── research2docs/
│       ├── __init__.py
│       ├── core/
│       │   ├── config.py
│       │   ├── models.py
│       │   ├── errors.py
│       │   └── logging.py
│       ├── ingestion/
│       │   ├── pdf_parser.py
│       │   ├── docx_parser.py
│       │   ├── markdown_parser.py
│       │   ├── html_parser.py
│       │   └── text_parser.py
│       ├── research/
│       │   ├── indexing.py
│       │   ├── retrieval.py
│       │   └── extraction.py
│       ├── generation/
│       │   ├── ollama_client.py
│       │   ├── prompt_registry.py
│       │   └── transformer.py
│       ├── verification/
│       │   ├── claim_extractor.py
│       │   ├── evidence_mapper.py
│       │   └── claim_validator.py
│       ├── editorial/
│       │   ├── revisions.py
│       │   └── reviews.py
│       ├── storage/
│       │   ├── database.py
│       │   ├── repositories.py
│       │   └── migrations.py
│       ├── export/
│       │   ├── docx_export.py
│       │   ├── markdown_export.py
│       │   ├── html_export.py
│       │   └── evidence_export.py
│       └── services/
│           ├── project_service.py
│           └── workflow_service.py
├── ui/
│   ├── app.py
│   ├── pages/
│   └── components/
├── prompts/
│   ├── research_extraction.md
│   ├── technical_explainer.md
│   ├── tutorial.md
│   ├── faq.md
│   ├── instructional_guide.md
│   ├── executive_brief.md
│   └── claim_verification.md
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── security/
│   └── fixtures/
└── scripts/
    └── smoke_test.py


8. Development roadmap
Phase	Deliverable	Completion gate
1. Foundation	Repo, configuration, models, SQLite, tests	Persistent project operations work
2. Ingestion	Five source parsers, passage IDs, search	Evidence passages retrievable
3. AI integration	Ollama client, templates, generation	Structured draft from real sources
4. Verification	Claim ledger, evidence mapping, flags	Unsupported claims are identified
5. Editorial	Review UI, revisions, conflict display	Human changes are tracked
6. Export	DOCX, Markdown, HTML, JSON	Evidence retained in outputs
7. Hardening	Security testing, docs, demonstration	Offline end-to-end test passes
I would use functional acceptance gates rather than promise a particular development duration. Local model performance, PDF extraction quality, and claim validation accuracy all require empirical testing.

Part 3. ChatGPT Codex Master Development Prompt
The following prompt is designed to give Codex the complete product direction while preventing it from attempting the entire application in a single unstructured implementation.
It instructs Codex to establish the architecture, implement a functional first milestone, document its work, and continue through testable phases.