"""
Dashboard Screen
Shows student progress, streak, and navigation
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.graphics import Color, Rectangle

try:
    from kivy_garden.graph import Graph, BarPlot
    HAS_GRAPH = True
except ImportError:
    HAS_GRAPH = False


class DashboardScreen(Screen):
    """Dashboard screen showing student progress"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "dashboard"
        self.student_id = None
        self._build_ui()

    def on_enter(self):
        app = App.get_running_app()
        services = app.services
        raw_id = getattr(app, "student_id", None) or getattr(services, "student_id", None)
        if not raw_id:
            # User somehow reached dashboard without logging in
            self.student_id = None
            return
        self.student_id = str(raw_id)
        self._update_stats()
        self._update_ai_status()

    def _build_ui(self):
        layout = BoxLayout(orientation="vertical", padding=15, spacing=15)

        header = Label(text="Dashboard", font_size=32, size_hint_y=0.08, bold=True)
        layout.add_widget(header)

        self.ai_status_label = Label(
            text="AI: starting…",
            font_size=12,
            size_hint_y=0.06,
            color=(0.4, 0.4, 0.4, 1),
        )
        layout.add_widget(self.ai_status_label)

        stats_layout = GridLayout(cols=2, spacing=10, size_hint_y=0.28)

        self.streak_label = Label(text="Streak: 0 days", font_size=18, size_hint_y=None, height=80)
        stats_layout.add_widget(self.streak_label)

        self.due_label = Label(text="Due Today: 0", font_size=18, size_hint_y=None, height=80)
        stats_layout.add_widget(self.due_label)

        self.retention_label = Label(text="Retention: 0%", font_size=18, size_hint_y=None, height=80)
        stats_layout.add_widget(self.retention_label)

        self.mastered_label = Label(text="Mastered: 0", font_size=18, size_hint_y=None, height=80)
        stats_layout.add_widget(self.mastered_label)

        layout.add_widget(stats_layout)

        self.graph_container = BoxLayout(orientation="vertical", size_hint_y=0.28)
        if HAS_GRAPH:
            self.graph = Graph(
                xlabel="Day",
                ylabel="Reviews",
                x_ticks_minor=1,
                x_ticks_major=1,
                y_ticks_major=5,
                y_grid_label=True,
                x_grid_label=True,
                padding=5,
                x_grid=True,
                y_grid=True,
                xmin=0,
                xmax=6,
                ymin=0,
                ymax=20,
            )
            self.bar_plot = BarPlot(color=[0.2, 0.6, 0.8, 1], bar_width=0.5)
            self.graph.add_plot(self.bar_plot)
            self.graph_container.add_widget(self.graph)
        else:
            self.graph_container.add_widget(Label(text="(kivy_garden.graph not installed)"))

        layout.add_widget(self.graph_container)

        actions_layout = BoxLayout(orientation="vertical", spacing=10, size_hint_y=0.32)

        review_btn = Button(
            text="Start Review",
            font_size=20,
            size_hint_y=0.3,
            background_color=(0.2, 0.6, 0.8, 1),
        )
        review_btn.bind(on_press=self.go_to_review)
        actions_layout.add_widget(review_btn)

        tutor_btn = Button(
            text="Ask Tutor",
            font_size=20,
            size_hint_y=0.3,
            background_color=(0.6, 0.2, 0.6, 1),
        )
        tutor_btn.bind(on_press=self.go_to_tutor)
        actions_layout.add_widget(tutor_btn)

        settings_btn = Button(
            text="Settings",
            font_size=18,
            size_hint_y=0.2,
            background_color=(0.5, 0.5, 0.5, 1),
        )
        settings_btn.bind(on_press=self.go_to_settings)
        actions_layout.add_widget(settings_btn)

        layout.add_widget(actions_layout)

        logout_btn = Button(
            text="Logout",
            font_size=16,
            size_hint_y=0.08,
            background_color=(0.8, 0.2, 0.2, 1),
        )
        logout_btn.bind(on_press=self.logout)
        layout.add_widget(logout_btn)

        self.add_widget(layout)

    def _update_ai_status(self):
        app = App.get_running_app()
        status = getattr(app, "ai_status", "") or app.services.ai_status_message()
        self.ai_status_label.text = f"AI: {status}"

    def _update_stats(self):
        app = App.get_running_app()
        scheduler = app.services.scheduler
        if not scheduler:
            return
        try:
            streak = scheduler.get_streak(self.student_id)
            due = scheduler.get_due_count(self.student_id)
            mastered = scheduler.get_mastered_count(self.student_id)

            retention_stats = scheduler.get_retention_stats(self.student_id, days=30)
            total_reviews = sum(r.get("total", 0) for r in retention_stats)
            passed_reviews = sum(r.get("passed", 0) for r in retention_stats)

            if total_reviews > 0:
                retention_pct = int((passed_reviews / total_reviews) * 100)
            else:
                retention_pct = 100

            self.streak_label.text = f"Streak: {streak} days"
            self.due_label.text = f"Due Today: {due}"
            self.retention_label.text = f"Retention: {retention_pct}%"
            self.mastered_label.text = f"Mastered: {mastered}"

            if HAS_GRAPH:
                stats_7d = scheduler.get_retention_stats(self.student_id, days=7)
                points = []
                max_y = 5
                for i in range(7):
                    if i < len(stats_7d):
                        val = stats_7d[i].get("total", 0)
                        points.append((i, val))
                        max_y = max(max_y, val)
                    else:
                        points.append((i, 0))

                self.bar_plot.points = points
                self.graph.ymax = ((max_y // 5) + 1) * 5

        except Exception as e:
            print(f"Error updating stats: {e}")
            self.streak_label.text = "Streak: 0 days"
            self.due_label.text = "Due Today: 0"
            self.retention_label.text = "Retention: 0%"
            self.mastered_label.text = "Mastered: 0"

    def go_to_review(self, instance):
        self.manager.current = "review"

    def go_to_tutor(self, instance):
        self.manager.current = "tutor_chat"

    def go_to_settings(self, instance):
        self.manager.current = "settings"

    def logout(self, instance):
        self.manager.current = "login"
