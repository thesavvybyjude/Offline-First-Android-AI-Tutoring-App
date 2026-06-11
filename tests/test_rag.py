"""
Tests for RAG Pipeline
"""

import pytest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.rag_pipeline import RAGPipeline
from backend.corpus_processor import CorpusProcessor


class TestRAGPipeline:
    """Test cases for RAG pipeline"""
    
    @pytest.fixture
    def sample_chunks(self):
        """Create sample chunks for testing"""
        return [
            {
                'text': 'Photosynthesis is the process by which plants convert sunlight into energy.',
                'chunk_id': 0,
                'source_file': 'biology.txt',
                'subject': 'Biology'
            },
            {
                'text': 'The mitochondria is the powerhouse of the cell.',
                'chunk_id': 1,
                'source_file': 'biology.txt',
                'subject': 'Biology'
            },
            {
                'text': 'Water is composed of two hydrogen atoms and one oxygen atom.',
                'chunk_id': 2,
                'source_file': 'chemistry.txt',
                'subject': 'Chemistry'
            }
        ]
    
    @pytest.fixture
    def rag(self, sample_chunks, tmp_path):
        """Create RAG pipeline instance with test data"""
        import json
        
        # Save sample chunks
        chunks_file = tmp_path / "test_chunks.json"
        with open(chunks_file, 'w') as f:
            json.dump(sample_chunks, f)
        
        rag = RAGPipeline(
            chunks_path=str(chunks_file),
            index_path=str(tmp_path / "test_index.index")
        )
        rag.chunks = sample_chunks
        return rag
    
    def test_load_embedding_model(self, rag):
        """Test loading embedding model"""
        rag.load_embedding_model()
        assert rag.embedding_model is not None
    
    def test_encode_text(self, rag):
        """Test text encoding"""
        rag.load_embedding_model()
        text = "Test text"
        embedding = rag.encode_text(text)
        assert embedding is not None
        assert len(embedding) > 0
    
    def test_build_index(self, rag):
        """Test building FAISS index"""
        rag.load_embedding_model()
        rag.build_index()
        assert rag.index is not None
        assert rag.index.ntotal == len(rag.chunks)
    
    def test_search(self, rag):
        """Test semantic search"""
        rag.load_embedding_model()
        rag.build_index()
        
        query = "What is photosynthesis?"
        results = rag.search(query, top_k=2)
        
        assert len(results) > 0
        assert 'similarity_score' in results[0]
        assert 'text' in results[0]
    
    def test_retrieve_context(self, rag):
        """Test context retrieval"""
        rag.load_embedding_model()
        rag.build_index()
        
        query = "What is photosynthesis?"
        context = rag.retrieve_context(query, max_tokens=100)
        
        assert context is not None
        assert len(context) > 0


class TestCorpusProcessor:
    """Test cases for corpus processor"""
    
    @pytest.fixture
    def processor(self, tmp_path):
        """Create corpus processor instance"""
        return CorpusProcessor(
            corpus_dir=str(tmp_path / "corpus"),
            chunks_dir=str(tmp_path / "chunks")
        )
    
    def test_semantic_chunking(self, processor):
        """Test semantic chunking"""
        text = "This is sentence one. This is sentence two. This is sentence three."
        chunks = processor.semantic_chunking(text, chunk_size=10, overlap=2)
        
        assert len(chunks) > 0
        assert 'text' in chunks[0]
        assert 'token_count' in chunks[0]
    
    def test_infer_subject(self, processor):
        """Test subject inference from filename"""
        assert processor._infer_subject('english_lesson.pdf') == 'English'
        assert processor._infer_subject('biology_chapter.pdf') == 'Biology'
        assert processor._infer_subject('math_test.pdf') == 'Mathematics'
