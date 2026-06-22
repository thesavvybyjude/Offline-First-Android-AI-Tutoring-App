"""
ZIDON AI - UI Theme & Design System
Centralized definitions for colors, typography, and spacing.
"""

from kivy.utils import get_color_from_hex

# --- Colors (RGBA tuples via hex conversion) ---
# Extracted from Tailwind configuration
COLORS = {
    "background": get_color_from_hex("#0b1326"),
    "surface": get_color_from_hex("#0b1326"),
    "surface-container": get_color_from_hex("#171f33"),
    "surface-container-low": get_color_from_hex("#131b2e"),
    "surface-container-high": get_color_from_hex("#222a3d"),
    "surface-container-highest": get_color_from_hex("#2d3449"),
    "surface-variant": get_color_from_hex("#2d3449"),
    "surface-bright": get_color_from_hex("#31394d"),
    
    "primary": get_color_from_hex("#b4c5ff"),
    "primary-container": get_color_from_hex("#2563eb"),
    "primary-fixed-dim": get_color_from_hex("#b4c5ff"),
    "on-primary-container": get_color_from_hex("#eeefff"),
    
    "secondary": get_color_from_hex("#d2bbff"),
    "secondary-container": get_color_from_hex("#6001d1"),
    "secondary-fixed-dim": get_color_from_hex("#d2bbff"),
    
    "tertiary": get_color_from_hex("#4ae176"),
    "tertiary-fixed": get_color_from_hex("#6bff8f"),
    "tertiary-fixed-dim": get_color_from_hex("#4ae176"),
    
    "on-surface": get_color_from_hex("#dae2fd"),
    "on-surface-variant": get_color_from_hex("#c3c6d7"),
    "on-background": get_color_from_hex("#dae2fd"),
    
    "outline": get_color_from_hex("#8d90a0"),
    "outline-variant": get_color_from_hex("#434655"),
    
    "error": get_color_from_hex("#ffb4ab"),
    "error-container": get_color_from_hex("#93000a"),
    
    "user-bubble": get_color_from_hex("#1E293B"),
    "white": get_color_from_hex("#ffffff"),
    "transparent": (0, 0, 0, 0)
}

# --- Typography ---
# Uses Manrope font family, fallback to Roboto if not loaded
FONTS = {
    "headline-lg": {"font_name": "Manrope-Bold", "font_size": "32sp"},
    "headline-lg-mobile": {"font_name": "Manrope-Bold", "font_size": "28sp"},
    "headline-md": {"font_name": "Manrope-SemiBold", "font_size": "24sp"},
    "headline-sm": {"font_name": "Manrope-SemiBold", "font_size": "20sp"},
    "body-lg": {"font_name": "Manrope-Regular", "font_size": "16sp"},
    "body-md": {"font_name": "Manrope-Regular", "font_size": "14sp"},
    "label-lg": {"font_name": "Manrope-SemiBold", "font_size": "14sp"},
    "label-sm": {"font_name": "Manrope-Medium", "font_size": "12sp"},
}

# --- Spacing ---
SPACING = {
    "base": "4dp",
    "xs": "8dp",
    "sm": "12dp",
    "md": "16dp",
    "lg": "24dp",
    "xl": "32dp",
    "touch-target": "48dp",
}

# --- Border Radius ---
RADIUS = {
    "default": "4dp",
    "lg": "8dp",
    "xl": "12dp",
    "2xl": "16dp",
    "full": "9999dp",
}

def get_color(name: str) -> tuple[float, float, float, float]:
    """Get color RGBA tuple by design token name."""
    return COLORS.get(name, COLORS["error"])

def get_font(style: str) -> dict[str, str]:
    """Get font dictionary (font_name, font_size) by style name."""
    return FONTS.get(style, FONTS["body-md"])
