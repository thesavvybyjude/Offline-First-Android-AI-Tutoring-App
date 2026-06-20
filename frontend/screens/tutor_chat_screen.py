"""
Tutor Chat Screen
AI tutoring interface with on-device streaming responses
"""

import sys
import os
import threading

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.properties import ObjectProperty
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle


class TutorChatScreen(Screen):
    """Tutor chat screen with on-device AI responses"""

    chat_layout = ObjectProperty(None)
    message_input = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "tutor_chat"
        self.messages = []
        self.current_ai_label = None
        self.typing_event = None
        self.typing_dots = 1
        self._generating = False
        self._build_ui()

    def on_enter(self):
        app = App.get_running_app()
        if not app.services.is_ai_ready() and not app.services._loading:
            app.services.load_ai_async(self._on_ai_reload)

    def on_leave(self, *args):
        """Clean up typing animation when leaving screen mid-generation."""
        self._cancel_typing_animation()

    def _on_ai_reload(self, ok: bool, err):
        app = App.get_running_app()
        app.ai_status = app.services.ai_status_message()

    def _build_ui(self):
        layout = BoxLayout(orientation="vertical", padding=10, spacing=10)

        header = BoxLayout(orientation="horizontal", size_hint_y=0.08)
        header_label = Label(text="AI Tutor", font_size=24, bold=True)
        back_btn = Button(text="←", size_hint_x=0.1, font_size=24)
        back_btn.bind(on_press=self.go_back)
        header.add_widget(back_btn)
        header.add_widget(header_label)
        layout.add_widget(header)

        scroll = ScrollView(size_hint_y=0.75)
        self.chat_layout = GridLayout(cols=1, spacing=5, size_hint_y=None)
        self.chat_layout.bind(minimum_height=self.chat_layout.setter("height"))
        scroll.add_widget(self.chat_layout)
        layout.add_widget(scroll)

        input_layout = BoxLayout(orientation="horizontal", size_hint_y=0.12, spacing=10)

        self.message_input = TextInput(
            hint_text="Ask a question...",
            multiline=False,
            font_size=16,
        )
        input_layout.add_widget(self.message_input)

        self.send_btn = Button(
            text="Send",
            size_hint_x=0.25,
            font_size=16,
            background_color=(0.2, 0.6, 0.8, 1),
        )
        self.send_btn.bind(on_press=self.send_message)
        input_layout.add_widget(self.send_btn)

        layout.add_widget(input_layout)
        self.add_widget(layout)

        self._add_message(
            "Hello! Ask me anything about your curriculum. "
            "If AI is still loading, wait a moment and try again.",
            is_user=False,
        )

    def send_message(self, instance):
        query = self.message_input.text.strip()
        if not query:
            return

        app = App.get_running_app()
        if not app.services.is_ai_ready():
            self._add_message(
                app.services.ai_status_message() + "\nRun setup_env.py to download a model.",
                is_user=False,
            )
            return

        self.message_input.text = ""
        self._add_message(query, is_user=True)
        self.send_btn.disabled = True
        self._generating = True

        self.current_ai_label = self._add_message("...", is_user=False, return_label=True)
        self.typing_dots = 1
        self.typing_event = Clock.schedule_interval(self._animate_typing, 0.5)

        threading.Thread(target=self._get_ai_response_worker, args=(query,), daemon=True).start()

    def _animate_typing(self, dt):
        self.typing_dots = (self.typing_dots % 3) + 1
        if self.current_ai_label:
            self.current_ai_label.text = "." * self.typing_dots

    def _cancel_typing_animation(self):
        if self.typing_event is not None:
            self.typing_event.cancel()
            self.typing_event = None

    def _add_message(self, text: str, is_user: bool = False, return_label: bool = False):
        msg_layout = BoxLayout(orientation="vertical", size_hint_y=None, padding=10)

        bubble = BoxLayout(orientation="vertical", size_hint_y=None, padding=10)

        with bubble.canvas.before:
            if is_user:
                Color(0.2, 0.6, 0.8, 1)
            else:
                Color(0.3, 0.3, 0.3, 1)
            bubble.rect = Rectangle(pos=bubble.pos, size=bubble.size)

        bubble.bind(pos=self._update_rect, size=self._update_rect)

        msg_label = Label(
            text=text,
            font_size=14,
            text_size=(340, None),
            halign="left",
            valign="top",
        )
        msg_label.bind(texture_size=msg_label.setter("size"))
        # Guard: texture_size may not be computed yet on first frame
        if msg_label.texture_size[1] > 0:
            msg_label.height = msg_label.texture_size[1] + 20
        else:
            msg_label.height = 40  # reasonable default until texture computes

        bubble.add_widget(msg_label)
        bubble.height = msg_label.height + 20

        msg_layout.add_widget(bubble)
        msg_layout.height = bubble.height

        self.chat_layout.add_widget(msg_layout)

        if return_label:
            return msg_label

    def _update_rect(self, instance, value):
        instance.rect.pos = instance.pos
        instance.rect.size = instance.size

    def _get_ai_response_worker(self, query: str):
        app = App.get_running_app()
        services = app.services
        response_text = ""
        try:
            prompt, _sources = services.build_tutor_prompt(query)
            first_token = True
            for token in services.generate_stream(prompt):
                response_text += token
                if first_token:
                    first_token = False
                    Clock.schedule_once(lambda dt: self._cancel_typing_animation())
                Clock.schedule_once(lambda dt, t=response_text: self._update_ai_label(t))
        except Exception as e:
            response_text = f"Error: {str(e)}"
            Clock.schedule_once(lambda dt: self._cancel_typing_animation())
            Clock.schedule_once(lambda dt, t=response_text: self._update_ai_label(t))

        Clock.schedule_once(lambda dt: self._on_ai_complete())

    def _update_ai_label(self, text):
        if self.current_ai_label:
            self.current_ai_label.text = text
            # Guard: texture_size may be (0,0) if label hasn't rendered yet
            tex_h = self.current_ai_label.texture_size[1]
            if tex_h > 0:
                self.current_ai_label.height = tex_h + 20
                bubble = self.current_ai_label.parent
                if bubble:
                    bubble.height = self.current_ai_label.height + 20
                    msg_layout = bubble.parent
                    if msg_layout:
                        msg_layout.height = bubble.height

    def _on_ai_complete(self):
        self._generating = False
        self.send_btn.disabled = False
        self.current_ai_label = None

    def go_back(self, instance):
        self.manager.current = "dashboard"
