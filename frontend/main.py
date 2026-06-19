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
import subprocess

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
        try:
            server_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend", "server.py")
            self.server_process = subprocess.Popen([sys.executable, server_path])
            print("Flask subprocess launched locally on port 5000.")
        except Exception as e:
            print(f"Failed to launch Flask subprocess: {e}")
    
    def on_stop(self):
        """Called when app stops"""
        if hasattr(self, 'server_process') and self.server_process:
            self.server_process.terminate()
            self.server_process.wait()
        print("AI Tutor App stopped")


if __name__ == '__main__':
    TutorApp().run()
