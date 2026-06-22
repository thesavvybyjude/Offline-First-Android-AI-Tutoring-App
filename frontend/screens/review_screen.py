"""
Review Screen
Flashcard review with SM2 spaced repetition
"""

import sys
import os
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.label import Label
from kivy.uix.button import ButtonBehavior
from kivy.uix.gridlayout import GridLayout
from kivy.properties import ObjectProperty
from kivy.animation import Animation
from kivy.graphics import Color, Rectangle, RoundedRectangle, Line
from kivy.app import App
from kivy.metrics import dp

from frontend.theme import get_color, get_font, RADIUS
from frontend.widgets.top_bar import TopBar
from frontend.widgets.glass_card import GlassCard
from frontend.widgets.gradient_button import GradientButton

class RatingButton(ButtonBehavior, BoxLayout):
    def __init__(self, rating: int, **kwargs):
        self.orientation = 'vertical'
        self.size_hint = (1, None)
        self.height = '64dp'
        self.rating = rating
        super().__init__(**kwargs)
        
        # Color mapping roughly based on SM2 quality (0=blackout, 5=perfect)
        if rating <= 2:
            self.base_color = get_color("error")
        elif rating == 3:
            self.base_color = get_color("tertiary")
        else:
            self.base_color = get_color("primary")
            
        self.bind(pos=self._update_canvas, size=self._update_canvas, state=self._update_canvas)
        
        font = get_font("title-lg")
        lbl = Label(text=str(rating), color=get_color("on-surface"), 
                    font_name=font["font_name"], font_size=font["font_size"], bold=True)
        self.add_widget(lbl)

    def _update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            r, g, b, a = self.base_color
            if self.state == 'down':
                Color(r, g, b, 0.4)
            else:
                Color(r, g, b, 0.1) # tinted background
            
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(12)])
            
            Color(r, g, b, 0.8) # Outline
            Line(rounded_rectangle=(self.x, self.y, self.width, self.height, dp(12)), width=1.5)


class ReviewScreen(Screen):
    """Premium flashcard review screen"""
    
    card_layout = ObjectProperty(None)
    question_label = ObjectProperty(None)
    answer_label = ObjectProperty(None)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "review"
        self.student_id = None
        self.current_record = None
        self.current_item = None
        self.items_queue = []
        self.total_session = 0
        self.reviewed_count = 0
        self.is_flipped = False
        
        self.bind(pos=self._update_bg, size=self._update_bg)
        self._build_ui()

    def _update_bg(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*get_color("background"))
            Rectangle(pos=self.pos, size=self.size)

    def on_enter(self):
        app = App.get_running_app()
        self.student_id = str(getattr(app, 'student_id', 'stu_001'))
        self._load_due_items()
    
    def _build_ui(self):
        main_layout = BoxLayout(orientation='vertical')
        
        # Top Bar
        self.top_bar = TopBar(title="Flashcard Review", show_back=True)
        self.top_bar.children[0].children[0].unbind(on_release=self.top_bar.children[0].children[0].events().get('on_release', [])) # remove default if any
        self.top_bar.children[0].children[0].bind(on_release=self.go_back) # Bind back button
        main_layout.add_widget(self.top_bar)
        
        # Progress Bar
        self.progress_container = BoxLayout(orientation='vertical', size_hint_y=None, height='4dp')
        with self.progress_container.canvas.before:
            Color(*get_color("surface-container-highest"))
            Rectangle(pos=self.progress_container.pos, size=self.progress_container.size)
        
        self.progress_bar = BoxLayout(size_hint_x=0.01) # Start at 1%
        with self.progress_bar.canvas.before:
            Color(*get_color("primary"))
            self.progress_rect = Rectangle(pos=self.progress_bar.pos, size=self.progress_bar.size)
            
        def update_prog_rect(instance, val):
            self.progress_rect.pos = instance.pos
            self.progress_rect.size = instance.size
        self.progress_bar.bind(pos=update_prog_rect, size=update_prog_rect)
        self.progress_container.add_widget(self.progress_bar)
        main_layout.add_widget(self.progress_container)

        # Content Area
        content = BoxLayout(orientation='vertical', padding=['24dp'], spacing='24dp')
        
        # Flashcard
        self.card_layout = GlassCard(orientation='vertical', padding='24dp', size_hint_y=0.6)
        
        # Question
        font_q = get_font("headline-md")
        self.question_label = Label(
            text='Loading...',
            font_name=font_q["font_name"],
            font_size=font_q["font_size"],
            color=get_color("on-surface"),
            halign='center',
            valign='center',
            bold=True
        )
        self.question_label.bind(size=self.question_label.setter('text_size'))
        self.card_layout.add_widget(self.question_label)
        
        # Divider
        self.divider = BoxLayout(size_hint_y=None, height='1dp', opacity=0)
        with self.divider.canvas.before:
            Color(*get_color("outline-variant"))
            Rectangle(pos=self.divider.pos, size=self.divider.size)
        self.divider.bind(pos=lambda inst, val: inst.canvas.before.clear() or [Color(*get_color("outline-variant")), Rectangle(pos=inst.pos, size=inst.size)])
        self.card_layout.add_widget(self.divider)
        
        # Answer
        font_a = get_font("body-lg")
        self.answer_label = Label(
            text='',
            font_name=font_a["font_name"],
            font_size=font_a["font_size"],
            color=get_color("on-surface-variant"),
            halign='center',
            valign='center',
            opacity=0
        )
        self.answer_label.bind(size=self.answer_label.setter('text_size'))
        self.card_layout.add_widget(self.answer_label)
        
        content.add_widget(self.card_layout)
        
        # Action Area
        self.action_layout = AnchorLayout(anchor_x='center', anchor_y='bottom', size_hint_y=0.4)
        
        # Flip button
        self.flip_btn = GradientButton(text="Show Answer", size_hint=(1, None), height='56dp')
        self.flip_btn.bind(on_release=self.flip_card)
        self.action_layout.add_widget(self.flip_btn)
        
        # Rating buttons (hidden initially)
        self.rating_layout = GridLayout(cols=6, spacing='8dp', size_hint=(1, None), height='80dp', opacity=0)
        # To make it invisible to layout when not needed, we use opacity, but Kivy still allocates space.
        # Since they are in the same anchor area, we can just switch widgets.
        
        for i in range(0, 6):
            btn = RatingButton(rating=i)
            btn.bind(on_release=lambda instance, rating=i: self.rate_card(rating))
            self.rating_layout.add_widget(btn)
        
        content.add_widget(self.action_layout)
        main_layout.add_widget(content)
        self.add_widget(main_layout)
    
    def _load_due_items(self):
        app = App.get_running_app()
        scheduler = app.services.scheduler
        if not scheduler:
            self.question_label.text = "Please log in first"
            return
        try:
            session = scheduler.get_review_session(self.student_id, limit=20)
            self.items_queue = list(session.items)
            self.total_session = len(self.items_queue)
            self.reviewed_count = 0
            self._update_progress()

            if self.items_queue:
                self._show_next_card()
            else:
                self.question_label.text = "No cards due for review!"
                self.answer_label.text = "Great job! Come back later."
                self.divider.opacity = 1
                self.answer_label.opacity = 1
                self.flip_btn.disabled = True
        except Exception as e:
            print(f"Error loading items: {e}")
            self.question_label.text = "Error loading cards"
    
    def _show_next_card(self):
        if not self.items_queue:
            self.question_label.text = "Review Complete!"
            self.answer_label.text = "You reviewed all due cards."
            self.divider.opacity = 1
            self.answer_label.opacity = 1
            self.flip_btn.disabled = True
            
            # Hide rating layout if visible
            self.action_layout.clear_widgets()
            self.action_layout.add_widget(self.flip_btn)
            return
        
        self.current_record, self.current_item = self.items_queue.pop(0)
        self.is_flipped = False
        
        q_text = self.current_item.question if self.current_item.question else "(No question text)"
        a_text = self.current_item.answer if self.current_item.answer else "(No answer text)"
        self.question_label.text = q_text
        self.answer_label.text = a_text
        self.answer_label.opacity = 0
        self.divider.opacity = 0
        
        # Reset buttons
        self.flip_btn.text = 'Show Answer'
        self.flip_btn.disabled = False
        self.action_layout.clear_widgets()
        self.action_layout.add_widget(self.flip_btn)
        self.rating_layout.opacity = 0
        
        self._update_progress()
    
    def _update_progress(self):
        if self.total_session == 0:
            self.progress_bar.size_hint_x = 0.01
            self.top_bar.title = "Review Complete"
        else:
            pct = max(0.01, self.reviewed_count / self.total_session)
            # Animate progress bar
            anim = Animation(size_hint_x=pct, duration=0.3)
            anim.start(self.progress_bar)
            self.top_bar.title = f"Review ({self.reviewed_count}/{self.total_session})"
    
    def flip_card(self, instance):
        if self.is_flipped:
            return
        
        self.is_flipped = True
        
        anim = Animation(opacity=1, duration=0.3)
        anim.start(self.answer_label)
        anim.start(self.divider)
        
        # Switch action buttons
        self.action_layout.clear_widgets()
        self.rating_layout.opacity = 0
        self.action_layout.add_widget(self.rating_layout)
        
        rating_anim = Animation(opacity=1, duration=0.3)
        rating_anim.start(self.rating_layout)
    
    def rate_card(self, rating: int):
        if not self.current_record:
            return
        
        try:
            app = App.get_running_app()
            scheduler = app.services.scheduler
            scheduler.record_response(
                self.current_record.id,
                rating,
            )
            self.reviewed_count += 1
            
            # Animate card disappearing
            anim = Animation(opacity=0, duration=0.2)
            anim.bind(on_complete=lambda *args: self._finish_rate_anim())
            anim.start(self.card_layout)
            
        except Exception as e:
            print(f"Error rating card: {e}")

    def _finish_rate_anim(self):
        self._show_next_card()
        # Restore opacity
        self.card_layout.opacity = 1
        anim = Animation(opacity=1, duration=0.2)
        anim.start(self.card_layout)
    
    def go_back(self, instance):
        self.manager.current = 'dashboard'

