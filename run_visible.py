"""Launch script that forces the Kivy window to top-left of screen, always on top."""
import os, sys

# Set Kivy environment BEFORE any kivy import
os.environ['KIVY_WINDOW'] = 'sdl2'
os.environ['KIVY_GL_BACKEND'] = 'glew'

# Force window position via Kivy config before importing kivy
os.environ['KIVY_LOG_LEVEL'] = 'info'

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Configure Kivy to place the window at a known position
from kivy.config import Config
Config.set('graphics', 'position', 'custom')
Config.set('graphics', 'left', '100')
Config.set('graphics', 'top', '100')
Config.set('graphics', 'width', '400')
Config.set('graphics', 'height', '700')
Config.set('graphics', 'borderless', '0')
Config.set('graphics', 'resizable', '1')
Config.set('graphics', 'window_state', 'visible')
Config.set('kivy', 'window_icon', '')

from frontend.main import TutorApp

print("=" * 50)
print("LAUNCHING APP - Window should appear at (100, 100)")
print("Window size: 400x700")
print("=" * 50)

TutorApp().run()
