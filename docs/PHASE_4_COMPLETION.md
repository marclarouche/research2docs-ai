# Research2Docs AI — Phase 4 completion

Completed October 17, 2026. Phase 4 adds deterministic citation/claim ledgers, provisional local AI support assessment, revision-bound evidence relationships and a working Evidence Review page. Human verification decisions, editorial editing, saved edited revisions, section regeneration and exports remain later phases.

## Delivered

- Exhaustive conservative prose-block claim candidates, copied exactly from each revision with stable application-derived IDs, text/content hashes, section/block locations and original citation relationships. Compound blocks are reviewed as a whole; this is not an atomic factual-claim classifier. Headings and model review notes/limitations are not separately assessed.
- New drafts create their initial ledger and claims atomically with the draft/revision/run. Existing Phase 3 drafts initialize on first review without rewriting saved draft content.
- Deterministic original-citation checks, exact stored-passage resolution and pending unsupported/not-assessed initial records. Citation presence alone does not grant support.
- Bounded project-scoped retrieval beyond original citations, whole-passage prompt packing and local structured assessment with a fixed versioned instruction/data boundary.
- Five automated proposals: source-supported, partial, unsupported, conflicting and potentially outdated. Model confidence and Human verified are rejected schema values/fields. Uncertainty becomes unsupported/inconclusive.
- Exact alias/excerpt validation with persisted offsets, supporting/contradictory relationships, multi-document conflict prerequisites and explicit date/version excerpts for temporal flags. Full source passages remain inspectable.
- Current claim results plus preserved assessment-run history, model/digest, prompt version/hash, request parameters, exact candidate evidence, explanation, method/time, original warnings and pending human status.
- Transactional publication and optimistic assessment versions. A stale competing result cannot replace a newer one. Revision/evidence changes stop reuse; failed inference/validation preserves the previous result.
- Evidence Review selection, ledger counts, assessment action, current status/explanation, exact source excerpts, full passages, original warnings and provenance. Dynamic content renders as inert text. A supported model proposal still shows provisional/pending labels.

Key additions: `verification/models.py`, `extraction.py`, `prompts.py`, `services/verification_service.py`, `storage/verification_repository.py`, `ui/evidence_review.py` and controlled verification tests. Updated migrations/database, draft publication, canonical revision checks, composition, settings/config, exact Claim text, UI shell/studio and required development docs. Migrations 1–3 and the original user documents remain unchanged.

## Actual checks

| Check | Result |
|---|---|
| Full deterministic pytest | **174 passed**, 1 optional local discovery test deselected; 5 existing upstream SWIG deprecation warnings |
| Strict mypy | Passed, 39 source/UI files |
| Ruff lint / formatting | Passed |
| Dependency integrity | `pip check`: no broken requirements; no dependencies added or changed |
| pip-audit | No known vulnerabilities across 75 entries; unpublished local `research2docs-ai` skipped because it is not on PyPI |
| Gitleaks | Exit 0, no leaks in the final publishable-source snapshot; runtime data/caches/outputs excluded |
| Existing smoke script | Project lifecycle and five-format import/search/exact PDF page-2 evidence/reopen passed |
| Controlled assessment coverage | All five categories, missing citations, ambiguity, invented references/quotes, duplicate roles, explicit temporal basis, rejected human/confidence output, failure preservation, exact offsets, revision binding, transactions and concurrency |
| Persistence / migration | Legacy initialization, schema 4 rollback, generation+ledger atomicity, reassessment history and fresh-process reopen without Streamlit/network |
| UI | Assessment/save/reopen, inert model markup, pending labels and stale form rejection passed; presentation-label refinement checked separately |

The real installed `qwen3-vl:4b-instruct` assessed the first Orion Archive prose block and returned a source-supported proposal with eight exact supporting excerpts. The result reopened successfully in Evidence Review, version 1, with **human review pending**. Draft ID `1e47d324-1e64-4193-a249-6932cf2a0b7b`; claim ID `4ff87315-cbd9-5ef0-95a5-98828f161333`. The other three units remain not assessed. This demonstrates operation on fictional sources, not semantic accuracy, independent verification or a benchmark.

Before the live schema 3→4 upgrade, a SQLite backup was saved in ignored `work/phase4-before-upgrade.sqlite3`. Every existing project, preference, source, section, passage, import warning, FTS, draft, revision, structured artifact and generation-run row compared equal after upgrade. Original `prd.md`, `codex-prompt.md` and `how-2-demo.md` hashes also matched their prior values. Only Research2Docs on port 8503 was restarted. No commit, remote configuration or push was requested or performed.

## Security choices and limits

Sources and model outputs remain untrusted. Separate application instructions and JSON data, no tools/execution/fetches, loopback-only installed-model checks, response/context bounds and the existing deadline watchdog continue to apply. Exact excerpts and citation identities establish reference integrity, not entailment, authority or truth. Retrieval may miss counterevidence; model conclusions can be wrong or affected by prompt injection. Temporal detection is a provisional concern based on an explicit date/version excerpt, not proof of obsolescence or authority. All statuses retain pending human review.

Default assessment retrieval adds up to eight FTS matches to original citations, packing whole passages inside the existing 24,000-byte / 32,768-context-token budget with 4,096 output tokens, 256 KiB response cap and 180-second inference deadline. Omitted candidates remain flagged. There is no automatic retry/assess-all loop, global concurrency budget, guaranteed server cancellation or background recovery of interrupted started runs. Local drafts, evidence and history remain unencrypted. No editing or source replacement/deletion feature exists yet; Phase 5 must create fresh claim identities and assessments for changed revisions.

Read [verification methodology](VERIFICATION.md), [data model](DATA_MODEL.md), [security](SECURITY.md) and [test plan](TEST_PLAN.md). Local audit JSON: `/private/tmp/research2docs-phase4-audit.json`. Screenshots and redacted scan reports are in ignored `outputs`.

Next phase: **Phase 5 editorial workspace**, after separate authorization. Human decisions and section regeneration have not started.
