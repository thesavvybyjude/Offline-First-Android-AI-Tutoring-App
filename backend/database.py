"""
SQLite Database Schema and Operations for AI Tutoring App
Implements SM2 spaced repetition and offline sync tracking
"""

import sqlite3
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import json


class DatabaseManager:
    """Manages SQLite database for students, knowledge items, and SM2 records"""
    
    def __init__(self, db_path: str = "data/tutor.db"):
        self.db_path = db_path
        self.conn = None
        self._ensure_db_directory()
        self._initialize_database()
    
    def _ensure_db_directory(self):
        """Ensure the data directory exists"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    def connect(self):
        """Establish database connection"""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
        return self.conn
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def _initialize_database(self):
        """Create all database tables and triggers"""
        conn = self.connect()
        cursor = conn.cursor()
        
        # Students table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                grade_level TEXT NOT NULL,
                school_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                synced BOOLEAN DEFAULT 0
            )
        """)
        
        # Knowledge items table (flashcards)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                source_chunk TEXT,
                chunk_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # SM2 repetition records
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS repetition_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL,
                ease_factor REAL DEFAULT 2.5,
                interval_days INTEGER DEFAULT 0,
                repetitions INTEGER DEFAULT 0,
                last_quality INTEGER DEFAULT 0,
                next_review TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_review TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                synced BOOLEAN DEFAULT 0,
                FOREIGN KEY (student_id) REFERENCES students(id),
                FOREIGN KEY (item_id) REFERENCES knowledge_items(id),
                UNIQUE(student_id, item_id)
            )
        """)
        
        # Sync log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER,
                table_name TEXT NOT NULL,
                record_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                success BOOLEAN DEFAULT 1,
                FOREIGN KEY (student_id) REFERENCES students(id)
            )
        """)
        
        # Create indexes for performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_rep_next_review 
            ON repetition_records(next_review)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_rep_student 
            ON repetition_records(student_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_items_subject 
            ON knowledge_items(subject)
        """)
        
        # Create triggers for automatic timestamp updates
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS update_students_timestamp 
            AFTER UPDATE ON students
            BEGIN
                UPDATE students SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END
        """)
        
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS update_items_timestamp 
            AFTER UPDATE ON knowledge_items
            BEGIN
                UPDATE knowledge_items SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END
        """)
        
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS update_rep_timestamp 
            AFTER UPDATE ON repetition_records
            BEGIN
                UPDATE repetition_records SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END
        """)
        
        conn.commit()
    
    # Student operations
    def create_student(self, name: str, grade_level: str, school_id: str = None) -> int:
        """Create a new student record"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO students (name, grade_level, school_id) VALUES (?, ?, ?)",
            (name, grade_level, school_id)
        )
        conn.commit()
        return cursor.lastrowid
    
    def get_student(self, student_id: int) -> Optional[Dict]:
        """Get student by ID"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM students WHERE id = ?", (student_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_all_students(self) -> List[Dict]:
        """Get all students"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM students")
        return [dict(row) for row in cursor.fetchall()]
    
    # Knowledge item operations
    def create_knowledge_item(self, subject: str, question: str, answer: str, 
                             source_chunk: str = None, chunk_id: int = None) -> int:
        """Create a new knowledge item (flashcard)"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO knowledge_items 
               (subject, question, answer, source_chunk, chunk_id) 
               VALUES (?, ?, ?, ?, ?)""",
            (subject, question, answer, source_chunk, chunk_id)
        )
        conn.commit()
        return cursor.lastrowid
    
    def get_knowledge_item(self, item_id: int) -> Optional[Dict]:
        """Get knowledge item by ID"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM knowledge_items WHERE id = ?", (item_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_items_by_subject(self, subject: str) -> List[Dict]:
        """Get all knowledge items for a subject"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM knowledge_items WHERE subject = ?", (subject,))
        return [dict(row) for row in cursor.fetchall()]
    
    # SM2 repetition record operations
    def create_repetition_record(self, student_id: int, item_id: int) -> int:
        """Create a new repetition record with default SM2 values"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO repetition_records 
               (student_id, item_id, ease_factor, interval_days, repetitions, next_review) 
               VALUES (?, ?, 2.5, 0, 0, CURRENT_TIMESTAMP)""",
            (student_id, item_id)
        )
        conn.commit()
        return cursor.lastrowid
    
    def get_repetition_record(self, student_id: int, item_id: int) -> Optional[Dict]:
        """Get repetition record for student-item pair"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM repetition_records WHERE student_id = ? AND item_id = ?",
            (student_id, item_id)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def update_repetition_record(self, student_id: int, item_id: int, quality: int) -> Dict:
        """
        Update repetition record using SM2 algorithm
        Quality: 0-5 (0=complete failure, 5=perfect response)
        """
        record = self.get_repetition_record(student_id, item_id)
        if not record:
            self.create_repetition_record(student_id, item_id)
            record = self.get_repetition_record(student_id, item_id)
        
        # SM2 Algorithm
        ef = record['ease_factor']
        repetitions = record['repetitions']
        interval = record['interval_days']
        
        if quality >= 3:
            # Correct response
            if repetitions == 0:
                interval = 1
            elif repetitions == 1:
                interval = 6
            else:
                interval = int(round(interval * ef))
            
            repetitions += 1
        else:
            # Incorrect response - reset
            repetitions = 0
            interval = 1
        
        # Update ease factor
        ef = ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        if ef < 1.3:
            ef = 1.3
        
        # Calculate next review date
        next_review = datetime.now() + timedelta(days=interval)
        
        # Update record
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(
            """UPDATE repetition_records 
               SET ease_factor = ?, interval_days = ?, repetitions = ?, 
                   last_quality = ?, next_review = ?, last_review = CURRENT_TIMESTAMP,
                   synced = 0
               WHERE student_id = ? AND item_id = ?""",
            (ef, interval, repetitions, quality, next_review, student_id, item_id)
        )
        conn.commit()
        
        # Log sync action
        self._log_sync_action(student_id, 'repetition_records', 
                             self.get_repetition_record(student_id, item_id)['id'], 'UPDATE')
        
        return self.get_repetition_record(student_id, item_id)
    
    def get_due_items(self, student_id: int, limit: int = 20) -> List[Dict]:
        """Get items due for review today"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(
            """SELECT r.*, k.question, k.answer, k.subject 
               FROM repetition_records r
               JOIN knowledge_items k ON r.item_id = k.id
               WHERE r.student_id = ? AND r.next_review <= CURRENT_TIMESTAMP
               ORDER BY r.next_review ASC
               LIMIT ?""",
            (student_id, limit)
        )
        return [dict(row) for row in cursor.fetchall()]
    
    def get_student_stats(self, student_id: int) -> Dict:
        """Get student statistics for dashboard"""
        conn = self.connect()
        cursor = conn.cursor()
        
        # Items due today
        cursor.execute(
            """SELECT COUNT(*) as due_count 
               FROM repetition_records 
               WHERE student_id = ? AND next_review <= CURRENT_TIMESTAMP""",
            (student_id,)
        )
        due_count = cursor.fetchone()['due_count']
        
        # Total items mastered (interval > 21 days)
        cursor.execute(
            """SELECT COUNT(*) as mastered_count 
               FROM repetition_records 
               WHERE student_id = ? AND interval_days > 21""",
            (student_id,)
        )
        mastered_count = cursor.fetchone()['mastered_count']
        
        # Average retention (based on ease factor)
        cursor.execute(
            """SELECT AVG(ease_factor) as avg_ef 
               FROM repetition_records 
               WHERE student_id = ?""",
            (student_id,)
        )
        avg_ef = cursor.fetchone()['avg_ef'] or 2.5
        retention = min(0.99, (avg_ef - 1.3) / 2.5)  # Normalize to 0-1 range
        
        return {
            'due_today': due_count,
            'mastered': mastered_count,
            'retention': round(retention, 2)
        }
    
    # Sync operations
    def get_unsynced_records(self, table_name: str) -> List[Dict]:
        """Get all unsynced records from a table"""
        conn = self.connect()
        cursor = conn.cursor()
        
        if table_name == 'students':
            cursor.execute("SELECT * FROM students WHERE synced = 0")
        elif table_name == 'repetition_records':
            cursor.execute("SELECT * FROM repetition_records WHERE synced = 0")
        else:
            return []
        
        return [dict(row) for row in cursor.fetchall()]
    
    def mark_as_synced(self, table_name: str, record_id: int):
        """Mark a record as synced"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(
            f"UPDATE {table_name} SET synced = 1 WHERE id = ?",
            (record_id,)
        )
        conn.commit()
    
    def _log_sync_action(self, student_id: int, table_name: str, record_id: int, action: str):
        """Log a sync action"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO sync_log (student_id, table_name, record_id, action) 
               VALUES (?, ?, ?, ?)""",
            (student_id, table_name, record_id, action)
        )
        conn.commit()
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
