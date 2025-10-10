# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
    QTextEdit, QPushButton, QComboBox, QDateEdit, QMessageBox, QTableWidget,
    QTableWidgetItem, QDoubleSpinBox, QSizePolicy
)
from db_connection import get_db, dict_cursor_factory
from PyQt5.QtCore import Qt, QDate
import json

# Optional: „Aus Lager“-Dialog; wenn nicht vorhanden, bleibt der Button deaktiviert.
try:
    from gui.select_inventory_item import SelectInventoryItemDialog
    HAS_LAGER = True
except Exception:
    HAS_LAGER = False


def _to_float(val, default=0.0):
    if val is None:
        return float(default)
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip().replace("'", "").replace(" ", "")
    s = s.replace(",", ".")
    try:
        return float(s)
    except Exception:
        return float(default)


def _fmt_money(x):
    try:
        return f"{float(x):.2f}"
    except Exception:
        return "0.00"


class RechnungDialog(QDialog):
    """
    Kombinierte Version des Rechnung-Dialogs:
    - Beinhaltet die Positions-Tabelle (Beschreibung, Menge, Einzelpreis, Total) inkl. Summenberechnung
    - Behält die neuen Felder/Defaults: Zahlungsbedingungen-Default, Abschiedsgruss mit Firmenname
      aus config/einstellungen.json, Status-Dropdown, UID, MWST-Spinbox, ISO-Datum (yyyy-MM-dd)
    - Liest/schreibt Positionen über get_rechnung()
    """
    COL_BESCHREIBUNG = 0
    COL_MENGE = 1
    COL_EPREIS = 2
    COL_TOTAL = 3

    def __init__(self, kunden_liste, kunden_firmen, kunden_adressen, *args, **kwargs):
        parent = kwargs.pop('parent', None)
        super().__init__(parent)
        self.setWindowTitle("Rechnung")
        self.resize(1200, 900)

        # --- Eingangsparameter ---
        self.rechnung = None
        self.mwst_voreinstellung = float(kwargs.pop('mwst_voreinstellung', 0.0))
        if len(args) >= 1:
            a0 = args[0]
            if isinstance(a0, dict):
                self.rechnung = a0
            else:
                try:
                    self.mwst_voreinstellung = float(a0)
                except Exception:
                    pass

        self.kunden_liste = list(kunden_liste or [])
        self.kunden_firmen = dict(kunden_firmen or {})
        self.kunden_adressen = dict(kunden_adressen or {})

        # --- UI ---
        root = QVBoxLayout(self)
        grid = QGridLayout()
        row = 0

        # Kopfbereich
        grid.addWidget(QLabel("Rechnungs-Nr:"), row, 0)
        self.le_rechnungsnr = QLineEdit()
        grid.addWidget(self.le_rechnungsnr, row, 1, 1, 3)
        row += 1

        grid.addWidget(QLabel("Kunde:"), row, 0)
        self.cb_kunde = QComboBox()
        self.cb_kunde.addItems(self.kunden_liste)
        grid.addWidget(self.cb_kunde, row, 1)

        grid.addWidget(QLabel("Firma:"), row, 2)
        self.le_firma = QLineEdit()
        self.le_firma.setReadOnly(True)
        grid.addWidget(self.le_firma, row, 3)
        row += 1

        grid.addWidget(QLabel("Adresse:"), row, 0)
        self.te_adresse = QTextEdit()
        self.te_adresse.setFixedHeight(70)
        self.te_adresse.setReadOnly(True)
        grid.addWidget(self.te_adresse, row, 1, 1, 3)
        row += 1

        grid.addWidget(QLabel("Datum:"), row, 0)
        self.de_datum = QDateEdit(calendarPopup=True)
        self.de_datum.setDisplayFormat("yyyy-MM-dd")  # ISO wie in der neuen Version
        self.de_datum.setDate(QDate.currentDate())
        grid.addWidget(self.de_datum, row, 1)

        grid.addWidget(QLabel("UID:"), row, 2)
        self.le_uid = QLineEdit()
        grid.addWidget(self.le_uid, row, 3)
        row += 1

        # MWST
        grid.addWidget(QLabel("MWST %:"), row, 0)
        self.sb_mwst = QDoubleSpinBox()
        self.sb_mwst.setDecimals(2)
        self.sb_mwst.setRange(0.0, 100.0)
        self.sb_mwst.setSingleStep(0.1)
        self.sb_mwst.setValue(self.mwst_voreinstellung)
        grid.addWidget(self.sb_mwst, row, 1)
        row += 1

        # Zahlungsbedingungen
        grid.addWidget(QLabel("Zahlungsbedingungen:"), row, 0)
        self.text_zahlungskonditionen = QTextEdit()
        self.text_zahlungskonditionen.setFixedHeight(60)
        grid.addWidget(self.text_zahlungskonditionen, row, 1, 1, 3)
        row += 1

        # Status
        grid.addWidget(QLabel("Status:"), row, 0)
        self.cb_status = QComboBox()
        self.cb_status.addItem("Automatisch (aus Fälligkeit)", "")
        self.cb_status.addItem("offen", "offen")
        self.cb_status.addItem("bezahlt", "bezahlt")
        self.cb_status.addItem("überfällig", "überfällig")
        grid.addWidget(self.cb_status, row, 1, 1, 3)
        row += 1

        # Abschiedsgruss
        grid.addWidget(QLabel("Abschiedsgruss:"), row, 0)
        self.text_abschluss = QTextEdit()
        self.text_abschluss.setFixedHeight(70)
        grid.addWidget(self.text_abschluss, row, 1, 1, 3)
        row += 1

        root.addLayout(grid)

        # --- Positionen (hinzugefügt) ---
        self.tbl_pos = QTableWidget(0, 4)
        self.tbl_pos.setHorizontalHeaderLabels(["Beschreibung", "Menge", "Einzelpreis", "Total"])
        # Spaltenbreiten festlegen: Beschreibung grösser, Total kleiner
        self.tbl_pos.setColumnWidth(0, 800)   # Beschreibung
        self.tbl_pos.setColumnWidth(1, 80)    # Menge
        self.tbl_pos.setColumnWidth(2, 100)   # Einzelpreis
        self.tbl_pos.setColumnWidth(3, 100)   # Total

        self.tbl_pos.horizontalHeader().setStretchLastSection(True)
        self.tbl_pos.setSelectionBehavior(self.tbl_pos.SelectRows)
        self.tbl_pos.setEditTriggers(self.tbl_pos.AllEditTriggers)
        root.addWidget(self.tbl_pos)
        # Sichtbarkeit: mindestens 4 Zeilen + Header sichtbar machen
        try:
            row_h = self.tbl_pos.verticalHeader().defaultSectionSize()
            header_h = self.tbl_pos.horizontalHeader().height()
            extra = 60  # Ränder/Scrollleisten-Puffer
            self.tbl_pos.setMinimumHeight(int(4 * row_h + header_h + extra))
        except Exception:
            self.tbl_pos.setMinimumHeight(4 * 30 + 24 + 60)  # Fallback

        # Buttons für Positionen
        btn_row_pos = QHBoxLayout()
        self.btn_add = QPushButton("Position hinzufügen")
        self.btn_remove = QPushButton("Ausgewählte entfernen")
        self.btn_from_stock = QPushButton("Aus Lager...")
        self.btn_from_stock.setEnabled(HAS_LAGER)

        # Buttons sollen gleichmäßig verteilt werden
        for b in (self.btn_add, self.btn_remove, self.btn_from_stock):
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        btn_row_pos.addWidget(self.btn_add)
        btn_row_pos.addWidget(self.btn_remove)
        btn_row_pos.addWidget(self.btn_from_stock)

        # Gleiche Stretch-Faktoren für alle drei Buttons
        btn_row_pos.setStretch(0, 1)
        btn_row_pos.setStretch(1, 1)
        btn_row_pos.setStretch(2, 1)

        root.addLayout(btn_row_pos)

        # Summenbereich
        sum_row = QGridLayout()
        sum_row.addWidget(QLabel("Zwischensumme:"), 0, 2)
        self.le_subtotal = QLineEdit("0.00"); self.le_subtotal.setReadOnly(True); self.le_subtotal.setAlignment(Qt.AlignRight)
        sum_row.addWidget(self.le_subtotal, 0, 3)

        sum_row.addWidget(QLabel("MWST-Betrag:"), 1, 2)
        self.le_mwst_betrag = QLineEdit("0.00"); self.le_mwst_betrag.setReadOnly(True); self.le_mwst_betrag.setAlignment(Qt.AlignRight)
        sum_row.addWidget(self.le_mwst_betrag, 1, 3)

        sum_row.addWidget(QLabel("Gesamtsumme:"), 2, 2)
        self.le_total = QLineEdit("0.00"); self.le_total.setReadOnly(True); self.le_total.setAlignment(Qt.AlignRight)
        sum_row.addWidget(self.le_total, 2, 3)
        root.addLayout(sum_row)

        # Buttons unten
        btn_row = QHBoxLayout()
        btn_ok = QPushButton("Speichern")
        btn_cancel = QPushButton("Abbrechen")
        btn_row.addStretch()
        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_cancel)
        root.addLayout(btn_row)

        # Connections
        self.cb_kunde.currentTextChanged.connect(self._on_kunde_changed)
        btn_ok.clicked.connect(self._accept)
        btn_cancel.clicked.connect(self.reject)
        self.btn_add.clicked.connect(self._add_position)
        self.btn_remove.clicked.connect(self._remove_selected_positions)
        self.btn_from_stock.clicked.connect(self._choose_from_stock)
        self.tbl_pos.cellChanged.connect(self._on_cell_changed)
        self.sb_mwst.valueChanged.connect(self._recalc_totals)

        # --- Defaults setzen (nur bei neuer Rechnung) ---
        if not self.rechnung:
            # Zahlungsbedingungen: hart gewünschter Standardtext
            self.text_zahlungskonditionen.setPlainText("Zahlbar inner 10 Tagen")
            # Abschiedsgruss: Firmenname aus Einstellungen holen
            firmenname = self._lade_firmenname_aus_einstellungen() or "INAT Performance GmbH"
            self.text_abschluss.setPlainText(f"Freundliche grüsse {firmenname}")

        # Kunde -> Firma/Adresse initial
        self._on_kunde_changed(self.cb_kunde.currentText())

        # Falls Bearbeiten: bestehende Werte einfüllen (überschreibt defaults)
        if isinstance(self.rechnung, dict):
            self._befuelle_von_rechnung(self.rechnung)

        # Erste Summenberechnung
        self._recalc_totals()

    # -- Helpers --
    def _on_kunde_changed(self, name: str):
        self.le_firma.setText(self.kunden_firmen.get(name, ""))
        self.te_adresse.setPlainText(self.kunden_adressen.get(name, ""))

    def _lade_firmenname_aus_einstellungen(self) -> str:
        """
        Liest den Firmennamen aus config/einstellungen.json.
        Erwartete Felder in dieser Reihenfolge: 'name_der_firma', 'firma_name', 'firma', 'name'.
        """
        try:
            with open("config/einstellungen.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            return (
                data.get("name_der_firma")
                or data.get("firma_name")
                or data.get("firma")
                or data.get("name")
                or ""
            )
        except Exception:
            return ""

    def _befuelle_von_rechnung(self, r: dict):
        self.le_rechnungsnr.setText(r.get("rechnung_nr", ""))

        kunde = r.get("kunde", "")
        if kunde and kunde in self.kunden_liste:
            self.cb_kunde.setCurrentText(kunde)
        elif kunde:
            # Kunde existiert evtl. nicht mehr -> trotzdem anzeigen
            self.cb_kunde.insertItem(0, kunde)
            self.cb_kunde.setCurrentIndex(0)
        self.le_firma.setText(r.get("firma", ""))
        self.te_adresse.setPlainText(r.get("adresse", ""))

        ds = (r.get("datum") or "").strip()
        if ds:
            try:
                y, m, d = [int(x) for x in ds.split("-")]
                self.de_datum.setDate(QDate(y, m, d))
            except Exception:
                pass

        self.le_uid.setText(r.get("uid", ""))
        try:
            self.sb_mwst.setValue(float(r.get("mwst", self.mwst_voreinstellung)))
        except Exception:
            pass

        if r.get("zahlungskonditionen"):
            self.text_zahlungskonditionen.setPlainText(r.get("zahlungskonditionen"))

        abschluss = (r.get("abschluss") or "").strip().lower()
        idx = self.cb_status.findData(abschluss if abschluss in ("offen","bezahlt","überfällig") else "")
        self.cb_status.setCurrentIndex(idx if idx >= 0 else 0)

        if r.get("abschluss_text"):
            self.text_abschluss.setPlainText(r.get("abschluss_text"))

        # Positionen laden
        pos_list = r.get("positionen") or []
        for p in pos_list:
            beschr = p.get("beschreibung", p.get("text", ""))
            menge = _to_float(p.get("menge", p.get("qty", 1)), 1.0)
            epreis = _to_float(p.get("einzelpreis", p.get("preis", p.get("unit_price", 0.0))), 0.0)
            self._add_position(beschr, menge, epreis, recalc=False)
        self._recalc_totals()

         # -- Positionen API --
    def _add_position(self, beschreibung: str = "", menge: float = 1.0, epreis: float = 0.0, recalc=True):
        # Begrenzung: maximal 10 Positionen
        if self.tbl_pos.rowCount() >= 10:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Maximale Anzahl erreicht",
                "Es können maximal 10 Positionen pro Rechnung hinzugefügt werden."
            )
            return


        self.tbl_pos.blockSignals(True)
        row = self.tbl_pos.rowCount()
        self.tbl_pos.insertRow(row)

        it_b = QTableWidgetItem(str(beschreibung or ""))
        it_b.setFlags(it_b.flags() | Qt.ItemIsEditable)
        self.tbl_pos.setItem(row, self.COL_BESCHREIBUNG, it_b)

        it_m = QTableWidgetItem(_fmt_money(menge).replace(".00", ""))  # Menge oft ganzzahlig
        it_m.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.tbl_pos.setItem(row, self.COL_MENGE, it_m)

        it_p = QTableWidgetItem(_fmt_money(epreis))
        it_p.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.tbl_pos.setItem(row, self.COL_EPREIS, it_p)

        total = menge * epreis
        it_t = QTableWidgetItem(_fmt_money(total))
        it_t.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)  # Total ist readonly
        it_t.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.tbl_pos.setItem(row, self.COL_TOTAL, it_t)

        self.tbl_pos.blockSignals(False)
        if recalc:
            self._recalc_totals()

    def _remove_selected_positions(self):
        rows = sorted({idx.row() for idx in self.tbl_pos.selectedIndexes()}, reverse=True)
        if not rows:
            return
        self.tbl_pos.blockSignals(True)
        for r in rows:
            self.tbl_pos.removeRow(r)
        self.tbl_pos.blockSignals(False)
        self._recalc_totals()

    def _on_cell_changed(self, row, col):
        if col in (self.COL_MENGE, self.COL_EPREIS, self.COL_BESCHREIBUNG):
            menge = _to_float(self._item_text(row, self.COL_MENGE), 0.0)
            preis = _to_float(self._item_text(row, self.COL_EPREIS), 0.0)
            total = menge * preis
            self.tbl_pos.blockSignals(True)
            it_t = self.tbl_pos.item(row, self.COL_TOTAL)
            if it_t is None:
                it_t = QTableWidgetItem()
                it_t.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                it_t.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.tbl_pos.setItem(row, self.COL_TOTAL, it_t)
            it_t.setText(_fmt_money(total))
            self.tbl_pos.blockSignals(False)
            self._recalc_totals()

    def _item_text(self, row, col):
        it = self.tbl_pos.item(row, col)
        return it.text() if it else ""

    def _choose_from_stock(self):
        if self.tbl_pos.rowCount() >= 10:
            QMessageBox.warning(self, "Limit erreicht", "Es können maximal 10 Positionen pro Rechnung hinzugefügt werden.")
            return
        if not HAS_LAGER:
            QMessageBox.information(self, "Nicht verfügbar", "Der Lagerdialog ist nicht verfügbar.")
            return
        dlg = SelectInventoryItemDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            item = getattr(dlg, "selected_item", None) or {}
            beschr = item.get("name") or item.get("bezeichnung") or ""
            epreis = _to_float(item.get("price") or item.get("verkaufspreis") or item.get("preis") or 0.0, 0.0)
            self._add_position(beschr, 1.0, epreis)

    # -- Summen --
    def _recalc_totals(self):
        subtotal = 0.0
        for r in range(self.tbl_pos.rowCount()):
            subtotal += _to_float(self._item_text(r, self.COL_TOTAL), 0.0)
        mwst_satz = float(self.sb_mwst.value())
        mwst_betrag = subtotal * (mwst_satz / 100.0)
        total = subtotal + mwst_betrag

        self.le_subtotal.setText(_fmt_money(subtotal))
        self.le_mwst_betrag.setText(_fmt_money(mwst_betrag))
        self.le_total.setText(_fmt_money(total))

    # -- API --
    def _accept(self):
        if not self.cb_kunde.currentText().strip():
            QMessageBox.warning(self, "Fehlende Angaben", "Bitte einen Kunden auswählen.")
            return
        self.accept()

    def get_rechnung(self) -> dict:
        # Positionen einsammeln
        positionen = []
        for r in range(self.tbl_pos.rowCount()):
            beschr = self._item_text(r, self.COL_BESCHREIBUNG).strip()
            menge = _to_float(self._item_text(r, self.COL_MENGE), 0.0)
            epreis = _to_float(self._item_text(r, self.COL_EPREIS), 0.0)
            total = _to_float(self._item_text(r, self.COL_TOTAL), menge * epreis)
            positionen.append({
                "beschreibung": beschr,
                "menge": menge,
                "einzelpreis": epreis,
                "total": total
            })

        return {
            "rechnung_nr": self.le_rechnungsnr.text().strip(),
            "kunde": self.cb_kunde.currentText().strip(),
            "firma": self.le_firma.text().strip(),
            "adresse": self.te_adresse.toPlainText().strip(),
            "datum": self.de_datum.date().toString("yyyy-MM-dd"),
            "uid": self.le_uid.text().strip(),
            "mwst": float(self.sb_mwst.value()),
            "zahlungskonditionen": self.text_zahlungskonditionen.toPlainText().strip(),
            "abschluss": self.cb_status.currentData() or "",       # manuell gesetzter Status (DB-Feld)
            "abschluss_text": self.text_abschluss.toPlainText().strip(),  # nur für Export/UI
            "positionen": positionen,
            "summen": {
                "zwischensumme": _to_float(self.le_subtotal.text(), 0.0),
                "mwst_betrag": _to_float(self.le_mwst_betrag.text(), 0.0),
                "gesamt": _to_float(self.le_total.text(), 0.0)
            }
        }


class RechnungLayoutDialog(QDialog):
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setWindowTitle("Rechnungslayout bearbeiten (Platzhalter)")
        self.resize(400, 200)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(
            "Dieses Dialogfenster ist ein Platzhalter.\n"
            "Falls du ein echtes Layout-UI brauchst, sag Bescheid."
        ))
        btn = QPushButton("Schließen")
        btn.clicked.connect(self.reject)
        lay.addWidget(btn)

