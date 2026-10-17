"""Versioned transactional schema; future workflow tables have no Phase 1 write API."""

SCHEMA_VERSION = 5
MIGRATION_1 = (
    """CREATE TABLE projects (
        project_id TEXT PRIMARY KEY, title TEXT NOT NULL CHECK(length(trim(title)) BETWEEN 1 AND 200),
        description TEXT NOT NULL, goals_json TEXT NOT NULL CHECK(json_valid(goals_json)),
        version INTEGER NOT NULL CHECK(version >= 1), created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL)""",
    """CREATE TABLE app_preferences (
        key TEXT PRIMARY KEY CHECK(key = 'selected_model'), value TEXT NOT NULL)""",
    """CREATE TABLE source_documents (
        project_id TEXT NOT NULL REFERENCES projects(project_id), source_id TEXT NOT NULL,
        filename TEXT NOT NULL, sha256 TEXT NOT NULL CHECK(length(sha256) = 64),
        metadata_json TEXT NOT NULL CHECK(json_valid(metadata_json)),
        PRIMARY KEY(project_id, source_id), UNIQUE(project_id, sha256))""",
    """CREATE TABLE source_passages (
        project_id TEXT NOT NULL, passage_id TEXT NOT NULL, source_id TEXT NOT NULL,
        text TEXT NOT NULL, ordinal INTEGER NOT NULL CHECK(ordinal >= 0),
        locator_json TEXT NOT NULL CHECK(json_valid(locator_json)),
        extraction_method TEXT NOT NULL, PRIMARY KEY(project_id, passage_id),
        UNIQUE(project_id, source_id, ordinal),
        FOREIGN KEY(project_id, source_id) REFERENCES source_documents(project_id, source_id))""",
    """CREATE TABLE drafts (
        project_id TEXT NOT NULL REFERENCES projects(project_id), draft_id TEXT NOT NULL,
        title TEXT NOT NULL, goals_json TEXT NOT NULL CHECK(json_valid(goals_json)),
        created_at TEXT NOT NULL, PRIMARY KEY(project_id, draft_id))""",
    """CREATE TABLE revisions (
        project_id TEXT NOT NULL, revision_id TEXT NOT NULL, draft_id TEXT NOT NULL,
        number INTEGER NOT NULL CHECK(number >= 1), content TEXT NOT NULL,
        created_at TEXT NOT NULL, PRIMARY KEY(project_id, revision_id),
        UNIQUE(project_id, draft_id, number),
        FOREIGN KEY(project_id, draft_id) REFERENCES drafts(project_id, draft_id))""",
    """CREATE TABLE claims (
        project_id TEXT NOT NULL, claim_id TEXT NOT NULL, revision_id TEXT NOT NULL,
        text TEXT NOT NULL, assessment TEXT NOT NULL CHECK(assessment IN (
        'source_supported','partially_supported','unsupported','conflicting_evidence',
        'potentially_outdated','human_verified')),
        assessment_json TEXT NOT NULL CHECK(json_valid(assessment_json)),
        PRIMARY KEY(project_id, claim_id),
        FOREIGN KEY(project_id, revision_id) REFERENCES revisions(project_id, revision_id))""",
    """CREATE TABLE evidence_links (
        project_id TEXT NOT NULL, claim_id TEXT NOT NULL, passage_id TEXT NOT NULL,
        relation TEXT NOT NULL CHECK(relation IN ('supporting','contradictory')),
        PRIMARY KEY(project_id, claim_id, passage_id, relation),
        FOREIGN KEY(project_id, claim_id) REFERENCES claims(project_id, claim_id),
        FOREIGN KEY(project_id, passage_id) REFERENCES source_passages(project_id, passage_id))""",
    """CREATE TABLE editorial_decisions (
        project_id TEXT NOT NULL, decision_id TEXT NOT NULL, claim_id TEXT NOT NULL,
        reviewer TEXT NOT NULL, decision TEXT NOT NULL CHECK(decision IN ('accepted','rejected')),
        rationale TEXT NOT NULL CHECK(length(trim(rationale)) > 0), created_at TEXT NOT NULL,
        PRIMARY KEY(project_id, decision_id),
        FOREIGN KEY(project_id, claim_id) REFERENCES claims(project_id, claim_id))""",
    """CREATE TABLE generation_runs (
        project_id TEXT NOT NULL REFERENCES projects(project_id), run_id TEXT NOT NULL,
        revision_id TEXT, model TEXT NOT NULL, prompt_version TEXT NOT NULL,
        parameters_json TEXT NOT NULL CHECK(json_valid(parameters_json)), started_at TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('started','completed','failed')),
        PRIMARY KEY(project_id, run_id),
        FOREIGN KEY(project_id, revision_id) REFERENCES revisions(project_id, revision_id))""",
)


MIGRATION_2 = (
    """CREATE TABLE source_imports (
        project_id TEXT NOT NULL, source_id TEXT NOT NULL,
        warnings_json TEXT NOT NULL CHECK(json_valid(warnings_json)),
        PRIMARY KEY(project_id, source_id),
        FOREIGN KEY(project_id, source_id) REFERENCES source_documents(project_id, source_id))""",
    """CREATE TABLE source_sections (
        project_id TEXT NOT NULL, section_id TEXT NOT NULL, source_id TEXT NOT NULL,
        text TEXT NOT NULL, metadata_json TEXT NOT NULL CHECK(json_valid(metadata_json)),
        PRIMARY KEY(project_id, section_id),
        FOREIGN KEY(project_id, source_id) REFERENCES source_documents(project_id, source_id))""",
    """CREATE VIRTUAL TABLE passage_fts USING fts5(
        project_id UNINDEXED, passage_id UNINDEXED, text,
        tokenize="unicode61 tokenchars '_'")""",
    """INSERT INTO passage_fts (project_id, passage_id, text)
        SELECT project_id, passage_id, text FROM source_passages""",
)


MIGRATION_3 = (
    """CREATE TABLE generated_drafts (
        project_id TEXT NOT NULL, revision_id TEXT NOT NULL,
        payload_json TEXT NOT NULL CHECK(json_valid(payload_json)),
        PRIMARY KEY(project_id, revision_id),
        FOREIGN KEY(project_id, revision_id) REFERENCES revisions(project_id, revision_id))""",
)


MIGRATION_4 = (
    """CREATE TABLE verification_ledgers (
        project_id TEXT NOT NULL, revision_id TEXT NOT NULL,
        payload_json TEXT NOT NULL CHECK(json_valid(payload_json)),
        PRIMARY KEY(project_id, revision_id),
        FOREIGN KEY(project_id, revision_id) REFERENCES revisions(project_id, revision_id))""",
    """CREATE TABLE claim_units (
        project_id TEXT NOT NULL, claim_id TEXT NOT NULL, revision_id TEXT NOT NULL,
        section_index INTEGER NOT NULL CHECK(section_index>=0), block_index INTEGER NOT NULL CHECK(block_index>=0),
        payload_json TEXT NOT NULL CHECK(json_valid(payload_json)),
        PRIMARY KEY(project_id, claim_id), UNIQUE(project_id, revision_id, section_index, block_index),
        FOREIGN KEY(project_id, claim_id) REFERENCES claims(project_id, claim_id),
        FOREIGN KEY(project_id, revision_id) REFERENCES verification_ledgers(project_id, revision_id))""",
    """CREATE TABLE assessment_runs (
        project_id TEXT NOT NULL, assessment_id TEXT NOT NULL, revision_id TEXT NOT NULL, claim_id TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('started','completed','failed')), started_at TEXT NOT NULL,
        payload_json TEXT NOT NULL CHECK(json_valid(payload_json)), PRIMARY KEY(project_id,assessment_id),
        FOREIGN KEY(project_id,claim_id) REFERENCES claims(project_id,claim_id),
        FOREIGN KEY(project_id,revision_id) REFERENCES revisions(project_id,revision_id))""",
)


MIGRATION_5 = (
    """CREATE TABLE draft_heads (
        project_id TEXT NOT NULL, draft_id TEXT NOT NULL, revision_id TEXT NOT NULL,
        PRIMARY KEY(project_id,draft_id),
        FOREIGN KEY(project_id,draft_id) REFERENCES drafts(project_id,draft_id),
        FOREIGN KEY(project_id,revision_id) REFERENCES revisions(project_id,revision_id))""",
    """INSERT INTO draft_heads SELECT r.project_id,r.draft_id,r.revision_id FROM revisions r
        WHERE r.number=(SELECT max(r2.number) FROM revisions r2
        WHERE r2.project_id=r.project_id AND r2.draft_id=r.draft_id)""",
    """CREATE TABLE revision_events (
        project_id TEXT NOT NULL,revision_id TEXT NOT NULL,parent_revision_id TEXT NOT NULL,
        editor TEXT NOT NULL,note TEXT NOT NULL,origin TEXT NOT NULL,
        created_at TEXT NOT NULL,PRIMARY KEY(project_id,revision_id),
        FOREIGN KEY(project_id,revision_id) REFERENCES revisions(project_id,revision_id),
        FOREIGN KEY(project_id,parent_revision_id) REFERENCES revisions(project_id,revision_id))""",
    """CREATE TABLE human_review_events (
        project_id TEXT NOT NULL,event_id TEXT NOT NULL,claim_id TEXT NOT NULL,
        action TEXT NOT NULL CHECK(action IN ('accepted','rejected','reopened')),
        payload_json TEXT NOT NULL CHECK(json_valid(payload_json)),created_at TEXT NOT NULL,
        PRIMARY KEY(project_id,event_id),
        FOREIGN KEY(project_id,claim_id) REFERENCES claims(project_id,claim_id))""",
)
