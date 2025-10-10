from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
)
from db_connection import get_db, dict_cursor_factory
import json
import os

CONFIG_PFAD = os.path.join("config", "qr_daten.json")


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
        if os.path.exists(CONFIG_PFAD):
            try:
                with open(CONFIG_PFAD, "r", encoding="utf-8") as f:
                    config = json.load(f)
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
            except (json.JSONDecodeError, IOError):
                pass

    def save_data(self):
        # Pflichtfelder prüfen
        fehlende_felder = []
        if not self.inputs["name"].text().strip():
            fehlende_felder.append("Empfängername")
        if not self.inputs["street"].text().strip():
            fehlende_felder.append("Straße")
        if not self.inputs["pcode"].text().strip():
            fehlende_felder.append("PLZ")
        if not self.inputs["city"].text().strip():
            fehlende_felder.append("Ort")
        if not self.inputs["country"].text().strip():
            fehlende_felder.append("Land")
        if not self.inputs["iban"].text().strip():
            fehlende_felder.append("IBAN")

        if fehlende_felder:
            QMessageBox.warning(
                self,
                "Pflichtfelder fehlen",
                "Bitte füllen Sie folgende Felder aus:\n\n" + "\n".join(fehlende_felder)
            )
            return  # Nicht speichern!
        
        os.makedirs(os.path.dirname(CONFIG_PFAD), exist_ok=True)

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


        with open(CONFIG_PFAD, "w", encoding="utf-8") as f:
            json.dump(daten, f, indent=4)

        QMessageBox.information(self, "Gespeichert", "QR-Rechnungsdaten wurden gespeichert.")
        self.accept()


