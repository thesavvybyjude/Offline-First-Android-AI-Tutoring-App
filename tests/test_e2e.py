"""
End-to-End Tests
Tests complete workflows from query to response to SM2 update
"""

import pytest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import DatabaseManager
from backend.rag_pipeline import RAGPipeline
from backend.inference_engine import InferenceEngine
from backend.sm2_scheduler import SM2Scheduler
from backend.corpus_processor import CorpusProcessor


class TestEndToEnd:
    """End-to-end test cases"""
    
    @pytest.fixture
    def db(self, tmp_path):
        """Create test database"""
        db_path = tmp_path / "test_tutor.db"
        return DatabaseManager(str(db_path))
    
    @pytest.fixture
    def sample_chunks(self, tmp_path):
        """Create sample chunks"""
        import json
        chunks = [
            {
                'text': 'Photosynthesis is the process by which plants convert sunlight, water, and carbon dioxide into glucose and oxygen.',
                'chunk_id': 0,
                'source_file': 'biology.txt',
                'subject': 'Biology'
            },
            {
                'text': 'The equation for photosynthesis is 6CO2 + 6H2O + light energy → C6H12O6 + 6O2.',
                'chunk_id': 1,
                'source_file': 'biology.txt',
                'subject': 'Biology'
            }
        ]
        
        chunks_file = tmp_path / "test_chunks.json"
        with open(chunks_file, 'w') as f:
            json.dump(chunks, f)
        
        return chunks
    
    @pytest.fixture
    def rag(self, sample_chunks, tmp_path):
        """Create RAG pipeline"""
        rag = RAGPipeline(
            chunks_path=str(tmp_path / "test_chunks.json"),
            index_path=str(tmp_path / "test_index.index")
        )
        rag.chunks = sample_chunks
        rag.load_embedding_model()
        rag.build_index()
        return rag
    
    def test_query_to_retrieval_flow(self, rag):
        """Test complete query to retrieval flow"""
        query = "What is photosynthesis?"
        
        # Retrieve context
        context = rag.retrieve_context(query, max_tokens=100)
        
        assert context is not None
        assert len(context) > 0
        assert 'photosynthesis' in context.lower()
    
    def test_student_creation_to_review_flow(self, db):
        """Test complete student creation to review flow"""
        # Create student
        student_id = db.create_student("Test Student", "SS1", "SCH001")
        
        # Create knowledge item
        item_id = db.create_knowledge_item(
            subject="Biology",
            question="What is photosynthesis?",
            answer="The process by which plants convert sunlight into energy."
        )
        
        # Create repetition record
        db.create_repetition_record(student_id, item_id)
        
        # Get due items
        due_items = db.get_due_items(student_id)
        
        assert len(due_items) == 1
        assert due_items[0]['item_id'] == item_id
    
    def test_sm2_update_flow(self, db):
        """Test complete SM2 update flow"""
        # Setup
        student_id = db.create_student("Test", "SS1")
        item_id = db.create_knowledge_item("Biology", "Q?", "A?")
        db.create_repetition_record(student_id, item_id)
        
        # Update with quality 4
        scheduler = SM2Scheduler(db)
        params = scheduler.schedule_review(student_id, item_id, quality=4)
        
        assert params['repetitions'] == 1
        assert params['interval_days'] == 1
        
        # Update again with quality 5
        params = scheduler.schedule_review(student_id, item_id, quality=5)
        
        assert params['repetitions'] == 2
        assert params['interval_days'] == 6
    
    def test_offline_mode_simulation(self, db, rag):
        """Test offline mode simulation"""
        # Create student and items without internet
        student_id = db.create_student("Offline Student", "SS1")
        
        # Query should work offline
        query = "What is photosynthesis?"
        results = rag.search(query, top_k=1)
        
        assert len(results) > 0
        
        # SM2 should work offline
        item_id = db.create_knowledge_item("Biology", "Q?", "A?")
        db.create_repetition_record(student_id, item_id)
        
        due_items = db.get_due_items(student_id)
        assert len(due_items) == 1
    
    def test_flashcard_seeding_flow(self, db, sample_chunks, tmp_path):
        """Test flashcard seeding from chunks"""
        # This test would require inference engine, which needs the model
        # For now, we'll test the database part
        
        # Create knowledge items manually (simulating LLM generation)
        for chunk in sample_chunks:
            db.create_knowledge_item(
                subject=chunk['subject'],
                question=f"Question about {chunk['subject']}",
                answer="Sample answer",
                source_chunk=chunk['text'],
                chunk_id=chunk['chunk_id']
            )
        
        # Verify items were created
        items = db.get_items_by_subject('Biology')
        assert len(items) == 2
