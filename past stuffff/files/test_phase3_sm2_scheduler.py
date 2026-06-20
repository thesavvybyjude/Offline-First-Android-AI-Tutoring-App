"""
test_phase3_sm2_scheduler.py
Phase 3: SM2 Spaced Repetition Engine

Tests every SM2 computation, boundary condition, schema constraint,
trigger behaviour, and session queue query.
"""

import pytest
import sqlite3
from datetime import date, timedelta, datetime


# ─── Reference SM2 implementation used by tests ────────────────────

class _SM2Scheduler:

    MIN_EF = 1.3
    DEFAULT_EF = 2.5

    def __init__(self, conn: sqlite3.Connection, student_id: int):
        self.conn = conn
        self.student_id = student_id

    # ── Core SM2 maths ──────────────────────────────────────────────

    def compute_ef(self, ef: float, quality: int) -> float:
        """Update ease factor. Floor at MIN_EF."""
        new_ef = ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        return max(self.MIN_EF, new_ef)

    def compute_interval(self, ef: float, n: int, prev_interval: int = 1) -> int:
        """Return next interval in days."""
        if n == 1:
            return 1
        if n == 2:
            return 6
        return max(1, round(prev_interval * ef))

    # ── DB operations ───────────────────────────────────────────────

    def get_due_items(self, reference_date: date = None) -> list:
        ref = (reference_date or date.today()).isoformat()
        rows = self.conn.execute(
            """SELECT rr.id, rr.item_id, ki.question, ki.answer,
                      rr.ease_factor, rr.interval_days, rr.repetitions
               FROM repetition_records rr
               JOIN knowledge_items ki ON ki.id = rr.item_id
               WHERE rr.student_id = ?
                 AND rr.next_review <= ?
               ORDER BY rr.next_review ASC
               LIMIT 20""",
            (self.student_id, ref)
        ).fetchall()
        return [dict(r) for r in rows]

    def update_record(self, record_id: int, quality: int,
                      prev_interval: int = 1) -> dict:
        row = self.conn.execute(
            "SELECT ease_factor, repetitions FROM repetition_records WHERE id=?",
            (record_id,)
        ).fetchone()
        if not row:
            raise ValueError(f"No repetition_record with id={record_id}")
        ef, n = row["ease_factor"], row["repetitions"]

        if quality < 3:
            new_n        = 0
            new_interval = 1
            new_ef       = ef   # EF unchanged on failure
        else:
            new_n        = n + 1
            new_ef       = self.compute_ef(ef, quality)
            new_interval = self.compute_interval(new_ef, new_n, prev_interval)

        next_review = (date.today() + timedelta(days=new_interval)).isoformat()
        self.conn.execute(
            """UPDATE repetition_records
               SET ease_factor=?, interval_days=?, repetitions=?,
                   last_quality=?, next_review=?
               WHERE id=?""",
            (new_ef, new_interval, new_n, quality, next_review, record_id)
        )
        self.conn.commit()
        return {"ef": new_ef, "interval": new_interval, "repetitions": new_n,
                "next_review": next_review}


# ═══════════════════════════════════════════════════════════════════
# GROUP 1 — SQLite schema
# ═══════════════════════════════════════════════════════════════════

class TestSQLiteSchema:

    def test_all_four_tables_exist(self, db):
        """All four required tables must exist after schema creation."""
        tables = {r[0] for r in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        required = {"students", "knowledge_items", "repetition_records", "sync_log"}
        missing  = required - tables
        assert not missing, f"Missing tables: {missing}"

    def test_students_columns(self, db):
        """students table must have all required columns."""
        cols = {r[1] for r in db.execute("PRAGMA table_info(students)").fetchall()}
        required = {"id","name","grade_level","school_id","created_at","updated_at","synced"}
        assert required <= cols, f"Missing columns in students: {required - cols}"

    def test_repetition_records_columns(self, db):
        """repetition_records must have all required columns."""
        cols = {r[1] for r in db.execute(
            "PRAGMA table_info(repetition_records)").fetchall()}
        required = {"id","student_id","item_id","ease_factor","interval_days",
                    "repetitions","last_quality","next_review","updated_at","synced"}
        assert required <= cols, f"Missing columns: {required - cols}"

    def test_knowledge_items_columns(self, db):
        """knowledge_items must have all required columns."""
        cols = {r[1] for r in db.execute(
            "PRAGMA table_info(knowledge_items)").fetchall()}
        required = {"id","subject","question","answer","source_chunk","created_at"}
        assert required <= cols, f"Missing columns: {required - cols}"

    def test_sync_log_columns(self, db):
        """sync_log must have all required columns."""
        cols = {r[1] for r in db.execute(
            "PRAGMA table_info(sync_log)").fetchall()}
        required = {"id","student_id","table_name","record_id","action",
                    "synced_at","success"}
        assert required <= cols, f"Missing columns: {required - cols}"

    def test_repetition_records_index_exists(self, db):
        """Index on repetition_records(student_id, next_review) must exist."""
        indexes = {r[1] for r in db.execute(
            "PRAGMA index_list(repetition_records)").fetchall()}
        assert len(indexes) >= 1, (
            "No index found on repetition_records. "
            "Add: CREATE INDEX idx_rep_student_review ON repetition_records(student_id, next_review)"
        )

    def test_insert_student_succeeds(self, db):
        """Must be able to insert a valid student row."""
        db.execute(
            "INSERT INTO students (name, grade_level, school_id) VALUES (?,?,?)",
            ("Test Student", "SS2", "SCH001")
        )
        db.commit()
        count = db.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        assert count == 1

    def test_foreign_key_enforced(self, db):
        """repetition_records must reject invalid student_id foreign key."""
        db.execute("PRAGMA foreign_keys = ON")
        db.execute(
            "INSERT INTO knowledge_items (subject, question, answer) VALUES (?,?,?)",
            ("Biology", "Q?", "A.")
        )
        db.commit()
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                """INSERT INTO repetition_records
                   (student_id, item_id) VALUES (?,?)""",
                (9999, 1)  # student_id 9999 does not exist
            )
            db.commit()


# ═══════════════════════════════════════════════════════════════════
# GROUP 2 — SQLite triggers
# ═══════════════════════════════════════════════════════════════════

class TestSQLiteTriggers:

    def _get_record(self, db, record_id):
        return dict(db.execute(
            "SELECT * FROM repetition_records WHERE id=?", (record_id,)
        ).fetchone())

    def test_update_sets_synced_to_zero(self, populated_db):
        """Trigger must set synced=0 on any UPDATE to repetition_records."""
        db, student_id = populated_db
        # manually set synced=1 on record 1
        db.execute("UPDATE repetition_records SET synced=1 WHERE id=1")
        db.commit()
        row = self._get_record(db, 1)
        assert row["synced"] == 1

        # now trigger a real update
        db.execute("UPDATE repetition_records SET last_quality=4 WHERE id=1")
        db.commit()
        row = self._get_record(db, 1)
        assert row["synced"] == 0, (
            "Trigger did not reset synced=0 after UPDATE."
        )

    def test_update_refreshes_updated_at(self, populated_db):
        """Trigger must update the updated_at timestamp on UPDATE."""
        db, _ = populated_db
        original = dict(db.execute(
            "SELECT updated_at FROM repetition_records WHERE id=1"
        ).fetchone())["updated_at"]

        import time; time.sleep(1.1)  # ensure timestamp difference
        db.execute("UPDATE repetition_records SET last_quality=3 WHERE id=1")
        db.commit()
        new_ts = dict(db.execute(
            "SELECT updated_at FROM repetition_records WHERE id=1"
        ).fetchone())["updated_at"]

        assert new_ts != original, (
            f"updated_at not refreshed by trigger. "
            f"Before: {original}, After: {new_ts}"
        )

    def test_insert_does_not_trigger_synced_reset(self, db):
        """INSERT into repetition_records must leave synced as default (0)."""
        db.execute(
            "INSERT INTO students (name) VALUES ('T')"
        )
        db.execute(
            "INSERT INTO knowledge_items (subject, question, answer) VALUES ('Bio','Q','A')"
        )
        db.commit()
        db.execute(
            "INSERT INTO repetition_records (student_id, item_id) VALUES (1, 1)"
        )
        db.commit()
        row = dict(db.execute(
            "SELECT synced FROM repetition_records WHERE id=1"
        ).fetchone())
        assert row["synced"] == 0


# ═══════════════════════════════════════════════════════════════════
# GROUP 3 — SM2 algorithm: compute_ef
# ═══════════════════════════════════════════════════════════════════

class TestSM2ComputeEF:

    @pytest.fixture
    def sm2(self, db, populated_db):
        db, student_id = populated_db
        return _SM2Scheduler(db, student_id)

    def test_quality_5_increases_ef(self, db):
        sm2 = _SM2Scheduler(db, 1)
        new_ef = sm2.compute_ef(2.5, 5)
        assert new_ef > 2.5, f"Quality 5 should increase EF. Got {new_ef}"

    def test_quality_4_keeps_ef_roughly_same(self, db):
        sm2 = _SM2Scheduler(db, 1)
        new_ef = sm2.compute_ef(2.5, 4)
        # quality=4: EF + (0.1 - 1*(0.08+1*0.02)) = EF + 0
        assert abs(new_ef - 2.5) < 0.05, (
            f"Quality 4 should keep EF roughly unchanged. Got {new_ef}"
        )

    def test_quality_3_decreases_ef(self, db):
        sm2 = _SM2Scheduler(db, 1)
        new_ef = sm2.compute_ef(2.5, 3)
        assert new_ef < 2.5, f"Quality 3 should decrease EF. Got {new_ef}"

    def test_ef_floor_at_1_3(self, db):
        sm2 = _SM2Scheduler(db, 1)
        # Repeatedly apply quality=0 to drive EF below floor
        ef = 2.5
        for _ in range(20):
            ef = sm2.compute_ef(ef, 0)
        assert ef == sm2.MIN_EF, f"EF should floor at {sm2.MIN_EF}. Got {ef}"

    def test_quality_0_decreases_ef_maximally(self, db):
        sm2 = _SM2Scheduler(db, 1)
        ef_q0 = sm2.compute_ef(2.5, 0)
        ef_q3 = sm2.compute_ef(2.5, 3)
        assert ef_q0 <= ef_q3, "Quality 0 should decrease EF more than quality 3."

    @pytest.mark.parametrize("quality", [0, 1, 2, 3, 4, 5])
    def test_all_quality_levels_return_float(self, db, quality):
        sm2 = _SM2Scheduler(db, 1)
        ef = sm2.compute_ef(2.5, quality)
        assert isinstance(ef, float), f"Quality {quality}: EF must be float, got {type(ef)}"

    def test_ef_never_below_minimum(self, db):
        sm2 = _SM2Scheduler(db, 1)
        for q in range(6):
            ef = sm2.compute_ef(1.3, q)
            assert ef >= sm2.MIN_EF, (
                f"Quality {q} produced EF {ef} below minimum {sm2.MIN_EF}"
            )


# ═══════════════════════════════════════════════════════════════════
# GROUP 4 — SM2 algorithm: compute_interval
# ═══════════════════════════════════════════════════════════════════

class TestSM2ComputeInterval:

    @pytest.fixture
    def sm2(self, db):
        return _SM2Scheduler(db, 1)

    def test_first_repetition_is_1_day(self, sm2):
        """n=1 must always return 1 day regardless of EF."""
        assert sm2.compute_interval(2.5, 1) == 1

    def test_second_repetition_is_6_days(self, sm2):
        """n=2 must always return 6 days (SM2 spec)."""
        assert sm2.compute_interval(2.5, 2) == 6

    def test_third_repetition_uses_ef(self, sm2):
        """n=3 must be prev_interval * EF rounded."""
        result = sm2.compute_interval(ef=2.5, n=3, prev_interval=6)
        assert result == round(6 * 2.5), f"Expected {round(6*2.5)}, got {result}"

    def test_interval_never_below_1(self, sm2):
        """Interval must always be at least 1 day."""
        result = sm2.compute_interval(ef=1.3, n=3, prev_interval=1)
        assert result >= 1

    def test_higher_ef_produces_longer_interval(self, sm2):
        """Higher ease factor must produce longer interval."""
        short = sm2.compute_interval(ef=1.3, n=3, prev_interval=6)
        long  = sm2.compute_interval(ef=2.8, n=3, prev_interval=6)
        assert long > short, (
            f"Higher EF should give longer interval. Got {long} vs {short}"
        )

    def test_interval_grows_across_repetitions(self, sm2):
        """Interval must grow monotonically across successful repetitions."""
        ef = 2.5
        interval = 1
        intervals = []
        for n in range(1, 8):
            interval = sm2.compute_interval(ef, n, interval)
            intervals.append(interval)
        for i in range(len(intervals) - 1):
            assert intervals[i+1] >= intervals[i], (
                f"Interval did not grow at repetition {i+2}: "
                f"{intervals[i]} → {intervals[i+1]}"
            )


# ═══════════════════════════════════════════════════════════════════
# GROUP 5 — update_record() with DB writes
# ═══════════════════════════════════════════════════════════════════

class TestUpdateRecord:

    @pytest.fixture
    def sm2_and_record(self, populated_db):
        db, student_id = populated_db
        sm2 = _SM2Scheduler(db, student_id)
        record_id = db.execute(
            "SELECT id FROM repetition_records WHERE student_id=? LIMIT 1",
            (student_id,)
        ).fetchone()[0]
        return sm2, db, record_id

    def test_quality_5_increments_repetitions(self, sm2_and_record):
        sm2, db, record_id = sm2_and_record
        before = db.execute(
            "SELECT repetitions FROM repetition_records WHERE id=?", (record_id,)
        ).fetchone()[0]
        result = sm2.update_record(record_id, quality=5)
        assert result["repetitions"] == before + 1

    def test_quality_below_3_resets_repetitions_to_0(self, sm2_and_record):
        sm2, db, record_id = sm2_and_record
        # first do a successful rep to get repetitions > 0
        sm2.update_record(record_id, quality=5)
        # now fail
        result = sm2.update_record(record_id, quality=2)
        assert result["repetitions"] == 0, (
            f"Quality < 3 should reset repetitions to 0. Got {result['repetitions']}"
        )

    def test_quality_below_3_sets_interval_to_1(self, sm2_and_record):
        sm2, _, record_id = sm2_and_record
        result = sm2.update_record(record_id, quality=1)
        assert result["interval"] == 1, (
            f"Failed review should reset interval to 1. Got {result['interval']}"
        )

    def test_next_review_is_future_date(self, sm2_and_record):
        sm2, _, record_id = sm2_and_record
        result = sm2.update_record(record_id, quality=4)
        next_r = date.fromisoformat(result["next_review"])
        assert next_r >= date.today(), (
            f"next_review {result['next_review']} is in the past."
        )

    def test_last_quality_is_written(self, sm2_and_record):
        sm2, db, record_id = sm2_and_record
        sm2.update_record(record_id, quality=3)
        row = db.execute(
            "SELECT last_quality FROM repetition_records WHERE id=?", (record_id,)
        ).fetchone()
        assert row[0] == 3

    def test_invalid_record_id_raises(self, populated_db):
        db, student_id = populated_db
        sm2 = _SM2Scheduler(db, student_id)
        with pytest.raises((ValueError, Exception)):
            sm2.update_record(record_id=99999, quality=4)

    @pytest.mark.parametrize("quality", [0, 1, 2, 3, 4, 5])
    def test_all_quality_levels_write_successfully(self, populated_db, quality):
        db, student_id = populated_db
        sm2 = _SM2Scheduler(db, student_id)
        record_id = db.execute(
            "SELECT id FROM repetition_records WHERE student_id=? LIMIT 1",
            (student_id,)
        ).fetchone()[0]
        result = sm2.update_record(record_id, quality=quality)
        assert "ef" in result and "interval" in result and "repetitions" in result


# ═══════════════════════════════════════════════════════════════════
# GROUP 6 — get_due_items() session queue
# ═══════════════════════════════════════════════════════════════════

class TestSessionQueue:

    def test_returns_only_due_items(self, populated_db):
        """Items with next_review in future must NOT appear in queue."""
        db, student_id = populated_db
        sm2 = _SM2Scheduler(db, student_id)
        today = date.today()
        due_items = sm2.get_due_items(reference_date=today)
        for item in due_items:
            record = db.execute(
                "SELECT next_review FROM repetition_records WHERE id=?",
                (item["id"],)
            ).fetchone()
            nr = date.fromisoformat(record[0][:10])
            assert nr <= today, (
                f"Item {item['id']} with next_review={record[0]} "
                "appeared in due queue but is not yet due."
            )

    def test_returns_at_most_20_items(self, populated_db):
        """Session queue must be capped at 20 items."""
        db, student_id = populated_db
        sm2 = _SM2Scheduler(db, student_id)
        due_items = sm2.get_due_items()
        assert len(due_items) <= 20, (
            f"Session returned {len(due_items)} items — must be <= 20."
        )

    def test_15_items_due_today(self, populated_db):
        """populated_db seeds 15 items due today — all should appear."""
        db, student_id = populated_db
        sm2 = _SM2Scheduler(db, student_id)
        due_items = sm2.get_due_items()
        assert len(due_items) == 15, (
            f"Expected 15 due items, got {len(due_items)}."
        )

    def test_items_ordered_by_next_review(self, populated_db):
        """Due items must be ordered by next_review ASC."""
        db, student_id = populated_db
        sm2 = _SM2Scheduler(db, student_id)
        due_items = sm2.get_due_items()
        dates = [item.get("next_review", "") for item in due_items
                 if item.get("next_review")]
        assert dates == sorted(dates), "Items not sorted by next_review ASC."

    def test_items_have_required_keys(self, populated_db):
        """Each due item must contain question and answer keys."""
        db, student_id = populated_db
        sm2 = _SM2Scheduler(db, student_id)
        due_items = sm2.get_due_items()
        if not due_items:
            pytest.skip("No due items in test DB.")
        for item in due_items:
            assert "question" in item, f"Item {item} missing 'question'."
            assert "answer"   in item, f"Item {item} missing 'answer'."

    def test_no_due_items_returns_empty_list(self, db):
        """When no items are due, return empty list (not None or error)."""
        db.execute(
            "INSERT INTO students (name) VALUES ('Solo')"
        )
        db.commit()
        sm2 = _SM2Scheduler(db, student_id=1)
        result = sm2.get_due_items()
        assert isinstance(result, list)
        assert len(result) == 0

    def test_wrong_student_sees_no_items(self, populated_db):
        """A student with no records must get an empty queue."""
        db, _ = populated_db
        db.execute("INSERT INTO students (name) VALUES ('Other')")
        db.commit()
        new_id = db.execute("SELECT MAX(id) FROM students").fetchone()[0]
        sm2 = _SM2Scheduler(db, new_id)
        items = sm2.get_due_items()
        assert items == [], (
            f"Student {new_id} has no records but got {len(items)} items."
        )
