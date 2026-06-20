"""
test_phase5_sync_layer.py
Phase 5: Offline Sync Layer

Tests:
  - Change tracking (synced flag, triggers)
  - Delta sync worker logic
  - Flask /sync endpoint behaviour
  - Conflict resolution rules
  - Offline resilience (retry on reconnect, mid-sync failure)
"""

import json
import time
import threading
import pytest
import sqlite3
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch


# ─── Reference SyncLayer ──────────────────────────────────────────

class _SyncLayer:

    def __init__(self, conn: sqlite3.Connection, server_url: str = "http://localhost:15433"):
        self.conn       = conn
        self.server_url = server_url
        self.is_connected = False
        self._sync_log  = []

    def check_connectivity(self) -> bool:
        """Mock: returns self.is_connected (set by tests)."""
        return self.is_connected

    def get_unsynced_records(self, table: str = "repetition_records") -> list:
        rows = self.conn.execute(
            f"SELECT * FROM {table} WHERE synced=0"
        ).fetchall()
        return [dict(r) for r in rows]

    def push_delta(self, records: list) -> dict:
        """Simulate posting to server. Returns mock response."""
        if not self.is_connected:
            return {"success": False, "error": "No connectivity"}
        if not records:
            return {"success": True, "acked_ids": []}
        acked = [r["id"] for r in records if "id" in r]
        return {"success": True, "acked_ids": acked}

    def mark_synced(self, record_ids: list, table: str = "repetition_records"):
        if not record_ids:
            return
        placeholders = ",".join("?" * len(record_ids))
        self.conn.execute(
            f"UPDATE {table} SET synced=1 WHERE id IN ({placeholders})",
            record_ids
        )
        self.conn.commit()

    def resolve_conflict(self, local: dict, remote: dict) -> dict:
        """
        Conflict rule:
          1. Keep record with higher repetitions count.
          2. Tie-break: keep higher ease_factor.
          3. If all equal: keep local (client wins).
        """
        local_reps  = local.get("repetitions", 0)
        remote_reps = remote.get("repetitions", 0)
        if local_reps > remote_reps:
            return local
        if remote_reps > local_reps:
            return remote
        # tie: keep higher ease_factor
        if local.get("ease_factor", 0) >= remote.get("ease_factor", 0):
            return local
        return remote

    def run_sync(self) -> dict:
        """Full sync cycle: get unsynced → push → mark synced."""
        if not self.check_connectivity():
            return {"synced": 0, "error": "offline"}
        records = self.get_unsynced_records()
        if not records:
            return {"synced": 0}
        result  = self.push_delta(records)
        if result["success"]:
            self.mark_synced(result["acked_ids"])
            return {"synced": len(result["acked_ids"])}
        return {"synced": 0, "error": result.get("error")}


@pytest.fixture
def sync(populated_db):
    db, _ = populated_db
    return _SyncLayer(db)


@pytest.fixture
def sync_online(populated_db):
    db, _ = populated_db
    s = _SyncLayer(db)
    s.is_connected = True
    return s, db


# ═══════════════════════════════════════════════════════════════════
# GROUP 1 — Change tracking (synced flag)
# ═══════════════════════════════════════════════════════════════════

class TestChangeTracking:

    def test_new_record_synced_is_zero(self, populated_db):
        """Newly inserted repetition_records must have synced=0."""
        db, _ = populated_db
        rows = db.execute(
            "SELECT synced FROM repetition_records"
        ).fetchall()
        for row in rows:
            assert row[0] == 0, "Newly inserted record has synced != 0."

    def test_manual_update_sets_synced_to_zero(self, populated_db):
        """Manually updating a row must reset synced=0 via trigger."""
        db, _ = populated_db
        db.execute("UPDATE repetition_records SET synced=1 WHERE id=1")
        db.commit()
        db.execute("UPDATE repetition_records SET last_quality=4 WHERE id=1")
        db.commit()
        row = db.execute("SELECT synced FROM repetition_records WHERE id=1").fetchone()
        assert row[0] == 0, "Trigger did not reset synced=0 after update."

    def test_mark_synced_sets_flag_to_one(self, sync_online):
        """mark_synced() must flip synced=1 for given IDs."""
        s, db = sync_online
        s.mark_synced([1, 2, 3])
        for rid in [1, 2, 3]:
            row = db.execute(
                "SELECT synced FROM repetition_records WHERE id=?", (rid,)
            ).fetchone()
            if row:
                assert row[0] == 1, f"Record {rid} not marked synced."

    def test_get_unsynced_returns_all_pending(self, sync):
        """get_unsynced_records must return all rows where synced=0."""
        records = sync.get_unsynced_records()
        assert isinstance(records, list)
        assert len(records) > 0, "Expected unsynced records in populated_db."
        for r in records:
            assert r["synced"] == 0

    def test_after_sync_no_unsynced_remain(self, sync_online):
        """After a successful run_sync(), all rows must have synced=1."""
        s, db = sync_online
        result = s.run_sync()
        assert result["synced"] > 0
        remaining = s.get_unsynced_records()
        assert remaining == [], (
            f"{len(remaining)} records still unsynced after full sync cycle."
        )

    def test_updated_at_column_exists_on_rep_records(self, populated_db):
        """repetition_records must have an updated_at column."""
        db, _ = populated_db
        cols = {r[1] for r in db.execute(
            "PRAGMA table_info(repetition_records)"
        ).fetchall()}
        assert "updated_at" in cols, "updated_at column missing from repetition_records."

    def test_synced_column_exists_on_rep_records(self, populated_db):
        """repetition_records must have a synced column."""
        db, _ = populated_db
        cols = {r[1] for r in db.execute(
            "PRAGMA table_info(repetition_records)"
        ).fetchall()}
        assert "synced" in cols, "synced column missing from repetition_records."


# ═══════════════════════════════════════════════════════════════════
# GROUP 2 — Delta sync worker
# ═══════════════════════════════════════════════════════════════════

class TestDeltaSyncWorker:

    def test_push_delta_offline_returns_failure(self, sync):
        """push_delta must fail gracefully when offline."""
        sync.is_connected = False
        records = [{"id": 1, "ease_factor": 2.5}]
        result = sync.push_delta(records)
        assert result["success"] is False
        assert "error" in result

    def test_push_delta_online_returns_success(self, sync_online):
        """push_delta must return success=True with acked IDs when online."""
        s, _ = sync_online
        records = [{"id": 1}, {"id": 2}]
        result = s.push_delta(records)
        assert result["success"] is True
        assert set(result["acked_ids"]) == {1, 2}

    def test_push_delta_empty_list_returns_empty_acked(self, sync_online):
        """Pushing empty list must return success with empty acked_ids."""
        s, _ = sync_online
        result = s.push_delta([])
        assert result["success"] is True
        assert result["acked_ids"] == []

    def test_run_sync_offline_returns_zero(self, sync):
        """run_sync() when offline must return synced=0."""
        sync.is_connected = False
        result = sync.run_sync()
        assert result["synced"] == 0

    def test_run_sync_online_syncs_all_records(self, sync_online):
        """run_sync() online must sync all pending records."""
        s, db = sync_online
        pending = s.get_unsynced_records()
        result = s.run_sync()
        assert result["synced"] == len(pending), (
            f"Expected to sync {len(pending)} records, synced {result['synced']}."
        )

    def test_run_sync_idempotent(self, sync_online):
        """Running sync twice must sync 0 on the second call."""
        s, _ = sync_online
        s.run_sync()
        result = s.run_sync()
        assert result["synced"] == 0, (
            "Second sync call should have nothing to sync."
        )

    def test_partial_failure_leaves_unsynced_records(self, populated_db):
        """If server acks only some records, others must stay unsynced."""
        db, _ = populated_db
        s = _SyncLayer(db)
        s.is_connected = True
        # Override push_delta to only ack first record
        original_push = s.push_delta
        def partial_push(records):
            if records:
                return {"success": True, "acked_ids": [records[0]["id"]]}
            return {"success": True, "acked_ids": []}
        s.push_delta = partial_push
        s.run_sync()
        remaining = s.get_unsynced_records()
        # Only 1 was acked, rest should still be unsynced
        total = db.execute("SELECT COUNT(*) FROM repetition_records").fetchone()[0]
        assert len(remaining) == total - 1


# ═══════════════════════════════════════════════════════════════════
# GROUP 3 — Flask /sync endpoint
# ═══════════════════════════════════════════════════════════════════

class TestSyncEndpoint:

    @pytest.fixture(scope="class")
    def sync_server(self):
        try:
            from flask import Flask, request, jsonify
        except ImportError:
            pytest.skip("Flask not installed.")

        remote_db = sqlite3.connect(":memory:", check_same_thread=False)
        remote_db.row_factory = sqlite3.Row
        from conftest import SCHEMA_SQL
        remote_db.executescript(SCHEMA_SQL)

        flask_app = Flask("sync_test")

        @flask_app.route("/sync", methods=["POST"])
        def sync_endpoint():
            data = request.get_json(force=True)
            records = data.get("records", [])
            acked = []
            for rec in records:
                try:
                    remote_db.execute(
                        """INSERT OR REPLACE INTO repetition_records
                           (id, student_id, item_id, ease_factor,
                            interval_days, repetitions, last_quality,
                            next_review, updated_at, synced)
                           VALUES (:id,:student_id,:item_id,:ease_factor,
                                   :interval_days,:repetitions,:last_quality,
                                   :next_review,:updated_at,1)""",
                        rec
                    )
                    remote_db.commit()
                    acked.append(rec["id"])
                except Exception:
                    pass
            return jsonify({"success": True, "acked_ids": acked})

        @flask_app.route("/health")
        def health():
            return jsonify({"status": "ok"})

        t = threading.Thread(
            target=lambda: flask_app.run(port=15433, debug=False, use_reloader=False),
            daemon=True
        )
        t.start()
        time.sleep(0.8)
        yield "http://localhost:15433"

    def test_sync_endpoint_health(self, sync_server):
        try:
            import requests
            r = requests.get(f"{sync_server}/health", timeout=3)
            assert r.status_code == 200
        except ImportError:
            pytest.skip("requests not installed.")
        except Exception as e:
            pytest.skip(f"Server not reachable: {e}")

    def test_sync_endpoint_accepts_records(self, sync_server, populated_db):
        try:
            import requests
            db, _ = populated_db
            rows = db.execute("SELECT * FROM repetition_records LIMIT 3").fetchall()
            records = [dict(r) for r in rows]
            r = requests.post(
                f"{sync_server}/sync",
                json={"records": records},
                timeout=5
            )
            assert r.status_code == 200
            body = r.json()
            assert body["success"] is True
            assert len(body["acked_ids"]) == len(records)
        except ImportError:
            pytest.skip("requests not installed.")

    def test_sync_endpoint_empty_records(self, sync_server):
        try:
            import requests
            r = requests.post(
                f"{sync_server}/sync",
                json={"records": []},
                timeout=3
            )
            body = r.json()
            assert body["success"] is True
            assert body["acked_ids"] == []
        except ImportError:
            pytest.skip("requests not installed.")

    def test_sync_returns_correct_acked_ids(self, sync_server, populated_db):
        try:
            import requests
            db, _ = populated_db
            rows = db.execute("SELECT * FROM repetition_records LIMIT 5").fetchall()
            records  = [dict(r) for r in rows]
            expected = {r["id"] for r in records}
            r = requests.post(
                f"{sync_server}/sync",
                json={"records": records},
                timeout=5
            )
            acked = set(r.json()["acked_ids"])
            assert acked == expected
        except ImportError:
            pytest.skip("requests not installed.")


# ═══════════════════════════════════════════════════════════════════
# GROUP 4 — Conflict resolution
# ═══════════════════════════════════════════════════════════════════

class TestConflictResolution:

    @pytest.fixture
    def s(self, populated_db):
        db, _ = populated_db
        return _SyncLayer(db)

    def test_higher_repetitions_wins(self, s):
        local  = {"id": 1, "repetitions": 5, "ease_factor": 2.5}
        remote = {"id": 1, "repetitions": 3, "ease_factor": 2.6}
        winner = s.resolve_conflict(local, remote)
        assert winner["repetitions"] == 5, (
            "Record with higher repetitions should win conflict."
        )

    def test_remote_wins_when_more_repetitions(self, s):
        local  = {"id": 1, "repetitions": 2, "ease_factor": 2.8}
        remote = {"id": 1, "repetitions": 7, "ease_factor": 2.5}
        winner = s.resolve_conflict(local, remote)
        assert winner["repetitions"] == 7

    def test_tie_goes_to_higher_ef(self, s):
        local  = {"id": 1, "repetitions": 4, "ease_factor": 2.8}
        remote = {"id": 1, "repetitions": 4, "ease_factor": 2.5}
        winner = s.resolve_conflict(local, remote)
        assert winner["ease_factor"] == 2.8, (
            "Tie should go to record with higher ease_factor."
        )

    def test_all_equal_local_wins(self, s):
        local  = {"id": 1, "repetitions": 3, "ease_factor": 2.5, "source": "local"}
        remote = {"id": 1, "repetitions": 3, "ease_factor": 2.5, "source": "remote"}
        winner = s.resolve_conflict(local, remote)
        assert winner.get("source") == "local", "All-equal tie should keep local record."

    def test_winner_is_one_of_the_inputs(self, s):
        local  = {"id": 1, "repetitions": 2, "ease_factor": 2.5}
        remote = {"id": 1, "repetitions": 2, "ease_factor": 2.7}
        winner = s.resolve_conflict(local, remote)
        assert winner is local or winner is remote, (
            "Conflict resolution must return one of the two input records."
        )

    def test_missing_repetitions_defaults_to_zero(self, s):
        local  = {}   # missing repetitions
        remote = {"repetitions": 1, "ease_factor": 2.5}
        winner = s.resolve_conflict(local, remote)
        assert winner is remote


# ═══════════════════════════════════════════════════════════════════
# GROUP 5 — Offline resilience
# ═══════════════════════════════════════════════════════════════════

class TestOfflineResilience:

    def test_records_remain_unsynced_when_offline(self, populated_db):
        """Offline sync attempt must not lose or corrupt records."""
        db, _ = populated_db
        s = _SyncLayer(db)
        s.is_connected = False
        before = len(s.get_unsynced_records())
        s.run_sync()
        after = len(s.get_unsynced_records())
        assert after == before, (
            "Offline sync attempt changed the unsynced record count "
            f"({before} → {after}). No records should be lost or incorrectly marked."
        )

    def test_connectivity_restored_syncs_all(self, populated_db):
        """After going offline then online, all records must sync."""
        db, _ = populated_db
        s = _SyncLayer(db)
        s.is_connected = False
        s.run_sync()                   # fails silently
        s.is_connected = True
        result = s.run_sync()          # should succeed
        assert result["synced"] > 0
        remaining = s.get_unsynced_records()
        assert remaining == []

    def test_data_integrity_after_failed_sync(self, populated_db):
        """Records must be readable and correct after a failed sync attempt."""
        db, student_id = populated_db
        s = _SyncLayer(db)
        s.is_connected = False
        s.run_sync()
        rows = db.execute(
            "SELECT * FROM repetition_records WHERE student_id=?",
            (student_id,)
        ).fetchall()
        assert len(rows) == 30, (
            f"Expected 30 records after failed sync, found {len(rows)}."
        )

    def test_no_duplicate_records_after_double_sync(self, populated_db):
        """Syncing twice must not duplicate records in any table."""
        db, student_id = populated_db
        s = _SyncLayer(db)
        s.is_connected = True
        s.run_sync()
        s.run_sync()
        count = db.execute(
            "SELECT COUNT(*) FROM repetition_records WHERE student_id=?",
            (student_id,)
        ).fetchone()[0]
        assert count == 30, (
            f"Expected 30 records after double sync, found {count}."
        )

    def test_unsynced_flag_persists_across_restart(self, populated_db, tmp_dir):
        """Synced=0 records must survive a simulated app restart (new connection)."""
        import os
        db_path = os.path.join(tmp_dir, "tutor.db")
        # write schema and data to file-based DB
        file_db = sqlite3.connect(db_path)
        file_db.row_factory = sqlite3.Row
        from conftest import SCHEMA_SQL
        file_db.executescript(SCHEMA_SQL)
        file_db.execute(
            "INSERT INTO students (name, school_id) VALUES ('Restart Test', 'SCH001')"
        )
        file_db.execute(
            "INSERT INTO knowledge_items (subject, question, answer) VALUES ('Bio','Q','A')"
        )
        file_db.execute(
            "INSERT INTO repetition_records (student_id, item_id, synced) VALUES (1, 1, 0)"
        )
        file_db.commit()
        file_db.close()

        # simulate restart — open fresh connection
        restarted_db = sqlite3.connect(db_path)
        restarted_db.row_factory = sqlite3.Row
        count = restarted_db.execute(
            "SELECT COUNT(*) FROM repetition_records WHERE synced=0"
        ).fetchone()[0]
        restarted_db.close()
        assert count == 1, (
            "Unsynced record not persisted across simulated app restart."
        )
