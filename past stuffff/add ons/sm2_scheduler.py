"""
SM2 Spaced Repetition Scheduler.
Implements the SuperMemo SM-2 algorithm over SQLite3.
All operations work fully offline; synced flag marks rows for delta push.
"""

from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Generator, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SM2 Constants
# ---------------------------------------------------------------------------

MIN_EASE_FACTOR = 1.3      # EF never drops below this
INITIAL_EASE_FACTOR = 2.5
DAILY_REVIEW_LIMIT = 20

# Interval schedule for first reviews (days)
FIRST_INTERVAL = 1
SECOND_INTERVAL = 6

# Quality thresholds
QUALITY_RESET_THRESHOLD = 3   # quality < 3 → reset to day 1
QUALITY_MAX = 5
QUALITY_MIN = 0

SCHEMA_SQL = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS students (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    grade_level TEXT NOT NULL DEFAULT 'SS2',
    school_id   TEXT,
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now')),
    updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now')),
    synced      INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS knowledge_items (
    id           TEXT PRIMARY KEY,
    subject      TEXT NOT NULL,
    question     TEXT NOT NULL,
    answer       TEXT NOT NULL,
    source_chunk TEXT,
    difficulty   INTEGER NOT NULL DEFAULT 3,
    created_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now'))
);

CREATE TABLE IF NOT EXISTS repetition_records (
    id              TEXT PRIMARY KEY,
    student_id      TEXT NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    item_id         TEXT NOT NULL REFERENCES knowledge_items(id) ON DELETE CASCADE,
    ease_factor     REAL NOT NULL DEFAULT 2.5,
    interval_days   INTEGER NOT NULL DEFAULT 1,
    repetitions     INTEGER NOT NULL DEFAULT 0,
    last_quality    INTEGER,
    next_review     TEXT NOT NULL DEFAULT (date('now')),
    updated_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now')),
    synced          INTEGER NOT NULL DEFAULT 0,
    UNIQUE(student_id, item_id)
);

CREATE TABLE IF NOT EXISTS sync_log (
    id          TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    student_id  TEXT REFERENCES students(id),
    table_name  TEXT NOT NULL,
    record_id   TEXT NOT NULL,
    action      TEXT NOT NULL CHECK(action IN ('INSERT', 'UPDATE', 'DELETE')),
    payload     TEXT,
    synced_at   TEXT,
    success     INTEGER DEFAULT 0
);

-- Triggers: mark rows dirty on write
CREATE TRIGGER IF NOT EXISTS trg_students_update
AFTER UPDATE ON students
FOR EACH ROW BEGIN
    UPDATE students SET updated_at = strftime('%Y-%m-%dT%H:%M:%S', 'now'), synced = 0
    WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_repetition_update
AFTER UPDATE ON repetition_records
FOR EACH ROW
WHEN NEW.last_quality IS NOT OLD.last_quality
  OR NEW.ease_factor != OLD.ease_factor
  OR NEW.interval_days != OLD.interval_days
  OR NEW.repetitions != OLD.repetitions
  OR NEW.next_review != OLD.next_review
BEGIN
    UPDATE repetition_records
    SET updated_at = strftime('%Y-%m-%dT%H:%M:%S', 'now'), synced = 0
    WHERE id = NEW.id;
    INSERT INTO sync_log (table_name, record_id, action, student_id)
    VALUES ('repetition_records', NEW.id, 'UPDATE', NEW.student_id);
END;

CREATE TRIGGER IF NOT EXISTS trg_repetition_insert
AFTER INSERT ON repetition_records
FOR EACH ROW BEGIN
    INSERT INTO sync_log (table_name, record_id, action, student_id)
    VALUES ('repetition_records', NEW.id, 'INSERT', NEW.student_id);
END;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_rep_next_review ON repetition_records(student_id, next_review);
CREATE INDEX IF NOT EXISTS idx_sync_log_unsync ON sync_log(success) WHERE success = 0;
"""


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class KnowledgeItem:
    id: str
    subject: str
    question: str
    answer: str
    source_chunk: Optional[str] = None
    difficulty: int = 3


@dataclass
class RepetitionRecord:
    id: str
    student_id: str
    item_id: str
    ease_factor: float = INITIAL_EASE_FACTOR
    interval_days: int = 1
    repetitions: int = 0
    last_quality: Optional[int] = None
    next_review: str = ""       # ISO date string YYYY-MM-DD
    updated_at: str = ""
    synced: int = 0


@dataclass
class ReviewSession:
    student_id: str
    items: list[tuple[RepetitionRecord, KnowledgeItem]]
    generated_at: str = ""

    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = date.today().isoformat()

    def is_empty(self) -> bool:
        return len(self.items) == 0


@dataclass
class SM2Result:
    record_id: str
    quality: int
    new_ease_factor: float
    new_interval_days: int
    new_repetitions: int
    next_review_date: str
    was_reset: bool


# ---------------------------------------------------------------------------
# SM2 Algorithm (pure function — easy to test)
# ---------------------------------------------------------------------------

def compute_sm2(
    quality: int,
    ease_factor: float,
    interval_days: int,
    repetitions: int,
) -> tuple[float, int, int]:
    """
    Pure SM-2 computation. Returns (new_ef, new_interval, new_repetitions).

    quality: 0–5 (0=complete blackout, 5=perfect recall)
    """
    if not (QUALITY_MIN <= quality <= QUALITY_MAX):
        raise ValueError(f"Quality must be {QUALITY_MIN}–{QUALITY_MAX}, got {quality}")

    if quality < QUALITY_RESET_THRESHOLD:
        # Failed — reset to start
        return ease_factor, FIRST_INTERVAL, 0

    # Update ease factor
    new_ef = ease_factor + (0.1 - (QUALITY_MAX - quality) * (0.08 + (QUALITY_MAX - quality) * 0.02))
    new_ef = max(MIN_EASE_FACTOR, new_ef)

    # Update interval
    new_reps = repetitions + 1
    if new_reps == 1:
        new_interval = FIRST_INTERVAL
    elif new_reps == 2:
        new_interval = SECOND_INTERVAL
    else:
        new_interval = round(interval_days * new_ef)

    return new_ef, new_interval, new_reps


# ---------------------------------------------------------------------------
# SM2 Scheduler (SQLite-backed)
# ---------------------------------------------------------------------------

class SM2Scheduler:
    """
    Manages flashcard scheduling via SM-2 over SQLite3.
    
    Usage:
        scheduler = SM2Scheduler(db_path=Path("data/tutor.db"))
        scheduler.init_db()
        
        # Get today's review queue
        session = scheduler.get_review_session(student_id="stu_001")
        
        # After student rates a card
        result = scheduler.record_response(record_id="rec_abc", quality=4)
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    # --- Setup ---

    def init_db(self) -> None:
        """Create schema if not exists. Safe to call multiple times."""
        with self._connect() as conn:
            conn.executescript(SCHEMA_SQL)
        logger.info(f"Database initialized: {self.db_path}")

    # --- Students ---

    def upsert_student(self, student_id: str, name: str, grade_level: str = "SS2", school_id: Optional[str] = None) -> None:
        sql = """
            INSERT INTO students (id, name, grade_level, school_id)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                grade_level = excluded.grade_level,
                school_id = excluded.school_id
        """
        with self._connect() as conn:
            conn.execute(sql, (student_id, name, grade_level, school_id))

    def get_student(self, student_id: str) -> Optional[dict]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM students WHERE id = ?", (student_id,)
            ).fetchone()
        return dict(row) if row else None

    # --- Knowledge Items ---

    def upsert_knowledge_item(self, item: KnowledgeItem) -> None:
        sql = """
            INSERT INTO knowledge_items (id, subject, question, answer, source_chunk, difficulty)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                question = excluded.question,
                answer = excluded.answer,
                source_chunk = excluded.source_chunk
        """
        with self._connect() as conn:
            conn.execute(sql, (
                item.id, item.subject, item.question,
                item.answer, item.source_chunk, item.difficulty
            ))

    def seed_items_for_student(self, student_id: str, subject: Optional[str] = None) -> int:
        """
        Create repetition_records for all knowledge_items the student doesn't have yet.
        Returns number of new records created.
        """
        import uuid
        filter_sql = "AND ki.subject = ?" if subject else ""
        params = (student_id, subject) if subject else (student_id,)

        with self._connect() as conn:
            items = conn.execute(f"""
                SELECT ki.id FROM knowledge_items ki
                WHERE ki.id NOT IN (
                    SELECT item_id FROM repetition_records WHERE student_id = ?
                )
                {filter_sql}
            """, params).fetchall()

            if not items:
                return 0

            today = date.today().isoformat()
            records = [
                (str(uuid.uuid4()), student_id, row["id"], INITIAL_EASE_FACTOR, 1, 0, today)
                for row in items
            ]
            conn.executemany("""
                INSERT OR IGNORE INTO repetition_records
                    (id, student_id, item_id, ease_factor, interval_days, repetitions, next_review)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, records)
            logger.info(f"Seeded {len(records)} items for student {student_id}")
            return len(records)

    # --- Review Session ---

    def get_review_session(
        self,
        student_id: str,
        limit: int = DAILY_REVIEW_LIMIT,
        subject: Optional[str] = None,
    ) -> ReviewSession:
        """
        Return today's due cards, ordered by most overdue first.
        Joins repetition_records with knowledge_items.
        """
        today = date.today().isoformat()
        filter_sql = "AND ki.subject = ?" if subject else ""
        params: tuple = (student_id, today, limit)
        if subject:
            params = (student_id, today, subject, limit)

        sql = f"""
            SELECT rr.*, ki.subject, ki.question, ki.answer, ki.source_chunk, ki.difficulty
            FROM repetition_records rr
            JOIN knowledge_items ki ON rr.item_id = ki.id
            WHERE rr.student_id = ?
              AND rr.next_review <= ?
              {filter_sql}
            ORDER BY rr.next_review ASC
            LIMIT ?
        """
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()

        session_items = []
        for row in rows:
            d = dict(row)
            record = RepetitionRecord(
                id=d["id"], student_id=d["student_id"], item_id=d["item_id"],
                ease_factor=d["ease_factor"], interval_days=d["interval_days"],
                repetitions=d["repetitions"], last_quality=d["last_quality"],
                next_review=d["next_review"], synced=d["synced"],
            )
            item = KnowledgeItem(
                id=d["item_id"], subject=d["subject"], question=d["question"],
                answer=d["answer"], source_chunk=d["source_chunk"], difficulty=d["difficulty"],
            )
            session_items.append((record, item))

        logger.debug(f"Review session for {student_id}: {len(session_items)} cards due")
        return ReviewSession(student_id=student_id, items=session_items)

    def get_due_count(self, student_id: str) -> int:
        today = date.today().isoformat()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as n FROM repetition_records WHERE student_id=? AND next_review<=?",
                (student_id, today)
            ).fetchone()
        return row["n"] if row else 0

    # --- Recording Responses ---

    def record_response(self, record_id: str, quality: int) -> SM2Result:
        """
        Apply SM-2 algorithm and persist new state.
        quality: 0–5 (0 = complete blackout, 5 = perfect)
        """
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM repetition_records WHERE id=?", (record_id,)
            ).fetchone()
            if not row:
                raise ValueError(f"Record not found: {record_id}")

            d = dict(row)
            new_ef, new_interval, new_reps = compute_sm2(
                quality=quality,
                ease_factor=d["ease_factor"],
                interval_days=d["interval_days"],
                repetitions=d["repetitions"],
            )
            next_review = (date.today() + timedelta(days=new_interval)).isoformat()
            was_reset = quality < QUALITY_RESET_THRESHOLD

            conn.execute("""
                UPDATE repetition_records
                SET ease_factor=?, interval_days=?, repetitions=?,
                    last_quality=?, next_review=?
                WHERE id=?
            """, (new_ef, new_interval, new_reps, quality, next_review, record_id))

        result = SM2Result(
            record_id=record_id,
            quality=quality,
            new_ease_factor=new_ef,
            new_interval_days=new_interval,
            new_repetitions=new_reps,
            next_review_date=next_review,
            was_reset=was_reset,
        )
        logger.debug(
            f"SM2 update {record_id}: q={quality} ef={new_ef:.2f} "
            f"interval={new_interval}d next={next_review} reset={was_reset}"
        )
        return result

    # --- Progress / Analytics ---

    def get_retention_stats(self, student_id: str, days: int = 7) -> list[dict]:
        """
        Returns per-day review counts and success rates for the past N days.
        Used for the dashboard 7-day bar chart.
        """
        sql = """
            SELECT
                date(rr.updated_at) as review_date,
                COUNT(*) as total,
                SUM(CASE WHEN rr.last_quality >= 3 THEN 1 ELSE 0 END) as passed
            FROM repetition_records rr
            WHERE rr.student_id = ?
              AND rr.updated_at >= date('now', ?)
            GROUP BY date(rr.updated_at)
            ORDER BY review_date ASC
        """
        with self._connect() as conn:
            rows = conn.execute(sql, (student_id, f"-{days} days")).fetchall()
        return [dict(r) for r in rows]

    def get_mastered_count(self, student_id: str, threshold_interval: int = 21) -> int:
        """Items with interval >= threshold are considered 'mastered'."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as n FROM repetition_records "
                "WHERE student_id=? AND interval_days>=?",
                (student_id, threshold_interval)
            ).fetchone()
        return row["n"] if row else 0

    def get_streak(self, student_id: str) -> int:
        """Count of consecutive days with at least one review. Max 30 days lookback."""
        sql = """
            SELECT DISTINCT date(updated_at) as d
            FROM repetition_records
            WHERE student_id=?
              AND last_quality IS NOT NULL
              AND updated_at >= date('now', '-30 days')
            ORDER BY d DESC
        """
        with self._connect() as conn:
            rows = conn.execute(sql, (student_id,)).fetchall()

        streak = 0
        prev = date.today()
        for row in rows:
            d = date.fromisoformat(row["d"])
            if (prev - d).days <= 1:
                streak += 1
                prev = d
            else:
                break
        return streak

    # --- Unsynced Records (for SyncLayer) ---

    def get_unsynced_records(self, student_id: str) -> list[dict]:
        sql = """
            SELECT sl.id as sync_log_id, rr.*
            FROM sync_log sl
            JOIN repetition_records rr ON sl.record_id = rr.id
            WHERE sl.student_id=? AND sl.success=0
            ORDER BY rr.updated_at ASC
        """
        with self._connect() as conn:
            rows = conn.execute(sql, (student_id,)).fetchall()
        return [dict(r) for r in rows]

    def mark_synced(self, record_ids: list[str]) -> None:
        """
        Mark sync_log entries as successful and update the synced flag on
        the corresponding repetition_records.
        record_ids: repetition_record IDs accepted by the server.
        """
        if not record_ids:
            return
        placeholders = ",".join("?" * len(record_ids))
        now = datetime.now().isoformat()
        with self._connect() as conn:
            conn.execute(
                f"UPDATE sync_log SET success=1, synced_at=? WHERE record_id IN ({placeholders}) AND success=0",
                [now] + list(record_ids)
            )
            conn.execute(
                f"UPDATE repetition_records SET synced=1 WHERE id IN ({placeholders})",
                list(record_ids)
            )

    # --- Internal ---

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(str(self.db_path), detect_types=sqlite3.PARSE_DECLTYPES)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
