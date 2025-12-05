# -*- coding: utf-8 -*-
from .base_dialog import BaseDialog
from .dialog_styles import GROUPBOX_STYLE
from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QDateEdit, QMessageBox, QGroupBox, QFormLayout
)
from db_connection import get_db
from PyQt5.QtCore import Qt, QDate
from i18n import _
from gui.popup_calendar import PopupCalendarWidget


class ReifenlagerDialog(BaseDialog):
    def __init__(self, parent=None, reifen=None):
        super().__init__(parent)
        self.setWindowTitle(_("Reifen erfassen") if reifen is None else _("Reifen bearbeiten"))
        self.resize(520, 650)

        layout = self.content_layout
        layout.setSpacing(15)

        # === Kunde & Fahrzeug ===
        kunde_group = QGroupBox(_("Kunde & Fahrzeug"))
        kunde_group.setStyleSheet(GROUPBOX_STYLE)
        kunde_layout = QFormLayout(kunde_group)
        kunde_layout.setSpacing(10)

        self.kunden_input = QComboBox()
        self.kunden_input.setEditable(True)
        self._lade_kunden()
        kunde_layout.addRow(_("Kunde:"), self.kunden_input)

        self.fahrzeug_input = QLineEdit()
        kunde_layout.addRow(_("Fahrzeug:"), self.fahrzeug_input)

        layout.addWidget(kunde_group)

        # === Reifendaten ===
        reifen_group = QGroupBox(_("Reifendaten"))
        reifen_group.setStyleSheet(GROUPBOX_STYLE)
        reifen_layout = QFormLayout(reifen_group)
        reifen_layout.setSpacing(10)

        self.dimension_input = QLineEdit()
        self.dimension_input.setPlaceholderText(_("z.B. 205/55 R16"))
        reifen_layout.addRow(_("Dimension:"), self.dimension_input)

        self.typ_input = QComboBox()
        self.typ_input.addItems([_("Sommer"), _("Winter"), _("Ganzjahr")])
        reifen_layout.addRow(_("Typ:"), self.typ_input)

        self.dot_input = QLineEdit()
        reifen_layout.addRow(_("DOT:"), self.dot_input)

        layout.addWidget(reifen_group)

        # === Lager ===
        lager_group = QGroupBox(_("Lagerung"))
        lager_group.setStyleSheet(GROUPBOX_STYLE)
        lager_layout = QFormLayout(lager_group)
        lager_layout.setSpacing(10)

        self.lagerort_input = QLineEdit()
        lager_layout.addRow(_("Lagerort:"), self.lagerort_input)

        self.eingelagert_am_input = QDateEdit()
        self.eingelagert_am_input.setCalendarPopup(True)
        self.eingelagert_am_input.setDisplayFormat("dd.MM.yyyy")
        self.eingelagert_am_input.setDate(QDate.currentDate())
        try:
            cal = PopupCalendarWidget(self)
            cal.setVerticalHeaderFormat(cal.NoVerticalHeader)
            cal.setGridVisible(True)
            self.eingelagert_am_input.setCalendarWidget(cal)
        except Exception:
            pass
        lager_layout.addRow(_("Eingelagert am:"), self.eingelagert_am_input)

        self.ausgelagert_am_input = QDateEdit()
        self.ausgelagert_am_input.setCalendarPopup(True)
        self.ausgelagert_am_input.setDisplayFormat("dd.MM.yyyy")
        self.ausgelagert_am_input.setDate(QDate(2000, 1, 1))
        try:
            cal2 = PopupCalendarWidget(self)
            cal2.setVerticalHeaderFormat(cal2.NoVerticalHeader)
            cal2.setGridVisible(True)
            self.ausgelagert_am_input.setCalendarWidget(cal2)
        except Exception:
            pass
        lager_layout.addRow(_("Ausgelagert am:"), self.ausgelagert_am_input)

        layout.addWidget(lager_group)

        # === Preis & Bemerkung ===
        preis_group = QGroupBox(_("Preis & Bemerkung"))
        preis_group.setStyleSheet(GROUPBOX_STYLE)
        preis_layout = QFormLayout(preis_group)
        preis_layout.setSpacing(10)

        self.preis_input = QLineEdit()
        self.preis_input.setPlaceholderText(_("Pflichtfeld"))
        preis_layout.addRow(_("Preis:"), self.preis_input)

        self.waehrung_input = QComboBox()
        self.waehrung_input.addItems(["CHF", "EUR", "USD"])
        preis_layout.addRow(_("Währung:"), self.waehrung_input)

        self.bemerkung_input = QLineEdit()
        preis_layout.addRow(_("Bemerkung:"), self.bemerkung_input)

        layout.addWidget(preis_group)

        # Daten laden wenn vorhanden
        if reifen:
            idx = self.kunden_input.findText(reifen.get("kunde_anzeige", ""), Qt.MatchContains)
            if idx >= 0:
                self.kunden_input.setCurrentIndex(idx)
            self.fahrzeug_input.setText(reifen.get("fahrzeug", ""))
            self.dimension_input.setText(reifen.get("dimension", ""))
            typ_idx = self.typ_input.findText(reifen.get("typ", ""), Qt.MatchExactly)
            if typ_idx >= 0:
                self.typ_input.setCurrentIndex(typ_idx)
            self.dot_input.setText(reifen.get("dot", ""))
            self.lagerort_input.setText(reifen.get("lagerort", ""))
            self.preis_input.setText(str(reifen.get("preis", "")))
            waehrung_idx = self.waehrung_input.findText(reifen.get("waehrung", "CHF"), Qt.MatchExactly)
            if waehrung_idx >= 0:
                self.waehrung_input.setCurrentIndex(waehrung_idx)
            eingelagert = reifen.get("eingelagert_am", "")
            if eingelagert:
                try:
                    self.eingelagert_am_input.setDate(QDate.fromString(eingelagert, "yyyy-MM-dd"))
                except Exception:
                    pass
            ausgelagert = reifen.get("ausgelagert_am", "")
            if ausgelagert:
                try:
                    self.ausgelagert_am_input.setDate(QDate.fromString(ausgelagert, "yyyy-MM-dd"))
                except Exception:
                    pass
            self.bemerkung_input.setText(reifen.get("bemerkung", ""))

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
        if not self.dimension_input.text().strip():
            fehler.append(_("Dimension"))
        
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

    def _lade_kunden(self):
        """Lädt alle Kunden aus der Datenbank in das Dropdown."""
        self.kunden_input.clear()
        self.kunden_input.addItem(_("(Kein Kunde)"), None)
        
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("SELECT kundennr, anrede, name, firma FROM kunden ORDER BY name")
            rows = cur.fetchall()
            
            for r in rows:
                if hasattr(r, 'keys'):
                    kundennr = r['kundennr']
                    anrede = r['anrede'] or ""
                    name = r['name'] or ""
                    firma = r['firma'] or ""
                else:
                    kundennr, anrede, name, firma = r[0], r[1] or "", r[2] or "", r[3] or ""
                
                display = f"{anrede} {name}".strip()
                if firma:
                    display = f"{display} ({firma})" if display else firma
                
                self.kunden_input.addItem(display, kundennr)
        except Exception as e:
            print(_("Fehler beim Laden der Kunden:"), e)
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def get_daten(self):
        sentinel = QDate(2000, 1, 1)

        def fmt_date(widget):
            if not hasattr(widget, "date"):
                return ""
            d = widget.date()
            if not d.isValid():
                return ""
            if d == sentinel:
                return ""
            return d.toString("yyyy-MM-dd")

        return {
            "kundennr": None if self.kunden_input.currentData() is None else int(self.kunden_input.currentData()),
            "kunde_anzeige": self.kunden_input.currentText(),
            "fahrzeug": self.fahrzeug_input.text().strip(),
            "dimension": self.dimension_input.text().strip(),
            "typ": self.typ_input.currentText(),
            "dot": self.dot_input.text().strip(),
            "lagerort": self.lagerort_input.text().strip(),
            "eingelagert_am": fmt_date(getattr(self, "eingelagert_am_input", None)),
            "ausgelagert_am": fmt_date(getattr(self, "ausgelagert_am_input", None)),
            "bemerkung": self.bemerkung_input.text().strip(),
            "preis": None if self.preis_input.text().strip() == "" else float(self.preis_input.text().strip().replace(',', '.').replace("'", "")),
            "waehrung": self.waehrung_input.currentText()
        }
