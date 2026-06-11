"""
RAG Pipeline: Semantic chunking, FAISS indexing, and context retrieval.
Runs fully offline using all-MiniLM-L6-v2 (22MB) + FAISS FlatIP index.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import faiss
import numpy as np
from jinja2 import Template
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

CHUNK_SIZE_TOKENS = 256
CHUNK_OVERLAP_TOKENS = 50
MIN_CHUNK_TOKENS = 80
TOP_K = 3
SIMILARITY_THRESHOLD = 0.45
MAX_PROMPT_TOKENS = 1024

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384  # all-MiniLM-L6-v2 output dimension

PROMPT_TEMPLATE = Template("""\
### System
You are an expert tutor for Nigerian secondary school students (NERDC/WAEC curriculum).
Answer clearly, concisely, and at a {{ grade_level }} level. Use examples where helpful.

### Relevant Curriculum Context
{% for chunk in context_chunks %}
[Source {{ loop.index }}: {{ chunk.source }}]
{{ chunk.text }}
{% endfor %}

### Student Question
{{ query }}

### Tutor Response
""")


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class Chunk:
    id: str
    text: str
    source: str          # e.g. "Biology_SS2_Ch3"
    subject: str
    token_count: int


@dataclass
class RetrievalResult:
    chunks: list[Chunk]
    scores: list[float]
    query_embedding: np.ndarray
    elapsed_ms: float


@dataclass
class PromptPackage:
    prompt: str
    context_chunks: list[Chunk]
    token_estimate: int


# ---------------------------------------------------------------------------
# Chunker
# ---------------------------------------------------------------------------

class SemanticChunker:
    """
    Splits raw curriculum text into overlapping fixed-token windows,
    respecting sentence boundaries.
    """

    # Rough approximation: 1 token ≈ 4 characters for English text
    CHARS_PER_TOKEN = 4

    def chunk_text(self, text: str, source: str, subject: str) -> list[Chunk]:
        """Return list of Chunk objects from a raw document string."""
        sentences = self._split_sentences(text)
        chunks: list[Chunk] = []
        buffer: list[str] = []
        buffer_tokens = 0
        chunk_idx = 0

        for sent in sentences:
            sent_tokens = self._estimate_tokens(sent)
            if buffer_tokens + sent_tokens > CHUNK_SIZE_TOKENS and buffer:
                chunk = self._make_chunk(buffer, source, subject, chunk_idx)
                if chunk.token_count >= MIN_CHUNK_TOKENS:
                    chunks.append(chunk)
                chunk_idx += 1
                # Keep overlap: retain last N tokens worth of sentences
                buffer, buffer_tokens = self._trim_to_overlap(buffer)
            buffer.append(sent)
            buffer_tokens += sent_tokens

        # Final buffer
        if buffer:
            chunk = self._make_chunk(buffer, source, subject, chunk_idx)
            if chunk.token_count >= MIN_CHUNK_TOKENS:
                chunks.append(chunk)

        logger.info(f"Chunked '{source}' → {len(chunks)} chunks")
        return chunks

    # --- helpers ---

    def _split_sentences(self, text: str) -> list[str]:
        """Basic sentence splitter on . ! ? boundaries."""
        text = re.sub(r"\s+", " ", text.strip())
        return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]

    def _estimate_tokens(self, text: str) -> int:
        return max(1, len(text) // self.CHARS_PER_TOKEN)

    def _make_chunk(self, sentences: list[str], source: str, subject: str, idx: int) -> Chunk:
        text = " ".join(sentences)
        return Chunk(
            id=f"{source}_{idx:04d}",
            text=text,
            source=source,
            subject=subject,
            token_count=self._estimate_tokens(text),
        )

    def _trim_to_overlap(self, sentences: list[str]) -> tuple[list[str], int]:
        """Keep trailing sentences totalling ~CHUNK_OVERLAP_TOKENS."""
        kept: list[str] = []
        tokens = 0
        for sent in reversed(sentences):
            t = self._estimate_tokens(sent)
            if tokens + t > CHUNK_OVERLAP_TOKENS:
                break
            kept.insert(0, sent)
            tokens += t
        return kept, tokens


# ---------------------------------------------------------------------------
# FAISS Index Manager
# ---------------------------------------------------------------------------

class FAISSIndex:
    """
    Wraps a FAISS FlatIP (inner-product / cosine) index.
    Embeddings are L2-normalised before insertion so IP == cosine similarity.
    """

    def __init__(self, dim: int = EMBEDDING_DIM):
        self.dim = dim
        self.index: Optional[faiss.IndexFlatIP] = None
        self.chunks: list[Chunk] = []

    def build(self, chunks: list[Chunk], embeddings: np.ndarray) -> None:
        assert embeddings.shape == (len(chunks), self.dim), \
            f"Shape mismatch: {embeddings.shape} vs ({len(chunks)}, {self.dim})"
        normed = self._l2_normalize(embeddings)
        self.index = faiss.IndexFlatIP(self.dim)
        self.index.add(normed.astype(np.float32))
        self.chunks = list(chunks)
        logger.info(f"FAISS index built: {self.index.ntotal} vectors")

    def search(self, query_embedding: np.ndarray, k: int = TOP_K) -> tuple[list[Chunk], list[float]]:
        if self.index is None or self.index.ntotal == 0:
            return [], []
        q = self._l2_normalize(query_embedding.reshape(1, -1)).astype(np.float32)
        scores, indices = self.index.search(q, min(k, self.index.ntotal))
        results, result_scores = [], []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0 and score >= SIMILARITY_THRESHOLD:
                results.append(self.chunks[idx])
                result_scores.append(float(score))
        return results, result_scores

    def save(self, index_path: Path, chunks_path: Path) -> None:
        faiss.write_index(self.index, str(index_path))
        with open(chunks_path, "w", encoding="utf-8") as f:
            json.dump([vars(c) for c in self.chunks], f, ensure_ascii=False, indent=2)
        logger.info(f"Saved index → {index_path}, chunks → {chunks_path}")

    def load(self, index_path: Path, chunks_path: Path) -> None:
        self.index = faiss.read_index(str(index_path))
        with open(chunks_path, encoding="utf-8") as f:
            self.chunks = [Chunk(**d) for d in json.load(f)]
        logger.info(f"Loaded FAISS index: {self.index.ntotal} vectors, {len(self.chunks)} chunks")

    @staticmethod
    def _l2_normalize(arr: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(arr, axis=-1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)
        return arr / norms


# ---------------------------------------------------------------------------
# RAG Pipeline (main class)
# ---------------------------------------------------------------------------

class RAGPipeline:
    """
    Orchestrates: embed → search → threshold filter → inject into prompt.
    Thread-safe for single-device use (no concurrent inference).
    """

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.index_path = data_dir / "curriculum.index"
        self.chunks_path = data_dir / "chunks.json"

        self.embedder: Optional[SentenceTransformer] = None
        self.faiss_index = FAISSIndex()
        self.chunker = SemanticChunker()
        self._loaded = False

    # --- Public API ---

    def load(self, model_cache_dir: Optional[Path] = None) -> None:
        """Load embedding model + FAISS index. Call once at app startup."""
        logger.info("Loading embedding model…")
        kwargs = {}
        if model_cache_dir:
            kwargs["cache_folder"] = str(model_cache_dir)
        self.embedder = SentenceTransformer(EMBEDDING_MODEL, **kwargs)

        if self.index_path.exists() and self.chunks_path.exists():
            self.faiss_index.load(self.index_path, self.chunks_path)
        else:
            logger.warning("No FAISS index found — call ingest_documents() first")

        self._loaded = True
        logger.info("RAG pipeline ready")

    def ingest_documents(self, documents: list[dict]) -> None:
        """
        Build or rebuild the FAISS index from raw documents.

        documents: list of {"text": str, "source": str, "subject": str}
        """
        self._require_loaded()
        all_chunks: list[Chunk] = []
        for doc in documents:
            chunks = self.chunker.chunk_text(
                doc["text"], doc["source"], doc["subject"]
            )
            all_chunks.extend(chunks)

        if not all_chunks:
            raise ValueError("No chunks produced — check document content")

        logger.info(f"Embedding {len(all_chunks)} chunks…")
        texts = [c.text for c in all_chunks]
        embeddings = self.embedder.encode(
            texts,
            batch_size=64,
            show_progress_bar=True,
            normalize_embeddings=False,
        )
        self.faiss_index.build(all_chunks, np.array(embeddings))
        self.faiss_index.save(self.index_path, self.chunks_path)

    def retrieve(self, query: str) -> RetrievalResult:
        """Encode query and retrieve top-K similar chunks."""
        self._require_loaded()
        t0 = time.perf_counter()
        q_emb = self.embedder.encode([query], normalize_embeddings=False)[0]
        chunks, scores = self.faiss_index.search(np.array(q_emb))
        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.debug(f"Retrieved {len(chunks)} chunks in {elapsed_ms:.1f}ms")
        return RetrievalResult(
            chunks=chunks,
            scores=scores,
            query_embedding=q_emb,
            elapsed_ms=elapsed_ms,
        )

    def build_prompt(
        self,
        query: str,
        grade_level: str = "SS2",
        retrieval: Optional[RetrievalResult] = None,
    ) -> PromptPackage:
        """Build final prompt string with injected context. Token-capped at MAX_PROMPT_TOKENS."""
        if retrieval is None:
            retrieval = self.retrieve(query)

        prompt = PROMPT_TEMPLATE.render(
            grade_level=grade_level,
            context_chunks=retrieval.chunks,
            query=query,
        )
        # Rough token estimate
        token_estimate = len(prompt) // SemanticChunker.CHARS_PER_TOKEN

        # Trim context if over budget
        ctx_chunks = list(retrieval.chunks)
        while token_estimate > MAX_PROMPT_TOKENS and ctx_chunks:
            ctx_chunks.pop()
            prompt = PROMPT_TEMPLATE.render(
                grade_level=grade_level,
                context_chunks=ctx_chunks,
                query=query,
            )
            token_estimate = len(prompt) // SemanticChunker.CHARS_PER_TOKEN

        return PromptPackage(
            prompt=prompt,
            context_chunks=ctx_chunks,
            token_estimate=token_estimate,
        )

    def _require_loaded(self) -> None:
        if not self._loaded or self.embedder is None:
            raise RuntimeError("Call RAGPipeline.load() before use")
