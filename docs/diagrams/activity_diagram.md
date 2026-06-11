# Activity Diagram - Query Flow

## Student Query Activity Diagram

```
[Start]
  |
  v
[Student enters question]
  |
  v
[App checks offline mode?]
  |
  +-- Yes --> [Load local RAG pipeline]
  |            |
  |            v
  |        [Encode query with embedding model]
  |            |
  |            v
  |        [Search FAISS index (top-3)]
  |            |
  |            v
  |        [Filter by similarity threshold (≥0.45)]
  |            |
  |            v
  |        [Retrieve context chunks]
  |            |
  |            v
  |        [Build prompt with Jinja2 template]
  |            |
  |            v
  |        [Generate response with Phi-3 Mini]
  |            |
  |            v
  |        [Stream tokens to UI]
  |            |
  |            v
  |        [Display response + source chips]
  |
  +-- No --> [Check internet connection]
               |
               +-- Available --> [Sync with server first]
               |                   |
               |                   v
               |               [Proceed with local RAG]
               |
               +-- Unavailable --> [Show offline warning]
                                   |
                                   v
                               [Proceed with local RAG]
  |
  v
[Student satisfied?]
  |
  +-- Yes --> [Optional: Create flashcard from Q&A]
  |            |
  |            v
  |        [Add to knowledge base]
  |
  +-- No --> [Student may ask follow-up]
  |
  v
[End]
```

## Flashcard Review Activity Diagram

```
[Start]
  |
  v
[Student clicks "Start Review"]
  |
  v
[Load SM2 scheduler]
  |
  v
[Get due items (WHERE next_review ≤ today)]
  |
  v
[Items available?]
  |
  +-- No --> [Display "No cards due"]
  |            |
  |            v
  |        [Return to dashboard]
  |
  +-- Yes --> [Show first card (question)]
  |
  v
[Student clicks "Show Answer"]
  |
  v
[Reveal answer with animation]
  |
  v
[Display rating buttons (1-5)]
  |
  v
[Student rates quality]
  |
  v
[Calculate SM2 parameters]
  |
  v
[Update ease factor]
  |
  v
[Calculate interval]
  |
  v
[Set next_review date]
  |
  v
[Update repetition record in SQLite]
  |
  v
[Mark record as unsynced]
  |
  v
[More cards in queue?]
  |
  +-- Yes --> [Show next card]
  |
  +-- No --> [Display review summary]
               |
               v
           [If online: Sync changes]
               |
               v
           [Return to dashboard]
  |
  v
[End]
```

## Sync Activity Diagram

```
[Start]
  |
  v
[ConnectivityManager detects internet]
  |
  v
[Trigger sync worker]
  |
  v
[Get unsynced records from SQLite]
  |
  v
[Records found?]
  |
  +-- No --> [Nothing to sync]
  |            |
  |            v
  |        [End]
  |
  +-- Yes --> [Prepare delta payload (JSON)]
  |
  v
[POST to /sync/push endpoint]
  |
  v
[Server processes changes]
  |
  v
[Conflict resolution applied]
  |
  v
[Server returns success]
  |
  v
[Mark local records as synced]
  |
  v
[GET from /sync/pull endpoint]
  |
  v
[Receive remote changes]
  |
  v
[Process incoming changes]
  |
  v
[Apply conflict resolution]
  |
  v
[Update local database]
  |
  v
[Log sync action to sync_log]
  |
  v
[End]
```
