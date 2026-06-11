"""
Inference Engine: Phi-3 Mini GGUF via llama-cpp-python.
Supports streaming token generation and graceful fallback for low-RAM devices.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Generator, Iterator, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DEFAULT_MODEL_FILENAME = "Phi-3-mini-4k-instruct-q4.gguf"

# Generation defaults — tuned for factual tutoring (low temperature)
DEFAULT_PARAMS = {
    "max_tokens": 512,
    "temperature": 0.3,
    "top_p": 0.9,
    "top_k": 40,
    "repeat_penalty": 1.1,
    "stop": ["### Student", "### System", "</s>"],
}

# Hardware presets keyed by available RAM (GB)
RAM_PRESETS: dict[str, dict] = {
    "3gb":  {"n_ctx": 2048, "n_threads": 4, "n_gpu_layers": 0},
    "4gb":  {"n_ctx": 4096, "n_threads": 4, "n_gpu_layers": 0},
    "6gb+": {"n_ctx": 4096, "n_threads": 6, "n_gpu_layers": 0},
}


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class GenerationResult:
    text: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    elapsed_ms: float
    tokens_per_second: float


@dataclass
class BenchmarkResult:
    device_id: str
    model_path: str
    n_prompts: int
    mean_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    mean_tokens_per_second: float
    timestamp: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%S"))


# ---------------------------------------------------------------------------
# Inference Engine
# ---------------------------------------------------------------------------

class InferenceEngine:
    """
    Thin wrapper around llama_cpp.Llama.
    
    Usage:
        engine = InferenceEngine(model_path=Path("models/Phi-3-mini-4k-instruct-q4.gguf"))
        engine.load(ram_gb=4)
        
        # Blocking
        result = engine.generate("Explain photosynthesis")
        
        # Streaming
        for token in engine.generate_stream("Explain photosynthesis"):
            print(token, end="", flush=True)
    """

    def __init__(self, model_path: Optional[Path] = None, models_dir: Optional[Path] = None):
        if model_path:
            self.model_path = Path(model_path)
        elif models_dir:
            self.model_path = Path(models_dir) / DEFAULT_MODEL_FILENAME
        else:
            raise ValueError("Provide model_path or models_dir")

        self._llm = None
        self._lock = threading.Lock()
        self._loaded = False

    # --- Lifecycle ---

    def load(self, ram_gb: float = 4.0, verbose: bool = False) -> None:
        """Load the GGUF model. Blocks until ready (~3–8s on first load)."""
        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Model not found: {self.model_path}\n"
                "Download Phi-3-mini-4k-instruct-q4.gguf from HuggingFace:\n"
                "  huggingface-cli download microsoft/Phi-3-mini-4k-instruct-gguf "
                "Phi-3-mini-4k-instruct-q4.gguf --local-dir ./models"
            )

        preset = self._select_preset(ram_gb)
        logger.info(f"Loading model {self.model_path.name} with preset {preset}…")

        try:
            from llama_cpp import Llama
            self._llm = Llama(
                model_path=str(self.model_path),
                n_ctx=preset["n_ctx"],
                n_threads=preset["n_threads"],
                n_gpu_layers=preset["n_gpu_layers"],
                verbose=verbose,
            )
        except ImportError:
            raise ImportError(
                "llama-cpp-python not installed. "
                "Install with: pip install llama-cpp-python --extra-index-url "
                "https://abetlen.github.io/llama-cpp-python/whl/cpu"
            )

        self._loaded = True
        logger.info("Model loaded and ready")

    def unload(self) -> None:
        """Release model memory."""
        with self._lock:
            if self._llm is not None:
                del self._llm
                self._llm = None
                self._loaded = False
        logger.info("Model unloaded")

    # --- Generation ---

    def generate(
        self,
        prompt: str,
        params: Optional[dict] = None,
        on_token: Optional[Callable[[str], None]] = None,
    ) -> GenerationResult:
        """
        Blocking generation. Optionally calls on_token(token_str) for streaming UI updates.
        """
        self._require_loaded()
        p = {**DEFAULT_PARAMS, **(params or {})}

        with self._lock:
            t0 = time.perf_counter()
            if on_token:
                text, usage = self._stream_with_callback(prompt, p, on_token)
            else:
                output = self._llm(prompt, **p)
                text = output["choices"][0]["text"]
                usage = output.get("usage", {})
            elapsed_ms = (time.perf_counter() - t0) * 1000

        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", len(text.split()))
        tps = (completion_tokens / (elapsed_ms / 1000)) if elapsed_ms > 0 else 0

        return GenerationResult(
            text=text.strip(),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            elapsed_ms=elapsed_ms,
            tokens_per_second=tps,
        )

    def generate_stream(self, prompt: str, params: Optional[dict] = None) -> Iterator[str]:
        """
        Generator that yields token strings one at a time.
        Use in Kivy via Clock.schedule_once or a background thread.
        """
        self._require_loaded()
        p = {**DEFAULT_PARAMS, **(params or {}), "stream": True}

        with self._lock:
            for chunk in self._llm(prompt, **p):
                token = chunk["choices"][0].get("text", "")
                if token:
                    yield token

    # --- Benchmarking ---

    def benchmark(
        self,
        prompts: list[str],
        device_id: str = "unknown",
        params: Optional[dict] = None,
    ) -> BenchmarkResult:
        """Run N prompts, collect latency stats. Returns BenchmarkResult."""
        import statistics
        latencies: list[float] = []
        tps_list: list[float] = []

        for i, prompt in enumerate(prompts):
            logger.debug(f"Benchmark prompt {i+1}/{len(prompts)}")
            result = self.generate(prompt, params=params)
            latencies.append(result.elapsed_ms)
            tps_list.append(result.tokens_per_second)

        latencies_sorted = sorted(latencies)
        n = len(latencies_sorted)

        return BenchmarkResult(
            device_id=device_id,
            model_path=str(self.model_path),
            n_prompts=n,
            mean_latency_ms=statistics.mean(latencies),
            p50_latency_ms=latencies_sorted[n // 2],
            p95_latency_ms=latencies_sorted[int(n * 0.95)],
            mean_tokens_per_second=statistics.mean(tps_list),
        )

    # --- Helpers ---

    def _stream_with_callback(
        self,
        prompt: str,
        params: dict,
        on_token: Callable[[str], None],
    ) -> tuple[str, dict]:
        """Internal: stream tokens and call callback, return (full_text, usage)."""
        params = {**params, "stream": True}
        tokens: list[str] = []
        for chunk in self._llm(prompt, **params):
            token = chunk["choices"][0].get("text", "")
            if token:
                tokens.append(token)
                on_token(token)
        text = "".join(tokens)
        # llama-cpp doesn't return usage in stream mode, estimate
        usage = {
            "prompt_tokens": len(prompt.split()),
            "completion_tokens": len(tokens),
        }
        return text, usage

    def _select_preset(self, ram_gb: float) -> dict:
        if ram_gb >= 6:
            return RAM_PRESETS["6gb+"]
        elif ram_gb >= 4:
            return RAM_PRESETS["4gb"]
        else:
            return RAM_PRESETS["3gb"]

    def _require_loaded(self) -> None:
        if not self._loaded or self._llm is None:
            raise RuntimeError("Call InferenceEngine.load() before generating")

    @property
    def is_loaded(self) -> bool:
        return self._loaded
