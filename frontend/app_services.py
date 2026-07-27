"""
Shared app services: DB, RAG, and on-device inference (no Flask subprocess).

All heavy AI dependencies (llama-cpp-python, faiss, sentence-transformers, numpy)
are imported lazily so the APK can launch even when they're not installed.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Callable, Optional

from kivy.clock import Clock

from backend.sm2_scheduler import SM2Scheduler
from frontend.app_paths import ensure_app_storage, is_android
from frontend.model_downloader import ModelDownloader

logger = logging.getLogger(__name__)

# --- Lazy import flags (set once at first use) ---
_HAS_LLAMA = None
_HAS_RAG = None


def _check_llama() -> bool:
    global _HAS_LLAMA
    if _HAS_LLAMA is None:
        try:
            from llama_cpp import Llama  # noqa: F401
            _HAS_LLAMA = True
        except ImportError:
            _HAS_LLAMA = False
    return _HAS_LLAMA


def _check_rag() -> bool:
    global _HAS_RAG
    if _HAS_RAG is None:
        try:
            import numpy  # noqa: F401
            import faiss  # noqa: F401
            from sentence_transformers import SentenceTransformer  # noqa: F401
            _HAS_RAG = True
        except ImportError:
            _HAS_RAG = False
    return _HAS_RAG


class AppServices:
    def __init__(self, user_data_dir: Optional[str] = None):
        paths = ensure_app_storage(user_data_dir)
        self.data_dir: Path = paths["data_dir"]
        self.models_dir: Path = paths["models_dir"]
        self.db_path: Path = paths["db_path"]

        self.scheduler: Optional[SM2Scheduler] = None
        self.rag = None  # RAGPipeline | None
        self.engine = None  # InferenceEngine | None
        self.downloader = ModelDownloader(self.models_dir)

        self.student_id: Optional[str] = None
        self.grade_level: str = "SS2"
        self.school_id: Optional[str] = None

        self._loading = False
        self._ai_ready = False
        self._ai_error: Optional[str] = None
        self._lock = threading.Lock()

    def bootstrap_student(
        self,
        student_id: str,
        name: str,
        grade_level: str = "SS2",
        school_id: Optional[str] = None,
        on_ai_ready: Optional[Callable[[bool, Optional[str]], None]] = None,
    ) -> None:
        """Create DB, student row, starter flashcards; load AI in background."""
        self.student_id = student_id
        self.grade_level = grade_level
        self.school_id = school_id

        self.scheduler = SM2Scheduler(self.db_path)
        self.scheduler.init_db()
        self.scheduler.upsert_student(student_id, name, grade_level, school_id)

        from backend.seed_data import seed_default_knowledge
        seeded = seed_default_knowledge(self.scheduler, student_id)
        logger.info("Seeded %d flashcards for %s", seeded, student_id)

        if on_ai_ready:
            self.load_ai_async(on_ai_ready)

    def load_ai_async(
        self, on_complete: Callable[[bool, Optional[str]], None]
    ) -> None:
        if self._loading:
            return
        self._loading = True
        self._ai_ready = False
        self._ai_error = None

        def worker():
            ok, err = self._load_ai_sync()
            Clock.schedule_once(lambda dt: on_complete(ok, err), 0)

        threading.Thread(target=worker, daemon=True).start()

    def _load_ai_sync(self) -> tuple[bool, Optional[str]]:
        with self._lock:
            try:
                # --- Check llama-cpp-python ---
                if not _check_llama():
                    return False, "AI engine not available"

                # --- Check if a GGUF model exists before trying to load ---
                if not self.downloader.model_exists():
                    self._ai_ready = False
                    self._ai_error = "AI model not found"
                    return False, "AI model not downloaded yet"

                logger.info("Model found in %s — loading…", self.models_dir)

                # --- Load LLM FIRST (so chat works immediately) ---
                if self.engine is None:
                    from backend.inference_engine import InferenceEngine
                    try:
                        self.engine = InferenceEngine(models_dir=self.models_dir)
                    except (FileNotFoundError, ValueError) as e:
                        return False, "AI model not found"
                    ram = 3.0 if is_android() else 4.0
                    self.engine.load(ram_gb=ram)

                self._ai_ready = self.engine is not None and self.engine.is_loaded
                if not self._ai_ready:
                    return False, "Model loaded but engine not ready."
                self._ai_error = None

                # --- Load RAG AFTER LLM (optional, can be slow due to
                #     embedding model download from HuggingFace) ---
                if self.rag is None and _check_rag():
                    try:
                        from backend.rag_pipeline import RAGPipeline
                        self.rag = RAGPipeline(self.data_dir)
                        self.rag.load(model_cache_dir=self.models_dir / "embeddings")
                        logger.info("RAG pipeline loaded")
                    except Exception as rag_exc:
                        logger.warning("RAG load skipped: %s", rag_exc)
                        self.rag = None

                return True, None
            except FileNotFoundError as exc:
                logger.warning("AI model file missing: %s", exc)
                self._ai_ready = False
                self._ai_error = "Model not found."
                return False, self._ai_error
            except Exception as exc:
                logger.exception("AI load failed")
                self._ai_ready = False
                self._ai_error = str(exc)
                return False, str(exc)
            finally:
                self._loading = False

    def is_ai_ready(self) -> bool:
        return self._ai_ready and self.engine is not None and self.engine.is_loaded

    def ai_status_message(self) -> str:
        if self._loading:
            return "Loading AI…"
        if self.is_ai_ready():
            return "AI Ready ✓"
        if self._ai_error:
            return "Offline Mode"
        return "Offline Mode"

    def build_tutor_prompt(self, query: str, subject: str = "Biology") -> tuple[str, list[str]]:
        if self.rag and hasattr(self.rag, "is_loaded") and self.rag.is_loaded:
            pkg = self.rag.build_prompt(query, grade_level=self.grade_level, subject=subject)
            sources = [c.source for c in pkg.context_chunks]
            return pkg.prompt, sources
        fallback = (
            f"### System\nYou are a tutor for Nigerian SS1 {subject} students.\n\n"
            f"### Student\n{query}\n\n### Tutor Response\n"
        )
        return fallback, []

    def generate_stream(self, prompt: str):
        if not self.is_ai_ready():
            raise RuntimeError(self.ai_status_message())
        assert self.engine is not None
        return self.engine.generate_stream(prompt)
