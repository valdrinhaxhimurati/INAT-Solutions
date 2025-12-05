# -*- coding: utf-8 -*-
"""
Release Notes - Zeigt Neuigkeiten nach einem Update an
"""
from datetime import datetime
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QFrame, QCheckBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from db_connection import get_config_value, set_config_value
from version import __version__
from i18n import _

# Deutsche Monatsnamen
MONATE = {
    1: "Januar", 2: "Februar", 3: "März", 4: "April",
    5: "Mai", 6: "Juni", 7: "Juli", 8: "August",
    9: "September", 10: "Oktober", 11: "November", 12: "Dezember"
}

def get_current_month_year():
    """Gibt den aktuellen Monat und Jahr auf Deutsch zurück."""
    now = datetime.now()
    return f"{MONATE[now.month]} {now.year}"

# Release Notes für jede Version
def get_release_notes():
    """Generiert die Release Notes mit aktuellem Datum."""
    return {
        "0.9.2.0": {
            "titel": f"Version {__version__} - {get_current_month_year()}",
            "highlights": [
                "🎨 Neues Dashboard-Design mit professionellem Look",
                "📄 Live-PDF-Vorschau im Rechnungslayout-Dialog",
                "💳 Neue Funktion: Zahlung direkt erfassen",
                "🎯 12 verschiedene Rechnungsstile zur Auswahl",
            ],
            "details": """
<h3>Dashboard</h3>
<ul>
<li>Komplett überarbeitetes Dashboard mit modernem Design</li>
<li>Statistik-Karten zeigen nur noch aktive Module an</li>
<li>Verbesserte Lesbarkeit mit größeren Schriften</li>
<li>Einheitliche Farben passend zur Anwendung</li>
</ul>

<h3>Rechnungslayout</h3>
<ul>
<li>Live-Vorschau: Änderungen werden sofort als PDF-Bild angezeigt</li>
<li>12 professionelle Stile: Classic, Corporate, Modern, Elegant, Swiss, und mehr</li>
<li>Kopfzeile/Logo sind jetzt gegenseitig exklusiv (bessere Übersicht)</li>
<li>Vorschau und Export sehen jetzt identisch aus</li>
</ul>

<h3>Rechnungen</h3>
<ul>
<li>Neue Funktion "Zahlung erfassen" direkt aus der Rechnungsliste</li>
<li>Automatische Verknüpfung mit der Buchhaltung</li>
<li>Status wird automatisch auf "Bezahlt" gesetzt</li>
</ul>

<h3>Verbesserungen</h3>
<ul>
<li>Stabilere Datenbankverbindung für SQLite und PostgreSQL</li>
<li>Bessere Fehlerbehandlung beim Speichern</li>
<li>Optimierte Performance beim Laden großer Datensätze</li>
</ul>
"""
        },
    }


class ReleaseNotesDialog(QDialog):
    """Dialog zur Anzeige der Release Notes nach einem Update."""
    
    def __init__(self, version: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Was ist neu in INAT Solutions"))
        self.setMinimumSize(780, 930)  
        self.resize(840, 1015)  
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        notes = get_release_notes().get(version, {})
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # Header
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #4a6fa5, stop:1 #3b5b85);
                border-radius: 10px;
                padding: 15px;
            }
        """)
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(20, 15, 20, 15)
        
        title = QLabel(notes.get("titel", f"Version {version}"))
        title.setStyleSheet("color: white; font-size: 29px; font-weight: bold; background: transparent;")
        header_layout.addWidget(title)
        
        subtitle = QLabel(_("Vielen Dank für das Update!"))
        subtitle.setStyleSheet("color: rgba(255,255,255,0.8); font-size: 17px; background: transparent;")
        header_layout.addWidget(subtitle)
        
        layout.addWidget(header)
        
        # Highlights
        if notes.get("highlights"):
            highlights_label = QLabel(_("Highlights"))
            highlights_label.setStyleSheet("color: #333; font-size: 19px; font-weight: 600; margin-top: 10px;")
            layout.addWidget(highlights_label)
            
            highlights_frame = QFrame()
            highlights_frame.setStyleSheet("""
                QFrame {
                    background-color: #f0f4fb;
                    border: 1px solid #d0d8e0;
                    border-radius: 8px;
                    padding: 10px;
                }
            """)
            highlights_layout = QVBoxLayout(highlights_frame)
            highlights_layout.setSpacing(8)
            highlights_layout.setContentsMargins(15, 12, 15, 12)
            
            for highlight in notes.get("highlights", []):
                hl = QLabel(highlight)
                hl.setStyleSheet("color: #333; font-size: 17px; background: transparent;")
                highlights_layout.addWidget(hl)
            
            layout.addWidget(highlights_frame)
        
        # Details
        if notes.get("details"):
            details_label = QLabel(_("Details"))
            details_label.setStyleSheet("color: #333; font-size: 19px; font-weight: 600; margin-top: 5px;")
            layout.addWidget(details_label)
            
            details_text = QTextEdit()
            details_text.setReadOnly(True)
            details_text.setHtml(notes.get("details", ""))
            details_text.setStyleSheet("""
                QTextEdit {
                    background-color: white;
                    border: 1px solid #c2c9d8;
                    border-radius: 8px;
                    padding: 10px;
                    font-size: 16px;
                    color: #333;
                }
            """)
            layout.addWidget(details_text, 1)
        
        # Footer mit Checkbox
        footer = QHBoxLayout()
        footer.setSpacing(15)
        
        self.dont_show_again = QCheckBox(_("Nicht mehr für diese Version anzeigen"))
        self.dont_show_again.setStyleSheet("color: #666; font-size: 14px;")
        footer.addWidget(self.dont_show_again)
        
        footer.addStretch()
        
        btn_ok = QPushButton(_("Verstanden"))
        btn_ok.setMinimumWidth(120)
        btn_ok.clicked.connect(self._on_ok)
        footer.addWidget(btn_ok)
        
        layout.addLayout(footer)
    
    def _on_ok(self):
        if self.dont_show_again.isChecked():
            # Speichere dass diese Version bereits angezeigt wurde
            try:
                set_config_value("last_shown_release_notes", __version__)
            except Exception:
                pass
        self.accept()


def should_show_release_notes() -> bool:
    """Prüft ob Release Notes angezeigt werden sollen."""
    try:
        last_shown = get_config_value("last_shown_release_notes", "")
        # Zeige nur wenn:
        # 1. Die aktuelle Version in get_release_notes() vorhanden ist
        # 2. Die Version noch nicht angezeigt wurde
        return __version__ in get_release_notes() and last_shown != __version__
    except Exception:
        return False


def show_release_notes_if_needed(parent=None):
    """Zeigt Release Notes an wenn ein Update durchgeführt wurde."""
    if should_show_release_notes():
        dialog = ReleaseNotesDialog(__version__, parent)
        dialog.exec_()


def mark_release_notes_shown():
    """Markiert die aktuelle Version als angezeigt."""
    try:
        set_config_value("last_shown_release_notes", __version__)
    except Exception:
        pass
