from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
)
from db_connection import get_qr_daten, set_qr_daten
from paths import data_dir
import json, os

CONFIG_PFAD = str(data_dir() / "qr_daten.json")


class QRDatenDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("QR-Rechnungsdaten")
        layout = QVBoxLayout()

        self.inputs = {}

        felder = [
            ("name", "Empfängername (z. B. DeineFirma AG)"),
            ("street", "Empfängerstraße"),
            ("pcode", "PLZ"),
            ("city", "Ort"),
            ("country", "Land (z. B. CH)"),
            ("iban", "IBAN (QR-IBAN)"),
            ("currency", "Währung (z. B. CHF)"),
            ("reference", "Referenznummer (optional)"),
            ("unstructured_message", "Mitteilung / Zahlungszweck"),
        ]


        for key, label in felder:
            layout.addWidget(QLabel(label))
            line_edit = QLineEdit()
            self.inputs[key] = line_edit
            layout.addWidget(line_edit)

        self.save_button = QPushButton("Speichern")
        self.save_button.clicked.connect(self.save_data)
        layout.addWidget(self.save_button)

        self.setLayout(layout)
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
            QMessageBox.information(self, "Gespeichert", "QR-Rechnungsdaten wurden gespeichert.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Speichern fehlgeschlagen: {e}")


