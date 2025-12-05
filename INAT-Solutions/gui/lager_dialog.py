from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QGroupBox, QFormLayout
)
from .base_dialog import BaseDialog
from .dialog_styles import GROUPBOX_STYLE
from db_connection import get_db, dict_cursor_factory
from i18n import _


class LagerDialog(BaseDialog):
    def __init__(self, parent=None, artikel=None):
        super().__init__(parent)
        self.setWindowTitle(_("Artikel erfassen") if artikel is None else _("Artikel bearbeiten"))
        self.resize(450, 380)

        layout = self.content_layout
        layout.setSpacing(15)

        # === Artikeldaten ===
        artikel_group = QGroupBox(_("Artikeldaten"))
        artikel_group.setStyleSheet(GROUPBOX_STYLE)
        artikel_layout = QFormLayout(artikel_group)
        artikel_layout.setSpacing(10)

        self.artikelnummer_input = QLineEdit()
        self.artikelnummer_input.setPlaceholderText(_("Pflichtfeld"))
        artikel_layout.addRow(_("Artikelnummer:"), self.artikelnummer_input)

        self.bezeichnung_input = QLineEdit()
        artikel_layout.addRow(_("Bezeichnung:"), self.bezeichnung_input)

        layout.addWidget(artikel_group)

        # === Lagerbestand ===
        bestand_group = QGroupBox(_("Lagerbestand"))
        bestand_group.setStyleSheet(GROUPBOX_STYLE)
        bestand_layout = QFormLayout(bestand_group)
        bestand_layout.setSpacing(10)

        self.bestand_input = QLineEdit()
        self.bestand_input.setPlaceholderText(_("Zahl eingeben"))
        bestand_layout.addRow(_("Bestand:"), self.bestand_input)

        self.lagerort_input = QLineEdit()
        bestand_layout.addRow(_("Lagerort:"), self.lagerort_input)

        layout.addWidget(bestand_group)

        if artikel:
            self.artikelnummer_input.setText(artikel.get("artikelnummer", ""))
            self.bezeichnung_input.setText(artikel.get("bezeichnung", ""))
            self.bestand_input.setText(str(artikel.get("bestand", "")))
            self.lagerort_input.setText(artikel.get("lagerort", ""))

        layout.addStretch()

        # === Buttons (zentriert) ===
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancel = QPushButton(_("Abbrechen"))
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_ok = QPushButton(_("Speichern"))
        btn_ok.clicked.connect(self.accept_dialog)
        btn_layout.addWidget(btn_ok)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def accept_dialog(self):
        if not self.artikelnummer_input.text().strip():
            QMessageBox.warning(self, _("Pflichtfeld"), _("Bitte Artikelnummer eingeben!"))
            return
        if not self.bestand_input.text().strip().isdigit():
            QMessageBox.warning(self, _("Pflichtfeld"), _("Bitte Bestand als Zahl eingeben!"))
            return
        self.accept()

    def get_daten(self):
        return {
            "artikelnummer": self.artikelnummer_input.text().strip(),
            "bezeichnung": self.bezeichnung_input.text().strip(),
            "bestand": int(self.bestand_input.text().strip()),
            "lagerort": self.lagerort_input.text().strip()
        }




