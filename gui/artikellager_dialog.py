# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QTextEdit, QPushButton, QHBoxLayout, QComboBox
from PyQt5.QtCore import Qt
class ArtikellagerDialog(QDialog):
    def __init__(self, parent=None, artikel=None):
        super().__init__(parent)
        self.setWindowTitle("Artikel hinzufügen/bearbeiten")
        layout = QVBoxLayout()

        self.artikelnummer_input = QLineEdit()
        self.artikelnummer_input.setPlaceholderText("Artikelnummer")
        layout.addWidget(QLabel("Artikelnummer:"))
        layout.addWidget(self.artikelnummer_input)

        self.bezeichnung_input = QLineEdit()
        self.bezeichnung_input.setPlaceholderText("Bezeichnung")
        layout.addWidget(QLabel("Bezeichnung:"))
        layout.addWidget(self.bezeichnung_input)

        self.bestand_input = QLineEdit()
        self.bestand_input.setPlaceholderText("Bestand")
        layout.addWidget(QLabel("Bestand:"))
        layout.addWidget(self.bestand_input)

        self.lagerort_input = QLineEdit()
        self.lagerort_input.setPlaceholderText("Lagerort")
        layout.addWidget(QLabel("Lagerort:"))
        layout.addWidget(self.lagerort_input)

        self.preis_input = QLineEdit()
        self.preis_input.setPlaceholderText("Preis")
        layout.addWidget(QLabel("Preis:"))
        layout.addWidget(self.preis_input)

        self.waehrung_input = QComboBox()
        self.waehrung_input.addItems(["EUR", "USD", "CHF"])
        layout.addWidget(QLabel("Währung:"))
        layout.addWidget(self.waehrung_input)

        if artikel:
            self.artikelnummer_input.setText(artikel.get("artikelnummer", ""))
            self.bezeichnung_input.setText(artikel.get("bezeichnung", ""))
            self.bestand_input.setText(str(artikel.get("bestand", "")))
            self.lagerort_input.setText(artikel.get("lagerort", ""))
            self.preis_input.setText(str(artikel.get("preis", "")))
            waehrung_idx = self.waehrung_input.findText(artikel.get("waehrung", "EUR"), Qt.MatchExactly)
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
            "artikelnummer": self.artikelnummer_input.text().strip(),
            "bezeichnung": self.bezeichnung_input.text().strip(),
            "bestand": self.bestand_input.text().strip(),
            "lagerort": self.lagerort_input.text().strip(),
            "preis": self.preis_input.text().strip(),
            "waehrung": self.waehrung_input.currentText()
        }