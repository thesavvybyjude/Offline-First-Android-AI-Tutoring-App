"""
Login Screen
Student authentication and offline mode selection
"""

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.properties import ObjectProperty
from kivy.core.window import Window


class LoginScreen(Screen):
    """Login screen for student authentication"""
    
    student_id_input = ObjectProperty(None)
    school_code_input = ObjectProperty(None)
    offline_checkbox = ObjectProperty(None)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'login'
        self._build_ui()
    
    def _build_ui(self):
        """Build the login UI"""
        # Main layout
        layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        
        # Title
        title = Label(
            text='AI Tutor',
            font_size=48,
            size_hint_y=0.2,
            bold=True
        )
        layout.add_widget(title)
        
        # Subtitle
        subtitle = Label(
            text='Offline-First Learning',
            font_size=18,
            size_hint_y=0.1
        )
        layout.add_widget(subtitle)
        
        # Student ID input
        self.student_id_input = TextInput(
            hint_text='Student ID',
            size_hint_y=0.1,
            multiline=False,
            font_size=16
        )
        layout.add_widget(self.student_id_input)
        
        # School code input
        self.school_code_input = TextInput(
            hint_text='School Code',
            size_hint_y=0.1,
            multiline=False,
            font_size=16
        )
        layout.add_widget(self.school_code_input)
        
        # Offline mode checkbox
        offline_layout = BoxLayout(orientation='horizontal', size_hint_y=0.1)
        self.offline_checkbox = CheckBox(active=True)
        offline_label = Label(text='Continue Offline', font_size=16)
        offline_layout.add_widget(self.offline_checkbox)
        offline_layout.add_widget(offline_label)
        layout.add_widget(offline_layout)
        
        # Login button
        login_btn = Button(
            text='Login',
            size_hint_y=0.15,
            font_size=20,
            background_color=(0.2, 0.6, 0.8, 1)
        )
        login_btn.bind(on_press=self.on_login)
        layout.add_widget(login_btn)
        
        # Spacer
        layout.add_widget(Label(size_hint_y=0.2))
        
        self.add_widget(layout)
    
    def on_login(self, instance):
        """Handle login button press"""
        student_id = self.student_id_input.text.strip()
        school_code = self.school_code_input.text.strip()
        offline_mode = self.offline_checkbox.active
        
        if not student_id:
            self.student_id_input.hint_text = 'Student ID required!'
            return
        
        # Store user data in app
        app = self.manager.app
        app.student_id = student_id
        app.school_code = school_code
        app.offline_mode = offline_mode
        
        # Navigate to dashboard
        self.manager.current = 'dashboard'
        
        print(f"Login: Student ID={student_id}, School={school_code}, Offline={offline_mode}")
