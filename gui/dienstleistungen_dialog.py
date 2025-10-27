# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QTextEdit, QPushButton, QHBoxLayout, QComboBox
from PyQt5.QtCore import Qt
class DienstleistungenDialog(QDialog):
    def __init__(self, parent=None, dienstleistung=None):
        super().__init__(parent)
        self.setWindowTitle("Dienstleistung hinzufügen/bearbeiten")
        self.setModal(True)
        layout = QVBoxLayout()

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Name der Dienstleistung")
        layout.addWidget(QLabel("Name:"))
        layout.addWidget(self.name_input)

        self.beschreibung_input = QTextEdit()
        layout.addWidget(QLabel("Beschreibung:"))
        layout.addWidget(self.beschreibung_input)

        self.preis_input = QLineEdit()
        self.preis_input.setPlaceholderText("Preis (z.B. 100.00)")
        layout.addWidget(QLabel("Preis:"))
        layout.addWidget(self.preis_input)

        self.einheit_input = QLineEdit()
        self.einheit_input.setPlaceholderText("Einheit (z.B. Stunde)")
        layout.addWidget(QLabel("Einheit:"))
        layout.addWidget(self.einheit_input)

        self.bemerkung_input = QTextEdit()
        layout.addWidget(QLabel("Bemerkung:"))
        layout.addWidget(self.bemerkung_input)

        self.waehrung_input = QComboBox()
        self.waehrung_input.addItems(["EUR", "USD", "CHF"])
        layout.addWidget(QLabel("Währung:"))
        layout.addWidget(self.waehrung_input)

        if dienstleistung:
            self.name_input.setText(dienstleistung.get("name", ""))
            self.beschreibung_input.setPlainText(dienstleistung.get("beschreibung", ""))
            self.preis_input.setText(str(dienstleistung.get("preis", "")))
            self.einheit_input.setText(dienstleistung.get("einheit", ""))
            self.bemerkung_input.setPlainText(dienstleistung.get("bemerkung", ""))
            waehrung_idx = self.waehrung_input.findText(dienstleistung.get("waehrung", "EUR"), Qt.MatchExactly)
            if waehrung_idx >= 0:
                self.waehrung_input.setCurrentIndex(waehrung_idx)

        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("OK")
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton("Abbrechen")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def get_daten(self):
        return {
            "name": self.name_input.text().strip(),
            "beschreibung": self.beschreibung_input.toPlainText().strip(),
            "preis": self.preis_input.text().strip(),
            "einheit": self.einheit_input.text().strip(),
            "bemerkung": self.bemerkung_input.toPlainText().strip(),
            "waehrung": self.waehrung_input.currentText()
        }