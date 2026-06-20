"""
Flask REST API: Sync server for receiving delta pushes from Android clients.
Deploy on any low-cost VPS. SQLite works fine for <500 students;
swap for PostgreSQL at scale.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, request, Response

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = Flask(__name__)
DB_PATH = Path("data/server.db")

# ---------------------------------------------------------------------------
# AI Engines (Loaded Lazily for Local Server Mode)
# ---------------------------------------------------------------------------
rag_engine = None
inference_engine = None
engine_lock = threading.Lock()
_engine_errors: dict[str, str] = {}  # tracks init failures for /query diagnostics

def init_engines():
    global rag_engine, inference_engine
    with engine_lock:
        if rag_engine is None:
            from backend.rag_pipeline import RAGPipeline
            try:
                rag_engine = RAGPipeline(Path("data"))
                rag_engine.load()
                logger.info("RAG Pipeline loaded via Server")
            except ImportError as e:
                logger.warning("RAG dependencies not installed: %s", e)
                _engine_errors["rag"] = str(e)
                rag_engine = None
            except Exception as e:
                logger.error("Failed to load RAG in server: %s", e)
                _engine_errors["rag"] = str(e)
                rag_engine = None
                
        if inference_engine is None:
            from backend.inference_engine import InferenceEngine
            try:
                inference_engine = InferenceEngine(models_dir=Path("models"))
                inference_engine.load(ram_gb=4.0)
                logger.info("Inference Engine loaded via Server")
            except Exception as e:
                logger.error("Failed to load Inference Engine in server: %s", e)
                _engine_errors["inference"] = str(e)
                inference_engine = None

# ---------------------------------------------------------------------------
# Server DB Schema
# ---------------------------------------------------------------------------

SERVER_SCHEMA = """
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS repetition_records (
    id              TEXT PRIMARY KEY,
    student_id      TEXT NOT NULL,
    item_id         TEXT NOT NULL,
    ease_factor     REAL NOT NULL,
    interval_days   INTEGER NOT NULL,
    repetitions     INTEGER NOT NULL,
    last_quality    INTEGER,
    next_review     TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    received_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now')),
    UNIQUE(student_id, item_id)
);

CREATE INDEX IF NOT EXISTS idx_rr_student ON repetition_records(student_id, updated_at);
"""


@contextmanager
def get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.executescript(SERVER_SCHEMA)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "timestamp": datetime.utcnow().isoformat()})


# ---------------------------------------------------------------------------
# AI Inference: Local -> Server
# ---------------------------------------------------------------------------

@app.route("/query", methods=["POST"])
def query():
    """
    Handle inference query.
    Body: { "query": str, "grade_level": str }
    Streams JSON lines: {"token": str}
    """
    init_engines()
    data = request.get_json(silent=True)
    if not data or "query" not in data:
        return jsonify({"error": "Missing query"}), 400
        
    q = data["query"]
    grade_level = data.get("grade_level", "SS2")
    
    if rag_engine and rag_engine.is_loaded:
        pkg = rag_engine.build_prompt(q, grade_level=grade_level)
        prompt = pkg.prompt
    else:
        # Fallback if RAG is not loaded
        prompt = f"### Student\n{q}\n\n### Assistant\n"
        
    if not inference_engine or not inference_engine.is_loaded:
        reason = _engine_errors.get("inference", "Model not loaded")
        return jsonify({"error": reason}), 503
        
    def generate():
        for token in inference_engine.generate_stream(prompt):
            yield json.dumps({"token": token}) + "\n"
            
    return Response(generate(), mimetype='application/x-ndjson')


# ---------------------------------------------------------------------------
# Push: Client → Server
# ---------------------------------------------------------------------------

@app.route("/api/v1/sync/push", methods=["POST"])
def sync_push():
    """
    Accept delta records from a client.
    Body: { "student_id": str, "records": [...], "client_timestamp": str }
    Response: { "accepted_ids": [...], "rejected_ids": [...] }
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    student_id = data.get("student_id")
    records: list[dict] = data.get("records", [])

    if not student_id or not records:
        return jsonify({"error": "Missing student_id or records"}), 400

    accepted_ids: list[str] = []
    rejected_ids: list[str] = []

    with get_db() as conn:
        for rec in records:
            try:
                rec_id = rec.get("id")
                if not rec_id:
                    rejected_ids.append("missing_id")
                    continue

                # Last-write-wins: check existing server record
                existing = conn.execute(
                    "SELECT updated_at FROM repetition_records WHERE id=?", (rec_id,)
                ).fetchone()

                if existing:
                    server_ts = existing["updated_at"]
                    client_ts = rec.get("updated_at", "")
                    if client_ts <= server_ts:
                        # Server is newer — skip (client will get this on pull)
                        rejected_ids.append(rec_id)
                        continue

                conn.execute("""
                    INSERT INTO repetition_records
                        (id, student_id, item_id, ease_factor, interval_days,
                         repetitions, last_quality, next_review, updated_at)
                    VALUES (:id, :student_id, :item_id, :ease_factor, :interval_days,
                            :repetitions, :last_quality, :next_review, :updated_at)
                    ON CONFLICT(student_id, item_id) DO UPDATE SET
                        ease_factor   = CASE WHEN excluded.updated_at > updated_at THEN excluded.ease_factor   ELSE ease_factor   END,
                        interval_days = CASE WHEN excluded.updated_at > updated_at THEN excluded.interval_days ELSE interval_days END,
                        repetitions   = CASE WHEN excluded.updated_at > updated_at THEN excluded.repetitions   ELSE repetitions   END,
                        last_quality  = CASE WHEN excluded.updated_at > updated_at THEN excluded.last_quality  ELSE last_quality  END,
                        next_review   = CASE WHEN excluded.updated_at > updated_at THEN excluded.next_review   ELSE next_review   END,
                        updated_at    = CASE WHEN excluded.updated_at > updated_at THEN excluded.updated_at    ELSE updated_at    END
                """, {**rec, "student_id": student_id})
                accepted_ids.append(rec_id)

            except Exception as e:
                logger.exception(f"Error processing record {rec.get('id')}: {e}")
                rejected_ids.append(rec.get("id", "unknown"))

    logger.info(f"Push from {student_id}: accepted={len(accepted_ids)} rejected={len(rejected_ids)}")
    return jsonify({
        "accepted_ids": accepted_ids,
        "rejected_ids": rejected_ids,
        "server_timestamp": datetime.utcnow().isoformat(),
    })


# ---------------------------------------------------------------------------
# Pull: Server → Client
# ---------------------------------------------------------------------------

@app.route("/api/v1/sync/pull", methods=["GET"])
def sync_pull():
    """
    Return records updated since `since` for a given student.
    Query params: student_id, since (optional ISO timestamp)
    Response: { "records": [...], "server_timestamp": str }
    """
    student_id = request.args.get("student_id")
    since = request.args.get("since")

    if not student_id:
        return jsonify({"error": "Missing student_id"}), 400

    with get_db() as conn:
        if since:
            rows = conn.execute(
                "SELECT * FROM repetition_records WHERE student_id=? AND updated_at > ? ORDER BY updated_at ASC",
                (student_id, since)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM repetition_records WHERE student_id=? ORDER BY updated_at ASC",
                (student_id,)
            ).fetchall()

    records = [dict(r) for r in rows]
    logger.info(f"Pull for {student_id} since={since}: {len(records)} records")
    return jsonify({
        "records": records,
        "server_timestamp": datetime.utcnow().isoformat(),
        "count": len(records),
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
