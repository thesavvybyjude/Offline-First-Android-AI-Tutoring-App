from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.graphics import Color, RoundedRectangle
from kivy.properties import StringProperty, BooleanProperty
from frontend.theme import get_color, get_font

class ChatBubble(BoxLayout):
    """
    Chat bubble widget with distinct styling for User vs AI.
    """
    text = StringProperty("")
    is_user = BooleanProperty(False)
    
    def __init__(self, **kwargs):
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.padding = ['16dp', '12dp']
        self.spacing = '4dp'
        
        # Let parent handle size_hint_x based on alignment
        super().__init__(**kwargs)
        
        with self.canvas.before:
            self.bg_color_inst = Color(*get_color("user-bubble"))
            self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[0,0,0,0])
            self.line_color = Color(1, 1, 1, 0.1)
            from kivy.graphics import Line
            self.bg_line = Line(rounded_rectangle=(self.x, self.y, self.width, self.height, 0,0,0,0), width=1)
            
        self.bind(pos=self._update_canvas, size=self._update_canvas)
        self.bind(text=self._build_ui)
        self._build_ui()

    def _build_ui(self, *args):
        self.clear_widgets()
        
        font = get_font("body-md")
        
        # If AI, add the avatar/header
        if not self.is_user:
            header = BoxLayout(orientation='horizontal', size_hint_y=None, height='24dp', spacing='8dp')
            
            # Simple colored square as avatar placeholder
            avatar = Label(text="Z", size_hint=(None, None), size=('24dp', '24dp'), 
                           color=get_color("on-primary-container"))
            with avatar.canvas.before:
                Color(*get_color("primary-container"))
                from kivy.metrics import dp
                av_rect = RoundedRectangle(pos=avatar.pos, size=avatar.size, radius=[dp(12)])
            def update_avatar_bg(instance, value):
                av_rect.pos = instance.pos
                av_rect.size = instance.size
            avatar.bind(pos=update_avatar_bg, size=update_avatar_bg)
            
            name = Label(text="Offline AI Tutor", color=get_color("on-surface-variant"),
                         font_name=get_font("label-sm")["font_name"],
                         font_size=get_font("label-sm")["font_size"],
                         halign='left', valign='middle')
            name.bind(size=name.setter('text_size'))
            
            header.add_widget(avatar)
            header.add_widget(name)
            self.add_widget(header)
        
        # Message text
        text_color = get_color("on-surface") if self.is_user else get_color("white")
        
        lbl = Label(
            text=self.text,
            color=text_color,
            font_name=font["font_name"],
            font_size=font["font_size"],
            halign='left',
            valign='top',
            size_hint_y=None,
            markup=True
        )
        lbl.bind(width=lambda *x: lbl.setter('text_size')(lbl, (lbl.width, None)),
                 texture_size=lambda *x: lbl.setter('height')(lbl, lbl.texture_size[1]))
                 
        self.add_widget(lbl)
        
        # Adjust own height based on children
        self.bind(minimum_height=self.setter('height'))
        self._update_canvas()

    def _update_canvas(self, *args):
        if self.is_user:
            self.bg_color_inst.rgba = get_color("user-bubble")
        else:
            self.bg_color_inst.rgba = get_color("secondary-container")
            
        from kivy.metrics import dp
        r = dp(16)
        if self.is_user:
            radius = [r, r, r, dp(2)]
        else:
            radius = [r, r, dp(2), r]
            
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        self.bg_rect.radius = radius
        self.bg_line.rounded_rectangle = (self.x, self.y, self.width, self.height, *radius)
