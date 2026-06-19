"""
setup_env.py
Scaffolds the environment for the Offline-First AI Tutoring System.
Downloads the GGUF model and sets up the corpus directory.
"""

import os
import urllib.request
import sys
from pathlib import Path

MODEL_URL = "https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf"
MODEL_FILENAME = "Phi-3-mini-4k-instruct-q4.gguf"

def download_progress_hook(count, block_size, total_size):
    """Callback to print download progress"""
    percent = int(count * block_size * 100 / total_size)
    sys.stdout.write(f"\rDownloading model: {percent}% ")
    sys.stdout.flush()

def setup():
    print("Initializing Offline-First AI Tutoring System Environment...")
    
    # Create directories
    dirs = [
        "data/corpus/pdfs",
        "data/corpus/images",
        "models",
        "logs"
    ]
    
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)
        print(f"Ensured directory exists: {d}")
        
    # Download model if not exists
    model_path = Path("models") / MODEL_FILENAME
    if not model_path.exists():
        print(f"\nModel {MODEL_FILENAME} not found. Starting download (this is a large file, ~2.4GB)...")
        try:
            urllib.request.urlretrieve(MODEL_URL, model_path, reporthook=download_progress_hook)
            print("\nDownload complete.")
        except Exception as e:
            print(f"\nError downloading model: {e}")
            sys.exit(1)
    else:
        print(f"\nModel {MODEL_FILENAME} already exists. Skipping download.")
        
    print("\nEnvironment setup complete. You can now run `python frontend/main.py` or tests.")

if __name__ == "__main__":
    setup()
