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
        
        self.bind(pos=self._update_canvas, size=self._update_canvas)
        self.bind(state=self._on_state)
        
        self._build_ui()

    def _build_ui(self):
        self.clear_widgets()
        
        if self.icon:
            # We use a standard label for icon if it's a unicode/material symbol, 
            # but for now we'll just use a simple label or omit if no font
            icon_lbl = Label(
                text=self.icon, 
                color=self.text_color,
                size_hint_x=None, 
                width='24dp',
                font_name="Roboto" # Fallback
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

    def _update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            if self.state == 'down':
                # Darker when pressed
                r, g, b, a = self.bg_color
                Color(r*0.8, g*0.8, b*0.8, a)
            else:
                Color(*self.bg_color)
                
            from kivy.metrics import dp
            r_val = float(str(RADIUS['xl']).replace('dp', ''))
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(r_val)])

    def _on_state(self, instance, value):
        self._update_canvas()
        
    def on_text(self, instance, value):
        self._build_ui()
        
    def on_icon(self, instance, value):
        self._build_ui()
