# Entity Relationship Diagram (ERD) - AI Tutor Database

## Tables

### STUDENTS
```
┌─────────────────────────────────────────┐
│ STUDENTS                                │
├─────────────────────────────────────────┤
│ PK id           INTEGER                 │
│    name         TEXT NOT NULL           │
│    grade_level  TEXT NOT NULL           │
│    school_id    TEXT                    │
│    created_at   TIMESTAMP               │
│    updated_at   TIMESTAMP               │
│    synced       BOOLEAN DEFAULT 0       │
└─────────────────────────────────────────┘
```

### KNOWLEDGE_ITEMS
```
┌─────────────────────────────────────────┐
│ KNOWLEDGE_ITEMS                         │
├─────────────────────────────────────────┤
│ PK id           INTEGER                 │
│    subject      TEXT NOT NULL           │
│    question     TEXT NOT NULL           │
│    answer       TEXT NOT NULL           │
│    source_chunk TEXT                    │
│    chunk_id     INTEGER                 │
│    created_at   TIMESTAMP               │
│    updated_at   TIMESTAMP               │
└─────────────────────────────────────────┘
```

### REPETITION_RECORDS
```
┌─────────────────────────────────────────┐
│ REPETITION_RECORDS                      │
├─────────────────────────────────────────┤
│ PK id               INTEGER             │
│ FK student_id       INTEGER             │
│ FK item_id          INTEGER             │
│    ease_factor      REAL DEFAULT 2.5   │
│    interval_days    INTEGER DEFAULT 0   │
│    repetitions      INTEGER DEFAULT 0   │
│    last_quality     INTEGER DEFAULT 0   │
│    next_review      TIMESTAMP           │
│    last_review      TIMESTAMP           │
│    updated_at       TIMESTAMP           │
│    synced           BOOLEAN DEFAULT 0   │
│                    │                    │
│ UNIQUE (student_id, item_id)           │
└─────────────────────────────────────────┘
```

### SYNC_LOG
```
┌─────────────────────────────────────────┐
│ SYNC_LOG                                │
├─────────────────────────────────────────┤
│ PK id           INTEGER                 │
│ FK student_id   INTEGER                 │
│    table_name   TEXT NOT NULL           │
│    record_id    INTEGER NOT NULL        │
│    action       TEXT NOT NULL           │
│    synced_at    TIMESTAMP               │
│    success      BOOLEAN DEFAULT 1       │
└─────────────────────────────────────────┘
```

## Relationships

### Foreign Keys
- **REPETITION_RECORDS.student_id** → **STUDENTS.id**
- **REPETITION_RECORDS.item_id** → **KNOWLEDGE_ITEMS.id**
- **SYNC_LOG.student_id** → **STUDENTS.id**

### Cardinality
- **STUDENTS** (1) ─────< (N) **REPETITION_RECORDS**
  - One student can have many repetition records
  - Each repetition record belongs to one student

- **KNOWLEDGE_ITEMS** (1) ─────< (N) **REPETITION_RECORDS**
  - One knowledge item can have many repetition records (for different students)
  - Each repetition record belongs to one knowledge item

- **STUDENTS** (1) ─────< (N) **SYNC_LOG**
  - One student can have many sync log entries
  - Each sync log entry belongs to one student (optional)

### Constraints
- **UNIQUE constraint** on (student_id, item_id) in REPETITION_RECORDS
  - Ensures each student has at most one repetition record per knowledge item

### Indexes
```
CREATE INDEX idx_rep_next_review ON repetition_records(next_review);
CREATE INDEX idx_rep_student ON repetition_records(student_id);
CREATE INDEX idx_items_subject ON knowledge_items(subject);
```

## Triggers
```
TRIGGER: update_students_timestamp
AFTER UPDATE ON students
BEGIN
    UPDATE students SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

TRIGGER: update_items_timestamp
AFTER UPDATE ON knowledge_items
BEGIN
    UPDATE knowledge_items SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

TRIGGER: update_rep_timestamp
AFTER UPDATE ON repetition_records
BEGIN
    UPDATE repetition_records SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
```

## Data Flow

### SM2 Algorithm Flow
1. Student reviews flashcard → quality rating (0-5)
2. Update REPETITION_RECORDS:
   - Calculate new ease_factor
   - Calculate new interval_days
   - Increment repetitions (if quality ≥ 3)
   - Set next_review date
   - Set synced = FALSE
3. If online: SyncLayer pushes change to server

### Sync Flow
1. SyncLayer queries REPETITION_RECORDS WHERE synced = FALSE
2. Prepare delta payload (JSON)
3. POST to server /sync/push
4. Server applies changes with conflict resolution
5. Mark local records as synced = TRUE
6. Log action to SYNC_LOG
