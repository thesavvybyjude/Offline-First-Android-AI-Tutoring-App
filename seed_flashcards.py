"""
seed_flashcards.py
One-time seeding script. Uses Phi-3 Mini to generate Q&A pairs
for each semantic chunk in the vector index, then inserts them into SQLite.
"""

import os
import sys
import json
from pathlib import Path

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.rag_pipeline import RAGPipeline
from backend.inference_engine import InferenceEngine
from backend.sm2_scheduler import SM2Scheduler, KnowledgeItem

def generate_flashcards():
    print("Initializing LLM Seeding Script...")
    
    rag = RAGPipeline()
    try:
        rag.load()
    except RuntimeError as e:
        print(f"Error loading RAG index: {e}")
        print("Please ingest documents first using RAGPipeline.ingest_documents()")
        return
        
    engine = InferenceEngine(models_dir=Path("models"))
    print("Loading inference engine (4GB preset)...")
    try:
        engine.load(ram_gb=4.0)
    except FileNotFoundError:
        print("Model not found. Run setup_env.py first.")
        return
        
    scheduler = SM2Scheduler(db_path=Path("data/tutor.db"))
    scheduler.init_db()
    
    # Define generation prompt
    prompt_template = """### System
You are an expert tutor creating flashcards for secondary school students. 
Extract exactly ONE clear Question and ONE concise Answer from the provided text.
Format your response exactly as:
Q: [Your Question]
A: [Your Answer]

### Text
{text}

### Assistant
"""

    print(f"Loaded {len(rag.index.chunks)} chunks. Beginning Q&A generation...")
    
    new_items_count = 0
    # For demo purposes, we process up to 50 chunks to save time
    chunks_to_process = rag.index.chunks[:50] 
    
    for i, chunk in enumerate(chunks_to_process):
        print(f"Processing chunk {i+1}/{len(chunks_to_process)} from {chunk.subject}...")
        
        prompt = prompt_template.format(text=chunk.text)
        result = engine.generate(prompt, params={"max_tokens": 128, "temperature": 0.2})
        
        # Simple parser for Q: and A:
        lines = result.text.split('\n')
        q = None
        a = None
        for line in lines:
            line = line.strip()
            if line.startswith("Q:"):
                q = line[2:].strip()
            elif line.startswith("A:"):
                a = line[2:].strip()
                
        if q and a:
            item_id = f"item_gen_{chunk.id}"
            item = KnowledgeItem(
                id=item_id,
                subject=chunk.subject,
                question=q,
                answer=a,
                source_chunk=chunk.id,
                difficulty=3
            )
            scheduler.upsert_knowledge_item(item)
            new_items_count += 1
            print(f"  -> Generated: {q[:50]}...")
        else:
            print(f"  -> Failed to parse LLM output: {result.text[:50]}...")
            
    print(f"\nSuccessfully generated {new_items_count} flashcards!")
    
    # Queue these for all existing test students
    with sqlite3.connect("data/tutor.db") as conn:
        conn.row_factory = sqlite3.Row
        students = conn.execute("SELECT id FROM students").fetchall()
        
    for student in students:
        s_id = student["id"]
        seeded = scheduler.seed_items_for_student(s_id)
        print(f"Seeded {seeded} new flashcards for student {s_id}")
        
    engine.unload()

if __name__ == "__main__":
    import sqlite3
    generate_flashcards()
