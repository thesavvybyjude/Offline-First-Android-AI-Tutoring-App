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
from frontend.screens.tutor_chat_screen import ChipButton

class RatingButton(ButtonBehavior, BoxLayout):
    def __init__(self, text: str, rating: int, color_name: str, **kwargs):
        self.orientation = 'vertical'
        self.size_hint = (1, None)
        self.height = '64dp'
        self.rating = rating
        super().__init__(**kwargs)
        
        self.base_color = get_color(color_name)
            
        self.bind(pos=self._update_canvas, size=self._update_canvas, state=self._update_canvas)
        
        font = get_font("label-lg")
        lbl = Label(text=text, color=get_color("on-surface"), 
                    font_name=font["font_name"], font_size=font["font_size"], bold=True)
        self.add_widget(lbl)

    def _update_canvas(self, *args):
        from kivy.clock import Clock
        Clock.schedule_once(self._deferred_update_canvas, -1)

    def _deferred_update_canvas(self, dt):
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
        self.active_subject = "Biology"
        
        with self.canvas.before:
            Color(*get_color("background"))
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        def update_bg(instance, value):
            self.bg_rect.pos = instance.pos
            self.bg_rect.size = instance.size
        self.bind(pos=update_bg, size=update_bg)
        self._build_ui()

    def on_enter(self):
        app = App.get_running_app()
        self.student_id = str(getattr(app, 'student_id', 'stu_001'))
        self._load_due_items()
    
    def _build_ui(self):
        main_layout = BoxLayout(orientation='vertical')
        
        # Top Bar
        self.top_bar = TopBar(title="Flashcard Review", show_back=False)
        main_layout.add_widget(self.top_bar)
        
        # Subject Selection
        sub_head = BoxLayout(orientation='horizontal', size_hint_y=None, height='40dp', padding=['16dp', '0dp'], spacing='8dp')
        self.btn_biology = ChipButton(text="Biology")
        self.btn_english = ChipButton(text="English")
        self.btn_biology.bind(on_release=lambda x: self._select_subject("Biology"))
        self.btn_english.bind(on_release=lambda x: self._select_subject("English"))
        sub_head.add_widget(self.btn_biology)
        sub_head.add_widget(self.btn_english)
        sub_head.add_widget(BoxLayout(size_hint_x=1)) # spacer
        
        # AI Generate Button
        self.btn_generate = ChipButton(text="✨ AI Generate")
        self.btn_generate.bind(on_release=lambda x: self._open_generate_dialog())
        sub_head.add_widget(self.btn_generate)
        
        main_layout.add_widget(sub_head)
        
        # Initial state
        self.btn_biology.state = 'down'
        self.btn_biology._update_canvas()
        
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
        
        # Badge Area
        badge_area = AnchorLayout(anchor_x='left', anchor_y='top', size_hint_y=None, height='24dp')
        font_sm = get_font("label-sm")
        self.badge_lbl = Label(
            text="🧬 Biology",
            color=get_color("primary"),
            font_name=font_sm["font_name"],
            font_size=font_sm["font_size"],
            bold=True,
            size_hint=(None, None),
            height='24dp',
            padding=['12dp', '0dp']
        )
        self.badge_lbl.bind(texture_size=self.badge_lbl.setter('size'))
        with self.badge_lbl.canvas.before:
            Color(*get_color("primary")[:3] + (0.2,))
            self.badge_rect = RoundedRectangle(pos=self.badge_lbl.pos, size=self.badge_lbl.size, radius=[dp(12)])
        def update_badge_rect(instance, value):
            self.badge_rect.pos = instance.pos
            self.badge_rect.size = instance.size
        self.badge_lbl.bind(pos=update_badge_rect, size=update_badge_rect)
        badge_area.add_widget(self.badge_lbl)
        self.card_layout.add_widget(badge_area)
        
        # Spacer
        self.card_layout.add_widget(BoxLayout(size_hint_y=None, height='16dp'))
        
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
            self.divider_rect = Rectangle(pos=self.divider.pos, size=self.divider.size)
        def update_divider_rect(instance, value):
            self.divider_rect.pos = instance.pos
            self.divider_rect.size = instance.size
        self.divider.bind(pos=update_divider_rect, size=update_divider_rect)
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
        self.action_layout = BoxLayout(orientation='vertical', size_hint_y=0.4, padding=['0dp', '0dp', '0dp', '16dp'])
        
        # Flip button
        self.flip_btn = GradientButton(text="Show Answer", size_hint=(1, None), height='56dp')
        self.flip_btn.bind(on_release=self.flip_card)
        
        # Rating buttons (hidden initially)
        from kivy.uix.widget import Widget
        self.action_layout_spacer = Widget()
        self.action_layout.add_widget(self.action_layout_spacer)
        self.action_layout.add_widget(self.flip_btn)
        
        self.rating_layout = GridLayout(cols=4, spacing='8dp', size_hint=(1, None), height='64dp', opacity=0)
        
        ratings = [
            ("Again", 0, "error"),
            ("Hard", 2, "secondary"),
            ("Good", 4, "primary"),
            ("Easy", 5, "tertiary")
        ]
        
        for text, r, c in ratings:
            btn = RatingButton(text=text, rating=r, color_name=c)
            btn.bind(on_release=lambda instance, rating=r: self.rate_card(rating))
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
            session = scheduler.get_review_session(self.student_id, limit=20, subject=self.active_subject)
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
            
    def _select_subject(self, subject):
        if self.active_subject == subject:
            return
        self.active_subject = subject
        self.btn_biology.state = 'down' if subject == 'Biology' else 'normal'
        self.btn_english.state = 'down' if subject == 'English' else 'normal'
        self.btn_biology._update_canvas()
        self.btn_english._update_canvas()
        self._load_due_items()
    
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
        self.badge_lbl.text = "🧬 Biology" if self.current_item.subject == "Biology" else "📚 English"
        self.answer_label.opacity = 0
        self.divider.opacity = 0
        
        # Reset buttons
        self.flip_btn.text = 'Show Answer'
        self.flip_btn.disabled = False
        self.action_layout.clear_widgets()
        self.action_layout.add_widget(self.action_layout_spacer)
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
        self.action_layout.add_widget(self.action_layout_spacer)
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

    def _open_generate_dialog(self):
        from kivy.uix.popup import Popup
        from kivy.uix.textinput import TextInput
        
        content = BoxLayout(orientation='vertical', spacing='16dp', padding='16dp')
        
        font = get_font("body-md")
        topic_input = TextInput(
            hint_text=f"Enter a {self.active_subject} topic...",
            multiline=False,
            font_name=font["font_name"],
            font_size=font["font_size"],
            size_hint_y=None, height='48dp',
            padding=['12dp', '12dp']
        )
        content.add_widget(topic_input)
        
        status_lbl = Label(text="", color=get_color("error"), font_name=font["font_name"], font_size=font["font_size"], size_hint_y=None, height='32dp')
        content.add_widget(status_lbl)
        
        btn_layout = BoxLayout(orientation='horizontal', spacing='16dp', size_hint_y=None, height='48dp')
        cancel_btn = GradientButton(text="Cancel", size_hint_x=0.5)
        gen_btn = GradientButton(text="Generate", size_hint_x=0.5)
        
        btn_layout.add_widget(cancel_btn)
        btn_layout.add_widget(gen_btn)
        content.add_widget(btn_layout)
        
        popup = Popup(title=f"Generate {self.active_subject} Cards", content=content, size_hint=(0.9, 0.4), background_color=get_color("surface"), title_color=get_color("on-surface"))
        
        def on_cancel(instance):
            popup.dismiss()
            
        def on_generate(instance):
            topic = topic_input.text.strip()
            if not topic:
                status_lbl.text = "Please enter a topic."
                return
            status_lbl.text = "Warming up AI Model..."
            status_lbl.color = get_color("primary")
            gen_btn.disabled = True
            topic_input.disabled = True
            
            import threading
            threading.Thread(target=self._run_generation, args=(topic, popup, status_lbl, gen_btn, topic_input), daemon=True).start()
            
        cancel_btn.bind(on_release=on_cancel)
        gen_btn.bind(on_release=on_generate)
        popup.open()

    def _run_generation(self, topic, popup, status_lbl, gen_btn, topic_input):
        from kivy.clock import Clock
        app = App.get_running_app()
        
        def set_status(msg):
            Clock.schedule_once(lambda dt: setattr(status_lbl, 'text', msg), 0)
            
        try:
            if not app.services.is_ai_ready() or not getattr(app.services, 'rag', None) or not app.services.rag.is_loaded:
                set_status("AI is not ready yet. Please wait.")
                Clock.schedule_once(lambda dt: setattr(gen_btn, 'disabled', False), 0)
                Clock.schedule_once(lambda dt: setattr(topic_input, 'disabled', False), 0)
                Clock.schedule_once(lambda dt: setattr(status_lbl, 'color', get_color('error')), 0)
                return
                
            set_status(f"Generating flashcards for '{topic}'...")
            
            from backend.flashcard_generator import FlashcardGenerator
            generator = FlashcardGenerator(app.services.rag, app.services.engine, app.services.scheduler)
            count = generator.generate_and_save(self.student_id, self.active_subject, topic)
            
            if count > 0:
                set_status(f"Success! Created {count} cards.")
                import time
                time.sleep(1)
                Clock.schedule_once(lambda dt: popup.dismiss(), 0)
                Clock.schedule_once(lambda dt: self._load_due_items(), 0)
            else:
                set_status("Failed to generate cards. Try a different topic.")
                Clock.schedule_once(lambda dt: setattr(status_lbl, 'color', get_color('error')), 0)
                Clock.schedule_once(lambda dt: setattr(gen_btn, 'disabled', False), 0)
                Clock.schedule_once(lambda dt: setattr(topic_input, 'disabled', False), 0)
                
        except Exception as e:
            set_status(f"Error: {str(e)[:40]}")
            Clock.schedule_once(lambda dt: setattr(status_lbl, 'color', get_color('error')), 0)
            Clock.schedule_once(lambda dt: setattr(gen_btn, 'disabled', False), 0)
            Clock.schedule_once(lambda dt: setattr(topic_input, 'disabled', False), 0)

