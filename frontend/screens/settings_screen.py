"""
Settings Screen
App configuration and student preferences
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.switch import Switch
from kivy.uix.slider import Slider
from kivy.properties import ObjectProperty
from backend.database import DatabaseManager


class SettingsScreen(Screen):
    """Settings screen for app configuration"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'settings'
        self.db = DatabaseManager()
        self.student_id = None
        self._build_ui()
    
    def on_enter(self):
        """Called when screen is entered"""
        app = self.manager.app
        self.student_id = getattr(app, 'student_id', 1)
        self._load_student_data()
    
    def _build_ui(self):
        """Build the settings UI"""
        # Main layout
        layout = BoxLayout(orientation='vertical', padding=15, spacing=15)
        
        # Header
        header = BoxLayout(orientation='horizontal', size_hint_y=0.08)
        back_btn = Button(text='←', size_hint_x=0.1, font_size=24)
        back_btn.bind(on_press=self.go_back)
        header_label = Label(text='Settings', font_size=24, bold=True)
        header.add_widget(back_btn)
        header.add_widget(header_label)
        layout.add_widget(header)
        
        # Student name
        name_layout = BoxLayout(orientation='vertical', size_hint_y=0.12)
        name_label = Label(text='Student Name', font_size=14, halign='left')
        self.name_input = TextInput(
            hint_text='Your name',
            multiline=False,
            font_size=16
        )
        name_layout.add_widget(name_label)
        name_layout.add_widget(self.name_input)
        layout.add_widget(name_layout)
        
        # Subject focus
        subject_layout = BoxLayout(orientation='vertical', size_hint_y=0.12)
        subject_label = Label(text='Subject Focus', font_size=14, halign='left')
        self.subject_input = TextInput(
            hint_text='English, Biology, etc.',
            multiline=False,
            font_size=16
        )
        subject_layout.add_widget(subject_label)
        subject_layout.add_widget(self.subject_input)
        layout.add_widget(subject_layout)
        
        # Daily review limit
        limit_layout = BoxLayout(orientation='vertical', size_hint_y=0.12)
        limit_label = Label(text='Daily Review Limit', font_size=14, halign='left')
        self.limit_slider = Slider(min=5, max=50, value=20, step=5)
        self.limit_value_label = Label(text='20 cards/day', font_size=14)
        self.limit_slider.bind(value=self._update_limit_label)
        limit_layout.add_widget(limit_label)
        limit_layout.add_widget(self.limit_slider)
        limit_layout.add_widget(self.limit_value_label)
        layout.add_widget(limit_layout)
        
        # Auto-sync toggle
        sync_layout = BoxLayout(orientation='horizontal', size_hint_y=0.1)
        sync_label = Label(text='Auto-Sync', font_size=16)
        self.sync_switch = Switch(active=True)
        sync_layout.add_widget(sync_label)
        sync_layout.add_widget(self.sync_switch)
        layout.add_widget(sync_layout)
        
        # Storage usage
        storage_layout = BoxLayout(orientation='vertical', size_hint_y=0.1)
        storage_label = Label(text='Storage Usage', font_size=14, halign='left')
        self.storage_value_label = Label(text='0 MB / 2.1 GB', font_size=14)
        storage_layout.add_widget(storage_label)
        storage_layout.add_widget(self.storage_value_label)
        layout.add_widget(storage_layout)
        
        # Clear cache button
        clear_btn = Button(
            text='Clear Cache',
            font_size=16,
            size_hint_y=0.1,
            background_color=(0.8, 0.4, 0.2, 1)
        )
        clear_btn.bind(on_press=self.clear_cache)
        layout.add_widget(clear_btn)
        
        # Save button
        save_btn = Button(
            text='Save Settings',
            font_size=18,
            size_hint_y=0.12,
            background_color=(0.2, 0.6, 0.8, 1)
        )
        save_btn.bind(on_press=self.save_settings)
        layout.add_widget(save_btn)
        
        # Spacer
        layout.add_widget(Label(size_hint_y=0.1))
        
        self.add_widget(layout)
    
    def _load_student_data(self):
        """Load student data from database"""
        try:
            student = self.db.get_student(self.student_id)
            if student:
                self.name_input.text = student.get('name', '')
        except Exception as e:
            print(f"Error loading student data: {e}")
    
    def _update_limit_label(self, instance, value):
        """Update limit label when slider changes"""
        self.limit_value_label.text = f'{int(value)} cards/day'
    
    def _update_storage_usage(self):
        """Update storage usage display"""
        # Calculate storage usage
        import os
        data_dir = "data"
        models_dir = "models"
        
        total_size = 0
        for directory in [data_dir, models_dir]:
            if os.path.exists(directory):
                for root, dirs, files in os.walk(directory):
                    for file in files:
                        file_path = os.path.join(root, file)
                        total_size += os.path.getsize(file_path)
        
        # Convert to MB
        size_mb = total_size / (1024 * 1024)
        self.storage_value_label.text = f'{size_mb:.1f} MB / 2.1 GB'
    
    def clear_cache(self, instance):
        """Clear cache data"""
        # Placeholder for cache clearing logic
        print("Cache cleared")
        self._update_storage_usage()
    
    def save_settings(self, instance):
        """Save settings to database"""
        try:
            # Update student name
            name = self.name_input.text.strip()
            if name:
                conn = self.db.connect()
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE students SET name=? WHERE id=?",
                    (name, self.student_id)
                )
                conn.commit()
            
            print("Settings saved")
            self.go_back(None)
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def go_back(self, instance):
        """Return to dashboard"""
        self.manager.current = 'dashboard'
