"""
Resolve writable and bundled paths for desktop dev and Android APK.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Optional

from kivy.utils import platform as kivy_platform


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def is_android() -> bool:
    return kivy_platform == "android" or "ANDROID_ARGUMENT" in __import__("os").environ


def _copy_if_missing(src: Path, dst: Path) -> None:
    if not src.is_file():
        return
    if dst.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _copy_tree_lite(src: Path, dst: Path, skip_gguf: bool = True) -> None:
    if not src.exists():
        return
    for path in src.rglob("*"):
        if not path.is_file():
            continue
        if skip_gguf and path.suffix.lower() == ".gguf":
            continue
        rel = path.relative_to(src)
        target = dst / rel
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


def ensure_app_storage(user_data_dir: Optional[str] = None) -> dict[str, Path]:
    """
    Return data_dir and models_dir suitable for the current platform.
    On Android, copies bundled corpus/index into writable user_data_dir on first run.
    """
    root = project_root()
    writable = Path(user_data_dir) if user_data_dir else root

    data_dir = writable / "data"
    models_dir = writable / "models"
    data_dir.mkdir(parents=True, exist_ok=True)
    models_dir.mkdir(parents=True, exist_ok=True)

    bundled_data = root / "data"
    bundled_models = root / "models"
    if bundled_data.exists():
        _copy_tree_lite(bundled_data, data_dir, skip_gguf=True)
    if bundled_models.exists():
        for gguf in bundled_models.glob("*.gguf"):
            _copy_if_missing(gguf, models_dir / gguf.name)

    return {
        "root": root,
        "writable": writable,
        "data_dir": data_dir,
        "models_dir": models_dir,
        "db_path": data_dir / "tutor.db",
    }
