from kivy.uix.boxlayout import BoxLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.graphics import Color, RoundedRectangle
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
        self.bind(active=self._build_ui)
        self.bind(pos=self._update_canvas, size=self._update_canvas, state=self._update_canvas)
        self._build_ui()

    def _build_ui(self, *args):
        self.clear_widgets()
        
        # Colors based on state
        color = get_color("primary") if self.active else get_color("on-surface-variant")
        
        # Icon (Using a placeholder unicode/text for now, can be an Image if pngs are used)
        icon_lbl = Label(
            text=self.icon,
            color=color,
            font_size='24sp',
            size_hint_y=None,
            height='28dp'
        )
        self.add_widget(icon_lbl)
        
        # Text
        font = get_font("label-sm")
        lbl = Label(
            text=self.text,
            color=color,
            font_name=font["font_name"],
            font_size=font["font_size"],
            size_hint_y=None,
            height='16dp'
        )
        self.add_widget(lbl)

    def _update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            if self.state == 'down':
                r, g, b, a = get_color("surface-variant")
                Color(r, g, b, a)
                RoundedRectangle(pos=self.pos, size=self.size, radius=[8])

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
        self.bind(pos=self._update_canvas, size=self._update_canvas)
        self._build_tabs()

    def _build_tabs(self):
        self.clear_widgets()
        
        tabs = [
            {"id": "dashboard", "text": "Home", "icon": "H"},
            {"id": "chat", "text": "Chat", "icon": "C"},
            {"id": "review", "text": "Study", "icon": "S"},
            {"id": "settings", "text": "Settings", "icon": "O"}
        ]
        
        for tab in tabs:
            tab_widget = NavTab(
                text=tab["text"],
                icon=tab["icon"],
                active=(self.current_tab == tab["id"])
            )
            # Use default arg to bind correct id in lambda
            tab_widget.bind(on_release=lambda instance, tid=tab["id"]: self.dispatch('on_tab_select', tid))
            self.add_widget(tab_widget)

    def _update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            # Top border
            r, g, b, a = get_color("outline-variant")
            Color(r, g, b, 0.5)
            from kivy.graphics import Rectangle
            Rectangle(pos=(self.x, self.top - 1), size=(self.width, 1))
            
            # Background
            Color(*get_color("surface-container"))
            Rectangle(pos=self.pos, size=self.size)

    def on_tab_select(self, tab_id):
        # Override this in app shell to handle navigation
        pass
        
    def on_current_tab(self, instance, value):
        self._build_tabs()
