# -*- coding: utf-8 -*-
from .base_dialog import BaseDialog
from .dialog_styles import GROUPBOX_STYLE
from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QMessageBox, QGroupBox, QFormLayout
)
from PyQt5.QtCore import Qt
from gui.widgets import NumericLineEdit
from i18n import _


class DienstleistungenDialog(BaseDialog):
    def __init__(self, parent=None, dienstleistung=None):
        super().__init__(parent)
        self.setWindowTitle(_("Dienstleistung erfassen") if dienstleistung is None else _("Dienstleistung bearbeiten"))
        self.resize(500, 450)

        layout = self.content_layout
        layout.setSpacing(15)

        # === Bezeichnung ===
        bezeichnung_group = QGroupBox(_("Bezeichnung"))
        bezeichnung_group.setStyleSheet(GROUPBOX_STYLE)
        bezeichnung_layout = QFormLayout(bezeichnung_group)
        bezeichnung_layout.setSpacing(10)

        self.bezeichnung_input = QLineEdit()
        self.bezeichnung_input.setPlaceholderText(_("Pflichtfeld"))
        bezeichnung_layout.addRow(_("Bezeichnung:"), self.bezeichnung_input)

        self.beschreibung_input = QLineEdit()
        bezeichnung_layout.addRow(_("Beschreibung:"), self.beschreibung_input)

        layout.addWidget(bezeichnung_group)

        # === Preis ===
        preis_group = QGroupBox(_("Preis"))
        preis_group.setStyleSheet(GROUPBOX_STYLE)
        preis_layout = QFormLayout(preis_group)
        preis_layout.setSpacing(10)

        self.preis_input = NumericLineEdit()
        self.preis_input.setPlaceholderText(_("Pflichtfeld"))
        preis_layout.addRow(_("Preis:"), self.preis_input)

        self.waehrung_input = QComboBox()
        self.waehrung_input.addItems(["CHF", "EUR", "USD"])
        preis_layout.addRow(_("Währung:"), self.waehrung_input)

        self.einheit_input = QLineEdit()
        self.einheit_input.setPlaceholderText(_("z.B. Stunde, Stück"))
        preis_layout.addRow(_("Einheit:"), self.einheit_input)

        layout.addWidget(preis_group)

        # === Zusätzliche Informationen ===
        zusatz_group = QGroupBox(_("Zusätzliche Informationen"))
        zusatz_group.setStyleSheet(GROUPBOX_STYLE)
        zusatz_layout = QFormLayout(zusatz_group)
        zusatz_layout.setSpacing(10)

        self.bemerkung_input = QLineEdit()
        zusatz_layout.addRow(_("Bemerkung:"), self.bemerkung_input)

        layout.addWidget(zusatz_group)

        # Daten laden wenn vorhanden
        if dienstleistung:
            self.bezeichnung_input.setText(dienstleistung.get("name", ""))
            self.beschreibung_input.setText(dienstleistung.get("beschreibung", ""))
            self.preis_input.setValue(float(dienstleistung.get("preis", 0)))
            self.einheit_input.setText(dienstleistung.get("einheit", ""))
            self.bemerkung_input.setText(dienstleistung.get("bemerkung", ""))
            waehrung_idx = self.waehrung_input.findText(dienstleistung.get("waehrung", "CHF"), Qt.MatchExactly)
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
            "name": self.bezeichnung_input.text().strip(),
            "beschreibung": self.beschreibung_input.text().strip(),
            "preis": float(self.preis_input.text().strip().replace(",", ".")) if self.preis_input.text().strip() != "" else 0.0,
            "einheit": self.einheit_input.text().strip(),
            "bemerkung": self.bemerkung_input.text().strip(),
            "waehrung": self.waehrung_input.currentText()
        }