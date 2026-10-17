"""Source import/exploration presentation only; processing lives in SourceService."""

from uuid import UUID

import streamlit as st

from research2docs.ingestion.models import ImportMetadata, ImportResult
from research2docs.services.workspace_service import WorkspaceService


def warning_text(code: str) -> str:
    descriptions = {
        "metadata_truncated": "Some extracted title/author metadata exceeded the display limits and was shortened. Consult the original for complete metadata.",
        "html_layout_flattened": "HTML layout is flattened. Scripts, styles and embedded frames are excluded.",
        "docx_layout_limitations": "DOCX headers, footers, images, comments and tracked changes may be omitted.",
        "docx_tables_flattened": "DOCX tables are flattened into row text; compare important values with the original.",
        "pdf_reading_order_limitations": "PDF reading order may differ from the visual page. Verify important excerpts in the original.",
        "identical_content_already_saved_metadata_unchanged": "These exact bytes are already saved. The original source metadata was preserved.",
    }
    if code.startswith("pdf_no_text_page_"):
        return (
            "No extractable text on PDF page "
            + code.removeprefix("pdf_no_text_page_")
            + ". No OCR was performed."
        )
    return descriptions.get(code, code)


def import_panel(workspace: WorkspaceService, project_id: str) -> None:
    st.subheader("Source documents")
    st.caption(
        "Import up to 10 files per batch: text PDF, DOCX, Markdown, TXT or local HTML. Sources and searchable passages save together; no model is needed."
    )
    with st.form("import_" + project_id):
        uploads = st.file_uploader(
            "Source files",
            type=["pdf", "docx", "md", "markdown", "txt", "html", "htm"],
            accept_multiple_files=True,
        )
        title = st.text_input("Source title override (single file only)", max_chars=200)
        author = st.text_input("Author override (optional)", max_chars=500)
        url = st.text_input(
            "Reference URL (optional; stored as a label, never fetched)", max_chars=2000
        )
        submitted = st.form_submit_button("Import and index sources")
    if submitted:
        with st.spinner("Extracting in bounded workers and saving exact evidence…"):
            results = workspace.sources.import_batch(
                project_id,
                [(upload.name, upload.getvalue()) for upload in uploads],
                ImportMetadata(
                    title=title.strip() or None,
                    author=author.strip() or None,
                    supplied_url=url.strip() or None,
                ),
            )
        st.session_state["import_results_" + project_id] = [r.model_dump_json() for r in results]
    for raw in st.session_state.get("import_results_" + project_id, []):
        result = ImportResult.model_validate_json(raw)
        st.text(result.filename)
        if result.accepted:
            st.success(
                "Already saved; existing metadata preserved."
                if result.duplicate
                else f"Imported and indexed · {result.passages} passages"
            )
        else:
            st.error("Not imported · " + result.reason)
        for warning in result.warnings:
            st.text(warning_text(warning))
    sources = workspace.sources.list_sources(project_id)
    if sources:
        st.dataframe(
            [
                {
                    "Title": item.source.title,
                    "File": item.source.filename,
                    "Format": item.source.source_type,
                    "Author": item.source.author or "Not supplied",
                    "Passages": item.passages,
                    "SHA-256": item.source.sha256,
                }
                for item in sources
            ],
            hide_index=True,
        )
    else:
        st.info("No sources imported yet.")
    st.caption(
        "Original uploads are not retained. Keep originals. Extracted text is stored locally and is unencrypted. Byte-identical files are skipped within the project, including renamed copies."
    )


def explorer(workspace: WorkspaceService, project_id: str) -> None:
    st.subheader("Source Explorer")
    sources = workspace.sources.list_sources(project_id)
    if not sources:
        st.info("Import source files in Project Workspace first.")
        return
    st.caption(
        "Full-text retrieval only. Scores are ranking signals, not confidence, source authority or factual verification. Source content is untrusted data."
    )
    with st.form("search_" + project_id):
        query = st.text_input("Search source passages", max_chars=2000)
        searched = st.form_submit_button("Search passages")
    if searched:
        hits = workspace.sources.search(project_id, query)
        if not hits:
            st.info("No matching passages. Try a different word or identifier.")
        for hit in hits:
            st.text(f"{hit.rank}. {hit.source.title} · {hit.source.filename}")
            show_passage(workspace, project_id, hit.passage.passage_id)
            st.caption(f"FTS5 BM25: {hit.score:.6g}")
    names = {
        str(item.source.source_id): f"{item.source.title} · {item.source.filename}"
        for item in sources
    }
    source_id = st.selectbox("Source document", list(names), format_func=names.__getitem__)
    summary = next(item for item in sources if str(item.source.source_id) == source_id)
    with st.expander("Source metadata"):
        st.text("Title: " + summary.source.title)
        st.text("Author: " + (summary.source.author or "Not supplied"))
        st.text("File: " + summary.source.filename)
        st.text("SHA-256: " + summary.source.sha256)
        st.text("Source ID: " + source_id)
        st.text("Imported: " + summary.source.imported_at.isoformat())
        st.text("Reference URL: " + (summary.source.supplied_url or "Not supplied"))
        for warning in summary.warnings:
            st.text(warning_text(warning))
    passages = workspace.sources.source_passages(project_id, source_id)
    passage_names = {
        str(p.passage_id): f"{p.ordinal + 1} · {p.heading or p.section or 'Source passage'}"
        for p in passages
    }
    selected = st.selectbox(
        "Stored passage", list(passage_names), format_func=passage_names.__getitem__
    )
    if selected:
        show_passage(workspace, project_id, UUID(selected))


def show_passage(workspace: WorkspaceService, project_id: str, passage_id: UUID) -> None:
    passage = workspace.sources.resolve_passage(project_id, passage_id)
    st.text("Passage ID: " + str(passage.passage_id))
    st.text(
        "Page: "
        + (str(passage.page) if passage.page else "Not available")
        + " · "
        + (passage.section or "Section not available")
    )
    if passage.heading:
        st.text("Heading: " + passage.heading)
    st.caption(
        f"Extraction: {passage.extraction_method} · Exact section characters [{passage.char_start}, {passage.char_end})"
    )
    st.code(passage.text, language="text", wrap_lines=True)
