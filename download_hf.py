from huggingface_hub import hf_hub_download
import shutil
import os

repo_id = "lmstudio-community/SmolLM2-360M-Instruct-GGUF"
filename = "SmolLM2-360M-Instruct-Q4_K_M.gguf"
print("Downloading model via huggingface_hub...")
cache_file = hf_hub_download(repo_id=repo_id, filename=filename)
print("Download complete, copying to models/")
os.makedirs("models", exist_ok=True)
shutil.copy(cache_file, f"models/{filename}")
print("Done!")
