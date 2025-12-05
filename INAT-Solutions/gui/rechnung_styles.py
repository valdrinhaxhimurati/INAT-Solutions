# -*- coding: utf-8 -*-
"""
Invoice Style Definitions for PDF Layouts.
Each style defines colors, fonts, header designs and table appearance.
"""
from reportlab.lib import colors
from reportlab.lib.units import mm

# ============================================================================
# AVAILABLE FONTS (ReportLab built-in)
# ============================================================================
AVAILABLE_FONTS = {
    "Helvetica": "Helvetica",
    "Helvetica-Bold": "Helvetica-Bold",
    "Times-Roman": "Times-Roman",
    "Times-Bold": "Times-Bold",
    "Courier": "Courier",
    "Courier-Bold": "Courier-Bold",
}

# ============================================================================
# STYLE DEFINITIONS - Inspired by modern invoice templates
# ============================================================================

RECHNUNG_STYLES = {
    # ========== 1. CLASSIC - Clean minimal, inspired by German invoice ==========
    "classic": {
        "name": "Classic",
        "beschreibung": "Clean minimal design with subtle table lines",
        "vorschau_farbe": "#1F2937",
        
        # Font
        "font": "Helvetica",
        "font_bold": "Helvetica-Bold",
        
        # Colors - Black/Gray
        "header_bg": colors.Color(0.12, 0.12, 0.12),
        "header_text": colors.white,
        "zeile_alternierend": None,
        "linien_farbe": colors.Color(0.85, 0.85, 0.85),
        "akzent_farbe": colors.Color(0.12, 0.12, 0.12),
        
        # Table style
        "tabelle_gitter": False,
        "linien_staerke": 0.5,
        "header_fett": True,
        "nur_horizontale_linien": True,
        "header_linie_unten": True,
        
        # Total box
        "total_box": False,
        
        # Header design - Simple top and bottom lines
        "kopf_design": "double_lines",
        "kopf_farbe": colors.Color(0.12, 0.12, 0.12),
    },
    
    # ========== 2. CORPORATE - Dark blue with orange accent (Bild 1) ==========
    "corporate": {
        "name": "Corporate",
        "beschreibung": "Professional dark blue with orange diagonal accent",
        "vorschau_farbe": "#1E3A5F",
        
        # Font
        "font": "Helvetica",
        "font_bold": "Helvetica-Bold",
        
        # Colors - Dark blue + Orange
        "header_bg": colors.Color(0.96, 0.52, 0.09),  # Orange header
        "header_text": colors.white,
        "zeile_alternierend": colors.Color(0.98, 0.98, 0.99),
        "linien_farbe": colors.Color(0.9, 0.9, 0.9),
        "akzent_farbe": colors.Color(0.12, 0.23, 0.37),  # Dark blue
        "akzent_farbe2": colors.Color(0.96, 0.52, 0.09),  # Orange
        
        # Table style
        "tabelle_gitter": False,
        "linien_staerke": 0.5,
        "header_fett": True,
        "nur_horizontale_linien": True,
        
        # Total box - Orange
        "total_box": True,
        "total_bg": colors.Color(0.96, 0.52, 0.09),
        "total_text": colors.white,
        
        # Header design - Diagonal corners + footer
        "kopf_design": "diagonal_corners",
        "kopf_farbe": colors.Color(0.12, 0.23, 0.37),
        "kopf_farbe2": colors.Color(0.96, 0.52, 0.09),
    },
    
    # ========== 3. EXECUTIVE - Red/Gray with side text (Bild 2) ==========
    "executive": {
        "name": "Executive",
        "beschreibung": "Bold red accents with right side stripe",
        "vorschau_farbe": "#DC2626",
        
        # Font
        "font": "Times-Roman",
        "font_bold": "Times-Bold",
        
        # Colors - Red + Dark Gray
        "header_bg": colors.Color(0.86, 0.15, 0.15),  # Red
        "header_text": colors.white,
        "zeile_alternierend": None,
        "linien_farbe": colors.Color(0.85, 0.85, 0.85),
        "akzent_farbe": colors.Color(0.86, 0.15, 0.15),
        "akzent_farbe2": colors.Color(0.25, 0.25, 0.25),  # Dark gray
        
        # Table style
        "tabelle_gitter": False,
        "linien_staerke": 0.5,
        "header_fett": True,
        "nur_horizontale_linien": True,
        
        # Total box
        "total_box": True,
        "total_bg": colors.Color(0.86, 0.15, 0.15),
        "total_text": colors.white,
        
        # Header design - Right stripe + diagonal corner
        "kopf_design": "right_stripe_diagonal",
        "kopf_farbe": colors.Color(0.86, 0.15, 0.15),
        "kopf_farbe2": colors.Color(0.25, 0.25, 0.25),
    },
    
    # ========== 4. MODERN - Purple/Blue gradient style (Bild 4) ==========
    "modern": {
        "name": "Modern",
        "beschreibung": "Purple-blue gradient with diagonal stripes",
        "vorschau_farbe": "#7C3AED",
        
        # Font
        "font": "Helvetica",
        "font_bold": "Helvetica-Bold",
        
        # Colors - Purple/Blue
        "header_bg": colors.Color(0.29, 0.18, 0.55),  # Purple
        "header_text": colors.white,
        "zeile_alternierend": colors.Color(0.98, 0.98, 1.0),
        "linien_farbe": colors.Color(0.9, 0.88, 0.95),
        "akzent_farbe": colors.Color(0.29, 0.18, 0.55),
        "akzent_farbe2": colors.Color(0.15, 0.35, 0.65),  # Blue
        
        # Table style
        "tabelle_gitter": False,
        "linien_staerke": 0.5,
        "header_fett": True,
        "nur_horizontale_linien": True,
        
        # Total box
        "total_box": True,
        "total_bg": colors.Color(0.29, 0.18, 0.55),
        "total_text": colors.white,
        
        # Header design - Gradient bar top + bottom with stripes
        "kopf_design": "gradient_bars",
        "kopf_farbe": colors.Color(0.29, 0.18, 0.55),
        "kopf_farbe2": colors.Color(0.15, 0.35, 0.65),
    },
    
    # ========== 5. MINIMAL - Ultra clean (Bild 5) ==========
    "minimal": {
        "name": "Minimal",
        "beschreibung": "Ultra-clean design with only essential lines",
        "vorschau_farbe": "#374151",
        
        # Font
        "font": "Helvetica",
        "font_bold": "Helvetica-Bold",
        
        # Colors - Pure black/gray
        "header_bg": colors.Color(0.15, 0.15, 0.15),
        "header_text": colors.white,
        "zeile_alternierend": None,
        "linien_farbe": colors.Color(0.75, 0.75, 0.75),
        "akzent_farbe": colors.Color(0.15, 0.15, 0.15),
        
        # Table style - Very minimal
        "tabelle_gitter": False,
        "linien_staerke": 0.75,
        "header_fett": True,
        "nur_horizontale_linien": True,
        "header_linie_unten": True,
        
        # Total box
        "total_box": False,
        
        # Header design - None, just content
        "kopf_design": None,
    },
    
    # ========== 6. ELEGANT - Soft curves (Bild 6) ==========
    "elegant": {
        "name": "Elegant",
        "beschreibung": "Flowing wave design with soft colors",
        "vorschau_farbe": "#EC4899",
        
        # Font
        "font": "Times-Roman",
        "font_bold": "Times-Bold",
        
        # Colors - Pink/Teal
        "header_bg": colors.Color(0.93, 0.29, 0.60),  # Pink
        "header_text": colors.white,
        "zeile_alternierend": colors.Color(0.99, 0.97, 0.98),
        "linien_farbe": colors.Color(0.92, 0.88, 0.90),
        "akzent_farbe": colors.Color(0.93, 0.29, 0.60),
        "akzent_farbe2": colors.Color(0.06, 0.60, 0.55),  # Teal
        
        # Table style
        "tabelle_gitter": False,
        "linien_staerke": 0.5,
        "header_fett": True,
        "nur_horizontale_linien": True,
        
        # Total box
        "total_box": True,
        "total_bg": colors.Color(0.06, 0.60, 0.55),
        "total_text": colors.white,
        
        # Header design - Wave corners
        "kopf_design": "wave_corners",
        "kopf_farbe": colors.Color(0.93, 0.29, 0.60),
        "kopf_farbe2": colors.Color(0.06, 0.60, 0.55),
    },
    
    # ========== 7. SWISS - Clean red accent, precision ==========
    "swiss": {
        "name": "Swiss",
        "beschreibung": "Swiss precision with clean red header bar",
        "vorschau_farbe": "#DC2626",
        
        # Font
        "font": "Helvetica",
        "font_bold": "Helvetica-Bold",
        
        # Colors - Red
        "header_bg": colors.Color(0.86, 0.15, 0.15),
        "header_text": colors.white,
        "zeile_alternierend": None,
        "linien_farbe": colors.Color(0.88, 0.88, 0.88),
        "akzent_farbe": colors.Color(0.86, 0.15, 0.15),
        
        # Table style
        "tabelle_gitter": False,
        "linien_staerke": 0.75,
        "header_fett": True,
        "nur_horizontale_linien": True,
        
        # Total box - Red
        "total_box": True,
        "total_bg": colors.Color(0.86, 0.15, 0.15),
        "total_text": colors.white,
        
        # Header design - Top bar only
        "kopf_design": "top_bar",
        "kopf_farbe": colors.Color(0.86, 0.15, 0.15),
    },
    
    # ========== 8. NATURE - Green organic ==========
    "nature": {
        "name": "Nature",
        "beschreibung": "Organic green with natural feel",
        "vorschau_farbe": "#059669",
        
        # Font
        "font": "Times-Roman",
        "font_bold": "Times-Bold",
        
        # Colors - Green
        "header_bg": colors.Color(0.02, 0.59, 0.41),
        "header_text": colors.white,
        "zeile_alternierend": colors.Color(0.96, 0.99, 0.97),
        "linien_farbe": colors.Color(0.82, 0.92, 0.85),
        "akzent_farbe": colors.Color(0.02, 0.59, 0.41),
        
        # Table style
        "tabelle_gitter": False,
        "linien_staerke": 0.5,
        "header_fett": True,
        "nur_horizontale_linien": True,
        
        # Total box
        "total_box": True,
        "total_bg": colors.Color(0.02, 0.59, 0.41),
        "total_text": colors.white,
        
        # Header design - Left stripe
        "kopf_design": "left_stripe",
        "kopf_farbe": colors.Color(0.02, 0.59, 0.41),
    },
    
    # ========== 9. DARK - Dark theme with accent ==========
    "dark": {
        "name": "Dark",
        "beschreibung": "Dark theme with red accent stripe",
        "vorschau_farbe": "#1F2937",
        
        # Font
        "font": "Courier",
        "font_bold": "Courier-Bold",
        
        # Colors - Very dark with red
        "header_bg": colors.Color(0.15, 0.15, 0.18),
        "header_text": colors.white,
        "zeile_alternierend": colors.Color(0.96, 0.96, 0.96),
        "linien_farbe": colors.Color(0.8, 0.8, 0.82),
        "akzent_farbe": colors.Color(0.15, 0.15, 0.18),
        "akzent_farbe2": colors.Color(0.91, 0.27, 0.38),  # Red accent
        
        # Table style
        "tabelle_gitter": False,
        "linien_staerke": 0.5,
        "header_fett": True,
        "nur_horizontale_linien": True,
        
        # Total box
        "total_box": True,
        "total_bg": colors.Color(0.91, 0.27, 0.38),
        "total_text": colors.white,
        
        # Header design - Top accent line
        "kopf_design": "accent_lines",
        "kopf_farbe": colors.Color(0.15, 0.15, 0.18),
        "kopf_farbe2": colors.Color(0.91, 0.27, 0.38),
    },
    
    # ========== 10. OCEAN - Deep blue ==========
    "ocean": {
        "name": "Ocean",
        "beschreibung": "Deep ocean blue with full header bar",
        "vorschau_farbe": "#0369A1",
        
        # Font
        "font": "Helvetica",
        "font_bold": "Helvetica-Bold",
        
        # Colors - Ocean blue
        "header_bg": colors.Color(0.01, 0.41, 0.63),
        "header_text": colors.white,
        "zeile_alternierend": colors.Color(0.96, 0.98, 1.0),
        "linien_farbe": colors.Color(0.82, 0.90, 0.96),
        "akzent_farbe": colors.Color(0.01, 0.41, 0.63),
        
        # Table style
        "tabelle_gitter": False,
        "linien_staerke": 0.5,
        "header_fett": True,
        "nur_horizontale_linien": True,
        
        # Total box
        "total_box": True,
        "total_bg": colors.Color(0.01, 0.41, 0.63),
        "total_text": colors.white,
        
        # Header design - Full width bar
        "kopf_design": "full_width_bar",
        "kopf_farbe": colors.Color(0.01, 0.41, 0.63),
        "kopf_hoehe": 40,
    },
    
    # ========== 11. SUNSET - Orange warm ==========
    "sunset": {
        "name": "Sunset",
        "beschreibung": "Warm sunset orange with diagonal corner",
        "vorschau_farbe": "#EA580C",
        
        # Font
        "font": "Helvetica",
        "font_bold": "Helvetica-Bold",
        
        # Colors - Orange
        "header_bg": colors.Color(0.92, 0.34, 0.05),
        "header_text": colors.white,
        "zeile_alternierend": colors.Color(1.0, 0.98, 0.96),
        "linien_farbe": colors.Color(0.95, 0.88, 0.82),
        "akzent_farbe": colors.Color(0.92, 0.34, 0.05),
        
        # Table style
        "tabelle_gitter": False,
        "linien_staerke": 0.5,
        "header_fett": True,
        "nur_horizontale_linien": True,
        
        # Total box
        "total_box": True,
        "total_bg": colors.Color(0.92, 0.34, 0.05),
        "total_text": colors.white,
        
        # Header design - Diagonal triangle
        "kopf_design": "diagonal_triangle",
        "kopf_farbe": colors.Color(0.92, 0.34, 0.05),
    },
    
    # ========== 12. PROFESSIONAL - Slate business ==========
    "professional": {
        "name": "Professional",
        "beschreibung": "Business slate gray with gold accent",
        "vorschau_farbe": "#475569",
        
        # Font
        "font": "Times-Roman",
        "font_bold": "Times-Bold",
        
        # Colors - Slate + Gold
        "header_bg": colors.Color(0.28, 0.33, 0.41),
        "header_text": colors.white,
        "zeile_alternierend": colors.Color(0.98, 0.98, 0.97),
        "linien_farbe": colors.Color(0.88, 0.88, 0.86),
        "akzent_farbe": colors.Color(0.28, 0.33, 0.41),
        "gold_akzent": colors.Color(0.83, 0.69, 0.22),  # Gold
        
        # Table style
        "tabelle_gitter": False,
        "linien_staerke": 0.5,
        "header_fett": True,
        "nur_horizontale_linien": True,
        "header_linie_unten": True,
        
        # Total box
        "total_box": True,
        "total_bg": colors.Color(0.28, 0.33, 0.41),
        "total_text": colors.white,
        
        # Header design - Left stripe with gold
        "kopf_design": "left_stripe_gold",
        "kopf_farbe": colors.Color(0.28, 0.33, 0.41),
    },
}

def get_stil(stil_name: str) -> dict:
    """Returns the style, or 'classic' as fallback."""
    return RECHNUNG_STYLES.get(stil_name, RECHNUNG_STYLES["classic"])

def get_alle_stile() -> list:
    """Returns a list of all available style names."""
    return list(RECHNUNG_STYLES.keys())

def get_stil_namen() -> dict:
    """Returns a dict with style_key -> display_name."""
    return {key: style["name"] for key, style in RECHNUNG_STYLES.items()}

def get_available_fonts() -> dict:
    """Returns available font options."""
    return AVAILABLE_FONTS
