"""Debug launcher - captures all errors and tests imports."""
import sys, os, traceback

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

print("=" * 50)
print("DEBUG: Starting import checks...")
print(f"Python: {sys.executable}")
print(f"CWD: {os.getcwd()}")
print("=" * 50)

# Test each import
imports_ok = True
try:
    import kivy
    print(f"[OK] kivy {kivy.__version__}")
except Exception as e:
    print(f"[FAIL] kivy: {e}")
    imports_ok = False

try:
    from kivy.app import App
    from kivy.core.window import Window
    print(f"[OK] kivy.app, kivy.core.window")
except Exception as e:
    print(f"[FAIL] kivy core: {e}")
    imports_ok = False

try:
    from frontend.theme import get_color, get_font
    print(f"[OK] frontend.theme")
except Exception as e:
    print(f"[FAIL] frontend.theme: {e}")
    traceback.print_exc()
    imports_ok = False

try:
    from frontend.widgets.glass_card import GlassCard
    print(f"[OK] frontend.widgets.glass_card")
except Exception as e:
    print(f"[FAIL] frontend.widgets.glass_card: {e}")
    traceback.print_exc()
    imports_ok = False

try:
    from frontend.widgets.gradient_button import GradientButton
    print(f"[OK] frontend.widgets.gradient_button")
except Exception as e:
    print(f"[FAIL] frontend.widgets.gradient_button: {e}")
    traceback.print_exc()
    imports_ok = False

try:
    from frontend.widgets.bottom_nav import BottomNav
    print(f"[OK] frontend.widgets.bottom_nav")
except Exception as e:
    print(f"[FAIL] frontend.widgets.bottom_nav: {e}")
    traceback.print_exc()
    imports_ok = False

try:
    from frontend.screens.login_screen import LoginScreen
    print(f"[OK] frontend.screens.login_screen")
except Exception as e:
    print(f"[FAIL] frontend.screens.login_screen: {e}")
    traceback.print_exc()
    imports_ok = False

try:
    from frontend.screens.dashboard_screen import DashboardScreen
    print(f"[OK] frontend.screens.dashboard_screen")
except Exception as e:
    print(f"[FAIL] frontend.screens.dashboard_screen: {e}")
    traceback.print_exc()
    imports_ok = False

try:
    from frontend.screens.tutor_chat_screen import TutorChatScreen
    print(f"[OK] frontend.screens.tutor_chat_screen")
except Exception as e:
    print(f"[FAIL] frontend.screens.tutor_chat_screen: {e}")
    traceback.print_exc()
    imports_ok = False

try:
    from frontend.screens.review_screen import ReviewScreen
    print(f"[OK] frontend.screens.review_screen")
except Exception as e:
    print(f"[FAIL] frontend.screens.review_screen: {e}")
    traceback.print_exc()
    imports_ok = False

try:
    from frontend.screens.settings_screen import SettingsScreen
    print(f"[OK] frontend.screens.settings_screen")
except Exception as e:
    print(f"[FAIL] frontend.screens.settings_screen: {e}")
    traceback.print_exc()
    imports_ok = False

try:
    from frontend.app_services import AppServices
    print(f"[OK] frontend.app_services")
except Exception as e:
    print(f"[FAIL] frontend.app_services: {e}")
    traceback.print_exc()
    imports_ok = False

print("=" * 50)
if not imports_ok:
    print("IMPORT FAILURES DETECTED - cannot run app.")
    sys.exit(1)

print("All imports OK! Launching Kivy app...")
print(f"Window will be 360x640")
print("=" * 50)

try:
    from frontend.main import TutorApp
    app = TutorApp()
    app.run()
except Exception as e:
    print(f"\n{'='*50}")
    print(f"APP CRASHED: {e}")
    print(f"{'='*50}")
    traceback.print_exc()
    sys.exit(1)
