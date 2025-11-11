# -*- coding: utf-8 -*-
# NEU: BaseDialog importieren
from .base_dialog import BaseDialog
from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QCheckBox, QTextEdit
)
from db_connection import get_db, dict_cursor_factory
from PyQt5.QtCore import Qt
from gui.widgets import NumericLineEdit

# ÄNDERUNG: Von BaseDialog erben
class ArtikellagerDialog(BaseDialog):
    def __init__(self, parent=None, artikel=None):
        # ÄNDERUNG: super() für BaseDialog aufrufen
        super().__init__(parent)
        self.setWindowTitle("Artikel erfassen" if artikel is None else "Artikel bearbeiten")
        self.resize(480, 600)

        # WICHTIG: Das Layout vom BaseDialog verwenden
        layout = self.content_layout

        self.artikelnummer_input = QLineEdit()
        self.bezeichnung_input = QLineEdit()
        self.bestand_input = QLineEdit()
        self.lagerort_input = QLineEdit()
        self.preis_input = QLineEdit()
        self.waehrung_input = QComboBox()
        self.waehrung_input.addItems(["EUR", "USD", "CHF"])
        self.bemerkung_input = QTextEdit()

        layout.addWidget(QLabel("Artikelnummer:"))
        layout.addWidget(self.artikelnummer_input)
        layout.addWidget(QLabel("Bezeichnung:"))
        layout.addWidget(self.bezeichnung_input)
        layout.addWidget(QLabel("Bestand:"))
        layout.addWidget(self.bestand_input)
        layout.addWidget(QLabel("Lagerort:"))
        layout.addWidget(self.lagerort_input)
        layout.addWidget(QLabel("Preis:"))
        layout.addWidget(self.preis_input)
        layout.addWidget(QLabel("Währung:"))
        layout.addWidget(self.waehrung_input)
        layout.addWidget(QLabel("Bemerkung:"))
        layout.addWidget(self.bemerkung_input)

        if artikel:
            self.artikelnummer_input.setText(artikel.get("artikelnummer",""))
            self.bezeichnung_input.setText(artikel.get("bezeichnung",""))
            self.bestand_input.setText(str(artikel.get("bestand","")))
            self.lagerort_input.setText(artikel.get("lagerort",""))
            self.preis_input.setText(str(artikel.get("preis","")))
            waehrung_idx = self.waehrung_input.findText(artikel.get("waehrung", "EUR"), Qt.MatchExactly)
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

        # ÄNDERUNG: self.setLayout(layout) wird nicht mehr benötigt
        # self.setLayout(layout)

    def _lade_lieferanten(self):
        # DIESE METHODE BLEIBT UNVERÄNDERT
        try:
            with get_db().cursor(cursor_factory=dict_cursor_factory) as cursor:
                cursor.execute("SELECT id, name FROM lieferanten ORDER BY name")
                return cursor.fetchall()
        except Exception as e:
                print("Fehler beim Laden der Lieferanten:", e)
                return []

    def get_daten(self):
        # DIESE METHODE BLEIBT UNVERÄNDERT
        return {
            "artikelnummer": self.artikelnummer_input.text().strip(),
            "bezeichnung": self.bezeichnung_input.text().strip(),
            "bestand": self.bestand_input.text().strip(),
            "lagerort": self.lagerort_input.text().strip(),
            "preis": self.preis_input.text().strip(),
            "waehrung": self.waehrung_input.currentText()
        }