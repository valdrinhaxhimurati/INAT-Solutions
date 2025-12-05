# -*- coding: utf-8 -*-
"""
MainWindow mit moderner Sidebar-Navigation (wie auf dem Screenshot)
"""
import ctypes
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QSizePolicy, QDesktopWidget, QStackedWidget, QFrame, QPushButton,
    QGraphicsDropShadowEffect
)
from db_connection import get_db, dict_cursor_factory
from PyQt5.QtGui import QFont, QIcon, QPainter, QPixmap, QColor
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, QThread, QTimer, QPoint, QEvent, QSize
from PyQt5.QtWinExtras import QtWin

from gui.dashboard_tab import DashboardTab
from gui.kunden_tab import KundenTab
from gui.rechnungen_tab import RechnungenTab
from gui.buchhaltung_tab import BuchhaltungTab
from gui.einstellungen_tab import EinstellungenTab
from gui.lieferanten_tab import LieferantenTab
from gui.lager_tab import LagerTab
from gui.auftragskalender_tab import AuftragskalenderTab
from gui.widgets import WindowButtons

from version import __version__
from i18n import _
from paths import resource_path

import sys
import os


# Farben (App-Farbschema)
COLORS = {
    "sidebar_bg": "#1e293b",        # Dunkle Sidebar
    "sidebar_text": "#94a3b8",      # Sidebar Text
    "sidebar_text_active": "#ffffff",
    "sidebar_hover": "#334155",     # Sidebar Hover
    "sidebar_active": "#4a6fa5",    # Original INAT Blau
    "content_bg": "#f5f7fa",        # Heller Hintergrund
    "surface": "#ffffff",
    "border": "#e2e8f0",            # Rahmenfarbe
    "primary": "#4a6fa5",           # Original INAT Blau
}


class SidebarNavButton(QPushButton):
    """Navigation Button für die Sidebar (Showcase-Design mit Punkt-Indikator)."""
    
    def __init__(self, text: str, icon_char: str = "", parent=None):
        super().__init__(parent)
        self._is_active = False
        self._icon_char = icon_char
        self._text = text
        
        # Layout mit Icon, Text und Punkt
        self.setFixedHeight(44)
        self.setCursor(Qt.PointingHandCursor)
        self.setCheckable(True)
        
        # Text mit Icon
        self.setText(f"  {icon_char}   {text}" if icon_char else f"     {text}")
        
        self._update_style()
    
    def set_active(self, active: bool):
        self._is_active = active
        self.setChecked(active)
        self._update_style()
    
    def _update_style(self):
        if self._is_active:
            # Aktiver Button: Text mit Punkt am Ende
            display_text = f"  {self._icon_char}   {self._text}                     •" if self._icon_char else f"     {self._text}                     •"
            self.setText(display_text)
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: rgba(74, 111, 165, 0.15);
                    color: {COLORS['sidebar_text_active']};
                    border: none;
                    border-radius: 10px;
                    padding: 10px 16px;
                    text-align: left;
                    font-size: 14px;
                    font-weight: 500;
                }}
            """)
        else:
            # Inaktiver Button: Ohne Punkt
            display_text = f"  {self._icon_char}   {self._text}" if self._icon_char else f"     {self._text}"
            self.setText(display_text)
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {COLORS['sidebar_text']};
                    border: none;
                    border-radius: 10px;
                    padding: 10px 16px;
                    text-align: left;
                    font-size: 14px;
                    font-weight: 400;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['sidebar_hover']};
                    color: {COLORS['sidebar_text_active']};
                }}
            """)


class ModernSidebar(QFrame):
    """Dunkle Sidebar-Navigation wie im Showcase."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setFixedWidth(280)
        self.setObjectName("modernSidebar")
        
        self.setStyleSheet(f"""
            #modernSidebar {{
                background-color: {COLORS['sidebar_bg']};
                border: none;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 16)
        layout.setSpacing(4)
        
        # Titelleiste-Bereich (für Fenster-Verschiebung)
        self.title_area = QWidget()
        self.title_area.setFixedHeight(70)
        self.title_area.setStyleSheet("background: transparent;")
        title_layout = QHBoxLayout(self.title_area)
        title_layout.setContentsMargins(8, 20, 8, 12)
        
        # Logo
        logo_label = QLabel()
        try:
            logo_pixmap = QPixmap(resource_path("icons/logo.svg")).scaled(
                32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            logo_label.setPixmap(logo_pixmap)
        except Exception:
            logo_label.setText("🔷")
        logo_label.setStyleSheet("background: transparent;")
        title_layout.addWidget(logo_label)
        
        # App Name und Version in einem Container
        app_info = QVBoxLayout()
        app_info.setSpacing(2)
        
        app_name = QLabel("INAT Solutions")
        app_name.setStyleSheet(f"""
            color: {COLORS['sidebar_text_active']};
            font-size: 18px;
            font-weight: 700;
            background: transparent;
        """)
        app_info.addWidget(app_name)
        
        version_label = QLabel(f"Business Software v{__version__}")
        version_label.setStyleSheet("""
            color: #6b7280;
            font-size: 11px;
            background: transparent;
        """)
        app_info.addWidget(version_label)
        
        title_layout.addLayout(app_info)
        title_layout.addStretch()
        
        layout.addWidget(self.title_area)
        layout.addSpacing(8)
        
        # Navigation Buttons
        self.nav_buttons = []
        nav_items = [
            (_("Dashboard"), "📊", 0),
            (_("Rechnungen"), "📄", 1),
            (_("Kunden"), "👥", 2),
            (_("Kalender"), "📅", 3),
            (_("Lager"), "📦", 4),
            (_("Buchhaltung"), "💰", 5),
            (_("Einstellungen"), "⚙️", 7),
        ]
        
        for text, icon, index in nav_items:
            btn = SidebarNavButton(text, icon)
            btn.clicked.connect(lambda checked, i=index: self._on_nav_click(i))
            self.nav_buttons.append(btn)
            layout.addWidget(btn)
        
        layout.addStretch()
        
        # Trennlinie vor Benutzer-Bereich
        separator = QFrame()
        separator.setFixedHeight(1)
        separator.setStyleSheet(f"background-color: {COLORS['sidebar_hover']};")
        layout.addWidget(separator)
        
        layout.addSpacing(12)
        
        # Benutzer-Bereich unten (Showcase-Stil)
        self.user_section = QWidget()
        self.user_section.setStyleSheet("background: transparent;")
        user_layout = QHBoxLayout(self.user_section)
        user_layout.setContentsMargins(8, 8, 8, 8)
        user_layout.setSpacing(12)
        
        # Avatar mit Initialen
        self.user_avatar = QLabel("VH")
        self.user_avatar.setFixedSize(40, 40)
        self.user_avatar.setAlignment(Qt.AlignCenter)
        self.user_avatar.setStyleSheet(f"""
            background-color: {COLORS['sidebar_hover']};
            color: {COLORS['sidebar_text_active']};
            font-size: 14px;
            font-weight: 600;
            border-radius: 20px;
        """)
        user_layout.addWidget(self.user_avatar)
        
        # Benutzer-Info
        user_info = QVBoxLayout()
        user_info.setSpacing(2)
        
        self.user_name_label = QLabel("Benutzer")
        self.user_name_label.setStyleSheet(f"""
            color: {COLORS['sidebar_text_active']};
            font-size: 14px;
            font-weight: 600;
            background: transparent;
        """)
        user_info.addWidget(self.user_name_label)
        
        self.user_role_label = QLabel("Administrator")
        self.user_role_label.setStyleSheet(f"""
            color: {COLORS['sidebar_text']};
            font-size: 12px;
            background: transparent;
        """)
        user_info.addWidget(self.user_role_label)
        
        user_layout.addLayout(user_info)
        user_layout.addStretch()
        
        layout.addWidget(self.user_section)
        
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
        
        # Parent informieren
        if self.parent_window and hasattr(self.parent_window, 'switch_to_page'):
            self.parent_window.switch_to_page(index)
    
    def set_active_index(self, index: int):
        """Setzt den aktiven Tab von aussen."""
        for i, btn in enumerate(self.nav_buttons):
            btn.set_active(i == index)
    
    def set_user_info(self, name: str, role: str = "Administrator"):
        """Setzt die Benutzer-Information in der Sidebar."""
        self.user_name_label.setText(name)
        self.user_role_label.setText(role)
        # Avatar-Initialen aus Name generieren
        parts = name.split()
        if len(parts) >= 2:
            initials = parts[0][0].upper() + parts[1][0].upper()
        elif len(parts) == 1 and len(parts[0]) >= 2:
            initials = parts[0][:2].upper()
        else:
            initials = name[:2].upper() if name else "??"
        self.user_avatar.setText(initials)


class CustomTitleBar(QWidget):
    """Titelleiste-Widget für Fenster-Buttons."""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.parent_window = parent
        self.setFixedHeight(64)
        self.setStyleSheet(f"""
            background-color: {COLORS['surface']};
            border-bottom: 1px solid {COLORS['border']};
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(32, 0, 16, 0)
        
        # Titel (zeigt aktuellen Tab-Namen)
        self.title_label = QLabel(_("Dashboard"))
        self.title_label.setStyleSheet("""
            color: #1f2937;
            font-size: 24px;
            font-weight: 700;
        """)
        layout.addWidget(self.title_label)
        
        layout.addStretch()
        
        # Rechte Seite: Datum + Fenster-Buttons
        right_section = QHBoxLayout()
        right_section.setSpacing(16)
        
        # Datum
        import datetime
        today = datetime.date.today()
        date_str = today.strftime("%d.%m.%Y")
        self.date_label = QLabel(date_str)
        self.date_label.setStyleSheet("""
            color: #6b7280;
            font-size: 14px;
            font-weight: 500;
        """)
        right_section.addWidget(self.date_label)
        
        layout.addLayout(right_section)
        
        # Spacing vor Fenster-Buttons
        layout.addSpacing(16)
        
        # Fenster-Buttons
        self.window_buttons = WindowButtons(parent)
        layout.addWidget(self.window_buttons)
    
    def set_title(self, title: str):
        self.title_label.setText(title)


class MainWindow(QMainWindow):
    """Hauptfenster mit moderner Sidebar-Navigation."""
    
    def __init__(self, benutzername: str = "", login_db_path: str = None):
        super().__init__()
        self.benutzername = benutzername
        self._login_db_path = login_db_path
        
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setWindowTitle(_("INAT Solutions v{}").format(__version__))
        self.setWindowIcon(QIcon(resource_path("icons/logo.svg")))
        
        # Höhe der Titelleiste für Fenster-Verschiebung
        self.title_bar_height = 60
        
        # Zentrales Widget
        central = QWidget()
        central.setStyleSheet(f"background-color: {COLORS['content_bg']};")
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Sidebar
        self.sidebar = ModernSidebar(self)
        main_layout.addWidget(self.sidebar)
        
        # Content-Bereich
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # Titelleiste
        self.title_bar = CustomTitleBar(self)
        self.window_buttons = self.title_bar.window_buttons
        content_layout.addWidget(self.title_bar)
        
        # Stacked Widget für die verschiedenen Seiten
        self.pages = QStackedWidget()
        self.pages.setStyleSheet(f"background-color: {COLORS['content_bg']};")
        content_layout.addWidget(self.pages)
        
        main_layout.addWidget(content_container, stretch=1)
        
        # Tabs/Seiten erstellen
        self.dashboard_tab = DashboardTab()
        self.rechnungen_tab = RechnungenTab()
        self.kunden_tab = KundenTab()
        self.auftragskalender_tab = AuftragskalenderTab()
        self.lager_tab = LagerTab()
        self.buchhaltung_tab = BuchhaltungTab()
        self.lieferanten_tab = LieferantenTab()
        self.einstellungen_tab = EinstellungenTab(self)
        
        # Seiten zum StackedWidget hinzufügen (Reihenfolge wie in Sidebar)
        self.pages.addWidget(self.dashboard_tab)      # 0
        self.pages.addWidget(self.rechnungen_tab)     # 1
        self.pages.addWidget(self.kunden_tab)         # 2
        self.pages.addWidget(self.auftragskalender_tab)  # 3
        self.pages.addWidget(self.lager_tab)          # 4
        self.pages.addWidget(self.buchhaltung_tab)    # 5
        self.pages.addWidget(self.lieferanten_tab)    # 6
        self.pages.addWidget(self.einstellungen_tab)  # 7
        
        # Titel-Mapping
        self.page_titles = [
            _("Dashboard"),
            _("Rechnungen"),
            _("Kunden"),
            _("Kalender"),
            _("Lager"),
            _("Buchhaltung"),
            _("Lieferanten"),
            _("Einstellungen"),
        ]
        
        # Signal-Verbindungen
        self.kunden_tab.kunde_aktualisiert.connect(self.rechnungen_tab.aktualisiere_kunden_liste)
        self.kunden_tab.kunde_aktualisiert.connect(self.auftragskalender_tab.update_customer_data)
        self._connect_signals()
        
        # Statusleiste verstecken (Benutzer-Info ist jetzt in Sidebar)
        self.statusBar().hide()
        
        # Benutzername in Sidebar setzen
        if self.benutzername:
            self.sidebar.set_user_info(self.benutzername, _("Administrator"))
        
        self.setCentralWidget(central)
        
        self.resize(1920, 1080)
        self.center_window()
        
        QTimer.singleShot(0, self.finish_init)
    
    def switch_to_page(self, index: int):
        """Wechselt zur angegebenen Seite."""
        if 0 <= index < self.pages.count():
            self.pages.setCurrentIndex(index)
            if index < len(self.page_titles):
                self.title_bar.set_title(self.page_titles[index])
    
    def _connect_signals(self):
        """Zentrale Methode für Signal-Slot-Verbindungen."""
        print(_("Richte zusätzliche Signal-Verbindungen ein..."))
        
        # Lieferanten → Lager
        self.lieferanten_tab.lieferant_aktualisiert.connect(
            self.lager_tab.aktualisiere_lieferanten_liste
        )
        
        # Einstellungen → Buchhaltung (Kategorien)
        self.einstellungen_tab.kategorien_geaendert.connect(
            self.buchhaltung_tab.aktualisiere_kategorien
        )
        
        # Rechnungen → Buchhaltung (Zahlung erfasst)
        self.rechnungen_tab.zahlung_erfasst.connect(
            self.buchhaltung_tab.lade_eintraege
        )
    
    def nativeEvent(self, eventType, message):
        """Native Windows-Events für Fenster-Verschiebung und -Größenänderung."""
        retval, result = super().nativeEvent(eventType, message)
        
        if eventType == b"windows_generic_MSG":
            msg = ctypes.wintypes.MSG.from_address(message.__int__())
            
            if msg.message == 0x0084:  # WM_NCHITTEST
                x_global = ctypes.c_short(msg.lParam & 0xFFFF).value
                y_global = ctypes.c_short((msg.lParam >> 16) & 0xFFFF).value
                
                global_pos = QPoint(x_global, y_global)
                local_pos = self.mapFromGlobal(global_pos)
                x = local_pos.x()
                y = local_pos.y()
                
                border_width = 8
                rect = self.rect()
                
                # Ecken
                if x < border_width and y < border_width:
                    return True, 13  # HTTOPLEFT
                if x > rect.width() - border_width and y < border_width:
                    return True, 14  # HTTOPRIGHT
                if x < border_width and y > rect.height() - border_width:
                    return True, 16  # HTBOTTOMLEFT
                if x > rect.width() - border_width and y > rect.height() - border_width:
                    return True, 17  # HTBOTTOMRIGHT
                
                # Kanten
                if y < border_width:
                    return True, 12  # HTTOP
                if y > rect.height() - border_width:
                    return True, 15  # HTBOTTOM
                if x < border_width:
                    return True, 10  # HTLEFT
                if x > rect.width() - border_width:
                    return True, 11  # HTRIGHT
                
                # Titelleiste (Sidebar-Bereich oder Titelleiste-Widget)
                sidebar_width = self.sidebar.width() if hasattr(self, 'sidebar') else 220
                
                # Im Sidebar-Bereich: Titelbereich für Verschiebung
                if x < sidebar_width and y < self.title_bar_height:
                    # Prüfen ob über Buttons
                    return True, 2  # HTCAPTION
                
                # Im Content-Bereich: Titelleiste
                if x >= sidebar_width and y < self.title_bar_height:
                    # Prüfen ob über Fenster-Buttons
                    if hasattr(self, 'window_buttons'):
                        buttons_pos = self.window_buttons.mapFromGlobal(global_pos)
                        if self.window_buttons.rect().contains(buttons_pos):
                            return retval, result  # Qt übernimmt
                    return True, 2  # HTCAPTION
        
        return retval, result
    
    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange:
            if hasattr(self, 'window_buttons'):
                self.window_buttons.update_maximize_icon()
        super().changeEvent(event)
    
    def finish_init(self):
        if getattr(self, "_deferred_started", False):
            return
        self._deferred_started = True

        try:
            from gui.tab_loader import TabLoader
        except Exception as e:
            print(f"[DBG] cannot import TabLoader: {e}", flush=True)
            return

        try:
            loader = TabLoader(key="buchhaltung", table="buchhaltung", chunk_size=200)
            t = QThread()
            loader.moveToThread(t)

            # route chunks to the real tab (must have append_rows / load_from_cache)
            if hasattr(self, "buchhaltung_tab") and self.buchhaltung_tab is not None:
                loader.chunk_ready.connect(lambda k, chunk, w=self.buchhaltung_tab: w.append_rows(chunk))
                # notify tab when loader finished so it can show "Keine Einträge" if empty
                try:
                    loader.finished.connect(lambda k, w=self.buchhaltung_tab: w.load_finished())
                except Exception:
                    pass

            # optional: total rows -> update progress (implement _on_loader_total if present)
            if hasattr(self, "_on_loader_total"):
                loader.total_rows.connect(self._on_loader_total)

            # debug prints / error routing
            loader.finished.connect(lambda k: print(f"[DBG] buchhaltung loader finished: {k}", flush=True))
            loader.error.connect(lambda k, msg: print(f"[DBG] loader error {k}: {msg}", flush=True))

            t.started.connect(loader.run)
            t.start()

            # keep reference to prevent GC
            if not hasattr(self, "_tab_loader_threads"):
                self._tab_loader_threads = []
            self._tab_loader_threads.append((t, loader))

            print("[DBG] started buchhaltung TabLoader", flush=True)
        except Exception as e:
            print(f"[DBG] start buchhaltung loader failed: {e}", flush=True)

        # start rechnungen loader (asynchronous like Buchhaltung) — STARTS ALWAYS
        try:
            # --- KORREKTUR: Dynamische Query für korrekte Sortierung ---
            with get_db() as conn:
                is_sqlite = getattr(conn, "is_sqlite", False)
            
            if is_sqlite:
                # SQLite: CAST zu INTEGER für numerische Sortierung
                order_clause = "ORDER BY CAST(rechnung_nr AS INTEGER) DESC, id DESC"
            else:
                # PostgreSQL: CAST zu BIGINT für numerische Sortierung
                order_clause = "ORDER BY CAST(NULLIF(regexp_replace(rechnung_nr, '\\D', '', 'g'), '') AS BIGINT) DESC NULLS LAST, id DESC"

            rechnungen_query = f"""
                SELECT id, rechnung_nr, kunde, firma, adresse, datum, mwst, zahlungskonditionen, positionen, uid, abschluss, COALESCE(abschluss_text,'') 
                FROM rechnungen 
                {order_clause}
            """

            loader_r = TabLoader(
                key="rechnungen",
                table="rechnungen",
                query=rechnungen_query,
                chunk_size=200
            )
            t_r = QThread()
            loader_r.moveToThread(t_r)

            if hasattr(self, "rechnungen_tab") and self.rechnungen_tab is not None:
                loader_r.chunk_ready.connect(lambda k, chunk, w=self.rechnungen_tab: w.append_rows(chunk))
                try:
                    loader_r.finished.connect(lambda k, w=self.rechnungen_tab: w.load_finished())
                except Exception:
                    pass

            # debug hooks
            loader_r.total_rows.connect(lambda k, total: print(f"[DBG] rechnungen total={total}", flush=True))
            loader_r.finished.connect(lambda k: print(f"[DBG] rechnungen loader finished: {k}", flush=True))
            loader_r.error.connect(lambda k, msg: print(f"[DBG] rechnungen loader error {k}: {msg}", flush=True))

            t_r.started.connect(loader_r.run)
            t_r.start()

            if not hasattr(self, "_tab_loader_threads"):
                self._tab_loader_threads = []
            self._tab_loader_threads.append((t_r, loader_r))

            print("[DBG] started rechnungen TabLoader", flush=True)
        except Exception as e:
            print(f"[DBG] start rechnungen loader failed: {e}", flush=True)

        # start kunden loader (asynchronous)
        try:
            loader_k = TabLoader(
                key="kunden",
                table="kunden",
                # --- KORREKTUR: Alphabetische Sortierung nach Namen hinzufügen ---
                query="SELECT * FROM kunden ORDER BY name ASC",
                chunk_size=200
            )
            t_k = QThread()
            loader_k.moveToThread(t_k)

            if hasattr(self, "kunden_tab") and self.kunden_tab is not None:
                loader_k.chunk_ready.connect(lambda k, chunk, w=self.kunden_tab: w.append_rows(chunk))
                try:
                    loader_k.finished.connect(lambda k, w=self.kunden_tab: w.load_finished())
                except Exception:
                    pass

            loader_k.total_rows.connect(lambda k, total: print(f"[DBG] kunden total={total}", flush=True))
            loader_k.finished.connect(lambda k: print(f"[DBG] kunden loader finished: {k}", flush=True))
            loader_k.error.connect(lambda k, msg: print(f"[DBG] kunden loader error {k}: {msg}", flush=True))

            t_k.started.connect(loader_k.run)
            t_k.start()

            if not hasattr(self, "_tab_loader_threads"):
                self._tab_loader_threads = []
            self._tab_loader_threads.append((t_k, loader_k))
            print("[DBG] started kunden TabLoader", flush=True)
        except Exception as e:
            print(f"[DBG] start kunden loader failed: {e}", flush=True)

        # start lieferanten loader
        try:
            loader_l = TabLoader(
                key="lieferanten",
                table="lieferanten",
                query="SELECT id, lieferantnr, name, portal_link, login, passwort FROM lieferanten ORDER BY name",
                chunk_size=100
            )
            t_l = QThread()
            loader_l.moveToThread(t_l)

            if hasattr(self, "lieferanten_tab") and self.lieferanten_tab is not None:
                loader_l.chunk_ready.connect(lambda k, chunk, w=self.lieferanten_tab: w.append_rows(chunk))
                try:
                    loader_l.finished.connect(lambda k, w=self.lieferanten_tab: w.load_finished())
                except Exception:
                    pass

            loader_l.total_rows.connect(lambda k, total: print(f"[DBG] lieferanten total={total}", flush=True))
            loader_l.finished.connect(lambda k: print(f"[DBG] lieferanten loader finished: {k}", flush=True))
            loader_l.error.connect(lambda k, msg: print(f"[DBG] lieferanten loader error {k}: {msg}", flush=True))

            t_l.started.connect(loader_l.run)
            t_l.start()

            if not hasattr(self, "_tab_loader_threads"):
                self._tab_loader_threads = []
            self._tab_loader_threads.append((t_l, loader_l))
            print("[DBG] started lieferanten TabLoader", flush=True)
        except Exception as e:
            print(f"[DBG] start lieferanten loader failed: {e}", flush=True)

    def center_window(self):
        """Zentriert das Fenster auf dem Bildschirm."""
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

