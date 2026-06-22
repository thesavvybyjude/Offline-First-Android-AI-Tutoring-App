from kivy.uix.button import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.graphics import Color, RoundedRectangle
from kivy.properties import StringProperty, ListProperty
from frontend.theme import get_color, get_font, RADIUS

class GradientButton(ButtonBehavior, BoxLayout):
    """
    A premium action button with primary colors and rounded corners.
    """
    text = StringProperty("")
    icon = StringProperty("")
    bg_color = ListProperty(get_color("primary-container"))
    text_color = ListProperty(get_color("on-primary-container"))

    def __init__(self, **kwargs):
        self.orientation = 'horizontal'
        self.padding = ['16dp', '0dp']
        self.spacing = '8dp'
        self.size_hint_y = None
        self.height = '48dp' # touch-target
        super().__init__(**kwargs)
        
        with self.canvas.before:
            self.bg_color_inst = Color(*self.bg_color)
            from kivy.metrics import dp
            r_val = float(str(RADIUS['xl']).replace('dp', ''))
            self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(r_val)])
            
        def update_bg(instance, value):
            self.bg_rect.pos = instance.pos
            self.bg_rect.size = instance.size
        self.bind(pos=update_bg, size=update_bg)
        self.bind(state=self._on_state)
        
        self._build_ui()

    def _build_ui(self):
        self.clear_widgets()
        
        if self.icon:
            icon_lbl = Label(
                text=self.icon, 
                color=self.text_color,
                size_hint_x=None, 
                width='24dp',
                font_name="MaterialSymbols" # Uses Material Symbols
            )
            self.add_widget(icon_lbl)
            
        font = get_font("label-lg")
        lbl = Label(
            text=self.text,
            color=self.text_color,
            font_name=font["font_name"],
            font_size=font["font_size"],
            bold=True
        )
        self.add_widget(lbl)

    def _on_state(self, instance, value):
        from kivy.animation import Animation
        if self.state == 'down':
            # Darker and smaller
            anim = Animation(opacity=0.7, duration=0.1)
            anim.start(self)
        else:
            anim = Animation(opacity=1.0, duration=0.2)
            anim.start(self)
        
    def on_text(self, instance, value):
        if getattr(self, 'canvas', None) is not None:
            self._build_ui()
        
    def on_icon(self, instance, value):
        if getattr(self, 'canvas', None) is not None:
            self._build_ui()
