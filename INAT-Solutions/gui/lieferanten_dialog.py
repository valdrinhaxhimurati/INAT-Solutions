# -*- coding: utf-8 -*-
from .base_dialog import BaseDialog
from .dialog_styles import GROUPBOX_STYLE
from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QTextEdit, QMessageBox, QGroupBox, QFormLayout
)
from i18n import _


class LieferantenDialog(BaseDialog):
    def __init__(self, parent=None, lieferant=None):
        super().__init__(parent)
        self.setWindowTitle(_("Lieferant bearbeiten") if lieferant else _("Neuen Lieferant hinzufügen"))
        self.resize(520, 580)

        lieferant = lieferant or {}

        layout = self.content_layout
        layout.setSpacing(15)

        # === Stammdaten ===
        stamm_group = QGroupBox(_("Stammdaten"))
        stamm_group.setStyleSheet(GROUPBOX_STYLE)
        stamm_layout = QFormLayout(stamm_group)
        stamm_layout.setSpacing(10)

        self.input_name = QLineEdit(lieferant.get("name", ""))
        self.input_name.setPlaceholderText(_("Pflichtfeld"))
        stamm_layout.addRow(_("Name:"), self.input_name)

        self.input_adresse = QLineEdit(lieferant.get("adresse", ""))
        stamm_layout.addRow(_("Adresse:"), self.input_adresse)

        layout.addWidget(stamm_group)

        # === Kontakt ===
        kontakt_group = QGroupBox(_("Kontakt"))
        kontakt_group.setStyleSheet(GROUPBOX_STYLE)
        kontakt_layout = QFormLayout(kontakt_group)
        kontakt_layout.setSpacing(10)

        self.input_kontaktperson = QLineEdit(lieferant.get("kontaktperson", ""))
        kontakt_layout.addRow(_("Kontaktperson:"), self.input_kontaktperson)

        self.input_email = QLineEdit(lieferant.get("email", ""))
        self.input_email.setPlaceholderText(_("beispiel@email.ch"))
        kontakt_layout.addRow(_("E-Mail:"), self.input_email)

        self.input_telefon = QLineEdit(lieferant.get("telefon", ""))
        kontakt_layout.addRow(_("Telefon:"), self.input_telefon)

        self.input_portal_link = QLineEdit(lieferant.get("portal_link", ""))
        self.input_portal_link.setPlaceholderText(_("https://..."))
        kontakt_layout.addRow(_("Portal Link:"), self.input_portal_link)

        layout.addWidget(kontakt_group)

        # === Notizen ===
        notizen_group = QGroupBox(_("Notizen"))
        notizen_group.setStyleSheet(GROUPBOX_STYLE)
        notizen_layout = QVBoxLayout(notizen_group)

        self.input_notizen = QTextEdit(lieferant.get("notizen", ""))
        self.input_notizen.setPlaceholderText(_("Notizen zum Lieferanten..."))
        self.input_notizen.setFixedHeight(80)
        notizen_layout.addWidget(self.input_notizen)

        layout.addWidget(notizen_group)

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
            "name": self.input_name.text(),
            "adresse": self.input_adresse.text(),
            "kontaktperson": self.input_kontaktperson.text(),
            "email": self.input_email.text(),
            "telefon": self.input_telefon.text(),
            "portal_link": self.input_portal_link.text(),
            "notizen": self.input_notizen.toPlainText()
        }

