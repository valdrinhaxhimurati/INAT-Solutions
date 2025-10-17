from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QLineEdit, QFileDialog, QComboBox, QLabel, QDateEdit, QAbstractItemView, QToolButton  
)
from db_connection import get_db, dict_cursor_factory
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QColor, QFont
import sqlite3
import json
import os
from gui.buchhaltung_dialog import BuchhaltungDialog
from fpdf import FPDF
import tempfile
import subprocess
from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QDesktopServices
import glob
import shutil
from PyQt5.QtWidgets import QHeaderView
from paths import local_db_path, data_dir

import pandas as pd


class BuchhaltungTab(QWidget):
    def __init__(self):
        super().__init__()
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
        self.setLayout(main_layout)

        self.lade_eintraege()


    def lade_firmenname(self):
        config_path = "config.json"
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    return config.get("firmenname", "Meine Firma")
            except (json.JSONDecodeError, IOError):
                return "Meine Firma"
        return "Meine Firma"

    def lade_kategorien_aus_einstellungen(self):
        pfad = "config/einstellungen.json"
        if not os.path.exists(pfad):
            return ["Sonstiges"]
        try:
            with open(pfad, "r") as f:
                daten = json.load(f)
            kategorien = daten.get("buchhaltungs_kategorien", [])
            return kategorien if kategorien else ["Sonstiges"]
        except Exception:
            return ["Sonstiges"]

    def neuer_eintrag(self):
        while True:
            dialog = BuchhaltungDialog(kategorien=self.kategorien)
            if dialog.exec_() == dialog.Accepted:
                try:
                    self.speichere_eintrag_aus_dialog(dialog)
                    self.lade_eintraege()
                    break  # Erfolg -> Schleife verlassen
                except sqlite3.IntegrityError:
                    # Der Fehler wird im Dialog schon gemeldet!
                    pass
            else:
                break  


    def eintrag_bearbeiten(self):
        selected = self.table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, "Keine Auswahl", "Bitte zuerst einen Eintrag auswählen.")
            return

        eintrag_id = int(self.table.item(selected, 0).text())
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

        eintrag_id = int(self.table.item(selected, 0).text())
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

        try:
            if eintrag_id:
                # Update - Achtung: auch ID darf geändert werden
                if neue_id is not None:
                    cursor.execute("""
                        UPDATE buchhaltung
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
                    cursor.execute("""
                        INSERT INTO buchhaltung (id, datum, typ, kategorie, betrag, beschreibung)
                        VALUES (%s, %s, %s, %s, %s, %s)
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

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS buchhaltung (
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
                item = QTableWidgetItem(str(value))
                # ... Alignment setzen ...
                self.table.setItem(row_idx, col_idx, item)

            # Spalte "Rechnung" ganz am Ende hinzufügen
            eintrag_id = row[0]
            pattern = os.path.join("rechnungen", "*", f"{eintrag_id}_*.pdf")
            has_invoice = bool(glob.glob(pattern))
            invoice_item = QTableWidgetItem("✔" if has_invoice else "")
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
        # 1) Prüfen, ob eine Zeile ausgewählt ist
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Keine Auswahl", "Bitte zuerst einen Eintrag auswählen.")
            return

        # 2) Eintrags-ID und Datum auslesen
        eintrag_id = int(self.table.item(row, 0).text())
        datum_text = self.table.item(row, 1).text()  
        
        # QDate zum Year-String
        datum_qdate = QDate.fromString(datum_text, "yyyy-MM-dd")
        if not datum_qdate.isValid():
            QMessageBox.warning(self, "Fehler", f"Ungültiges Datum: {datum_text}")
            return
        jahr = datum_qdate.toString("yyyy")

        # 3) PDF-Datei auswählen
        pfad_src, _ = QFileDialog.getOpenFileName(self, "PDF-Rechnung auswählen", "", "PDF-Dateien (*.pdf)")
        if not pfad_src:
            return

        # 4) Zielordner und -datei bestimmen
        # ALT: ordner_ziel = os.path.join("rechnungen", jahr)
        # NEU: Zielordner unter ProgramData/data/rechnungen/Jahr
        ordner_ziel = str(data_dir() / "rechnungen" / jahr)
        os.makedirs(ordner_ziel, exist_ok=True)

        dateiname_orig = os.path.basename(pfad_src)
        dateiname_neu = f"{eintrag_id}_{dateiname_orig}"
        pfad_dst = os.path.join(ordner_ziel, dateiname_neu)

        # 5) Datei kopieren
        try:
            shutil.copyfile(pfad_src, pfad_dst)
            QMessageBox.information(self, "Erfolgreich", f"Rechnung gespeichert unter:\n{pfad_dst}")
            self.lade_eintraege()
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Rechnung konnte nicht gespeichert werden:\n{e}")

    def rechnung_oeffnen(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Keine Auswahl", "Bitte zuerst einen Eintrag auswählen.")
            return

        eintrag_id = int(self.table.item(row, 0).text())
        # nach allen PDFs suchen, die mit "<ID>_" anfangen
        # ALT: pattern = os.path.join("rechnungen", "*", f"{eintrag_id}_*.pdf")
        # NEU:
        pattern = str(data_dir() / "rechnungen" / "*" / f"{eintrag_id}_*.pdf")
        treffer = glob.glob(pattern)
        if not treffer:
            QMessageBox.information(self, "Keine Rechnung", "Für diesen Eintrag wurde keine Rechnung gefunden.")
            return

        # nimm die erste gefundene Datei (falls es mehrere sind)
        pfad = treffer[0]
        # im Standard-PDF-Viewer öffnen
        from PyQt5.QtCore import QUrl
        from PyQt5.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl.fromLocalFile(pfad))

    def rechnung_loeschen(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Keine Auswahl", "Bitte zuerst einen Eintrag auswählen.")
            return

        eintrag_id = int(self.table.item(row, 0).text())
        # Suche alle zugehörigen PDFs
        pattern = str(data_dir() / "rechnungen" / "*" / f"{eintrag_id}_*.pdf")
        files = glob.glob(pattern)
        if not files:
            QMessageBox.information(self, "Keine Rechnung", "Für diesen Eintrag wurde keine Rechnung gefunden.")
            return

        # Bestätigung
        antwort = QMessageBox.question(
            self, "Rechnung löschen",
            f"{len(files)} Datei(en) löschen?\n\n" + "\n".join(os.path.basename(f) for f in files),
            QMessageBox.Yes | QMessageBox.No
        )
        if antwort != QMessageBox.Yes:
            return

        # Löschen
        errors = []
        for f in files:
            try:
                os.remove(f)
            except Exception as e:
                errors.append((f, str(e)))

        if errors:
            text = "Nicht alle Dateien konnten gelöscht werden:\n" + "\n".join(f"{os.path.basename(f)}: {err}" for f, err in errors)
            QMessageBox.critical(self, "Fehler", text)
        else:
            QMessageBox.information(self, "Erfolgreich", "Rechnung(en) erfolgreich gelöscht.")
            # Tabelle neu laden, damit das Häkchen verschwindet
            self.lade_eintraege()



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
            QMessageBox.critical(self, "Fehler", "Keine Buchungszeile mit Belegnummer gefunden!")
            return

        daten = df.iloc[start_row:].copy().reset_index(drop=True)
        daten.columns = [
            "Belegnr", "Datum", "Einnahme", "Ausgabe", "Bemerkung", "Quittung", "Postkonto", "Offene Aufträge"
        ]
        daten = daten[daten["Belegnr"].notnull() & daten["Belegnr"].apply(lambda x: str(x).strip().isdigit())]

        conn = get_db()
        cursor = conn.cursor(cursor_factory=dict_cursor_factory(conn))

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


        for idx, row in daten.iterrows():
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

            cursor.execute("""
                INSERT OR IGNORE INTO buchhaltung (id, datum, typ, kategorie, betrag, beschreibung)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                belegnr, datum, typ, "Sonstiges", betrag, bemerkung
            ))

        conn.commit()
        conn.close()
        QMessageBox.information(self, "Fertig", f"{len(daten)} Buchungen importiert!")
        self.lade_eintraege()












