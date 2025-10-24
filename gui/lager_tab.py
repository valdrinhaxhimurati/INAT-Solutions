from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTabWidget
from gui.artikellager_tab import ArtikellagerTab
from gui.reifenlager_tab import ReifenlagerTab
from gui.materiallager_tab import MateriallagerTab
from db_connection import get_db, dict_cursor_factory

class LagerTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.tabs = QTabWidget()
        self.artikellager_tab = ArtikellagerTab()
        self.reifenlager_tab = ReifenlagerTab()
        self.materiallager_tab = MateriallagerTab()
        self.tabs.addTab(self.artikellager_tab, "Artikel")
        self.tabs.addTab(self.reifenlager_tab, "Reifen")
        self.tabs.addTab(self.materiallager_tab, "Material")
        layout.addWidget(self.tabs)
        self.setLayout(layout)


