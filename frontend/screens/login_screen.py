"""
Login Screen
Premium student authentication and offline mode selection
"""

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.switch import Switch
from kivy.properties import ObjectProperty
from kivy.graphics import Color, RoundedRectangle, Line, Rectangle
from kivy.app import App
from kivy.metrics import dp

from frontend.theme import get_color, get_font, RADIUS
from frontend.widgets.glass_card import GlassCard
from frontend.widgets.gradient_button import GradientButton

class LoginScreen(Screen):
    """Premium login screen matching mockup"""
    
    student_id_input = ObjectProperty(None)
    school_code_input = ObjectProperty(None)
    offline_switch = ObjectProperty(None)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'login'
        self.bind(pos=self._update_bg, size=self._update_bg)
        self._build_ui()
        
    def _update_bg(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*get_color("background"))
            Rectangle(pos=self.pos, size=self.size)
            
            # Subtle top gradient/glow
            Color(*get_color("primary-container")[:3] + (0.1,))
            RoundedRectangle(pos=(self.center_x - dp(150), self.top - dp(300)), 
                           size=(dp(300), dp(300)), radius=[dp(150)])

    def _build_ui(self):
        # Main layout
        main_layout = BoxLayout(orientation='vertical', padding=['24dp', '48dp', '24dp', '24dp'], spacing='32dp')
        
        # Header (Logo + Brand)
        header = BoxLayout(orientation='horizontal', size_hint_y=None, height='48dp', spacing='12dp', pos_hint={'center_x': 0.5})
        
        logo = Label(text="Z", color=get_color("on-primary-container"), size_hint_x=None, width='48dp')
        with logo.canvas.before:
            Color(*get_color("primary-container"))
            RoundedRectangle(pos=logo.pos, size=logo.size, radius=[dp(24)])
        logo.bind(pos=self._update_widget_canvas, size=self._update_widget_canvas)
        
        brand_font = get_font("headline-md")
        brand = Label(
            text="ZIDON AI",
            color=get_color("primary-fixed-dim"),
            font_name=brand_font["font_name"],
            font_size=brand_font["font_size"],
            bold=True,
            size_hint_x=None,
            width='120dp'
        )
        
        # Center header
        h_container = AnchorLayout(anchor_x='center', size_hint_y=None, height='48dp')
        h_box = BoxLayout(orientation='horizontal', size_hint_x=None, width='180dp', spacing='12dp')
        h_box.add_widget(logo)
        h_box.add_widget(brand)
        h_container.add_widget(h_box)
        main_layout.add_widget(h_container)
        
        # Hero Image/Illustration Area
        hero = FloatLayout(size_hint_y=None, height='200dp')
        # Circle bg
        circle = Label(size_hint=(None, None), size=('160dp', '160dp'), pos_hint={'center_x': 0.5, 'center_y': 0.5})
        with circle.canvas.before:
            Color(*get_color("surface-container-high"))
            RoundedRectangle(pos=circle.pos, size=circle.size, radius=[dp(80)])
            Color(*get_color("outline-variant"))
            Line(circle=(circle.center_x, circle.center_y, dp(80)), width=1)
        circle.bind(pos=self._update_circle, size=self._update_circle)
        
        # Offline badge
        badge = BoxLayout(orientation='horizontal', size_hint=(None, None), size=('120dp', '28dp'), 
                         pos_hint={'center_x': 0.7, 'y': 0.1}, padding=['8dp', '4dp'], spacing='4dp')
        with badge.canvas.before:
            Color(*get_color("surface-container-highest"))
            RoundedRectangle(pos=badge.pos, size=badge.size, radius=[dp(14)])
            Color(*get_color("tertiary-fixed-dim")[:3] + (0.5,))
            Line(rounded_rectangle=(badge.x, badge.y, badge.width, badge.height, dp(14)), width=1)
        badge.bind(pos=self._update_badge, size=self._update_badge)
        
        lbl_badge = Label(text="Offline Ready", color=get_color("tertiary-fixed-dim"),
                         font_name=get_font("label-sm")["font_name"], font_size=get_font("label-sm")["font_size"], bold=True)
        badge.add_widget(lbl_badge)
        
        hero.add_widget(circle)
        hero.add_widget(badge)
        main_layout.add_widget(hero)
        
        # Typography header
        typo_box = BoxLayout(orientation='vertical', size_hint_y=None, height='80dp', spacing='8dp')
        title_font = get_font("headline-lg-mobile")
        title = Label(
            text="Learn Smarter.\n[color=#b4c5ff]Anywhere.[/color]",
            markup=True,
            font_name=title_font["font_name"],
            font_size=title_font["font_size"],
            bold=True,
            halign='center'
        )
        subtitle = Label(
            text="Sign in to access your AI tutor.",
            color=get_color("on-surface-variant"),
            font_name=get_font("body-lg")["font_name"],
            font_size=get_font("body-lg")["font_size"],
            halign='center'
        )
        typo_box.add_widget(title)
        typo_box.add_widget(subtitle)
        main_layout.add_widget(typo_box)
        
        # Form Container (GlassCard)
        form = GlassCard(orientation='vertical', spacing='16dp', size_hint_y=None, height='320dp')
        
        # Student ID
        id_box = BoxLayout(orientation='vertical', size_hint_y=None, height='70dp', spacing='4dp')
        id_lbl = Label(text="Student ID", color=get_color("on-surface-variant"), font_name=get_font("label-sm")["font_name"],
                      font_size=get_font("label-sm")["font_size"], halign='left', size_hint_y=None, height='20dp')
        id_lbl.bind(size=id_lbl.setter('text_size'))
        
        self.student_id_input = TextInput(
            hint_text='Enter your ID',
            multiline=False,
            size_hint_y=None,
            height='48dp',
            background_color=get_color("surface"),
            foreground_color=get_color("on-surface"),
            cursor_color=get_color("primary"),
            padding=['16dp', '14dp']
        )
        id_box.add_widget(id_lbl)
        id_box.add_widget(self.student_id_input)
        form.add_widget(id_box)
        
        # School Code
        sc_box = BoxLayout(orientation='vertical', size_hint_y=None, height='70dp', spacing='4dp')
        sc_lbl = Label(text="School Code", color=get_color("on-surface-variant"), font_name=get_font("label-sm")["font_name"],
                      font_size=get_font("label-sm")["font_size"], halign='left', size_hint_y=None, height='20dp')
        sc_lbl.bind(size=sc_lbl.setter('text_size'))
        
        self.school_code_input = TextInput(
            hint_text='e.g. UNILAG',
            multiline=False,
            size_hint_y=None,
            height='48dp',
            background_color=get_color("surface"),
            foreground_color=get_color("on-surface"),
            cursor_color=get_color("primary"),
            padding=['16dp', '14dp']
        )
        sc_box.add_widget(sc_lbl)
        sc_box.add_widget(self.school_code_input)
        form.add_widget(sc_box)
        
        # Offline Toggle Row
        off_box = BoxLayout(orientation='horizontal', size_hint_y=None, height='56dp', padding=['12dp', '0dp'])
        with off_box.canvas.before:
            Color(*get_color("surface-container-low"))
            RoundedRectangle(pos=off_box.pos, size=off_box.size, radius=[dp(8)])
        off_box.bind(pos=self._update_off_box, size=self._update_off_box)
        
        off_text_box = BoxLayout(orientation='vertical', padding=['0dp', '8dp'])
        t1 = Label(text="Continue Offline", color=get_color("on-surface"), font_name=get_font("label-lg")["font_name"],
                  font_size=get_font("label-lg")["font_size"], halign='left', bold=True)
        t1.bind(size=t1.setter('text_size'))
        t2 = Label(text="Sync data later", color=get_color("on-surface-variant"), font_name=get_font("label-sm")["font_name"],
                  font_size=get_font("label-sm")["font_size"], halign='left')
        t2.bind(size=t2.setter('text_size'))
        off_text_box.add_widget(t1)
        off_text_box.add_widget(t2)
        
        self.offline_switch = Switch(active=True, size_hint_x=None, width='60dp')
        
        off_box.add_widget(off_text_box)
        off_box.add_widget(self.offline_switch)
        form.add_widget(off_box)
        
        # Submit Button
        btn = GradientButton(text="Sign In to ZIDON")
        btn.bind(on_release=self.on_login)
        form.add_widget(btn)
        
        main_layout.add_widget(form)
        
        # Need help
        help_lbl = Label(text="Need help logging in?", color=get_color("primary-fixed-dim"),
                        font_name=get_font("label-sm")["font_name"], font_size=get_font("label-sm")["font_size"],
                        size_hint_y=None, height='20dp')
        main_layout.add_widget(help_lbl)
        
        self.add_widget(main_layout)

    def _update_widget_canvas(self, instance, value):
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(*get_color("primary-container"))
            RoundedRectangle(pos=instance.pos, size=instance.size, radius=[dp(24)])

    def _update_circle(self, instance, value):
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(*get_color("surface-container-high"))
            RoundedRectangle(pos=instance.pos, size=instance.size, radius=[dp(80)])
            Color(*get_color("outline-variant"))
            Line(circle=(instance.center_x, instance.center_y, dp(80)), width=1)

    def _update_badge(self, instance, value):
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(*get_color("surface-container-highest"))
            RoundedRectangle(pos=instance.pos, size=instance.size, radius=[dp(14)])
            Color(*get_color("tertiary-fixed-dim")[:3] + (0.5,))
            Line(rounded_rectangle=(instance.x, instance.y, instance.width, instance.height, dp(14)), width=1)

    def _update_off_box(self, instance, value):
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(*get_color("surface-container-low"))
            RoundedRectangle(pos=instance.pos, size=instance.size, radius=[dp(8)])

    def on_login(self, instance):
        """Handle login button press"""
        student_id = self.student_id_input.text.strip()
        school_code = self.school_code_input.text.strip()
        offline_mode = self.offline_switch.active
        
        if not student_id:
            self.student_id_input.hint_text = 'Student ID required!'
            return

        if len(student_id) < 2:
            self.student_id_input.hint_text = 'ID must be >= 2 chars'
            self.student_id_input.text = ''
            return
        
        # Store user data in app and bootstrap DB + AI
        app = App.get_running_app()
        display_name = student_id
        app.bootstrap_student(student_id, display_name, school_code)
        app.offline_mode = offline_mode

        # Navigate to dashboard
        self.manager.current = "dashboard"
        print(f"Login: Student ID={student_id}, School={school_code}, Offline={offline_mode}")
