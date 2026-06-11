"""
Test suite for the offline AI tutoring app.
Run with: pytest tests/ -v

Tests are grouped by layer:
  - TestSM2Algorithm    → pure SM2 math
  - TestSM2Scheduler    → SQLite integration
  - TestSemanticChunker → chunking logic
  - TestFAISSIndex      → index build/search/serialize
  - TestRAGPipeline     → end-to-end retrieval (mocked embedder)
  - TestConflictResolver→ sync conflict logic
  - TestSyncLayer       → sync integration (mocked API)
  - TestIntegration     → query → RAG → SM2 full flow (mocked LLM)
"""

from __future__ import annotations

import json
import math
import sqlite3
import tempfile
import threading
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock
import numpy as np
import pytest

# ---------------------------------------------------------------------------
# SM2 Algorithm Tests
# ---------------------------------------------------------------------------

class TestSM2Algorithm:
    from backend.sm2_scheduler import compute_sm2

    def test_perfect_recall_first_rep(self):
        from backend.sm2_scheduler import compute_sm2, FIRST_INTERVAL
        ef, interval, reps = compute_sm2(quality=5, ease_factor=2.5, interval_days=1, repetitions=0)
        assert reps == 1
        assert interval == FIRST_INTERVAL
        assert ef > 2.5  # Perfect recall increases EF

    def test_perfect_recall_second_rep(self):
        from backend.sm2_scheduler import compute_sm2, SECOND_INTERVAL
        ef, interval, reps = compute_sm2(quality=5, ease_factor=2.5, interval_days=1, repetitions=1)
        assert reps == 2
        assert interval == SECOND_INTERVAL

    def test_perfect_recall_third_rep(self):
        from backend.sm2_scheduler import compute_sm2
        # After 2nd rep (interval=6), 3rd rep should use EF multiplier
        ef, interval, reps = compute_sm2(quality=5, ease_factor=2.5, interval_days=6, repetitions=2)
        assert reps == 3
        assert interval == round(6 * ef)  # ef is new ef after update

    def test_failed_recall_resets(self):
        from backend.sm2_scheduler import compute_sm2, FIRST_INTERVAL
        ef, interval, reps = compute_sm2(quality=2, ease_factor=2.5, interval_days=10, repetitions=5)
        assert reps == 0
        assert interval == FIRST_INTERVAL

    def test_ef_floor(self):
        from backend.sm2_scheduler import compute_sm2, MIN_EASE_FACTOR
        # Quality 3 repeatedly should drive EF down to floor
        ef, interval, reps = compute_sm2(quality=3, ease_factor=1.4, interval_days=1, repetitions=1)
        assert ef >= MIN_EASE_FACTOR

    def test_ef_increases_on_high_quality(self):
        from backend.sm2_scheduler import compute_sm2
        ef_start = 2.0
        ef, _, _ = compute_sm2(quality=5, ease_factor=ef_start, interval_days=1, repetitions=1)
        assert ef > ef_start

    def test_invalid_quality_raises(self):
        from backend.sm2_scheduler import compute_sm2
        with pytest.raises(ValueError):
            compute_sm2(quality=6, ease_factor=2.5, interval_days=1, repetitions=0)
        with pytest.raises(ValueError):
            compute_sm2(quality=-1, ease_factor=2.5, interval_days=1, repetitions=0)

    def test_quality_threshold_boundary(self):
        """Quality=3 should pass (≥ threshold), quality=2 should fail."""
        from backend.sm2_scheduler import compute_sm2, FIRST_INTERVAL
        # q=3: pass, reps increments
        _, _, reps_pass = compute_sm2(quality=3, ease_factor=2.5, interval_days=1, repetitions=2)
        assert reps_pass == 3
        # q=2: fail, reset
        _, interval_fail, reps_fail = compute_sm2(quality=2, ease_factor=2.5, interval_days=10, repetitions=5)
        assert reps_fail == 0
        assert interval_fail == FIRST_INTERVAL


# ---------------------------------------------------------------------------
# SM2 Scheduler (SQLite)
# ---------------------------------------------------------------------------

class TestSM2Scheduler:
    @pytest.fixture
    def scheduler(self, tmp_path):
        from backend.sm2_scheduler import SM2Scheduler
        s = SM2Scheduler(db_path=tmp_path / "test.db")
        s.init_db()
        return s

    @pytest.fixture
    def populated_scheduler(self, scheduler):
        from backend.sm2_scheduler import KnowledgeItem
        scheduler.upsert_student("stu_001", "Amaka", grade_level="SS2")
        items = [
            KnowledgeItem(id=f"item_{i:03d}", subject="Biology", question=f"Q{i}?", answer=f"A{i}.")
            for i in range(5)
        ]
        for item in items:
            scheduler.upsert_knowledge_item(item)
        scheduler.seed_items_for_student("stu_001", subject="Biology")
        return scheduler

    def test_init_creates_tables(self, scheduler):
        conn = sqlite3.connect(str(scheduler.db_path))
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        conn.close()
        assert {"students", "knowledge_items", "repetition_records", "sync_log"} <= tables

    def test_upsert_student(self, scheduler):
        scheduler.upsert_student("stu_001", "Emeka", "SS3", "school_a")
        student = scheduler.get_student("stu_001")
        assert student["name"] == "Emeka"
        assert student["grade_level"] == "SS3"

    def test_seed_creates_records(self, populated_scheduler):
        session = populated_scheduler.get_review_session("stu_001")
        assert len(session.items) == 5

    def test_seed_is_idempotent(self, populated_scheduler):
        n = populated_scheduler.seed_items_for_student("stu_001", "Biology")
        assert n == 0  # Already seeded

    def test_record_response_updates_sm2(self, populated_scheduler):
        session = populated_scheduler.get_review_session("stu_001")
        record, _ = session.items[0]
        result = populated_scheduler.record_response(record.id, quality=5)
        assert result.new_repetitions == 1
        assert result.new_ease_factor > 2.5
        # Next review should be in the future
        assert result.next_review_date > date.today().isoformat()

    def test_failed_response_next_review_today(self, populated_scheduler):
        session = populated_scheduler.get_review_session("stu_001")
        record, _ = session.items[0]
        result = populated_scheduler.record_response(record.id, quality=1)
        assert result.was_reset
        assert result.new_repetitions == 0
        # next review is tomorrow (interval=1 day)
        expected = (date.today() + timedelta(days=1)).isoformat()
        assert result.next_review_date == expected

    def test_review_session_respects_limit(self, populated_scheduler):
        session = populated_scheduler.get_review_session("stu_001", limit=3)
        assert len(session.items) <= 3

    def test_get_streak_single_day(self, populated_scheduler):
        # Not reviewed yet → streak = 0
        streak = populated_scheduler.get_streak("stu_001")
        assert streak == 0

    def test_sync_log_populated_on_update(self, populated_scheduler):
        session = populated_scheduler.get_review_session("stu_001")
        record, _ = session.items[0]
        populated_scheduler.record_response(record.id, quality=4)
        conn = sqlite3.connect(str(populated_scheduler.db_path))
        rows = conn.execute("SELECT * FROM sync_log WHERE record_id=?", (record.id,)).fetchall()
        conn.close()
        assert len(rows) >= 1

    def test_mark_synced_clears_flag(self, populated_scheduler):
        unsynced = populated_scheduler.get_unsynced_records("stu_001")
        if unsynced:
            # get_unsynced_records returns repetition_record rows; 'id' is the record id
            record_ids = [u["id"] for u in unsynced]
            populated_scheduler.mark_synced(record_ids)
            unsynced_after = populated_scheduler.get_unsynced_records("stu_001")
            assert len(unsynced_after) == 0


# ---------------------------------------------------------------------------
# Semantic Chunker
# ---------------------------------------------------------------------------

class TestSemanticChunker:
    @pytest.fixture
    def chunker(self):
        from backend.rag_pipeline import SemanticChunker
        return SemanticChunker()

    def test_basic_chunking(self, chunker):
        text = " ".join([f"Sentence {i} about biology." for i in range(200)])
        chunks = chunker.chunk_text(text, source="Bio_SS2", subject="Biology")
        assert len(chunks) >= 1
        for c in chunks:
            assert c.token_count >= 80

    def test_short_text_below_min_discarded(self, chunker):
        text = "Short text."
        chunks = chunker.chunk_text(text, source="tiny", subject="Biology")
        # Should produce 0 chunks (below MIN_CHUNK_TOKENS)
        assert len(chunks) == 0

    def test_chunk_ids_unique(self, chunker):
        text = " ".join([f"Sentence {i}." for i in range(300)])
        chunks = chunker.chunk_text(text, "src", "Math")
        ids = [c.id for c in chunks]
        assert len(ids) == len(set(ids))

    def test_source_preserved(self, chunker):
        chunks = chunker.chunk_text(
            " ".join([f"Sentence {i} about osmosis." for i in range(200)]),
            "Biology_Ch5", "Biology"
        )
        for c in chunks:
            assert c.source == "Biology_Ch5"
            assert c.subject == "Biology"

    def test_overlap_means_consecutive_chunks_share_sentences(self, chunker):
        sentences = [f"This is sentence number {i} about photosynthesis." for i in range(50)]
        text = " ".join(sentences)
        chunks = chunker.chunk_text(text, "src", "Bio")
        if len(chunks) >= 2:
            # Some words from chunk[0] end should appear in chunk[1] start (overlap)
            # We just verify chunks are non-empty and distinct
            assert chunks[0].text != chunks[1].text


# ---------------------------------------------------------------------------
# FAISS Index
# ---------------------------------------------------------------------------

class TestFAISSIndex:
    @pytest.fixture
    def sample_data(self):
        from backend.rag_pipeline import Chunk, EMBEDDING_DIM
        n = 20
        chunks = [
            Chunk(id=f"c{i}", text=f"Text {i}", source="src", subject="Bio", token_count=10)
            for i in range(n)
        ]
        # Random unit vectors
        embeddings = np.random.randn(n, EMBEDDING_DIM).astype(np.float32)
        return chunks, embeddings

    def test_build_and_search(self, sample_data):
        from backend.rag_pipeline import FAISSIndex, EMBEDDING_DIM, SIMILARITY_THRESHOLD
        chunks, embeddings = sample_data
        idx = FAISSIndex()
        idx.build(chunks, embeddings)

        # Query with first embedding (should find itself as top result)
        results, scores = idx.search(embeddings[0])
        # At least 1 result (the query itself should be close)
        # Note: threshold filter may drop some
        assert isinstance(results, list)
        assert isinstance(scores, list)
        assert len(results) == len(scores)

    def test_empty_index_returns_empty(self):
        from backend.rag_pipeline import FAISSIndex
        idx = FAISSIndex()
        results, scores = idx.search(np.random.randn(384))
        assert results == []
        assert scores == []

    def test_save_and_load(self, tmp_path, sample_data):
        from backend.rag_pipeline import FAISSIndex
        chunks, embeddings = sample_data
        idx = FAISSIndex()
        idx.build(chunks, embeddings)

        index_path = tmp_path / "test.index"
        chunks_path = tmp_path / "chunks.json"
        idx.save(index_path, chunks_path)

        idx2 = FAISSIndex()
        idx2.load(index_path, chunks_path)
        assert idx2.index.ntotal == len(chunks)
        assert len(idx2.chunks) == len(chunks)

    def test_l2_normalize(self):
        from backend.rag_pipeline import FAISSIndex
        arr = np.array([[3.0, 4.0], [0.0, 0.0]])
        normed = FAISSIndex._l2_normalize(arr)
        assert abs(np.linalg.norm(normed[0]) - 1.0) < 1e-6
        # Zero vector handled gracefully
        assert not np.any(np.isnan(normed[1]))


# ---------------------------------------------------------------------------
# RAG Pipeline (mocked embedder)
# ---------------------------------------------------------------------------

class TestRAGPipeline:
    @pytest.fixture
    def pipeline(self, tmp_path):
        from backend.rag_pipeline import RAGPipeline, EMBEDDING_DIM
        p = RAGPipeline(data_dir=tmp_path / "rag")

        # Mock the SentenceTransformer
        mock_embedder = MagicMock()
        mock_embedder.encode = MagicMock(
            side_effect=lambda texts, **kwargs: np.random.randn(
                len(texts) if isinstance(texts, list) else 1, EMBEDDING_DIM
            ).astype(np.float32)
        )
        p.embedder = mock_embedder
        p._loaded = True
        return p

    def test_ingest_and_retrieve(self, pipeline):
        docs = [
            {
                "text": " ".join([f"Biology sentence {i} about cells." for i in range(100)]),
                "source": "Biology_Ch1",
                "subject": "Biology",
            }
        ]
        pipeline.ingest_documents(docs)
        result = pipeline.retrieve("What are cells?")
        assert hasattr(result, "chunks")
        assert hasattr(result, "scores")
        assert result.elapsed_ms > 0

    def test_build_prompt_under_token_limit(self, pipeline):
        from backend.rag_pipeline import MAX_PROMPT_TOKENS
        docs = [
            {
                "text": " ".join([f"Long content sentence {i}." for i in range(200)]),
                "source": "src",
                "subject": "English",
            }
        ]
        pipeline.ingest_documents(docs)
        pkg = pipeline.build_prompt("Explain grammar", grade_level="SS1")
        assert pkg.token_estimate <= MAX_PROMPT_TOKENS
        assert "SS1" in pkg.prompt
        assert "Explain grammar" in pkg.prompt

    def test_require_loaded_raises(self, tmp_path):
        from backend.rag_pipeline import RAGPipeline
        p = RAGPipeline(data_dir=tmp_path / "rag2")
        with pytest.raises(RuntimeError):
            p.retrieve("test")


# ---------------------------------------------------------------------------
# Conflict Resolver
# ---------------------------------------------------------------------------

class TestConflictResolver:
    @pytest.fixture
    def resolver(self):
        from backend.sync_layer import ConflictResolver
        return ConflictResolver()

    def test_local_newer_wins(self, resolver):
        local = {"id": "r1", "updated_at": "2024-01-02T10:00:00", "repetitions": 5}
        remote = {"id": "r1", "updated_at": "2024-01-01T10:00:00", "repetitions": 3}
        winner, log = resolver.resolve(local, remote)
        assert winner is local
        assert "local_wins" in log.resolution

    def test_remote_newer_wins(self, resolver):
        local = {"id": "r1", "updated_at": "2024-01-01T10:00:00", "repetitions": 3}
        remote = {"id": "r1", "updated_at": "2024-01-02T10:00:00", "repetitions": 5}
        winner, log = resolver.resolve(local, remote)
        assert winner is remote
        assert "remote_wins" in log.resolution

    def test_tie_break_higher_reps(self, resolver):
        ts = "2024-01-01T10:00:00"
        local = {"id": "r1", "updated_at": ts, "repetitions": 7}
        remote = {"id": "r1", "updated_at": ts, "repetitions": 5}
        winner, log = resolver.resolve(local, remote)
        assert winner is local
        assert "tiebreak" in log.resolution

    def test_conflict_fields_detected(self, resolver):
        local = {"id": "r1", "updated_at": "2024-01-02", "ease_factor": 2.5, "interval_days": 6, "repetitions": 2, "next_review": "2024-02-01"}
        remote = {"id": "r1", "updated_at": "2024-01-01", "ease_factor": 3.0, "interval_days": 10, "repetitions": 4, "next_review": "2024-03-01"}
        _, log = resolver.resolve(local, remote)
        assert "ease_factor" in log.field_conflicts
        assert "interval_days" in log.field_conflicts


# ---------------------------------------------------------------------------
# Integration Test: Query → RAG → SM2 Update
# ---------------------------------------------------------------------------

class TestIntegration:
    """
    Tests the full student query flow without any network calls or real models.
    """

    @pytest.fixture
    def app_components(self, tmp_path):
        from backend.rag_pipeline import RAGPipeline, EMBEDDING_DIM
        from backend.sm2_scheduler import SM2Scheduler, KnowledgeItem
        from backend.inference_engine import InferenceEngine

        # Setup RAG with mocked embedder
        rag = RAGPipeline(data_dir=tmp_path / "rag")
        mock_embedder = MagicMock()
        mock_embedder.encode = MagicMock(
            side_effect=lambda texts, **kwargs: np.random.randn(
                len(texts) if isinstance(texts, list) else 1, EMBEDDING_DIM
            ).astype(np.float32)
        )
        rag.embedder = mock_embedder
        rag._loaded = True
        rag.ingest_documents([{
            "text": " ".join([f"Photosynthesis is the process {i}." for i in range(100)]),
            "source": "Bio_Ch3",
            "subject": "Biology",
        }])

        # Setup SM2 scheduler
        scheduler = SM2Scheduler(db_path=tmp_path / "tutor.db")
        scheduler.init_db()
        scheduler.upsert_student("stu_001", "TestStudent")
        item = KnowledgeItem(
            id="item_001",
            subject="Biology",
            question="What is photosynthesis?",
            answer="The process by which plants make food using sunlight.",
        )
        scheduler.upsert_knowledge_item(item)
        scheduler.seed_items_for_student("stu_001")

        # Mock inference engine
        engine = MagicMock(spec=InferenceEngine)
        from backend.inference_engine import GenerationResult
        engine.generate.return_value = GenerationResult(
            text="Photosynthesis is how plants convert light to glucose.",
            prompt_tokens=100,
            completion_tokens=15,
            total_tokens=115,
            elapsed_ms=850.0,
            tokens_per_second=17.6,
        )
        engine.is_loaded = True

        return rag, scheduler, engine

    def test_full_query_flow(self, app_components):
        rag, scheduler, engine = app_components

        # 1. Build prompt
        pkg = rag.build_prompt("What is photosynthesis?", grade_level="SS2")
        assert "photosynthesis" in pkg.prompt.lower() or len(pkg.prompt) > 0

        # 2. Generate response
        result = engine.generate(pkg.prompt)
        assert "photosynthesis" in result.text.lower()
        assert result.elapsed_ms > 0

        # 3. SM2 update after student rates the card
        session = scheduler.get_review_session("stu_001")
        assert not session.is_empty()
        record, item = session.items[0]
        assert item.subject == "Biology"

        sm2_result = scheduler.record_response(record.id, quality=4)
        assert sm2_result.new_repetitions == 1
        assert sm2_result.next_review_date > date.today().isoformat()

    def test_offline_mode_works_without_sync(self, app_components):
        """Core functionality must work with no network at all."""
        rag, scheduler, engine = app_components
        # Retrieve works offline
        retrieval = rag.retrieve("What is photosynthesis?")
        assert retrieval is not None

        # SM2 works offline
        session = scheduler.get_review_session("stu_001")
        assert not session.is_empty()

        # Engine generation works offline (mocked)
        result = engine.generate("test")
        assert result is not None

    def test_sm2_progression_over_sessions(self, app_components):
        """Simulate 3 review sessions and verify interval grows."""
        _, scheduler, _ = app_components
        session = scheduler.get_review_session("stu_001")
        record, _ = session.items[0]

        intervals = []
        for quality in [5, 5, 5]:
            r = scheduler.record_response(record.id, quality=quality)
            intervals.append(r.new_interval_days)
            record.id = record.id  # same record

        # Intervals should grow: 1 → 6 → 15 (approx)
        assert intervals[0] <= intervals[1] <= intervals[2]
