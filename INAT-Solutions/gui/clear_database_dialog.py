from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QCheckBox, QPushButton, QMessageBox,
    QHBoxLayout, QSpacerItem, QSizePolicy, QScrollArea, QWidget, QGroupBox
)
from PyQt5.QtCore import Qt
# NEU: BaseDialog importieren
from .base_dialog import BaseDialog
from .dialog_styles import GROUPBOX_STYLE
from db_connection import clear_selected_tables, get_db, get_remote_status
from i18n import _


def _get_table_names():
    """Holt alle Tabellennamen aus der aktuellen Datenbank."""
    conn = get_db()
    cur = conn.cursor()
    # Prüfen ob PostgreSQL verwendet wird
    remote = get_remote_status()
    use_postgres = remote.get("use_remote", False) and remote.get("db_url")
    
    if use_postgres:
        cur.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        """)
    else:
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [row[0] for row in cur.fetchall()]
    cur.close()
    return tables


# ÄNDERUNG: Von BaseDialog erben
class ClearDatabaseDialog(BaseDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Datenbank leeren"))
        self.setMinimumWidth(400)

        # WICHTIG: Das Layout vom BaseDialog verwenden
        layout = self.content_layout
        layout.setSpacing(15)

        # === Warnung ===
        warning_group = QGroupBox(_("Warnung"))
        warning_group.setStyleSheet(GROUPBOX_STYLE)
        warning_layout = QVBoxLayout(warning_group)
        
        info_label = QLabel(
            _("<b>Achtung:</b> Diese Aktion löscht ausgewählte Daten unwiderruflich.\n"
            "Bitte wählen Sie die zu löschenden Tabellen aus.")
        )
        info_label.setWordWrap(True)
        warning_layout.addWidget(info_label)
        layout.addWidget(warning_group)

        # === Tabellen-Auswahl ===
        tables_group = QGroupBox(_("Tabellen auswählen"))
        tables_group.setStyleSheet(GROUPBOX_STYLE)
        tables_layout = QVBoxLayout(tables_group)
        
        self.select_all_cb = QCheckBox(_("Alle auswählen"))
        tables_layout.addWidget(self.select_all_cb)

        # Scrollbare Liste der Tabellen
        self.container = QWidget()
        self.container_lay = QVBoxLayout(self.container)
        self.container_lay.setContentsMargins(0, 0, 0, 0)
        self.container_lay.setSpacing(4)

        self.checks = []
        tables = _get_table_names()  # ÄNDERUNG: Hilfsfunktion verwenden
        for t in tables:
            if t == "users":
                continue  # Benutzer-Tabelle überspringen
            cb = QCheckBox(t)
            self.container_lay.addWidget(cb, alignment=Qt.AlignLeft)
            self.checks.append(cb)
        self.container_lay.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.container)
        tables_layout.addWidget(scroll, 1)
        layout.addWidget(tables_group, 1)

        # Buttons (zentriert)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)
        self.btn_clear = QPushButton(_("Löschen"))
        self.btn_cancel = QPushButton(_("Abbrechen"))
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_clear)
        btn_layout.addStretch(1)
        layout.addLayout(btn_layout)

        # ÄNDERUNG: self.setLayout() entfernen
        
    def get_tables_to_clear(self):
        return [cb.text() for cb in self.checks if cb.isChecked()]

    def _toggle_all(self, checked: bool):
        for cb in self.checks:
            cb.setChecked(checked)

    def _on_clear(self):
        selected = self.get_tables_to_clear()
        if not selected:
            QMessageBox.information(self, _("Hinweis"), _("Bitte wählen Sie mindestens eine Tabelle aus."))
            return
        names = ", ".join(selected)
        res = QMessageBox.warning(
            self, _("Bestätigen"),
            _("Diese Aktion löscht alle Daten aus {len(selected)} Tabelle(n):\n{names}\n\nFortfahren?"),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if res != QMessageBox.Yes:
            return
        try:
            clear_selected_tables(selected)
            QMessageBox.information(self, _("Erfolg"), _("Ausgewählte Tabellen wurden gelöscht."))
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, _("Fehler"), _("Löschen fehlgeschlagen:\n") + f"{e}")
