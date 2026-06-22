from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.graphics import Color, Rectangle, RoundedRectangle
from frontend.theme import get_color, get_font

class TopBar(BoxLayout):
    """
    Unified top app bar with avatar, branding, and right-side actions.
    """
    def __init__(self, title="ZIDON AI", show_offline=True, **kwargs):
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = '64dp'
        self.padding = ['16dp', '0dp']
        self.spacing = '8dp'
        self.title_text = title
        self.show_offline = show_offline
        
        super().__init__(**kwargs)
        self.bind(pos=self._update_canvas, size=self._update_canvas)
        self._build_ui()

    def _build_ui(self):
        # Left side: Avatar + Brand
        left_box = BoxLayout(orientation='horizontal', spacing='8dp', size_hint_x=1)
        
        # Avatar placeholder (circle)
        avatar = BoxLayout(size_hint=(None, None), size=('32dp', '32dp'), pos_hint={'center_y': 0.5})
        with avatar.canvas.before:
            Color(*get_color("surface-variant"))
            from kivy.metrics import dp
            RoundedRectangle(pos=avatar.pos, size=avatar.size, radius=[dp(16)])
        # Bind pos/size update
        def update_avatar_rect(instance, value):
            instance.canvas.before.clear()
            with instance.canvas.before:
                Color(*get_color("surface-variant"))
                RoundedRectangle(pos=instance.pos, size=instance.size, radius=[dp(16)])
        avatar.bind(pos=update_avatar_rect, size=update_avatar_rect)
        
        left_box.add_widget(avatar)
        
        # Brand Name
        font = get_font("headline-md")
        brand = Label(
            text=self.title_text,
            color=get_color("primary-fixed-dim"),
            font_name=font["font_name"],
            font_size=font["font_size"],
            bold=True,
            halign='left',
            valign='middle'
        )
        brand.bind(size=brand.setter('text_size'))
        left_box.add_widget(brand)
        self.add_widget(left_box)
        
        # Right side: Actions
        if self.show_offline:
            # Offline icon
            icon = Label(
                text="O", # Placeholder for offline icon
                color=get_color("primary-fixed-dim"),
                size_hint_x=None,
                width='48dp'
            )
            self.add_widget(icon)

    def _update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            # Background
            Color(*get_color("surface"))
            Rectangle(pos=self.pos, size=self.size)
            
            # Bottom border
            Color(*get_color("outline-variant"))
            Rectangle(pos=(self.x, self.y), size=(self.width, 1))
