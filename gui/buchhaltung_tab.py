# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QLineEdit, QFileDialog, QComboBox, QLabel, QDateEdit, QAbstractItemView, QToolButton,
    QHeaderView  # <-- fehlte
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QColor, QFont, QStandardItemModel, QStandardItem, QIcon
from fpdf import FPDF
from db_connection import get_db, dict_cursor_factory, get_einstellungen, get_config_value
from paths import data_dir, local_db_path  # <-- fehlte
import pandas as pd
import datetime
import os, shutil, glob  # <-- fehlten
import sqlite3  # <-- fehlte
from gui.buchhaltung_dialog import BuchhaltungDialog
import hashlib, tempfile
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
        # blocking initial load - REMOVE or comment out
        # self.lade_eintraege()

    def init_ui(self):
        main_layout = QHBoxLayout()
        left_layout = QVBoxLayout()

        self.kategorien = self.lade_kategorien_aus_einstellungen()

        self.suchfeld = QLineEdit()
        self.suchfeld.setPlaceholderText("Suchen...")
        self.suchfeld.textChanged.connect(self.filter_tabelle)
        left_layout.addWidget(self.suchfeld)

        filter_layout = QHBoxLayout()

        self.filter_typ = QComboBox()
        self.filter_typ.addItems(["Alle", "Einnahme", "Ausgabe"])
        filter_layout.addWidget(QLabel("Typ:"))
        filter_layout.addWidget(self.filter_typ)

        self.filter_kategorie = QComboBox()
        self.filter_kategorie.addItem("Alle")
        self.filter_kategorie.addItems(self.kategorien)
        filter_layout.addWidget(QLabel("Kategorie:"))
        filter_layout.addWidget(self.filter_kategorie)

        self.filter_von = QDateEdit()
        self.filter_von.setCalendarPopup(True)
        heute = QDate.currentDate()
        self.filter_von.setDate(QDate(heute.year(), 1, 1))
        filter_layout.addWidget(QLabel("Von:"))
        filter_layout.addWidget(self.filter_von)

        self.filter_bis = QDateEdit()
        self.filter_bis.setCalendarPopup(True)
        self.filter_bis.setDate(QDate.currentDate())
        filter_layout.addWidget(QLabel("Bis:"))
        filter_layout.addWidget(self.filter_bis)

        self.btn_filter = QPushButton("Filter anwenden")


        self.btn_filter.clicked.connect(self.lade_eintraege)
        filter_layout.addWidget(self.btn_filter)

        left_layout.addLayout(filter_layout)

        self.table = QTableWidget()
        self.table.setStyleSheet("""
            QTableWidget {
                gridline-color: #bfc6d1;
            }
        """)


        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode    (QAbstractItemView.SingleSelection)
        self.gesamtbilanz_label = QPushButton("Gesamtbilanz: 0.00 CHF")
        self.gesamtbilanz_label.setEnabled(False)
        self.gesamtbilanz_label.setMinimumHeight(40)
        self.gesamtbilanz_label.setFont(QFont("Arial", 14, QFont.Bold))

        left_layout.addWidget(self.table)
        main_layout.addLayout(left_layout, 3)


        button_layout = QVBoxLayout()

        # --- Buttons als Instanzattribute (QToolButton) + Rollen für Icons ---
        self.btn_neu = QToolButton()
        self.btn_neu.setText('Neuer Eintrag')
        self.btn_neu.setProperty("role", "add")

        self.btn_bearbeiten = QToolButton()
        self.btn_bearbeiten.setText('Eintrag bearbeiten')
        self.btn_bearbeiten.setProperty("role", "edit")

        self.btn_loeschen = QToolButton()
        self.btn_loeschen.setText('Eintrag löschen')
        self.btn_loeschen.setProperty("role", "delete")

        self.btn_export_pdf = QToolButton()
        self.btn_export_pdf.setText('Export PDF')
        self.btn_export_pdf.setProperty("role", "download")

        self.btn_vorschau_pdf = QToolButton()
        self.btn_vorschau_pdf.setText('Vorschau PDF')
        self.btn_vorschau_pdf.setProperty("role", "preview")

        self.btn_add_invoice = QToolButton()
        self.btn_add_invoice.setText('Rechnung hinzufügen')
        self.btn_add_invoice.setProperty("role", "add")

        self.btn_open_invoice = QToolButton()
        self.btn_open_invoice.setText('Rechnung öffnen')
        self.btn_open_invoice.setProperty("role", "preview")

        self.btn_delete_invoice = QToolButton()
        self.btn_delete_invoice.setText('Rechnung löschen')
        self.btn_delete_invoice.setProperty("role", "delete")

        self.btn_import_excel = QToolButton()
        self.btn_import_excel.setText('Excel importieren')
        self.btn_import_excel.setProperty("role", "upload")

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

        # --- Layout ---
        button_layout.addWidget(self.btn_neu)
        button_layout.addWidget(self.btn_bearbeiten)
        button_layout.addWidget(self.btn_loeschen)
        button_layout.addWidget(self.btn_add_invoice)
        button_layout.addWidget(self.btn_open_invoice)
        button_layout.addWidget(self.btn_delete_invoice)
        button_layout.addWidget(self.btn_export_pdf)
        button_layout.addWidget(self.btn_vorschau_pdf)
        # falls du den Import-Button sichtbar möchtest:
        button_layout.addWidget(self.btn_import_excel)

        
        button_layout.addStretch()
        button_layout.addWidget(self.gesamtbilanz_label)


        main_layout.addLayout(button_layout, 1)
        # loading indicator label (shown until first chunk or finished)
        self._loading_label = QLabel("Lädt... Bitte warten", self)
        self._loading_label.setObjectName("buchhaltung_loading_label")
        self._loading_label.setAlignment(Qt.AlignCenter)
        # insert the label above the table in the layout if possible
        try:
            main_layout.insertWidget(0, self._loading_label)
        except Exception:
            try:
                main_layout.addWidget(self._loading_label)
            except Exception:
                pass
        self._loading_label.show()
        self.setLayout(main_layout)
        # DO NOT load data here (blocking). Data will be loaded asynchronously.
        # self.lade_eintrage()  # <- removed to avoid UI blocking on construction

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
            self.lade_eintraege()

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
            QMessageBox.warning(self, "Keine Auswahl", "Bitte zuerst einen Eintrag auswählen.")
            return

        eintrag_id = self.get_row_id(selected)
        if eintrag_id is None:
            QMessageBox.warning(self, "Fehler", "Kann ID der ausgewählten Zeile nicht bestimmen.")
            return

        eintrag = self.lade_eintrag_aus_db(eintrag_id)
        if not eintrag:
            QMessageBox.warning(self, "Fehler", "Eintrag nicht gefunden.")
            return

        dialog = BuchhaltungDialog(eintrag=eintrag, kategorien=self.kategorien)
        if dialog.exec_() == dialog.Accepted:
            self.speichere_eintrag_aus_dialog(dialog, eintrag_id=eintrag_id)
            self.lade_eintraege()

    def eintrag_loeschen(self):
        selected = self.table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, "Keine Auswahl", "Bitte zuerst einen Eintrag auswählen.")
            return

        eintrag_id = self.get_row_id(selected)
        if eintrag_id is None:
            QMessageBox.warning(self, "Fehler", "Kann ID der ausgewählten Zeile nicht bestimmen.")
            return

        antwort = QMessageBox.question(
            self, "Eintrag löschen", f"Eintrag mit ID {eintrag_id} wirklich löschen?",
            QMessageBox.Yes | QMessageBox.No
        )
        if antwort == QMessageBox.Yes:
            conn = get_db()
            cursor = conn.cursor(cursor_factory=dict_cursor_factory(conn))
            cursor.execute("DELETE FROM buchhaltung WHERE id = %s", (eintrag_id,))
            conn.commit()
            conn.close()
            self.lade_eintraege()

    def vorschau_pdf(self):
        if self.table.rowCount() == 0:
            QMessageBox.warning(self, "Vorschau", "Keine Daten zum Anzeigen.")
            return

        from datetime import datetime
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmpfile:
            pfad_tmp = tmpfile.name

        von_datum = self.filter_von.date().toString("dd.MM.yyyy")
        bis_datum = self.filter_bis.date().toString("dd.MM.yyyy")
        firmenname = self.lade_firmenname()

        self.erzeuge_buchhaltungs_pdf(pfad_tmp, von_datum, bis_datum, firmenname, open_after=True)



    def export_pdf(self):
        if self.table.rowCount() == 0:
            QMessageBox.warning(self, "Export", "Keine Daten zum Exportieren.")
            return

        von_datum = self.filter_von.date().toString("dd.MM.yyyy")
        bis_datum = self.filter_bis.date().toString("dd.MM.yyyy")
        firmenname = self.lade_firmenname()

        dateipfad, _ = QFileDialog.getSaveFileName(self, "PDF speichern", "", "PDF Dateien (*.pdf)")
        if not dateipfad:
            return

        self.erzeuge_buchhaltungs_pdf(dateipfad, von_datum, bis_datum, firmenname, open_after=False)
        QMessageBox.information(self, "Export", f"PDF erfolgreich gespeichert:\n{dateipfad}")



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

        headers = ["Nr", "Datum", "Typ", "Kategorie", "Betrag (CHF)", "Beschreibung", "Saldo (CHF)"]
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
                "Fehler",
                f"Die Nummer {daten['id']} existiert bereits!\nBitte gib eine andere ein."
            )
            dialog.input_nr.setFocus()
            dialog.input_nr.selectAll()
            conn.close()
            raise  # Fehler weitergeben, damit neuer_eintrag() weiß: nochmal versuchen
        conn.close()



    def lade_eintraege(self):
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

        query = "SELECT id, datum, typ, kategorie, betrag, beschreibung FROM buchhaltung WHERE 1=1"
        params = []

        typ = self.filter_typ.currentText()
        if typ != "Alle":
            query += " AND typ = %s"
            params.append(typ)

        kategorie = self.filter_kategorie.currentText()
        if kategorie != "Alle":
            query += " AND kategorie = %s"
            params.append(kategorie)

        von = self.filter_von.date().toString("yyyy-MM-dd")
        bis = self.filter_bis.date().toString("yyyy-MM-dd")
        query += " AND datum BETWEEN %s AND %s"
        params.extend([von, bis])

        query += " ORDER BY id DESC"


        cursor.execute(query, params)
        daten = cursor.fetchall()

        self.table.setRowCount(len(daten))
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Nr", "Datum", "Typ", "Kategorie", "Betrag (CHF)", "Beschreibung", "Rechnung"
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
            for col_idx, value in enumerate(row):
                if col_idx == 1:  # Datum-Spalte
                    text = normalize_date_for_display(value)
                else:
                    text = "" if value is None else str(value)
                item = QTableWidgetItem(text)
                # ...existing code...
                self.table.setItem(row_idx, col_idx, item)

            # Spalte "Rechnung" ganz am Ende hinzufügen
            eintrag_id = row[0]
            inv_rows = get_invoices_for_buchung(eintrag_id)
            if inv_rows:
                names = [r[1] for r in inv_rows]
                invoice_item = QTableWidgetItem(f"✔ {names[0]}")
                invoice_item.setToolTip("\n".join(names))
                invoice_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
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

    def filter_tabelle(self, text):
        for row in range(self.table.rowCount()):
            match = any(text.lower() in self.table.item(row, col).text().lower()
                        for col in range(self.table.columnCount())
                        if self.table.item(row, col))
            self.table.setRowHidden(row, not match)

    def rechnung_hinzufuegen(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Keine Auswahl", "Bitte zuerst einen Eintrag auswählen.")
            return

        eintrag_id = self.get_row_id(row)
        if eintrag_id is None:
            QMessageBox.warning(self, "Fehler", "Kann ID der ausgewählten Zeile nicht bestimmen.")
            return

        datum_text = self.table.item(row, 1).text() if self.table.item(row, 1) else ""
        datum_qdate = to_qdate(datum_text)
        if not datum_qdate.isValid():
            QMessageBox.warning(self, "Fehler", f"Ungültiges Datum: {datum_text}")
            return

        pfad_src, _ = QFileDialog.getOpenFileName(self, "PDF-Rechnung auswählen", "", "PDF-Dateien (*.pdf)")
        if not pfad_src:
            return

        try:
            with open(pfad_src, "rb") as f:
                data = f.read()
            filename = os.path.basename(pfad_src)
            save_invoice_db(eintrag_id, filename, data)
            QMessageBox.information(self, "Erfolgreich", f"Rechnung in Datenbank gespeichert: {filename}")
            self.lade_eintraege()
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Rechnung konnte nicht gespeichert werden:\n{e}")

    def rechnung_oeffnen(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Keine Auswahl", "Bitte zuerst einen Eintrag auswählen.")
            return

        eintrag_id = self.get_row_id(row)
        if eintrag_id is None:
            QMessageBox.warning(self, "Fehler", "Kann ID der ausgewählten Zeile nicht bestimmen.")
            return

        inv_rows = get_invoices_for_buchung(eintrag_id)
        if not inv_rows:
            QMessageBox.information(self, "Keine Rechnung", "Für diesen Eintrag wurde keine Rechnung gefunden.")
            return

        invoice_id = inv_rows[0][0]
        inv = get_invoice_bytes(invoice_id)
        if not inv:
            QMessageBox.critical(self, "Fehler", "Rechnung konnte nicht geladen werden.")
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
            QMessageBox.critical(self, "Fehler", f"Rechnung konnte nicht geöffnet werden:\n{e}")

    def rechnung_loeschen(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Keine Auswahl", "Bitte zuerst einen Eintrag auswählen.")
            return

        eintrag_id = self.get_row_id(row)
        if eintrag_id is None:
            QMessageBox.warning(self, "Fehler", "Kann ID der ausgewählten Zeile nicht bestimmen.")
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
            QMessageBox.information(self, "Erfolgreich", "Rechnung(en) in der Datenbank erfolgreich gelöscht.")
            self.lade_eintraege()
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Rechnung(en) konnten nicht gelöscht werden:\n{e}")

    def excel_importieren(self):
        excel_path, _ = QFileDialog.getOpenFileName(self, "Excel auswählen", "", "Excel-Dateien (*.xlsx *.xls)")
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
            QMessageBox.critical(self, "Fehler", "Keine Buchungszeile with Belegnummer gefunden!")
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
        QMessageBox.information(self, "Fertig", f"{len(daten)} Buchungen importiert!")
        self.lade_eintraege()

    def append_rows(self, rows):
        """Append a chunk of rows (dicts or sequences) into QTableWidget with fixed column order and coloring."""
        try:
            if not rows:
                return

            # hide loading label once data arrives
            try:
                if hasattr(self, "_loading_label") and self._loading_label.isVisible():
                    self._loading_label.hide()
            except Exception:
                pass

            expected_cols = ["id", "datum", "typ", "kategorie", "betrag", "beschreibung"]
            headers = ["Nr", "Datum", "Typ", "Kategorie", "Betrag (CHF)", "Beschreibung", "Rechnung"]

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

            # Insert newest entries at the top.
            try:
                for r in reversed(rows):
                    if isinstance(r, dict):
                        values = [r.get(c, "") for c in expected_cols]
                    else:
                        seq = list(r)
                        if len(seq) >= len(expected_cols):
                            values = seq[:len(expected_cols)]
                        else:
                            while len(seq) < len(expected_cols):
                                seq.append("")
                            values = seq[:len(expected_cols)]

                    # ensure id_text and numeric id
                    id_val = values[0]
                    id_text = "" if id_val is None else str(id_val)
                    try:
                        numeric_id = int(id_val) if (isinstance(id_val, int) or (isinstance(id_val, str) and id_text.lstrip("-").isdigit())) else None
                    except Exception:
                        numeric_id = None

                    # insert a new top row
                    self.table.insertRow(0)
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
                        # For the ID column, force the id_text (so column 0 always contains the id text)
                        if col_idx == 0:
                            item = QTableWidgetItem(id_text)
                            if numeric_id is not None:
                                try:
                                    item.setData(Qt.UserRole, numeric_id)
                                except Exception:
                                    pass
                        else:
                            item = QTableWidgetItem(text)
                        self.table.setItem(0, col_idx, item)

                    # invoice column (last)
                    invoice_col = self.table.columnCount() - 1
                    inv_item = QTableWidgetItem("")
                    inv_item.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(0, invoice_col, inv_item)

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
                            it = self.table.item(0, c)
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
        try:
            if self.table.rowCount() == 0:
                try:
                    if hasattr(self, "_loading_label"):
                        self._loading_label.setText("Keine Einträge")
                        self._loading_label.show()
                except Exception:
                    pass
            else:
                try:
                    if hasattr(self, "_loading_label"):
                        self._loading_label.hide()
                except Exception:
                    pass
        except Exception as e:
            print(f"[DBG] BuchhaltungTab.load_finished error: {e}", flush=True)

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













