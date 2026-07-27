"""
Kivy Main Application

Entry point for the Premium AI Tutoring Android App
"""

import os
import sys

from kivy.app import App
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, FadeTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.utils import platform as kivy_platform
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from frontend.app_services import AppServices
from frontend.theme import get_color
from frontend.screens.login_screen import LoginScreen
from frontend.screens.dashboard_screen import DashboardScreen
from frontend.screens.tutor_chat_screen import TutorChatScreen
from frontend.screens.review_screen import ReviewScreen
from frontend.screens.settings_screen import SettingsScreen
from frontend.widgets.bottom_nav import BottomNav

class RootLayout(AnchorLayout):
    """Main app shell containing ScreenManager and persistent BottomNav, responsive to screen size"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.anchor_x = 'center'
        self.anchor_y = 'center'
        
        self.orientation = 'vertical'
        
        # Wrapper to constrain width on large screens (tablets/desktops)
        self.content_wrapper = BoxLayout(orientation='vertical', size_hint_x=None)
        
        def update_width(instance, value):
            self.content_wrapper.width = min(instance.width, dp(600))
        self.bind(size=update_width)
        
        self.sm = ScreenManager(transition=FadeTransition(duration=0.2))
        self.sm.add_widget(LoginScreen(name="login"))
        self.sm.add_widget(DashboardScreen(name="dashboard"))
        self.sm.add_widget(TutorChatScreen(name="tutor_chat"))
        self.sm.add_widget(ReviewScreen(name="review"))
        self.sm.add_widget(SettingsScreen(name="settings"))
        
        self.nav = BottomNav()
        self.nav.bind(on_tab_select=self.on_nav_tab_select)
        
        # Listen to screen changes to update nav UI
        self.sm.bind(current=self.on_screen_change)
        
        self.content_wrapper.add_widget(self.sm)
        # Nav is not added initially since first screen is login
        
        with self.canvas.before:
            Color(*get_color("background"))
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        def update_bg(instance, value):
            self.bg_rect.pos = instance.pos
            self.bg_rect.size = instance.size
        self.bind(pos=update_bg, size=update_bg)
        
        self.add_widget(self.content_wrapper)

    def on_nav_tab_select(self, instance, tab_id):
        # Map tab ids to screen names
        screen_map = {
            "dashboard": "dashboard",
            "chat": "tutor_chat",
            "review": "review",
            "settings": "settings"
        }
        target = screen_map.get(tab_id)
        if target and self.sm.current != target:
            self.sm.current = target

    def on_screen_change(self, instance, value):
        # Show/Hide Bottom Nav
        if value == "login":
            if self.nav in self.content_wrapper.children:
                self.content_wrapper.remove_widget(self.nav)
        else:
            if self.nav not in self.content_wrapper.children:
                self.content_wrapper.add_widget(self.nav)
                
        # Sync tab active state
        reverse_map = {
            "dashboard": "dashboard",
            "tutor_chat": "chat",
            "review": "review",
            "settings": "settings"
        }
        tab_id = reverse_map.get(value)
        if tab_id:
            self.nav.current_tab = tab_id


class TutorApp(App):
    """Main Kivy application for Premium AI Tutor"""

    def build(self):
        if kivy_platform not in ("android", "ios"):
            Window.size = (360, 640)
        Window.title = "Offline AI Tutor"
        Window.clearcolor = get_color("background")

        self.services = AppServices(user_data_dir=self.user_data_dir)
        self.student_id = None
        self.school_code = None
        self.offline_mode = True
        self.ai_status = "Starting…"
        self.student_name = "Student"

        self.root_layout = RootLayout()
        return self.root_layout

    def bootstrap_student(self, student_id: str, name: str, school_code: str = "", on_complete=None) -> None:
        self.student_id = student_id
        self.school_code = school_code
        self.student_name = name or student_id
        self.ai_status = "Loading AI…"

        def on_ai_ready(ok: bool, err: str | None):
            self.ai_status = self.services.ai_status_message()
            # Try to update current screen if it has the method
            screen = self.root_layout.sm.current_screen
            if hasattr(screen, "_update_ai_status"):
                screen._update_ai_status()
            if on_complete:
                on_complete(ok, err)

        self.services.bootstrap_student(
            student_id=student_id,
            name=name or student_id,
            grade_level="SS2",
            school_id=school_code or None,
            on_ai_ready=on_ai_ready,
        )


if __name__ == "__main__":
    TutorApp().run()
