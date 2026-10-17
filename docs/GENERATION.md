# Phase 3 generation methodology

Document Studio uses ordinary `WorkspaceService.generation` APIs, independently of Streamlit. A generation request contains editorial goals and a bounded keyword research question. The selected model is an operator preference saved through Settings. No matching evidence, no selected model, or an over-budget prompt produces a safe error before inference.

## Formats and audience profiles

Five packaged application-owned templates live in `src/research2docs/generation/templates`, each at version 1.0. Every format has a distinct schema with its ordered section kinds, validated again after the model returns:

| Type | Ordered sections |
|---|---|
| Technical explainer | Concept, mechanism, examples, limitations |
| Step-by-step tutorial | Prerequisites, steps, expected results, troubleshooting, validation |
| FAQ | Concepts, practical questions, limitations; use question headings |
| Instructional guide | Objectives, concepts, examples, knowledge checks, conclusion |
| Executive technical brief | Findings, implications, risks, limitations, next steps |

Each section contains a heading and text blocks with citation-alias arrays and review notes. Missing procedural details must be stated as missing rather than invented. Additional editorial instructions are bounded preference data. General public, beginner, intermediate, advanced, executive and custom audiences have explicit writing treatments. Preserving factual meaning and qualifications is required in the prompt but is not semantically assessed in this phase.

## Evidence and context

Project-scoped FTS5 keyword retrieval selects up to eight passages. Whole exact passages are packed in ranked order; those that cannot fit are omitted with a warning. No character slices are silently truncated. The prompt has separate system instructions and a JSON envelope for preferences, format guidance and untrusted evidence. Only application aliases E1, E2, etc. are sent, mapped to authoritative UUIDs by the application. Returned aliases must belong to the supplied set and must not repeat within a block. Evidence is re-resolved before save and on reopen.

The default prompt cap is 24,000 UTF-8 bytes including schema/messages, with a 32,768-token configured context, 4,096 output tokens and a 2,048 framing reserve. The packer uses the smaller of its byte cap and context-minus-output-minus-reserve. This conservative proxy is not an exact model tokenizer. Metadata must expose a sufficient `.context_length`; unknown/insufficient context is rejected. Different tokenizers, server templates and context truncation behavior remain limitations. Change budgets in trusted `config/research2docs.toml`, then restart the app.

## Local inference and failure behavior

The fixed loopback `/api/chat` request uses JSON-schema `format`, `stream=false`, `think=false`, temperature 0, seed 0 and explicit context/output limits. Catalog and model metadata are checked again before inference. No tools, model pulls, URL retrieval, cloud SDK, proxy, redirects or remote fallback are used. These request parameters follow the [official Ollama API](https://github.com/ollama/ollama/blob/main/docs/api.md) and [structured-output documentation](https://ollama.com/blog/structured-outputs).

For targets of 400 words or fewer, the requested schema limits each section to one block, bounds prose characters in proportion to the target, and limits headings, review notes and limitations. This keeps short requests from expanding into many large blocks. Word counts remain approximate; supplied evidence and content validation still apply. The schema is included in the saved prompt hash.

The checked-in operator configuration uses a CPU walkthrough profile: 16,384 context tokens, 2,048 output tokens, three retrieved passages and a 600-second deadline. Class defaults above remain available to callers, but the TOML configuration overrides them in the app. This smaller profile supplies fewer passages and is intended for short drafts; use larger budgets deliberately for broader coverage or longer documents. A live 200-word NIST walkthrough request completed and saved an unreviewed four-section draft with three passages after the short-schema change. CPU generation still takes minutes; overlapping requests can queue and consume the deadline.

The default client deadline is 600 seconds with a 256 KiB response limit. Reads update socket timeout against the remaining deadline. Non-200, incomplete, output-limit, wrong-model, tool-call, invalid JSON, unexpected fields, oversized content, invalid sections and unknown citation references fail safely. There is no automatic repair/retry. A timeout closes the client connection but does not guarantee the server stops computation. Large word-count requests may not fit output limits; completed drafts warn about substantial length deviations.

## Persistence and review boundary

A run starts before model validation/inference. A successful response atomically creates a new draft, initial revision number 1, structured artifact and completed run. Handled failures save a failed run with no partial draft. A process interruption may leave a started record; no background recovery job exists. Template version, model identifier/digest, request settings, prompt/schema SHA-256, query, supplied exact evidence, goals and warnings survive restart.

All drafts remain **unreviewed**, even when every block has citations. Blocks without citations receive an application warning regardless of model review notes. Model-reported limitations are retained and labeled unassessed. References establish that passages exist, not that they entail the generated statement. There is no claim ledger, semantic support scoring, human-review workflow, editing, section regeneration or export in this phase. Those remain Phases 4–6. Never treat a generated command or procedure as verified operational guidance.
