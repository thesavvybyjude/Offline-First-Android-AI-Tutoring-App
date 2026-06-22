"""
Dashboard Screen
Shows student progress, streak, and navigation
"""

import sys
import os

from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import ButtonBehavior
from kivy.graphics import Color, Rectangle, RoundedRectangle, Line
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.widget import Widget

from frontend.theme import get_color, get_font, RADIUS
from frontend.widgets.top_bar import TopBar
from frontend.widgets.stat_card import StatCard
from frontend.widgets.bar_chart import BarChart
from frontend.widgets.glass_card import GlassCard
from frontend.widgets.gradient_button import GradientButton

class SecondaryButton(ButtonBehavior, BoxLayout):
    """Outlined secondary action button"""
    def __init__(self, text="", icon="", **kwargs):
        self.orientation = 'horizontal'
        self.padding = ['16dp', '0dp']
        self.spacing = '8dp'
        self.size_hint_y = None
        self.height = '80dp'
        self.btn_text = text
        self.icon = icon
        super().__init__(**kwargs)
        self.bind(pos=self._update_canvas, size=self._update_canvas, state=self._update_canvas)
        self._build_ui()
        
    def _build_ui(self):
        self.clear_widgets()
        
        # Left content
        left_box = BoxLayout(orientation='horizontal', spacing='12dp', size_hint_x=1)
        if self.icon:
            # Placeholder for icon
            icon_lbl = Label(text=self.icon, color=get_color("white"), font_name="MaterialSymbols", size_hint_x=None, width='32dp', font_size='24sp')
            left_box.add_widget(icon_lbl)
            
        font = get_font("headline-sm")
        lbl = Label(
            text=self.btn_text,
            color=get_color("white"),
            font_name=font["font_name"],
            font_size=font["font_size"],
            bold=True,
            halign='left',
            valign='middle'
        )
        lbl.bind(size=lbl.setter('text_size'))
        left_box.add_widget(lbl)
        self.add_widget(left_box)
        
        # Arrow
        arrow = Label(text=">", color=get_color("on-surface-variant"), size_hint_x=None, width='24dp', font_size='20sp')
        self.add_widget(arrow)

    def _update_canvas(self, *args):
        from kivy.clock import Clock
        Clock.schedule_once(self._deferred_update_canvas, -1)

    def _deferred_update_canvas(self, dt):
        self.canvas.before.clear()
        with self.canvas.before:
            if self.state == 'down':
                Color(*get_color("surface-bright"))
            else:
                Color(*get_color("surface-variant"))
            r_dp = dp(float(str(RADIUS['xl']).replace('dp', '')))
            RoundedRectangle(pos=self.pos, size=self.size, radius=[r_dp])
            
            Color(*get_color("outline-variant"))
            Line(rounded_rectangle=(self.x, self.y, self.width, self.height, r_dp), width=1)


class PrimaryCardButton(ButtonBehavior, BoxLayout):
    """Filled primary action button"""
    def __init__(self, text="", icon="", **kwargs):
        self.orientation = 'horizontal'
        self.padding = ['16dp', '0dp']
        self.spacing = '8dp'
        self.size_hint_y = None
        self.height = '80dp'
        self.btn_text = text
        self.icon = icon
        super().__init__(**kwargs)
        self.bind(pos=self._update_canvas, size=self._update_canvas, state=self._update_canvas)
        self._build_ui()
        
    def _build_ui(self):
        self.clear_widgets()
        
        # Left content
        left_box = BoxLayout(orientation='horizontal', spacing='12dp', size_hint_x=1)
        if self.icon:
            icon_lbl = Label(text=self.icon, color=get_color("white"), font_name="MaterialSymbols", size_hint_x=None, width='32dp', font_size='24sp')
            left_box.add_widget(icon_lbl)
            
        font = get_font("headline-sm")
        lbl = Label(
            text=self.btn_text,
            color=get_color("white"),
            font_name=font["font_name"],
            font_size=font["font_size"],
            bold=True,
            halign='left',
            valign='middle'
        )
        lbl.bind(size=lbl.setter('text_size'))
        left_box.add_widget(lbl)
        self.add_widget(left_box)
        
        # Arrow
        arrow = Label(text=">", color=get_color("on-primary-container"), size_hint_x=None, width='24dp', font_size='20sp')
        self.add_widget(arrow)

    def _update_canvas(self, *args):
        from kivy.clock import Clock
        Clock.schedule_once(self._deferred_update_canvas, -1)

    def _deferred_update_canvas(self, dt):
        self.canvas.before.clear()
        with self.canvas.before:
            r, g, b, a = get_color("primary-container")
            if self.state == 'down':
                Color(r*0.8, g*0.8, b*0.8, a)
            else:
                Color(r, g, b, a)
            r_dp = dp(float(str(RADIUS['xl']).replace('dp', '')))
            RoundedRectangle(pos=self.pos, size=self.size, radius=[r_dp])


class DashboardScreen(Screen):
    """Premium dashboard screen"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "dashboard"
        self.student_id = None
        self.student_name = "Student"
        
        # UI Elements that need updating
        self.streak_lbl = None
        self.greet_lbl = None
        self.stat_ai = None
        self.stat_due = None
        self.stat_retention = None
        self.stat_mastered = None
        self.bar_chart = None
        
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
        services = app.services
        raw_id = getattr(app, "student_id", None) or getattr(services, "student_id", None)
        if not raw_id:
            self.student_id = None
            return
        self.student_id = str(raw_id)
        
        # Try to get display name
        self.student_name = getattr(app, "student_name", None) or self.student_id
        if self.greet_lbl:
            self.greet_lbl.text = f"Hello, {self.student_name}!"
            
        self._update_stats()
        self._update_ai_status()
        
        # Poll AI status
        self.ai_poll_event = Clock.schedule_interval(lambda dt: self._update_ai_status(), 2.0)

    def on_leave(self):
        if hasattr(self, 'ai_poll_event'):
            self.ai_poll_event.cancel()

    def _build_ui(self):
        main_layout = BoxLayout(orientation='vertical')
        
        # Top Bar
        top_bar = TopBar(title="OFFLINE AI TUTOR")
        main_layout.add_widget(top_bar)
        
        # Scrollable Content
        scroll = ScrollView(do_scroll_x=False, do_scroll_y=True)
        content = BoxLayout(orientation='vertical', padding=['16dp', '24dp', '16dp', '24dp'], spacing='24dp', size_hint_y=None)
        content.bind(minimum_height=content.setter('height'))
        
        # Greeting & Streak
        greet_box = BoxLayout(orientation='horizontal', size_hint_y=None, height='60dp')
        
        text_box = BoxLayout(orientation='vertical')
        font_lg = get_font("headline-lg-mobile")
        self.greet_lbl = Label(
            text="Hello!",
            color=get_color("on-surface"),
            font_name=font_lg["font_name"],
            font_size=font_lg["font_size"],
            bold=True,
            halign='left'
        )
        self.greet_lbl.bind(size=self.greet_lbl.setter('text_size'))
        
        font_md = get_font("body-md")
        sub_lbl = Label(
            text="Ready for today's session?",
            color=get_color("on-surface-variant"),
            font_name=font_md["font_name"],
            font_size=font_md["font_size"],
            halign='left'
        )
        sub_lbl.bind(size=sub_lbl.setter('text_size'))
        
        text_box.add_widget(self.greet_lbl)
        text_box.add_widget(sub_lbl)
        greet_box.add_widget(text_box)
        
        # Streak Badge
        streak_badge = BoxLayout(orientation='horizontal', size_hint=(None, None), size=('120dp', '36dp'), 
                               padding=['8dp', '4dp'], spacing='4dp', pos_hint={'center_y': 0.5})
        with streak_badge.canvas.before:
            Color(*get_color("surface-container-high"))
            bg_rect = RoundedRectangle(pos=streak_badge.pos, size=streak_badge.size, radius=[dp(18)])
            Color(1, 1, 1, 0.1)
            bg_line = Line(rounded_rectangle=(streak_badge.x, streak_badge.y, streak_badge.width, streak_badge.height, dp(18)), width=1)
        
        def update_badge(instance, value):
            bg_rect.pos = instance.pos
            bg_rect.size = instance.size
            bg_line.rounded_rectangle = (instance.x, instance.y, instance.width, instance.height, dp(18))
        streak_badge.bind(pos=update_badge, size=update_badge)
        
        self.streak_lbl = Label(text="0 Day Streak", color=get_color("tertiary-fixed-dim"),
                               font_name=get_font("label-lg")["font_name"], font_size=get_font("label-lg")["font_size"], bold=True)
        streak_badge.add_widget(self.streak_lbl)
        greet_box.add_widget(streak_badge)
        
        content.add_widget(greet_box)
        
        # Bento Stats Grid
        stats_grid = GridLayout(cols=2, spacing='16dp', size_hint_y=None)
        stats_grid.bind(minimum_height=stats_grid.setter('height'))
        
        # 1. AI Status (spans 2 cols visually in mockup, but here we just make it a card)
        # We can make it span 2 cols by adding to a separate layout or letting it be a card
        ai_box = BoxLayout(orientation='vertical', size_hint_y=None, height='100dp')
        self.stat_ai = GlassCard(orientation='vertical', spacing='8dp')
        lbl_ai_title = Label(text="AI TUTOR STATUS", color=get_color("on-surface-variant"), 
                            font_name=get_font("label-sm")["font_name"], font_size=get_font("label-sm")["font_size"],
                            halign='left', size_hint_y=None, height='16dp')
        lbl_ai_title.bind(size=lbl_ai_title.setter('text_size'))
        self.lbl_ai_val = Label(text="Starting...", color=get_color("on-surface"), 
                               font_name=get_font("headline-sm")["font_name"], font_size=get_font("headline-sm")["font_size"],
                               bold=True, halign='left')
        self.lbl_ai_val.bind(size=self.lbl_ai_val.setter('text_size'))
        self.stat_ai.add_widget(lbl_ai_title)
        self.stat_ai.add_widget(BoxLayout(size_hint_y=1))
        self.stat_ai.add_widget(self.lbl_ai_val)
        ai_box.add_widget(self.stat_ai)
        content.add_widget(ai_box)
        
        # Remaining stats
        self.stat_due = StatCard(title="Due Today", value="0", unit="cards", size_hint_y=None, height='120dp')
        self.stat_retention = StatCard(title="Retention", value="0%", size_hint_y=None, height='120dp')
        self.stat_mastered = StatCard(title="Mastered", value="0", size_hint_y=None, height='120dp')
        
        # Let's put due in col 1, retention in col 2
        stats_grid.add_widget(self.stat_due)
        stats_grid.add_widget(self.stat_retention)
        
        # Put mastered below
        stats_grid.add_widget(self.stat_mastered)
        # Empty placeholder for 4th slot to maintain grid
        stats_grid.add_widget(Widget(size_hint_y=None, height='120dp'))
        
        content.add_widget(stats_grid)
        
        # Primary Actions
        actions_grid = GridLayout(cols=1, spacing='16dp', size_hint_y=None)
        actions_grid.bind(minimum_height=actions_grid.setter('height'))
        
        btn_review = PrimaryCardButton(text="Start Review", icon="\ue037") # play_arrow
        btn_review.bind(on_release=self.go_to_review)
        
        btn_tutor = SecondaryButton(text="Ask AI Tutor", icon="\ue0ca") # chat
        btn_tutor.bind(on_release=self.go_to_tutor)
        
        actions_grid.add_widget(btn_review)
        actions_grid.add_widget(btn_tutor)
        
        content.add_widget(actions_grid)
        
        # Activity Chart
        chart_card = GlassCard(orientation='vertical', size_hint_y=None, height='220dp')
        lbl_chart = Label(text="7-Day Activity", color=get_color("on-surface"), 
                         font_name=get_font("headline-sm")["font_name"], font_size=get_font("headline-sm")["font_size"],
                         bold=True, halign='left', size_hint_y=None, height='32dp')
        lbl_chart.bind(size=lbl_chart.setter('text_size'))
        chart_card.add_widget(lbl_chart)
        
        self.bar_chart = BarChart(size_hint_y=1)
        # Default empty data
        days = ["M", "T", "W", "T", "F", "S", "S"]
        self.bar_chart.data = [(d, 0.1) for d in days]
        
        chart_card.add_widget(self.bar_chart)
        content.add_widget(chart_card)
        
        scroll.add_widget(content)
        main_layout.add_widget(scroll)
        self.add_widget(main_layout)

    def _update_ai_status(self):
        app = App.get_running_app()
        status = getattr(app, "ai_status", "") or app.services.ai_status_message()
        self.lbl_ai_val.text = status

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

            self.streak_lbl.text = f"{streak} Day Streak"
            self.stat_due.value = str(due)
            self.stat_retention.value = f"{retention_pct}%"
            self.stat_mastered.value = str(mastered)

            # Update Chart
            stats_7d = scheduler.get_retention_stats(self.student_id, days=7)
            chart_data = []
            max_y = max((r.get("total", 0) for r in stats_7d), default=0)
            if max_y == 0: max_y = 1 # Avoid division by zero
            
            days_labels = ["M", "T", "W", "T", "F", "S", "S"] # Simplified labels
            for i in range(7):
                if i < len(stats_7d):
                    val = stats_7d[i].get("total", 0)
                    pct = val / max_y
                    chart_data.append((days_labels[i % 7], pct))
                else:
                    chart_data.append((days_labels[i % 7], 0.05)) # Tiny minimum visible bar

            self.bar_chart.data = chart_data

        except Exception as e:
            print(f"Error updating stats: {e}")

    def go_to_review(self, instance):
        self.manager.current = "review"

    def go_to_tutor(self, instance):
        self.manager.current = "tutor_chat"

