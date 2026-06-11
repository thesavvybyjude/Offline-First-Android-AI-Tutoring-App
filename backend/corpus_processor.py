"""
Corpus Processing Module
Extracts text from PDFs and performs semantic chunking for RAG pipeline
"""

import os
import re
from typing import List, Dict, Tuple
from pathlib import Path
import fitz  # PyMuPDF
import pdfplumber
from tqdm import tqdm


class CorpusProcessor:
    """Processes PDF corpus for the RAG pipeline"""
    
    def __init__(self, corpus_dir: str = "data/corpus", chunks_dir: str = "data/chunks"):
        self.corpus_dir = corpus_dir
        self.chunks_dir = chunks_dir
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure required directories exist"""
        os.makedirs(self.corpus_dir, exist_ok=True)
        os.makedirs(self.chunks_dir, exist_ok=True)
    
    def extract_text_from_pdf(self, pdf_path: str, method: str = "pymupdf") -> str:
        """
        Extract text from PDF file
        method: 'pymupdf' (faster) or 'pdfplumber' (better for tables)
        """
        if method == "pymupdf":
            return self._extract_with_pymupdf(pdf_path)
        else:
            return self._extract_with_pdfplumber(pdf_path)
    
    def _extract_with_pymupdf(self, pdf_path: str) -> str:
        """Extract text using PyMuPDF (fitz)"""
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    
    def _extract_with_pdfplumber(self, pdf_path: str) -> str:
        """Extract text using pdfplumber (better for tables)"""
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() + "\n"
        return text
    
    def process_corpus_directory(self, pattern: str = "*.pdf") -> List[Dict]:
        """
        Process all PDFs in corpus directory
        Returns list of extracted documents
        """
        pdf_files = list(Path(self.corpus_dir).glob(pattern))
        documents = []
        
        print(f"Found {len(pdf_files)} PDF files to process")
        
        for pdf_path in tqdm(pdf_files, desc="Extracting PDFs"):
            try:
                text = self.extract_text_from_pdf(str(pdf_path))
                if text.strip():
                    documents.append({
                        'filename': pdf_path.name,
                        'text': text,
                        'subject': self._infer_subject(pdf_path.name)
                    })
                    # Save extracted text
                    output_path = os.path.join(
                        self.chunks_dir, 
                        f"{pdf_path.stem}_extracted.txt"
                    )
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(text)
            except Exception as e:
                print(f"Error processing {pdf_path}: {e}")
        
        print(f"Successfully extracted {len(documents)} documents")
        return documents
    
    def _infer_subject(self, filename: str) -> str:
        """Infer subject from filename"""
        filename_lower = filename.lower()
        if 'english' in filename_lower or 'lang' in filename_lower:
            return 'English'
        elif 'biology' in filename_lower or 'bio' in filename_lower:
            return 'Biology'
        elif 'math' in filename_lower or 'maths' in filename_lower:
            return 'Mathematics'
        elif 'physics' in filename_lower:
            return 'Physics'
        elif 'chemistry' in filename_lower or 'chem' in filename_lower:
            return 'Chemistry'
        else:
            return 'General'
    
    def semantic_chunking(self, text: str, chunk_size: int = 256, 
                         overlap: int = 50, min_chunk_size: int = 80) -> List[Dict]:
        """
        Perform semantic chunking on text
        - chunk_size: target token count (approximately)
        - overlap: token overlap between chunks
        - min_chunk_size: minimum tokens to keep a chunk
        """
        # Split into sentences first
        sentences = self._split_into_sentences(text)
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence_tokens = len(sentence.split())
            
            # If adding this sentence would exceed chunk size
            if current_length + sentence_tokens > chunk_size and current_chunk:
                # Save current chunk if it meets minimum size
                if current_length >= min_chunk_size:
                    chunks.append({
                        'text': ' '.join(current_chunk),
                        'token_count': current_length
                    })
                
                # Start new chunk with overlap
                overlap_sentences = self._get_overlap_sentences(
                    current_chunk, overlap
                )
                current_chunk = overlap_sentences + [sentence]
                current_length = sum(len(s.split()) for s in current_chunk)
            else:
                current_chunk.append(sentence)
                current_length += sentence_tokens
        
        # Don't forget the last chunk
        if current_chunk and current_length >= min_chunk_size:
            chunks.append({
                'text': ' '.join(current_chunk),
                'token_count': current_length
            })
        
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences using regex"""
        # Handle common sentence boundaries
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _get_overlap_sentences(self, sentences: List[str], 
                              overlap_tokens: int) -> List[str]:
        """Get sentences for overlap from the end of current chunk"""
        overlap_sentences = []
        current_tokens = 0
        
        for sentence in reversed(sentences):
            sentence_tokens = len(sentence.split())
            if current_tokens + sentence_tokens <= overlap_tokens:
                overlap_sentences.insert(0, sentence)
                current_tokens += sentence_tokens
            else:
                break
        
        return overlap_sentences
    
    def chunk_document(self, document: Dict, chunk_size: int = 256, 
                      overlap: int = 50) -> List[Dict]:
        """Chunk a single document"""
        chunks = self.semantic_chunking(
            document['text'], 
            chunk_size=chunk_size, 
            overlap=overlap
        )
        
        # Add metadata to chunks
        for i, chunk in enumerate(chunks):
            chunk.update({
                'chunk_id': i,
                'source_file': document['filename'],
                'subject': document['subject']
            })
        
        return chunks
    
    def process_all_documents(self, chunk_size: int = 256, 
                             overlap: int = 50) -> List[Dict]:
        """
        Process all extracted documents into chunks
        Returns list of all chunks
        """
        # Load extracted documents
        extracted_files = list(Path(self.chunks_dir).glob("*_extracted.txt"))
        documents = []
        
        for file_path in extracted_files:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
                if text.strip():
                    documents.append({
                        'filename': file_path.stem.replace('_extracted', ''),
                        'text': text,
                        'subject': self._infer_subject(file_path.stem)
                    })
        
        # Chunk all documents
        all_chunks = []
        for doc in tqdm(documents, desc="Chunking documents"):
            chunks = self.chunk_document(doc, chunk_size, overlap)
            all_chunks.extend(chunks)
        
        # Save chunks to JSON
        import json
        chunks_path = os.path.join(self.chunks_dir, 'all_chunks.json')
        with open(chunks_path, 'w', encoding='utf-8') as f:
            json.dump(all_chunks, f, ensure_ascii=False, indent=2)
        
        print(f"Created {len(all_chunks)} chunks")
        print(f"Saved to {chunks_path}")
        
        return all_chunks
    
    def get_chunks(self) -> List[Dict]:
        """Load all chunks from JSON file"""
        import json
        chunks_path = os.path.join(self.chunks_dir, 'all_chunks.json')
        
        if not os.path.exists(chunks_path):
            return []
        
        with open(chunks_path, 'r', encoding='utf-8') as f:
            return json.load(f)


if __name__ == "__main__":
    # Example usage
    processor = CorpusProcessor()
    
    # Step 1: Extract text from PDFs
    print("Step 1: Extracting text from PDFs...")
    documents = processor.process_corpus_directory()
    
    # Step 2: Chunk documents
    print("\nStep 2: Chunking documents...")
    chunks = processor.process_all_documents(chunk_size=256, overlap=50)
    
    print(f"\nProcessing complete!")
    print(f"Total documents: {len(documents)}")
    print(f"Total chunks: {len(chunks)}")
