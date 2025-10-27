from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QPushButton, QDateEdit, QMessageBox
)
from db_connection import get_db, dict_cursor_factory
from PyQt5.QtCore import Qt, QDate

class ReifenlagerDialog(QDialog):
    def __init__(self, parent=None, reifen=None):
        super().__init__(parent)
        self.setWindowTitle("Reifen erfassen" if reifen is None else "Reifen bearbeiten")
        self.resize(500, 400)
        layout = QVBoxLayout()

        # Kundenliste als ComboBox
        layout.addWidget(QLabel("Kunde:"))
        self.kunden = self.lade_kundenliste()
        self.kunden_box = QComboBox()
        self.kunden_box.addItem("Kein Kunde", None)
        for k in self.kunden:
            kundennr = k.get("kundennr")
            anzeige = k.get("display") or f"{(k.get('anrede') or '').strip()} {(k.get('name') or '').strip()}".strip()
            self.kunden_box.addItem(anzeige or "", kundennr)
        layout.addWidget(self.kunden_box)

        # Restliche Felder
        self.fahrzeug_input = QLineEdit()
        self.dimension_input = QLineEdit()

        self.typ_input = QComboBox()
        self.typ_input.addItems(["Sommer", "Winter", "Ganzjahr"])

        self.dot_input = QLineEdit()
        self.lagerort_input = QLineEdit()

        self.eingelagert_am_input = QDateEdit()
        self.eingelagert_am_input.setCalendarPopup(True)
        self.eingelagert_am_input.setDisplayFormat("yyyy-MM-dd")
        self.eingelagert_am_input.setDate(QDate.currentDate())

        self.ausgelagert_am_input = QDateEdit()
        self.ausgelagert_am_input.setCalendarPopup(True)
        self.ausgelagert_am_input.setDisplayFormat("yyyy-MM-dd")
        # Standard: leer lassen (kein Datum)
        self.ausgelagert_am_input.setDate(QDate(2000, 1, 1))  # Optional: Dummy für "kein Auslagerungsdatum"

        self.bemerkung_input = QLineEdit()

        self.preis_input = QLineEdit()
        self.preis_input.setPlaceholderText("Preis")
        layout.addWidget(QLabel("Preis:"))
        layout.addWidget(self.preis_input)

        self.waehrung_input = QComboBox()
        self.waehrung_input.addItems(["EUR", "USD", "CHF"])
        layout.addWidget(QLabel("Währung:"))
        layout.addWidget(self.waehrung_input)

        layout.addWidget(QLabel("Fahrzeug:"))
        layout.addWidget(self.fahrzeug_input)
        layout.addWidget(QLabel("Dimension (z.B. 205/55 R16):"))
        layout.addWidget(self.dimension_input)
        layout.addWidget(QLabel("Typ (Sommer/Winter/Ganzjahr):"))
        layout.addWidget(self.typ_input)
        layout.addWidget(QLabel("DOT:"))
        layout.addWidget(self.dot_input)
        layout.addWidget(QLabel("Lagerort:"))
        layout.addWidget(self.lagerort_input)
        layout.addWidget(QLabel("Eingelagert am:"))
        layout.addWidget(self.eingelagert_am_input)
        layout.addWidget(QLabel("Ausgelagert am:"))
        layout.addWidget(self.ausgelagert_am_input)
        layout.addWidget(QLabel("Bemerkung:"))
        layout.addWidget(self.bemerkung_input)

        if reifen:
            idx = self.kunden_box.findText(reifen.get("kunde_anzeige", ""), Qt.MatchContains)
            if idx >= 0:
                self.kunden_box.setCurrentIndex(idx)
            self.fahrzeug_input.setText(reifen.get("fahrzeug", ""))
            self.dimension_input.setText(reifen.get("dimension", ""))
            typ_idx = self.typ_input.findText(reifen.get("typ", ""), Qt.MatchExactly)
            if typ_idx >= 0:
                self.typ_input.setCurrentIndex(typ_idx)
            self.dot_input.setText(reifen.get("dot", ""))
            self.lagerort_input.setText(reifen.get("lagerort", ""))
            self.preis_input.setText(str(reifen.get("preis", "")))
            waehrung_idx = self.waehrung_input.findText(reifen.get("waehrung", "EUR"), Qt.MatchExactly)
            if waehrung_idx >= 0:
                self.waehrung_input.setCurrentIndex(waehrung_idx)
            # Datum für eingelagert_am
            eingelagert = reifen.get("eingelagert_am", "")
            if eingelagert:
                try:
                    self.eingelagert_am_input.setDate(QDate.fromString(eingelagert, "yyyy-MM-dd"))
                except Exception:
                    pass
            # Datum für ausgelagert_am
            ausgelagert = reifen.get("ausgelagert_am", "")
            if ausgelagert:
                try:
                    self.ausgelagert_am_input.setDate(QDate.fromString(ausgelagert, "yyyy-MM-dd"))
                except Exception:
                    pass
            self.bemerkung_input.setText(reifen.get("bemerkung", ""))

        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("OK")
        btn_cancel = QPushButton("Abbrechen")
        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def lade_kundenliste(self):
        """
        Liefert Liste von dicts mit mindestens den Keys:
        'kundennr', 'anrede', 'name', 'firma', 'display'
        (robust gegen dict / sqlite3.Row / tuple rows)
        """
        out = []
        conn = get_db()
        try:
            try:
                cur = conn.cursor(cursor_factory=dict_cursor_factory(conn))
            except Exception:
                cur = conn.cursor()
            # explizit Spalten abfragen, damit Reihenfolge bekannt ist
            cur.execute("SELECT kundennr, anrede, name, firma FROM kunden ORDER BY name")
            rows = cur.fetchall()
            desc = getattr(cur, "description", None)
            col_names = [d[0].lower() for d in desc] if desc else []
        except Exception:
            rows = []
            col_names = []
        finally:
            try:
                conn.close()
            except Exception:
                pass

        for r in rows:
            # dict-like (oder sqlite3.Row behaves like mapping)
            if isinstance(r, dict) or hasattr(r, "keys"):
                try:
                    rd = dict(r)
                except Exception:
                    rd = {k: getattr(r, k) for k in getattr(r, "keys", lambda: [])()}
                # case-insensitive access
                rd_lower = {k.lower(): v for k, v in rd.items()}
                kundennr = rd_lower.get("kundennr")
                anrede = (rd_lower.get("anrede") or "") 
                name = (rd_lower.get("name") or "")
                firma = (rd_lower.get("firma") or "")
            else:
                # sequence/tuple fallback - use description mapping if available
                try:
                    seq = list(r)
                except Exception:
                    seq = []
                if col_names and len(col_names) == len(seq):
                    m = dict(zip(col_names, seq))
                    kundennr = m.get("kundennr")
                    anrede = (m.get("anrede") or "")
                    name = (m.get("name") or "")
                    firma = (m.get("firma") or "")
                else:
                    # assume order (kundennr, anrede, name, firma)
                    while len(seq) < 4:
                        seq.append(None)
                    kundennr, anrede, name, firma = seq[0], seq[1] or "", seq[2] or "", seq[3] or ""

            display = f"{anrede} {name}".strip()
            if firma:
                display = f"{display} ({firma})" if display else firma

            out.append({
                "kundennr": kundennr,
                "anrede": anrede,
                "name": name,
                "firma": firma,
                "display": display
            })
        return out

    def accept(self):
        # keine Pflicht mehr: akzeptieren auch ohne Kundenauswahl (DB vergibt eigene ID)
        super().accept()

    def get_daten(self):
        # Sentinel für "kein Datum" (falls ihr das so verwendet habt)
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
            "kundennr": None if self.kunden_box.currentData() is None else int(self.kunden_box.currentData()),
            "kunde_anzeige": self.kunden_box.currentText(),
            "fahrzeug": self.fahrzeug_input.text().strip(),
            "dimension": self.dimension_input.text().strip(),
            "typ": self.typ_input.currentText(),
            "dot": self.dot_input.text().strip(),
            "lagerort": self.lagerort_input.text().strip(),
            "eingelagert_am": fmt_date(getattr(self, "eingelagert_am_input", None)),
            "ausgelagert_am": fmt_date(getattr(self, "ausgelagert_am_input", None)),
            "bemerkung": self.bemerkung_input.text().strip(),
            "preis": self.preis_input.text().strip(),
            "waehrung": self.waehrung_input.currentText()
        }


