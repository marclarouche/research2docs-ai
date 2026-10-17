import pytest

from research2docs.core.config import Settings
from research2docs.core.errors import IngestionError, InputError, StorageError
from research2docs.core.models import ProjectInput
from research2docs.ingestion.models import ImportLimits, ImportMetadata
from research2docs.services.workspace_service import WorkspaceService


@pytest.fixture
def workspace(tmp_path):
    w = WorkspaceService(Settings(data_dir=str(tmp_path)))
    p = w.projects.create(ProjectInput(title="Fictional source test"))
    return w, p


def test_all_five_formats_worker_import_search_reopen(workspace, five_sources):
    w, p = workspace
    for name, data in five_sources.items():
        result = w.sources.import_document(p.project_id, data, name)
        assert result.accepted and result.passages > 0
    reopened = WorkspaceService(w.settings)
    inventory = reopened.sources.list_sources(p.project_id)
    assert len(inventory) == 5
    hits = reopened.sources.search(p.project_id, "EVIDENCE_READY", limit=20)
    assert len(hits) == 5
    pdf = next(h for h in hits if h.source.source_type == "pdf")
    assert pdf.passage.page == 2
    assert pdf.source.title == "Fictional PDF Research"
    assert pdf.source.author == "Fictional Documentation Team"
    html = next(h for h in hits if h.source.source_type == "html")
    assert "SHOULD_NOT_BE_EXTRACTED" not in html.passage.text
    for hit in hits:
        resolved = reopened.sources.resolve_passage(p.project_id, hit.passage.passage_id)
        assert resolved == hit.passage
        assert resolved.section_id and resolved.char_end
    text = next(h for h in hits if h.source.source_type == "txt")
    assert text.passage.text.startswith("  ") and "\r\n" in text.passage.text


def test_stable_ids_renames_and_duplicate_metadata_preservation(workspace):
    w, p = workspace
    data = b"# Original title\n\nA stable source.\n"
    first = w.sources.import_document(
        p.project_id,
        data,
        "original.md",
        ImportMetadata(author="Original author", supplied_url="https://example.invalid/source"),
    )
    saved = w.sources.list_sources(p.project_id)[0].source
    duplicate = w.sources.import_document(
        p.project_id, data, "renamed.md", ImportMetadata(title="Different title")
    )
    assert duplicate.duplicate and duplicate.source_id == first.source_id
    assert w.sources.list_sources(p.project_id)[0].source == saved
    other = w.projects.create(ProjectInput(title="Separate project"))
    copied = w.sources.import_document(other.project_id, data, "another-name.md")
    assert copied.source_id == first.source_id
    left = w.sources.source_passages(p.project_id, first.source_id)
    right = w.sources.source_passages(other.project_id, copied.source_id)
    assert [x.passage_id for x in left] == [x.passage_id for x in right]
    assert left[0].project_id != right[0].project_id


def test_mixed_batch_has_explicit_failures_and_atomic_successes(workspace):
    w, p = workspace
    results = w.sources.import_batch(
        p.project_id,
        [("good.txt", b"Searchable GOOD_MARKER."), ("bad.pdf", b"not a pdf"), ("empty.txt", b"")],
    )
    assert [r.accepted for r in results] == [True, False, False]
    assert results[1].reason == "content_type_mismatch"
    assert len(w.sources.list_sources(p.project_id)) == 1
    assert len(w.sources.search(p.project_id, "GOOD_MARKER")) == 1


def test_fts_failure_rolls_back_source_sections_passages(workspace):
    w, p = workspace
    with w.database.session(write=True) as conn:
        conn.execute("DROP TABLE passage_fts")
    with pytest.raises(StorageError):
        w.sources.import_document(p.project_id, b"ATOMIC_MARKER content", "atomic.txt")
    assert w.sources.list_sources(p.project_id) == []
    with w.database.session() as conn:
        assert conn.execute("SELECT count(*) FROM source_sections").fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM source_passages").fetchone()[0] == 0


def test_project_limits_count_exact_sections_not_overlap(tmp_path):
    settings = Settings(data_dir=str(tmp_path), ingestion=ImportLimits(max_sources=1))
    w = WorkspaceService(settings)
    p = w.projects.create(ProjectInput(title="Limit"))
    w.sources.import_document(p.project_id, b"First distinct document.", "a.txt")
    with pytest.raises(IngestionError, match="limit"):
        w.sources.import_document(p.project_id, b"Second distinct document.", "b.txt")
    assert len(w.sources.list_sources(p.project_id)) == 1


def test_search_inputs_scope_and_exact_identifiers(workspace):
    w, p = workspace
    result = w.sources.import_document(p.project_id, b"AUTH_REQUIRED means no token.\n", "api.txt")
    other = w.projects.create(ProjectInput(title="Other"))
    assert not w.sources.search(other.project_id, "AUTH_REQUIRED")
    with pytest.raises(InputError):
        w.sources.resolve_passage(
            other.project_id,
            w.sources.source_passages(p.project_id, result.source_id)[0].passage_id,
        )
    for query in [
        '" OR 1=1; DROP TABLE source_passages; --',
        "AUTH_REQUIRED OR NOT token",
        "AUTH_REQUIRED* NEAR(token)",
    ]:
        w.sources.search(p.project_id, query)
    assert w.sources.search(p.project_id, "AUTH_REQUIRED")
    assert not w.sources.search(p.project_id, "zxq_unique_missing")
    for query in ["", " " * 20, "x" * 2001, " ".join("term" + str(i) for i in range(65))]:
        with pytest.raises(InputError):
            w.sources.search(p.project_id, query)
    for limit in [0, 21, True]:
        with pytest.raises(InputError):
            w.sources.search(p.project_id, "token", limit=limit)


def test_tampered_passage_is_never_returned_as_exact_evidence(workspace):
    w, p = workspace
    result = w.sources.import_document(p.project_id, b"CORRUPTION_MARKER reference", "test.txt")
    passage = w.sources.source_passages(p.project_id, result.source_id)[0]
    with w.database.session(write=True) as conn:
        conn.execute(
            "UPDATE source_passages SET text=? WHERE passage_id=?",
            ("Altered material", str(passage.passage_id)),
        )
    with pytest.raises(StorageError):
        w.sources.resolve_passage(p.project_id, passage.passage_id)
    with pytest.raises(StorageError):
        w.sources.search(p.project_id, "CORRUPTION_MARKER")
