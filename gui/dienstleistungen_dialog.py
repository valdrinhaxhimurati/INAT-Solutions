# -*- coding: utf-8 -*-
# NEU: BaseDialog importieren
from .base_dialog import BaseDialog
from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QPushButton
)
from PyQt5.QtCore import Qt
from gui.widgets import NumericLineEdit

# ÄNDERUNG: Von BaseDialog erben
class DienstleistungenDialog(BaseDialog):
    def __init__(self, parent=None, dienstleistung=None):
        # ÄNDERUNG: super() für BaseDialog aufrufen
        super().__init__(parent)
        self.setWindowTitle("Dienstleistung erfassen" if dienstleistung is None else "Dienstleistung bearbeiten")
        self.resize(480, 400)

        # WICHTIG: Das Layout vom BaseDialog verwenden
        layout = self.content_layout

        self.bezeichnung_input = QLineEdit()
        self.beschreibung_input = QLineEdit()
        layout.addWidget(QLabel("Bezeichnung:"))
        layout.addWidget(self.bezeichnung_input)
        layout.addWidget(QLabel("Beschreibung:"))
        layout.addWidget(self.beschreibung_input)

        self.preis_input = NumericLineEdit()
        layout.addWidget(QLabel("Preis:"))
        layout.addWidget(self.preis_input)

        self.einheit_input = QLineEdit()
        self.einheit_input.setPlaceholderText("Einheit (z.B. Stunde)")
        layout.addWidget(QLabel("Einheit:"))
        layout.addWidget(self.einheit_input)

        self.bemerkung_input = QLineEdit()
        layout.addWidget(QLabel("Bemerkung:"))
        layout.addWidget(self.bemerkung_input)

        self.waehrung_input = QComboBox()
        self.waehrung_input.addItems(["EUR", "USD", "CHF"])
        layout.addWidget(QLabel("Währung:"))
        layout.addWidget(self.waehrung_input)

        if dienstleistung:
            self.bezeichnung_input.setText(dienstleistung.get("name", ""))
            self.beschreibung_input.setText(dienstleistung.get("beschreibung", ""))
            self.preis_input.setValue(float(dienstleistung.get("preis", 0)))
            self.einheit_input.setText(dienstleistung.get("einheit", ""))
            self.bemerkung_input.setText(dienstleistung.get("bemerkung", ""))
            waehrung_idx = self.waehrung_input.findText(dienstleistung.get("waehrung", "EUR"), Qt.MatchExactly)
            if waehrung_idx >= 0:
                self.waehrung_input.setCurrentIndex(waehrung_idx)

        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("OK")
        btn_cancel = QPushButton("Abbrechen")
        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

    def get_daten(self):
        return {
            "name": self.bezeichnung_input.text().strip(),
            "beschreibung": self.beschreibung_input.text().strip(),
            "preis": self.preis_input.text().strip(),
            "waehrung": self.waehrung_input.currentText()
        }