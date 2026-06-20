"""
Settings Screen
App configuration and student preferences
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.switch import Switch
from kivy.uix.slider import Slider
from kivy.properties import ObjectProperty


class SettingsScreen(Screen):
    """Settings screen for app configuration"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "settings"
        self.student_id = None
        self.student_data = None
        self._build_ui()

    def on_enter(self):
        app = App.get_running_app()
        raw_id = getattr(app, "student_id", None) or getattr(app.services, "student_id", None)
        self.student_id = str(raw_id) if raw_id else None
        self._load_student_data()
        self._update_storage_usage()

    def _build_ui(self):
        layout = BoxLayout(orientation="vertical", padding=15, spacing=15)

        header = BoxLayout(orientation="horizontal", size_hint_y=0.08)
        back_btn = Button(text="←", size_hint_x=0.1, font_size=24)
        back_btn.bind(on_press=self.go_back)
        header_label = Label(text="Settings", font_size=24, bold=True)
        header.add_widget(back_btn)
        header.add_widget(header_label)
        layout.add_widget(header)

        name_layout = BoxLayout(orientation="vertical", size_hint_y=0.12)
        name_label = Label(text="Student Name", font_size=14, halign="left")
        self.name_input = TextInput(hint_text="Your name", multiline=False, font_size=16)
        name_layout.add_widget(name_label)
        name_layout.add_widget(self.name_input)
        layout.add_widget(name_layout)

        subject_layout = BoxLayout(orientation="vertical", size_hint_y=0.12)
        subject_label = Label(text="Subject Focus", font_size=14, halign="left")
        self.subject_input = TextInput(
            hint_text="English, Biology, etc.",
            multiline=False,
            font_size=16,
        )
        subject_layout.add_widget(subject_label)
        subject_layout.add_widget(self.subject_input)
        layout.add_widget(subject_layout)

        limit_layout = BoxLayout(orientation="vertical", size_hint_y=0.12)
        limit_label = Label(text="Daily Review Limit", font_size=14, halign="left")
        self.limit_slider = Slider(min=5, max=50, value=20, step=5)
        self.limit_value_label = Label(text="20 cards/day", font_size=14)
        self.limit_slider.bind(value=self._update_limit_label)
        limit_layout.add_widget(limit_label)
        limit_layout.add_widget(self.limit_slider)
        limit_layout.add_widget(self.limit_value_label)
        layout.add_widget(limit_layout)

        sync_layout = BoxLayout(orientation="horizontal", size_hint_y=0.1)
        sync_label = Label(text="Auto-Sync (coming soon)", font_size=16)
        self.sync_switch = Switch(active=False)
        self.sync_switch.disabled = True
        sync_layout.add_widget(sync_label)
        sync_layout.add_widget(self.sync_switch)
        layout.add_widget(sync_layout)

        storage_layout = BoxLayout(orientation="vertical", size_hint_y=0.1)
        storage_label = Label(text="Storage Usage", font_size=14, halign="left")
        self.storage_value_label = Label(text="0 MB", font_size=14)
        storage_layout.add_widget(storage_label)
        storage_layout.add_widget(self.storage_value_label)
        layout.add_widget(storage_layout)

        clear_btn = Button(
            text="Clear Cache",
            font_size=16,
            size_hint_y=0.1,
            background_color=(0.8, 0.4, 0.2, 1),
        )
        clear_btn.bind(on_press=self.clear_cache)
        layout.add_widget(clear_btn)

        save_btn = Button(
            text="Save Settings",
            font_size=18,
            size_hint_y=0.12,
            background_color=(0.2, 0.6, 0.8, 1),
        )
        save_btn.bind(on_press=self.save_settings)
        layout.add_widget(save_btn)

        layout.add_widget(Label(size_hint_y=0.1))

        self.add_widget(layout)

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
        self.limit_value_label.text = f"{int(value)} cards/day"

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
            self.go_back(None)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def go_back(self, instance):
        self.manager.current = "dashboard"
