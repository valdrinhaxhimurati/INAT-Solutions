from PyQt5.QtWidgets import (
    QGroupBox, QLabel, QLineEdit, QCheckBox,
    QPushButton, QWidget, QHBoxLayout, QFormLayout, QMessageBox, QRadioButton, QApplication
)
from PyQt5.QtCore import Qt, QProcess
from gui.utils import create_button_bar
from db_connection import get_remote_status, test_remote_connection, enable_remote, disable_remote
from gui.base_dialog import BaseDialog

class DBSettingsDialog(BaseDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Datenbank-Einstellungen"))

        status = get_remote_status()
        self._initial_use_remote = bool(status.get("use_remote", False))
        self._initial_url = (status.get("db_url") or "").strip()

        # Root-Layout
        root = self.content_layout
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # GroupBox + FormLayout
        gb = QGroupBox(_("Datenbank"))
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        form.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)
        gb.setLayout(form)
        root.addWidget(gb)

        # Modus: Lokal/Remote
        self.lbl_modus = QLabel(_("Modus"))
        mode_field = QWidget()
        mode_row = QHBoxLayout(mode_field)
        mode_row.setContentsMargins(0, 0, 0, 0)
        mode_row.setSpacing(16)
        self.local_rb = QRadioButton(_("Lokal"))
        self.remote_rb = QRadioButton(_("Remote"))
        (self.remote_rb if self._initial_use_remote else self.local_rb).setChecked(True)
        mode_row.addWidget(self.local_rb)
        mode_row.addWidget(self.remote_rb)
        form.addRow(self.lbl_modus, mode_field)

        # URL-Zeile: Label + (LineEdit + Test-Button)
        self.url_label = QLabel(_("PostgreSQL-URL"))
        url_field = QWidget()
        url_row = QHBoxLayout(url_field)
        url_row.setContentsMargins(0, 0, 0, 0)
        url_row.setSpacing(8)

        self.db_url_edit = QLineEdit()
        self.db_url_edit.setPlaceholderText("postgresql://user:pass@host:port/dbname")
        self.db_url_edit = QLineEdit()
        self.db_url_edit.setText(self._initial_url)
        self.db_url_edit.setMinimumWidth(360)

        self.btn_test = QPushButton(_("Verbindung testen"))

        url_row.addWidget(self.db_url_edit, 1)
        url_row.addWidget(self.btn_test, 0)
        form.addRow(self.url_label, url_field)

        # OK/Abbrechen
        self.btn_speichern = QPushButton(_("Speichern"))
        self.btn_abbrechen = QPushButton(_("Abbrechen"))
        self.btn_speichern.clicked.connect(self._on_save)
        self.btn_abbrechen.clicked.connect(self.reject)
        root.addLayout(create_button_bar(self.btn_speichern, self.btn_abbrechen))

        # Events
        self.local_rb.toggled.connect(self._sync_mode_ui)
        self.remote_rb.toggled.connect(self._sync_mode_ui)
        self.btn_test.clicked.connect(self._on_test)

        # Initial UI-State
        self._sync_mode_ui()

        # 15% größer starten
        self.resize(int(self.sizeHint().width() * 1.15), int(self.sizeHint().height() * 1.15))

    def _sync_mode_ui(self):
        is_remote = self.remote_rb.isChecked()
        self.url_label.setVisible(is_remote)
        self.db_url_edit.parentWidget().setVisible(is_remote)
        self.db_url_edit.setEnabled(is_remote)
        self.btn_test.setEnabled(is_remote)

    def _on_test(self):
        url = self.db_url_edit.text().strip()
        if not url:
            QMessageBox.warning(self, _("Test fehlgeschlagen"), _("Bitte eine PostgreSQL-URL eingeben."))
            return
        ok, err = test_remote_connection(url)
        if ok:
            QMessageBox.information(self, _("Erfolg"), _("Verbindung erfolgreich."))
        else:
            QMessageBox.critical(self, _("Fehler"), _("Verbindung fehlgeschlagen:") + f"\n{err}")

    def _on_save(self):
        is_remote = self.remote_rb.isChecked()
        new_url = self.db_url_edit.text().strip()

        if is_remote:
            if not new_url:
                QMessageBox.warning(self, _("Fehler"), _("Bitte eine PostgreSQL-URL eingeben."))
                return
            ok, err = test_remote_connection(new_url)
            if not ok:
                res = QMessageBox.question(
                    self, _("Trotzdem speichern?"),
                    _("Test fehlgeschlagen:") + f"\n{err}\n\n" + _("Trotzdem Remote aktivieren?"),
                    QMessageBox.Yes | QMessageBox.No
                )
                if res != QMessageBox.Yes:
                    return
            enable_remote(new_url)
        else:
            disable_remote()

        changed = (is_remote != self._initial_use_remote) or (is_remote and new_url != self._initial_url)
        if changed:
            # Neustart vorschlagen und ggf. ausführen
            res = QMessageBox.question(
                self,
                "Neustart erforderlich",
                "Die Datenbank-Einstellungen wurden geändert. Anwendung jetzt neu starten?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if res == QMessageBox.Yes:
                import sys
                QProcess.startDetached(sys.executable, sys.argv)
                QApplication.instance().quit()
                return

        self.accept()

from gui.db_settings_dialog import DBSettingsDialog

def on_click_db_settings(self):
    dlg = DBSettingsDialog(self)
    dlg.exec_()
