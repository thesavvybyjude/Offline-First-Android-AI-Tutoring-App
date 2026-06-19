import sys
import os

# Ensure the root directory is in the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from frontend.main import TutorApp

if __name__ == '__main__':
    TutorApp().run()
