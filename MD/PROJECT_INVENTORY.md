# Project Inventory

This document serves as the absolute source of truth for the Offline-First Android AI Tutoring App repository. It catalogs every discovered folder, file, route, API endpoint, database model, component, service, utility, and external integration.

---

## 1. Folders and Files

### Root Directory
- `/`
  - `.git/` (Directory)
  - `add ons/` (Directory)
  - `backend/` (Directory)
  - `data/` (Directory)
  - `docs/` (Directory)
  - `frontend/` (Directory)
  - `logs/` (Directory)
  - `models/` (Directory)
  - `tests/` (Directory)
  - `benchmark.py` (Script for LLM latency testing)
  - `buildozer.spec` (Android build configuration)
  - `README.md` (Project documentation)
  - `requirements.txt` (Python dependencies)
  - `seed_flashcards.py` (Script to populate initial SM-2 data)
  - `setup.py` (Package configuration)
  - `setup_env.py` (Environment bootstrapper; downloads 2.1GB Phi-3 model)

### Backend Directory (`/backend`)
- `__init__.py`
- `corpus_processor.py` (PDF text extraction and cleaning)
- `database.py` (General DB logic, if applicable)
- `inference_engine.py` (LLM wrapper and streaming logic)
- `rag_pipeline.py` (FAISS indexing and semantic chunking)
- `server.py` (Flask REST API for synchronization)
- `sm2_scheduler.py` (Spaced repetition algorithm and local DB schema)
- `sync_layer.py` (Background daemon for delta syncing)

### Frontend Directory (`/frontend`)
- `__init__.py`
- `main.py` (Kivy App Entry Point)
- `/screens` (UI Views)
  - `dashboard_screen.py`
  - `login_screen.py`
  - `review_screen.py`
  - `settings_screen.py`
  - `tutor_chat_screen.py`
- `/widgets` (Empty - reserved for reusable UI components)

### Tests Directory (`/tests`)
- `test_all.py` (Unified test suite containing SM2, RAG, Sync, and E2E tests)

---

## 2. API Endpoints & Routes

Defined in `backend/server.py`:

| Endpoint | Method | Purpose | Payload |
|----------|--------|---------|---------|
| `/health` | GET | Check server connectivity | None |
| `/query` | POST | Cloud-based LLM Inference (streams JSON-L) | `{"query": str, "grade_level": str}` |
| `/api/v1/sync/push` | POST | Accept local delta records from the Android client | `{"student_id": str, "records": list, "client_timestamp": str}` |
| `/api/v1/sync/pull` | GET | Fetch remote delta records updated since a timestamp | Query Params: `student_id`, `since` |

---

## 3. Database Models

Defined via SQLite schemas in `backend/sm2_scheduler.py` and `backend/server.py`.

### Edge (Local SQLite) Tables:
- `students`
  - `id` (PK)
  - `name`
  - `grade_level`
  - `school_id`
  - `synced` (int, 0 or 1)
- `knowledge_items`
  - `id` (PK)
  - `subject`
  - `question`
  - `answer`
  - `source_chunk`
  - `difficulty`
- `repetition_records`
  - `id` (PK)
  - `student_id` (FK)
  - `item_id` (FK)
  - `ease_factor` (float)
  - `interval_days` (int)
  - `repetitions` (int)
  - `last_quality` (int)
  - `next_review` (ISO date string)
  - `synced` (int, 0 or 1)
- `sync_log`
  - Tracks dirty records waiting to be pushed to the server. Contains `action` (INSERT/UPDATE/DELETE).

### Cloud (Server SQLite) Tables:
- `repetition_records` (Mirrors the edge schema but acts as the master truth for all students).

---

## 4. Components & Services

### Backend Components
1. **InferenceEngine** (`backend.inference_engine`)
   - Wrapper for `llama_cpp.Llama`.
   - Manages streaming generation and RAM preset allocations (3GB, 4GB, 6GB+).
2. **RAGPipeline** (`backend.rag_pipeline`)
   - Orchestrates embedding generation, FAISS searching, and Jinja prompt templating.
3. **SM2Scheduler** (`backend.sm2_scheduler`)
   - Pure SM-2 mathematical function (`compute_sm2`).
   - SQLite-backed state management for generating daily review sessions.
4. **SyncLayer** (`backend.sync_layer`)
   - Background threading worker.
   - Pushes unsynced `sync_log` items and pulls remote records.

### Frontend Components (Kivy)
1. **TutorApp** (`frontend.main`)
   - Configures the `ScreenManager` and manages the backend `server_process` lifecycle.
2. **LoginScreen**
   - User profile registration.
3. **DashboardScreen**
   - Main hub displaying streak and progress analytics.
4. **TutorChatScreen**
   - Conversational UI interacting with the `InferenceEngine`.
5. **ReviewScreen**
   - Flashcard interface interacting with the `SM2Scheduler`.
6. **SettingsScreen**
   - Configuration management.

---

## 5. Utilities

1. **SemanticChunker** (`backend.rag_pipeline`)
   - Splits long text documents into fixed-token windows with sentence boundary awareness and defined overlap.
2. **FAISSIndex** (`backend.rag_pipeline`)
   - Manages the `faiss.IndexFlatIP` memory object.
   - Provides inner-product (cosine) similarity search over normalized embeddings.
3. **ConflictResolver** (`backend.sync_layer`)
   - Executes Last-Write-Wins (LWW) logic on conflicting `repetition_records`.
4. **ConnectivityChecker** (`backend.sync_layer`)
   - Lightweight `HEAD` requester to verify internet access before attempting a sync.

---

## 6. External Integrations & Dependencies

- **llama-cpp-python**: Executes the local Phi-3 Mini GGUF model in C++.
- **sentence-transformers**: Generates embeddings using `all-MiniLM-L6-v2`.
- **faiss-cpu**: C++ backend for the vector search index.
- **Kivy / KivyMD**: Python UI framework compiled to Android native views.
- **Buildozer**: Toolchain for compiling the Python app into an Android `.apk`.
- **Flask**: HTTP request handling for the remote sync server.
