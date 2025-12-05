# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QLineEdit, QFileDialog, QLabel, QAbstractItemView, QToolButton,
    QHeaderView, QSizePolicy, QFrame, QGraphicsDropShadowEffect
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QColor, QFont, QStandardItemModel, QStandardItem, QIcon
from fpdf import FPDF
from db_connection import get_db, dict_cursor_factory, get_einstellungen, get_config_value
from gui.popup_calendar import PopupCalendarWidget
from gui.modern_widgets import (
    COLORS, FONT_SIZES, SPACING, BORDER_RADIUS,
    get_table_stylesheet, get_button_primary_stylesheet,
    get_button_secondary_stylesheet, get_input_stylesheet
)
from paths import data_dir, local_db_path
import pandas as pd
import datetime
import os, shutil, glob
import sqlite3
from gui.buchhaltung_dialog import BuchhaltungDialog
import hashlib, tempfile
from i18n import _
# --- Invoice DB helpers (works for SQLite and Postgres) ---
def _execute_with_paramstyle(cur, query, params):
    try:
        cur.execute(query, params)
    except Exception:
        # fallback: replace %s with ? for sqlite3
        cur.execute(query.replace("%s", "?"), params)

def save_invoice_db(buchung_id: int, filename: str, data: bytes, content_type: str = "application/pdf"):
    conn = get_db()
    cur = conn.cursor()
    size = len(data)
    try:
        _execute_with_paramstyle(cur,
            "INSERT INTO invoices (buchung_id, filename, content, content_type, size) VALUES (%s,%s,%s,%s,%s)",
            (buchung_id, filename, data, content_type, size))
    except Exception:
        conn.rollback()
        conn.close()
        raise
    conn.commit()
    conn.close()

def get_invoices_for_buchung(buchung_id: int):
    conn = get_db()
    cur = conn.cursor()
    try:
        _execute_with_paramstyle(cur, "SELECT id, filename, size, created_at FROM invoices WHERE buchung_id = %s ORDER BY id ASC", (buchung_id,))
    except Exception:
        cur.execute("SELECT id, filename, size, created_at FROM invoices WHERE buchung_id = ? ORDER BY id ASC", (buchung_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_invoice_bytes(invoice_id: int):
    conn = get_db()
    cur = conn.cursor()
    try:
        _execute_with_paramstyle(cur, "SELECT filename, content, content_type FROM invoices WHERE id = %s", (invoice_id,))
    except Exception:
        cur.execute("SELECT filename, content, content_type FROM invoices WHERE id = ?", (invoice_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {"filename": row[0], "data": bytes(row[1]), "content_type": row[2]}

def delete_invoices_for_buchung(buchung_id: int):
    conn = get_db()
    cur = conn.cursor()
    try:
        _execute_with_paramstyle(cur, "DELETE FROM invoices WHERE buchung_id = %s", (buchung_id,))
    except Exception:
        cur.execute("DELETE FROM invoices WHERE buchung_id = ?", (buchung_id,))
    conn.commit()
    conn.close()

# ----------------- Einfache, zentrale Helfer (einmalig, modul-level) -----------------
def _is_sqlite_conn(conn) -> bool:
    """Erkenne SQLite-Verbindung (robust gegen Wrapper)."""
    try:
        import sqlite3 as _sqlite
        if isinstance(conn, _sqlite.Connection):
            return True
        return "sqlite" in conn.__class__.__module__.lower()
    except Exception:
        return False

def normalize_date_for_display(val) -> str:
    """Return 'YYYY-MM-DD' (no time) for display. Accepts date/datetime/str/bytes."""
    if val is None:
        return ""
    if isinstance(val, (bytes, bytearray)):
        try:
            val = val.decode("utf-8")
        except Exception:
            val = str(val)
    if isinstance(val, datetime.datetime):
        return val.date().isoformat()
    if isinstance(val, datetime.date):
        return val.isoformat()
    s = str(val).strip()
    if " " in s:
        s = s.split(" ", 1)[0]
    try:
        datetime.date.fromisoformat(s)
        return s
    except Exception:
        pass
    try:
        d = datetime.datetime.strptime(s, "%d.%m.%Y").date()
        return d.isoformat()
    except Exception:
        return s

def to_qdate(val) -> QDate:
    """Return QDate from val (date/datetime/str)."""
    if val is None or val == "":
        return QDate()  # invalid
    if isinstance(val, QDate):
        return val
    if isinstance(val, datetime.datetime):
        d = val.date()
        return QDate(d.year, d.month, d.day)
    if isinstance(val, datetime.date):
        return QDate(val.year, val.month, val.day)
    s = normalize_date_for_display(val)
    return QDate.fromString(s, "yyyy-MM-dd")

def to_db_date(val) -> str:
    """Return ISO 'YYYY-MM-DD' string for DB storage (no time)."""
    if val is None or val == "":
        return ""
    if isinstance(val, QDate):
        return val.toString("yyyy-MM-dd")
    if isinstance(val, datetime.datetime):
        return val.date().isoformat()
    if isinstance(val, datetime.date):
        return val.isoformat()
    return normalize_date_for_display(val)
# ------------------------------------------------------------------------------------

class BuchhaltungTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        # --- NEU: Temporäre Liste für initiales Laden ---
        self._initial_load_rows = []
        # blocking initial load - REMOVE or comment out
        # self.lade_eintraege()
    
    def _create_stat_card(self, title: str, value: str, accent_color: str) -> QFrame:
        """Erstellt eine Statistik-Karte im modernen Design."""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 12px;
            }}
        """)
        
        # Dezenter Schatten
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 15))
        card.setGraphicsEffect(shadow)
        
        card.setMinimumHeight(90)
        card.setMaximumHeight(110)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        layout = QVBoxLayout(card)
        layout.setSpacing(8)
        layout.setContentsMargins(20, 16, 20, 16)
        
        # Titel
        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: {FONT_SIZES['body']}px; font-weight: 500;")
        layout.addWidget(title_label)
        
        # Wert
        value_label = QLabel(value)
        value_label.setObjectName("valueLabel")
        value_label.setStyleSheet(f"color: {accent_color}; font-size: {FONT_SIZES['h2']}px; font-weight: 700;")
        layout.addWidget(value_label)
        
        layout.addStretch()
        
        return card

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.kategorien = self.lade_kategorien_aus_einstellungen()

        # Toolbar-Bereich
        toolbar = QFrame()
        toolbar.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border-bottom: 1px solid {COLORS['border']};
            }}
        """)
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(SPACING['xl'], SPACING['lg'], SPACING['xl'], SPACING['lg'])
        toolbar_layout.setSpacing(SPACING['md'])
        
        # Buttons links
        self.btn_neu = QPushButton(_("+ Neuer Eintrag"))
        self.btn_neu.setStyleSheet(get_button_primary_stylesheet() + "QPushButton { min-width: 140px; max-width: 180px; }")
        self.btn_neu.setCursor(Qt.PointingHandCursor)
        toolbar_layout.addWidget(self.btn_neu)
        
        for btn_text, btn_name in [
            (_("Bearbeiten"), "btn_bearbeiten"),
            (_("Löschen"), "btn_loeschen"),
            (_("PDF"), "btn_export_pdf"),
        ]:
            btn = QPushButton(btn_text)
            btn.setStyleSheet(get_button_secondary_stylesheet() + "QPushButton { min-width: 80px; max-width: 120px; }")
            btn.setCursor(Qt.PointingHandCursor)
            setattr(self, btn_name, btn)
            toolbar_layout.addWidget(btn)
        
        # Suchfeld - volle Breite
        self.suchfeld = QLineEdit()
        self.suchfeld.setPlaceholderText(_("🔍 Suchen..."))
        self.suchfeld.setStyleSheet(get_input_stylesheet())
        self.suchfeld.textChanged.connect(self.filter_tabelle)
        toolbar_layout.addWidget(self.suchfeld, 1)  # stretch=1 für volle Breite
        
        main_layout.addWidget(toolbar)
        
        # Content-Bereich
        content = QWidget()
        content.setStyleSheet(f"background-color: {COLORS['background']};")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.setSpacing(16)
        
        # === Showcase-Stil: 3 Statistik-Karten mit farbigen Akzentlinien ===
        import datetime
        monatsnamen = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]
        aktueller_monat = monatsnamen[datetime.date.today().month - 1]
        
        stats_row = QHBoxLayout()
        stats_row.setSpacing(16)
        
        # Einnahmen-Karte (Grün)
        self.card_einnahmen = self._create_stat_card(
            _("Einnahmen") + f" ({aktueller_monat})", 
            "CHF 0.00", 
            "#10b981"  # Grün
        )
        stats_row.addWidget(self.card_einnahmen)
        
        # Ausgaben-Karte (Rot)
        self.card_ausgaben = self._create_stat_card(
            _("Ausgaben") + f" ({aktueller_monat})", 
            "CHF 0.00", 
            "#ef4444"  # Rot
        )
        stats_row.addWidget(self.card_ausgaben)
        
        # Gewinn-Karte (Schwarz/Neutral)
        self.card_gewinn = self._create_stat_card(
            _("Gewinn") + f" ({aktueller_monat})", 
            "CHF 0.00", 
            "#1e293b"  # Dunkelgrau
        )
        stats_row.addWidget(self.card_gewinn)
        
        content_layout.addLayout(stats_row)
        
        # Tabellen-Header (ohne Karte)
        table_header = QWidget()
        table_header.setStyleSheet(f"background-color: transparent;")
        table_header_layout = QHBoxLayout(table_header)
        table_header_layout.setContentsMargins(0, 16, 0, 8)
        
        buchungen_label = QLabel(_("Buchungen"))
        buchungen_label.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            font-size: {FONT_SIZES['subtitle']}px;
            font-weight: 600;
        """)
        table_header_layout.addWidget(buchungen_label)
        table_header_layout.addStretch()
        
        export_link = QLabel(_("Exportieren"))
        export_link.setStyleSheet(f"""
            color: {COLORS['text_secondary']};
            font-size: {FONT_SIZES['body']}px;
        """)
        export_link.setCursor(Qt.PointingHandCursor)
        table_header_layout.addWidget(export_link)
        
        content_layout.addWidget(table_header)

        self.table = QTableWidget()
        self.table.setStyleSheet(get_table_stylesheet())
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        content_layout.addWidget(self.table, stretch=1)
        main_layout.addWidget(content, stretch=1)
        
        # Hidden widgets für Kompatibilität
        self.gesamtbilanz_label = QLabel()  # Versteckt, aber für Kompatibilität
        self.btn_vorschau_pdf = QPushButton(); self.btn_vorschau_pdf.hide()
        self.btn_add_invoice = QPushButton(); self.btn_add_invoice.hide()
        self.btn_open_invoice = QPushButton(); self.btn_open_invoice.hide()
        self.btn_delete_invoice = QPushButton(); self.btn_delete_invoice.hide()
        self.btn_import_excel = QPushButton(); self.btn_import_excel.hide()

        # --- Verbindungen ---
        self.btn_neu.clicked.connect(self.neuer_eintrag)
        self.btn_bearbeiten.clicked.connect(self.eintrag_bearbeiten)
        self.btn_loeschen.clicked.connect(self.eintrag_loeschen)
        self.btn_export_pdf.clicked.connect(self.export_pdf)
        self.btn_vorschau_pdf.clicked.connect(self.vorschau_pdf)
        self.btn_add_invoice.clicked.connect(self.rechnung_hinzufuegen)
        self.btn_open_invoice.clicked.connect(self.rechnung_oeffnen)
        self.btn_delete_invoice.clicked.connect(self.rechnung_loeschen)
        self.btn_import_excel.clicked.connect(self.excel_importieren)

    # NEU: Öffentliche Methode (Slot) zum Aktualisieren der Kategorien
    def aktualisiere_kategorien(self):
        """Lädt die Kategorien neu."""
        print("BuchhaltungTab: Signal 'kategorien_geaendert' empfangen. Aktualisiere Kategorien...")
        
        # Die Logik ist dieselbe wie im Konstruktor
        self.kategorien = self.lade_kategorien_aus_einstellungen()
        
    def lade_firmenname(self):
        """
        Lies 'firmenname' aus der Config-Tabelle (funktioniert für SQLite und Postgres).
        Fallback: "Meine Firma".
        """
        import json
        from db_connection import get_db

        conn = None
        try:
            conn = get_db()
            cur = conn.cursor()
            sql = "SELECT value FROM config WHERE key=%s LIMIT 1"
            try:
                cur.execute(sql, ("firmenname",))
            except Exception:
                # fallback to sqlite paramstyle
                cur.execute(sql.replace("%s", "?"), ("firmenname",))
            row = cur.fetchone()

            if not row:
                return "Meine Firma"

            # normalize row -> dict/tuple handling
            if isinstance(row, dict):
                val = row.get("value")
            elif hasattr(row, "keys"):
                try:
                    val = dict(row).get("value")
                except Exception:
                    desc = getattr(cur, "description", None)
                    if desc:
                        cols = [d[0] for d in desc]
                        val = dict(zip(cols, row)).get("value")
                    else:
                        val = row[0] if len(row) > 0 else None
            else:
                # tuple/list fallback
                val = row[0] if len(row) > 0 else None

            return val or "Meine Firma"
        except Exception:
            return "Meine Firma"
        finally:
            try:
                if conn:
                    conn.close()
            except Exception:
                pass

    def lade_kategorien_aus_einstellungen(self):
        """Liest die Kategorien aus der Datenbank."""
        kategorien = []
        try:
            daten = get_einstellungen()
            return daten.get("buchhaltungs_kategorien", [])
        except Exception:
            return []

    def neuer_eintrag(self):
        # Nächste freie Nummer aus DB holen
        with get_db() as con:
            with con.cursor() as cur:
                try:
                    cur.execute("SELECT MAX(id) FROM buchhaltung")
                    max_id = cur.fetchone()[0]
                    vorschlag_nr = str((max_id or 0) + 1)
                except Exception:
                    vorschlag_nr = ""
        dialog = BuchhaltungDialog(eintrag={"id": vorschlag_nr}, kategorien=self.kategorien)
        if dialog.exec_() == dialog.Accepted:
            self.speichere_eintrag_aus_dialog(dialog)
            # --- KORREKTUR: Langsamen Ladevorgang durch schnellen, asynchronen ersetzen ---
            self.lade_eintraege_async()

    def get_row_id(self, row_index) -> int | None:
        """Return numeric ID for given row or None if not found."""
        try:
            if row_index < 0 or row_index >= self.table.rowCount():
                return None
            # try UserRole on first cell
            it = self.table.item(row_index, 0)
            if it is not None:
                d = it.data(Qt.UserRole)
                if isinstance(d, int):
                    return d
                txt = (it.text() or "").strip()
                if txt.lstrip("-").isdigit():
                    return int(txt)
            # fallback: scan row for any numeric-looking cell
            for c in range(self.table.columnCount()):
                it = self.table.item(row_index, c)
                if it:
                    txt = (it.text() or "").strip()
                    if txt.lstrip("-").isdigit():
                        return int(txt)
        except Exception:
            pass
        return None

    def eintrag_bearbeiten(self):
        selected = self.table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, _("Keine Auswahl"), _("Bitte zuerst einen Eintrag auswählen."))
            return

        eintrag_id = self.get_row_id(selected)
        if eintrag_id is None:
            QMessageBox.warning(self, _("Fehler"), _("Kann ID der ausgewählten Zeile nicht bestimmen."))
            return

        eintrag = self.lade_eintrag_aus_db(eintrag_id)
        if not eintrag:
            QMessageBox.warning(self, _("Fehler"), _("Eintrag nicht gefunden."))
            return

        dialog = BuchhaltungDialog(eintrag=eintrag, kategorien=self.kategorien)
        if dialog.exec_() == dialog.Accepted:
            self.speichere_eintrag_aus_dialog(dialog, eintrag_id=eintrag_id)
            # --- KORREKTUR: Langsamen Ladevorgang durch schnellen, asynchronen ersetzen ---
            self.lade_eintraege_async()

    def eintrag_loeschen(self):
        selected = self.table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, _("Keine Auswahl"), _("Bitte zuerst einen Eintrag auswählen."))
            return

        eintrag_id = self.get_row_id(selected)
        if eintrag_id is None:
            QMessageBox.warning(self, _("Fehler"), _("Kann ID der ausgewählten Zeile nicht bestimmen."))
            return

        antwort = QMessageBox.question(
            self, _("Eintrag löschen"), _("Eintrag mit ID {eintrag_id} wirklich löschen?"),
            QMessageBox.Yes | QMessageBox.No
        )
        if antwort == QMessageBox.Yes:
            conn = get_db()
            cursor = conn.cursor(cursor_factory=dict_cursor_factory(conn))
            cursor.execute("DELETE FROM buchhaltung WHERE id = %s", (eintrag_id,))
            conn.commit()
            conn.close()
            # --- KORREKTUR: Langsamen Ladevorgang durch schnellen, asynchronen ersetzen ---
            self.lade_eintraege_async()

    def vorschau_pdf(self):
        if self.table.rowCount() == 0:
            QMessageBox.warning(self, _("Vorschau"), _("Keine Daten zum Anzeigen."))
            return

        from datetime import datetime
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmpfile:
            pfad_tmp = tmpfile.name

        heute = QDate.currentDate()
        von_datum = QDate(heute.year(), 1, 1).toString("dd.MM.yyyy")
        bis_datum = heute.toString("dd.MM.yyyy")
        firmenname = self.lade_firmenname()

        self.erzeuge_buchhaltungs_pdf(pfad_tmp, von_datum, bis_datum, firmenname, open_after=True)



    def export_pdf(self):
        if self.table.rowCount() == 0:
            QMessageBox.warning(self, _("Export"), _("Keine Daten zum Exportieren."))
            return

        heute = QDate.currentDate()
        von_datum = QDate(heute.year(), 1, 1).toString("dd.MM.yyyy")
        bis_datum = heute.toString("dd.MM.yyyy")
        firmenname = self.lade_firmenname()

        dateipfad, _filter = QFileDialog.getSaveFileName(self, "PDF speichern", "", "PDF Dateien (*.pdf)")
        if not dateipfad:
            return

        self.erzeuge_buchhaltungs_pdf(dateipfad, von_datum, bis_datum, firmenname, open_after=False)
        QMessageBox.information(self, _("Export"), _("PDF erfolgreich gespeichert:\n") + f"{dateipfad}")



    def erzeuge_buchhaltungs_pdf(self, pfad, von_datum, bis_datum, firmenname, open_after=False):
        from datetime import datetime

        def safe_text(text):
            return text.encode("latin-1", errors="replace").decode("latin-1")

        heute = datetime.now().strftime("%d.%m.%Y")

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        # Kopfzeile
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, safe_text(f"Buchungsauszug - {firmenname}"), ln=1, align='C')
        pdf.set_font("Arial", '', 10)
        zeile = f"Zeitraum: {von_datum} - {bis_datum}   Erstellt am: {heute}"
        pdf.cell(0, 8, safe_text(zeile), ln=1, align='C')
        pdf.ln(5)

        headers = [_("Nr"), _("Datum"), _("Typ"), _("Kategorie"), _("Betrag (CHF)"), _("Beschreibung"), _("Saldo (CHF)")]
        col_widths = [8, 20, 20, 25, 22, 73, 22]
        pdf.set_font("Arial", "B", 9)
        for i, header in enumerate(headers):
            pdf.cell(col_widths[i], 8, safe_text(header), border=1, align="C")
        pdf.ln()

        pdf.set_font("Arial", "", 9)
        saldo = 0.0
        total_einnahmen = 0.0
        total_ausgaben = 0.0

        for row in range(self.table.rowCount()):
            typ = self.table.item(row, 2).text().lower()
            betrag = float(self.table.item(row, 4).text())
            if typ == "einnahme":
                saldo += betrag
                total_einnahmen += betrag
            elif typ == "ausgabe":
                saldo -= betrag
                total_ausgaben += betrag

            beschreibung = self.table.item(row, 5).text() if self.table.item(row, 5) else ""
            beschreibung_lines = pdf.multi_cell(col_widths[5], 8, safe_text(beschreibung), border=0, align="L", split_only=True)
            num_lines = len(beschreibung_lines)
            row_height = 6 * max(1, num_lines)

            x_start = pdf.get_x()
            y_start = pdf.get_y()

            for col, width in enumerate(col_widths):
                pdf.set_xy(x_start + sum(col_widths[:col]), y_start)
                if col == 6:  # Saldo-Spalte
                    saldo_text = f"{saldo:,.2f}".replace(",", "'")
                    pdf.cell(width, row_height, saldo_text, border=1, align="R")
                elif col == 4:  # Betrag
                    betrag_text = f"{betrag:,.2f}".replace(",", "'")
                    pdf.cell(width, row_height, betrag_text, border=1, align="R")
                elif col == 5:  # Beschreibung
                    pdf.multi_cell(width, 6, safe_text(beschreibung), border=1, align="L")
                else:
                    text = self.table.item(row, col).text() if self.table.item(row, col) else ""
                    align = "C" if col == 1 else "L"
                    pdf.cell(width, row_height, safe_text(text), border=1, align=align)
            pdf.set_y(y_start + row_height)

            # Seitenumbruch?
            if pdf.get_y() > pdf.page_break_trigger - row_height:
                pdf.add_page()
                pdf.set_font("Arial", "B", 9)
                for i, header in enumerate(headers):
                    pdf.cell(col_widths[i], 8, safe_text(header), border=1, align="C")
                pdf.ln()
                pdf.set_font("Arial", "", 9)

        # Zusammenfassung
        pdf.ln(4)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 8, safe_text("Zusammenfassung"), ln=1)
        pdf.set_font("Arial", "", 9)
        pdf.cell(60, 8, safe_text("Total Einnahmen:"), align="L")
        pdf.cell(0, 8, f"{total_einnahmen:,.2f} CHF".replace(",", "'"), align="R", ln=1)
        pdf.cell(60, 8, safe_text("Total Ausgaben:"), align="L")
        pdf.cell(0, 8, f"{total_ausgaben:,.2f} CHF".replace(",", "'"), align="R", ln=1)

        pdf.cell(60, 8, safe_text("Endsaldo:"), align="L")
        if saldo < 0:
            pdf.set_text_color(200, 0, 0)
        else:
            pdf.set_text_color(0, 128, 0)
        pdf.cell(0, 8, f"{saldo:,.2f} CHF".replace(",", "'"), align="R", ln=1)
        pdf.set_text_color(0, 0, 0)

        pdf.output(pfad)

        if open_after:
            import os, subprocess
            if os.name == "nt":
                os.startfile(pfad)
            elif hasattr(os, "uname") and os.uname().sysname == "Darwin":
                subprocess.Popen(["open", pfad])
            else:
                subprocess.Popen(["xdg-open", pfad])



    def lade_eintrag_aus_db(self, eintrag_id):
        conn = get_db()
        cursor = conn.cursor(cursor_factory=dict_cursor_factory(conn))
        cursor.execute("SELECT id, datum, typ, kategorie, betrag, beschreibung FROM buchhaltung WHERE id = %s", (eintrag_id,)
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                "id": row[0],  # <- Wichtig!
                "datum": row[1],
                "typ": row[2],
                "kategorie": row[3],
                "betrag": row[4],
                "beschreibung": row[5]
            }
        return None


    def speichere_eintrag_aus_dialog(self, dialog, eintrag_id=None):
        daten = dialog.get_daten()
        try:
            betrag = float(daten["betrag"])
        except ValueError:
            betrag = 0.0

        conn = get_db()
        cursor = conn.cursor(cursor_factory=dict_cursor_factory(conn))

        # ID als int, wenn möglich
        try:
            neue_id = int(daten["id"])
        except (ValueError, TypeError):
            neue_id = None

        # sicherstellen: datum als ISO-String (YYYY-MM-DD) bevor SQL
        try:
            # konvertiere datum vor SQL
            daten["datum"] = to_db_date(daten.get("datum"))
            if eintrag_id:
                # Update - Achtung: auch ID darf geändert werden
                if neue_id is not None:
                    if _is_sqlite_conn(conn):
                        cursor.execute("""
                            UPDATE buchhaltung
                            SET id= %s, datum= %s, typ= %s, kategorie= %s, betrag= %s, beschreibung= %s
                            WHERE id= %s
                        """, (neue_id, daten["datum"], daten["typ"], daten["kategorie"], betrag, daten["beschreibung"], eintrag_id))
                    else:
                        # Postgres: ON CONFLICT bei ID-Änderung (falls nötig, aber hier ist es UPDATE)
                        cursor.execute("""
                            UPDATE public.buchhaltung
                            SET id= %s, datum= %s, typ= %s, kategorie= %s, betrag= %s, beschreibung= %s
                            WHERE id= %s
                        """, (neue_id, daten["datum"], daten["typ"], daten["kategorie"], betrag, daten["beschreibung"], eintrag_id))
                else:
                    # Falls keine gültige neue ID, kein Update der ID
                    cursor.execute("""
                        UPDATE buchhaltung
                        SET datum= %s, typ= %s, kategorie= %s, betrag= %s, beschreibung= %s
                        WHERE id= %s
                    """, (daten["datum"], daten["typ"], daten["kategorie"], betrag, daten["beschreibung"], eintrag_id))
            else:
                # Neuer Eintrag mit manueller ID oder ohne
                if neue_id is not None:
                    if _is_sqlite_conn(conn):
                        cursor.execute("""
                            INSERT OR IGNORE INTO buchhaltung (id, datum, typ, kategorie, betrag, beschreibung)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (neue_id, daten["datum"], daten["typ"], daten["kategorie"], betrag, daten["beschreibung"]))
                    else:
                        cursor.execute("""
                            INSERT INTO public.buchhaltung (id, datum, typ, kategorie, betrag, beschreibung)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            ON CONFLICT (id) DO NOTHING
                        """, (neue_id, daten["datum"], daten["typ"], daten["kategorie"], betrag, daten["beschreibung"]))
                else:
                    cursor.execute("""
                        INSERT INTO buchhaltung (datum, typ, kategorie, betrag, beschreibung)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (daten["datum"], daten["typ"], daten["kategorie"], betrag, daten["beschreibung"]))
            conn.commit()
        except sqlite3.IntegrityError:
            QMessageBox.warning(
                dialog,
                _("Fehler"),
                _("Die Nummer {id} existiert bereits!\nBitte gib eine andere ein.").format(id=daten['id'])
            )
            dialog.input_nr.setFocus()
            dialog.input_nr.selectAll()
            conn.close()
            raise  # Fehler weitergeben, damit neuer_eintrag() weiß: nochmal versuchen
        conn.close()



    def lade_eintraege(self):
        # --- HINWEIS: Diese Funktion wird jetzt nur noch selten direkt verwendet. ---
        # Der Haupt-Ladevorgang läuft über lade_eintraege_async.
        conn = get_db()
        cursor = conn.cursor(cursor_factory=dict_cursor_factory(conn))

        # backend-aware CREATE TABLE
        if _is_sqlite_conn(conn):
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS buchhaltung (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    datum TEXT,
                    typ TEXT,
                    kategorie TEXT,
                    betrag REAL,
                    beschreibung TEXT
                )
            """)
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS public.buchhaltung (
                    id SERIAL PRIMARY KEY,
                    datum TEXT,
                    typ TEXT,
                    kategorie TEXT,
                    betrag REAL,
                    beschreibung TEXT
                )
            """)

        # --- OPTIMIERUNG: N+1-Problem beheben durch JOIN ---
        query = """
            SELECT b.id, b.datum, b.typ, b.kategorie, b.betrag, b.beschreibung, 
                   (SELECT COUNT(*) FROM invoices i WHERE i.buchung_id = b.id) as invoice_count
            FROM buchhaltung b 
            ORDER BY id DESC
        """

        cursor.execute(query)
        daten = cursor.fetchall()

        self.table.setRowCount(len(daten))
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            _("Nr"), _("Datum"), _("Typ"), _("Kategorie"), _("Betrag (CHF)"), _("Beschreibung"), _("Rechnung")
        ])
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.setAlternatingRowColors(True)

        font = self.table.horizontalHeader().font()
        font.setBold(True)
        self.table.horizontalHeader().setFont(font)


        header = self.table.horizontalHeader()
        # Spalte 5 (Beschreibung) dehnt sich aus
        header.setSectionResizeMode(5, QHeaderView.Stretch)
        # Spalte 6 (Rechnung) passt sich nur dem Inhalt an
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)

        gesamt = 0.0
        
        for row_idx, row in enumerate(daten):
            # --- ANPASSUNG: Spaltenindizes haben sich durch die neue Abfrage geändert ---
            # row ist jetzt (id, datum, typ, kategorie, betrag, beschreibung, invoice_count)
            for col_idx, value in enumerate(row[:-1]): # Letzte Spalte (invoice_count) ignorieren
                if col_idx == 1:  # Datum-Spalte
                    text = normalize_date_for_display(value)
                else:
                    text = "" if value is None else str(value)
                item = QTableWidgetItem(text)
                # ...existing code...
                self.table.setItem(row_idx, col_idx, item)

            # Spalte "Rechnung" ganz am Ende hinzufügen
            invoice_count = row[6] # Letzte Spalte der neuen Abfrage
            if invoice_count > 0:
                invoice_item = QTableWidgetItem(f"✔ ({invoice_count})")
                invoice_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            else:
                invoice_item = QTableWidgetItem("")
                invoice_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_idx, 6, invoice_item)

            # Typ und Farbe
            typ = row[2].lower()
            if typ == "einnahme":
                color = QColor(230, 255, 230)
                gesamt += float(row[4])
            elif typ == "ausgabe":
                color = QColor(255, 230, 230)
                gesamt -= float(row[4])
            else:
                color = QColor(255, 255, 255)

            # JETZT für ALLE Spalten (inkl. Rechnung!) die Farbe setzen:
            for col in range(self.table.columnCount()):
                cell = self.table.item(row_idx, col)
                if cell:
                    cell.setBackground(color)

         

        conn.close()
        self.zeige_gesamtbilanz(gesamt)

    def zeige_gesamtbilanz(self, betrag):
        self.gesamtbilanz_label.setText(f"Gesamtbilanz: {betrag:.2f} CHF")
        if betrag < 0:
            self.gesamtbilanz_label.setStyleSheet("color: red; background-color: #ffe6e6;")
        else:
            self.gesamtbilanz_label.setStyleSheet("color: green; background-color: #e6ffe6;")
        
        # Aktualisiere auch die Statistik-Karten
        self._update_stat_cards()
    
    def _update_stat_cards(self):
        """Aktualisiert die Einnahmen/Ausgaben/Gewinn Karten."""
        try:
            einnahmen = 0.0
            ausgaben = 0.0
            
            for row in range(self.table.rowCount()):
                if self.table.isRowHidden(row):
                    continue
                
                # Typ-Spalte (Index 2)
                typ_item = self.table.item(row, 2)
                typ = typ_item.text() if typ_item else ""
                
                # Betrag-Spalte (Index 4)
                betrag_item = self.table.item(row, 4)
                if betrag_item:
                    try:
                        betrag_text = betrag_item.text().replace("CHF", "").replace("'", "").replace(",", ".").strip()
                        betrag = float(betrag_text)
                    except:
                        betrag = 0.0
                else:
                    betrag = 0.0
                
                if typ.lower() == "einnahme":
                    einnahmen += betrag
                elif typ.lower() == "ausgabe":
                    ausgaben += betrag
            
            gewinn = einnahmen - ausgaben
            
            # Karten aktualisieren
            if hasattr(self, 'card_einnahmen'):
                value_label = self.card_einnahmen.findChild(QLabel, "valueLabel")
                if value_label:
                    value_label.setText(f"CHF {einnahmen:,.2f}".replace(",", "'"))
            
            if hasattr(self, 'card_ausgaben'):
                value_label = self.card_ausgaben.findChild(QLabel, "valueLabel")
                if value_label:
                    value_label.setText(f"CHF {ausgaben:,.2f}".replace(",", "'"))
            
            if hasattr(self, 'card_gewinn'):
                value_label = self.card_gewinn.findChild(QLabel, "valueLabel")
                if value_label:
                    value_label.setText(f"CHF {gewinn:,.2f}".replace(",", "'"))
        except Exception as e:
            print(f"[DBG] _update_stat_cards error: {e}", flush=True)

    def filter_tabelle(self, text):
        for row in range(self.table.rowCount()):
            match = any(text.lower() in self.table.item(row, col).text().lower()
                        for col in range(self.table.columnCount())
                        if self.table.item(row, col))
            self.table.setRowHidden(row, not match)

    def rechnung_hinzufuegen(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, _("Keine Auswahl"), _("Bitte zuerst einen Eintrag auswählen."))
            return

        eintrag_id = self.get_row_id(row)
        if eintrag_id is None:
            QMessageBox.warning(self, _("Fehler"), _("Kann ID der ausgewählten Zeile nicht bestimmen."))
            return

        datum_text = self.table.item(row, 1).text() if self.table.item(row, 1) else ""
        datum_qdate = to_qdate(datum_text)
        if not datum_qdate.isValid():
            QMessageBox.warning(self, _("Fehler"), _("Ungültiges Datum: ") + datum_text)
            return

        pfad_src, _filter = QFileDialog.getOpenFileName(self, "PDF-Rechnung auswählen", "", "PDF-Dateien (*.pdf)")
        if not pfad_src:
            return

        try:
            with open(pfad_src, "rb") as f:
                data = f.read()
            filename = os.path.basename(pfad_src)
            save_invoice_db(eintrag_id, filename, data)
            QMessageBox.information(self, _("Erfolgreich"), _("Rechnung in Datenbank gespeichert: ") + filename)
            # --- KORREKTUR: Langsamen Ladevorgang durch schnellen, asynchronen ersetzen ---
            self.lade_eintraege_async()
        except Exception as e:
            QMessageBox.critical(self, _("Fehler"), _("Rechnung konnte nicht gespeichert werden:\n") + f"{e}")

    def rechnung_oeffnen(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, _("Keine Auswahl"), _("Bitte zuerst einen Eintrag auswählen."))
            return

        eintrag_id = self.get_row_id(row)
        if eintrag_id is None:
            QMessageBox.warning(self, _("Fehler"), _("Kann ID der ausgewählten Zeile nicht bestimmen."))
            return

        inv_rows = get_invoices_for_buchung(eintrag_id)
        if not inv_rows:
            QMessageBox.information(self, _("Keine Rechnung"), _("Für diesen Eintrag wurde keine Rechnung gefunden."))
            return

        invoice_id = inv_rows[0][0]
        inv = get_invoice_bytes(invoice_id)
        if not inv:
            QMessageBox.critical(self, _("Fehler"), _("Rechnung konnte nicht geladen werden."))
            return

        try:
            tmpf = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
            tmpf.write(inv["data"])
            tmpf.flush()
            tmpf.close()
            from PyQt5.QtCore import QUrl
            from PyQt5.QtGui import QDesktopServices
            QDesktopServices.openUrl(QUrl.fromLocalFile(tmpf.name))
        except Exception as e:
            QMessageBox.critical(self, _("Fehler"), _("Rechnung konnte nicht geöffnet werden:\n") + f"{e}")

    def rechnung_loeschen(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, _("Keine Auswahl"), _("Bitte zuerst einen Eintrag auswählen."))
            return

        eintrag_id = self.get_row_id(row)
        if eintrag_id is None:
            QMessageBox.warning(self, _("Fehler"), _("Kann ID der ausgewählten Zeile nicht bestimmen."))
            return

        antwort = QMessageBox.question(
            self, "Rechnung löschen",
            "Alle in der Datenbank zu dieser Buchung gespeicherten Rechnungen löschen?",
            QMessageBox.Yes | QMessageBox.No
        )
        if antwort != QMessageBox.Yes:
            return

        try:
            delete_invoices_for_buchung(eintrag_id)
            QMessageBox.information(self, _("Erfolgreich"), _("Rechnung(en) in der Datenbank erfolgreich gelöscht."))
            # --- KORREKTUR: Langsamen Ladevorgang durch schnellen, asynchronen ersetzen ---
            self.lade_eintraege_async()
        except Exception as e:
            QMessageBox.critical(self, _("Fehler"), _("Rechnung(en) konnten nicht gelöscht werden:\n") + f"{e}")

    def excel_importieren(self):
        excel_path, _filter = QFileDialog.getOpenFileName(self, "Excel auswählen", "", "Excel-Dateien (*.xlsx *.xls)")
        if not excel_path:
            return
        # ALT: db_path = "db/datenbank.sqlite"
        # NEU: Immer zentralen Pfad verwenden
        db_path = str(local_db_path())
        df = pd.read_excel(excel_path, sheet_name=0, header=None)

        # Finde erste Zeile mit Zahl in Spalte 0
        for start_row in range(len(df)):
            val = df.iloc[start_row, 0]
            if pd.notnull(val) and str(val).strip().isdigit():
                break
        else:
            QMessageBox.critical(self, _("Fehler"), _("Keine Buchungszeile with Belegnummer gefunden!"))
            return

        daten = df.iloc[start_row:].copy().reset_index(drop=True)
        daten.columns = [
            "Belegnr", "Datum", "Einnahme", "Ausgabe", "Bemerkung", "Quittung", "Postkonto", "Offene Aufträge"
        ]
        daten = daten[daten["Belegnr"].notnull() & daten["Belegnr"].apply(lambda x: str(x).strip().isdigit())]

        conn = get_db()
        cursor = conn.cursor(cursor_factory=dict_cursor_factory(conn))

        # backend-aware CREATE TABLE
        if _is_sqlite_conn(conn):
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS buchhaltung (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    datum TEXT,
                    typ TEXT,
                    kategorie TEXT,
                    betrag REAL,
                    beschreibung TEXT
                )
            """)
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS public.buchhaltung (
                    id SERIAL PRIMARY KEY,
                    datum TEXT,
                    typ TEXT,
                    kategorie TEXT,
                    betrag REAL,
                    beschreibung TEXT
                )
            """)

        def parse_datum(val):
            import datetime
            if pd.isnull(val) or str(val).strip() == "":
                return ""
            if isinstance(val, (float, int)):
                return pd.to_datetime(val, unit='d', origin='1899-12-30').strftime("%Y-%m-%d")
            s = str(val).strip()
            for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"):
                try:
                    return datetime.datetime.strptime(s, fmt).strftime("%Y-%m-%d")
                except:
                    continue
            try:
                return pd.to_datetime(s).strftime("%Y-%m-%d")
            except:
                return ""


        for index, row in df.iterrows():
            belegnr = int(row["Belegnr"])
            datum = parse_datum(row["Datum"])
            einnahme = row["Einnahme"] if pd.notnull(row["Einnahme"]) else 0
            ausgabe = row["Ausgabe"] if pd.notnull(row["Ausgabe"]) else 0
            bemerkung = str(row["Bemerkung"]) if pd.notnull(row["Bemerkung"]) else ""
            typ = "Einnahme" if einnahme and float(str(einnahme).replace("’", "").replace(" CHF", "").replace("'", "").replace(",", ".")) > 0 else "Ausgabe"
            betrag = float(str(einnahme if typ == "Einnahme" else ausgabe)
                           .replace("’", "")
                           .replace(" CHF", "")
                           .replace("'", "")
                           .replace(",", ".") or 0)

            if _is_sqlite_conn(conn):
                cursor.execute(
                    "INSERT OR IGNORE INTO buchhaltung (id, datum, typ, kategorie, betrag, beschreibung) VALUES (%s, %s, %s, %s, %s, %s)",
                    (belegnr, datum, typ, "Sonstiges", betrag, bemerkung)
                )
            else:
                cursor.execute(
                    "INSERT INTO public.buchhaltung (id, datum, typ, kategorie, betrag, beschreibung) "
                    "VALUES (%s, %s, %s, %s, %s, %s) "
                    "ON CONFLICT (id) DO NOTHING",
                    (belegnr, datum, typ, "Sonstiges", betrag, bemerkung)
                )

        conn.commit()
        conn.close()
        QMessageBox.information(self, _("Fertig"), _("{} Buchungen importiert!").format(len(daten)))
        # --- KORREKTUR: Langsamen Ladevorgang durch schnellen, asynchronen ersetzen ---
        self.lade_eintraege_async()

    def append_rows(self, rows):
        """Append a chunk of rows (dicts or sequences) into QTableWidget with fixed column order and coloring."""
        # --- NEU: Logik zum Sammeln der initialen Daten ---
        # Wenn der Filter-Prozess aktiv ist (erkennbar an _temp_filtered_rows),
        # soll diese Funktion nichts tun, da die Daten dort gesammelt werden.
        if hasattr(self, '_temp_filtered_rows') and self._temp_filtered_rows is not None:
             # Wenn display_collected_rows aufgerufen wird, ist die Liste nicht mehr None
            if rows == self._temp_filtered_rows:
                pass # Fortfahren, da dies der beabsichtigte Aufruf ist
            else:
                return # Ignorieren, da der Filter-Prozess die Kontrolle hat

        # Wenn es der initiale Ladevorgang ist, Daten sammeln
        elif hasattr(self, '_initial_load_rows') and self._initial_load_rows is not None:
            self._initial_load_rows.extend(rows)
            return # Noch nicht anzeigen, nur sammeln

        # --- Ab hier beginnt die eigentliche Anzeige-Logik ---
        try:
            if not rows:
                return

            # --- KORREKTUR: Spaltenliste an die SQL-Abfrage anpassen ---
            expected_cols = ["id", "datum", "typ", "kategorie", "betrag", "beschreibung", "invoice_count"]
            headers = [_("Nr"), _("Datum"), _("Typ"), _("Kategorie"), _("Betrag (CHF)"), _("Beschreibung"), _("Rechnung")]

            if self.table.columnCount() == 0:
                self.table.setColumnCount(len(headers))
                self.table.setHorizontalHeaderLabels(headers)
                self.table.verticalHeader().setVisible(False)
                header = self.table.horizontalHeader()
                header.setSectionResizeMode(5, QHeaderView.Stretch)
                header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
                self.table.setAlternatingRowColors(True)

            # suspend updates for speed
            try:
                self.table.setSortingEnabled(False)
                self.table.setUpdatesEnabled(False)
            except Exception:
                pass

            # Data is already sorted by SQL (ORDER BY id DESC).
            # We just need to append it to the end of the table.
            try:
                for r in rows:  # <-- KEIN reversed()
                    if isinstance(r, dict):
                        values = [r.get(c, "") for c in expected_cols]
                    else:
                        # --- KORREKTUR: Die gesamte Zeile verwenden ---
                        values = list(r)
                        while len(values) < len(expected_cols):
                            values.append("")

                    # ensure id_text and numeric id
                    id_val = values[0]
                    id_text = "" if id_val is None else str(id_val)
                    try:
                        numeric_id = int(id_val) if (isinstance(id_val, int) or (isinstance(id_val, str) and id_text.lstrip("-").isdigit())) else None
                    except Exception:
                        numeric_id = None

                    # Append row at the END of the table
                    row_position = self.table.rowCount()
                    self.table.insertRow(row_position)
                    
                    # --- KORREKTUR: Nur die ersten 6 Spalten durchlaufen ---
                    for col_idx, val in enumerate(values[:-1]):
                        if col_idx == 1:
                            text = normalize_date_for_display(val)
                        elif col_idx == 4:
                            try:
                                text = f"{float(val):.2f}"
                            except Exception:
                                text = "" if val is None else str(val)
                        else:
                            text = "" if val is None else str(val)
                        
                        if col_idx == 0:
                            item = QTableWidgetItem(id_text)
                            if numeric_id is not None:
                                try:
                                    item.setData(Qt.UserRole, numeric_id)
                                except Exception:
                                    pass
                        else:
                            item = QTableWidgetItem(text)
                        self.table.setItem(row_position, col_idx, item)

                    # --- KORREKTUR: invoice_count auswerten und in die letzte Spalte schreiben ---
                    invoice_count = values[6] if len(values) > 6 and values[6] else 0
                    invoice_col = self.table.columnCount() - 1
                    
                    if invoice_count > 0:
                        inv_item = QTableWidgetItem(f"✔ ({invoice_count})")
                        inv_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
                    else:
                        inv_item = QTableWidgetItem("")
                        inv_item.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(row_position, invoice_col, inv_item)


                    # apply color by typ (column index 2)
                    try:
                        typ_text = (values[2] or "").strip().lower()
                        if typ_text == "einnahme":
                            color = QColor(230, 255, 230)
                        elif typ_text == "ausgabe":
                            color = QColor(255, 230, 230)
                        else:
                            color = QColor(255, 255, 255)
                        for c in range(self.table.columnCount()):
                            it = self.table.item(row_position, c)
                            if it:
                                it.setBackground(color)
                    except Exception:
                        pass

            except Exception:
                # fallback: append if insert fails for any reason
                start_row = self.table.rowCount()
                self.table.setRowCount(start_row + len(rows))
                for r_idx, r in enumerate(rows):
                    rownum = start_row + r_idx
                    if isinstance(r, dict):
                        values = [r.get(c, "") for c in expected_cols]
                    else:
                        seq = list(r)
                        while len(seq) < len(expected_cols):
                            seq.append("")
                        values = seq[:len(expected_cols)]

                    id_val = values[0]
                    id_text = "" if id_val is None else str(id_val)
                    try:
                        numeric_id = int(id_val) if (isinstance(id_val, int) or (isinstance(id_val, str) and id_text.lstrip("-").isdigit())) else None
                    except Exception:
                        numeric_id = None

                    for col_idx, val in enumerate(values):
                        if col_idx == 1:
                            text = normalize_date_for_display(val)
                        elif col_idx == 4:
                            try:
                                text = f"{float(val):.2f}"
                            except Exception:
                                text = "" if val is None else str(val)
                        else:
                            text = "" if val is None else str(val)

                        if col_idx == 0:
                            item = QTableWidgetItem(id_text)
                            if numeric_id is not None:
                                try:
                                    item.setData(Qt.UserRole, numeric_id)
                                except Exception:
                                    pass
                        else:
                            item = QTableWidgetItem(text)
                        self.table.setItem(rownum, col_idx, item)

                    # invoice column (last)
                    invoice_col = self.table.columnCount() - 1
                    inv_item = QTableWidgetItem("")
                    inv_item.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(rownum, invoice_col, inv_item)

            # restore updates and do a single resize for visible columns
            try:
                self.table.setUpdatesEnabled(True)
                self.table.setSortingEnabled(True)
                self.table.sortItems(0, Qt.DescendingOrder)
                self.table.resizeColumnsToContents()
            except Exception:
                pass

            # update Gesamtbilanz based on current table contents
            try:
                self._recalc_gesamtbilanz_from_table()
            except Exception:
                pass

        except Exception as e:
            print(f"[DBG] BuchhaltungTab.append_rows error: {e}", flush=True)

    def load_finished(self):
        """Call when loader finished. Show 'Keine Einträge' if nothing loaded."""
        # --- NEU: Gesammelte initiale Daten jetzt anzeigen ---
        if hasattr(self, '_initial_load_rows') and self._initial_load_rows is not None:
            # Rufe append_rows mit den gesammelten Daten auf und setze die Sammelliste auf None,
            # um den Sammel-Modus zu beenden und die Anzeige zu erlauben.
            collected_rows = self._initial_load_rows
            self._initial_load_rows = None # WICHTIG: Sammelmodus beenden
            self.append_rows(collected_rows)



        # ensure Gesamtbilanz is up-to-date when loading finished
        try:
            self._recalc_gesamtbilanz_from_table()
        except Exception:
            pass

    def _recalc_gesamtbilanz_from_table(self):
        """Recalculate the total balance from table rows and update the label."""
        try:
            gesamt = 0.0
            for row in range(self.table.rowCount()):
                typ_it = self.table.item(row, 2)
                betrag_it = self.table.item(row, 4)
                if betrag_it is None:
                    continue
                txt = betrag_it.text().strip()
                if not txt:
                    continue
                # normalize number: allow commas/apostrophes
                norm = txt.replace("'", "").replace("’", "").replace(" ", "").replace(",", ".")
                try:
                    wert = float(norm)
                except Exception:
                    continue
                typ = (typ_it.text().strip().lower() if typ_it else "")
                if typ == "einnahme":
                    gesamt += wert
                elif typ == "ausgabe":
                    gesamt -= wert
            self.zeige_gesamtbilanz(gesamt)
        except Exception as e:
            print(f"[DBG] _recalc_gesamtbilanz_from_table error: {e}", flush=True)

    def append_row(self, row):
        """Compat wrapper: single-row convenience."""
        try:
            if row is None:
                return
            self.append_rows([row])
        except Exception as e:
            print(f"[DBG] BuchhaltungTab.append_row error: {e}", flush=True)

    def lade_eintraege_async(self):
        """Lädt alle Einträge asynchron (non-blocking)."""
        try:
            # Clear table
            self.table.setRowCount(0)
            
            # --- NEU: Temporäre Liste zum Sammeln ---
            self._temp_filtered_rows = []

            # --- OPTIMIERUNG: N+1-Problem beheben durch JOIN ---
            query = """
                SELECT b.id, b.datum, b.typ, b.kategorie, b.betrag, b.beschreibung,
                       (SELECT COUNT(*) FROM invoices i WHERE i.buchung_id = b.id) as invoice_count
                FROM buchhaltung b
                ORDER BY id DESC
            """

            # Start async loader
            from gui.tab_loader import TabLoader
            from PyQt5.QtCore import QThread

            loader = TabLoader(
                key="buchhaltung_all",
                query=query,
                params=[],
                chunk_size=100
            )
            thread = QThread()
            loader.moveToThread(thread)

            # --- NEU: An temporäre Liste anhängen ---
            loader.chunk_ready.connect(lambda key, chunk: self._temp_filtered_rows.extend(chunk))
            loader.finished.connect(self.display_collected_rows)
            loader.error.connect(lambda k, msg: QMessageBox.critical(self, _("Fehler"), _("Ladefehler:\n") + f"{msg}"))

            thread.started.connect(loader.run)
            thread.start()

            # Keep thread reference (cleanup on finished)
            if not hasattr(self, "_filter_threads"):
                self._filter_threads = []
            # Clean up old threads
            self._filter_threads = [(t, l) for t, l in self._filter_threads if t.isRunning()]
            self._filter_threads.append((thread, loader))

        except Exception as e:
            print(f"[DBG] lade_eintraege_async error: {e}", flush=True)
            QMessageBox.critical(self, _("Fehler"), _("Daten konnten nicht geladen werden:\n") + f"{e}")

    def display_collected_rows(self):
        """NEU: Diese Funktion wird aufgerufen, wenn ALLE Chunks geladen sind."""
        # Rufe append_rows mit der kompletten, sortierten Liste auf
        collected_rows = self._temp_filtered_rows
        self._temp_filtered_rows = collected_rows # Setze es auf sich selbst, damit append_rows es erkennt
        self.append_rows(collected_rows)
        self.load_finished() # Rufe finished manuell auf
        self._temp_filtered_rows = None # Speicher leeren und Filter-Modus beenden













