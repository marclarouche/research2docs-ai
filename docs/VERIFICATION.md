# Phase 4 claim assessment methodology

`WorkspaceService.verification` works independently of Streamlit. Evidence Review initializes or reopens a revision-bound ledger and assesses a selected review unit using the saved local model. There is no external verification, web retrieval, cloud fallback or human verification action in Phase 4.

## Claim extraction and coverage

Extraction version `prose-blocks:1.0` creates one conservative claim candidate per nonblank generated prose block. Text is copied exactly, including whitespace. IDs are UUID5 values derived from revision ID, section/block position and text SHA-256. Repeated prose at different positions has distinct IDs. All prose blocks are covered; headings, review notes and model-reported limitations are not separately extracted. A block can include several factual assertions, teaching content or recommendations. This is exhaustive block coverage, not an atomic factual-claim classifier. Full support requires all material assertions in the entire block to be supported; split/edited claim workflows remain Phase 5.

Every newly generated draft receives its ledger, claim rows and initial revision in the same transaction. Existing Phase 3 drafts are initialized on first Evidence Review/service access without changing draft text. Initial status is unsupported / not_assessed, with a pending human review. Citation presence only produces a valid-reference flag, never a supported assessment. Missing original citations remain flagged even if a later AI assessment finds candidate support.

## Deterministic validation

- Original citation aliases must belong to the draft's application-owned evidence mapping. Exact persisted project-scoped passages are resolved before ledger inspection and generation.
- Canonical revision content, artifact content and ledger content hash must match. Claim IDs/text/position/hash and original citation mapping are checked on reopen. A changed revision cannot inherit the previous assessment.
- Assessment replies cannot create authoritative IDs or choose Human verified. Aliases must belong to that assessment's supplied evidence set. Duplicate references and support/contradiction roles for the same passage are rejected.
- Every proposed evidence excerpt must be an exact substring of its stored passage. The application stores half-open offsets and rechecks them on inspection. Exact quotes prove reference integrity, not semantic support or adequate context; full passages remain inspectable.
- Supported/partial results require a supporting excerpt. Fully supported results cannot retain contradictory excerpts. Conflict requires supporting and contradictory excerpts from at least two source documents. Temporal flags require a source excerpt containing an explicit year or version; import timestamp is not publication age.
- Uncertain results become unsupported / inconclusive. Every automated result retains pending human review. Model confidence is not an accepted schema field or proof.

## Retrieval and semantic assessment

Original cited passages are considered first. Up to eight additional FTS5 passages are retrieved from the selected project using at most 64 distinct words from the exact claim. Duplicates are removed. Whole passages, source titles, filenames and page/section locators are packed within the existing generation context/prompt budget. Oversized candidates are omitted with a retained warning. No omitted source is silently represented as assessed.

A fixed system policy (`support-assessment:1.0`) is separate from a JSON envelope containing untrusted claim/source text. The model is asked to compare meaning, scope, negation, numbers, procedures and qualifications. It can propose source-supported, partially supported, unsupported, conflicting evidence or potentially outdated. The application validates references and category prerequisites; it does not independently prove the model's semantic interpretation. Source age/authority cannot be inferred from a filename, import date or ranking. Temporal flags are concerns for a reviewer, not a determination of the currently authoritative requirement.

The local Ollama transport, installed-model/context rechecks, JSON schema, no-tools policy, timeout watchdog, response cap, fixed temperature/seed and safe errors are shared with Phase 3. An assessment is one explicit user/service action; there are no automatic retries or unbounded assess-all jobs. No fitting evidence produces an inconclusive unsupported result without inference. A missing model selection produces a safe error. Malformed output, fake quotes, invalid references and inference failures preserve the previous assessment and record a failed run.

## Persistence, concurrency and review

Schema 4 adds ledger headers, typed claim-unit records and assessment runs, using existing claims/evidence_links. Each assessment run records revision/claim IDs, prompt version/hash, model identifier, parameters and exact candidate evidence. Completed results also retain model digest, timestamp, method, exact excerpts, explanation, pending human status and warning flags. Run records preserve previous successful assessments; failed runs do not replace the current one. Raw invalid model responses and exception details are not saved.

Publication atomically updates claim/unit records and evidence relationships and completes the run. The displayed assessment version must still match; concurrent results cannot overwrite each other. Revision content and packed source passages are checked again after inference. Interrupted processes may leave started runs; there is no background recovery or guaranteed server-side model cancellation. No material editing or source replacement/deletion API exists yet. New revisions must derive fresh claim IDs and require reassessment; Phase 5 must preserve this boundary.

All support statuses are **AI-assisted, source-relative and pending human review**. A source-supported record does not establish objective truth, trustworthy sourcing, completeness or successful human verification. Candidate retrieval may miss contradictory passages, compound blocks may hide unsupported details, and exact quotes can be irrelevant or cherry-picked. Inspect full sources and qualifications. No human decision, review rationale, certification or independent audit is fabricated. Local evidence, drafts and assessment history remain unencrypted, excluded from Git.
