# -*- coding: utf-8 -*-
from .base_dialog import BaseDialog
from .dialog_styles import GROUPBOX_STYLE
from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QTextEdit, QMessageBox, QGroupBox, QFormLayout
)
from PyQt5.QtCore import Qt
from i18n import _


class ArtikellagerDialog(BaseDialog):
    def __init__(self, parent=None, artikel=None):
        super().__init__(parent)
        self.setWindowTitle(_("Artikel erfassen") if artikel is None else _("Artikel bearbeiten"))
        self.resize(500, 550)

        layout = self.content_layout
        layout.setSpacing(15)

        # === Artikeldaten ===
        artikel_group = QGroupBox(_("Artikeldaten"))
        artikel_group.setStyleSheet(GROUPBOX_STYLE)
        artikel_layout = QFormLayout(artikel_group)
        artikel_layout.setSpacing(10)

        self.artikelnummer_input = QLineEdit()
        artikel_layout.addRow(_("Artikelnummer:"), self.artikelnummer_input)

        self.bezeichnung_input = QLineEdit()
        self.bezeichnung_input.setPlaceholderText(_("Pflichtfeld"))
        artikel_layout.addRow(_("Bezeichnung:"), self.bezeichnung_input)

        layout.addWidget(artikel_group)

        # === Bestand & Lager ===
        bestand_group = QGroupBox(_("Bestand & Lager"))
        bestand_group.setStyleSheet(GROUPBOX_STYLE)
        bestand_layout = QFormLayout(bestand_group)
        bestand_layout.setSpacing(10)

        self.bestand_input = QLineEdit()
        self.bestand_input.setPlaceholderText(_("0"))
        bestand_layout.addRow(_("Bestand:"), self.bestand_input)

        self.lagerort_input = QLineEdit()
        bestand_layout.addRow(_("Lagerort:"), self.lagerort_input)

        layout.addWidget(bestand_group)

        # === Preis ===
        preis_group = QGroupBox(_("Preis"))
        preis_group.setStyleSheet(GROUPBOX_STYLE)
        preis_layout = QFormLayout(preis_group)
        preis_layout.setSpacing(10)

        self.preis_input = QLineEdit()
        self.preis_input.setPlaceholderText(_("Pflichtfeld"))
        preis_layout.addRow(_("Preis:"), self.preis_input)

        self.waehrung_input = QComboBox()
        self.waehrung_input.addItems(["CHF", "EUR", "USD"])
        preis_layout.addRow(_("Währung:"), self.waehrung_input)

        layout.addWidget(preis_group)

        # === Bemerkung ===
        bemerkung_group = QGroupBox(_("Bemerkung"))
        bemerkung_group.setStyleSheet(GROUPBOX_STYLE)
        bemerkung_layout = QVBoxLayout(bemerkung_group)

        self.bemerkung_input = QTextEdit()
        self.bemerkung_input.setFixedHeight(60)
        bemerkung_layout.addWidget(self.bemerkung_input)

        layout.addWidget(bemerkung_group)

        # Daten laden wenn vorhanden
        if artikel:
            self.artikelnummer_input.setText(artikel.get("artikelnummer", ""))
            self.bezeichnung_input.setText(artikel.get("bezeichnung", ""))
            self.bestand_input.setText(str(artikel.get("bestand", "")))
            self.lagerort_input.setText(artikel.get("lagerort", ""))
            self.preis_input.setText(str(artikel.get("preis", "")))
            waehrung_idx = self.waehrung_input.findText(artikel.get("waehrung", "CHF"), Qt.MatchExactly)
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

    def get_daten(self):
        return {
            "artikelnummer": self.artikelnummer_input.text().strip(),
            "bezeichnung": self.bezeichnung_input.text().strip(),
            "bestand": int(self.bestand_input.text().strip()) if str(self.bestand_input.text()).strip() != "" else 0,
            "lagerort": self.lagerort_input.text().strip(),
            "preis": float(self.preis_input.text().strip().replace(",", ".").replace("'", "")),
            "waehrung": self.waehrung_input.currentText()
        }