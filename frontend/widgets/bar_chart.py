from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.graphics import Color, RoundedRectangle
from kivy.properties import ListProperty
from frontend.theme import get_color, get_font

class BarChart(BoxLayout):
    """
    A simple 7-day activity bar chart using Kivy Canvas.
    data format: [ (day_label, percentage_0_to_1), ... ]
    """
    data = ListProperty([])
    
    def __init__(self, **kwargs):
        self.orientation = 'horizontal'
        self.spacing = '8dp'
        super().__init__(**kwargs)
        self.bind(data=self._build_ui)
        self.bind(pos=self._update_canvas, size=self._update_canvas)

    def _build_ui(self, *args):
        self.clear_widgets()
        if not self.data:
            return
            
        for day, val in self.data:
            # Container for bar + label
            col = BoxLayout(orientation='vertical', spacing='4dp')
            
            # The bar area
            bar_area = Widget(size_hint_y=1)
            # Bind to draw the bar
            with bar_area.canvas.before:
                Color(*get_color("surface-variant"))
                from kivy.metrics import dp
                r = dp(4)
                bg_rect = RoundedRectangle(pos=bar_area.pos, size=bar_area.size, radius=[r, r, 0, 0])
                Color(*get_color("primary"))
                fill_rect = RoundedRectangle(pos=bar_area.pos, size=(bar_area.width, 0), radius=[r, r, 0, 0])
                
            def make_draw_bar(v, bg, fill, rad):
                def draw_bar(instance, *args):
                    bg.pos = instance.pos
                    bg.size = instance.size
                    
                    fill_height = instance.height * v
                    fill.pos = (instance.x, instance.y)
                    fill.size = (instance.width, fill_height)
                return draw_bar
            
            bar_draw_func = make_draw_bar(val, bg_rect, fill_rect, r)
            bar_area.bind(pos=bar_draw_func, size=bar_draw_func)
            col.add_widget(bar_area)
            
            # Label
            font = get_font("label-sm")
            lbl = Label(
                text=day,
                color=get_color("outline"),
                font_name=font["font_name"],
                font_size=font["font_size"],
                size_hint_y=None,
                height='16dp'
            )
            col.add_widget(lbl)
            
            self.add_widget(col)

    def _update_canvas(self, *args):
        pass
