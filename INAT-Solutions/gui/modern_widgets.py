# -*- coding: utf-8 -*-
"""
Moderne UI-Widgets für INAT Solutions
- Sidebar Navigation
- Moderne Karten
- Status Pills/Badges
- Avatar/Initialen
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QSizePolicy, QGraphicsDropShadowEffect,
    QStackedWidget
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QFont, QColor, QIcon, QPainter, QPixmap
from paths import resource_path
from i18n import _


# ============================================================================
# FARBEN (App-Farbschema)
# ============================================================================
COLORS = {
    "primary": "#4a6fa5",          # Original INAT Blau
    "primary_dark": "#3d5d8a",     # Dunkleres Blau
    "primary_light": "#6b8fc5",    # Helleres Blau
    "background": "#ffffff",       # Weißer Hintergrund
    "surface": "#ffffff",          # Weiß
    "surface_hover": "#f9fafb",    # Hover-Hintergrund
    "text_primary": "#1f2937",     # Dunkler Text
    "text_secondary": "#6b7280",   # Grauer Text
    "text_muted": "#9ca3af",       # Heller Text
    "border": "#e5e7eb",           # Rahmenfarbe
    "border_light": "#f3f4f6",     # Heller Rahmen
    "success": "#10b981",          # Grün
    "success_light": "#dcfce7",    # Helles Grün
    "success_text": "#15803d",     # Grüner Text
    "warning": "#f59e0b",          # Orange
    "warning_light": "#fef3c7",    # Helles Orange
    "warning_text": "#ea580c",     # Oranger Text
    "danger": "#ef4444",           # Rot
    "danger_light": "#fee2e2",     # Helles Rot
    "danger_text": "#dc2626",      # Roter Text
    "info": "#4a6fa5",             # Info Blau
    
    # Selektion & Hover
    "selection": "#e5e7eb",        # Auswahlfarbe (hellgrau)
    "selection_text": "#1f2937",   # Text bei Auswahl
    "hover": "#f9fafb",            # Hover-Hintergrund
    "hover_border": "#4a6fa5",     # Hover-Rahmen
    
    # Icons
    "icon_opacity": 0.4,           # Icon-Opazität (40% für hellgrau)
}

# ============================================================================
# SCHRIFTGRÖSSEN (zentral gesteuert)
# ============================================================================
FONT_SIZES = {
    # Tabellen
    "table_cell": 12,              # Zelleninhalt (pt)
    "table_header": 12,            # Tabellenüberschrift (pt)
    
    # Badges & Labels
    "badge": 12,                   # Status-Badges (px für CSS)
    "label": 14,                   # Normale Labels (pt)
    
    # Buttons & Input
    "button": 14,                  # Button-Text (pt)
    "input": 15,                   # Eingabefelder (px für CSS)
    
    # Überschriften (Hierarchie)
    "h1": 28,                      # Hauptüberschrift (px)
    "h2": 24,                      # Große Überschrift (px)
    "h3": 20,                      # Mittlere Überschrift (px)
    "h4": 18,                      # Kleine Überschrift (px)
    "h5": 16,                      # Sehr kleine Überschrift (px)
    "title": 24,                   # Große Überschriften (pt)
    "subtitle": 16,                # Unterüberschriften (pt)
    "section": 16,                 # Abschnittsüberschriften (pt)
    
    # Text
    "body": 14,                    # Fließtext (px)
    "small": 13,                   # Kleiner Text (px)
    "caption": 12,                 # Beschriftungen (px)
    
    # Icons
    "icon_small": 18,              # Kleine Icons (px)
    "icon_medium": 22,             # Mittlere Icons (px)
    "icon_large": 28,              # Große Icons (px)
    
    # Buttons (Größe)
    "btn_small": 32,               # Kleine Buttons (px)
    "btn_medium": 36,              # Mittlere Buttons (px)
    "btn_large": 42,               # Große Buttons (px)
}

# ============================================================================
# ABSTÄNDE & RADIEN (zentral gesteuert)
# ============================================================================
SPACING = {
    "xs": 4,                       # Extra klein
    "sm": 8,                       # Klein
    "md": 12,                      # Mittel
    "lg": 16,                      # Groß
    "xl": 24,                      # Extra groß
    "xxl": 32,                     # Sehr groß
}

BORDER_RADIUS = {
    "sm": 6,                       # Kleine Rundung
    "md": 8,                       # Mittlere Rundung
    "lg": 12,                      # Große Rundung
    "xl": 16,                      # Extra große Rundung
    "full": 9999,                  # Vollständig rund (Pill)
}

# ============================================================================
# STYLESHEET-GENERATOREN (einheitliche Styles)
# ============================================================================

def get_table_stylesheet():
    """Einheitliches Tabellen-Stylesheet."""
    return f"""
        QTableWidget {{
            background-color: {COLORS['surface']};
            border: none;
            border-radius: {BORDER_RADIUS['lg']}px;
            gridline-color: transparent;
            font-size: {FONT_SIZES['table_cell']}px;
            outline: none;
        }}
        QTableWidget::item {{
            padding: 14px 12px;
            border-bottom: 1px solid {COLORS['border_light']};
            color: {COLORS['text_primary']};
        }}
        QTableWidget::item:hover {{
            background-color: {COLORS['hover']};
        }}
        QTableWidget::item:selected {{
            background-color: {COLORS['selection']};
            color: {COLORS['selection_text']};
        }}
        QTableWidget::item:focus {{
            outline: none;
        }}
        QHeaderView::section {{
            background-color: {COLORS['surface_hover']};
            color: {COLORS['text_secondary']};
            font-weight: 600;
            font-size: {FONT_SIZES['table_header']}px;
            padding: 12px 12px;
            border: none;
            border-bottom: 1px solid {COLORS['border']};
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
    """

def get_button_primary_stylesheet():
    """Einheitliches Primary-Button-Stylesheet."""
    return f"""
        QPushButton {{
            background-color: {COLORS['primary']};
            color: white;
            border: none;
            border-radius: {BORDER_RADIUS['md']}px;
            padding: 10px 20px;
            font-size: {FONT_SIZES['button'] - 1}px;
            font-weight: 600;
        }}
        QPushButton:hover {{
            background-color: {COLORS['primary_dark']};
        }}
        QPushButton:pressed {{
            background-color: {COLORS['primary_dark']};
        }}
    """

def get_button_secondary_stylesheet():
    """Einheitliches Secondary-Button-Stylesheet."""
    return f"""
        QPushButton {{
            background-color: {COLORS['background']};
            color: {COLORS['text_primary']};
            border: 1px solid {COLORS['border']};
            border-radius: {BORDER_RADIUS['md']}px;
            padding: 10px 16px;
            font-size: {FONT_SIZES['button'] - 1}px;
        }}
        QPushButton:hover {{
            background-color: {COLORS['hover']};
            border-color: {COLORS['hover_border']};
        }}
        QPushButton:pressed {{
            background-color: {COLORS['selection']};
        }}
    """

def get_input_stylesheet():
    """Einheitliches Eingabefeld-Stylesheet."""
    return f"""
        QLineEdit {{
            background-color: {COLORS['background']};
            border: 1px solid {COLORS['border']};
            border-radius: {BORDER_RADIUS['md']}px;
            padding: 10px 16px;
            font-size: {FONT_SIZES['input']}px;
            color: {COLORS['text_primary']};
        }}
        QLineEdit:focus {{
            border-color: {COLORS['primary']};
            background-color: {COLORS['surface']};
        }}
        QLineEdit:hover {{
            border-color: {COLORS['hover_border']};
        }}
    """

def get_card_stylesheet():
    """Einheitliches Karten-Stylesheet."""
    return f"""
        QFrame {{
            background-color: {COLORS['surface']};
            border: 1px solid {COLORS['border']};
            border-radius: {BORDER_RADIUS['lg']}px;
        }}
    """

def get_toolbar_button_stylesheet():
    """Einheitliches Toolbar-Button-Stylesheet (für Icons)."""
    return f"""
        QToolButton {{
            border: none;
            background: transparent;
            border-radius: {BORDER_RADIUS['sm']}px;
            padding: 4px;
        }}
        QToolButton:hover {{
            background-color: {COLORS['hover']};
        }}
        QToolButton:pressed {{
            background-color: {COLORS['selection']};
        }}
    """

def get_combobox_stylesheet():
    """Einheitliches ComboBox-Stylesheet."""
    return f"""
        QComboBox {{
            background-color: {COLORS['surface']};
            border: 1px solid {COLORS['border']};
            border-radius: {BORDER_RADIUS['md']}px;
            padding: 8px 12px;
            font-size: {FONT_SIZES['button'] - 1}px;
            color: {COLORS['text_primary']};
        }}
        QComboBox:hover {{
            border-color: {COLORS['hover_border']};
        }}
        QComboBox:focus {{
            border-color: {COLORS['primary']};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 24px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {COLORS['surface']};
            border: 1px solid {COLORS['border']};
            border-radius: {BORDER_RADIUS['md']}px;
            selection-background-color: {COLORS['selection']};
            selection-color: {COLORS['selection_text']};
        }}
    """

def create_gray_icon(icon_path):
    """Erstellt ein hellgraues Icon mit der zentralen Opazität."""
    from PyQt5.QtGui import QPixmap, QPainter, QIcon
    from PyQt5.QtCore import Qt
    pixmap = QPixmap(icon_path)
    gray_pixmap = QPixmap(pixmap.size())
    gray_pixmap.fill(Qt.transparent)
    painter = QPainter(gray_pixmap)
    painter.setOpacity(COLORS['icon_opacity'])
    painter.drawPixmap(0, 0, pixmap)
    painter.end()
    return QIcon(gray_pixmap)


# ============================================================================
# SIDEBAR NAVIGATION
# ============================================================================
class SidebarButton(QPushButton):
    """Ein Button für die Sidebar-Navigation (dunkles Showcase-Design)."""
    
    def __init__(self, text: str, icon_name: str = None, parent=None):
        super().__init__(parent)
        self.setText(text)
        self._is_active = False
        
        if icon_name:
            try:
                self.setIcon(QIcon(resource_path(f"icons/{icon_name}")))
                self.setIconSize(QSize(24, 24))
            except Exception:
                pass
        
        self.setFixedHeight(48)
        self.setCursor(Qt.PointingHandCursor)
        self._update_style()
    
    def set_active(self, active: bool):
        self._is_active = active
        self._update_style()
    
    def _update_style(self):
        if self._is_active:
            # Aktiver Button: Primary-Blau mit Schatten (Showcase-Stil)
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['primary']};
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 12px 16px;
                    text-align: left;
                    font-size: 15px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['primary_dark']};
                }}
            """)
        else:
            # Inaktiver Button: Transparenter Hintergrund, grauer Text (Showcase-Stil)
            self.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #9ca3af;
                    border: none;
                    border-radius: 8px;
                    padding: 12px 16px;
                    text-align: left;
                    font-size: 15px;
                    font-weight: 400;
                }
                QPushButton:hover {
                    background-color: #374151;
                    color: white;
                }
            """)


class Sidebar(QFrame):
    """Moderne fixierte Sidebar mit Navigation (dunkles Showcase-Design)."""
    
    navigation_clicked = pyqtSignal(int)  # Index des geklickten Tabs
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(240)
        self.setObjectName("sidebar")
        
        # Dunkles Sidebar-Design (Showcase: bg-gray-800)
        self.setStyleSheet("""
            #sidebar {
                background-color: #1f2937;
                border-right: 2px solid #374151;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 20, 16, 20)
        layout.setSpacing(4)
        
        # Logo-Bereich
        logo_container = QWidget()
        logo_layout = QHBoxLayout(logo_container)
        logo_layout.setContentsMargins(8, 8, 8, 32)
        
        logo_label = QLabel()
        try:
            logo_pixmap = QPixmap(resource_path("icons/logo.svg")).scaled(
                36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            logo_label.setPixmap(logo_pixmap)
        except Exception:
            pass
        logo_layout.addWidget(logo_label)
        
        app_name = QLabel("INAT Solutions")
        app_name.setStyleSheet("""
            color: white;
            font-size: 18px;
            font-weight: 700;
        """)
        logo_layout.addWidget(app_name)
        logo_layout.addStretch()
        
        layout.addWidget(logo_container)
        
        # Versions-Label unter dem Logo
        version_label = QLabel("Business Software")
        version_label.setStyleSheet("""
            color: #6b7280;
            font-size: 12px;
            padding-left: 8px;
            margin-top: -20px;
            margin-bottom: 16px;
        """)
        layout.addWidget(version_label)
        
        # Navigation Buttons
        self.nav_buttons = []
        nav_items = [
            (_("Dashboard"), "dashboard.svg", 0),
            (_("Kunden"), "users.svg", 1),
            (_("Rechnungen"), "invoice.svg", 2),
            (_("Buchhaltung"), "accounting.svg", 3),
            (_("Lieferanten"), "supplier.svg", 4),
            (_("Lager"), "warehouse.svg", 5),
            (_("Kalender"), "calendar.svg", 6),
        ]
        
        for text, icon, index in nav_items:
            btn = SidebarButton(text, icon)
            btn.clicked.connect(lambda checked, i=index: self._on_nav_click(i))
            self.nav_buttons.append(btn)
            layout.addWidget(btn)
        
        layout.addStretch()
        
        # Trennlinie (dunkles Design)
        separator = QFrame()
        separator.setFixedHeight(1)
        separator.setStyleSheet("background-color: #374151;")
        layout.addWidget(separator)
        
        # Einstellungen unten
        settings_btn = SidebarButton(_("Einstellungen"), "settings.svg")
        settings_btn.clicked.connect(lambda: self._on_nav_click(7))
        self.nav_buttons.append(settings_btn)
        layout.addWidget(settings_btn)
        
        # Ersten Button als aktiv markieren
        if self.nav_buttons:
            self.nav_buttons[0].set_active(True)
    
    def _on_nav_click(self, index: int):
        # Alle Buttons deaktivieren
        for btn in self.nav_buttons:
            btn.set_active(False)
        
        # Geklickten Button aktivieren
        if 0 <= index < len(self.nav_buttons):
            self.nav_buttons[index].set_active(True)
        
        self.navigation_clicked.emit(index)
    
    def set_active_index(self, index: int):
        """Setzt den aktiven Tab von aussen."""
        for i, btn in enumerate(self.nav_buttons):
            btn.set_active(i == index)


# ============================================================================
# MODERNE KARTEN
# ============================================================================
class ModernCard(QFrame):
    """Eine moderne Karte mit Schatten und abgerundeten Ecken."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("modernCard")
        
        self.setStyleSheet(f"""
            #modernCard {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border_light']};
                border-radius: 12px;
            }}
        """)
        
        # Schatten-Effekt
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 25))
        self.setGraphicsEffect(shadow)
    
    def set_padding(self, padding: int):
        """Setzt das innere Padding."""
        if self.layout():
            self.layout().setContentsMargins(padding, padding, padding, padding)


class StatCard(QFrame):
    """Statistik-Karte für Dashboard."""
    
    def __init__(self, title: str, value: str, icon: str = None, 
                 trend: str = None, trend_positive: bool = True, parent=None):
        super().__init__(parent)
        self.setObjectName("statCard")
        
        self.setStyleSheet(f"""
            #statCard {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border_light']};
                border-radius: 12px;
                padding: 20px;
            }}
            #statCard:hover {{
                border-color: {COLORS['primary']};
            }}
        """)
        
        # Schatten
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setXOffset(0)
        shadow.setYOffset(3)
        shadow.setColor(QColor(0, 0, 0, 20))
        self.setGraphicsEffect(shadow)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # Icon (optional)
        if icon:
            icon_container = QFrame()
            icon_container.setFixedSize(48, 48)
            icon_container.setStyleSheet(f"""
                background-color: {COLORS['primary']}15;
                border-radius: 12px;
            """)
            icon_layout = QVBoxLayout(icon_container)
            icon_layout.setContentsMargins(0, 0, 0, 0)
            icon_label = QLabel(icon)
            icon_label.setAlignment(Qt.AlignCenter)
            icon_label.setStyleSheet("font-size: 20px; background: transparent;")
            icon_layout.addWidget(icon_label)
            layout.addWidget(icon_container)
        
        # Text-Bereich
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)
        
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            color: {COLORS['text_secondary']};
            font-size: 13px;
            font-weight: 500;
        """)
        text_layout.addWidget(title_label)
        
        value_label = QLabel(value)
        value_label.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            font-size: 28px;
            font-weight: 700;
        """)
        text_layout.addWidget(value_label)
        
        if trend:
            trend_color = COLORS['success'] if trend_positive else COLORS['danger']
            trend_arrow = "↑" if trend_positive else "↓"
            trend_label = QLabel(f"{trend_arrow} {trend}")
            trend_label.setStyleSheet(f"""
                color: {trend_color};
                font-size: 12px;
                font-weight: 500;
            """)
            text_layout.addWidget(trend_label)
        
        layout.addLayout(text_layout)
        layout.addStretch()


# ============================================================================
# STATUS BADGES
# ============================================================================
class StatusBadge(QLabel):
    """Status-Badge/Pill für Tabellen."""
    
    VARIANTS = {
        "success": {"bg": "#dcfce7", "text": "#166534"},
        "warning": {"bg": "#fef3c7", "text": "#92400e"},
        "danger": {"bg": "#fee2e2", "text": "#991b1b"},
        "info": {"bg": "#dbeafe", "text": "#1e40af"},
        "neutral": {"bg": "#f1f5f9", "text": "#475569"},
    }
    
    def __init__(self, text: str, variant: str = "neutral", parent=None):
        super().__init__(text, parent)
        self.set_variant(variant)
    
    def set_variant(self, variant: str):
        colors = self.VARIANTS.get(variant, self.VARIANTS["neutral"])
        self.setStyleSheet(f"""
            background-color: {colors['bg']};
            color: {colors['text']};
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 500;
        """)
        self.setAlignment(Qt.AlignCenter)


# ============================================================================
# AVATAR / INITIALEN
# ============================================================================
class AvatarLabel(QLabel):
    """Runder Avatar mit Initialen."""
    
    COLORS = [
        "#4a6fa5", "#10b981", "#f59e0b", "#ef4444", 
        "#8b5cf6", "#ec4899", "#06b6d4", "#84cc16"
    ]
    
    def __init__(self, name: str, size: int = 40, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignCenter)
        self.set_name(name)
    
    def set_name(self, name: str):
        # Initialen extrahieren
        parts = name.strip().split()
        if len(parts) >= 2:
            initials = (parts[0][0] + parts[-1][0]).upper()
        elif parts:
            initials = parts[0][:2].upper()
        else:
            initials = "?"
        
        # Farbe basierend auf Namen
        color_index = sum(ord(c) for c in name) % len(self.COLORS)
        color = self.COLORS[color_index]
        
        self.setText(initials)
        size = self.width()
        font_size = int(size * 0.4)
        
        self.setStyleSheet(f"""
            background-color: {color};
            color: white;
            border-radius: {size // 2}px;
            font-size: {font_size}px;
            font-weight: 600;
        """)


# ============================================================================
# MODERNE TOOLBAR
# ============================================================================
class ModernToolbar(QFrame):
    """Moderne Toolbar mit Primary Action und Suche."""
    
    search_changed = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(64)
        self.setStyleSheet(f"""
            background-color: {COLORS['surface']};
            border-bottom: 1px solid {COLORS['border']};
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 12, 24, 12)
        layout.setSpacing(16)
        
        self._buttons_layout = QHBoxLayout()
        self._buttons_layout.setSpacing(8)
        layout.addLayout(self._buttons_layout)
        
        layout.addStretch()
        
        # Suchfeld
        from PyQt5.QtWidgets import QLineEdit
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(_("🔍 Suchen..."))
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS['background']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 10px 16px;
                font-size: 15px;
                color: {COLORS['text_primary']};
            }}
            QLineEdit:focus {{
                border-color: {COLORS['primary']};
                background-color: {COLORS['surface']};
            }}
            QLineEdit::placeholder {{
                color: {COLORS['text_muted']};
            }}
        """)
        self.search_input.textChanged.connect(self.search_changed.emit)
        layout.addWidget(self.search_input, 1)  # stretch=1 für volle Breite
    
    def add_button(self, text: str, icon: str = None, primary: bool = False) -> QPushButton:
        """Fügt einen Button zur Toolbar hinzu."""
        btn = QPushButton(text)
        
        if icon:
            try:
                btn.setIcon(QIcon(resource_path(f"icons/{icon}")))
            except Exception:
                pass
        
        if primary:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['primary']};
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 10px 20px;
                    font-size: 14px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['primary_dark']};
                }}
                QPushButton:pressed {{
                    background-color: #2d4a6f;
                }}
            """)
        else:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['surface']};
                    color: {COLORS['text_primary']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 8px;
                    padding: 10px 16px;
                    font-size: 14px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['surface_hover']};
                    border-color: {COLORS['primary']};
                }}
            """)
        
        btn.setCursor(Qt.PointingHandCursor)
        self._buttons_layout.addWidget(btn)
        return btn


# ============================================================================
# LISTEN-EINTRAG (Mini-Karte)
# ============================================================================
class ListItem(QFrame):
    """Ein moderner Listen-Eintrag als Mini-Karte."""
    
    clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("listItem")
        self.setCursor(Qt.PointingHandCursor)
        
        self.setStyleSheet(f"""
            #listItem {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border_light']};
                border-radius: 10px;
                padding: 12px;
            }}
            #listItem:hover {{
                background-color: {COLORS['surface_hover']};
                border-color: {COLORS['primary']};
            }}
        """)
        
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(16, 12, 16, 12)
        self._layout.setSpacing(16)
    
    def set_content(self, avatar_name: str, title: str, subtitle: str = None,
                    right_text: str = None, right_subtitle: str = None,
                    badge_text: str = None, badge_variant: str = "neutral"):
        # Avatar
        avatar = AvatarLabel(avatar_name, 44)
        self._layout.addWidget(avatar)
        
        # Hauptinhalt
        content = QVBoxLayout()
        content.setSpacing(2)
        
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            font-size: 14px;
            font-weight: 600;
        """)
        content.addWidget(title_label)
        
        if subtitle:
            sub_label = QLabel(subtitle)
            sub_label.setStyleSheet(f"""
                color: {COLORS['text_secondary']};
                font-size: 12px;
            """)
            content.addWidget(sub_label)
        
        self._layout.addLayout(content)
        self._layout.addStretch()
        
        # Rechte Seite
        if right_text or badge_text:
            right_layout = QVBoxLayout()
            right_layout.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            right_layout.setSpacing(4)
            
            if right_text:
                right_label = QLabel(right_text)
                right_label.setStyleSheet(f"""
                    color: {COLORS['text_primary']};
                    font-size: 14px;
                    font-weight: 600;
                """)
                right_label.setAlignment(Qt.AlignRight)
                right_layout.addWidget(right_label)
            
            if right_subtitle:
                rsub_label = QLabel(right_subtitle)
                rsub_label.setStyleSheet(f"""
                    color: {COLORS['text_muted']};
                    font-size: 11px;
                """)
                rsub_label.setAlignment(Qt.AlignRight)
                right_layout.addWidget(rsub_label)
            
            if badge_text:
                badge = StatusBadge(badge_text, badge_variant)
                right_layout.addWidget(badge, alignment=Qt.AlignRight)
            
            self._layout.addLayout(right_layout)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
