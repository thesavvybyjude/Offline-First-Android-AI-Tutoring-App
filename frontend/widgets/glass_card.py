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
        with self.canvas.before:
            # Faux Drop shadow
            r_val = float(str(self.radius).replace('dp', ''))
            from kivy.metrics import dp
            r_dp = dp(r_val) if isinstance(self.radius, str) else self.radius
            
            # Shadow layers
            Color(0, 0, 0, 0.05)
            self.shadow1 = RoundedRectangle(pos=(self.x, self.y - dp(2)), size=self.size, radius=[r_dp])
            Color(0, 0, 0, 0.03)
            self.shadow2 = RoundedRectangle(pos=(self.x, self.y - dp(4)), size=(self.width, self.height + dp(2)), radius=[r_dp])
            
            # Background
            Color(*self.bg_color)
            self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[r_dp])
            
            # Subtle top border highlight
            Color(*self.border_color)
            self.border_line = Line(rounded_rectangle=(self.x, self.y, self.width, self.height, r_dp), width=1)
            
        def update_bg(instance, value):
            self.shadow1.pos = (instance.x, instance.y - dp(2))
            self.shadow1.size = instance.size
            self.shadow2.pos = (instance.x, instance.y - dp(4))
            self.shadow2.size = (instance.width, instance.height + dp(2))
            self.bg_rect.pos = instance.pos
            self.bg_rect.size = instance.size
            self.border_line.rounded_rectangle = (instance.x, instance.y, instance.width, instance.height, r_dp)
        
        self.bind(pos=update_bg, size=update_bg)
