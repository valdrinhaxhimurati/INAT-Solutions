# -*- coding: utf-8 -*-
"""
Dialog zum Erfassen einer Zahlung für eine Rechnung.
Erstellt automatisch einen Buchhaltungseintrag und setzt den Rechnungsstatus.
"""
from .base_dialog import BaseDialog
from .dialog_styles import GROUPBOX_STYLE
from PyQt5.QtWidgets import (
    QLabel, QLineEdit, QTextEdit, QComboBox,
    QPushButton, QDateEdit, QMessageBox, QGroupBox, QFormLayout, QHBoxLayout, QVBoxLayout
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QFont
import datetime
from i18n import _
from gui.popup_calendar import PopupCalendarWidget
from db_connection import get_db, get_einstellungen


class ZahlungErfassenDialog(BaseDialog):
    """Dialog zur Erfassung einer Zahlung für eine Rechnung."""
    
    def __init__(self, rechnung_nr: str, kunde: str, betrag: float, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Zahlung erfassen"))
        self.resize(500, 450)
        
        self.rechnung_nr = rechnung_nr
        self.kunde = kunde
        self.rechnungsbetrag = betrag
        
        layout = self.content_layout
        layout.setSpacing(15)
        
        # === Rechnungsinfo (nicht editierbar) ===
        info_group = QGroupBox(_("Rechnungsinformationen"))
        info_group.setStyleSheet(GROUPBOX_STYLE)
        info_layout = QFormLayout(info_group)
        info_layout.setSpacing(8)
        
        lbl_rechnung = QLabel(f"{rechnung_nr}")
        lbl_rechnung.setStyleSheet("font-weight: bold;")
        info_layout.addRow(_("Rechnung:"), lbl_rechnung)
        
        lbl_kunde = QLabel(f"{kunde}")
        info_layout.addRow(_("Kunde:"), lbl_kunde)
        
        lbl_betrag = QLabel(f"CHF {betrag:,.2f}".replace(",", "'"))
        lbl_betrag.setStyleSheet("font-weight: bold; color: #2980b9;")
        info_layout.addRow(_("Rechnungsbetrag:"), lbl_betrag)
        
        layout.addWidget(info_group)
        
        # === Zahlungsdetails ===
        zahlung_group = QGroupBox(_("Zahlungsdetails"))
        zahlung_group.setStyleSheet(GROUPBOX_STYLE)
        zahlung_layout = QFormLayout(zahlung_group)
        zahlung_layout.setSpacing(10)
        
        # Zahlungsbetrag
        self.input_betrag = QLineEdit()
        self.input_betrag.setText(f"{betrag:.2f}")
        self.input_betrag.setPlaceholderText(_("Zahlungsbetrag"))
        zahlung_layout.addRow(_("Zahlungsbetrag (CHF):"), self.input_betrag)
        
        # Zahlungsdatum
        self.input_datum = QDateEdit()
        self.input_datum.setDisplayFormat("dd.MM.yyyy")
        self.input_datum.setCalendarPopup(True)
        self.input_datum.setDate(QDate.currentDate())
        try:
            cal = PopupCalendarWidget(self)
            cal.setVerticalHeaderFormat(cal.NoVerticalHeader)
            cal.setGridVisible(True)
            self.input_datum.setCalendarWidget(cal)
        except Exception:
            pass
        zahlung_layout.addRow(_("Zahlungsdatum:"), self.input_datum)
        
        # Kategorie (aus Buchhaltungs-Kategorien)
        self.dropdown_kategorie = QComboBox()
        kategorien = self._lade_kategorien()
        if kategorien:
            self.dropdown_kategorie.addItems(kategorien)
        zahlung_layout.addRow(_("Kategorie:"), self.dropdown_kategorie)
        
        layout.addWidget(zahlung_group)
        
        # === Beschreibung ===
        beschreibung_group = QGroupBox(_("Beschreibung"))
        beschreibung_group.setStyleSheet(GROUPBOX_STYLE)
        beschreibung_layout = QFormLayout(beschreibung_group)
        
        self.input_beschreibung = QTextEdit()
        self.input_beschreibung.setFixedHeight(60)
        # Vorausgefüllte Beschreibung
        self.input_beschreibung.setPlainText(f"Rechnung {rechnung_nr} - {kunde}")
        beschreibung_layout.addRow(self.input_beschreibung)
        
        # Hinweis
        hinweis = QLabel(_("Die Beschreibung kann angepasst werden."))
        hinweis.setStyleSheet("color: #666; font-size: 11px;")
        beschreibung_layout.addRow(hinweis)
        
        layout.addWidget(beschreibung_group)
        
        layout.addStretch()
        
        # === Buttons (zentriert) ===
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.btn_abbrechen = QPushButton(_("Abbrechen"))
        self.btn_abbrechen.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_abbrechen)
        
        self.btn_buchen = QPushButton(_("Zahlung buchen"))
        self.btn_buchen.clicked.connect(self._on_buchen_clicked)
        btn_layout.addWidget(self.btn_buchen)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
    
    def _lade_kategorien(self) -> list:
        """Lädt die Buchhaltungs-Kategorien aus den Einstellungen."""
        try:
            daten = get_einstellungen()
            return daten.get("buchhaltungs_kategorien", [])
        except Exception:
            return []
    
    def _on_buchen_clicked(self):
        """Validiert und akzeptiert den Dialog."""
        betrag_text = self.input_betrag.text().strip().replace(",", ".").replace("'", "")
        
        if not betrag_text:
            QMessageBox.warning(self, _("Fehler"), _("Bitte gib einen Zahlungsbetrag ein."))
            return
        
        try:
            betrag = float(betrag_text)
            if betrag <= 0:
                raise ValueError()
        except ValueError:
            QMessageBox.warning(self, _("Fehler"), _("Bitte gib einen gültigen Betrag ein."))
            return
        
        if not self.dropdown_kategorie.currentText():
            QMessageBox.warning(self, _("Fehler"), _("Bitte wähle eine Kategorie aus."))
            return
        
        self.accept()
    
    def get_data(self) -> dict:
        """Gibt die eingegebenen Zahlungsdaten zurück."""
        betrag_text = self.input_betrag.text().strip().replace(",", ".").replace("'", "")
        try:
            betrag = float(betrag_text)
        except ValueError:
            betrag = 0.0
        
        return {
            "rechnung_nr": self.rechnung_nr,
            "kunde": self.kunde,
            "betrag": betrag,
            "datum": self.input_datum.date().toString("yyyy-MM-dd"),
            "kategorie": self.dropdown_kategorie.currentText(),
            "beschreibung": self.input_beschreibung.toPlainText().strip(),
        }
