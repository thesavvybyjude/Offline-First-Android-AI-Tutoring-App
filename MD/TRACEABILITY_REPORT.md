# Traceability Report

This document maps all major features described in the project documentation back to their exact location in the source code.

| Feature | File | Class | Function | Evidence |
| ------- | ---- | ----- | -------- | -------- |
| Local LLM Inference | `backend/inference_engine.py` | `InferenceEngine` | `generate()`, `generate_stream()` | Wrapper over `llama_cpp.Llama` is directly implemented and functional. |
| Hardware RAM Presets | `backend/inference_engine.py` | `InferenceEngine` | `_select_preset()` | `RAM_PRESETS` dictionary allocates context and threads based on RAM config. |
| Vector Embedding | `backend/rag_pipeline.py` | `RAGPipeline` | `ingest_documents()` | `SentenceTransformer` initialized and used to create embeddings. |
| Semantic Chunking | `backend/rag_pipeline.py` | `SemanticChunker` | `chunk_text()` | Text is split into overlapping chunks, tracking tokens. |
| FAISS Search | `backend/rag_pipeline.py` | `FAISSIndex` | `search()` | `IndexFlatIP` used for L2-normalized inner-product cosine similarity. |
| Prompt Construction | `backend/rag_pipeline.py` | `RAGPipeline` | `build_prompt()` | Jinja template (`PROMPT_TEMPLATE`) is injected with chunked context. |
| SM2 Scheduling Math | `backend/sm2_scheduler.py` | `SM2Scheduler` | `_calculate_sm2()` | Standard SM-2 algorithm modifying interval and ease factor. |
| Local DB Schema | `backend/sm2_scheduler.py` | `SM2Scheduler` | `_init_db()` | SQLite tables `students`, `knowledge_items`, `repetition_records`, `sync_log`. |
| Dirty Sync Tracking | `backend/sm2_scheduler.py` | `SM2Scheduler` | `_init_db()` | Triggers in SQLite `repetition_records_update_trg` log dirty rows to `sync_log`. |
| Background Syncing | `backend/sync_layer.py` | `SyncLayer` | `_sync_loop()` | Daemon thread loops checking for connectivity and pushing `sync_log`. |
| Conflict Resolution | `backend/sync_layer.py` | `ConflictResolver` | `resolve()` | Last-Write-Wins based on `updated_at` or `repetitions` count. |
| REST API Routes | `backend/server.py` | N/A | `/health`, `/query`, `/api/v1/sync/*` | Flask server exposes these exact routes for sync and fallback inference. |
| Kivy UI Lifecycle | `frontend/main.py` | `TutorApp` | `build()`, `on_start()` | Instantiates Kivy ScreenManager and manages the backend subprocess. |
| Chat Interface | `frontend/screens/tutor_chat_screen.py`| `TutorChatScreen` | `send_message()` | Connects UI interactions to `RAGPipeline` and `InferenceEngine`. |
| Flashcard UI | `frontend/screens/review_screen.py` | `ReviewScreen` | `submit_rating()` | Submits 0-5 quality score to `SM2Scheduler.submit_review()`. |
| Automated Testing | `tests/test_all.py` | N/A | `test_rag_pipeline()`, etc. | Uses pytest and mocked objects to cover core logic pathways. |
