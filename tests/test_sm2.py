"""
Tests for SM2 Scheduler
"""

import pytest
import sys
import os
from datetime import datetime, timedelta
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.sm2_scheduler import SM2Scheduler
from backend.database import DatabaseManager


class TestSM2Scheduler:
    """Test cases for SM2 algorithm"""
    
    @pytest.fixture
    def db(self, tmp_path):
        """Create test database"""
        db_path = tmp_path / "test_tutor.db"
        return DatabaseManager(str(db_path))
    
    @pytest.fixture
    def scheduler(self, db):
        """Create scheduler instance"""
        return SM2Scheduler(db)
    
    @pytest.fixture
    def student(self, db):
        """Create test student"""
        student_id = db.create_student("Test Student", "SS1", "SCH001")
        return student_id
    
    @pytest.fixture
    def knowledge_item(self, db):
        """Create test knowledge item"""
        item_id = db.create_knowledge_item(
            subject="Biology",
            question="What is photosynthesis?",
            answer="The process by which plants convert sunlight into energy."
        )
        return item_id
    
    def test_calculate_next_review_correct_response(self, scheduler):
        """Test SM2 calculation for correct response (quality >= 3)"""
        params = scheduler.calculate_next_review(
            quality=4,
            ease_factor=2.5,
            interval=1,
            repetitions=0
        )
        
        assert params['ease_factor'] > 2.5  # EF should increase
        assert params['interval_days'] == 1  # First repetition
        assert params['repetitions'] == 1
        assert params['last_quality'] == 4
    
    def test_calculate_next_review_incorrect_response(self, scheduler):
        """Test SM2 calculation for incorrect response (quality < 3)"""
        params = scheduler.calculate_next_review(
            quality=2,
            ease_factor=2.5,
            interval=6,
            repetitions=2
        )
        
        assert params['interval_days'] == 1  # Reset to day 1
        assert params['repetitions'] == 0  # Reset repetitions
    
    def test_calculate_next_review_second_repetition(self, scheduler):
        """Test SM2 calculation for second repetition"""
        params = scheduler.calculate_next_review(
            quality=4,
            ease_factor=2.5,
            interval=1,
            repetitions=1
        )
        
        assert params['interval_days'] == 6  # Second repetition = 6 days
        assert params['repetitions'] == 2
    
    def test_calculate_next_review_ef_minimum(self, scheduler):
        """Test that ease factor doesn't go below 1.3"""
        params = scheduler.calculate_next_review(
            quality=0,  # Very poor response
            ease_factor=1.4,
            interval=1,
            repetitions=0
        )
        
        assert params['ease_factor'] >= 1.3
    
    def test_schedule_review_new_record(self, scheduler, student, knowledge_item):
        """Test scheduling review for new record"""
        params = scheduler.schedule_review(student, knowledge_item, quality=4)
        
        assert params['repetitions'] == 1
        assert params['interval_days'] == 1
    
    def test_schedule_review_existing_record(self, scheduler, student, knowledge_item):
        """Test scheduling review for existing record"""
        # First review
        scheduler.schedule_review(student, knowledge_item, quality=4)
        
        # Second review
        params = scheduler.schedule_review(student, knowledge_item, quality=5)
        
        assert params['repetitions'] == 2
        assert params['interval_days'] == 6
    
    def test_get_due_items(self, scheduler, student, knowledge_item):
        """Test getting due items"""
        # Create record with next_review in the past
        scheduler.db.create_repetition_record(student, knowledge_item)
        
        due_items = scheduler.get_due_items(student)
        
        assert len(due_items) > 0
        assert due_items[0]['item_id'] == knowledge_item
    
    def test_get_student_stats(self, scheduler, student):
        """Test getting student statistics"""
        stats = scheduler.db.get_student_stats(student)
        
        assert 'due_today' in stats
        assert 'mastered' in stats
        assert 'retention' in stats
