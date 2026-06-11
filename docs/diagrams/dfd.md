# Data Flow Diagrams (DFD) - AI Tutor App

## DFD Level 0 (Context Diagram)

```
                    ┌─────────────┐
                    │   Student   │
                    └──────┬──────┘
                           │
                           │ 1. Query/Review
                           │
                    ┌──────▼──────┐
                    │  AI Tutor    │
                    │    App       │
                    └──────┬──────┘
                           │
                           │ 2. Sync Data
                           │
                    ┌──────▼──────┐
                    │   Server     │
                    └─────────────┘
```

**External Entities:**
- **Student**: Primary user who interacts with the app
- **Server**: Remote server for data synchronization

**Data Flows:**
1. Student submits queries, reviews flashcards, views progress
2. App syncs data with server when online

---

## DFD Level 1 (Decomposition)

```
┌─────────────────────────────────────────────────────────────┐
│                        Student                               │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           │ Query/Review
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                      AI Tutor App                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   UI Layer   │    │  Business    │    │   Data Layer │  │
│  │              │    │    Logic     │    │              │  │
│  │ - Screens    │───▶│              │───▶│              │  │
│  │ - Widgets    │    │ - RAG        │    │ - SQLite     │  │
│  │ - Navigation │    │ - SM2        │    │ - FAISS      │  │
│  └──────────────┘    │ - Sync       │    │ - Models     │  │
│                     └──────────────┘    └──────────────┘  │
│                                                             │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           │ Sync Data
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                      Sync Server                            │
├─────────────────────────────────────────────────────────────┤
│  - REST API (/sync/push, /sync/pull)                        │
│  - Conflict Resolution                                       │
│  - Database (PostgreSQL/MySQL)                              │
└─────────────────────────────────────────────────────────────┘
```

---

## DFD Level 2 (RAG Subsystem Detail)

```
┌─────────────────────────────────────────────────────────────┐
│                      Student Query                          │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           │ Query Text
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                   RAG Pipeline                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐                                          │
│  │   Query      │                                          │
│  └──────┬───────┘                                          │
│         │                                                  │
│         │ Encode                                           │
│         │                                                  │
│  ┌──────▼───────┐    ┌──────────────┐    ┌──────────────┐ │
│  │ Embedding    │───▶│  FAISS Index │───▶│ Top-K Chunks │ │
│  │ Model        │    │ (Cosine Sim) │    │ (Threshold)   │ │
│  │ (MiniLM-L6)  │    └──────────────┘    └──────┬───────┘ │
│  └──────────────┘                                  │         │
│                                                     │         │
│                                                     │ Context │
│                                                     │         │
│  ┌──────────────┐                            ┌──────▼───────┐ │
│  │  Prompt      │◀───────────────────────────│ Context      │ │
│  │  Template    │                            │ Assembly     │ │
│  │  (Jinja2)    │                            └──────────────┘ │
│  └──────┬───────┘                                          │
│         │                                                  │
│         │ Prompt + Context                                 │
│         │                                                  │
│  ┌──────▼───────┐                                          │
│  │   LLM        │                                          │
│  │ (Phi-3 Mini) │                                          │
│  └──────┬───────┘                                          │
│         │                                                  │
│         │ Response                                         │
│         │                                                  │
└─────────┼──────────────────────────────────────────────────┘
          │
          │ Response + Sources
          │
┌─────────▼──────────────────────────────────────────────────┐
│                      Student                                │
└─────────────────────────────────────────────────────────────┘
```

---

## DFD Level 2 (SM2 Subsystem Detail)

```
┌─────────────────────────────────────────────────────────────┐
│                   Student Review                            │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           │ Quality Rating (1-5)
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                   SM2 Scheduler                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │  Current     │───▶│  SM2         │───▶│  Updated     │  │
│  │  Parameters  │    │  Algorithm   │    │  Parameters  │  │
│  │              │    │              │    │              │  │
│  │ - EF         │    │ - EF Update  │    │ - New EF     │  │
│  │ - Interval   │    │ - Interval   │    │ - New Int.   │  │
│  │ - Reps       │    │ - Reps Reset │    │ - New Reps   │  │
│  └──────────────┘    └──────────────┘    └──────┬───────┘  │
│                                                 │          │
│                                                 │ Update   │
│                                                 │          │
│  ┌──────────────┐                            ┌──────▼───────┐ │
│  │  SQLite      │◀──────────────────────────│  Database    │ │
│  │  Database    │                            │  Write       │ │
│  └──────────────┘                            └──────────────┘ │
│                                                             │
│  ┌──────────────┐                                          │
│  │  Sync Flag   │                                          │
│  │  (synced=0)  │                                          │
│  └──────────────┘                                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## DFD Level 2 (Sync Subsystem Detail)

```
┌─────────────────────────────────────────────────────────────┐
│                   Offline Device                            │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           │ Unsynced Changes
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                   Sync Layer                                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │  Query       │───▶│  Delta       │───▶│  JSON        │  │
│  │  Unsynced    │    │  Builder     │    │  Payload     │  │
│  │  Records     │    │              │    │              │  │
│  └──────────────┘    └──────────────┘    └──────┬───────┘  │
│                                                 │          │
│                                                 │ POST    │
│                                                 │          │
│  ┌──────────────┐                            ┌──────▼───────┐ │
│  │  HTTP        │───▶│  Server      │                            │
│  │  Client      │    │  Endpoint    │    │  Conflict    │  │
│  │  (requests)  │    │  /sync/push  │    │  Resolution  │  │
│  └──────────────┘    └──────────────┘    └──────┬───────┘  │
│                                                 │          │
│                                                 │ Success  │
│                                                 │          │
│  ┌──────────────┐                            ┌──────▼───────┐ │
│  │  Mark        │◀──────────────────────────│  Response   │ │
│  │  Synced      │                            │  Handler    │ │
│  └──────────────┘                            └──────────────┘ │
│                                                             │
│  ┌──────────────┐                                          │
│  │  Log to      │                                          │
│  │  sync_log    │                                          │
│  └──────────────┘                                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Data Dictionary

### Data Stores
- **D1: SQLite Database** (Local)
  - students, knowledge_items, repetition_records, sync_log
- **D2: FAISS Index** (Local)
  - Vector embeddings for semantic search
- **D3: Server Database** (Remote)
  - Centralized student data and progress

### Data Flows
- **F1: Student Query** - Text input from student
- **F2: Context** - Retrieved knowledge chunks
- **F3: Response** - AI-generated answer
- **F4: Quality Rating** - Student's self-assessment (1-5)
- **F5: Delta Payload** - JSON with unsynced changes
- **F6: Sync Response** - Server acknowledgment
