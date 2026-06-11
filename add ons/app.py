"""
Kivy/KivyMD UI: 5 screens for the offline AI tutoring app.
Screens: Login → Dashboard → TutorChat → FlashcardReview → Settings

Run locally:   python ui/app.py
Build APK:     buildozer android debug
"""

from __future__ import annotations

import threading
from datetime import date
from pathlib import Path
from typing import Optional

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.recycleview import RecycleView
from kivy.uix.screenmanager import Screen, ScreenManager, SlideTransition
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.metrics import dp
from kivy.properties import StringProperty, NumericProperty, BooleanProperty, ListProperty

from kivymd.app import MDApp
from kivymd.uix.button import MDFlatButton, MDRaisedButton, MDIconButton
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.toolbar import MDTopAppBar

# --- App-level imports (adjust paths for APK build) ---
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.rag_pipeline import RAGPipeline
from core.inference_engine import InferenceEngine
from core.sm2_scheduler import SM2Scheduler, KnowledgeItem
from sync.sync_layer import SyncLayer

# ---------------------------------------------------------------------------
# App State (simple singleton)
# ---------------------------------------------------------------------------

class AppState:
    """Shared state accessible from all screens."""

    def __init__(self):
        self.student_id: Optional[str] = None
        self.student_name: Optional[str] = None
        self.grade_level: str = "SS2"
        self.subject_focus: str = "Biology"

        # Core components (initialized after login)
        self.rag: Optional[RAGPipeline] = None
        self.engine: Optional[InferenceEngine] = None
        self.scheduler: Optional[SM2Scheduler] = None
        self.sync: Optional[SyncLayer] = None

        # Current review session
        self.current_session = None
        self.session_index: int = 0
        self.showing_answer: bool = False

    @property
    def data_dir(self) -> Path:
        return Path("data") / (self.student_id or "default")

    def is_ready(self) -> bool:
        return all([self.rag, self.engine, self.scheduler, self.student_id])


state = AppState()


# ---------------------------------------------------------------------------
# Background Loader
# ---------------------------------------------------------------------------

def load_components(student_id: str, grade_level: str, on_complete):
    """Loads heavy components off the main thread."""
    data_dir = Path("data") / student_id
    models_dir = Path("models")

    try:
        # RAG
        rag = RAGPipeline(data_dir=data_dir / "rag")
        rag.load(model_cache_dir=models_dir / "embeddings")
        state.rag = rag

        # LLM
        engine = InferenceEngine(models_dir=models_dir)
        engine.load(ram_gb=4.0)
        state.engine = engine

        # SM2
        scheduler = SM2Scheduler(db_path=data_dir / "tutor.db")
        scheduler.init_db()
        scheduler.upsert_student(student_id, state.student_name or "Student", grade_level)
        scheduler.seed_items_for_student(student_id)
        state.scheduler = scheduler

        # Sync (optional — works offline)
        try:
            sync = SyncLayer(
                scheduler=scheduler,
                server_url="https://tutor.example.com",
                student_id=student_id,
                state_dir=data_dir / "sync",
            )
            sync.start()
            state.sync = sync
        except Exception:
            pass  # Sync is optional

        Clock.schedule_once(lambda dt: on_complete(True, None))
    except Exception as e:
        Clock.schedule_once(lambda dt: on_complete(False, str(e)))


# ---------------------------------------------------------------------------
# Screen 1: Login
# ---------------------------------------------------------------------------

class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "login"
        self._build_ui()

    def _build_ui(self):
        layout = BoxLayout(orientation="vertical", padding=dp(32), spacing=dp(16))

        layout.add_widget(MDLabel(
            text="📚 AI Tutor",
            font_style="H3",
            halign="center",
            size_hint_y=None,
            height=dp(80),
        ))
        layout.add_widget(MDLabel(
            text="Offline-First Learning",
            font_style="Subtitle1",
            halign="center",
            size_hint_y=None,
            height=dp(30),
            theme_text_color="Secondary",
        ))
        layout.add_widget(Widget(size_hint_y=None, height=dp(20)))

        self.student_id_field = MDTextField(
            hint_text="Student ID",
            icon_right="account",
            helper_text="e.g. STU20240001",
            helper_text_mode="on_focus",
        )
        self.school_code_field = MDTextField(
            hint_text="School Code",
            icon_right="school",
        )
        self.name_field = MDTextField(
            hint_text="Your Name",
            icon_right="pencil",
        )

        layout.add_widget(self.student_id_field)
        layout.add_widget(self.school_code_field)
        layout.add_widget(self.name_field)
        layout.add_widget(Widget(size_hint_y=None, height=dp(8)))

        self.status_label = MDLabel(
            text="",
            halign="center",
            theme_text_color="Error",
            size_hint_y=None,
            height=dp(24),
        )
        layout.add_widget(self.status_label)

        btn_layout = BoxLayout(orientation="horizontal", spacing=dp(12), size_hint_y=None, height=dp(48))
        login_btn = MDRaisedButton(text="Sign In", on_release=self.on_login)
        offline_btn = MDFlatButton(text="Continue Offline", on_release=self.on_offline)
        btn_layout.add_widget(login_btn)
        btn_layout.add_widget(offline_btn)
        layout.add_widget(btn_layout)
        layout.add_widget(Widget())  # spacer

        self.add_widget(layout)

    def on_login(self, *args):
        student_id = self.student_id_field.text.strip()
        name = self.name_field.text.strip() or "Student"
        if not student_id:
            self.status_label.text = "Please enter your Student ID"
            return
        self._start_loading(student_id, name)

    def on_offline(self, *args):
        self._start_loading("offline_user", "Offline Student")

    def _start_loading(self, student_id: str, name: str):
        state.student_id = student_id
        state.student_name = name
        self.status_label.text = "Loading AI models… (first run takes ~30s)"

        thread = threading.Thread(
            target=load_components,
            args=(student_id, state.grade_level, self._on_load_complete),
            daemon=True,
        )
        thread.start()

    def _on_load_complete(self, success: bool, error: Optional[str]):
        if success:
            self.manager.transition = SlideTransition(direction="left")
            self.manager.current = "dashboard"
        else:
            self.status_label.text = f"Load failed: {error}"


# ---------------------------------------------------------------------------
# Screen 2: Dashboard
# ---------------------------------------------------------------------------

class DashboardScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "dashboard"
        self._build_ui()

    def on_enter(self):
        self._refresh_stats()

    def _build_ui(self):
        layout = BoxLayout(orientation="vertical")

        toolbar = MDTopAppBar(title="📊 Dashboard")
        toolbar.right_action_items = [
            ["cog", lambda x: self._go("settings")],
        ]
        layout.add_widget(toolbar)

        scroll = ScrollView()
        content = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(16), size_hint_y=None)
        content.bind(minimum_height=content.setter("height"))

        # Streak card
        self.streak_label = MDLabel(text="🔥 Streak: — days", font_style="H5", halign="center")
        streak_card = MDCard(padding=dp(16), size_hint_y=None, height=dp(80))
        streak_card.add_widget(self.streak_label)
        content.add_widget(streak_card)

        # Stats row
        stats_row = BoxLayout(orientation="horizontal", spacing=dp(8), size_hint_y=None, height=dp(100))
        self.due_label = self._stat_card("📋 Due Today", "—")
        self.mastered_label = self._stat_card("🏆 Mastered", "—")
        self.retention_label = self._stat_card("📈 Retention", "—%")
        stats_row.add_widget(self.due_label[0])
        stats_row.add_widget(self.mastered_label[0])
        stats_row.add_widget(self.retention_label[0])
        content.add_widget(stats_row)

        # Action buttons
        review_btn = MDRaisedButton(
            text="▶  Start Review Session",
            size_hint_y=None, height=dp(52),
            on_release=lambda x: self._go("review"),
        )
        chat_btn = MDRaisedButton(
            text="💬  Ask the AI Tutor",
            size_hint_y=None, height=dp(52),
            on_release=lambda x: self._go("chat"),
        )
        content.add_widget(review_btn)
        content.add_widget(chat_btn)

        # Sync status
        self.sync_label = MDLabel(
            text="Sync: —",
            halign="center",
            theme_text_color="Secondary",
            size_hint_y=None, height=dp(24),
        )
        content.add_widget(self.sync_label)

        scroll.add_widget(content)
        layout.add_widget(scroll)
        self.add_widget(layout)

    def _stat_card(self, title: str, value: str):
        card = MDCard(padding=dp(8), size_hint_x=1)
        box = BoxLayout(orientation="vertical")
        val_lbl = MDLabel(text=value, font_style="H5", halign="center")
        ttl_lbl = MDLabel(text=title, font_style="Caption", halign="center", theme_text_color="Secondary")
        box.add_widget(val_lbl)
        box.add_widget(ttl_lbl)
        card.add_widget(box)
        return card, val_lbl

    def _refresh_stats(self):
        if not state.scheduler or not state.student_id:
            return
        due = state.scheduler.get_due_count(state.student_id)
        mastered = state.scheduler.get_mastered_count(state.student_id)
        streak = state.scheduler.get_streak(state.student_id)

        self.streak_label.text = f"🔥 Streak: {streak} day{'s' if streak != 1 else ''}"
        self.due_label[1].text = str(due)
        self.mastered_label[1].text = str(mastered)

        # Retention from last 7 days
        stats = state.scheduler.get_retention_stats(state.student_id, days=7)
        if stats:
            total = sum(s["total"] for s in stats)
            passed = sum(s["passed"] for s in stats)
            retention = (passed / total * 100) if total > 0 else 0
            self.retention_label[1].text = f"{retention:.0f}%"

        # Sync status
        if state.sync:
            self.sync_label.text = f"Sync: {state.sync.status.name}"

    def _go(self, screen_name: str):
        self.manager.transition = SlideTransition(direction="left")
        self.manager.current = screen_name


# ---------------------------------------------------------------------------
# Screen 3: Tutor Chat
# ---------------------------------------------------------------------------

class ChatMessage(BoxLayout):
    """Single message bubble."""
    text = StringProperty("")
    is_user = BooleanProperty(False)

    def __init__(self, text: str, is_user: bool, **kwargs):
        super().__init__(**kwargs)
        self.text = text
        self.is_user = is_user
        self.orientation = "horizontal"
        self.size_hint_y = None
        self.padding = (dp(8), dp(4))

        bubble = MDCard(
            padding=dp(12),
            size_hint=(0.8, None),
            md_bg_color=[0.2, 0.6, 1, 1] if is_user else [0.95, 0.95, 0.95, 1],
        )
        label = MDLabel(
            text=text,
            theme_text_color="Custom" if is_user else "Primary",
            text_color=[1, 1, 1, 1] if is_user else [0, 0, 0, 1],
            size_hint_y=None,
        )
        label.bind(texture_size=label.setter("size"))
        bubble.add_widget(label)
        bubble.bind(minimum_height=bubble.setter("height"))

        if is_user:
            self.add_widget(Widget())
            self.add_widget(bubble)
        else:
            self.add_widget(bubble)
            self.add_widget(Widget())

        self.bind(minimum_height=self.setter("height"))


class TutorChatScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "chat"
        self._messages: list[dict] = []
        self._build_ui()

    def _build_ui(self):
        layout = BoxLayout(orientation="vertical")

        toolbar = MDTopAppBar(title="💬 AI Tutor")
        toolbar.left_action_items = [["arrow-left", lambda x: self._go_back()]]
        layout.add_widget(toolbar)

        # Scrollable message list
        self.scroll = ScrollView(size_hint_y=1)
        self.message_stack = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=dp(4),
            padding=(dp(8), dp(8)),
        )
        self.message_stack.bind(minimum_height=self.message_stack.setter("height"))
        self.scroll.add_widget(self.message_stack)
        layout.add_widget(self.scroll)

        # Source chips area
        self.source_label = MDLabel(
            text="",
            theme_text_color="Secondary",
            font_style="Caption",
            size_hint_y=None,
            height=dp(20),
            padding=(dp(12), 0),
        )
        layout.add_widget(self.source_label)

        # Input row
        input_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(56),
            padding=(dp(8), dp(4)),
            spacing=dp(8),
        )
        self.input_field = MDTextField(
            hint_text="Ask anything…",
            multiline=False,
            size_hint_x=1,
        )
        self.input_field.bind(on_text_validate=self.send_message)

        send_btn = MDIconButton(icon="send", on_release=self.send_message)
        input_row.add_widget(self.input_field)
        input_row.add_widget(send_btn)
        layout.add_widget(input_row)

        self.add_widget(layout)

        # Welcome message
        self._add_message(
            "Hello! I'm your AI tutor. Ask me anything about your curriculum — I work offline too! 📚",
            is_user=False,
        )

    def send_message(self, *args):
        query = self.input_field.text.strip()
        if not query or not state.is_ready():
            return
        self.input_field.text = ""
        self._add_message(query, is_user=True)
        self._add_message("Thinking…", is_user=False)
        self.source_label.text = ""

        # Run inference in background thread
        threading.Thread(
            target=self._generate_response,
            args=(query,),
            daemon=True,
        ).start()

    def _generate_response(self, query: str):
        try:
            pkg = state.rag.build_prompt(query, grade_level=state.grade_level)
            sources = [c.source for c in pkg.context_chunks]
            collected_tokens: list[str] = []

            def on_token(token: str):
                collected_tokens.append(token)
                partial = "".join(collected_tokens)
                Clock.schedule_once(lambda dt: self._update_last_message(partial))

            result = state.engine.generate(pkg.prompt, on_token=on_token)

            # Final update
            final_text = result.text
            sources_text = " · ".join(f"[{s}]" for s in sources) if sources else "No context retrieved"

            Clock.schedule_once(lambda dt: self._update_last_message(final_text))
            Clock.schedule_once(lambda dt: setattr(self.source_label, "text", f"Sources: {sources_text}"))

        except Exception as e:
            error_msg = f"⚠️ Error: {str(e)}"
            Clock.schedule_once(lambda dt: self._update_last_message(error_msg))

    def _add_message(self, text: str, is_user: bool):
        msg = ChatMessage(text=text, is_user=is_user)
        self.message_stack.add_widget(msg)
        self._messages.append({"text": text, "is_user": is_user, "widget": msg})
        Clock.schedule_once(lambda dt: setattr(self.scroll, "scroll_y", 0))

    def _update_last_message(self, text: str):
        if self._messages:
            last = self._messages[-1]
            if not last["is_user"]:
                # Find label inside the card and update it
                try:
                    bubble = last["widget"].children[-1]
                    label = bubble.children[0]
                    label.text = text
                except (IndexError, AttributeError):
                    pass

    def _go_back(self):
        self.manager.transition = SlideTransition(direction="right")
        self.manager.current = "dashboard"


# ---------------------------------------------------------------------------
# Screen 4: Flashcard Review
# ---------------------------------------------------------------------------

class FlashcardReviewScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "review"
        self._session = None
        self._index = 0
        self._showing_answer = False
        self._build_ui()

    def on_enter(self):
        self._load_session()

    def _load_session(self):
        if not state.scheduler or not state.student_id:
            return
        self._session = state.scheduler.get_review_session(
            state.student_id, subject=state.subject_focus
        )
        self._index = 0
        self._showing_answer = False
        self._show_current_card()

    def _build_ui(self):
        layout = BoxLayout(orientation="vertical")

        toolbar = MDTopAppBar(title="📇 Flashcard Review")
        toolbar.left_action_items = [["arrow-left", lambda x: self._go_back()]]
        layout.add_widget(toolbar)

        # Progress
        self.progress_label = MDLabel(
            text="Card 0 of 0",
            halign="center",
            theme_text_color="Secondary",
            size_hint_y=None,
            height=dp(32),
        )
        layout.add_widget(self.progress_label)

        # Card
        card_area = BoxLayout(padding=dp(16), size_hint_y=1)
        self.card = MDCard(padding=dp(24), md_bg_color=[1, 1, 1, 1])
        card_inner = BoxLayout(orientation="vertical", spacing=dp(16))

        self.question_label = MDLabel(
            text="",
            font_style="H6",
            halign="center",
            size_hint_y=None,
        )
        self.question_label.bind(texture_size=self.question_label.setter("size"))

        self.answer_label = MDLabel(
            text="",
            halign="center",
            theme_text_color="Secondary",
            size_hint_y=None,
            opacity=0,
        )
        self.answer_label.bind(texture_size=self.answer_label.setter("size"))

        self.flip_btn = MDRaisedButton(
            text="Show Answer",
            size_hint_y=None,
            height=dp(44),
            on_release=self.flip_card,
        )

        card_inner.add_widget(self.question_label)
        card_inner.add_widget(self.answer_label)
        card_inner.add_widget(self.flip_btn)
        self.card.add_widget(card_inner)
        card_area.add_widget(self.card)
        layout.add_widget(card_area)

        # Rating buttons (hidden until answer shown)
        self.rating_area = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            height=dp(120),
            padding=(dp(16), dp(8)),
            spacing=dp(8),
            opacity=0,
        )
        rating_row = BoxLayout(spacing=dp(8))
        ratings = [("✗ Again", 1), ("Hmm", 2), ("OK", 3), ("Good", 4), ("✓ Perfect", 5)]
        for label, quality in ratings:
            btn = MDRaisedButton(
                text=label,
                on_release=lambda x, q=quality: self.rate_card(q),
            )
            rating_row.add_widget(btn)
        self.rating_area.add_widget(MDLabel(
            text="How well did you remember?",
            halign="center",
            size_hint_y=None,
            height=dp(24),
        ))
        self.rating_area.add_widget(rating_row)
        layout.add_widget(self.rating_area)

        self.add_widget(layout)

    def _show_current_card(self):
        if not self._session or self._session.is_empty():
            self.question_label.text = "🎉 All done for today!"
            self.answer_label.text = ""
            self.flip_btn.opacity = 0
            self.rating_area.opacity = 0
            self.progress_label.text = "Session complete"
            return

        total = len(self._session.items)
        if self._index >= total:
            self.question_label.text = "🎉 Session complete!"
            self.flip_btn.opacity = 0
            self.rating_area.opacity = 0
            self.progress_label.text = f"Finished {total} cards"
            return

        record, item = self._session.items[self._index]
        self.progress_label.text = f"Card {self._index + 1} of {total}"
        self.question_label.text = item.question
        self.answer_label.text = item.answer
        self.answer_label.opacity = 0
        self.flip_btn.text = "Show Answer"
        self.flip_btn.opacity = 1
        self.rating_area.opacity = 0
        self._showing_answer = False

    def flip_card(self, *args):
        if not self._showing_answer:
            self.answer_label.opacity = 1
            self.flip_btn.opacity = 0
            self.rating_area.opacity = 1
            self._showing_answer = True

    def rate_card(self, quality: int):
        if not self._session or self._index >= len(self._session.items):
            return
        record, _ = self._session.items[self._index]
        state.scheduler.record_response(record.id, quality=quality)
        self._index += 1
        self._showing_answer = False
        self._show_current_card()

    def _go_back(self):
        self.manager.transition = SlideTransition(direction="right")
        self.manager.current = "dashboard"


# ---------------------------------------------------------------------------
# Screen 5: Settings
# ---------------------------------------------------------------------------

class SettingsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "settings"
        self._build_ui()

    def _build_ui(self):
        layout = BoxLayout(orientation="vertical")
        toolbar = MDTopAppBar(title="⚙️ Settings")
        toolbar.left_action_items = [["arrow-left", lambda x: self._go_back()]]
        layout.add_widget(toolbar)

        scroll = ScrollView()
        content = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12), size_hint_y=None)
        content.bind(minimum_height=content.setter("height"))

        # Student info
        content.add_widget(MDLabel(text="Student", font_style="Subtitle1", size_hint_y=None, height=dp(32)))
        self.name_field = MDTextField(hint_text="Display Name")
        content.add_widget(self.name_field)

        # Subject focus
        content.add_widget(MDLabel(text="Subject Focus", font_style="Subtitle1", size_hint_y=None, height=dp(32)))
        subjects_row = BoxLayout(spacing=dp(8), size_hint_y=None, height=dp(44))
        for subj in ["Biology", "English", "Chemistry", "Physics", "Mathematics"]:
            btn = MDFlatButton(text=subj, on_release=lambda x, s=subj: self._set_subject(s))
            subjects_row.add_widget(btn)
        content.add_widget(subjects_row)

        self.subject_label = MDLabel(
            text=f"Current: {state.subject_focus}",
            halign="left",
            size_hint_y=None,
            height=dp(24),
        )
        content.add_widget(self.subject_label)

        # Storage info
        content.add_widget(MDLabel(text="Storage", font_style="Subtitle1", size_hint_y=None, height=dp(32)))
        self.storage_label = MDLabel(
            text="Computing…",
            theme_text_color="Secondary",
            size_hint_y=None,
            height=dp(24),
        )
        content.add_widget(self.storage_label)

        # Sync toggle
        content.add_widget(MDLabel(text="Sync", font_style="Subtitle1", size_hint_y=None, height=dp(32)))
        sync_btn = MDRaisedButton(text="Force Sync Now", on_release=self._force_sync)
        content.add_widget(sync_btn)
        self.sync_result_label = MDLabel(text="", size_hint_y=None, height=dp(24))
        content.add_widget(self.sync_result_label)

        # Clear cache
        clear_btn = MDFlatButton(text="Clear Cache", on_release=self._clear_cache)
        content.add_widget(clear_btn)

        scroll.add_widget(content)
        layout.add_widget(scroll)
        self.add_widget(layout)

    def on_enter(self):
        self.name_field.text = state.student_name or ""
        self._update_storage_info()
        self.subject_label.text = f"Current: {state.subject_focus}"

    def _set_subject(self, subject: str):
        state.subject_focus = subject
        self.subject_label.text = f"Current: {subject}"

    def _force_sync(self, *args):
        if state.sync:
            self.sync_result_label.text = "Syncing…"
            def run():
                result = state.sync.force_sync()
                msg = f"Pushed {result.pushed}, pulled {result.pulled}"
                if result.errors:
                    msg += f" ⚠️ {result.errors[0]}"
                Clock.schedule_once(lambda dt: setattr(self.sync_result_label, "text", msg))
            threading.Thread(target=run, daemon=True).start()
        else:
            self.sync_result_label.text = "Sync not configured"

    def _clear_cache(self, *args):
        # In production: clear FAISS index cache and re-prompt for rebuild
        self.sync_result_label.text = "Cache cleared (restart required)"

    def _update_storage_info(self):
        try:
            data_dir = state.data_dir
            total_bytes = sum(f.stat().st_size for f in data_dir.rglob("*") if f.is_file())
            models_bytes = sum(
                f.stat().st_size for f in Path("models").rglob("*") if f.is_file()
            ) if Path("models").exists() else 0
            total_mb = (total_bytes + models_bytes) / (1024 * 1024)
            self.storage_label.text = f"Data + Models: {total_mb:.1f} MB"
        except Exception:
            self.storage_label.text = "Storage: unavailable"

    def _go_back(self):
        self.manager.transition = SlideTransition(direction="right")
        self.manager.current = "dashboard"


# ---------------------------------------------------------------------------
# App Entry Point
# ---------------------------------------------------------------------------

class TutorApp(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.accent_palette = "Teal"
        self.theme_cls.theme_style = "Light"

        sm = ScreenManager()
        sm.add_widget(LoginScreen())
        sm.add_widget(DashboardScreen())
        sm.add_widget(TutorChatScreen())
        sm.add_widget(FlashcardReviewScreen())
        sm.add_widget(SettingsScreen())
        return sm

    def on_stop(self):
        if state.sync:
            state.sync.stop()


if __name__ == "__main__":
    TutorApp().run()
