from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.properties import StringProperty
from frontend.theme import get_color, get_font, RADIUS

class StatCard(BoxLayout):
    """
    A bento-style stat card for the dashboard.
    """
    title = StringProperty("TITLE")
    value = StringProperty("0")
    unit = StringProperty("")
    
    def __init__(self, **kwargs):
        self.orientation = 'vertical'
        self.padding = '16dp'
        self.spacing = '8dp'
        
        # Color tokens
        self.bg_color = get_color("surface-container")
        self.border_color = get_color("surface-bright")
        
        # Make glass
        r, g, b, a = self.bg_color
        self.bg_color = (r, g, b, 0.7)
        r, g, b, a = self.border_color
        self.border_color = (r, g, b, 0.3)
        
        super().__init__(**kwargs)
        self.bind(pos=self._update_canvas, size=self._update_canvas)
        self.bind(title=self._build_ui, value=self._build_ui, unit=self._build_ui)
        self._build_ui()

    def _build_ui(self, *args):
        self.clear_widgets()
        
        # Title
        font_sm = get_font("label-sm")
        title_lbl = Label(
            text=self.title.upper(),
            color=get_color("on-surface-variant"),
            font_name=font_sm["font_name"],
            font_size=font_sm["font_size"],
            halign='left',
            valign='top',
            size_hint_y=None,
            height='16dp'
        )
        title_lbl.bind(size=title_lbl.setter('text_size'))
        self.add_widget(title_lbl)
        
        # Spacer
        self.add_widget(BoxLayout(size_hint_y=1))
        
        # Value area
        val_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height='36dp', spacing='4dp')
        
        font_lg = get_font("headline-lg-mobile")
        val_lbl = Label(
            text=self.value,
            color=get_color("primary"),
            font_name=font_lg["font_name"],
            font_size=font_lg["font_size"],
            bold=True,
            size_hint_x=None
        )
        val_lbl.bind(texture_size=val_lbl.setter('size'))
        val_layout.add_widget(val_lbl)
        
        if self.unit:
            unit_lbl = Label(
                text=self.unit,
                color=get_color("on-surface-variant"),
                font_name=font_sm["font_name"],
                font_size=font_sm["font_size"],
                valign='bottom',
                size_hint_x=None
            )
            unit_lbl.bind(texture_size=unit_lbl.setter('size'))
            # Pad bottom to align with baseline
            unit_pad = BoxLayout(orientation='vertical')
            unit_pad.add_widget(BoxLayout(size_hint_y=1))
            unit_pad.add_widget(unit_lbl)
            val_layout.add_widget(unit_pad)
            
        self.add_widget(val_layout)

    def _update_canvas(self, *args):
        from kivy.clock import Clock
        Clock.schedule_once(self._deferred_update_canvas, -1)

    def _deferred_update_canvas(self, dt):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self.bg_color)
            from kivy.metrics import dp
            r_dp = dp(float(str(RADIUS['xl']).replace('dp', '')))
            RoundedRectangle(pos=self.pos, size=self.size, radius=[r_dp])
            
            Color(*self.border_color)
            Line(rounded_rectangle=(self.x, self.y, self.width, self.height, r_dp), width=1)
