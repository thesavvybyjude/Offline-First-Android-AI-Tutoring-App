"""
Kivy Main Application
Entry point for the AI Tutoring Android App
"""

import os
import sys

from kivy.app import App
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager
from kivy.utils import platform as kivy_platform

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from frontend.app_services import AppServices
from frontend.screens.login_screen import LoginScreen
from frontend.screens.dashboard_screen import DashboardScreen
from frontend.screens.tutor_chat_screen import TutorChatScreen
from frontend.screens.review_screen import ReviewScreen
from frontend.screens.settings_screen import SettingsScreen


class TutorApp(App):
    """Main Kivy application for AI Tutor"""

    def build(self):
        if kivy_platform not in ("android", "ios"):
            Window.size = (360, 640)
        Window.title = "AI Tutor"

        self.services = AppServices(user_data_dir=self.user_data_dir)
        self.student_id = None
        self.school_code = None
        self.offline_mode = True
        self.ai_status = "Starting…"

        sm = ScreenManager()
        sm.add_widget(LoginScreen(name="login"))
        sm.add_widget(DashboardScreen(name="dashboard"))
        sm.add_widget(TutorChatScreen(name="tutor_chat"))
        sm.add_widget(ReviewScreen(name="review"))
        sm.add_widget(SettingsScreen(name="settings"))
        return sm

    def bootstrap_student(self, student_id: str, name: str, school_code: str = "") -> None:
        self.student_id = student_id
        self.school_code = school_code
        self.ai_status = "Loading AI…"

        def on_ai_ready(ok: bool, err: str | None):
            self.ai_status = self.services.ai_status_message()
            if hasattr(self, "root") and self.root.current == "dashboard":
                screen = self.root.get_screen("dashboard")
                if hasattr(screen, "_update_ai_status"):
                    screen._update_ai_status()

        self.services.bootstrap_student(
            student_id=student_id,
            name=name or student_id,
            grade_level="SS2",
            school_id=school_code or None,
            on_ai_ready=on_ai_ready,
        )


if __name__ == "__main__":
    TutorApp().run()
