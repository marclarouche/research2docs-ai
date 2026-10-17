"""Byte-only deterministic extraction. Called inside the bounded parser worker."""

import io
import re
import stat
import zipfile
from pathlib import PurePosixPath

from research2docs.core.errors import IngestionError
from research2docs.ingestion.models import ExtractedSection, ImportLimits, ParsedSource, SourceType


class Sections:
    def __init__(self, limits: ImportLimits):
        self.limits = limits
        self.items: list[ExtractedSection] = []
        self.characters = 0

    def add(
        self,
        text: str,
        *,
        heading: str | None = None,
        page: int | None = None,
        locator: str | None = None,
    ) -> None:
        if not text.strip():
            return
        self.characters += len(text)
        if (
            self.characters > self.limits.max_text_chars
            or len(self.items) >= self.limits.max_sections
        ):
            raise IngestionError("extraction_limit")
        self.items.append(
            ExtractedSection(
                text=text,
                ordinal=len(self.items),
                heading=heading[:500] if heading else None,
                page=page,
                locator=locator or f"Section {len(self.items) + 1}",
            )
        )


def metadata(value: object, max_chars: int, warnings: list[str] | None = None) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    value = value.strip()
    if len(value) > max_chars and warnings is not None and "metadata_truncated" not in warnings:
        warnings.append("metadata_truncated")
    return value[:max_chars]


def decode(data: bytes) -> str:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeError:
        raise IngestionError("invalid_utf8") from None
    if any(ord(c) < 32 and c not in "\n\r\t\f" for c in text):
        raise IngestionError("binary_text")
    return text


def parse_text(data: bytes, kind: SourceType, limits: ImportLimits) -> ParsedSource:
    from markdown_it import MarkdownIt

    text = decode(data)
    if len(text) > limits.max_text_chars:
        raise IngestionError("extraction_limit")
    if re.match(r"\s*(?:<!doctype\s+html|<html\b)", text, re.IGNORECASE):
        raise IngestionError("content_type_mismatch")
    sections = Sections(limits)
    title = None
    warnings: list[str] = []
    if kind == "markdown":
        lines = text.splitlines(keepends=True)
        offsets = [0]
        for line in lines:
            offsets.append(offsets[-1] + len(line))
        starts: list[tuple[int, str | None]] = [(0, None)]
        tokens = MarkdownIt("commonmark", {"html": False}).parse(text)
        for i, token in enumerate(tokens):
            if token.type == "heading_open" and token.map is not None:
                heading_text = tokens[i + 1].content
                if title is None:
                    title = metadata(heading_text, 200, warnings)
                offset = offsets[token.map[0]]
                if starts[-1][0] == offset:
                    starts[-1] = (offset, heading_text)
                else:
                    starts.append((offset, heading_text))
        for i, (start, heading) in enumerate(starts):
            end = starts[i + 1][0] if i + 1 < len(starts) else len(text)
            sections.add(
                text[start:end], heading=heading, locator=f"Decoded characters {start}:{end}"
            )
    else:
        sections.add(text, locator=f"Decoded characters 0:{len(text)}")
    return ParsedSource(
        source_type=kind,
        warnings=warnings,
        title=title,
        sections=sections.items,
        extraction_method=f"utf8-{'markdown-it' if kind == 'markdown' else 'plain'}",
    )


def parse_html(data: bytes, limits: ImportLimits) -> ParsedSource:
    from bs4 import BeautifulSoup

    text = decode(data)
    if not re.search(
        r"<(?:html|head|body|title|h[1-6]|p|div|article|section|table|ul|ol)\b", text, re.IGNORECASE
    ):
        raise IngestionError("content_type_mismatch")
    soup = BeautifulSoup(text, "html.parser")
    warnings = ["html_layout_flattened"]
    title = metadata(soup.title.get_text() if soup.title else None, 200, warnings)
    author_tag = soup.find("meta", attrs={"name": re.compile(r"^author$", re.IGNORECASE)})
    author = metadata(author_tag.get("content") if author_tag else None, 500, warnings)
    for tag in soup(["script", "style", "iframe", "object", "embed", "form", "template", "head"]):
        tag.decompose()
    if soup.head is not None:
        soup.head.decompose()
    sections = Sections(limits)
    buffer: list[str] = []
    heading: str | None = None
    # Walk text nodes once; nested tags cannot duplicate block text.
    buffered = 0
    for node in soup.descendants:
        from bs4.element import (
            Comment,
            Declaration,
            Doctype,
            NavigableString,
            ProcessingInstruction,
            Tag,
        )

        if isinstance(node, Tag) and node.name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            sections.add("\n".join(buffer), heading=heading)
            buffer = []
            buffered = 0
            heading = metadata(node.get_text(" ", strip=True), 500)
            if title is None:
                title = metadata(heading, 200)
        elif isinstance(node, NavigableString) and not isinstance(
            node, (Comment, Declaration, Doctype, ProcessingInstruction)
        ):
            value = str(node).strip()
            if value:
                buffer.append(value)
                buffered += len(value) + 1
                if buffered + sections.characters > limits.max_text_chars:
                    raise IngestionError("extraction_limit")
    sections.add("\n".join(buffer), heading=heading)
    return ParsedSource(
        source_type="html",
        title=title,
        author=author,
        sections=sections.items,
        extraction_method="beautifulsoup-html.parser",
        warnings=warnings,
    )


def check_docx(data: bytes, limits: ImportLimits) -> None:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        entries = archive.infolist()
        names = {item.filename for item in entries}
        if (
            len(entries) > limits.max_zip_entries
            or len(names) != len(entries)
            or not {"[Content_Types].xml", "word/document.xml", "_rels/.rels"} <= names
        ):
            raise IngestionError("invalid_docx_package")
        total = 0
        for entry in entries:
            path = PurePosixPath(entry.filename)
            if (
                path.is_absolute()
                or ".." in path.parts
                or "\\" in entry.filename
                or ":" in entry.filename
                or entry.flag_bits & 1
                or stat.S_ISLNK(entry.external_attr >> 16)
                or "vbaproject" in entry.filename.lower()
            ):
                raise IngestionError("unsafe_docx_package")
            total += entry.file_size
            if total > limits.max_zip_expanded_bytes:
                raise IngestionError("archive_expansion_limit")
            if entry.file_size > 1048576 and entry.file_size > max(entry.compress_size, 1) * 200:
                raise IngestionError("archive_ratio_limit")
            # Verify actual decompression/CRC and reject XML declarations without extracting files.
            with archive.open(entry) as stream:
                content = stream.read(min(limits.max_zip_expanded_bytes, entry.file_size) + 1)
            if len(content) != entry.file_size:
                raise IngestionError("invalid_docx_package")
            if entry.filename.endswith((".xml", ".rels")):
                normalized = content.replace(b"\x00", b"").upper()
                if b"<!DOCTYPE" in normalized or b"<!ENTITY" in normalized:
                    raise IngestionError("unsafe_xml")
            if entry.filename == "[Content_Types].xml" and b"macroenabled" in content.lower():
                raise IngestionError("unsafe_docx_package")


def parse_docx(data: bytes, limits: ImportLimits) -> ParsedSource:
    from docx import Document
    from docx.document import Document as DocxDocument
    from docx.table import Table

    check_docx(data, limits)
    document: DocxDocument = Document(io.BytesIO(data))
    sections = Sections(limits)
    warnings = ["docx_layout_limitations"]
    title = metadata(document.core_properties.title, 200, warnings)
    author = metadata(document.core_properties.author, 500, warnings)
    heading: str | None = None
    buffer: list[str] = []
    buffered = 0
    for element in document.iter_inner_content():
        if isinstance(element, Table):
            value = "\n".join("\t".join(cell.text for cell in row.cells) for row in element.rows)
            if "docx_tables_flattened" not in warnings:
                warnings.append("docx_tables_flattened")
        else:
            value = element.text
            style = element.style.name if element.style else ""
            if style.startswith(("Heading", "Title")) and value.strip():
                sections.add("\n\n".join(buffer), heading=heading)
                buffer = []
                buffered = 0
                heading = metadata(value, 500)
                if title is None:
                    title = metadata(heading, 200)
        if value:
            buffer.append(value)
            buffered += len(value) + 2
        if buffered + sections.characters > limits.max_text_chars:
            raise IngestionError("extraction_limit")
    sections.add("\n\n".join(buffer), heading=heading)
    return ParsedSource(
        source_type="docx",
        title=title,
        author=author,
        sections=sections.items,
        extraction_method="python-docx-body-order",
        warnings=warnings,
    )


def parse_pdf(data: bytes, limits: ImportLimits) -> ParsedSource:
    import pymupdf

    sections = Sections(limits)
    warnings = ["pdf_reading_order_limitations"]
    with pymupdf.open(stream=data, filetype="pdf") as document:  # type: ignore[no-untyped-call]  # PyMuPDF factory lacks annotations.
        if document.is_encrypted or document.needs_pass:
            raise IngestionError("encrypted_pdf")
        if len(document) > limits.max_pdf_pages:
            raise IngestionError("pdf_page_limit")
        for index, page in enumerate(document):
            value = page.get_text("text", sort=True)
            if not value.strip():
                warnings.append(f"pdf_no_text_page_{index + 1}")
            sections.add(value, page=index + 1, locator=f"Page {index + 1}")
        info = document.metadata or {}
        title = metadata(info.get("title"), 200, warnings)
        author = metadata(info.get("author"), 500, warnings)
    return ParsedSource(
        source_type="pdf",
        title=title,
        author=author,
        sections=sections.items,
        extraction_method="pymupdf-sorted-text",
        warnings=warnings,
    )


def parse(data: bytes, kind: SourceType, limits: ImportLimits) -> ParsedSource:
    if not data or len(data) > limits.max_file_bytes:
        raise IngestionError("file_size_limit")
    if kind == "pdf":
        if not data.startswith(b"%PDF-"):
            raise IngestionError("content_type_mismatch")
        result = parse_pdf(data, limits)
    elif kind == "docx":
        if not data.startswith(b"PK\x03\x04"):
            raise IngestionError("content_type_mismatch")
        result = parse_docx(data, limits)
    else:
        if data.startswith((b"%PDF-", b"PK\x03\x04")):
            raise IngestionError("content_type_mismatch")
        result = parse_html(data, limits) if kind == "html" else parse_text(data, kind, limits)
    if not result.sections:
        raise IngestionError(
            "no_extractable_text", "No usable text was found. Scanned PDFs require external OCR."
        )
    return result
