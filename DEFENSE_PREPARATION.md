# Defense Preparation Report

This document prepares the development team for rigorous technical scrutiny from supervisors, lecturers, or architectural reviewers.

---

## 1. Edge AI and Inference Constraints

**Q: Why was `llama-cpp-python` chosen over PyTorch or TensorFlow for on-device inference?**
* **Answer**: Android devices have severe RAM constraints and lack standard NVIDIA GPUs. PyTorch relies heavily on CUDA and carries a massive library overhead. `llama.cpp` is written in pure C/C++, is heavily optimized for ARM CPUs (which power Androids), and supports GGUF quantization. This allows us to fit a 3.8 billion parameter model (Phi-3) into just ~2.2GB of RAM.
* **Evidence**: `backend/inference_engine.py` (Lines 117-124), utilizing the `Llama` class with `n_gpu_layers=0` for CPU inference.

**Q: How does the system prevent the app from crashing on low-end 3GB RAM phones?**
* **Answer**: The `InferenceEngine` implements dynamic hardware presets. If a device has 3GB of RAM, the system throttles the context window (`n_ctx`) to 2048 tokens and limits CPU threads. For 6GB+ devices, it expands the context to 4096 tokens to allow for more RAG textbook chunks.
* **Evidence**: `backend/inference_engine.py` (Lines 36-40), the `RAM_PRESETS` dictionary.

---

## 2. RAG & Vector Database

**Q: Why use FAISS FlatIP instead of a more complex index like HNSW?**
* **Answer**: HNSW is excellent for billions of vectors, but carries significant memory overhead for building the graph. Our curriculum corpus is relatively small (thousands of chunks, not millions). A Flat Inner-Product (FlatIP) index requires virtually no RAM overhead and can compute exact cosine similarities across a small corpus in milliseconds, making it perfect for mobile edge devices.
* **Evidence**: `backend/rag_pipeline.py` (Line 163), `FAISSIndex` class uses `faiss.IndexFlatIP`.

**Q: How do you prevent the RAG pipeline from injecting too much context and causing an Out-Of-Memory (OOM) error?**
* **Answer**: The system uses a strict `MAX_PROMPT_TOKENS` budget. While building the Jinja prompt, it estimates token counts. If the prompt exceeds the budget, it iteratively pops the least relevant context chunk from the list until it fits safely within the context window.
* **Evidence**: `backend/rag_pipeline.py` (Lines 312-325), the `build_prompt` token-trimming while loop.

---

## 3. Offline-First Synchronization

**Q: In an offline-first app, what happens if a user studies on their phone offline, studies on a tablet offline, and then connects both to the internet simultaneously?**
* **Answer**: The server utilizes a Last-Write-Wins (LWW) conflict resolution strategy. When a push is received, the server compares the timestamp of the incoming `repetition_record` against its own database. If the server's record is newer, it rejects the client's update. Additionally, it tracks the `repetitions` integer count; an update with a higher repetition count generally supersedes a lower one.
* **Evidence**: `backend/sync_layer.py`, specifically the `ConflictResolver.resolve()` method.

**Q: Does the sync process drain mobile data by uploading the whole database?**
* **Answer**: No. The system uses a Delta-Sync mechanism. Local SQLite triggers log the exact rows that have changed into a `sync_log` table. During synchronization, only these flagged rows are pushed to the Flask server, minimizing data usage to mere kilobytes.
* **Evidence**: `backend/sm2_scheduler.py` database triggers, and `backend/sync_layer.py` `_push_deltas()`.
