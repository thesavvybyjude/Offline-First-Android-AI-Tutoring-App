import logging
import re
import uuid
from typing import List, Tuple
from backend.rag_pipeline import RAGPipeline
from backend.inference_engine import InferenceEngine
from backend.sm2_scheduler import SM2Scheduler, KnowledgeItem

logger = logging.getLogger(__name__)

FLASHCARD_PROMPT = """\
### System
You are an expert tutor for Nigerian secondary school students.
Your task is to generate 3 spaced-repetition flashcards based on the provided context.
Focus ONLY on the context provided.
You MUST output the flashcards in exactly the following format:
Q: [Question text]
A: [Answer text]

Do not include any introductory or concluding text. Just the Q: and A: pairs.

### Relevant Curriculum Context
{context}

### Topic
Create 3 flashcards specifically about: {topic}

### Response
"""

class FlashcardGenerator:
    def __init__(self, rag: RAGPipeline, engine: InferenceEngine, scheduler: SM2Scheduler):
        self.rag = rag
        self.engine = engine
        self.scheduler = scheduler

    def generate_and_save(self, student_id: str, subject: str, topic: str) -> int:
        """
        Generate flashcards using RAG + LLM, save to DB, and assign to student.
        Returns the number of flashcards successfully created.
        """
        logger.info(f"Generating flashcards for {subject}: {topic}")
        
        if not self.rag.is_loaded:
            raise RuntimeError("RAGPipeline must be loaded first.")
        if not self.engine.is_loaded:
            raise RuntimeError("InferenceEngine must be loaded first.")

        # 1. Retrieve Context
        # We search specifically for the topic
        retrieval = self.rag.retrieve(topic)
        filtered_chunks = [c for c in retrieval.chunks if c.subject.lower() == subject.lower()]
        
        if not filtered_chunks:
            logger.warning(f"No context found for topic: {topic} in subject: {subject}")
            context_text = "No specific context found. Use general knowledge for this subject."
            source_chunk = f"{subject}_Generated"
        else:
            context_text = "\n\n".join([f"- {c.text}" for c in filtered_chunks[:3]])
            source_chunk = filtered_chunks[0].source
            
        # 2. Build Prompt
        prompt = FLASHCARD_PROMPT.format(context=context_text, topic=topic)
        
        # 3. Generate from LLM
        # Use a slightly higher temperature for creativity, but low enough to stick to format
        params = {"temperature": 0.4, "max_tokens": 512, "stop": ["###"]}
        result = self.engine.generate(prompt, params=params)
        raw_text = result.text
        
        logger.debug(f"LLM Output:\n{raw_text}")
        
        # 4. Parse Output
        cards = self._parse_flashcards(raw_text)
        if not cards:
            logger.error("Failed to parse any flashcards from LLM output.")
            return 0
            
        # 5. Save to DB
        new_items = []
        for q, a in cards:
            item_id = f"gen_{uuid.uuid4().hex[:8]}"
            item = KnowledgeItem(
                id=item_id,
                subject=subject,
                question=q,
                answer=a,
                source_chunk=source_chunk,
                difficulty=2
            )
            self.scheduler.upsert_knowledge_item(item)
            new_items.append(item)
            
        # Seed them for the student
        added = self.scheduler.seed_items_for_student(student_id, subject=subject)
        logger.info(f"Successfully generated and seeded {added} flashcards.")
        return added

    def _parse_flashcards(self, text: str) -> List[Tuple[str, str]]:
        """
        Robustly parse Q: and A: pairs from raw LLM text.
        """
        cards = []
        # Find all occurrences of Q: followed by anything until A:, and then A: until the next Q: or end of string.
        pattern = r"Q:\s*(.*?)\s*A:\s*(.*?)(?=Q:|#|$)"
        matches = re.findall(pattern, text, flags=re.DOTALL | re.IGNORECASE)
        
        for q, a in matches:
            q_clean = q.strip()
            a_clean = a.strip()
            if q_clean and a_clean:
                cards.append((q_clean, a_clean))
                
        return cards
