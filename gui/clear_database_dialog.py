from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QCheckBox, QPushButton, QMessageBox,
    QHBoxLayout, QSpacerItem, QSizePolicy, QScrollArea, QWidget
)
from PyQt5.QtCore import Qt
# NEU: BaseDialog importieren
from .base_dialog import BaseDialog
from db_connection import clear_selected_tables, get_db

# ÄNDERUNG: Von BaseDialog erben
class ClearDatabaseDialog(BaseDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Datenbank leeren")
        self.setMinimumWidth(400)

        # WICHTIG: Das Layout vom BaseDialog verwenden
        layout = self.content_layout
        layout.setSpacing(15)

        info_label = QLabel(
            "<b>Achtung:</b> Diese Aktion löscht ausgewählte Daten unwiderruflich.\n"
            "Bitte wählen Sie die zu löschenden Tabellen aus."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        self.select_all_cb = QCheckBox("Alle auswÃ¤hlen")
        layout.addWidget(self.select_all_cb)

        # Scrollbare Liste der Tabellen
        self.container = QWidget()
        self.container_lay = QVBoxLayout(self.container)
        self.container_lay.setContentsMargins(0, 0, 0, 0)
        self.container_lay.setSpacing(4)

        self.checks = []
        tables = get_db().get_tables()  # ÄNDERUNG: Tabellen direkt von der DB abrufen
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
        layout.addWidget(scroll, 1)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)
        self.btn_clear = QPushButton("Löschen")
        self.btn_cancel = QPushButton("Abbrechen")
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_clear)
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
            QMessageBox.information(self, "Hinweis", "Bitte wÃ¤hlen Sie mindestens eine Tabelle aus.")
            return
        names = ", ".join(selected)
        res = QMessageBox.warning(
            self, "BestÃ¤tigen",
            f"Diese Aktion lÃ¶scht alle Daten aus {len(selected)} Tabelle(n):\n{names}\n\nFortfahren?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if res != QMessageBox.Yes:
            return
        try:
            clear_selected_tables(selected)
            QMessageBox.information(self, "Erfolg", "AusgewÃ¤hlte Tabellen wurden gelÃ¶scht.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"LÃ¶schen fehlgeschlagen:\n{e}")
