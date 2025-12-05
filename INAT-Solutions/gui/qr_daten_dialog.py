from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox,
    QHBoxLayout, QGroupBox, QFormLayout
)

from .base_dialog import BaseDialog
from .dialog_styles import GROUPBOX_STYLE
from db_connection import get_qr_daten, set_qr_daten
from paths import data_dir
import json, os
from i18n import _

CONFIG_PFAD = str(data_dir() / "qr_daten.json")


class QRDatenDialog(BaseDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("QR-Rechnungsdaten"))
        self.resize(520, 600)

        layout = self.content_layout
        layout.setSpacing(15)
        self.inputs = {}

        # === Empfänger ===
        empfaenger_group = QGroupBox(_("Empfänger"))
        empfaenger_group.setStyleSheet(GROUPBOX_STYLE)
        empfaenger_layout = QFormLayout(empfaenger_group)
        empfaenger_layout.setSpacing(10)

        self.inputs["name"] = QLineEdit()
        self.inputs["name"].setPlaceholderText(_("z.B. DeineFirma AG"))
        empfaenger_layout.addRow(_("Name:"), self.inputs["name"])

        self.inputs["street"] = QLineEdit()
        empfaenger_layout.addRow(_("Strasse:"), self.inputs["street"])

        self.inputs["pcode"] = QLineEdit()
        empfaenger_layout.addRow(_("PLZ:"), self.inputs["pcode"])

        self.inputs["city"] = QLineEdit()
        empfaenger_layout.addRow(_("Ort:"), self.inputs["city"])

        self.inputs["country"] = QLineEdit()
        self.inputs["country"].setPlaceholderText(_("z.B. CH"))
        empfaenger_layout.addRow(_("Land:"), self.inputs["country"])

        layout.addWidget(empfaenger_group)

        # === Zahlungsdaten ===
        zahlung_group = QGroupBox(_("Zahlungsdaten"))
        zahlung_group.setStyleSheet(GROUPBOX_STYLE)
        zahlung_layout = QFormLayout(zahlung_group)
        zahlung_layout.setSpacing(10)

        self.inputs["iban"] = QLineEdit()
        self.inputs["iban"].setPlaceholderText(_("QR-IBAN"))
        zahlung_layout.addRow(_("IBAN:"), self.inputs["iban"])

        self.inputs["currency"] = QLineEdit()
        self.inputs["currency"].setPlaceholderText(_("z.B. CHF"))
        zahlung_layout.addRow(_("Währung:"), self.inputs["currency"])

        self.inputs["reference"] = QLineEdit()
        self.inputs["reference"].setPlaceholderText(_("optional"))
        zahlung_layout.addRow(_("Referenznummer:"), self.inputs["reference"])

        self.inputs["unstructured_message"] = QLineEdit()
        zahlung_layout.addRow(_("Mitteilung:"), self.inputs["unstructured_message"])

        layout.addWidget(zahlung_group)

        layout.addStretch()

        # === Buttons (zentriert) ===
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.cancel_button = QPushButton(_("Abbrechen"))
        self.cancel_button.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_button)

        self.save_button = QPushButton(_("Speichern"))
        self.save_button.clicked.connect(self.save_data)
        btn_layout.addWidget(self.save_button)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.load_data()

    def load_data(self):
        try:
            config = get_qr_daten()
            creditor = config.get("creditor", {})
            self.inputs["name"].setText(creditor.get("name", ""))
            self.inputs["street"].setText(creditor.get("street", ""))
            self.inputs["pcode"].setText(creditor.get("pcode", ""))
            self.inputs["city"].setText(creditor.get("city", ""))
            self.inputs["country"].setText(creditor.get("country", ""))
            self.inputs["iban"].setText(config.get("iban", ""))
            self.inputs["currency"].setText(config.get("currency", "CHF"))
            self.inputs["reference"].setText(config.get("reference", ""))
            self.inputs["unstructured_message"].setText(config.get("unstructured_message", ""))
        except Exception:
            pass

    def save_data(self):
        daten = {
            "creditor": {
                "name": self.inputs["name"].text().strip(),
                "street": self.inputs["street"].text().strip(),
                "pcode": self.inputs["pcode"].text().strip(),
                "city": self.inputs["city"].text().strip(),
                "country": self.inputs["country"].text().strip()
            },
            "iban": self.inputs["iban"].text().strip(),
            "currency": self.inputs["currency"].text().strip(),
            "reference": self.inputs["reference"].text().strip(),
            "unstructured_message": self.inputs["unstructured_message"].text().strip(),
            "amount": 0
        }
        try:
            set_qr_daten(daten)
            QMessageBox.information(self, _("Gespeichert"), _("QR-Rechnungsdaten wurden gespeichert."))
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, _("Fehler"), _("Speichern fehlgeschlagen: {e}"))



