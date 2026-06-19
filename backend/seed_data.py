"""
Default curriculum flashcards for first-run experience (no LLM required).
"""

from __future__ import annotations

from backend.sm2_scheduler import KnowledgeItem, SM2Scheduler

DEFAULT_ITEMS: list[KnowledgeItem] = [
    KnowledgeItem(
        id="bio_osmosis",
        subject="Biology",
        question="What is osmosis?",
        answer="Movement of water through a selectively permeable membrane from higher to lower water concentration.",
        source_chunk="Biology_Ch1",
        difficulty=2,
    ),
    KnowledgeItem(
        id="bio_mitochondria",
        subject="Biology",
        question="What is the function of mitochondria?",
        answer="They produce energy (ATP) for the cell — often called the powerhouse of the cell.",
        source_chunk="Biology_Ch1",
        difficulty=2,
    ),
    KnowledgeItem(
        id="bio_cell",
        subject="Biology",
        question="What is a cell?",
        answer="The smallest unit of life that can carry out all life processes.",
        source_chunk="Biology_Ch1",
        difficulty=1,
    ),
    KnowledgeItem(
        id="eng_noun",
        subject="English",
        question="What is a noun?",
        answer="A word that names a person, place, thing, or idea.",
        source_chunk="English_Ch1",
        difficulty=1,
    ),
    KnowledgeItem(
        id="eng_verb",
        subject="English",
        question="What is a verb?",
        answer="A word that expresses an action or state of being.",
        source_chunk="English_Ch1",
        difficulty=1,
    ),
    KnowledgeItem(
        id="eng_sentence",
        subject="English",
        question="What makes a complete sentence?",
        answer="A subject and a predicate that express a complete thought.",
        source_chunk="English_Ch1",
        difficulty=2,
    ),
    KnowledgeItem(
        id="bio_photosynthesis",
        subject="Biology",
        question="What is photosynthesis?",
        answer="The process plants use to convert light energy into chemical energy (glucose) using CO₂ and water.",
        source_chunk="Biology_Ch1",
        difficulty=3,
    ),
    KnowledgeItem(
        id="bio_dna",
        subject="Biology",
        question="What does DNA store?",
        answer="Genetic information that controls traits and cell activities.",
        source_chunk="Biology_Ch1",
        difficulty=3,
    ),
]


def seed_default_knowledge(scheduler: SM2Scheduler, student_id: str) -> int:
    """Insert starter flashcards and repetition records for a new student."""
    for item in DEFAULT_ITEMS:
        scheduler.upsert_knowledge_item(item)
    return scheduler.seed_items_for_student(student_id)
