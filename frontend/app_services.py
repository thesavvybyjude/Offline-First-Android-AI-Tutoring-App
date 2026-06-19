"""
Shared app services: DB, RAG, and on-device inference (no Flask subprocess).
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Callable, Optional

from kivy.clock import Clock

from backend.inference_engine import InferenceEngine
from backend.rag_pipeline import RAGPipeline
from backend.seed_data import seed_default_knowledge
from backend.sm2_scheduler import SM2Scheduler
from frontend.app_paths import ensure_app_storage, is_android

logger = logging.getLogger(__name__)


class AppServices:
    def __init__(self, user_data_dir: Optional[str] = None):
        paths = ensure_app_storage(user_data_dir)
        self.data_dir: Path = paths["data_dir"]
        self.models_dir: Path = paths["models_dir"]
        self.db_path: Path = paths["db_path"]

        self.scheduler: Optional[SM2Scheduler] = None
        self.rag: Optional[RAGPipeline] = None
        self.engine: Optional[InferenceEngine] = None

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
                try:
                    from llama_cpp import Llama  # noqa: F401
                except ImportError:
                    return False, (
                        "llama-cpp-python not installed. "
                        "On desktop: pip install llama-cpp-python. "
                        "On Android APK: use a build with AI dependencies."
                    )

                if self.rag is None:
                    try:
                        self.rag = RAGPipeline(self.data_dir)
                        self.rag.load(model_cache_dir=self.models_dir / "embeddings")
                    except Exception as rag_exc:
                        logger.warning("RAG load skipped: %s", rag_exc)
                        self.rag = None

                if self.engine is None:
                    self.engine = InferenceEngine(models_dir=self.models_dir)
                    ram = 3.0 if is_android() else 4.0
                    self.engine.load(ram_gb=ram)

                self._ai_ready = self.engine is not None and self.engine.is_loaded
                if not self._ai_ready:
                    return False, "Model file not found — run: python setup_env.py"
                self._ai_error = None
                return True, None
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
            return "Loading AI models…"
        if self.is_ai_ready():
            model_name = self.engine.model_path.name if self.engine else "model"
            return f"AI ready ({model_name})"
        if self._ai_error:
            return f"AI offline: {self._ai_error}"
        return "AI not loaded — run setup_env.py to download a model"

    def build_tutor_prompt(self, query: str) -> tuple[str, list[str]]:
        if self.rag and self.rag.is_loaded:
            pkg = self.rag.build_prompt(query, grade_level=self.grade_level)
            sources = [c.source for c in pkg.context_chunks]
            return pkg.prompt, sources
        fallback = (
            f"### System\nYou are a tutor for Nigerian SS2 students.\n\n"
            f"### Student\n{query}\n\n### Tutor Response\n"
        )
        return fallback, []

    def generate_stream(self, prompt: str):
        if not self.is_ai_ready():
            raise RuntimeError(self.ai_status_message())
        assert self.engine is not None
        return self.engine.generate_stream(prompt)
