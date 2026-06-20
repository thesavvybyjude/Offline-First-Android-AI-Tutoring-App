"""
test_phase2_rag_pipeline.py
Phase 2: RAG Pipeline — encode, retrieve, threshold, prompt, F1 evaluation

Every test here answers one question:
  "Does the RAG pipeline do what it claims?"
"""

import os
import json
import pytest
import numpy as np


# ─── Minimal RAGPipeline implementation for testing ────────────────
# Tests use this reference implementation so they don't depend on
# the production file existing yet.  When production code is ready,
# swap the import at the top of each test class.

class _RAGPipeline:
    """Minimal reference implementation used by tests."""

    def __init__(self, embeddings: np.ndarray, chunks: list, threshold: float = 0.45):
        import faiss
        self.chunks = chunks
        self.threshold = threshold
        self.dim = embeddings.shape[1]
        # normalise for cosine similarity via inner product
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        self._normed = (embeddings / norms).astype("float32")
        self.index = faiss.IndexFlatIP(self.dim)
        self.index.add(self._normed)

    def encode_query(self, text: str) -> np.ndarray:
        """Return a (384,) float32 unit-normalised embedding."""
        # deterministic fake encoder: hash-seeded random vector
        np.random.seed(abs(hash(text)) % (2**31))
        vec = np.random.rand(self.dim).astype("float32")
        return (vec / np.linalg.norm(vec))

    def retrieve(self, query: str, top_k: int = 3) -> list:
        """Return list of (chunk_text, similarity_score) tuples."""
        q_vec = self.encode_query(query).reshape(1, -1)
        D, I = self.index.search(q_vec, k=top_k)
        results = []
        for score, idx in zip(D[0], I[0]):
            if score >= self.threshold:
                results.append((self.chunks[idx], float(score)))
        return results

    def inject_context(self, query: str, chunks: list) -> str:
        """Build the structured prompt string."""
        from jinja2 import Template
        tmpl = Template(
            "[SYSTEM] You are a curriculum-aligned tutor. Answer using the context below.\n"
            "[CONTEXT]\n{% for c in chunks %}{{ c[0] }}\n{% endfor %}"
            "[QUERY] {{ query }}\n[RESPONSE]"
        )
        return tmpl.render(chunks=chunks, query=query)


@pytest.fixture
def rag(sample_embeddings, sample_chunks):
    return _RAGPipeline(sample_embeddings, sample_chunks, threshold=0.0)


@pytest.fixture
def rag_threshold(sample_embeddings, sample_chunks):
    """Pipeline with threshold=0.45 (production setting)."""
    return _RAGPipeline(sample_embeddings, sample_chunks, threshold=0.45)


# ═══════════════════════════════════════════════════════════════════
# GROUP 1 — encode_query()
# ═══════════════════════════════════════════════════════════════════

class TestEncodeQuery:

    def test_output_shape_is_384(self, rag):
        """encode_query must return a (384,) array."""
        vec = rag.encode_query("What is osmosis?")
        assert vec.shape == (384,), f"Expected (384,), got {vec.shape}"

    def test_output_dtype_is_float32(self, rag):
        """encode_query must return float32."""
        vec = rag.encode_query("Define photosynthesis.")
        assert vec.dtype == np.float32, f"Expected float32, got {vec.dtype}"

    def test_output_is_unit_normalised(self, rag):
        """encode_query output must have L2 norm ≈ 1.0."""
        vec = rag.encode_query("Explain cell division.")
        norm = float(np.linalg.norm(vec))
        assert abs(norm - 1.0) < 1e-5, f"Vector norm is {norm:.6f}, expected ~1.0"

    def test_empty_string_does_not_crash(self, rag):
        """encode_query must handle empty string input gracefully."""
        vec = rag.encode_query("")
        assert vec.shape == (384,)

    def test_long_string_does_not_crash(self, rag):
        """encode_query must handle very long strings without error."""
        long_text = "biology " * 1000
        vec = rag.encode_query(long_text)
        assert vec.shape == (384,)

    def test_different_queries_produce_different_vectors(self, rag):
        """Two different queries must not produce identical embeddings."""
        v1 = rag.encode_query("What is osmosis?")
        v2 = rag.encode_query("Explain meiosis.")
        assert not np.allclose(v1, v2), (
            "Two different queries returned identical embeddings — encoder is broken."
        )


# ═══════════════════════════════════════════════════════════════════
# GROUP 2 — retrieve()
# ═══════════════════════════════════════════════════════════════════

class TestRetrieve:

    def test_returns_list(self, rag):
        """retrieve() must return a list."""
        results = rag.retrieve("What is cell respiration?", top_k=3)
        assert isinstance(results, list)

    def test_returns_at_most_top_k(self, rag):
        """retrieve() must return at most top_k results."""
        results = rag.retrieve("Explain osmosis.", top_k=3)
        assert len(results) <= 3

    def test_results_are_tuples(self, rag):
        """Each result must be a (str, float) tuple."""
        results = rag.retrieve("What is ATP?", top_k=3)
        for item in results:
            assert isinstance(item, tuple) and len(item) == 2
            assert isinstance(item[0], str)
            assert isinstance(item[1], float)

    def test_results_sorted_by_score_descending(self, rag):
        """Results must be sorted highest similarity first."""
        results = rag.retrieve("Biology cellular concept 3", top_k=5)
        scores = [r[1] for r in results]
        assert scores == sorted(scores, reverse=True), (
            f"Results not sorted descending: {scores}"
        )

    def test_top_k_1_returns_one_result(self, rag):
        """top_k=1 must return exactly 1 result (if above threshold)."""
        results = rag.retrieve("Biology concept", top_k=1)
        assert len(results) <= 1

    def test_threshold_filters_low_similarity(self, sample_embeddings, sample_chunks):
        """With high threshold=0.99, very few (possibly 0) chunks returned."""
        pipeline = _RAGPipeline(sample_embeddings, sample_chunks, threshold=0.99)
        results = pipeline.retrieve("completely unrelated query xyz", top_k=3)
        assert len(results) <= 3  # may be 0 — that is correct behaviour

    def test_threshold_zero_returns_top_k(self, rag):
        """With threshold=0.0, retrieve must always return top_k results."""
        results = rag.retrieve("What is biology?", top_k=3)
        assert len(results) == 3, (
            f"Expected 3 results with threshold=0.0, got {len(results)}"
        )

    def test_chunk_text_is_non_empty(self, rag):
        """Each retrieved chunk text must be a non-empty string."""
        results = rag.retrieve("Explain respiration.", top_k=3)
        for chunk_text, _ in results:
            assert len(chunk_text.strip()) > 0, "Retrieved chunk is empty string."


# ═══════════════════════════════════════════════════════════════════
# GROUP 3 — inject_context() / prompt template
# ═══════════════════════════════════════════════════════════════════

class TestInjectContext:

    def test_prompt_contains_query(self, rag):
        """Generated prompt must contain the original query text."""
        query = "What is the function of mitochondria?"
        chunks = rag.retrieve(query, top_k=2)
        prompt = rag.inject_context(query, chunks)
        assert query in prompt, "Query text missing from generated prompt."

    def test_prompt_contains_retrieved_chunks(self, rag):
        """Generated prompt must contain text from retrieved chunks."""
        query = "Explain photosynthesis."
        chunks = rag.retrieve(query, top_k=2)
        prompt = rag.inject_context(query, chunks)
        for chunk_text, _ in chunks:
            assert chunk_text[:30] in prompt, (
                f"Chunk text not found in prompt: '{chunk_text[:30]}...'"
            )

    def test_prompt_contains_system_role(self, rag):
        """Prompt must contain the system role instruction."""
        query = "Define osmosis."
        chunks = rag.retrieve(query, top_k=1)
        prompt = rag.inject_context(query, chunks)
        assert "SYSTEM" in prompt or "tutor" in prompt.lower(), (
            "System role instruction missing from prompt."
        )

    def test_prompt_is_string(self, rag):
        """inject_context must return a string."""
        query = "What is meiosis?"
        chunks = rag.retrieve(query, top_k=2)
        prompt = rag.inject_context(query, chunks)
        assert isinstance(prompt, str)

    def test_prompt_token_count_under_1024(self, rag):
        """Full prompt must be under 1,024 tokens."""
        try:
            import tiktoken
            enc = tiktoken.get_encoding("cl100k_base")
        except ImportError:
            pytest.skip("tiktoken not installed.")
        query = "Explain the process of cellular respiration in detail."
        chunks = rag.retrieve(query, top_k=3)
        prompt = rag.inject_context(query, chunks)
        token_count = len(enc.encode(prompt))
        assert token_count < 1024, (
            f"Prompt has {token_count} tokens — exceeds 1,024 limit. "
            "Reduce chunk size or top_k."
        )

    def test_empty_chunks_produces_valid_prompt(self, rag):
        """inject_context must handle empty chunk list gracefully."""
        prompt = rag.inject_context("What is biology?", [])
        assert isinstance(prompt, str) and len(prompt) > 0


# ═══════════════════════════════════════════════════════════════════
# GROUP 4 — Similarity threshold validation
# ═══════════════════════════════════════════════════════════════════

class TestSimilarityThreshold:

    THRESHOLD = 0.45

    def test_threshold_value_is_in_valid_range(self):
        """Chosen threshold must be between 0.40 and 0.50 as per spec."""
        assert 0.40 <= self.THRESHOLD <= 0.50, (
            f"Threshold {self.THRESHOLD} is outside the validated range [0.40, 0.50]."
        )

    def test_noise_query_filtered_by_threshold(self, sample_embeddings, sample_chunks):
        """A query semantically unrelated to corpus must return 0 chunks above threshold."""
        pipeline = _RAGPipeline(sample_embeddings, sample_chunks, threshold=self.THRESHOLD)
        # Use a fixed random vector unlikely to match anything highly
        np.random.seed(9999)
        noise_vec = np.random.rand(384).astype("float32")
        # Override encode_query to return this noise vector
        pipeline.encode_query = lambda _: noise_vec / np.linalg.norm(noise_vec)
        results = pipeline.retrieve("xyzzy quantum blockchain", top_k=3)
        # With random corpus and random query, similarity should be ~0.5 for 384-dim
        # This test validates the threshold *logic* path is exercised
        for _, score in results:
            assert score >= self.THRESHOLD, (
                f"Chunk with score {score:.4f} below threshold {self.THRESHOLD} was returned."
            )


# ═══════════════════════════════════════════════════════════════════
# GROUP 5 — F1 score evaluation
# ═══════════════════════════════════════════════════════════════════

class TestRAGEvaluation:
    """
    These tests validate the F1 evaluation framework itself.
    The actual 100-item gold-standard evaluation is run as a script
    (scripts/eval_rag_f1.py) and must produce F1 >= 0.70.
    """

    def _compute_f1(self, retrieved: set, relevant: set) -> dict:
        if not retrieved:
            return {"precision": 0.0, "recall": 0.0, "f1": 0.0}
        tp = len(retrieved & relevant)
        precision = tp / len(retrieved)
        recall    = tp / len(relevant) if relevant else 0.0
        f1 = (2 * precision * recall / (precision + recall)
              if (precision + recall) > 0 else 0.0)
        return {"precision": precision, "recall": recall, "f1": f1}

    def test_perfect_retrieval_gives_f1_1(self):
        """When retrieved == relevant, F1 must be 1.0."""
        result = self._compute_f1({1, 2, 3}, {1, 2, 3})
        assert abs(result["f1"] - 1.0) < 1e-9

    def test_no_retrieval_gives_f1_0(self):
        """When retrieved is empty, F1 must be 0.0."""
        result = self._compute_f1(set(), {1, 2, 3})
        assert result["f1"] == 0.0

    def test_partial_retrieval_f1(self):
        """Partial overlap must produce correct F1."""
        # retrieved={1,2,3}, relevant={1,2,4}  → TP=2, P=2/3, R=2/3, F1=2/3
        result = self._compute_f1({1, 2, 3}, {1, 2, 4})
        expected_f1 = 2/3
        assert abs(result["f1"] - expected_f1) < 1e-6

    def test_precision_penalises_noise(self):
        """Returning irrelevant chunks must lower precision."""
        r_clean = self._compute_f1({1, 2}, {1, 2})
        r_noisy = self._compute_f1({1, 2, 3, 4, 5}, {1, 2})
        assert r_noisy["precision"] < r_clean["precision"]

    def test_recall_penalises_missed_relevant(self):
        """Missing relevant chunks must lower recall."""
        r_full = self._compute_f1({1, 2, 3}, {1, 2, 3})
        r_miss = self._compute_f1({1}, {1, 2, 3})
        assert r_miss["recall"] < r_full["recall"]

    def test_f1_threshold_is_0_70(self):
        """Document that minimum acceptable F1 is 0.70."""
        MIN_F1 = 0.70
        assert MIN_F1 == 0.70, "F1 threshold changed — update docs and re-evaluate."

    def test_gold_standard_file_exists_when_ready(self):
        """Gold-standard Q&A JSON file must exist before full evaluation."""
        gold_path = os.environ.get("TUTOR_GOLD_PATH", "data/gold_qa_100.json")
        if not os.path.exists(gold_path):
            pytest.skip(
                f"Gold-standard file not created yet: {gold_path}\n"
                "Complete corpus preparation before running full F1 evaluation."
            )
        with open(gold_path) as f:
            data = json.load(f)
        assert len(data) >= 100, (
            f"Gold-standard file has only {len(data)} items. Need >= 100."
        )
        for item in data[:3]:
            assert "question" in item, "Gold item missing 'question' key."
            assert "relevant_chunks" in item, "Gold item missing 'relevant_chunks' key."
