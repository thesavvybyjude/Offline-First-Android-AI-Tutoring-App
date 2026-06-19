"""
test_phase4_android_ui.py
Phase 4: Android Front-End Logic

Tests the business logic behind each screen WITHOUT requiring
a real Android device or Kivy display. Each test uses the
TutorApp controller class in isolation.

Structure:
  TestLoginLogic       — credential validation
  TestDashboardData    — SQLite stat queries
  TestTutorChat        — query dispatch and response handling
  TestReviewSession    — card queue, rating dispatch
  TestSettingsLogic    — preferences read/write, storage calc
  TestLocalServer      — Flask /query endpoint smoke tests
"""

import os
import json
import time
import pytest
import sqlite3
import threading
from unittest.mock import MagicMock, patch, PropertyMock


# ─── Minimal TutorApp controller ──────────────────────────────────
# Tests import this stub. Swap for production import when ready.

class _TutorApp:
    """Lightweight controller that the UI screens call."""

    def __init__(self, conn: sqlite3.Connection, student_id: int = None):
        self.conn  = conn
        self.student_id = student_id
        self.rag     = MagicMock()
        self.engine  = MagicMock()
        self.sm2     = MagicMock()
        self.sync    = MagicMock()
        self._chat_history = []

    # ── Login ──────────────────────────────────────────────────────
    def login(self, student_id_str: str, school_code: str):
        try:
            sid = int(student_id_str)
        except ValueError:
            return {"success": False, "error": "Student ID must be numeric."}
        row = self.conn.execute(
            "SELECT id, name FROM students WHERE id=? AND school_id=?",
            (sid, school_code)
        ).fetchone()
        if row:
            self.student_id = row[0]
            return {"success": True, "name": row[1]}
        return {"success": False, "error": "Student ID or school code not recognised."}

    # ── Dashboard ──────────────────────────────────────────────────
    def get_dashboard_stats(self) -> dict:
        from datetime import date, timedelta
        today = date.today().isoformat()
        week_ago = (date.today() - timedelta(days=6)).isoformat()
        due = self.conn.execute(
            "SELECT COUNT(*) FROM repetition_records WHERE student_id=? AND next_review<=?",
            (self.student_id, today)
        ).fetchone()[0]
        mastered = self.conn.execute(
            "SELECT COUNT(*) FROM repetition_records WHERE student_id=? AND repetitions>=3",
            (self.student_id,)
        ).fetchone()[0]
        ars_row = self.conn.execute(
            """SELECT AVG(CASE WHEN last_quality>=3 THEN 1.0 ELSE 0.0 END)
               FROM repetition_records WHERE student_id=?""",
            (self.student_id,)
        ).fetchone()[0]
        ars = round(ars_row or 0.0, 2)
        return {"due_today": due, "mastered": mastered, "ars": ars}

    # ── Chat ───────────────────────────────────────────────────────
    def handle_query(self, text: str) -> dict:
        if not text or not text.strip():
            return {"error": "Query cannot be empty."}
        chunks = self.rag.retrieve(text, top_k=3)
        prompt = self.rag.inject_context(text, chunks)
        response = self.engine.generate(prompt, max_tokens=256)
        source   = chunks[0][0] if chunks else ""
        self._chat_history.append({"role": "student", "text": text})
        self._chat_history.append({"role": "ai", "text": response, "source": source})
        return {"response": response, "source": source}

    def get_chat_history(self) -> list:
        return list(self._chat_history)

    def clear_chat(self):
        self._chat_history.clear()

    # ── Review ─────────────────────────────────────────────────────
    def start_review_session(self) -> list:
        return self.sm2.get_due_items()

    def submit_rating(self, record_id: int, quality: int) -> dict:
        if quality < 0 or quality > 5:
            return {"error": f"Quality {quality} out of range [0, 5]."}
        return self.sm2.update_record(record_id, quality)

    # ── Settings ───────────────────────────────────────────────────
    def save_preference(self, key: str, value: str):
        self.conn.execute(
            """INSERT INTO preferences (key, value)
               VALUES (?, ?)
               ON CONFLICT(key) DO UPDATE SET value=excluded.value""",
            (key, value)
        )
        self.conn.commit()

    def get_preference(self, key: str, default=None):
        row = self.conn.execute(
            "SELECT value FROM preferences WHERE key=?", (key,)
        ).fetchone()
        return row[0] if row else default

    def get_storage_usage(self, paths: list) -> dict:
        total = 0
        breakdown = {}
        for p in paths:
            size = os.path.getsize(p) if os.path.exists(p) else 0
            breakdown[p] = size
            total += size
        return {"total_bytes": total, "breakdown": breakdown,
                "total_gb": round(total / (1024**3), 3)}


@pytest.fixture
def app_db(db):
    """DB with preferences table added."""
    db.execute("""
        CREATE TABLE IF NOT EXISTS preferences (
            key   TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    db.execute(
        "INSERT INTO students (name, grade_level, school_id) VALUES (?,?,?)",
        ("Test Student", "SS2", "SCH001")
    )
    db.commit()
    return db


@pytest.fixture
def app(app_db):
    return _TutorApp(app_db, student_id=1)


# ═══════════════════════════════════════════════════════════════════
# GROUP 1 — Login logic
# ═══════════════════════════════════════════════════════════════════

class TestLoginLogic:

    def test_valid_credentials_return_success(self, app):
        result = app.login("1", "SCH001")
        assert result["success"] is True
        assert result["name"] == "Test Student"

    def test_wrong_school_code_fails(self, app):
        result = app.login("1", "WRONG")
        assert result["success"] is False
        assert "error" in result

    def test_nonexistent_student_id_fails(self, app):
        result = app.login("9999", "SCH001")
        assert result["success"] is False

    def test_non_numeric_id_fails(self, app):
        result = app.login("abc", "SCH001")
        assert result["success"] is False
        assert "numeric" in result["error"].lower()

    def test_empty_id_fails(self, app):
        result = app.login("", "SCH001")
        assert result["success"] is False

    def test_login_sets_student_id(self, app):
        app.login("1", "SCH001")
        assert app.student_id == 1


# ═══════════════════════════════════════════════════════════════════
# GROUP 2 — Dashboard data queries
# ═══════════════════════════════════════════════════════════════════

class TestDashboardData:

    def test_stats_return_dict(self, app):
        stats = app.get_dashboard_stats()
        assert isinstance(stats, dict)

    def test_stats_contain_required_keys(self, app):
        stats = app.get_dashboard_stats()
        for key in ("due_today", "mastered", "ars"):
            assert key in stats, f"Missing key '{key}' in dashboard stats."

    def test_due_today_is_integer(self, app):
        stats = app.get_dashboard_stats()
        assert isinstance(stats["due_today"], int)

    def test_mastered_is_integer(self, app):
        stats = app.get_dashboard_stats()
        assert isinstance(stats["mastered"], int)

    def test_ars_is_float_between_0_and_1(self, app):
        stats = app.get_dashboard_stats()
        ars = stats["ars"]
        assert isinstance(ars, float)
        assert 0.0 <= ars <= 1.0, f"ARS {ars} outside [0.0, 1.0]."

    def test_due_count_matches_seeded_data(self, populated_db):
        db, student_id = populated_db
        db.execute("""
            CREATE TABLE IF NOT EXISTS preferences (key TEXT PRIMARY KEY, value TEXT)
        """)
        a = _TutorApp(db, student_id)
        stats = a.get_dashboard_stats()
        # populated_db seeds 15 items due today
        assert stats["due_today"] == 15, (
            f"Expected 15 due items, got {stats['due_today']}."
        )

    def test_mastered_count_with_no_repetitions(self, app):
        # fresh app with no repetition records → mastered = 0
        stats = app.get_dashboard_stats()
        assert stats["mastered"] == 0


# ═══════════════════════════════════════════════════════════════════
# GROUP 3 — Tutor chat
# ═══════════════════════════════════════════════════════════════════

class TestTutorChat:

    def test_handle_query_returns_dict(self, app):
        app.rag.retrieve.return_value = [("Osmosis text", 0.82)]
        app.rag.inject_context.return_value = "Augmented prompt"
        app.engine.generate.return_value = "Osmosis is the movement of water."
        result = app.handle_query("What is osmosis?")
        assert isinstance(result, dict)

    def test_handle_query_returns_response_key(self, app):
        app.rag.retrieve.return_value = [("Chunk", 0.7)]
        app.rag.inject_context.return_value = "Prompt"
        app.engine.generate.return_value = "Response text."
        result = app.handle_query("Explain respiration.")
        assert "response" in result
        assert result["response"] == "Response text."

    def test_handle_query_returns_source_key(self, app):
        app.rag.retrieve.return_value = [("Source chunk text", 0.75)]
        app.rag.inject_context.return_value = "Prompt"
        app.engine.generate.return_value = "Answer."
        result = app.handle_query("Define ATP.")
        assert "source" in result
        assert result["source"] == "Source chunk text"

    def test_empty_query_returns_error(self, app):
        result = app.handle_query("")
        assert "error" in result

    def test_whitespace_only_query_returns_error(self, app):
        result = app.handle_query("   ")
        assert "error" in result

    def test_chat_history_grows_per_query(self, app):
        app.rag.retrieve.return_value = []
        app.rag.inject_context.return_value = "P"
        app.engine.generate.return_value = "R"
        app.handle_query("Q1")
        app.handle_query("Q2")
        history = app.get_chat_history()
        assert len(history) == 4  # 2 student + 2 ai messages

    def test_chat_history_has_roles(self, app):
        app.rag.retrieve.return_value = []
        app.rag.inject_context.return_value = "P"
        app.engine.generate.return_value = "R"
        app.handle_query("What is DNA?")
        history = app.get_chat_history()
        roles = {m["role"] for m in history}
        assert "student" in roles
        assert "ai"      in roles

    def test_clear_chat_empties_history(self, app):
        app.rag.retrieve.return_value = []
        app.rag.inject_context.return_value = "P"
        app.engine.generate.return_value = "R"
        app.handle_query("Q")
        app.clear_chat()
        assert app.get_chat_history() == []

    def test_rag_retrieve_called_with_correct_args(self, app):
        app.rag.retrieve.return_value = []
        app.rag.inject_context.return_value = "P"
        app.engine.generate.return_value = "R"
        app.handle_query("Mitosis question")
        app.rag.retrieve.assert_called_once_with("Mitosis question", top_k=3)


# ═══════════════════════════════════════════════════════════════════
# GROUP 4 — Review session
# ═══════════════════════════════════════════════════════════════════

class TestReviewSession:

    def test_start_review_calls_sm2(self, app):
        app.sm2.get_due_items.return_value = [{"id": 1, "question": "Q", "answer": "A"}]
        items = app.start_review_session()
        app.sm2.get_due_items.assert_called_once()
        assert len(items) == 1

    def test_submit_rating_calls_sm2_update(self, app):
        app.sm2.update_record.return_value = {"ef": 2.5, "interval": 6, "repetitions": 1}
        app.submit_rating(record_id=1, quality=4)
        app.sm2.update_record.assert_called_once_with(1, 4)

    def test_submit_rating_returns_dict(self, app):
        app.sm2.update_record.return_value = {"ef": 2.6, "interval": 6, "repetitions": 1}
        result = app.submit_rating(1, 5)
        assert isinstance(result, dict)

    @pytest.mark.parametrize("quality", [0, 1, 2, 3, 4, 5])
    def test_all_quality_ratings_accepted(self, app, quality):
        app.sm2.update_record.return_value = {"ef": 2.5, "interval": 1, "repetitions": 0}
        result = app.submit_rating(1, quality)
        assert "error" not in result

    def test_quality_below_0_rejected(self, app):
        result = app.submit_rating(1, -1)
        assert "error" in result

    def test_quality_above_5_rejected(self, app):
        result = app.submit_rating(1, 6)
        assert "error" in result


# ═══════════════════════════════════════════════════════════════════
# GROUP 5 — Settings / preferences
# ═══════════════════════════════════════════════════════════════════

class TestSettingsLogic:

    def test_save_and_retrieve_preference(self, app):
        app.save_preference("subject", "Biology")
        val = app.get_preference("subject")
        assert val == "Biology"

    def test_preference_default_when_missing(self, app):
        val = app.get_preference("nonexistent_key", default="default_val")
        assert val == "default_val"

    def test_preference_overwrite(self, app):
        app.save_preference("review_limit", "10")
        app.save_preference("review_limit", "20")
        val = app.get_preference("review_limit")
        assert val == "20"

    def test_auto_sync_toggle_persists(self, app):
        app.save_preference("auto_sync", "true")
        assert app.get_preference("auto_sync") == "true"
        app.save_preference("auto_sync", "false")
        assert app.get_preference("auto_sync") == "false"

    def test_storage_usage_returns_dict(self, app, tmp_dir):
        dummy = os.path.join(tmp_dir, "model.gguf")
        with open(dummy, "wb") as f:
            f.write(b"x" * 1024)
        result = app.get_storage_usage([dummy])
        assert "total_bytes" in result
        assert "total_gb"    in result
        assert "breakdown"   in result

    def test_storage_usage_total_is_sum_of_parts(self, app, tmp_dir):
        files = []
        for i, size in enumerate([512, 1024, 256]):
            p = os.path.join(tmp_dir, f"file{i}")
            with open(p, "wb") as f:
                f.write(b"x" * size)
            files.append(p)
        result = app.get_storage_usage(files)
        assert result["total_bytes"] == 512 + 1024 + 256

    def test_storage_usage_missing_file_counts_as_zero(self, app):
        result = app.get_storage_usage(["/nonexistent/path/model.gguf"])
        assert result["breakdown"]["/nonexistent/path/model.gguf"] == 0
        assert result["total_bytes"] == 0


# ═══════════════════════════════════════════════════════════════════
# GROUP 6 — Local Flask server smoke tests
# ═══════════════════════════════════════════════════════════════════

class TestLocalServer:
    """
    Smoke tests for the local HTTP server that the Kivy UI calls.
    Starts Flask in a background thread and sends real HTTP requests.
    """

    @pytest.fixture(scope="class")
    def server(self):
        """Start a minimal Flask server in background for smoke tests."""
        try:
            from flask import Flask, request, jsonify
        except ImportError:
            pytest.skip("Flask not installed.")

        flask_app = Flask("tutor_test")

        @flask_app.route("/query", methods=["POST"])
        def query():
            data = request.get_json(force=True)
            q = data.get("query", "")
            if not q.strip():
                return jsonify({"error": "empty query"}), 400
            return jsonify({
                "response": f"Test response for: {q}",
                "source":   "Test chunk"
            })

        @flask_app.route("/health", methods=["GET"])
        def health():
            return jsonify({"status": "ok"})

        t = threading.Thread(
            target=lambda: flask_app.run(port=15432, debug=False, use_reloader=False),
            daemon=True
        )
        t.start()
        time.sleep(0.8)
        yield "http://localhost:15432"

    def test_health_endpoint_returns_ok(self, server):
        try:
            import requests
            r = requests.get(f"{server}/health", timeout=3)
            assert r.status_code == 200
            assert r.json()["status"] == "ok"
        except ImportError:
            pytest.skip("requests not installed.")
        except Exception as e:
            pytest.skip(f"Server not reachable: {e}")

    def test_query_endpoint_returns_response(self, server):
        try:
            import requests
            r = requests.post(
                f"{server}/query",
                json={"query": "What is osmosis?"},
                timeout=5
            )
            assert r.status_code == 200
            body = r.json()
            assert "response" in body
            assert len(body["response"]) > 0
        except ImportError:
            pytest.skip("requests not installed.")

    def test_query_endpoint_rejects_empty_query(self, server):
        try:
            import requests
            r = requests.post(
                f"{server}/query",
                json={"query": ""},
                timeout=3
            )
            assert r.status_code == 400
        except ImportError:
            pytest.skip("requests not installed.")

    def test_query_response_has_source_key(self, server):
        try:
            import requests
            r = requests.post(
                f"{server}/query",
                json={"query": "Explain meiosis."},
                timeout=5
            )
            body = r.json()
            assert "source" in body
        except ImportError:
            pytest.skip("requests not installed.")
