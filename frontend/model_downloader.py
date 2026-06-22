"""
Model downloader for first-run on Android.

If the GGUF model isn't bundled in the APK (or the user wants a different
model), this module downloads it from HuggingFace on first launch.

Usage:
    from frontend.model_downloader import ModelDownloader

    downloader = ModelDownloader(models_dir=Path("models"))
    downloader.download_async(
        on_progress=lambda pct: print(f"{pct}%"),
        on_complete=lambda ok, err: print("Done!" if ok else err),
    )
"""

from __future__ import annotations

import logging
import os
import threading
import urllib.request
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# Default model: SmolLM2-360M-Instruct Q4_K_M (~271 MB)
DEFAULT_MODEL_URL = (
    "https://huggingface.co/lmstudio-community/SmolLM2-360M-Instruct-GGUF/"
    "resolve/main/SmolLM2-360M-Instruct-Q4_K_M.gguf"
)
DEFAULT_MODEL_FILENAME = "SmolLM2-360M-Instruct-Q4_K_M.gguf"
EXPECTED_SIZE_MB = 271  # approximate, for progress estimation


class ModelDownloader:
    """Downloads AI model files with progress reporting."""

    def __init__(self, models_dir: Path):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self._downloading = False
        self._cancelled = False

    @property
    def model_path(self) -> Path:
        return self.models_dir / DEFAULT_MODEL_FILENAME

    def model_exists(self) -> bool:
        """Check if ANY valid GGUF model is already in models_dir."""
        # Check the default model first
        p = self.model_path
        if p.exists() and p.stat().st_size > 100_000_000:
            return True
        # Check for any other GGUF file that's large enough to be real
        return self.find_existing_model() is not None

    def find_existing_model(self) -> Optional[Path]:
        """Return the path to any existing GGUF model, or None."""
        for gguf in sorted(self.models_dir.glob("*.gguf"), key=lambda p: p.stat().st_size):
            if gguf.stat().st_size > 100_000_000:
                return gguf
        return None

    def download_sync(
        self,
        url: str = DEFAULT_MODEL_URL,
        filename: str = DEFAULT_MODEL_FILENAME,
        on_progress: Optional[Callable[[int], None]] = None,
    ) -> tuple[bool, Optional[str]]:
        """
        Download model synchronously. Returns (success, error_message).
        
        on_progress: called with percentage (0-100) during download.
        """
        if self._downloading:
            return False, "Download already in progress"

        self._downloading = True
        self._cancelled = False
        dest = self.models_dir / filename
        temp = dest.with_suffix(".tmp")

        try:
            logger.info("Downloading %s → %s", url, dest)

            def _hook(block_num, block_size, total_size):
                if self._cancelled:
                    raise _DownloadCancelled()
                if total_size > 0 and on_progress:
                    pct = min(100, int(block_num * block_size * 100 / total_size))
                    on_progress(pct)

            urllib.request.urlretrieve(url, str(temp), reporthook=_hook)

            # Verify download
            size = temp.stat().st_size
            if size < 100_000_000:
                temp.unlink(missing_ok=True)
                return False, f"Downloaded file too small ({size} bytes) — may be corrupted"

            # Atomic rename
            if dest.exists():
                dest.unlink()
            temp.rename(dest)

            logger.info("Model downloaded: %s (%.0f MB)", dest.name, size / 1e6)
            if on_progress:
                on_progress(100)
            return True, None

        except _DownloadCancelled:
            temp.unlink(missing_ok=True)
            return False, "Download cancelled"
        except Exception as e:
            temp.unlink(missing_ok=True)
            logger.exception("Model download failed")
            return False, str(e)
        finally:
            self._downloading = False

    def download_async(
        self,
        url: str = DEFAULT_MODEL_URL,
        filename: str = DEFAULT_MODEL_FILENAME,
        on_progress: Optional[Callable[[int], None]] = None,
        on_complete: Optional[Callable[[bool, Optional[str]], None]] = None,
    ) -> None:
        """Download model in a background thread."""
        def _worker():
            ok, err = self.download_sync(url, filename, on_progress)
            if on_complete:
                # Schedule on Kivy main thread if available
                try:
                    from kivy.clock import Clock
                    Clock.schedule_once(lambda dt: on_complete(ok, err), 0)
                except ImportError:
                    on_complete(ok, err)

        threading.Thread(target=_worker, daemon=True, name="ModelDownloader").start()

    def cancel(self) -> None:
        """Cancel an in-progress download."""
        self._cancelled = True

    @property
    def is_downloading(self) -> bool:
        return self._downloading


class _DownloadCancelled(Exception):
    pass
