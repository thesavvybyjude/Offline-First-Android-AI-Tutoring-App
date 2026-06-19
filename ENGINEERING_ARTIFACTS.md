# Engineering Artifacts

This document contains additional architectural models generated during the documentation audit to fully map system behavior.

---

## 1. Class Diagrams

### AI & Synchronization Core (UML)
```mermaid
classDiagram
    class InferenceEngine {
        +Path model_path
        -Llama _llm
        -Lock _lock
        +load(ram_gb: float)
        +generate(prompt: str) GenerationResult
        +generate_stream(prompt: str) Iterator
    }
    
    class RAGPipeline {
        +Path data_dir
        -FAISSIndex faiss_index
        -SentenceTransformer embedder
        +load()
        +ingest_documents(docs: list)
        +retrieve(query: str) RetrievalResult
        +build_prompt(query: str) PromptPackage
    }

    class SM2Scheduler {
        +str db_path
        +submit_review(student_id: str, item_id: str, quality: int)
        +get_due_items(student_id: str) list
        -_calculate_sm2(quality, repetitions, ease_factor, interval)
    }

    class SyncLayer {
        +str server_url
        +ConflictResolver resolver
        +start_background_sync()
        -_push_deltas()
        -_pull_updates()
    }
```

---

## 2. Sequence Diagrams

### Flashcard Review Flow
```mermaid
sequenceDiagram
    actor Student
    participant UI as ReviewScreen
    participant SM2 as SM2Scheduler
    participant DB as SQLite (Edge)
    participant Sync as SyncLayer

    Student->>UI: Rates flashcard (e.g., 4)
    UI->>SM2: submit_review(student_id, item_id, 4)
    SM2->>SM2: _calculate_sm2()
    SM2->>DB: UPDATE repetition_records (ease_factor, interval, synced=0)
    DB-->>SM2: Trigger logs to sync_log
    SM2-->>UI: Review recorded
    UI-->>Student: Shows next flashcard
    
    Sync->>Sync: Background tick
    Sync->>DB: SELECT * FROM sync_log
    DB-->>Sync: Returns dirty records
    Sync->>Sync: Initiates push to server
```

---

## 3. State Diagrams

### Flashcard Lifecycle
```mermaid
stateDiagram-v2
    [*] --> New
    New --> Learning : First Review
    Learning --> Reviewing : Quality >= 3 (Graduated)
    Reviewing --> Reviewing : Quality >= 3 (Interval Increases)
    Reviewing --> Lapsed : Quality < 3 (Failed)
    Lapsed --> Learning : Re-learning
```

### User Session Lifecycle
```mermaid
stateDiagram-v2
    [*] --> Disconnected
    Disconnected --> Connecting : App Boot
    Connecting --> Online : Server /health returns 200 OK
    Connecting --> OfflineMode : Request Timeout
    Online --> Syncing : sync_log has rows
    Syncing --> Online : Push/Pull Success
    Syncing --> OfflineMode : Connection Dropped
```

---

## 4. Navigation Diagram

### Application Screen Map
```mermaid
graph TD
    Login[LoginScreen] -->|Valid Auth| Dashboard[DashboardScreen]
    
    Dashboard --> Chat[TutorChatScreen]
    Dashboard --> Review[ReviewScreen]
    Dashboard --> Settings[SettingsScreen]
    
    Chat -->|Back| Dashboard
    Review -->|Back| Dashboard
    Settings -->|Back| Dashboard
```
