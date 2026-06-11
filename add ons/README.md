# Offline-First Android AI Tutoring App

Phi-3 Mini (GGUF) + RAG (FAISS) + SM2 Spaced Repetition — runs fully on-device.

## Architecture

```
Student Query
    │
    ▼
RAGPipeline.build_prompt()          ← FAISS similarity search (all-MiniLM-L6-v2)
    │   top-3 curriculum chunks
    ▼
InferenceEngine.generate()          ← Phi-3 Mini Q4_K_M (llama-cpp-python)
    │   streamed response
    ▼
Kivy UI (5 screens)                 ← Login / Dashboard / Chat / Review / Settings
    │   student rates card (0–5)
    ▼
SM2Scheduler.record_response()      ← SQLite + SM-2 algorithm
    │   if online
    ▼
SyncLayer.push_delta()              ← Flask REST API (last-write-wins)
```

## Project Structure

```
tutor_app/
├── core/
│   ├── rag_pipeline.py         # Chunking + FAISS + prompt building
│   ├── inference_engine.py     # Phi-3 GGUF wrapper + streaming
│   └── sm2_scheduler.py        # SM-2 algorithm + SQLite schema
├── sync/
│   ├── sync_layer.py           # Delta sync client + conflict resolver
│   └── server.py               # Flask REST sync server
├── ui/
│   └── app.py                  # Kivy/KivyMD 5-screen app
├── tests/
│   └── test_all.py             # pytest suite (no real models needed)
├── models/                     # Place GGUF + embedding model here
├── data/                       # SQLite DB + FAISS index (per-student)
├── buildozer.spec              # Android APK config
└── requirements.txt
```

## Quickstart (Desktop)

### 1. Install dependencies

```bash
python3.11 -m venv .venv
source .venv/bin/activate

pip install \
  llama-cpp-python \
  sentence-transformers \
  faiss-cpu \
  kivy[base] kivymd \
  flask jinja2 numpy pytest
```

### 2. Download models

```bash
mkdir -p models

# Phi-3 Mini GGUF (~2.1GB)
pip install huggingface-hub
huggingface-cli download \
  microsoft/Phi-3-mini-4k-instruct-gguf \
  Phi-3-mini-4k-instruct-q4.gguf \
  --local-dir ./models

# all-MiniLM-L6-v2 is downloaded automatically by sentence-transformers
# on first RAGPipeline.load() call (~22MB)
```

### 3. Ingest curriculum

```python
from pathlib import Path
from core.rag_pipeline import RAGPipeline

rag = RAGPipeline(data_dir=Path("data/default/rag"))
rag.load()

# Add your NERDC/WAEC PDF texts here
documents = [
    {
        "text": open("corpus/Biology_SS2.txt").read(),
        "source": "Biology_SS2",
        "subject": "Biology",
    },
    # add more...
]
rag.ingest_documents(documents)
print("Index built!")
```

### 4. Run the app

```bash
python ui/app.py
```

### 5. Run tests (no models required — all mocked)

```bash
pytest tests/test_all.py -v
```

## Android APK Build

```bash
pip install buildozer cython

# First build (downloads NDK/SDK — ~20 min)
buildozer android debug

# Deploy to connected device
buildozer android deploy run

# Or manually
adb install -r bin/aitutor-1.0.0-arm64-v8a-debug.apk
```

### Device Requirements
- Android 9+ (API 28)
- ARM64 (arm64-v8a)
- ≥ 3GB RAM
- ≥ 4GB free storage

## Sync Server

```bash
cd sync/
pip install flask
python server.py
# Runs on :5000 — reverse proxy behind nginx for production
```

## Performance Targets

| Metric | Target | Typical (mid-range) |
|--------|--------|----------------------|
| First token latency | < 3s | ~1.2–2.8s |
| Full response (100 tok) | < 15s | ~8–12s |
| RAG retrieval | < 200ms | ~40–80ms |
| SM2 update (SQLite) | < 5ms | ~1ms |
| App cold start | < 10s | ~5–8s |

## SM-2 Algorithm

Quality 0–5 → EF update → interval:
- Rep 1: 1 day
- Rep 2: 6 days
- Rep 3+: interval × EF
- Quality < 3: reset to day 1, EF unchanged

EF update: `EF' = EF + (0.1 - (5-q) × (0.08 + (5-q) × 0.02))`  
Minimum EF: 1.3

## Sync Protocol

1. Client polls connectivity every 30s
2. On connect: POST unsynced rows → `/api/v1/sync/push`
3. Server applies last-write-wins (by `updated_at`)
4. Client GETs changes since last pull → `/api/v1/sync/pull`
5. Conflict: keep higher `repetitions` count on tie

## License

MIT
