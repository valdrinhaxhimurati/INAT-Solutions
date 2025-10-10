from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QPushButton,
    QWidget, QScrollArea, QMessageBox
)
from PyQt5.QtCore import Qt
from db_connection import list_business_tables, clear_selected_tables, get_remote_status

class ClearDatabaseDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Datenbank löschen")
        self.setMinimumWidth(420)

        try:
            status = get_remote_status()
            is_remote = bool(status.get("use_remote", False))
        except Exception:
            is_remote = False
        mode_txt = "Remote (PostgreSQL)" if is_remote else "Lokal (SQLite)"

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        info = QLabel(f"Wählen Sie die Tabellen, die gelöscht werden sollen.\nModus: {mode_txt}\nHinweis: Die Benutzer-Tabelle 'users' wird nie gelöscht.")
        info.setWordWrap(True)
        root.addWidget(info)

        self.select_all_cb = QCheckBox("Alle auswählen")
        root.addWidget(self.select_all_cb)

        # Scrollbare Liste der Tabellen
        self.container = QWidget()
        self.container_lay = QVBoxLayout(self.container)
        self.container_lay.setContentsMargins(0, 0, 0, 0)
        self.container_lay.setSpacing(4)

        self.checks = []
        try:
            tables = list_business_tables(exclude=("users",))
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Tabellen konnten nicht geladen werden:\n{e}")
            tables = []
        for t in tables:
            cb = QCheckBox(t)
            self.container_lay.addWidget(cb, alignment=Qt.AlignLeft)
            self.checks.append(cb)
        self.container_lay.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.container)
        root.addWidget(scroll, 1)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.btn_clear = QPushButton("Löschen")
        self.btn_cancel = QPushButton("Abbrechen")
        btn_row.addWidget(self.btn_cancel)
        btn_row.addWidget(self.btn_clear)
        root.addLayout(btn_row)

        # Events
        self.select_all_cb.toggled.connect(self._toggle_all)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_clear.clicked.connect(self._on_clear)

    def _toggle_all(self, checked: bool):
        for cb in self.checks:
            cb.setChecked(checked)

    def _on_clear(self):
        selected = [cb.text() for cb in self.checks if cb.isChecked()]
        if not selected:
            QMessageBox.information(self, "Hinweis", "Bitte wählen Sie mindestens eine Tabelle aus.")
            return
        names = ", ".join(selected)
        res = QMessageBox.warning(
            self, "Bestätigen",
            f"Diese Aktion löscht alle Daten aus {len(selected)} Tabelle(n):\n{names}\n\nFortfahren?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if res != QMessageBox.Yes:
            return
        try:
            clear_selected_tables(selected)
            QMessageBox.information(self, "Erfolg", "Ausgewählte Tabellen wurden gelöscht.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Löschen fehlgeschlagen:\n{e}")