from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QPushButton, QDateEdit
)
from db_connection import get_db, dict_cursor
from PyQt5.QtCore import Qt, QDate
import sqlite3

class ReifenlagerDialog(QDialog):
    def __init__(self, parent=None, reifen=None):
        super().__init__(parent)
        self.setWindowTitle("Reifen erfassen" if reifen is None else "Reifen bearbeiten")
        self.resize(500, 400)
        layout = QVBoxLayout()

        # Kundenliste als ComboBox
        layout.addWidget(QLabel("Kunde:"))
        self.kunde_box = QComboBox()
        self.kunden = self.lade_kundenliste()
        for kundennr, anzeige in self.kunden:
            self.kunde_box.addItem(anzeige, kundennr)
        layout.addWidget(self.kunde_box)

        # Restliche Felder
        self.fahrzeug_input = QLineEdit()
        self.dimension_input = QLineEdit()

        self.typ_input = QComboBox()
        self.typ_input.addItems(["Sommer", "Winter", "Ganzjahr"])

        self.dot_input = QLineEdit()
        self.lagerort_input = QLineEdit()

        self.eingelagert_am_input = QDateEdit()
        self.eingelagert_am_input.setCalendarPopup(True)
        self.eingelagert_am_input.setDisplayFormat("yyyy-MM-dd")
        self.eingelagert_am_input.setDate(QDate.currentDate())

        self.ausgelagert_am_input = QDateEdit()
        self.ausgelagert_am_input.setCalendarPopup(True)
        self.ausgelagert_am_input.setDisplayFormat("yyyy-MM-dd")
        # Standard: leer lassen (kein Datum)
        self.ausgelagert_am_input.setDate(QDate(2000, 1, 1))  # Optional: Dummy für "kein Auslagerungsdatum"

        self.bemerkung_input = QLineEdit()

        layout.addWidget(QLabel("Fahrzeug:"))
        layout.addWidget(self.fahrzeug_input)
        layout.addWidget(QLabel("Dimension (z.B. 205/55 R16):"))
        layout.addWidget(self.dimension_input)
        layout.addWidget(QLabel("Typ (Sommer/Winter/Ganzjahr):"))
        layout.addWidget(self.typ_input)
        layout.addWidget(QLabel("DOT:"))
        layout.addWidget(self.dot_input)
        layout.addWidget(QLabel("Lagerort:"))
        layout.addWidget(self.lagerort_input)
        layout.addWidget(QLabel("Eingelagert am:"))
        layout.addWidget(self.eingelagert_am_input)
        layout.addWidget(QLabel("Ausgelagert am:"))
        layout.addWidget(self.ausgelagert_am_input)
        layout.addWidget(QLabel("Bemerkung:"))
        layout.addWidget(self.bemerkung_input)

        if reifen:
            idx = self.kunde_box.findText(reifen.get("kunde_anzeige", ""), Qt.MatchContains)
            if idx >= 0:
                self.kunde_box.setCurrentIndex(idx)
            self.fahrzeug_input.setText(reifen.get("fahrzeug", ""))
            self.dimension_input.setText(reifen.get("dimension", ""))
            typ_idx = self.typ_input.findText(reifen.get("typ", ""), Qt.MatchExactly)
            if typ_idx >= 0:
                self.typ_input.setCurrentIndex(typ_idx)
            self.dot_input.setText(reifen.get("dot", ""))
            self.lagerort_input.setText(reifen.get("lagerort", ""))
            # Datum für eingelagert_am
            eingelagert = reifen.get("eingelagert_am", "")
            if eingelagert:
                try:
                    self.eingelagert_am_input.setDate(QDate.fromString(eingelagert, "yyyy-MM-dd"))
                except Exception:
                    pass
            # Datum für ausgelagert_am
            ausgelagert = reifen.get("ausgelagert_am", "")
            if ausgelagert:
                try:
                    self.ausgelagert_am_input.setDate(QDate.fromString(ausgelagert, "yyyy-MM-dd"))
                except Exception:
                    pass
            self.bemerkung_input.setText(reifen.get("bemerkung", ""))

        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("OK")
        btn_cancel = QPushButton("Abbrechen")
        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def lade_kundenliste(self):
        conn = get_db()
        cursor = conn.cursor(cursor_factory=dict_cursor(conn))
        try:
            cursor.execute("SELECT kundennr, anrede, name, firma, plz, stadt FROM kunden")
            kunden = cursor.fetchall()
        except Exception:
            kunden = []
        conn.close()
        return [
            (k[0], f"{k[1]} {k[2]} ({k[3]}) - {k[4]} {k[5]}") for k in kunden
        ]

    def get_daten(self):
        return {
            "kundennr": int(self.kunde_box.currentData()),
            "kunde_anzeige": self.kunde_box.currentText(),
            "fahrzeug": self.fahrzeug_input.text().strip(),
            "dimension": self.dimension_input.text().strip(),
            "typ": self.typ_input.currentText(),
            "dot": self.dot_input.text().strip(),
            "lagerort": self.lagerort_input.text().strip(),
            "eingelagert_am": self.eingelagert_am_input.date().toString("yyyy-MM-dd"),
            "ausgelagert_am": self.ausgelagert_am_input.date().toString("yyyy-MM-dd"),
            "bemerkung": self.bemerkung_input.text().strip()
        }
