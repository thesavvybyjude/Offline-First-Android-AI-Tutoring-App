from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.graphics import Color, Rectangle, RoundedRectangle
from frontend.theme import get_color, get_font

class TopBar(BoxLayout):
    """
    Unified top app bar with avatar, branding, and right-side actions.
    """
    def __init__(self, title="OFFLINE AI TUTOR", show_offline=True, show_back=False, **kwargs):
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = '56dp'
        self.padding = ['16dp', '0dp']
        self.spacing = '8dp'
        self.title_text = title
        self.show_offline = show_offline
        self.show_back = show_back
        
        super().__init__(**kwargs)
        
        with self.canvas.before:
            # Background
            Color(*get_color("surface"))
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
            
            # Bottom border
            Color(*get_color("outline-variant"))
            self.border_rect = Rectangle(pos=(self.x, self.y), size=(self.width, 1))
            
        def update_bg(instance, value):
            self.bg_rect.pos = instance.pos
            self.bg_rect.size = instance.size
            self.border_rect.pos = (instance.x, instance.y)
            self.border_rect.size = (instance.width, 1)
        self.bind(pos=update_bg, size=update_bg)
        
        self._build_ui()

    def _build_ui(self):
        self.clear_widgets()
        
        # Left side: Avatar/Back + Brand
        left_box = BoxLayout(orientation='horizontal', spacing='8dp', size_hint_x=1)
        
        # Avatar placeholder (circle)
        avatar = BoxLayout(size_hint=(None, None), size=('32dp', '32dp'), pos_hint={'center_y': 0.5})
        with avatar.canvas.before:
            Color(*get_color("surface-variant"))
            from kivy.metrics import dp
            av_rect = RoundedRectangle(pos=avatar.pos, size=avatar.size, radius=[dp(16)])
        def update_avatar_rect(instance, value):
            av_rect.pos = instance.pos
            av_rect.size = instance.size
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
                text="\ue648", # wifi_off Material Symbol
                color=get_color("primary-fixed-dim"),
                font_name="MaterialSymbols",
                font_size="24sp",
                size_hint_x=None,
                width='48dp'
            )
            self.add_widget(icon)
