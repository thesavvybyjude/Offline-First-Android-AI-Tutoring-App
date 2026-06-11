"""
RAG Pipeline Module
Implements semantic search using FAISS and sentence-transformers
"""

import os
import json
import numpy as np
from typing import List, Dict, Tuple, Optional
from sentence_transformers import SentenceTransformer
import faiss
from tqdm import tqdm


class RAGPipeline:
    """Retrieval-Augmented Generation pipeline with FAISS index"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2",
                 index_path: str = "data/faiss_index.index",
                 chunks_path: str = "data/chunks/all_chunks.json"):
        self.model_name = model_name
        self.index_path = index_path
        self.chunks_path = chunks_path
        self.embedding_model = None
        self.index = None
        self.chunks = []
        self.embeddings = None
        
    def load_embedding_model(self):
        """Load the sentence transformer model"""
        print(f"Loading embedding model: {self.model_name}")
        self.embedding_model = SentenceTransformer(self.model_name)
        print("Model loaded successfully")
    
    def encode_text(self, text: str) -> np.ndarray:
        """Encode text to embedding vector"""
        if self.embedding_model is None:
            self.load_embedding_model()
        return self.embedding_model.encode(text, convert_to_numpy=True)
    
    def encode_batch(self, texts: List[str]) -> np.ndarray:
        """Encode batch of texts to embedding vectors"""
        if self.embedding_model is None:
            self.load_embedding_model()
        return self.embedding_model.encode(texts, convert_to_numpy=True)
    
    def load_chunks(self) -> List[Dict]:
        """Load chunks from JSON file"""
        if not os.path.exists(self.chunks_path):
            raise FileNotFoundError(f"Chunks file not found: {self.chunks_path}")
        
        with open(self.chunks_path, 'r', encoding='utf-8') as f:
            self.chunks = json.load(f)
        
        print(f"Loaded {len(self.chunks)} chunks")
        return self.chunks
    
    def build_index(self, chunks: List[Dict] = None):
        """
        Build FAISS index from chunks
        Uses FlatIP (inner product) for cosine similarity
        """
        if chunks is not None:
            self.chunks = chunks
        
        if not self.chunks:
            raise ValueError("No chunks available. Load chunks first.")
        
        print("Encoding chunks...")
        texts = [chunk['text'] for chunk in self.chunks]
        self.embeddings = self.encode_batch(texts)
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(self.embeddings)
        
        # Create FAISS index (Inner Product = Cosine Similarity for normalized vectors)
        dimension = self.embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dimension)
        self.index.add(self.embeddings.astype('float32'))
        
        print(f"Index built with {self.index.ntotal} vectors")
        
        # Save index
        self.save_index()
    
    def save_index(self):
        """Save FAISS index to disk"""
        faiss.write_index(self.index, self.index_path)
        print(f"Index saved to {self.index_path}")
    
    def load_index(self):
        """Load FAISS index from disk"""
        if not os.path.exists(self.index_path):
            raise FileNotFoundError(f"Index file not found: {self.index_path}")
        
        self.index = faiss.read_index(self.index_path)
        print(f"Index loaded from {self.index_path}")
        print(f"Index contains {self.index.ntotal} vectors")
        
        # Load chunks if not already loaded
        if not self.chunks:
            self.load_chunks()
    
    def search(self, query: str, top_k: int = 3, 
               threshold: float = 0.45) -> List[Dict]:
        """
        Search for relevant chunks using semantic similarity
        Returns chunks with similarity scores above threshold
        """
        if self.index is None:
            self.load_index()
        
        # Encode query
        query_embedding = self.encode_text(query)
        query_embedding = query_embedding.reshape(1, -1)
        
        # Normalize for cosine similarity
        faiss.normalize_L2(query_embedding)
        
        # Search
        scores, indices = self.index.search(query_embedding.astype('float32'), top_k)
        
        # Filter by threshold and format results
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if score >= threshold and idx < len(self.chunks):
                chunk = self.chunks[idx].copy()
                chunk['similarity_score'] = float(score)
                results.append(chunk)
        
        return results
    
    def retrieve_context(self, query: str, max_tokens: int = 1024) -> str:
        """
        Retrieve context for prompt injection
        Combines top chunks until max_tokens is reached
        """
        results = self.search(query, top_k=5, threshold=0.45)
        
        context_parts = []
        total_tokens = 0
        
        for result in results:
            chunk_text = result['text']
            chunk_tokens = len(chunk_text.split())
            
            if total_tokens + chunk_tokens <= max_tokens:
                context_parts.append(f"[Source: {result['source_file']}]\n{chunk_text}")
                total_tokens += chunk_tokens
            else:
                break
        
        return "\n\n".join(context_parts)


if __name__ == "__main__":
    # Example usage
    rag = RAGPipeline()
    
    # Load chunks
    rag.load_chunks()
    
    # Build index
    rag.build_index()
    
    # Test search
    query = "What is photosynthesis?"
    results = rag.search(query, top_k=3)
    
    print(f"\nQuery: {query}")
    print(f"Found {len(results)} relevant chunks:")
    for i, result in enumerate(results, 1):
        print(f"\n{i}. Score: {result['similarity_score']:.4f}")
        print(f"   Subject: {result['subject']}")
        print(f"   Text: {result['text'][:200]}...")
