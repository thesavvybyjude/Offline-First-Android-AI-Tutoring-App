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
            # We use a closure to capture the current val
            def draw_bar(instance, v=val, *args):
                instance.canvas.before.clear()
                with instance.canvas.before:
                    # Background track
                    Color(*get_color("surface-variant"))
                    from kivy.metrics import dp
                    r = dp(4)
                    RoundedRectangle(pos=instance.pos, size=instance.size, radius=[r, r, 0, 0])
                    
                    # Fill
                    # Simulate gradient with solid primary
                    Color(*get_color("primary"))
                    fill_height = instance.height * v
                    fill_y = instance.y
                    if fill_height > 0:
                        RoundedRectangle(pos=(instance.x, fill_y), size=(instance.width, fill_height), radius=[r, r, 0, 0])
            
            bar_area.bind(pos=draw_bar, size=draw_bar)
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
