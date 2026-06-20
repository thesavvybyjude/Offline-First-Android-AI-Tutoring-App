"""
conftest.py — shared pytest fixtures for the offline AI tutor test suite.
Run all tests: pytest tests/ -v
Run one phase: pytest tests/test_phase1_environment.py -v
"""

import os
import sqlite3
import tempfile
import json
import pytest
import numpy as np


# ─── Paths ─────────────────────────────────────────────────────────────────
MODEL_PATH = os.environ.get("TUTOR_MODEL_PATH", "models/phi3-mini-q4_k_m.gguf")
INDEX_PATH  = os.environ.get("TUTOR_INDEX_PATH", "data/corpus.index")
CHUNKS_PATH = os.environ.get("TUTOR_CHUNKS_PATH", "data/chunks.json")
DB_PATH     = os.environ.get("TUTOR_DB_PATH",    ":memory:")


# ─── SQLite schema helper ───────────────────────────────────────────────────
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS students (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    grade_level TEXT,
    school_id  TEXT,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    synced      BOOLEAN  DEFAULT 0
);

CREATE TABLE IF NOT EXISTS knowledge_items (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    subject      TEXT NOT NULL,
    question     TEXT NOT NULL,
    answer       TEXT NOT NULL,
    source_chunk TEXT,
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS repetition_records (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id   INTEGER NOT NULL REFERENCES students(id),
    item_id      INTEGER NOT NULL REFERENCES knowledge_items(id),
    ease_factor  REAL    DEFAULT 2.5,
    interval_days INTEGER DEFAULT 1,
    repetitions  INTEGER DEFAULT 0,
    last_quality INTEGER DEFAULT 0,
    next_review  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    synced       BOOLEAN  DEFAULT 0
);

CREATE TABLE IF NOT EXISTS sync_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER REFERENCES students(id),
    table_name TEXT,
    record_id  INTEGER,
    action     TEXT,
    synced_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    success    BOOLEAN  DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_rep_student_review
    ON repetition_records(student_id, next_review);

CREATE TRIGGER IF NOT EXISTS trg_rep_updated
AFTER UPDATE ON repetition_records
BEGIN
    UPDATE repetition_records
    SET updated_at = CURRENT_TIMESTAMP, synced = 0
    WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_student_updated
AFTER UPDATE ON students
BEGIN
    UPDATE students
    SET updated_at = CURRENT_TIMESTAMP, synced = 0
    WHERE id = NEW.id;
END;
"""


@pytest.fixture
def db():
    """In-memory SQLite DB with full schema applied."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQL)
    yield conn
    conn.close()


@pytest.fixture
def populated_db(db):
    """DB pre-loaded with 1 student, 30 knowledge items, 30 repetition records."""
    db.execute(
        "INSERT INTO students (name, grade_level, school_id) VALUES (?,?,?)",
        ("Amara Okafor", "SS2", "SCH001")
    )
    student_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

    from datetime import date, timedelta
    today = date.today()
    for i in range(30):
        db.execute(
            "INSERT INTO knowledge_items (subject, question, answer, source_chunk) VALUES (?,?,?,?)",
            ("Biology", f"Question {i}", f"Answer {i}", f"Chunk text {i}")
        )
        item_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        # half due today, half due in future
        offset = 0 if i < 15 else (i - 14)
        next_review = (today + timedelta(days=offset)).isoformat()
        db.execute(
            """INSERT INTO repetition_records
               (student_id, item_id, ease_factor, interval_days, repetitions, next_review)
               VALUES (?,?,?,?,?,?)""",
            (student_id, item_id, 2.5, 1, 0, next_review)
        )
    db.commit()
    return db, student_id


@pytest.fixture
def tmp_dir():
    """Temporary directory for file-based tests."""
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def sample_chunks():
    """20 short curriculum-like text chunks for RAG tests."""
    return [
        f"Biology concept {i}: This is a description of concept number {i} "
        f"related to cellular processes and osmosis in plant cells."
        for i in range(20)
    ]


@pytest.fixture
def sample_embeddings(sample_chunks):
    """Fake 384-dim float32 embeddings for 20 chunks (deterministic)."""
    np.random.seed(42)
    return np.random.rand(len(sample_chunks), 384).astype("float32")
