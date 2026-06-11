"""
Kivy Main Application
Entry point for the AI Tutoring Android App
"""

import os
import sys
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.core.window import Window
from kivy.config import Config

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from frontend.screens.login_screen import LoginScreen
from frontend.screens.dashboard_screen import DashboardScreen
from frontend.screens.tutor_chat_screen import TutorChatScreen
from frontend.screens.review_screen import ReviewScreen
from frontend.screens.settings_screen import SettingsScreen


class TutorApp(App):
    """Main Kivy application for AI Tutor"""
    
    def build(self):
        """Build the application UI"""
        # Configure window
        Window.size = (360, 640)  # Mobile phone size
        Window.title = "AI Tutor"
        
        # Create screen manager
        sm = ScreenManager()
        
        # Add all screens
        sm.add_widget(LoginScreen(name='login'))
        sm.add_widget(DashboardScreen(name='dashboard'))
        sm.add_widget(TutorChatScreen(name='tutor_chat'))
        sm.add_widget(ReviewScreen(name='review'))
        sm.add_widget(SettingsScreen(name='settings'))
        
        return sm
    
    def on_start(self):
        """Called when app starts"""
        print("AI Tutor App started")
    
    def on_stop(self):
        """Called when app stops"""
        print("AI Tutor App stopped")


if __name__ == '__main__':
    TutorApp().run()
