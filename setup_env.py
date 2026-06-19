"""
setup_env.py
Scaffolds the environment: downloads a small on-device model (~270 MB) by default.
"""

import sys
import urllib.request
from pathlib import Path

# Default mobile-friendly model (~271 MB Q4_K_M)
SMALL_MODEL_URL = (
    "https://huggingface.co/tensorblock/SmolLM2-360M-Instruct-GGUF/"
    "resolve/main/SmolLM2-360M-Instruct-Q4_K_M.gguf"
)
SMALL_MODEL_FILENAME = "SmolLM2-360M-Instruct-Q4_K_M.gguf"

# Optional larger desktop model (~2.4 GB)
LARGE_MODEL_URL = (
    "https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/"
    "resolve/main/Phi-3-mini-4k-instruct-q4.gguf"
)
LARGE_MODEL_FILENAME = "Phi-3-mini-4k-instruct-q4.gguf"


def download_progress_hook(count, block_size, total_size):
    if total_size <= 0:
        return
    percent = int(count * block_size * 100 / total_size)
    sys.stdout.write(f"\rDownloading: {percent}% ")
    sys.stdout.flush()


def download_model(url: str, dest: Path) -> None:
    print(f"Downloading {dest.name} from HuggingFace…")
    urllib.request.urlretrieve(url, dest, reporthook=download_progress_hook)
    print("\nDownload complete.")


def setup(use_large_model: bool = False):
    print("Initializing Offline-First AI Tutoring System Environment…")

    for d in ["data/corpus/pdfs", "data/corpus/images", "models", "logs"]:
        Path(d).mkdir(parents=True, exist_ok=True)
        print(f"Ensured directory exists: {d}")

    models_dir = Path("models")
    if use_large_model:
        model_path = models_dir / LARGE_MODEL_FILENAME
        url = LARGE_MODEL_URL
    else:
        model_path = models_dir / SMALL_MODEL_FILENAME
        url = SMALL_MODEL_URL

    if not model_path.exists():
        print(f"\nModel not found. Downloading {model_path.name}…")
        try:
            download_model(url, model_path)
        except Exception as e:
            print(f"\nError downloading model: {e}")
            print("Try manually: huggingface-cli download tensorblock/SmolLM2-360M-Instruct-GGUF")
            sys.exit(1)
    else:
        size_mb = model_path.stat().st_size / (1024 * 1024)
        print(f"\nModel {model_path.name} already exists ({size_mb:.0f} MB).")

    print("\nEnvironment setup complete.")
    print("Run: python main.py")
    print("Or build APK: buildozer android debug")


if __name__ == "__main__":
    large = "--large" in sys.argv
    setup(use_large_model=large)
