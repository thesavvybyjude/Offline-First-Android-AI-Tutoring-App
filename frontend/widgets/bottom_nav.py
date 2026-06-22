from kivy.uix.boxlayout import BoxLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.graphics import Color, RoundedRectangle, Rectangle
from kivy.uix.label import Label
from kivy.properties import StringProperty, BooleanProperty, ObjectProperty
from frontend.theme import get_color, get_font

class NavTab(ButtonBehavior, BoxLayout):
    text = StringProperty("")
    icon = StringProperty("")
    active = BooleanProperty(False)
    
    def __init__(self, **kwargs):
        self.orientation = 'vertical'
        self.padding = ['0dp', '8dp']
        self.spacing = '2dp'
        super().__init__(**kwargs)
        
        with self.canvas.before:
            self.bg_color_inst = Color(0, 0, 0, 0)
            self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[8])
            
        def update_bg(instance, value):
            self.bg_rect.pos = instance.pos
            self.bg_rect.size = instance.size
        self.bind(pos=update_bg, size=update_bg)
        self.bind(state=self._on_state)
        
        self.bind(active=self._build_ui)
        self._build_ui()

    def _build_ui(self, *args):
        self.clear_widgets()
        
        # Colors based on state
        color = get_color("white") if self.active else get_color("on-surface-variant")
        
        # Icon wrapper for the pill background
        from kivy.uix.anchorlayout import AnchorLayout
        icon_wrapper = AnchorLayout(anchor_x='center', anchor_y='center', size_hint_y=None, height='32dp')
        
        if self.active:
            from kivy.metrics import dp
            with icon_wrapper.canvas.before:
                r, g, b, a = get_color("secondary-container")
                Color(r, g, b, a)
                self.active_pill = RoundedRectangle(size=(dp(64), dp(32)), radius=[dp(16)])
            def update_pill(instance, value):
                self.active_pill.pos = (instance.center_x - dp(32), instance.center_y - dp(16))
            icon_wrapper.bind(pos=update_pill, size=update_pill)
        
        icon_lbl = Label(
            text=self.icon,
            color=color,
            font_name="MaterialSymbols",
            font_size='24sp',
            size_hint=(None, None),
            size=('24dp', '24dp')
        )
        icon_wrapper.add_widget(icon_lbl)
        self.add_widget(icon_wrapper)
        
        # Text
        font = get_font("label-sm")
        lbl = Label(
            text=self.text,
            color=color,
            font_name=font["font_name"],
            font_size=font["font_size"],
            size_hint_y=None,
            height='16dp',
            bold=self.active
        )
        self.add_widget(lbl)

    def _on_state(self, instance, value):
        from kivy.animation import Animation
        if self.state == 'down':
            r, g, b, a = get_color("surface-variant")
            self.bg_color_inst.rgba = (r, g, b, a)
        else:
            self.bg_color_inst.rgba = (0, 0, 0, 0)

class BottomNav(BoxLayout):
    """
    Persistent bottom navigation bar.
    Fires 'on_tab_select' event.
    """
    current_tab = StringProperty("dashboard")
    
    def __init__(self, **kwargs):
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = '64dp'
        
        # Register event
        self.register_event_type('on_tab_select')
        
        super().__init__(**kwargs)
        
        with self.canvas.before:
            # Background
            Color(*get_color("surface-container"))
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
            
            # Top border
            r, g, b, a = get_color("outline-variant")
            Color(r, g, b, 0.5)
            self.border_rect = Rectangle(pos=(self.x, self.top - 1), size=(self.width, 1))
            
        def update_bg(instance, value):
            self.bg_rect.pos = instance.pos
            self.bg_rect.size = instance.size
            self.border_rect.pos = (instance.x, instance.top - 1)
            self.border_rect.size = (instance.width, 1)
        self.bind(pos=update_bg, size=update_bg)
        
        self._build_tabs()

    def _build_tabs(self):
        self.clear_widgets()
        
        # Material Symbols unicode mapping
        tabs = [
            {"id": "dashboard", "text": "Home", "icon": "\ue88a"}, # home
            {"id": "chat", "text": "Chat", "icon": "\ue0ca"}, # chat
            {"id": "review", "text": "Study", "icon": "\ue666"}, # auto_stories
            {"id": "settings", "text": "Settings", "icon": "\ue8b8"} # settings
        ]
        
        for tab in tabs:
            tab_widget = NavTab(
                text=tab["text"],
                icon=tab["icon"],
                active=(self.current_tab == tab["id"])
            )
            tab_widget.bind(on_release=lambda instance, tid=tab["id"]: self.dispatch('on_tab_select', tid))
            self.add_widget(tab_widget)

    def on_tab_select(self, tab_id):
        # Override this in app shell to handle navigation
        pass
        
    def on_current_tab(self, instance, value):
        if getattr(self, 'canvas', None) is not None:
            self._build_tabs()
