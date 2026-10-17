# Complete Research2Docs AI walkthrough

Open http://127.0.0.1:8503/. The current demonstration uses **Orion Archive — Fictional Phase 2 Demo**, five clearly fictional documents and one draft with three saved revisions. It is demonstration material, not a real product, deployment or research finding. No human decision has been recorded on your behalf.

## 1 Create or reopen a project

On Dashboard, reopen the Orion Archive project to inspect the completed example. To repeat from scratch, create a separate project such as **Full Workflow Walkthrough** with a short research purpose. In Project Workspace choose a document type, audience, working title, length and depth, then Save project. Metadata persists after refresh.

## 2 Import the five source files

In Project Workspace, under Source documents, select `overview.md`, `notes.txt`, `reference.html`, `workflow.docx` and `troubleshooting.pdf` from `samples/fictional_research` in this repository. Exclude its README. The uploader may show a plus icon rather than a Browse button. Leave optional metadata blank unless deliberately overriding it; import and inspect each result/warning. Identical content is skipped without replacing its saved metadata. No source URL is fetched.

## 3 Inspect original evidence

Open Source Explorer and search **RESEARCH_READY**. Inspect source metadata and choose the PDF's page-2 passage. Confirm the exact marker and the qualification that source availability does not verify claims. Search is keyword retrieval, not an answer generator or verification result. The five demo documents produce ten stored passages.

## 4 Select the local model

In Settings select Check local Ollama. Choose the installed `qwen3-vl:4b-instruct` candidate and Save model selection. If Ollama is unavailable, start the installed local service. The app does not download models or fall back to a cloud service. Project/source/export operations work without inference.

## 5 Generate an unreviewed draft

In Document Studio choose Technical explainer, Beginner technical, title **Orion Archive readiness**, and target 300 words. Enter **RESEARCH_READY Orion Archive readiness verification limitations** as the research question. Generate and save. Review the result's warnings, section structure, source aliases and evidence. Other format/audience combinations are available. Length is approximate and bounded output can reject a truncated response.

## 6 Assess a claim against its sources

In Evidence Review select the draft and its latest saved revision. Choose one claim/prose block and Assess selected claim locally. Inspect the explanation, exact excerpts, full source context, contradictory/temporal evidence if any, method/model metadata and pending human status. A block can contain several factual assertions. Source-supported is an AI proposal about the supplied passages, not external truth or human approval. Use Reload claim assessment if another session changed it.

## 7 Record your own editorial decision

Read the full passages. In the human-decision form enter your reviewer name and rationale, select the passages you actually reviewed, and confirm that this is your own review of the exact claim/revision. Accept only when you consider the source support adequate. Otherwise reject, or leave pending. Additional project sources can be inspected in the source selector. The app records your self-reported judgment; it does not authenticate identity or independently prove the claim. Reopen an accepted/rejected decision if you want another automated assessment. Earlier decisions remain in history.

## 8 Save an edited revision

Back in Document Studio choose the latest revision, then a section under Editorial workspace. Enter an editor name and reason, change a sentence or heading, and Save as new revision. Verify the revision number increases, the old text is still selectable, and every new claim is pending/not assessed. The existing example's revision 1 is the generated draft, revision 2 regenerates only the Concept section, and revision 3 clarifies that section's fictional-demonstration heading. Earlier assessments and decisions do not transfer.

## 9 Regenerate one section

On the latest revision choose a section and use the separate regeneration form. Supply an editor name, reason and instructions such as **Make this concise for a beginner while preserving the fictional nature and verification limitations**. Regenerate selected section locally. The app saves another revision; compare it with its parent and confirm the other sections are unchanged. Inspect citations and reassess the new revision.

## 10 Export the selected revision

Open Export Center, select the draft and exact revision, then a format. Prepare export and Download prepared export. Repeat for Markdown, editable Word, standalone HTML and JSON evidence manifest. Open the DOCX/HTML and inspect the draft banner, unresolved count, citations, claim ledger and evidence appendix. Inspect JSON for exact passage IDs, model/prompt information and recorded decisions. Export never clears review flags or marks the document verified.

## 11 Confirm persistence

Refresh the app or restart it with the same storage directory. Reopen the project, draft/revision history, evidence, decisions and Export Center. The demo currently uses `/private/tmp/research2docs-phase1-demo`; ordinary launch uses the configured Git-ignored `data` directory. Temporary-directory storage is for demonstration and may be cleaned by the OS. Use a persistent chosen directory for important work and back it up with the app stopped.

The repository's deterministic tests cover this complete flow with fictional fixture decisions; the real local demonstration exercised generation, assessment, section regeneration, a browser edit and all four exports. Model quality, factual truth and authenticated human review are not inferred from those operational checks.

## Portfolio follow-up with the supplied NIST reference

The repository also contains `docs/NIST.AI.100-1.pdf`. For the real-source portfolio demonstration suggested in the original `how-2-demo.md`, create a separate **NIST AI RMF Walkthrough** project and import that PDF. Repeat the same workflow with these three outputs:

1. Technical explainer / General public / **What Is the NIST AI RMF?** / query **AI risk management framework voluntary trustworthy GOVERN MAP MEASURE MANAGE**.
2. Instructional guide / Advanced technical or Custom cybersecurity professionals / **Implementing AI Risk Management** / query **GOVERN MAP MEASURE MANAGE profiles functions risk management**.
3. Executive technical brief / Executive / **AI Governance Executive Overview** / query **AI governance organizational leadership roles responsibilities risk tolerance**.

Inspect passages before relying on each generated answer. As an explicitly labeled verification challenge, save a new revision containing **The NIST AI RMF requires every organization to complete a mandatory annual certification audit**. Assess that claim and inspect the actual source context; the expected review concern is whether the source establishes such a universal mandatory requirement. Do not claim that this test or a particular model result has already occurred. Reject or leave unresolved if support is absent. Real-source generation/support quality must be observed, not inferred from the fictional demo or automated fixture tests.
