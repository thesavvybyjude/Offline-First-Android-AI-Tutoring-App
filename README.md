# Offline-First Android AI Tutoring App

A complete offline-first AI tutoring application for Android devices using on-device LLM inference, RAG pipeline, and spaced repetition.

## Project Overview

This app provides personalized tutoring for Nigerian students (NERDC/WAEC curriculum) without requiring internet connectivity. It uses:
- **LLM**: Phi-3 Mini Q4_K_M (2.1GB) for offline text generation
- **RAG**: FAISS + all-MiniLM-L6-v2 for semantic search
- **SM2**: SQLite-based spaced repetition for flashcard scheduling
- **UI**: Kivy/KivyMD for Android interface
- **Sync**: Flask REST with delta sync for offline-first data synchronization

## Technology Stack

| Layer | Technologies |
|-------|--------------|
| Backend | Python 3.11, SQLite3, llama-cpp-python, sentence-transformers, FAISS, Flask, Jinja2 |
| Models | Phi-3 Mini Q4_K_M GGUF, all-MiniLM-L6-v2 |
| Frontend | Kivy, KivyMD, matplotlib, Buildozer |
| Testing | pytest, unittest.mock, pandas, sklearn |

## Project Structure

```
.
├── backend/
│   ├── rag_pipeline.py      # RAG retrieval and FAISS index
│   ├── inference_engine.py  # LLM inference with llama-cpp-python
│   ├── sm2_scheduler.py     # Spaced repetition algorithm
│   ├── sync_layer.py        # Offline sync with delta sync
│   └── database.py          # SQLite schema and operations
├── frontend/
│   ├── main.py              # Kivy app entry point
│   ├── screens/
│   │   ├── login_screen.py
│   │   ├── dashboard_screen.py
│   │   ├── tutor_chat_screen.py
│   │   ├── review_screen.py
│   │   └── settings_screen.py
│   └── widgets/
├── models/
│   ├── phi-3-mini-q4_k_m.gguf
│   └── all-MiniLM-L6-v2
├── data/
│   ├── corpus/              # Extracted PDF text
│   ├── chunks/              # Chunked knowledge base
│   ├── faiss_index.index    # FAISS vector index
│   └── tutor.db             # SQLite database
├── tests/
│   ├── test_rag.py
│   ├── test_sm2.py
│   ├── test_sync.py
│   └── test_e2e.py
├── docs/
│   ├── diagrams/
│   └── wireframes/
├── buildozer.spec
└── requirements.txt
```

## Installation

### Development Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Model Setup

```bash
# Download Phi-3 Mini GGUF model (2.1GB)
# Place in models/ directory

# Download embedding model
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2').save('models/all-MiniLM-L6-v2')"
```

## Development Phases

1. **Phase 1**: Environment & Knowledge Base (Weeks 1-2)
2. **Phase 2**: RAG Pipeline (Weeks 3-4)
3. **Phase 3**: SM2 Spaced Repetition (Weeks 5-6)
4. **Phase 4**: Android Front-End UI (Weeks 7-9)
5. **Phase 5**: Offline Sync Layer (Weeks 10-11)
6. **Phase 6**: Integration & Benchmarking (Weeks 12-13)

## Running the Application

### Backend Server

```bash
python backend/server.py
```

### Android App (Development)

```bash
# Run on desktop for testing
python frontend/main.py

# Build APK
buildozer android debug
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=backend --cov=frontend
```

## Performance Targets

- LLM generation: <3s per query on mid-range devices
- Target devices: Android phones with ≥3GB RAM, ≥4GB storage free
- Model footprint: ~2.1GB

## License

[MIT](LICENSE)

---

Built by [Jude Thompson](https://github.com/thesavvybyjude)
