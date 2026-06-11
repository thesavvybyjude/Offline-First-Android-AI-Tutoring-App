"""
SM2 Spaced Repetition Scheduler
Implements the SuperMemo 2 algorithm for flashcard scheduling
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional
from backend.database import DatabaseManager


class SM2Scheduler:
    """SM2 Algorithm implementation for spaced repetition"""
    
    def __init__(self, db_manager: DatabaseManager = None):
        self.db = db_manager or DatabaseManager()
    
    def calculate_next_review(self, quality: int, ease_factor: float,
                            interval: int, repetitions: int) -> Dict[str, any]:
        """
        Calculate next review parameters using SM2 algorithm
        quality: 0-5 (0=complete failure, 5=perfect response)
        ease_factor: Current ease factor (default 2.5)
        interval: Current interval in days
        repetitions: Current repetition count
        
        Returns dict with updated parameters
        """
        # Update ease factor
        new_ef = ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        new_ef = max(1.3, new_ef)  # Minimum ease factor is 1.3
        
        # Update interval and repetitions
        if quality >= 3:
            # Correct response
            if repetitions == 0:
                new_interval = 1
            elif repetitions == 1:
                new_interval = 6
            else:
                new_interval = int(round(interval * new_ef))
            new_repetitions = repetitions + 1
        else:
            # Incorrect response - reset
            new_interval = 1
            new_repetitions = 0
        
        # Calculate next review date
        next_review = datetime.now() + timedelta(days=new_interval)
        
        return {
            'ease_factor': new_ef,
            'interval_days': new_interval,
            'repetitions': new_repetitions,
            'next_review': next_review,
            'last_quality': quality
        }
    
    def schedule_review(self, student_id: int, item_id: int, 
                       quality: int) -> Dict:
        """
        Schedule next review for a student-item pair
        Updates the database with new SM2 parameters
        """
        # Get current record
        record = self.db.get_repetition_record(student_id, item_id)
        
        if record is None:
            # Create new record with defaults
            self.db.create_repetition_record(student_id, item_id)
            record = self.db.get_repetition_record(student_id, item_id)
        
        # Calculate new parameters
        params = self.calculate_next_review(
            quality=quality,
            ease_factor=record['ease_factor'],
            interval=record['interval_days'],
            repetitions=record['repetitions']
        )
        
        # Update database
        self.db.update_repetition_record(student_id, item_id, quality)
        
        return params
    
    def get_due_items(self, student_id: int, limit: int = 20) -> List[Dict]:
        """Get items due for review today"""
        return self.db.get_due_items(student_id, limit)
    
    def get_review_session(self, student_id: int, session_size: int = 20) -> Dict:
        """
        Get a complete review session for a student
        Returns session info with due items
        """
        due_items = self.get_due_items(student_id, limit=session_size)
        stats = self.db.get_student_stats(student_id)
        
        return {
            'student_id': student_id,
            'due_count': len(due_items),
            'items': due_items,
            'stats': stats
        }
    
    def seed_flashcards_from_chunks(self, chunks: List[Dict], 
                                   inference_engine) -> int:
        """
        Auto-generate flashcards from RAG chunks using LLM
        Returns number of flashcards created
        """
        created_count = 0
        
        from tqdm import tqdm
        
        for chunk in tqdm(chunks, desc="Generating flashcards"):
            try:
                # Generate flashcard using LLM
                flashcard = inference_engine.generate_flashcard(
                    chunk_text=chunk['text'],
                    subject=chunk['subject']
                )
                
                # Validate flashcard
                if flashcard['question'] and flashcard['answer']:
                    # Create knowledge item
                    item_id = self.db.create_knowledge_item(
                        subject=chunk['subject'],
                        question=flashcard['question'],
                        answer=flashcard['answer'],
                        source_chunk=chunk['text'],
                        chunk_id=chunk.get('chunk_id')
                    )
                    created_count += 1
            except Exception as e:
                print(f"Error generating flashcard for chunk {chunk.get('chunk_id')}: {e}")
                continue
        
        print(f"Created {created_count} flashcards from {len(chunks)} chunks")
        return created_count
    
    def get_learning_curve(self, student_id: int, days: int = 7) -> List[Dict]:
        """
        Get learning curve data for the last N days
        Returns daily review counts and average quality
        """
        conn = self.db.connect()
        cursor = conn.cursor()
        
        curve_data = []
        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            date_str = date.strftime('%Y-%m-%d')
            
            # Get reviews on this date
            cursor.execute(
                """SELECT COUNT(*) as count, AVG(last_quality) as avg_quality
                   FROM repetition_records
                   WHERE student_id = ? 
                   AND DATE(last_review) = ?""",
                (student_id, date_str)
            )
            row = cursor.fetchone()
            
            curve_data.append({
                'date': date_str,
                'reviews': row['count'] or 0,
                'avg_quality': round(row['avg_quality'] or 0, 2)
            })
        
        return list(reversed(curve_data))


if __name__ == "__main__":
    # Example usage
    scheduler = SM2Scheduler()
    
    # Test SM2 calculation
    params = scheduler.calculate_next_review(
        quality=4,
        ease_factor=2.5,
        interval=1,
        repetitions=0
    )
    
    print("SM2 Calculation Result:")
    print(f"  Ease Factor: {params['ease_factor']:.2f}")
    print(f"  Interval: {params['interval_days']} days")
    print(f"  Repetitions: {params['repetitions']}")
    print(f"  Next Review: {params['next_review']}")
