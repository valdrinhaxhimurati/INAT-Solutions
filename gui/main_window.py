# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QMainWindow, QTabWidget, QLabel, QWidget 
)
from db_connection import get_db, dict_cursor_factory
from PyQt5.QtGui import QFont
from gui.kunden_tab import KundenTab
from gui.rechnungen_tab import RechnungenTab
from gui.buchhaltung_tab import BuchhaltungTab
from gui.einstellungen_tab import EinstellungenTab
from gui.lieferanten_tab import LieferantenTab
from gui.lager_tab import LagerTab

from version import __version__
from PyQt5.QtGui import QIcon, QPainter, QPixmap
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, QThread, QTimer

import sys
import os

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class MainWindow(QMainWindow):
    def __init__(self, benutzername: str = "", login_db_path: str = None):
        super().__init__()
        self.benutzername = benutzername
        self._login_db_path = login_db_path
        self.setWindowTitle("Deine Anwendung")
        self.resize(1920, 1080)
        self.benutzername = benutzername or "Unbekannt"
        self.logo_path = "C:/Users/V.Haxhimurati/Documents/TEST/INAT SOLUTIONS.png"
        self.setWindowTitle(f"INAT Solutions v{__version__}")
        self.setWindowIcon(QIcon(resource_path("favicon.ico")))


        self.tabs = QTabWidget()
        self.kunden_tab = KundenTab()
        self.rechnungen_tab = RechnungenTab()
        self.buchhaltung_tab = BuchhaltungTab()
        self.lieferanten_tab = LieferantenTab()
        self.lager_tab = LagerTab()  
        self.einstellungen_tab = EinstellungenTab(self)
        self.kunden_tab.kunde_aktualisiert.connect(self.rechnungen_tab.aktualisiere_kunden_liste)

        self.tabs.addTab(self.kunden_tab, "Kunden")
        self.tabs.addTab(self.rechnungen_tab, "Rechnungen")
        self.tabs.addTab(self.buchhaltung_tab, "Buchhaltung")
        self.tabs.addTab(self.lieferanten_tab, "Lieferanten")
        self.tabs.addTab(self.lager_tab, "Lager")
        self.tabs.addTab(self.einstellungen_tab, "Einstellungen")

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

        self.setCentralWidget(self.tabs)

        # schedule background init after event-loop / after show to avoid blocking UI
        QTimer.singleShot(0, self.finish_init)

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
            loader_r = TabLoader(
                key="rechnungen",
                table="rechnungen",
                query="SELECT id, rechnung_nr, kunde, firma, adresse, datum, mwst, zahlungskonditionen, positionen, uid, abschluss, COALESCE(abschluss_text,'') FROM public.rechnungen ORDER BY datum DESC",
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

        # start kunden loader (asynchronous like others) — STARTS ALWAYS
        try:
            loader_k = TabLoader(
                key="kunden",
                table="kunden",
                query="SELECT kundennr, anrede, name, firma, plz, strasse, stadt, email, bemerkung FROM kunden ORDER BY kundennr",
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

