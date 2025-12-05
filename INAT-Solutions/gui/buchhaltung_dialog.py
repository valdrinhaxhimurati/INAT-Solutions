# -*- coding: utf-8 -*-
from .base_dialog import BaseDialog
from .dialog_styles import GROUPBOX_STYLE
from PyQt5.QtWidgets import (
    QLabel, QLineEdit, QTextEdit, QComboBox,
    QPushButton, QDateEdit, QMessageBox, QGroupBox, QFormLayout, QHBoxLayout
)
from PyQt5.QtCore import Qt, QDate
import datetime
from i18n import _
from gui.popup_calendar import PopupCalendarWidget


def _to_qdate_dateonly(val):
    """Konvertiert val zu QDate (Datum-only)."""
    if val is None:
        return QDate()
    if isinstance(val, QDate):
        return QDate(val.year(), val.month(), val.day())
    if isinstance(val, datetime.datetime):
        d = val.date()
        return QDate(d.year, d.month, d.day)
    if isinstance(val, datetime.date):
        return QDate(val.year, val.month, val.day)
    s = str(val).split(" ")[0]
    q = QDate.fromString(s, "yyyy-MM-dd")
    if q.isValid():
        return q
    return QDate.fromString(s, "dd.MM.yyyy")


def _to_date_str(val):
    """Gibt ISO-Datum 'YYYY-MM-DD' zurück (kein Zeitanteil)."""
    if val is None or val == "":
        return ""
    if isinstance(val, QDate):
        return val.toString("yyyy-MM-dd")
    if isinstance(val, datetime.datetime):
        return val.date().isoformat()
    if isinstance(val, datetime.date):
        return val.isoformat()
    s = str(val).split(" ")[0]
    try:
        datetime.date.fromisoformat(s)
        return s
    except Exception:
        try:
            d = datetime.datetime.strptime(s, "%d.%m.%Y").date()
            return d.isoformat()
        except Exception:
            return ""


def _to_qdate(val):
    """Konvertiert val sicher zu QDate."""
    if val is None:
        return QDate()
    if isinstance(val, QDate):
        return val
    if isinstance(val, datetime.datetime) or isinstance(val, datetime.date):
        d = val.date() if isinstance(val, datetime.datetime) else val
        return QDate(d.year, d.month, d.day)
    try:
        s = str(val)
        qd = QDate.fromString(s, "yyyy-MM-dd")
        if qd.isValid():
            return qd
        qd = QDate.fromString(s, "dd.MM.yyyy")
        return qd
    except Exception:
        return QDate()


class BuchhaltungDialog(BaseDialog):
    def __init__(self, eintrag=None, kategorien=None):
        super().__init__()
        self.setWindowTitle(_("Buchhaltungseintrag"))
        self.resize(550, 500)

        layout = self.content_layout
        layout.setSpacing(15)

        # === Grunddaten ===
        grund_group = QGroupBox(_("Grunddaten"))
        grund_group.setStyleSheet(GROUPBOX_STYLE)
        grund_layout = QFormLayout(grund_group)
        grund_layout.setSpacing(10)

        self.input_nr = QLineEdit()
        grund_layout.addRow(_("Nr:"), self.input_nr)

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
        grund_layout.addRow(_("Datum:"), self.input_datum)

        layout.addWidget(grund_group)

        # === Buchung ===
        buchung_group = QGroupBox(_("Buchung"))
        buchung_group.setStyleSheet(GROUPBOX_STYLE)
        buchung_layout = QFormLayout(buchung_group)
        buchung_layout.setSpacing(10)

        self.dropdown_typ = QComboBox()
        self.dropdown_typ.addItems([_("Einnahme"), _("Ausgabe")])
        buchung_layout.addRow(_("Typ:"), self.dropdown_typ)

        self.dropdown_kategorie = QComboBox()
        if kategorien:
            self.dropdown_kategorie.addItems(kategorien)
        buchung_layout.addRow(_("Kategorie:"), self.dropdown_kategorie)

        self.input_betrag = QLineEdit()
        self.input_betrag.setPlaceholderText(_("Pflichtfeld"))
        buchung_layout.addRow(_("Betrag (CHF):"), self.input_betrag)

        layout.addWidget(buchung_group)

        # === Beschreibung ===
        beschreibung_group = QGroupBox(_("Beschreibung"))
        beschreibung_group.setStyleSheet(GROUPBOX_STYLE)
        beschreibung_layout = QFormLayout(beschreibung_group)

        self.input_beschreibung = QTextEdit()
        self.input_beschreibung.setFixedHeight(80)
        beschreibung_layout.addRow(self.input_beschreibung)

        layout.addWidget(beschreibung_group)

        # Daten laden wenn vorhanden
        if isinstance(eintrag, dict):
            self.input_nr.setText(str(eintrag.get("id", "")))
            datum_str = eintrag.get("datum", "")
            qdate = _to_qdate(datum_str)
            if qdate.isValid():
                self.input_datum.setDate(qdate)
            self.dropdown_typ.setCurrentText(eintrag.get("typ", "Einnahme"))
            self.dropdown_kategorie.setCurrentText(eintrag.get("kategorie", ""))
            self.input_betrag.setText(str(eintrag.get("betrag", "")))
            self.input_beschreibung.setPlainText(eintrag.get("beschreibung", ""))

        layout.addStretch()

        # === Buttons (zentriert) ===
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_abbrechen = QPushButton(_("Abbrechen"))
        self.btn_abbrechen.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_abbrechen)

        self.btn_speichern = QPushButton(_("Speichern"))
        self.btn_speichern.clicked.connect(self._on_ok_clicked)
        btn_layout.addWidget(self.btn_speichern)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _on_ok_clicked(self):
        """Prüft Pflichtfelder und zeigt Fehlermeldung wenn etwas fehlt."""
        fehler = []
        
        betrag_text = self.input_betrag.text().strip()
        if not betrag_text:
            fehler.append(_("Betrag"))
        else:
            try:
                float(betrag_text.replace(',', '.').replace("'", ""))
            except Exception:
                fehler.append(_("Betrag (ungültiger Wert)"))
        
        if fehler:
            QMessageBox.warning(
                self,
                _("Pflichtfelder fehlen"),
                _("Bitte fülle folgende Pflichtfelder aus:") + "\n\n• " + "\n• ".join(fehler)
            )
            return
        
        self.accept()

    def get_daten(self):
        """Rückgabe der eingegebenen Daten als Dictionary"""
        return {
            "id": self.input_nr.text(),
            "datum": self.input_datum.date().toString("yyyy-MM-dd"),
            "typ": self.dropdown_typ.currentText(),
            "kategorie": self.dropdown_kategorie.currentText(),
            "betrag": self.input_betrag.text(),
            "beschreibung": self.input_beschreibung.toPlainText(),
        }

