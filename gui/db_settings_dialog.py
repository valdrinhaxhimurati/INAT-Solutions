from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QLineEdit, QCheckBox, QPushButton, QMessageBox, QWidget
)
from gui.utils import create_button_bar
from db_connection import get_remote_status, test_remote_connection, enable_remote, disable_remote

class DBSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Datenbank-Einstellungen")
        self.setMinimumWidth(520)

        status = get_remote_status()

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        gb = QGroupBox("Datenbank")
        v = QVBoxLayout(gb)
        v.setContentsMargins(16, 16, 16, 16)
        v.setSpacing(12)
        root.addWidget(gb)

        # Modus
        v.addWidget(QLabel("Modus"))
        self.remote_cb = QCheckBox("Remote-PostgreSQL verwenden")
        self.remote_cb.setChecked(bool(status.get("use_remote", False)))
        v.addWidget(self.remote_cb)

        # Remote-Bereich (wird komplett ein-/ausgeblendet)
        self.remote_container = QWidget()
        rc = QVBoxLayout(self.remote_container)
        rc.setContentsMargins(0, 0, 0, 0)
        rc.setSpacing(8)

        # URL Zeile: Label + Edit
        url_row = QHBoxLayout()
        url_row.setSpacing(8)
        self.db_url_label = QLabel("PostgreSQL-URL")
        url_row.addWidget(self.db_url_label)
        self.db_url_edit = QLineEdit()
        self.db_url_edit.setPlaceholderText("postgresql://user:pass@host:port/dbname")
        self.db_url_edit.setText(status.get("db_url") or "")
        url_row.addWidget(self.db_url_edit, 1)
        rc.addLayout(url_row)

        # Test-Button (links, wie der Rest)
        test_row = QHBoxLayout()
        self.btn_test = QPushButton("Verbindung testen")
        test_row.addWidget(self.btn_test)
        test_row.addStretch(1)
        rc.addLayout(test_row)

        v.addWidget(self.remote_container)

        # OK/Abbrechen (wie im Buchhaltungsdialog via create_button_bar)
        self.btn_speichern = QPushButton("Speichern")
        self.btn_abbrechen = QPushButton("Abbrechen")
        self.btn_speichern.clicked.connect(self._on_save)
        self.btn_abbrechen.clicked.connect(self.reject)
        root.addLayout(create_button_bar(self.btn_speichern, self.btn_abbrechen))

        # Sichtbarkeit initialisieren
        self.remote_cb.toggled.connect(self._update_enabled)
        self._update_enabled(self.remote_cb.isChecked())

        # Aktionen
        self.btn_test.clicked.connect(self._on_test)

    def _update_enabled(self, enabled: bool):
        self.remote_container.setVisible(enabled)
        self.db_url_edit.setEnabled(enabled)
        self.btn_test.setEnabled(enabled)

    def _on_test(self):
        url = self.db_url_edit.text().strip()
        if not url:
            QMessageBox.warning(self, "Test fehlgeschlagen", "Bitte eine PostgreSQL-URL eingeben.")
            return
        ok, err = test_remote_connection(url)
        if ok:
            QMessageBox.information(self, "Erfolg", "Verbindung erfolgreich.")
        else:
            QMessageBox.critical(self, "Fehler", f"Verbindung fehlgeschlagen:\n{err}")

    def _on_save(self):
        if self.remote_cb.isChecked():
            url = self.db_url_edit.text().strip()
            if not url:
                QMessageBox.warning(self, "Fehler", "Bitte eine PostgreSQL-URL eingeben.")
                return
            ok, err = test_remote_connection(url)
            if not ok:
                res = QMessageBox.question(
                    self, "Trotzdem speichern?",
                    f"Test fehlgeschlagen:\n{err}\n\nTrotzdem Remote aktivieren?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if res != QMessageBox.Yes:
                    return
            enable_remote(url)
        else:
            disable_remote()
        self.accept()

from gui.db_settings_dialog import DBSettingsDialog

def on_click_db_settings(self):
    dlg = DBSettingsDialog(self)
    dlg.exec_()