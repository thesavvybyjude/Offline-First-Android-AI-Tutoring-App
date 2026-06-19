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
from pathlib import Path
from kivy.app import App
from backend.sm2_scheduler import SM2Scheduler

try:
    from kivy_garden.graph import Graph, BarPlot
    HAS_GRAPH = True
except ImportError:
    HAS_GRAPH = False


class DashboardScreen(Screen):
    """Dashboard screen showing student progress"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'dashboard'
        self.scheduler = SM2Scheduler(Path("data/tutor.db"))
        self.student_id = None
        self._build_ui()
    
    def on_enter(self):
        """Called when screen is entered"""
        app = App.get_running_app()
        # Make sure the database schema exists
        self.scheduler.init_db()
        self.student_id = str(getattr(app, 'student_id', 'stu_001'))
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
        
        # Graph layout
        self.graph_container = BoxLayout(orientation='vertical', size_hint_y=0.3)
        if HAS_GRAPH:
            self.graph = Graph(
                xlabel='Day', ylabel='Reviews', x_ticks_minor=1,
                x_ticks_major=1, y_ticks_major=5,
                y_grid_label=True, x_grid_label=True, padding=5,
                x_grid=True, y_grid=True, xmin=0, xmax=6, ymin=0, ymax=20
            )
            self.bar_plot = BarPlot(color=[0.2, 0.6, 0.8, 1], bar_width=0.5)
            self.graph.add_plot(self.bar_plot)
            self.graph_container.add_widget(self.graph)
        else:
            self.graph_container.add_widget(Label(text="(kivy_garden.graph not installed)"))
            
        layout.add_widget(self.graph_container)
        
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
            streak = self.scheduler.get_streak(self.student_id)
            due = self.scheduler.get_due_count(self.student_id)
            mastered = self.scheduler.get_mastered_count(self.student_id)
            
            # Compute average retention
            retention_stats = self.scheduler.get_retention_stats(self.student_id, days=30)
            total_reviews = sum(r.get('total', 0) for r in retention_stats)
            passed_reviews = sum(r.get('passed', 0) for r in retention_stats)
            
            if total_reviews > 0:
                retention_pct = int((passed_reviews / total_reviews) * 100)
            else:
                retention_pct = 100 # Default if no reviews yet
            
            self.streak_label.text = f'Streak: {streak} days'
            self.due_label.text = f'Due Today: {due}'
            self.retention_label.text = f'Retention: {retention_pct}%'
            self.mastered_label.text = f'Mastered: {mastered}'
            
            # Update graph
            if HAS_GRAPH:
                stats_7d = self.scheduler.get_retention_stats(self.student_id, days=7)
                points = []
                max_y = 5
                # Fill 7 days
                for i in range(7):
                    # We could map real dates to X, but for simplicity we use 0-6
                    if i < len(stats_7d):
                        val = stats_7d[i].get('total', 0)
                        points.append((i, val))
                        max_y = max(max_y, val)
                    else:
                        points.append((i, 0))
                
                self.bar_plot.points = points
                self.graph.ymax = ((max_y // 5) + 1) * 5
                
        except Exception as e:
            print(f"Error updating stats: {e}")
            self.streak_label.text = 'Streak: 0 days'
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
