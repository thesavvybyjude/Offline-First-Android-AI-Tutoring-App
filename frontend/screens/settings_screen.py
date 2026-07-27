"""
Settings Screen
App configuration and student preferences
"""

import sys
import os

from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import ButtonBehavior
from kivy.uix.switch import Switch
from kivy.uix.slider import Slider
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Rectangle, RoundedRectangle, Line
from kivy.metrics import dp

from frontend.theme import get_color, get_font, RADIUS
from frontend.widgets.top_bar import TopBar
from frontend.widgets.glass_card import GlassCard
from frontend.widgets.gradient_button import GradientButton

class StyledTextInput(TextInput):
    def __init__(self, **kwargs):
        kwargs['background_color'] = get_color("transparent")
        kwargs['foreground_color'] = get_color("on-surface")
        kwargs['cursor_color'] = get_color("primary")
        kwargs['padding'] = ['16dp', '16dp']
        kwargs['multiline'] = False
        kwargs['size_hint_y'] = None
        kwargs['height'] = '56dp'
        font = get_font("body-lg")
        kwargs['font_name'] = font["font_name"]
        kwargs['font_size'] = font["font_size"]
        super().__init__(**kwargs)
        self.bind(pos=self._update_canvas, size=self._update_canvas, focus=self._update_canvas)

    def _update_canvas(self, *args):
        from kivy.clock import Clock
        Clock.schedule_once(self._deferred_update_canvas, -1)

    def _deferred_update_canvas(self, dt):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*get_color("surface-container-high"))
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(12)])
            
            if self.focus:
                Color(*get_color("primary"))
                Line(rounded_rectangle=(self.x, self.y, self.width, self.height, dp(12)), width=1.5)
            else:
                Color(*get_color("outline-variant"))
                Line(rounded_rectangle=(self.x, self.y, self.width, self.height, dp(12)), width=1)


class SecondaryButton(ButtonBehavior, BoxLayout):
    def __init__(self, text="", **kwargs):
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = '48dp'
        super().__init__(**kwargs)
        self.bind(pos=self._update_canvas, size=self._update_canvas, state=self._update_canvas)
        
        font = get_font("label-lg")
        lbl = Label(text=text, color=get_color("error"), font_name=font["font_name"], font_size=font["font_size"], bold=True)
        self.add_widget(lbl)

    def _update_canvas(self, *args):
        from kivy.clock import Clock
        Clock.schedule_once(self._deferred_update_canvas, -1)

    def _deferred_update_canvas(self, dt):
        self.canvas.before.clear()
        with self.canvas.before:
            if self.state == 'down':
                Color(*get_color("error")[:3] + (0.2,))
            else:
                Color(*get_color("transparent"))
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(24)])
            
            Color(*get_color("error"))
            Line(rounded_rectangle=(self.x, self.y, self.width, self.height, dp(24)), width=1)


class SettingsScreen(Screen):
    """Premium settings screen"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "settings"
        self.student_id = None
        self.student_data = None
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
        raw_id = getattr(app, "student_id", None) or getattr(app.services, "student_id", None)
        self.student_id = str(raw_id) if raw_id else None
        self._load_student_data()
        self._update_storage_usage()

    def _build_ui(self):
        main_layout = BoxLayout(orientation='vertical')
        
        # Top Bar
        top_bar = TopBar(title="Settings")
        main_layout.add_widget(top_bar)
        
        # Scrollable content
        scroll = ScrollView(do_scroll_x=False, do_scroll_y=True)
        content = BoxLayout(orientation='vertical', padding=['16dp', '24dp', '16dp', '80dp'], spacing='24dp', size_hint_y=None)
        content.bind(minimum_height=content.setter('height'))

        font_lbl = get_font("label-md")
        font_val = get_font("body-lg")

        # 1. Profile Section
        profile_card = GlassCard(orientation='vertical', spacing='16dp', size_hint_y=None)
        profile_card.bind(minimum_height=profile_card.setter('height'))
        
        lbl_profile = Label(text="PROFILE", color=get_color("primary"), font_name=font_lbl["font_name"], font_size=font_lbl["font_size"], bold=True, size_hint_y=None, height='24dp', halign='left')
        lbl_profile.bind(size=lbl_profile.setter('text_size'))
        profile_card.add_widget(lbl_profile)

        # Name
        self.name_input = StyledTextInput(hint_text="Your name")
        profile_card.add_widget(self.name_input)
        
        # Subject
        self.subject_input = StyledTextInput(hint_text="Subject Focus (e.g. Biology)")
        profile_card.add_widget(self.subject_input)
        
        content.add_widget(profile_card)

        # 2. Preferences Section
        pref_card = GlassCard(orientation='vertical', spacing='16dp', size_hint_y=None)
        pref_card.bind(minimum_height=pref_card.setter('height'))
        
        lbl_pref = Label(text="PREFERENCES", color=get_color("primary"), font_name=font_lbl["font_name"], font_size=font_lbl["font_size"], bold=True, size_hint_y=None, height='24dp', halign='left')
        lbl_pref.bind(size=lbl_pref.setter('text_size'))
        pref_card.add_widget(lbl_pref)

        # Daily Limit
        limit_box = BoxLayout(orientation='horizontal', size_hint_y=None, height='48dp')
        lbl_limit = Label(text="Daily Review Limit", color=get_color("on-surface"), font_name=font_val["font_name"], font_size=font_val["font_size"], halign='left')
        lbl_limit.bind(size=lbl_limit.setter('text_size'))
        self.limit_value_label = Label(text="20", color=get_color("on-surface-variant"), font_name=font_val["font_name"], font_size=font_val["font_size"], size_hint_x=0.2, halign='right')
        self.limit_value_label.bind(size=self.limit_value_label.setter('text_size'))
        limit_box.add_widget(lbl_limit)
        limit_box.add_widget(self.limit_value_label)
        pref_card.add_widget(limit_box)
        
        self.limit_slider = Slider(min=5, max=50, value=20, step=5, size_hint_y=None, height='32dp')
        self.limit_slider.bind(value=self._update_limit_label)
        pref_card.add_widget(self.limit_slider)

        # Auto Sync
        sync_box = BoxLayout(orientation='horizontal', size_hint_y=None, height='48dp')
        lbl_sync = Label(text="Auto-Sync (Coming Soon)", color=get_color("on-surface"), font_name=font_val["font_name"], font_size=font_val["font_size"], halign='left')
        lbl_sync.bind(size=lbl_sync.setter('text_size'))
        self.sync_switch = Switch(active=False, disabled=True, size_hint_x=0.3)
        sync_box.add_widget(lbl_sync)
        sync_box.add_widget(self.sync_switch)
        pref_card.add_widget(sync_box)

        content.add_widget(pref_card)

        # 3. System Section
        sys_card = GlassCard(orientation='vertical', spacing='16dp', size_hint_y=None)
        sys_card.bind(minimum_height=sys_card.setter('height'))
        
        lbl_sys = Label(text="SYSTEM", color=get_color("primary"), font_name=font_lbl["font_name"], font_size=font_lbl["font_size"], bold=True, size_hint_y=None, height='24dp', halign='left')
        lbl_sys.bind(size=lbl_sys.setter('text_size'))
        sys_card.add_widget(lbl_sys)

        # Storage
        storage_box = BoxLayout(orientation='horizontal', size_hint_y=None, height='48dp')
        lbl_storage = Label(text="Storage Usage", color=get_color("on-surface"), font_name=font_val["font_name"], font_size=font_val["font_size"], halign='left')
        lbl_storage.bind(size=lbl_storage.setter('text_size'))
        self.storage_value_label = Label(text="0 MB", color=get_color("on-surface-variant"), font_name=font_val["font_name"], font_size=font_val["font_size"], size_hint_x=0.4, halign='right')
        self.storage_value_label.bind(size=self.storage_value_label.setter('text_size'))
        storage_box.add_widget(lbl_storage)
        storage_box.add_widget(self.storage_value_label)
        sys_card.add_widget(storage_box)

        # Clear Cache Button
        clear_btn = SecondaryButton(text="Clear Cache")
        clear_btn.bind(on_release=self.clear_cache)
        sys_card.add_widget(clear_btn)

        content.add_widget(sys_card)

        # 4. Developer Section
        dev_card = GlassCard(orientation='vertical', spacing='16dp', size_hint_y=None)
        dev_card.bind(minimum_height=dev_card.setter('height'))
        
        lbl_dev = Label(text="DEVELOPER INFO", color=get_color("primary"), font_name=font_lbl["font_name"], font_size=font_lbl["font_size"], bold=True, size_hint_y=None, height='24dp', halign='left')
        lbl_dev.bind(size=lbl_dev.setter('text_size'))
        dev_card.add_widget(lbl_dev)

        dev_info_box = BoxLayout(orientation='vertical', size_hint_y=None, height='48dp', spacing='4dp')
        dev_text1 = Label(text="Developed by ZIDON", color=get_color("on-surface"), font_name=font_val["font_name"], font_size=font_val["font_size"], halign='left', bold=True)
        dev_text1.bind(size=dev_text1.setter('text_size'))
        dev_text2 = Label(text="Offline AI Tutor v1.0", color=get_color("on-surface-variant"), font_name=font_lbl["font_name"], font_size=font_lbl["font_size"], halign='left')
        dev_text2.bind(size=dev_text2.setter('text_size'))
        dev_info_box.add_widget(dev_text1)
        dev_info_box.add_widget(dev_text2)
        dev_card.add_widget(dev_info_box)

        content.add_widget(dev_card)

        # Save Button
        save_btn = GradientButton(text="Save Settings", size_hint_y=None, height='56dp')
        save_btn.bind(on_release=self.save_settings)
        content.add_widget(save_btn)

        scroll.add_widget(content)
        main_layout.add_widget(scroll)
        self.add_widget(main_layout)

    def _load_student_data(self):
        app = App.get_running_app()
        scheduler = app.services.scheduler
        if not scheduler:
            self.student_data = {}
            return
        try:
            self.student_data = scheduler.get_student(self.student_id)
            if self.student_data:
                self.name_input.text = self.student_data.get("name", "")
            else:
                self.name_input.text = ""
                self.student_data = {}
        except Exception as e:
            print(f"Error loading student data: {e}")
            self.student_data = {}

    def _update_limit_label(self, instance, value):
        self.limit_value_label.text = f"{int(value)}"

    def _update_storage_usage(self):
        app = App.get_running_app()
        data_dir = app.services.data_dir
        models_dir = app.services.models_dir

        total_size = 0
        for directory in [data_dir, models_dir]:
            if directory.exists():
                for root, _dirs, files in os.walk(directory):
                    for file in files:
                        try:
                            total_size += os.path.getsize(os.path.join(root, file))
                        except OSError:
                            pass  # File deleted mid-walk or permission error

        size_mb = total_size / (1024 * 1024)
        self.storage_value_label.text = f"{size_mb:.1f} MB used"

    def clear_cache(self, instance):
        print("Cache clear not implemented")
        self._update_storage_usage()

    def save_settings(self, instance):
        app = App.get_running_app()
        scheduler = app.services.scheduler
        if not scheduler:
            return
        try:
            name = self.name_input.text.strip()
            if name:
                grade_level = self.student_data.get("grade_level", "SS2")
                school_id = self.student_data.get("school_id", None)
                scheduler.upsert_student(self.student_id, name, grade_level, school_id)
                # update global app var
                app.student_name = name
            self.go_back(None)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def go_back(self, instance):
        self.manager.current = "dashboard"
