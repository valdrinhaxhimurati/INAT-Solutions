# -*- coding: utf-8 -*-
import ctypes
from PyQt5.QtWidgets import (
    QMainWindow, QTabWidget, QLabel, QWidget, QVBoxLayout, QHBoxLayout, QToolButton, QSizePolicy, QTabBar, QDesktopWidget
)
from db_connection import get_db, dict_cursor_factory
from PyQt5.QtGui import QFont
from gui.kunden_tab import KundenTab
from gui.rechnungen_tab import RechnungenTab
from gui.buchhaltung_tab import BuchhaltungTab
from gui.einstellungen_tab import EinstellungenTab
from gui.lieferanten_tab import LieferantenTab
from gui.lager_tab import LagerTab
from gui.auftragskalender_tab import AuftragskalenderTab 
from gui.widgets import WindowButtons

from version import __version__
from PyQt5.QtGui import QIcon, QPainter, QPixmap
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, QThread, QTimer, QPoint, QEvent
# NEUER IMPORT für die native Fenster-API
from PyQt5.QtWinExtras import QtWin

import sys
import os

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class DraggableTabBar(QTabBar):
    """
    Eine QTabBar, die nur als Platzhalter dient. Die Drag-Logik wird
    zentral in MainWindow.nativeEvent gehandhabt.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent


class CustomTitleBar(QWidget):
    """
    Ein Widget, das nur als Platzhalter für den Titelbereich dient. Die Drag-Logik
    wird zentral in MainWindow.nativeEvent gehandhabt.
    """
    def __init__(self, parent):
        super().__init__(parent)
        self.parent_window = parent


class MainWindow(QMainWindow):
    def __init__(self, benutzername: str = "", login_db_path: str = None):
        super().__init__()
        self.benutzername = benutzername
        self._login_db_path = login_db_path
        
        self.setWindowFlags(Qt.FramelessWindowHint)

        self.setWindowTitle(f"INAT Solutions v{__version__}")
        self.setWindowIcon(QIcon(resource_path("icons/logo.svg")))

        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Erstelle das Tab-Widget
        self.tabs = QTabWidget()
        self.tabs.setObjectName("mainTabs")
        self.tabs.setTabBar(DraggableTabBar(self))

        # Tabs sollen nicht automatisch breiter werden und bei Platzmangel scrollen
        self.tabs.tabBar().setExpanding(False)
        self.tabs.tabBar().setElideMode(Qt.ElideRight)
        self.tabs.setUsesScrollButtons(True)

        # Höhe der Titelleiste auf einen vernünftigen Wert setzen
        self.title_bar_height = 60
        self.tabs.tabBar().setFixedHeight(self.title_bar_height)

        # Linke Ecke: Logo-Container
        left_corner_container = CustomTitleBar(self)
        left_corner_container.setFixedHeight(self.title_bar_height)
        left_layout = QHBoxLayout(left_corner_container)
        left_layout.setContentsMargins(12, 0, 10, 0)
        icon_label = QLabel()
        # NEU: Hintergrund des Labels transparent machen
        icon_label.setStyleSheet("background: transparent;")
        # Logo-Größe an die neue Leistenhöhe anpassen
        icon_pixmap = QPixmap(resource_path("icons/logo.svg")).scaled(36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        icon_label.setPixmap(icon_pixmap)
        icon_label.setFixedHeight(self.title_bar_height) # Wichtig für vertikale Zentrierung
        left_layout.addWidget(icon_label, 0, Qt.AlignVCenter)

        # Rechte Ecke: Fenster-Buttons
        self.window_buttons = WindowButtons(self)
        self.window_buttons.setFixedHeight(self.title_bar_height)

        # 3. Setze die Corner-Widgets
        self.tabs.setCornerWidget(left_corner_container, Qt.TopLeftCorner)
        self.tabs.setCornerWidget(self.window_buttons, Qt.TopRightCorner)

        # 4. Füge die Tabs hinzu
        self.kunden_tab = KundenTab()
        self.rechnungen_tab = RechnungenTab()
        self.buchhaltung_tab = BuchhaltungTab()
        self.lieferanten_tab = LieferantenTab()
        self.lager_tab = LagerTab() 
        self.auftragskalender_tab = AuftragskalenderTab()
        self.einstellungen_tab = EinstellungenTab(self)
        self.kunden_tab.kunde_aktualisiert.connect(self.rechnungen_tab.aktualisiere_kunden_liste)
        self.kunden_tab.kunde_aktualisiert.connect(self.auftragskalender_tab.update_customer_data)

        
        self.resize(1920, 1080)
        self.center_window()

        # Aufruf der zentralen Methode zum Verbinden von Signalen
        self._connect_signals()

        self.tabs.addTab(self.kunden_tab, "Kunden")
        self.tabs.addTab(self.rechnungen_tab, "Rechnungen")
        self.tabs.addTab(self.buchhaltung_tab, "Buchhaltung")
        self.tabs.addTab(self.lieferanten_tab, "Lieferanten")
        self.tabs.addTab(self.lager_tab, "Lager")
        self.tabs.addTab(self.auftragskalender_tab, "Auftragskalender")
        self.tabs.addTab(self.einstellungen_tab, "Einstellungen")

        main_layout.addWidget(self.tabs)

        # Statusleiste
        self.status_bar = self.statusBar()
        user_label = QLabel(f"👤  Angemeldet als: {self.benutzername}")
        font = QFont("Segoe UI", 15)
        font.setBold(False)
        user_label.setFont(font)
        user_label.setStyleSheet("""
            QLabel {
                background: transparent;
                border: none;
                color: #4a6fa5;
                font-size: 15px;
                font-weight: normal;
                padding-left: 10px;
                padding-right: 10px;
            }
        """)
        self.status_bar.addWidget(user_label)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.status_bar.addWidget(spacer, 1)

        version_label = QLabel(f"v{__version__}")
        version_label.setStyleSheet("""
            QLabel {
                background: transparent;
                border: none;
                color: #888;
                font-size: 14px;
                padding-right: 10px;
            }
        """)
        self.status_bar.addWidget(version_label)

        self.setCentralWidget(main_widget)
        QTimer.singleShot(0, self.finish_init)

    # --- NEUE METHODE ---
    def _connect_signals(self):
        """Zentrale Methode, um alle Signal-Slot-Verbindungen zu erstellen."""
        
        print("Richte zusätzliche Signal-Verbindungen ein...")

        # Verbindungen:
        # ------------------------------------

        # 2. Lieferanten-Änderungen
        # QUELLE: LieferantenTab | ZIEL: LagerTab
        self.lieferanten_tab.lieferant_aktualisiert.connect(self.lager_tab.aktualisiere_lieferanten_liste)

        # 3. Buchhaltungs-Kategorien-Änderungen
        # QUELLE: EinstellungenTab | ZIEL: BuchhaltungTab
        self.einstellungen_tab.kategorien_geaendert.connect(self.buchhaltung_tab.aktualisiere_kategorien)




    def nativeEvent(self, eventType, message):
        """
        Fängt native Windows-Nachrichten ab, um das Verhalten eines Standard-Fensters
        (Verschieben, Größenänderung, Aero Snap) korrekt zu implementieren.
        """
        retval, result = super().nativeEvent(eventType, message)
        
        if eventType == b"windows_generic_MSG":
            msg = ctypes.wintypes.MSG.from_address(message.__int__())

            if msg.message == 0x0084:  # WM_NCHITTEST
                # Korrekte Extraktion der Mausposition (behandelt auch negative Werte)
                x_global = ctypes.c_short(msg.lParam & 0xFFFF).value
                y_global = ctypes.c_short((msg.lParam >> 16) & 0xFFFF).value
                
                # Globale Position in Widget-lokale Koordinaten umrechnen
                global_pos = QPoint(x_global, y_global)
                local_pos = self.mapFromGlobal(global_pos)
                x = local_pos.x()
                y = local_pos.y()
                
                # Größenänderung an den Fensterrändern (höchste Priorität)
                border_width = 8
                rect = self.rect()
                
                # Ecken haben Vorrang
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
                
                # Titelleiste (nur wenn nicht an den Rändern)
                if y < self.title_bar_height:
                    # Prüfen, ob die Maus über einem Tab ist
                    tab_bar = self.tabs.tabBar()
                    tab_local_pos = tab_bar.mapFromGlobal(global_pos)
                    tab_at_pos = tab_bar.tabAt(tab_local_pos)
                    
                    # Wenn über einem Tab -> normale Qt-Verarbeitung
                    if tab_at_pos != -1:
                        return retval, result  # Qt übernimmt
                    
                    # Prüfen, ob die Maus über den Fenster-Buttons ist
                    buttons_widget = self.window_buttons
                    buttons_local_pos = buttons_widget.mapFromGlobal(global_pos)
                    
                    # Wenn über den Buttons -> normale Qt-Verarbeitung
                    if buttons_widget.rect().contains(buttons_local_pos):
                        return retval, result  # Qt übernimmt
                    
                    # Maus ist im leeren Bereich der Titelleiste (Logo, Lücke)
                    # -> Windows mitteilen, dass dies die Titelleiste ist
                    return True, 2  # HTCAPTION

        return retval, result

    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange:
            if hasattr(self, 'window_buttons'):
                self.window_buttons.update_maximize_icon()
        super().changeEvent(event)

    # Für einen Button
    def animate_button(self, button):
        anim = QPropertyAnimation(button, b"geometry")
        anim.setDuration(300)
        anim.setEasingCurve(QEasingCurve.InOutQuad)
        anim.setStartValue(button.geometry())
        anim.setEndValue(button.geometry().adjusted(0, -5, 0, -5))  # Leichter Lift
        anim.start()

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

