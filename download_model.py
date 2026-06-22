import sys
from pathlib import Path

# Add the implementation dir to path
sys.path.append(str(Path(__file__).parent.absolute()))

from frontend.model_downloader import ModelDownloader

dl = ModelDownloader(Path("models"))
print("Starting download...")
def progress(pct):
    print(f"\rDownload progress: {pct}%", end="")

success, err = dl.download_sync(on_progress=progress)
print() # newline
if success:
    print("Download completed successfully.")
else:
    print(f"Download failed: {err}")
