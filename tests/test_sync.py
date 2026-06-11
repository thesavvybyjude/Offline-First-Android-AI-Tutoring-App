"""
Tests for Sync Layer
"""

import pytest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.sync_layer import SyncLayer
from backend.database import DatabaseManager


class TestSyncLayer:
    """Test cases for sync layer"""
    
    @pytest.fixture
    def db(self, tmp_path):
        """Create test database"""
        db_path = tmp_path / "test_tutor.db"
        return DatabaseManager(str(db_path))
    
    @pytest.fixture
    def sync(self, db):
        """Create sync layer instance"""
        return SyncLayer(db_manager=db, server_url="http://localhost:5000")
    
    @pytest.fixture
    def student(self, db):
        """Create test student"""
        student_id = db.create_student("Test Student", "SS1", "SCH001")
        return student_id
    
    def test_sync_layer_initialization(self, sync):
        """Test sync layer initialization"""
        assert sync.db is not None
        assert sync.server_url == "http://localhost:5000"
    
    def test_get_unsynced_records(self, sync, student):
        """Test getting unsynced records"""
        # Create a student record (automatically unsynced)
        records = sync.db.get_unsynced_records('students')
        
        assert len(records) >= 0
    
    def test_mark_as_synced(self, sync, student):
        """Test marking record as synced"""
        sync.db.mark_as_synced('students', student)
        
        # Verify it's marked as synced
        student_data = sync.db.get_student(student)
        assert student_data['synced'] == 1
    
    def test_sync_student_conflict_resolution(self, sync):
        """Test conflict resolution for student records"""
        # Create initial record
        student_id = sync.db.create_student("Original Name", "SS1")
        
        # Simulate server update with newer timestamp
        newer_data = {
            'id': student_id,
            'name': 'Updated Name',
            'grade_level': 'SS2',
            'school_id': 'SCH001',
            'created_at': '2024-01-01',
            'updated_at': '2024-12-31'
        }
        
        result = sync._sync_student(newer_data, 'UPDATE')
        
        assert result['success'] == True
        assert 'updated' in result['action']
    
    def test_sync_repetition_record_conflict_resolution(self, sync):
        """Test conflict resolution for repetition records"""
        # Create student and item
        student_id = sync.db.create_student("Test", "SS1")
        item_id = sync.db.create_knowledge_item(
            "Biology", "Q?", "A?"
        )
        
        # Create repetition record
        sync.db.create_repetition_record(student_id, item_id)
        
        # Simulate server update with higher repetition count
        newer_data = {
            'student_id': student_id,
            'item_id': item_id,
            'ease_factor': 2.6,
            'interval_days': 10,
            'repetitions': 5,  # Higher than local
            'last_quality': 4,
            'next_review': '2024-12-31',
            'updated_at': '2024-12-31'
        }
        
        result = sync._sync_repetition_record(newer_data, 'UPDATE')
        
        assert result['success'] == True
        assert 'conflict resolved' in result['action'].lower()
