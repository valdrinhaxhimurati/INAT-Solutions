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
from PyQt5.QtCore import Qt

import sys
import os

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class MainWindow(QMainWindow):
    def __init__(self, benutzername=None):
        super().__init__()
        
        from main import LOGIN_DB_PATH
        
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
        user_label = QLabel(f"ðŸ‘¤  Angemeldet als: {self.benutzername}")
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
