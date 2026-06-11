"""
Dashboard Screen
Shows student progress, streak, and navigation
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
from kivy.graphics import Color, Rectangle
from backend.database import DatabaseManager


class DashboardScreen(Screen):
    """Dashboard screen showing student progress"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'dashboard'
        self.db = DatabaseManager()
        self.student_id = None
        self._build_ui()
    
    def on_enter(self):
        """Called when screen is entered"""
        app = self.manager.app
        self.student_id = getattr(app, 'student_id', 1)
        self._update_stats()
    
    def _build_ui(self):
        """Build the dashboard UI"""
        # Main layout
        layout = BoxLayout(orientation='vertical', padding=15, spacing=15)
        
        # Header
        header = Label(
            text='Dashboard',
            font_size=32,
            size_hint_y=0.1,
            bold=True
        )
        layout.add_widget(header)
        
        # Stats grid
        stats_layout = GridLayout(cols=2, spacing=10, size_hint_y=0.3)
        
        # Streak
        self.streak_label = Label(
            text='Streak: 0 days',
            font_size=18,
            size_hint_y=None,
            height=80
        )
        stats_layout.add_widget(self.streak_label)
        
        # Due today
        self.due_label = Label(
            text='Due Today: 0',
            font_size=18,
            size_hint_y=None,
            height=80
        )
        stats_layout.add_widget(self.due_label)
        
        # Retention
        self.retention_label = Label(
            text='Retention: 0%',
            font_size=18,
            size_hint_y=None,
            height=80
        )
        stats_layout.add_widget(self.retention_label)
        
        # Mastered
        self.mastered_label = Label(
            text='Mastered: 0',
            font_size=18,
            size_hint_y=None,
            height=80
        )
        stats_layout.add_widget(self.mastered_label)
        
        layout.add_widget(stats_layout)
        
        # Action buttons
        actions_layout = BoxLayout(orientation='vertical', spacing=10, size_hint_y=0.4)
        
        # Start review button
        review_btn = Button(
            text='Start Review',
            font_size=20,
            size_hint_y=0.3,
            background_color=(0.2, 0.6, 0.8, 1)
        )
        review_btn.bind(on_press=self.go_to_review)
        actions_layout.add_widget(review_btn)
        
        # Ask tutor button
        tutor_btn = Button(
            text='Ask Tutor',
            font_size=20,
            size_hint_y=0.3,
            background_color=(0.6, 0.2, 0.6, 1)
        )
        tutor_btn.bind(on_press=self.go_to_tutor)
        actions_layout.add_widget(tutor_btn)
        
        # Settings button
        settings_btn = Button(
            text='Settings',
            font_size=18,
            size_hint_y=0.2,
            background_color=(0.5, 0.5, 0.5, 1)
        )
        settings_btn.bind(on_press=self.go_to_settings)
        actions_layout.add_widget(settings_btn)
        
        layout.add_widget(actions_layout)
        
        # Logout button
        logout_btn = Button(
            text='Logout',
            font_size=16,
            size_hint_y=0.1,
            background_color=(0.8, 0.2, 0.2, 1)
        )
        logout_btn.bind(on_press=self.logout)
        layout.add_widget(logout_btn)
        
        self.add_widget(layout)
    
    def _update_stats(self):
        """Update dashboard statistics"""
        try:
            stats = self.db.get_student_stats(self.student_id)
            
            self.streak_label.text = f'Streak: 7 days'  # Placeholder
            self.due_label.text = f'Due Today: {stats["due_today"]}'
            self.retention_label.text = f'Retention: {int(stats["retention"] * 100)}%'
            self.mastered_label.text = f'Mastered: {stats["mastered"]}'
        except Exception as e:
            print(f"Error updating stats: {e}")
            self.due_label.text = 'Due Today: 0'
            self.retention_label.text = 'Retention: 0%'
            self.mastered_label.text = 'Mastered: 0'
    
    def go_to_review(self, instance):
        """Navigate to review screen"""
        self.manager.current = 'review'
    
    def go_to_tutor(self, instance):
        """Navigate to tutor chat screen"""
        self.manager.current = 'tutor_chat'
    
    def go_to_settings(self, instance):
        """Navigate to settings screen"""
        self.manager.current = 'settings'
    
    def logout(self, instance):
        """Logout and return to login screen"""
        self.manager.current = 'login'
