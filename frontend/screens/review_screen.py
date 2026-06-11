"""
Review Screen
Flashcard review with SM2 spaced repetition
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.properties import ObjectProperty
from kivy.animation import Animation
from kivy.graphics import Color, Rectangle
from backend.database import DatabaseManager
from backend.sm2_scheduler import SM2Scheduler


class ReviewScreen(Screen):
    """Flashcard review screen with flip animation"""
    
    card_layout = ObjectProperty(None)
    question_label = ObjectProperty(None)
    answer_label = ObjectProperty(None)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'review'
        self.db = DatabaseManager()
        self.scheduler = SM2Scheduler(self.db)
        self.student_id = None
        self.current_item = None
        self.items_queue = []
        self.is_flipped = False
        self._build_ui()
    
    def on_enter(self):
        """Called when screen is entered"""
        app = self.manager.app
        self.student_id = getattr(app, 'student_id', 1)
        self._load_due_items()
    
    def _build_ui(self):
        """Build the review UI"""
        # Main layout
        layout = BoxLayout(orientation='vertical', padding=15, spacing=15)
        
        # Header
        header = BoxLayout(orientation='horizontal', size_hint_y=0.08)
        back_btn = Button(text='←', size_hint_x=0.1, font_size=24)
        back_btn.bind(on_press=self.go_back)
        header_label = Label(text='Flashcard Review', font_size=20, bold=True)
        self.progress_label = Label(text='0/0', font_size=16)
        header.add_widget(back_btn)
        header.add_widget(header_label)
        header.add_widget(self.progress_label)
        layout.add_widget(header)
        
        # Card area
        self.card_layout = BoxLayout(
            orientation='vertical',
            size_hint_y=0.5,
            padding=20
        )
        
        with self.card_layout.canvas.before:
            Color(1, 1, 1, 1)
            self.card_layout.rect = Rectangle(pos=self.card_layout.pos, size=self.card_layout.size)
        
        self.card_layout.bind(pos=self._update_card_rect, size=self._update_card_rect)
        
        # Question
        self.question_label = Label(
            text='Loading...',
            font_size=18,
            text_size=(330, None),
            halign='center',
            valign='center'
        )
        self.card_layout.add_widget(self.question_label)
        
        # Answer (hidden initially)
        self.answer_label = Label(
            text='',
            font_size=16,
            text_size=(330, None),
            halign='center',
            valign='center',
            opacity=0
        )
        self.card_layout.add_widget(self.answer_label)
        
        layout.add_widget(self.card_layout)
        
        # Flip button
        self.flip_btn = Button(
            text='Show Answer',
            font_size=18,
            size_hint_y=0.1,
            background_color=(0.2, 0.6, 0.8, 1)
        )
        self.flip_btn.bind(on_press=self.flip_card)
        layout.add_widget(self.flip_btn)
        
        # Rating buttons (hidden initially)
        self.rating_layout = GridLayout(cols=5, spacing=5, size_hint_y=0.15, opacity=0)
        
        for i in range(1, 6):
            btn = Button(text=str(i), font_size=20)
            btn.bind(on_press=lambda instance, rating=i: self.rate_card(rating))
            self.rating_layout.add_widget(btn)
        
        layout.add_widget(self.rating_layout)
        
        # Spacer
        layout.add_widget(Label(size_hint_y=0.1))
        
        self.add_widget(layout)
    
    def _update_card_rect(self, instance, value):
        """Update card rectangle"""
        self.card_layout.rect.pos = instance.pos
        self.card_layout.rect.size = instance.size
    
    def _load_due_items(self):
        """Load items due for review"""
        try:
            session = self.scheduler.get_review_session(self.student_id, session_size=20)
            self.items_queue = session['items']
            self._update_progress()
            
            if self.items_queue:
                self._show_next_card()
            else:
                self.question_label.text = "No cards due for review!"
                self.answer_label.text = "Great job! Come back later."
                self.answer_label.opacity = 1
                self.flip_btn.disabled = True
        except Exception as e:
            print(f"Error loading items: {e}")
            self.question_label.text = "Error loading cards"
    
    def _show_next_card(self):
        """Show the next card in the queue"""
        if not self.items_queue:
            self.question_label.text = "Review Complete!"
            self.answer_label.text = f"You reviewed {len(self.items_queue)} cards."
            self.answer_label.opacity = 1
            self.flip_btn.disabled = True
            return
        
        self.current_item = self.items_queue.pop(0)
        self.is_flipped = False
        
        # Show question
        self.question_label.text = self.current_item['question']
        self.answer_label.text = self.current_item['answer']
        self.answer_label.opacity = 0
        
        # Reset buttons
        self.flip_btn.text = 'Show Answer'
        self.flip_btn.disabled = False
        self.rating_layout.opacity = 0
        
        self._update_progress()
    
    def _update_progress(self):
        """Update progress label"""
        total = len(self.items_queue) + (1 if self.current_item else 0)
        reviewed = len(self.items_queue)
        self.progress_label.text = f'{reviewed}/{total}'
    
    def flip_card(self, instance):
        """Flip the card to show answer"""
        if self.is_flipped:
            return
        
        self.is_flipped = True
        
        # Animate answer appearance
        anim = Animation(opacity=1, duration=0.3)
        anim.start(self.answer_label)
        
        # Show rating buttons
        rating_anim = Animation(opacity=1, duration=0.3)
        rating_anim.start(self.rating_layout)
        
        self.flip_btn.text = 'Answer Shown'
        self.flip_btn.disabled = True
    
    def rate_card(self, rating: int):
        """Rate the card and schedule next review"""
        if not self.current_item:
            return
        
        try:
            # Update SM2 record
            self.scheduler.schedule_review(
                self.student_id,
                self.current_item['item_id'],
                rating
            )
            
            # Hide rating buttons
            anim = Animation(opacity=0, duration=0.2)
            anim.start(self.rating_layout)
            
            # Show next card
            self._show_next_card()
            
        except Exception as e:
            print(f"Error rating card: {e}")
    
    def go_back(self, instance):
        """Return to dashboard"""
        self.manager.current = 'dashboard'
