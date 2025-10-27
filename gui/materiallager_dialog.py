# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QSpinBox,
    QComboBox, QPushButton
)
from db_connection import get_db, dict_cursor_factory
from PyQt5.QtCore import Qt

class MateriallagerDialog(QDialog):
    def __init__(self, parent=None, material=None):
        super().__init__(parent)
        self.setWindowTitle("Material erfassen" if material is None else "Material bearbeiten")
        self.resize(480, 320)
        layout = QVBoxLayout()

        self.materialnummer_input = QLineEdit()
        self.bezeichnung_input = QLineEdit()
        self.menge_input = QSpinBox(); self.menge_input.setRange(0, 1_000_000)
        self.einheit_input = QComboBox(); self.einheit_input.addItems(["Stück","Meter","Kilogramm","Liter","Packung","Sonstiges"])
        self.lagerort_input = QLineEdit()
        self.lieferant_box = QComboBox()
        self.lieferant_box.addItem("Kein Lieferant", None)
        for ln, name in self._lade_lieferanten():
            self.lieferant_box.addItem(name, ln)
        self.bemerkung_input = QLineEdit()
        self.preis_input = QLineEdit()
        self.preis_input.setPlaceholderText("Preis")
        layout.addWidget(QLabel("Preis:"))
        layout.addWidget(self.preis_input)

        self.waehrung_input = QComboBox()
        self.waehrung_input.addItems(["EUR", "USD", "CHF"])
        layout.addWidget(QLabel("Währung:"))
        layout.addWidget(self.waehrung_input)

        layout.addWidget(QLabel("Materialnummer:"))
        layout.addWidget(self.materialnummer_input)
        layout.addWidget(QLabel("Bezeichnung:"))
        layout.addWidget(self.bezeichnung_input)
        layout.addWidget(QLabel("Menge:"))
        layout.addWidget(self.menge_input)
        layout.addWidget(QLabel("Einheit:"))
        layout.addWidget(self.einheit_input)
        layout.addWidget(QLabel("Lagerort:"))
        layout.addWidget(self.lagerort_input)
        layout.addWidget(QLabel("Lieferant (optional):"))
        layout.addWidget(self.lieferant_box)
        layout.addWidget(QLabel("Bemerkung:"))
        layout.addWidget(self.bemerkung_input)

        if material:
            self.materialnummer_input.setText(material.get("materialnummer",""))
            self.bezeichnung_input.setText(material.get("bezeichnung",""))
            try:
                self.menge_input.setValue(int(material.get("menge",0)))
            except Exception:
                self.menge_input.setValue(0)
            ein = material.get("einheit","")
            idx = self.einheit_input.findText(ein, Qt.MatchExactly)
            if idx >= 0:
                self.einheit_input.setCurrentIndex(idx)
            self.lagerort_input.setText(material.get("lagerort",""))
            lf = material.get("lieferantnr", None)
            if lf is not None:
                idx = self.lieferant_box.findData(lf)
                if idx >= 0:
                    self.lieferant_box.setCurrentIndex(idx)
            self.bemerkung_input.setText(material.get("bemerkung",""))
            self.preis_input.setText(str(material.get("preis", "")))
            waehrung_idx = self.waehrung_input.findText(material.get("waehrung", "EUR"), Qt.MatchExactly)
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

        self.setLayout(layout)

    def _lade_lieferanten(self):
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT id AS lieferantnr, name FROM public.lieferanten ORDER BY name")
            rows = cur.fetchall()
            conn.close()
            return rows
        except Exception:
            try:
                conn = get_db()
                cur = conn.cursor()
                cur.execute("SELECT id AS lieferantnr, name FROM lieferanten ORDER BY name")
                rows = cur.fetchall()
                conn.close()
                return rows
            except Exception as e:
                print("Fehler beim Laden der Lieferanten:", e)
                return []

    def get_daten(self):
        try:
            lf = self.lieferant_box.currentData()
        except Exception:
            lf = None
        try:
            lf_val = int(lf) if lf is not None and str(lf).strip() != "" else None
        except Exception:
            lf_val = None

        return {
            "materialnummer": self.materialnummer_input.text().strip(),
            "bezeichnung": self.bezeichnung_input.text().strip(),
            "menge": int(self.menge_input.value()),
            "einheit": self.einheit_input.currentText(),
            "lagerort": self.lagerort_input.text().strip(),
            "lieferantnr": lf_val,
            "bemerkung": self.bemerkung_input.text().strip(),
            "preis": self.preis_input.text().strip(),
            "waehrung": self.waehrung_input.currentText()
        }
