import zipfile
from io import BytesIO
from uuid import uuid4

import pytest

from research2docs.core.errors import IngestionError
from research2docs.ingestion.chunker import passages, source_identity
from research2docs.ingestion.models import ImportLimits
from research2docs.ingestion.parsers import parse


@pytest.mark.parametrize(
    "name,kind",
    [
        ("reference.md", "markdown"),
        ("notes.txt", "txt"),
        ("reference.html", "html"),
        ("reference.docx", "docx"),
        ("reference.pdf", "pdf"),
    ],
)
def test_parser_locations_and_metadata(five_sources, name, kind):
    result = parse(five_sources[name], kind, ImportLimits())
    assert result.sections and result.extraction_method
    assert [s.ordinal for s in result.sections] == list(range(len(result.sections)))
    if kind == "markdown":
        assert len(result.sections) == 2
        assert result.sections[1].heading == "Evidence"
        assert "# This is code" in result.sections[1].text
    if kind == "docx":
        assert "docx_tables_flattened" in result.warnings


@pytest.mark.parametrize(
    "data,kind",
    [
        (b"not pdf", "pdf"),
        (b"not docx", "docx"),
        (b"%PDF-1.7\nfake", "txt"),
        (b"PK\x03\x04fake", "markdown"),
        (b"not html", "html"),
        (b"\xff\xfe", "txt"),
        (b"a\x00b", "txt"),
        (b"<html><body>html</body></html>", "txt"),
        (b"", "txt"),
        (b" \n\t", "txt"),
    ],
)
def test_malformed_or_disguised_inputs_are_rejected(data, kind):
    with pytest.raises((IngestionError, ValueError)):
        parse(data, kind, ImportLimits())


def test_exact_overlapping_slices_unicode_and_stability():
    data = ("# Source\r\n\r\n  " + ("é alpha\n" * 400)).encode()
    limits = ImportLimits(passage_chars=200, overlap_chars=20)
    parsed = parse(data, "markdown", limits)
    sid = source_identity("a" * 64)
    project = uuid4()
    sections, chunks = passages(project, sid, parsed, limits)
    by_id = {s.section_id: s for s in sections}
    assert len(chunks) > 2
    for c in chunks:
        assert c.text == by_id[c.section_id].text[c.char_start : c.char_end]
        assert len(c.text) <= 200
    assert [c.passage_id for c in chunks] == [
        c.passage_id for c in passages(project, sid, parsed, limits)[1]
    ]
    changed = limits.model_copy(update={"passage_chars": 201})
    assert chunks[0].passage_id != passages(project, sid, parsed, changed)[1][0].passage_id


def test_section_and_passage_limits_fail_instead_of_truncating():
    with pytest.raises(IngestionError):
        parse(b"X" * 101, "txt", ImportLimits(max_text_chars=100))
    parsed = parse(b"Word " * 200, "txt", ImportLimits())
    with pytest.raises(IngestionError):
        passages(
            uuid4(),
            uuid4(),
            parsed,
            ImportLimits(passage_chars=100, overlap_chars=0, max_passages=1),
        )


def rewrite_docx(original, name, contents):
    target = BytesIO()
    with zipfile.ZipFile(BytesIO(original)) as src, zipfile.ZipFile(target, "w") as dst:
        for info in src.infolist():
            dst.writestr(info.filename, src.read(info.filename))
        dst.writestr(name, contents)
    return target.getvalue()


@pytest.mark.parametrize(
    "name,content",
    [
        ("../outside.txt", b"cannot write"),
        ("/tmp/outside.txt", b"cannot write"),
        ("word/unsafe.xml", b'<!DOCTYPE x [<!ENTITY e SYSTEM "file:///etc/passwd">]><x>&e;</x>'),
        ("word/unsafe.xml", '<!DOCTYPE x [<!ENTITY e "x">]><x>&e;</x>'.encode("utf-16")),
        ("word/vbaProject.bin", b"macro"),
    ],
)
def test_docx_traversal_entities_and_macro_parts_rejected(five_sources, name, content):
    data = rewrite_docx(five_sources["reference.docx"], name, content)
    with pytest.raises(IngestionError):
        parse(data, "docx", ImportLimits())


def test_archive_bomb_and_entry_limits(five_sources):
    with pytest.raises(IngestionError):
        parse(five_sources["reference.docx"], "docx", ImportLimits(max_zip_expanded_bytes=1024))
    with pytest.raises(IngestionError):
        parse(five_sources["reference.docx"], "docx", ImportLimits(max_zip_entries=3))
    bomb = rewrite_docx(five_sources["reference.docx"], "word/big.txt", b"A" * 1200000)
    # Default ZIP_STORED fixture hits expanded-byte limit; the regular parser never extracts paths.
    with pytest.raises(IngestionError):
        parse(bomb, "docx", ImportLimits(max_zip_expanded_bytes=1000000))


def test_pdf_encryption_image_only_and_page_count():
    import pymupdf

    doc = pymupdf.open()
    doc.new_page()
    with pytest.raises(IngestionError):
        parse(doc.tobytes(), "pdf", ImportLimits())
    encrypted = doc.tobytes(
        encryption=pymupdf.PDF_ENCRYPT_AES_256, owner_pw="fixture", user_pw="fixture"
    )
    with pytest.raises(IngestionError) as error:
        parse(encrypted, "pdf", ImportLimits())
    assert error.value.reason == "encrypted_pdf"
    doc.new_page().insert_text((72, 72), "Visible text")
    with pytest.raises(IngestionError):
        parse(doc.tobytes(), "pdf", ImportLimits(max_pdf_pages=1))
    mixed = parse(doc.tobytes(), "pdf", ImportLimits())
    assert mixed.sections[0].page == 2 and "pdf_no_text_page_1" in mixed.warnings
    doc.close()


def test_high_compression_docx_part_is_rejected(five_sources):
    data = BytesIO()
    with (
        zipfile.ZipFile(BytesIO(five_sources["reference.docx"])) as src,
        zipfile.ZipFile(data, "w", compression=zipfile.ZIP_DEFLATED) as dst,
    ):
        for item in src.infolist():
            dst.writestr(item.filename, src.read(item.filename))
        dst.writestr("word/big.txt", b"A" * 1200000)
    with pytest.raises(IngestionError) as error:
        parse(data.getvalue(), "docx", ImportLimits())
    assert error.value.reason == "archive_ratio_limit"


def test_long_bibliographic_metadata_is_bounded_with_warning():
    html = (
        "<html><head><title>"
        + ("T" * 300)
        + '</title><meta name="author" content="'
        + ("A" * 600)
        + '"></head><body><p>Visible evidence</p></body></html>'
    ).encode()
    parsed = parse(html, "html", ImportLimits())
    assert len(parsed.title) == 200 and len(parsed.author) == 500
    assert "metadata_truncated" in parsed.warnings


def test_html_doctype_and_head_are_not_fabricated_body_passages():
    parsed = parse(
        b"<!doctype html><html><head><title>Label</title><style>x</style><script>x</script></head><body><h1>Actual heading</h1><p>Actual body.</p></body></html>",
        "html",
        ImportLimits(),
    )
    assert len(parsed.sections) == 1
    assert parsed.sections[0].text == "Actual heading\nActual body."
    assert parsed.title == "Label"
