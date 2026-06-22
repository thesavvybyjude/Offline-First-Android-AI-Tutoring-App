"""
Tutor Chat Screen
Premium AI tutoring interface with on-device streaming responses
"""

import sys
import os
import threading

from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import ButtonBehavior
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.properties import ObjectProperty
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle, RoundedRectangle, Line
from kivy.metrics import dp

from frontend.theme import get_color, get_font, RADIUS
from frontend.widgets.top_bar import TopBar
from frontend.widgets.chat_bubble import ChatBubble

class IconButton(ButtonBehavior, BoxLayout):
    def __init__(self, icon=">", icon_color=None, bg_color=None, **kwargs):
        self.orientation = 'horizontal'
        self.size_hint = (None, None)
        self.size = ('40dp', '40dp')
        super().__init__(**kwargs)
        
        self.icon_color = icon_color or get_color("on-surface-variant")
        self.bg_color = bg_color or get_color("transparent")
        
        self.bind(pos=self._update_canvas, size=self._update_canvas, state=self._update_canvas)
        
        lbl = Label(text=icon, color=self.icon_color, font_size='24sp', bold=True)
        self.add_widget(lbl)

    def _update_canvas(self, *args):
        from kivy.clock import Clock
        Clock.schedule_once(self._deferred_update_canvas, -1)

    def _deferred_update_canvas(self, dt):
        self.canvas.before.clear()
        with self.canvas.before:
            r, g, b, a = self.bg_color
            if self.state == 'down':
                Color(r, g, b, min(1.0, a + 0.2)) # Slightly more opaque when pressed
            else:
                Color(r, g, b, a)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(8)])

class ChipButton(ButtonBehavior, BoxLayout):
    def __init__(self, text="", **kwargs):
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = '32dp'
        self.size_hint_x = None
        self.padding = ['12dp', '4dp']
        super().__init__(**kwargs)
        self.bind(pos=self._update_canvas, size=self._update_canvas, state=self._update_canvas)
        
        font = get_font("label-sm")
        self.lbl = Label(text=text, color=get_color("on-surface"), font_name=font["font_name"], font_size=font["font_size"])
        self.lbl.bind(texture_size=self._update_width)
        self.add_widget(self.lbl)

    def _update_width(self, instance, value):
        self.width = value[0] + dp(24) # Add padding

    def _update_canvas(self, *args):
        from kivy.clock import Clock
        Clock.schedule_once(self._deferred_update_canvas, -1)

    def _deferred_update_canvas(self, dt):
        self.canvas.before.clear()
        with self.canvas.before:
            if self.state == 'down':
                Color(*get_color("surface-variant"))
            else:
                Color(*get_color("surface-container-high"))
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(16)])
            Color(*get_color("outline-variant"))
            Line(rounded_rectangle=(self.x, self.y, self.width, self.height, dp(16)), width=1)


class TutorChatScreen(Screen):
    """Premium tutor chat screen"""

    chat_layout = ObjectProperty(None)
    message_input = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "tutor_chat"
        self.current_ai_bubble = None
        self.typing_event = None
        self.typing_dots = 1
        self._generating = False
        self._shown_loading_msg = False
        self._ai_ready_event = None
        
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
        if not app.services.is_ai_ready() and not app.services._loading:
            app.services.load_ai_async(self._on_ai_reload)

    def on_leave(self, *args):
        self._cancel_typing_animation()
        self._cancel_ai_ready_check()

    def _on_ai_reload(self, ok: bool, err):
        app = App.get_running_app()
        app.ai_status = app.services.ai_status_message()
        if ok:
            self.send_btn.disabled = False
            self._add_message("AI is ready! Send your question.", is_user=False)
            self._shown_loading_msg = False
            self._cancel_ai_ready_check()

    def _schedule_ai_ready_check(self):
        if self._ai_ready_event is not None:
            return
        def _check(dt):
            app = App.get_running_app()
            if app.services.is_ai_ready():
                self.send_btn.disabled = False
                self._add_message("AI is ready! Send your question.", is_user=False)
                self._shown_loading_msg = False
                self._cancel_ai_ready_check()
        self._ai_ready_event = Clock.schedule_interval(_check, 2.0)

    def _cancel_ai_ready_check(self):
        if self._ai_ready_event is not None:
            self._ai_ready_event.cancel()
            self._ai_ready_event = None

    def _build_ui(self):
        main_layout = BoxLayout(orientation='vertical')
        
        # Top Bar
        top_bar = TopBar(title="OFFLINE AI TUTOR")
        main_layout.add_widget(top_bar)
        
        # Sub-header (Subject Selection)
        sub_head = BoxLayout(orientation='horizontal', size_hint_y=None, height='40dp', padding=['16dp', '0dp'], spacing='8dp')
        
        self.btn_english = ChipButton(text="English")
        self.btn_biology = ChipButton(text="Biology")
        
        sub_head.add_widget(self.btn_biology)
        sub_head.add_widget(self.btn_english)
        sub_head.add_widget(BoxLayout(size_hint_x=1)) # spacer
        main_layout.add_widget(sub_head)

        # Chat Area
        scroll = ScrollView(size_hint_y=1, do_scroll_x=False, bar_width='4dp')
        self.chat_layout = GridLayout(cols=1, spacing='16dp', padding=['16dp', '16dp', '16dp', '24dp'], size_hint_y=None)
        self.chat_layout.bind(minimum_height=self.chat_layout.setter('height'))
        
        # Date Divider
        date_box = AnchorLayout(anchor_x='center', size_hint_y=None, height='24dp')
        font = get_font("label-sm")
        date_lbl = Label(text="Today", color=get_color("on-surface-variant"), font_name=font["font_name"], 
                        font_size=font["font_size"], size_hint=(None, 1), padding=['12dp', '0dp'])
        date_lbl.bind(texture_size=date_lbl.setter('size'))
        with date_lbl.canvas.before:
            Color(*get_color("surface-container-high"))
            date_bg = RoundedRectangle(pos=date_lbl.pos, size=date_lbl.size, radius=[dp(12)])
        def update_date_bg(instance, value):
            date_bg.pos = instance.pos
            date_bg.size = instance.size
        date_lbl.bind(pos=update_date_bg, size=update_date_bg)
        date_box.add_widget(date_lbl)
        self.chat_layout.add_widget(date_box)
        
        scroll.add_widget(self.chat_layout)
        main_layout.add_widget(scroll)

        # Bottom Input Area
        input_container = BoxLayout(orientation='vertical', size_hint_y=None, height='120dp', padding=['16dp', '8dp', '16dp', '16dp'])
        with input_container.canvas.before:
            Color(*get_color("surface")[:3] + (0.9,)) # 90% opaque background
            ic_rect = Rectangle(pos=input_container.pos, size=input_container.size)
            Color(*get_color("outline-variant"))
            ic_line = Line(rectangle=(input_container.x, input_container.top-1, input_container.width, 1), width=1)
        def update_input_bg(instance, value):
            ic_rect.pos = instance.pos
            ic_rect.size = instance.size
            ic_line.rectangle = (instance.x, instance.top-1, instance.width, 1)
        input_container.bind(pos=update_input_bg, size=update_input_bg)
        
        # Suggested Prompts (Scrollable row)
        prompt_scroll = ScrollView(size_hint_y=None, height='40dp', do_scroll_y=False)
        self.prompt_box = BoxLayout(orientation='horizontal', size_hint_x=None, spacing='8dp', padding=['0dp', '4dp'])
        self.prompt_box.bind(minimum_width=self.prompt_box.setter('width'))
        prompt_scroll.add_widget(self.prompt_box)
        input_container.add_widget(prompt_scroll)
        
        # Subject selection logic
        self.btn_english.bind(on_release=lambda x: self._select_subject("English"))
        self.btn_biology.bind(on_release=lambda x: self._select_subject("Biology"))
        self._select_subject("Biology") # Default subject
        
        # Input Box
        input_row = BoxLayout(orientation='horizontal', size_hint_y=None, height='56dp', spacing='8dp', padding=['4dp'])
        with input_row.canvas.before:
            Color(*get_color("user-bubble"))
            ir_rect = RoundedRectangle(pos=input_row.pos, size=input_row.size, radius=[dp(12)])
            Color(*get_color("surface-bright"))
            ir_line = Line(rounded_rectangle=(input_row.x, input_row.y, input_row.width, input_row.height, dp(12)), width=1)
        def update_input_row_bg(instance, value):
            ir_rect.pos = instance.pos
            ir_rect.size = instance.size
            ir_line.rounded_rectangle = (instance.x, instance.y, instance.width, instance.height, dp(12))
        input_row.bind(pos=update_input_row_bg, size=update_input_row_bg)
        
        attach_btn = IconButton(icon="+", icon_color=get_color("on-surface-variant"))
        input_row.add_widget(attach_btn)
        
        font = get_font("body-md")
        self.message_input = TextInput(
            hint_text="Ask a question...",
            multiline=True, # Auto-growing theoretically, but fixed height here for simplicity
            background_color=get_color("transparent"),
            foreground_color=get_color("on-surface"),
            cursor_color=get_color("primary"),
            font_name=font["font_name"],
            font_size=font["font_size"],
            padding=['16dp', '10dp']
        )
        input_row.add_widget(self.message_input)
        
        self.send_btn = IconButton(icon="^", icon_color=get_color("on-primary"), bg_color=get_color("primary"))
        self.send_btn.bind(on_release=self.send_message)
        input_row.add_widget(self.send_btn)
        
        input_container.add_widget(input_row)
        
        # Disclaimer
        disc_font = get_font("label-sm")
        disc = Label(text="Offline AI Tutor can make mistakes. Check important academic facts.",
                    color=get_color("on-surface-variant"), font_name=disc_font["font_name"],
                    font_size=dp(10), size_hint_y=None, height='16dp')
        input_container.add_widget(disc)
        
        main_layout.add_widget(input_container)
        self.add_widget(main_layout)

        self._add_message(
            "Hello! Ask me anything about your curriculum. "
            "If AI is still loading, wait a moment and try again.",
            is_user=False,
        )

    def _select_subject(self, subject):
        self.active_subject = subject
        
        # Update chip visuals
        self.btn_biology.state = 'down' if subject == 'Biology' else 'normal'
        self.btn_english.state = 'down' if subject == 'English' else 'normal'
        self.btn_biology._update_canvas()
        self.btn_english._update_canvas()
        
        # Update prompts
        self.prompt_box.clear_widgets()
        if subject == "Biology":
            prompts = ["Explain Photosynthesis", "What factors affect it?", "Give me a quiz"]
        else:
            prompts = ["What is a Noun?", "How to write an Essay?", "Give me a reading test"]
            
        for p in prompts:
            btn = ChipButton(text=p)
            btn.bind(on_release=lambda instance, text=p: self._set_and_send(text))
            self.prompt_box.add_widget(btn)

    def _update_date_bg(self, instance):
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(*get_color("surface-container-high"))
            RoundedRectangle(pos=instance.pos, size=instance.size, radius=[dp(12)])

    def _update_input_bg(self, instance, value):
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(*get_color("surface")[:3] + (0.9,))
            Rectangle(pos=instance.pos, size=instance.size)
            Color(*get_color("outline-variant"))
            Line(rectangle=(instance.x, instance.top-1, instance.width, 1), width=1)
            
    def _update_input_row_bg(self, instance, value):
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(*get_color("user-bubble"))
            RoundedRectangle(pos=instance.pos, size=instance.size, radius=[dp(12)])
            Color(*get_color("surface-bright"))
            Line(rounded_rectangle=(instance.x, instance.y, instance.width, instance.height, dp(12)), width=1)

    def _set_and_send(self, text):
        if not self.send_btn.disabled:
            self.message_input.text = text
            self.send_message(None)

    def send_message(self, instance):
        query = self.message_input.text.strip()
        if not query:
            return

        app = App.get_running_app()
        if not app.services.is_ai_ready():
            if not self._shown_loading_msg:
                status = app.services.ai_status_message()
                if app.services._loading:
                    msg = status + "\nPlease wait — Send will enable when ready."
                elif app.services.downloader.model_exists():
                    msg = status + "\nModel found — loading, please wait."
                    app.services.load_ai_async(self._on_ai_reload)
                else:
                    msg = status + "\nRun setup_env.py to download a model."
                self._add_message(msg, is_user=False)
                self._shown_loading_msg = True

            self.send_btn.disabled = True
            self._schedule_ai_ready_check()
            return

        self.message_input.text = ""
        self._add_message(query, is_user=True)
        self.send_btn.disabled = True
        self._generating = True

        self.current_ai_bubble = self._add_message("...", is_user=False)
        self.typing_dots = 1
        self.typing_event = Clock.schedule_interval(self._animate_typing, 0.5)

        threading.Thread(target=self._get_ai_response_worker, args=(query,), daemon=True).start()

    def _animate_typing(self, dt):
        self.typing_dots = (self.typing_dots % 3) + 1
        if self.current_ai_bubble:
            self.current_ai_bubble.text = "." * self.typing_dots

    def _cancel_typing_animation(self):
        if self.typing_event is not None:
            self.typing_event.cancel()
            self.typing_event = None

    def _add_message(self, text: str, is_user: bool = False):
        # Anchor box to align left or right
        anchor = AnchorLayout(anchor_x='right' if is_user else 'left', size_hint_y=None)
        
        # We wrap in another box to limit max width (approx 85% of screen)
        # For simplicity, we just use padding on the anchor to prevent spanning full width
        pad_x = ['64dp', '0dp'] if is_user else ['0dp', '32dp']
        anchor.padding = pad_x
        
        bubble = ChatBubble(text=text, is_user=is_user)
        # Bind height of anchor to height of bubble
        bubble.bind(height=anchor.setter('height'))
        
        anchor.add_widget(bubble)
        self.chat_layout.add_widget(anchor)
        
        # Scroll to bottom
        Clock.schedule_once(lambda dt: self._scroll_to_bottom(), 0.1)
        
        return bubble

    def _scroll_to_bottom(self):
        # Assuming the parent of chat_layout is the ScrollView
        scrollview = self.chat_layout.parent
        if isinstance(scrollview, ScrollView):
            scrollview.scroll_y = 0

    def _get_ai_response_worker(self, query: str):
        app = App.get_running_app()
        services = app.services
        response_text = ""
        try:
            subject = getattr(self, 'active_subject', 'Biology')
            prompt, _sources = services.build_tutor_prompt(query, subject=subject)
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
        if self.current_ai_bubble:
            self.current_ai_bubble.text = text
            Clock.schedule_once(lambda dt: self._scroll_to_bottom(), 0.1)

    def _on_ai_complete(self):
        self._generating = False
        self.send_btn.disabled = False
        self.current_ai_bubble = None

    def go_back(self, instance):
        self.manager.current = "dashboard"

