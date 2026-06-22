from kivy.uix.boxlayout import BoxLayout
from kivy.graphics import Color, RoundedRectangle, Line
from frontend.theme import get_color, RADIUS

class GlassCard(BoxLayout):
    """
    A premium card widget with a semi-transparent background and subtle top border,
    simulating a glassmorphism effect in Kivy.
    """
    def __init__(self, **kwargs):
        # Default properties
        self.orientation = kwargs.pop('orientation', 'vertical')
        self.padding = kwargs.pop('padding', '16dp')
        self.spacing = kwargs.pop('spacing', '8dp')
        self.radius = kwargs.pop('radius', RADIUS['xl'])
        
        # Color tokens
        self.bg_color = kwargs.pop('bg_color', get_color("surface-container"))
        self.border_color = kwargs.pop('border_color', get_color("surface-bright"))
        
        # Adjust background alpha for glass effect
        r, g, b, a = self.bg_color
        self.bg_color = (r, g, b, 0.7)  # 70% opacity
        
        # Adjust border alpha
        r, g, b, a = self.border_color
        self.border_color = (r, g, b, 0.3)
        
        super().__init__(**kwargs)
        self.bind(pos=self._update_canvas, size=self._update_canvas)

    def _update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            # Background
            Color(*self.bg_color)
            r_val = float(str(self.radius).replace('dp', ''))
            # Kivy doesn't easily let us pass a string like '16dp' directly to radius in Python code without metrics
            from kivy.metrics import dp
            r_dp = dp(r_val) if isinstance(self.radius, str) else self.radius
            
            RoundedRectangle(pos=self.pos, size=self.size, radius=[r_dp])
            
            # Subtle top border highlight
            Color(*self.border_color)
            Line(rounded_rectangle=(self.x, self.y, self.width, self.height, r_dp), width=1)
