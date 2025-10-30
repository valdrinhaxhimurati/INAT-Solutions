from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QLabel, QDialog
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from gui.artikellager_tab import ArtikellagerTab
from gui.reifenlager_tab import ReifenlagerTab
from gui.materiallager_tab import MateriallagerTab
from gui.dienstleistungen_tab import DienstleistungenTab
from gui.lager_einstellungen_dialog import LagerEinstellungenDialog
from db_connection import get_db, dict_cursor_factory

def _to_bool(val):
    if isinstance(val, bool):
        return val
    if val is None:
        return False
    try:
        return bool(int(val))
    except Exception:
        s = str(val).strip().lower()
        return s in ("1", "true", "t", "yes", "y", "on")

class LagerTab(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self._load_aktive_lager()

    def _load_aktive_lager(self):
        # Layout leeren
        while self.layout.count():
            child = self.layout.takeAt(0)
            if child.widget():
                child.widget().setParent(None)

        # Tabs leeren und entfernen, falls vorhanden
        if hasattr(self, 'tabs'):
            self.tabs.clear()
            self.layout.removeWidget(self.tabs)
            self.tabs.setParent(None)
            self.tabs = None

        try:
            conn = get_db()
            cur = conn.cursor()
            # Wir lesen aktiv in Python aus, damit sowohl SQLite (0/1) als auch Postgres (TRUE/FALSE) funktionieren
            cur.execute("SELECT lager_typ, aktiv FROM lager_einstellungen")
            aktive = []
            for row in cur.fetchall():
                if isinstance(row, dict):
                    lager_typ = row.get('lager_typ')
                    aktiv_val = row.get('aktiv')
                else:
                    if len(row) >= 2:
                        lager_typ, aktiv_val = row[0], row[1]
                    else:
                        continue
                if lager_typ and _to_bool(aktiv_val):
                    aktive.append(lager_typ)
            conn.close()
        except Exception:
            aktive = []

        if len(aktive) == 0:
            # Stretch oben
            self.layout.addStretch()
            # Hinweis-Text
            self.hinweis = QLabel("Module können in den Einstellungen aktiviert werden.")
            self.hinweis.setAlignment(Qt.AlignCenter)
            font = self.hinweis.font()
            font.setPointSize(24)
            self.hinweis.setFont(font)
            self.layout.addWidget(self.hinweis)
            # Stretch unten
            self.layout.addStretch()
        else:
            # Tabs hinzufügen
            self.tabs = QTabWidget()
            if "material" in aktive:
                self.materiallager_tab = MateriallagerTab()
                self.tabs.addTab(self.materiallager_tab, "Material")
            if "reifen" in aktive:
                self.reifenlager_tab = ReifenlagerTab()
                self.tabs.addTab(self.reifenlager_tab, "Reifen")
            if "artikel" in aktive:
                self.artikellager_tab = ArtikellagerTab()
                self.tabs.addTab(self.artikellager_tab, "Artikel")
            if "dienstleistungen" in aktive:
                self.dienstleistungen_tab = DienstleistungenTab()
                self.tabs.addTab(self.dienstleistungen_tab, "Dienstleistungen")
            self.layout.addWidget(self.tabs)

    def _open_einstellungen(self):
        dlg = LagerEinstellungenDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            # Tabs neu laden
            self.tabs.clear()
            self._load_aktive_lager()


