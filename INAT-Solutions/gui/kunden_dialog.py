# -*- coding: utf-8 -*-
from .base_dialog import BaseDialog
from .dialog_styles import GROUPBOX_STYLE
from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QMessageBox, QGroupBox, QFormLayout
)
from i18n import _


class KundenDialog(BaseDialog):
    def __init__(self, parent=None, kunde=None):
        super().__init__(parent)
        self.setWindowTitle(_("Kunde bearbeiten") if kunde else _("Neuen Kunden hinzufügen"))
        self.resize(500, 500)

        kunde = kunde or {}

        layout = self.content_layout
        layout.setSpacing(15)

        # === Persönliche Daten ===
        personal_group = QGroupBox(_("Persönliche Daten"))
        personal_group.setStyleSheet(GROUPBOX_STYLE)
        personal_layout = QFormLayout(personal_group)
        personal_layout.setSpacing(10)

        self.input_anrede = QLineEdit(kunde.get("anrede", ""))
        self.input_anrede.setPlaceholderText(_("Herr / Frau"))
        personal_layout.addRow(_("Anrede:"), self.input_anrede)

        self.input_name = QLineEdit(kunde.get("name", ""))
        self.input_name.setPlaceholderText(_("Pflichtfeld"))
        personal_layout.addRow(_("Name:"), self.input_name)

        self.input_firma = QLineEdit(kunde.get("firma", ""))
        personal_layout.addRow(_("Firma:"), self.input_firma)

        layout.addWidget(personal_group)

        # === Adresse ===
        address_group = QGroupBox(_("Adresse"))
        address_group.setStyleSheet(GROUPBOX_STYLE)
        address_layout = QFormLayout(address_group)
        address_layout.setSpacing(10)

        self.input_strasse = QLineEdit(kunde.get("strasse", ""))
        address_layout.addRow(_("Strasse:"), self.input_strasse)

        self.input_plz = QLineEdit(kunde.get("plz", ""))
        address_layout.addRow(_("PLZ:"), self.input_plz)

        self.input_stadt = QLineEdit(kunde.get("stadt", ""))
        address_layout.addRow(_("Stadt:"), self.input_stadt)

        layout.addWidget(address_group)

        # === Kontakt ===
        contact_group = QGroupBox(_("Kontakt"))
        contact_group.setStyleSheet(GROUPBOX_STYLE)
        contact_layout = QFormLayout(contact_group)
        contact_layout.setSpacing(10)

        self.input_email = QLineEdit(kunde.get("email", ""))
        self.input_email.setPlaceholderText(_("beispiel@email.ch"))
        contact_layout.addRow(_("E-Mail:"), self.input_email)

        self.input_bemerkung = QLineEdit(kunde.get("bemerkung", ""))
        contact_layout.addRow(_("Bemerkung:"), self.input_bemerkung)

        layout.addWidget(contact_group)

        layout.addStretch()

        # === Buttons (zentriert) ===
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_abbrechen = QPushButton(_("Abbrechen"))
        btn_abbrechen.clicked.connect(self.reject)
        btn_layout.addWidget(btn_abbrechen)

        self.btn_ok = QPushButton(_("Speichern"))
        self.btn_ok.clicked.connect(self._on_ok_clicked)
        btn_layout.addWidget(self.btn_ok)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _on_ok_clicked(self):
        """Prüft Pflichtfelder und zeigt Fehlermeldung wenn etwas fehlt."""
        fehler = []
        if not self.input_name.text().strip():
            fehler.append(_("Name"))
        
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
            "anrede": self.input_anrede.text(),
            "name": self.input_name.text(),
            "firma": self.input_firma.text(),
            "plz": self.input_plz.text(),
            "strasse": self.input_strasse.text(),
            "stadt": self.input_stadt.text(),
            "email": self.input_email.text(),
            "bemerkung": self.input_bemerkung.text(),
        }



