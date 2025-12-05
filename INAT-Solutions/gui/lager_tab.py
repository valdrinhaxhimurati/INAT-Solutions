from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QLabel, QDialog, QFrame, QHBoxLayout, QPushButton
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from gui.artikellager_tab import ArtikellagerTab
from gui.reifenlager_tab import ReifenlagerTab
from gui.materiallager_tab import MateriallagerTab
from gui.dienstleistungen_tab import DienstleistungenTab
from gui.lager_einstellungen_dialog import LagerEinstellungenDialog
from gui.modern_widgets import COLORS, FONT_SIZES, SPACING, BORDER_RADIUS
from db_connection import get_db, dict_cursor_factory
from i18n import _

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
        self.setStyleSheet(f"background-color: {COLORS['background']};")
        
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.setLayout(self.layout)
        self._load_aktive_lager()

    # NEU: Öffentliche Methode (Slot) zum Empfangen und Weiterleiten von Aktualisierungen
    def aktualisiere_lieferanten_liste(self):
        """
        Wird aufgerufen, wenn sich die Lieferantenliste ändert.
        Leitet die Anforderung an relevante Unter-Tabs weiter.
        """
        print("LagerTab: Signal 'lieferant_aktualisiert' empfangen.")
        
        # Prüfen, ob der Materiallager-Tab existiert und eine Aktualisierungsmethode hat
        if hasattr(self, 'materiallager_tab') and hasattr(self.materiallager_tab, 'aktualisiere_daten'):
            print("--> Leite Aktualisierung an MateriallagerTab weiter.")
            self.materiallager_tab.aktualisiere_daten()
        
        # Hier könnten zukünftig weitere Unter-Tabs (z.B. Artikellager) aktualisiert werden.

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
            # Container für zentrierten Hinweis
            container = QWidget()
            container.setStyleSheet(f"background-color: {COLORS['background']};")
            container_layout = QVBoxLayout(container)
            container_layout.addStretch()
            
            # Hinweis-Karte
            hint_card = QFrame()
            hint_card.setStyleSheet(f"""
                QFrame {{
                    background-color: {COLORS['surface']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 12px;
                    padding: 40px;
                }}
            """)
            hint_layout = QVBoxLayout(hint_card)
            hint_layout.setAlignment(Qt.AlignCenter)
            
            self.hinweis = QLabel(_("\U0001F4E6 Module k\u00f6nnen in den Einstellungen aktiviert werden."))
            self.hinweis.setAlignment(Qt.AlignCenter)
            self.hinweis.setStyleSheet(f"""
                color: {COLORS['text_secondary']};
                font-size: {FONT_SIZES['subtitle']}px;
            """)
            hint_layout.addWidget(self.hinweis)
            
            container_layout.addWidget(hint_card, alignment=Qt.AlignCenter)
            container_layout.addStretch()
            self.layout.addWidget(container)
        else:
            # Moderner Tab-Container
            container = QWidget()
            container.setStyleSheet(f"background-color: {COLORS['background']};")
            container_layout = QVBoxLayout(container)
            container_layout.setContentsMargins(SPACING['xl'], SPACING['xl'], SPACING['xl'], SPACING['xl'])
            container_layout.setSpacing(0)
            
            # Tabs im Showcase-Stil (flache Tabs in weisser Karte)
            self.tabs = QTabWidget()
            self.tabs.setStyleSheet(f"""
                QTabWidget::pane {{
                    background-color: {COLORS['surface']};
                    border: none;
                    border-top: 1px solid {COLORS['border']};
                }}
                QTabWidget {{
                    background-color: {COLORS['surface']};
                    border: 1px solid {COLORS['border']};
                    border-radius: {BORDER_RADIUS['lg']}px;
                }}
                QTabBar {{
                    background-color: {COLORS['surface']};
                }}
                QTabBar::tab {{
                    background-color: transparent;
                    color: {COLORS['text_secondary']};
                    border: none;
                    border-bottom: 2px solid transparent;
                    padding: 14px 24px;
                    margin: 0;
                    font-size: {FONT_SIZES['button']}px;
                    font-weight: 500;
                }}
                QTabBar::tab:selected {{
                    color: {COLORS['primary']};
                    border-bottom: 2px solid {COLORS['primary']};
                    font-weight: 600;
                }}
                QTabBar::tab:hover:!selected {{
                    color: {COLORS['text_primary']};
                }}
            """)
            
            if "material" in aktive:
                self.materiallager_tab = MateriallagerTab()
                self.tabs.addTab(self.materiallager_tab, _("Materiallager"))
            if "reifen" in aktive:
                self.reifenlager_tab = ReifenlagerTab()
                self.tabs.addTab(self.reifenlager_tab, _("Reifenlager"))
            if "artikel" in aktive:
                self.artikellager_tab = ArtikellagerTab()
                self.tabs.addTab(self.artikellager_tab, _("Artikellager"))
            if "dienstleistungen" in aktive:
                self.dienstleistungen_tab = DienstleistungenTab()
                self.tabs.addTab(self.dienstleistungen_tab, _("Dienstleistungen"))
            
            container_layout.addWidget(self.tabs)
            self.layout.addWidget(container)

    def _open_einstellungen(self):
        dlg = LagerEinstellungenDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            # Tabs neu laden
            self.tabs.clear()
            self._load_aktive_lager()


