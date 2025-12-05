# -*- coding: utf-8 -*-
from .base_dialog import BaseDialog
from .dialog_styles import GROUPBOX_STYLE
from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QMessageBox, QGroupBox, QFormLayout
)
from db_connection import get_db
from PyQt5.QtCore import Qt
from gui.widgets import NumericLineEdit
from i18n import _


class MateriallagerDialog(BaseDialog):
    def __init__(self, parent=None, material=None):
        super().__init__(parent)
        self.setWindowTitle(_("Material erfassen") if material is None else _("Material bearbeiten"))
        self.resize(520, 600)
        
        layout = self.content_layout
        layout.setSpacing(15)

        # === Materialdaten ===
        material_group = QGroupBox(_("Materialdaten"))
        material_group.setStyleSheet(GROUPBOX_STYLE)
        material_layout = QFormLayout(material_group)
        material_layout.setSpacing(10)

        self.materialnummer_input = QLineEdit()
        material_layout.addRow(_("Materialnummer:"), self.materialnummer_input)

        self.bezeichnung_input = QLineEdit()
        self.bezeichnung_input.setPlaceholderText(_("Pflichtfeld"))
        material_layout.addRow(_("Bezeichnung:"), self.bezeichnung_input)

        layout.addWidget(material_group)

        # === Bestand & Lager ===
        bestand_group = QGroupBox(_("Bestand & Lager"))
        bestand_group.setStyleSheet(GROUPBOX_STYLE)
        bestand_layout = QFormLayout(bestand_group)
        bestand_layout.setSpacing(10)

        self.menge_input = NumericLineEdit(decimals=0)
        self.menge_input.setRange(0, 1_000_000)
        bestand_layout.addRow(_("Menge:"), self.menge_input)

        self.einheit_input = QComboBox()
        self.einheit_input.addItems(["Stück", "Meter", "Kilogramm", "Liter", "Packung", "Sonstiges"])
        bestand_layout.addRow(_("Einheit:"), self.einheit_input)

        self.lagerort_input = QLineEdit()
        bestand_layout.addRow(_("Lagerort:"), self.lagerort_input)

        layout.addWidget(bestand_group)

        # === Preis & Lieferant ===
        preis_group = QGroupBox(_("Preis & Lieferant"))
        preis_group.setStyleSheet(GROUPBOX_STYLE)
        preis_layout = QFormLayout(preis_group)
        preis_layout.setSpacing(10)

        self.preis_input = QLineEdit()
        self.preis_input.setPlaceholderText(_("Pflichtfeld"))
        preis_layout.addRow(_("Preis:"), self.preis_input)

        self.waehrung_input = QComboBox()
        self.waehrung_input.addItems(["CHF", "EUR", "USD"])
        preis_layout.addRow(_("Währung:"), self.waehrung_input)

        self.lieferant_box = QComboBox()
        self.lieferant_box.addItem(_("Kein Lieferant"), None)
        for ln, name in self._lade_lieferanten():
            self.lieferant_box.addItem(name, ln)
        preis_layout.addRow(_("Lieferant:"), self.lieferant_box)

        layout.addWidget(preis_group)

        # === Bemerkung ===
        bemerkung_group = QGroupBox(_("Bemerkung"))
        bemerkung_group.setStyleSheet(GROUPBOX_STYLE)
        bemerkung_layout = QFormLayout(bemerkung_group)

        self.bemerkung_input = QLineEdit()
        bemerkung_layout.addRow(_("Bemerkung:"), self.bemerkung_input)

        layout.addWidget(bemerkung_group)

        # Daten laden wenn vorhanden
        if material:
            self.materialnummer_input.setText(material.get("materialnummer", ""))
            self.bezeichnung_input.setText(material.get("bezeichnung", ""))
            try:
                self.menge_input.setValue(int(material.get("menge", 0)))
            except Exception:
                self.menge_input.setValue(0)
            ein = material.get("einheit", "")
            idx = self.einheit_input.findText(ein, Qt.MatchExactly)
            if idx >= 0:
                self.einheit_input.setCurrentIndex(idx)
            self.lagerort_input.setText(material.get("lagerort", ""))
            lf = material.get("lieferantnr", None)
            if lf is not None:
                idx = self.lieferant_box.findData(lf)
                if idx >= 0:
                    self.lieferant_box.setCurrentIndex(idx)
            self.bemerkung_input.setText(material.get("bemerkung", ""))
            self.preis_input.setText(str(material.get("preis", "")))
            waehrung_idx = self.waehrung_input.findText(material.get("waehrung", "CHF"), Qt.MatchExactly)
            if waehrung_idx >= 0:
                self.waehrung_input.setCurrentIndex(waehrung_idx)

        layout.addStretch()

        # === Buttons (zentriert) ===
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_cancel = QPushButton(_("Abbrechen"))
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        self.btn_ok = QPushButton(_("Speichern"))
        self.btn_ok.clicked.connect(self._on_ok_clicked)
        btn_layout.addWidget(self.btn_ok)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _on_ok_clicked(self):
        """Prüft Pflichtfelder und zeigt Fehlermeldung wenn etwas fehlt."""
        fehler = []
        if not self.bezeichnung_input.text().strip():
            fehler.append(_("Bezeichnung"))
        
        preis_text = self.preis_input.text().strip()
        if not preis_text:
            fehler.append(_("Preis"))
        else:
            try:
                float(preis_text.replace(',', '.').replace("'", ""))
            except Exception:
                fehler.append(_("Preis (ungültiger Wert)"))
        
        if fehler:
            QMessageBox.warning(
                self,
                _("Pflichtfelder fehlen"),
                _("Bitte fülle folgende Pflichtfelder aus:") + "\n\n• " + "\n• ".join(fehler)
            )
            return
        
        self.accept()

    def _lade_lieferanten(self):
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT lieferantnr, name FROM lieferanten ORDER BY name")
            rows = [(row[0], row[1]) for row in cur.fetchall()]
            conn.close()
            return rows
        except Exception as e:
            print(_("Fehler beim Laden der Lieferanten:"), e)
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
            "preis": float(self.preis_input.text().strip().replace(",", ".").replace("'", "")),
            "waehrung": self.waehrung_input.currentText()
        }