# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QDialog, QFileDialog, QInputDialog
)
from db_connection import get_db, dict_cursor
import sqlite3
import json
import os
import subprocess
from gui.rechnung_dialog import RechnungDialog, RechnungLayoutDialog
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF
from decimal import Decimal
from PyQt5.QtGui import QBrush, QColor
from datetime import datetime, timedelta
import tempfile
from PyQt5.QtWidgets import QToolButton


# Pastell-Farben wie im Buchhaltungstab
PASTELL_GRUEN  = QColor(230, 255, 230)   # bezahlt
PASTELL_ROT    = QColor(255, 230, 230)   # überfällig
PASTELL_ORANGE = QColor(255, 245, 230)   # offen

class RechnungenTab(QWidget):
    def __init__(self):
        super().__init__()

        self.initialisiere_datenbank()

        # Hauptlayout: horizontal, links Tabelle, rechts Buttons
        self.layout_main = QHBoxLayout(self)

        # Einstellungen und Layout laden
        self._lade_einstellungen()
        self._lade_rechnungslayout()

        # Kundeninformationen
        self.kunden_liste = self._lade_kundennamen()
        self.kunden_adressen = self._lade_kunden_adressen()
        self.kunden_firmen = self._lade_kunden_firmen()

        # Tabelle mit Rechnungen
        self.table = QTableWidget()
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self._setup_table()
        self.layout_main.addWidget(self.table, stretch=1)

        # Buttons rechts
        btn_layout = QVBoxLayout()

        # --- Buttons als Instanzattribute (QToolButton) + sinnvolle Rollen ---
        self.btn_neu = QToolButton()
        self.btn_neu.setText('Neue Rechnung')
        self.btn_neu.setProperty("role", "add")

        self.btn_bearbeiten = QToolButton()
        self.btn_bearbeiten.setText('Rechnung bearbeiten')
        self.btn_bearbeiten.setProperty("role", "edit")

        self.btn_loeschen = QToolButton()
        self.btn_loeschen.setText('Rechnung löschen')
        self.btn_loeschen.setProperty("role", "delete")

        self.btn_set_status = QToolButton()
        self.btn_set_status.setText('Status ändern')
        self.btn_set_status.setProperty("role", "refresh")   # besser als "edit" für Status ändern

        self.btn_exportieren = QToolButton()
        self.btn_exportieren.setText('Export PDF')
        self.btn_exportieren.setProperty("role", "download")

        self.btn_vorschau = QToolButton()
        self.btn_vorschau.setText("Vorschau PDF")
        self.btn_vorschau.setProperty("role", "preview")

        self.btn_layout_bearbeiten = QToolButton()
        self.btn_layout_bearbeiten.setText('Rechnungslayout bearbeiten')
        self.btn_layout_bearbeiten.setProperty("role", "settings")

        # --- Verbindungen ---
        self.btn_neu.clicked.connect(self.neue_rechnung)
        self.btn_bearbeiten.clicked.connect(self.bearbeite_rechnung)
        self.btn_loeschen.clicked.connect(self.loesche_rechnung)
        self.btn_set_status.clicked.connect(self._status_aendern)
        self.btn_exportieren.clicked.connect(self.exportiere_ausgewaehlte_rechnung)
        self.btn_vorschau.clicked.connect(self.vorschau_ausgewaehlte_rechnung)
        self.btn_layout_bearbeiten.clicked.connect(self.oeffne_rechnungslayout_dialog)

        # --- Layout ---
        for btn in [
            self.btn_neu, self.btn_bearbeiten, self.btn_loeschen,
            self.btn_set_status, self.btn_exportieren, self.btn_vorschau,
            self.btn_layout_bearbeiten
        ]:
            btn_layout.addWidget(btn)



        btn_layout.addStretch()

        self.layout_main.addLayout(btn_layout)

        # Rechnungen laden
        self.lade_rechnungen()

    
    def aktualisiere_kunden_liste(self):
        """Vom KundenTab-Signal aufgerufen: Kundenlisten neu laden und Tabelle refreshen."""
        self.kunden_liste = self._lade_kundennamen()
        self.kunden_adressen = self._lade_kunden_adressen()
        self.kunden_firmen = self._lade_kunden_firmen()
        self.lade_rechnungen()
# ---------------- DB / Settings ----------------

    def initialisiere_datenbank(self):
        conn = get_db()
        cursor = conn.cursor(cursor_factory=dict_cursor(conn))

        # Tabelle Kunden
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS public.kunden (
                kundennr BIGSERIAL PRIMARY KEY,
                name     TEXT,
                firma    TEXT,
                plz      TEXT,
                strasse  TEXT,
                stadt    TEXT,
                email    TEXT,
                anrede   TEXT
            )
        """)


        # Tabelle Rechnungen
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rechnungen (
                id SERIAL PRIMARY KEY,
                rechnung_nr TEXT,
                kunde TEXT,
                firma TEXT,
                adresse TEXT,
                datum TEXT,
                mwst REAL,
                zahlungskonditionen TEXT,
                positionen TEXT,
                uid TEXT,
                abschluss TEXT
            )
        """)

        # Alte DBs: Spalten nachziehen (idempotent)
        for spalte in ["abschluss", "uid", "firma", "abschluss_text"]:
            try:
                # Spalten idempotent nachziehen (PostgreSQL)
                cursor.execute("ALTER TABLE rechnungen ADD COLUMN IF NOT EXISTS abschluss TEXT")
                cursor.execute("ALTER TABLE rechnungen ADD COLUMN IF NOT EXISTS uid TEXT")
                cursor.execute("ALTER TABLE rechnungen ADD COLUMN IF NOT EXISTS firma TEXT")
                cursor.execute("ALTER TABLE rechnungen ADD COLUMN IF NOT EXISTS abschluss_text TEXT")

            except sqlite3.OperationalError:
                pass

        conn.commit()
        conn.close()

    def oeffne_rechnungslayout_dialog(self):
        dialog = RechnungLayoutDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self._lade_rechnungslayout()

    def _lade_einstellungen(self):
        """MWST aus JSON-Konfig laden, Standard 7.7%"""
        try:
            with open("config/einstellungen.json", "r", encoding="utf-8") as f:
                daten = json.load(f)
            self.mwst = float(daten.get("mwst", 7.7))
            self.uid = daten.get("uid", "")
        except Exception:
            self.mwst = 7.7
            self.uid = ""

    def _lade_rechnungslayout(self):
        """Layout aus JSON-Datei laden oder Defaults setzen"""
        pfad = "config/rechnung_layout.json"
        if os.path.exists(pfad):
            with open(pfad, "r", encoding="utf-8") as f:
                daten = json.load(f)
            self.layout_config = {
                "kopfzeile": {
                    "text": daten.get("kopfzeile", ""),
                    "schrift": "Helvetica",
                    "groesse": 10,
                    "farbe": [0, 0, 0]
                },
                "einleitung": daten.get("einleitung", ""),
                "fusszeile": {
                    "text": daten.get("fusszeile", ""),
                    "schrift": "Helvetica-Oblique",
                    "groesse": 8,
                    "farbe": [100, 100, 100]
                },
                "logo_datei": daten.get("logo_pfad"),
                "logo_skala": daten.get("logo_skala", 100),
                "betreff": daten.get("betreff", "Rechnung"),
                "schrift": daten.get("schrift", "Helvetica"),
                "schrift_bold": daten.get("schrift_bold", "Helvetica-Bold"),
                "schrift_kursiv": daten.get("schrift_kursiv", "Helvetica-Oblique"),
                "farbe_text": daten.get("farbe_text", [0, 0, 0]),
                "schriftgroesse": daten.get("schriftgroesse", 10),
                "schriftgroesse_betreff": daten.get("schriftgroesse_betreff", 12)
            }
        else:
            self.layout_config = {
                "kopfzeile": {
                    "text": "Deine Firma GmbH\nMusterstraße 1\n8000 Zürich",
                    "schrift": "Helvetica-Bold",
                    "groesse": 14,
                    "farbe": [0, 0, 0]
                },
                "einleitung": ("Sehr geehrte Damen und Herren,\n\n"
                               "vielen Dank für Ihren Auftrag. Hiermit erhalten Sie unsere Rechnung:"),
                "fusszeile": {
                    "text": "Vielen Dank für Ihren Auftrag!",
                    "schrift": "Helvetica-Oblique",
                    "groesse": 8,
                    "farbe": [100, 100, 100]
                },
                "logo_datei": None,
                "logo_skala": 100,
                "betreff": "Rechnung",
                "schrift": "Helvetica",
                "schrift_bold": "Helvetica-Bold",
                "schrift_kursiv": "Helvetica-Oblique",
                "farbe_text": [0, 0, 0],
                "schriftgroesse": 10,
                "schriftgroesse_betreff": 12
            }

    # ---------------- Kunden Daten ----------------

    def _lade_kunden_adressen(self):
        conn = get_db()
        cursor = conn.cursor(cursor_factory=dict_cursor(conn))
        cursor.execute("SELECT name, firma, plz, strasse, stadt FROM kunden ORDER BY name")
        daten = cursor.fetchall()
        conn.close()
        return {name: f"{strasse}\n{plz} {stadt}" for name, firma, plz, strasse, stadt in daten}

    def _lade_kunden_firmen(self):
        conn = get_db()
        cursor = conn.cursor(cursor_factory=dict_cursor(conn))
        cursor.execute("SELECT name, firma FROM kunden ORDER BY name")
        daten = cursor.fetchall()
        conn.close()
        return {name: firma for name, firma in daten}

    def _lade_kundennamen(self):
        conn = get_db()
        cursor = conn.cursor(cursor_factory=dict_cursor(conn))
        cursor.execute("SELECT name FROM kunden ORDER BY name")
        namen = [row[0] for row in cursor.fetchall()]
        conn.close()
        return namen

    # ---------------- Tabelle / UI ----------------

    def _setup_table(self):
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Rechnungs-Nr", "Kunde", "Datum", "Status"])
        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(1, 150)
        self.table.setColumnWidth(2, 200)
        self.table.setColumnWidth(3, 100)
        self.table.setColumnWidth(4, 100)
        self.table.setSelectionBehavior(self.table.SelectRows)
        self.table.setEditTriggers(self.table.NoEditTriggers)

    def _setze_zeilenfarbe(self, row_idx, farbe: QColor):
        """Färbt die komplette Tabellenzeile ein."""
        brush = QBrush(farbe)
        for c in range(self.table.columnCount()):
            it = self.table.item(row_idx, c)
            if it is None:
                it = QTableWidgetItem("")
                self.table.setItem(row_idx, c, it)
            it.setBackground(brush)

    def lade_rechnungen(self):
        conn = get_db()
        cursor = conn.cursor(cursor_factory=dict_cursor(conn))

        cursor.execute("""
            SELECT id, rechnung_nr, kunde, firma, adresse, datum, mwst, zahlungskonditionen, positionen, uid, abschluss, abschluss_text
            FROM rechnungen ORDER BY datum DESC
        """)
        daten = cursor.fetchall()
        conn.close()

        self.rechnungen = []
        self.table.setRowCount(len(daten))

        for i, (id_, nr, kunde, firma, adresse, datum, mwst, zahlungskonditionen, positionen_json, uid, abschluss, abschluss_text) in enumerate(daten):
            self.table.setItem(i, 0, QTableWidgetItem(str(id_)))
            self.table.setItem(i, 1, QTableWidgetItem(nr or ""))
            self.table.setItem(i, 2, QTableWidgetItem(kunde or ""))
            self.table.setItem(i, 3, QTableWidgetItem(str(datum or "")))

            status_text, farbe = self._berechne_status(str(datum or ""), zahlungskonditionen or "", abschluss or "")
            self.table.setItem(i, 4, QTableWidgetItem(status_text))
            self._setze_zeilenfarbe(i, farbe)

            try:
                positionen = json.loads(positionen_json) if positionen_json else []
            except Exception:
                positionen = []

            self.rechnungen.append({
                "id": id_,
                "rechnung_nr": nr or "",
                "kunde": kunde or "",
                "firma": firma or "",
                "adresse": adresse or "",
                "datum": datum or "",
                "mwst": mwst,
                "zahlungskonditionen": zahlungskonditionen or "",
                "positionen": positionen,
                "uid": uid or "",
                "abschluss": abschluss or "",
                "abschluss_text": abschluss_text or "",
                "status": status_text,
            })

    # ---------------- Status-Logik ----------------

    def _berechne_status(self, datum_str, zahlungskonditionen, abschluss):
        """
        Gibt (status_text, farbe_qcolor) zurück.

        Regeln:
        - Wenn 'abschluss' explizit einen Status enthält ('bezahlt'/'offen'/'überfällig'),
          gilt das als **manuelle Festlegung** -> keine Automatik, nur Farbe setzen.
        - Sonst automatische Berechnung aus Datum + Zahlungsziel.
          Standard-Zahlungsziel = 10 Tage, wenn Feld leer.
        Farben: Pastell wie im Buchhaltungstab.
        """
        status_man = (abschluss or "").strip().lower()
        if status_man in ("bezahlt", "offen", "überfällig"):
            if status_man == "bezahlt":
                return "bezahlt", PASTELL_GRUEN
            elif status_man == "überfällig":
                return "überfällig", PASTELL_ROT
            else:
                return "offen", PASTELL_ORANGE

        # -------- Automatik --------
        # Datum parsen
        rechnungsdatum = None
        for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d.%m.%y"):
            try:
                rechnungsdatum = datetime.strptime(datum_str, fmt).date()
                break
            except Exception:
                pass
        if not rechnungsdatum:
            rechnungsdatum = datetime.today().date()

        # Zahlungsziel: Standard 10 Tage
        ziel_tage = 10
        if isinstance(zahlungskonditionen, str) and zahlungskonditionen.strip():
            import re as _re
            m = _re.search(r"(\d+)", zahlungskonditionen)
            if m:
                try:
                    ziel_tage = int(m.group(1))
                except Exception:
                    pass

        faellig_am = rechnungsdatum + timedelta(days=ziel_tage)
        heute = datetime.today().date()
        if heute > faellig_am:
            return "überfällig", PASTELL_ROT
        return "offen", PASTELL_ORANGE

    def _status_aendern(self):
        """Status per Button wählen; manuelle Auswahl überschreibt Automatik dauerhaft (in DB)."""
        zeile = self.table.currentRow()
        if zeile < 0:
            QMessageBox.warning(self, "Keine Auswahl", "Bitte zuerst eine Rechnung auswählen.")
            return
        rechnung_id = int(self.table.item(zeile, 0).text())

        status, ok = QInputDialog.getItem(
            self, "Rechnungsstatus wählen",
            "Status:",
            ["offen", "bezahlt", "überfällig"],
            0, False
        )
        if not ok:
            return

        # In DB als 'abschluss' speichern (gilt als manuell)
        conn = get_db()
        cursor = conn.cursor(cursor_factory=dict_cursor(conn))
        cursor.execute("UPDATE rechnungen SET abschluss= %s WHERE id= %s", (status, rechnung_id))
        conn.commit()
        conn.close()

        # UI aktualisieren
        datum = self.table.item(zeile, 3).text()
        zahlk = None
        for r in self.rechnungen:
            if r["id"] == rechnung_id:
                zahlk = r.get("zahlungskonditionen", "")
                r["abschluss"] = status  # in Memory nachziehen
                break

        status_text, farbe = self._berechne_status(datum, zahlk or "", status)
        self.table.setItem(zeile, 4, QTableWidgetItem(status_text))
        self._setze_zeilenfarbe(zeile, farbe)

        QMessageBox.information(self, "Rechnung", f"Status geändert zu: {status_text}")

    # ---------------- CRUD Rechnungen ----------------

    def neue_rechnung(self):
        dialog = RechnungDialog(self.kunden_liste, self.kunden_firmen, self.kunden_adressen, mwst_voreinstellung=self.mwst)
        if dialog.exec_() == QDialog.Accepted:
            rechnung = dialog.get_rechnung()
            # Default-Zahlungsziel-Text setzen, falls leer
            if not rechnung.get("zahlungskonditionen", "").strip():
                rechnung["zahlungskonditionen"] = "Zahlbar inner 10 Tagen"
            # 'abschluss' leer lassen -> Automatik
            if not rechnung.get("abschluss", ""):
                rechnung["abschluss"] = ""
            self.speichere_rechnung(rechnung)
            self.lade_rechnungen()

    def bearbeite_rechnung(self):
        zeile = self.table.currentRow()
        if zeile < 0:
            QMessageBox.warning(self, "Keine Auswahl", "Bitte zuerst eine Rechnung auswählen.")
            return
        rechnung_id = int(self.table.item(zeile, 0).text())
        rechnung = self.lade_rechnung_nach_id(rechnung_id)
        if not rechnung:
            QMessageBox.warning(self, "Fehler", "Rechnung nicht gefunden.")
            return

        dialog = RechnungDialog(self.kunden_liste, self.kunden_firmen, self.kunden_adressen, rechnung, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            neue_rechnung = dialog.get_rechnung()
            if not neue_rechnung.get("zahlungskonditionen", "").strip():
                neue_rechnung["zahlungskonditionen"] = "Zahlbar inner 10 Tagen"
            # abschluss so lassen wie im Dialog (leer = Automatik)
            self.speichere_rechnung(neue_rechnung, rechnung_id)
            self.lade_rechnungen()

    def loesche_rechnung(self):
        zeile = self.table.currentRow()
        if zeile < 0:
            QMessageBox.warning(self, "Keine Auswahl", "Bitte zuerst eine Rechnung auswählen.")
            return
        rechnung_id = int(self.table.item(zeile, 0).text())

        antwort = QMessageBox.question(
            self, "Rechnung löschen",
            f"Soll die Rechnung mit ID {rechnung_id} gelöscht werden?",
            QMessageBox.Yes | QMessageBox.No
        )
        if antwort == QMessageBox.Yes:
            conn = get_db()
            cursor = conn.cursor(cursor_factory=dict_cursor(conn))
            cursor.execute("DELETE FROM rechnungen WHERE id = %s", (rechnung_id,))
            conn.commit()
            conn.close()
            self.lade_rechnungen()

    def speichere_rechnung(self, rechnung, rechnung_id=None):
        """Rechnung in DB speichern (neu oder update)"""
        positionen_json = json.dumps(rechnung.get("positionen", []), ensure_ascii=False)
        conn = get_db()
        cursor = conn.cursor(cursor_factory=dict_cursor(conn))

        if rechnung_id is not None:
            cursor.execute("""
                UPDATE rechnungen SET
                    rechnung_nr = %s, kunde = %s, firma = %s, adresse = %s, datum = %s,
                    mwst = %s, zahlungskonditionen = %s, positionen = %s, uid = %s, abschluss = %s
                WHERE id = %s
            """, (
                rechnung.get("rechnung_nr", ""),
                rechnung.get("kunde", ""),
                rechnung.get("firma", ""),
                rechnung.get("adresse", ""),
                rechnung.get("datum", ""),
                rechnung.get("mwst", 0),
                rechnung.get("zahlungskonditionen", ""),
                positionen_json,
                rechnung.get("uid", ""),
                rechnung.get("abschluss", ""),
                rechnung_id
            ))
        else:
            cursor.execute("""
                INSERT INTO rechnungen (
                    rechnung_nr, kunde, firma, adresse, datum,
                    mwst, zahlungskonditionen, positionen, uid, abschluss, abschluss_text
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""", (
                rechnung.get("rechnung_nr", ""),
                rechnung.get("kunde", ""),
                rechnung.get("firma", ""),
                rechnung.get("adresse", ""),
                rechnung.get("datum", ""),
                rechnung.get("mwst", 0),
                rechnung.get("zahlungskonditionen", ""),
                positionen_json,
                rechnung.get("uid", ""),
                rechnung.get("abschluss", ""),
                rechnung.get("abschluss_text", ""),
            ))

        conn.commit()
        conn.close()

    # ---------------- Helpers ----------------

    def lade_rechnung_nach_id(self, rechnung_id):
        for rechnung in self.rechnungen:
            if rechnung["id"] == rechnung_id:
                return rechnung
        return None

    def exportiere_ausgewaehlte_rechnung(self):
        zeile = self.table.currentRow()
        if zeile < 0:
            QMessageBox.warning(self, "Keine Auswahl", "Bitte zuerst eine Rechnung auswählen.")
            return
        rechnung_id = int(self.table.item(zeile, 0).text())
        rechnung = self.lade_rechnung_nach_id(rechnung_id)
        if not rechnung:
            QMessageBox.warning(self, "Fehler", "Rechnung nicht gefunden.")
            return

        pfad, _ = QFileDialog.getSaveFileName(self, "PDF speichern", f"Rechnung_{rechnung['rechnung_nr']}.pdf", "PDF-Dateien (*.pdf)")
        if pfad:
            try:
                self._exportiere_pdf(rechnung, pfad)
                QMessageBox.information(self, "Erfolg", f"PDF wurde gespeichert unter:\n{pfad}")
            except Exception as e:
                QMessageBox.critical(self, "Fehler", f"Fehler beim PDF Export:\n{str(e)}")

    def vorschau_ausgewaehlte_rechnung(self):
        zeile = self.table.currentRow()
        if zeile < 0:
            QMessageBox.warning(self, "Keine Auswahl", "Bitte zuerst eine Rechnung auswählen.")
            return

        rechnung_id = int(self.table.item(zeile, 0).text())
        rechnung = self.lade_rechnung_nach_id(rechnung_id)
        if not rechnung:
            QMessageBox.warning(self, "Fehler", "Rechnung nicht gefunden.")
            return

        # Layout neu laden (inkl. logo_skala)
        self._lade_rechnungslayout()
        logo_skala = self.layout_config.get("logo_skala", 100)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            self._exportiere_pdf(rechnung, tmp.name, logo_skala=logo_skala)
            tmp_path = tmp.name

        if os.name == "nt":
            os.startfile(tmp_path)
        elif hasattr(os, "uname") and os.uname().sysname == "Darwin":
            subprocess.Popen(["open", tmp_path])
        else:
            subprocess.Popen(["xdg-open", tmp_path])

    def _exportiere_pdf(self, rechnung, dateipfad, logo_skala=100):
        c = canvas.Canvas(dateipfad, pagesize=A4)
        width, height = A4

        # Blöcke: Name: (x_links, y_unten, breite, höhe)
        blocks = {
            "logo":      (20*mm, 250*mm, 170*mm, 35*mm),
            "adresse":   (20*mm, 200*mm, 70*mm, 25*mm),
            "details":   (140*mm, 215*mm, 70*mm, 25*mm),
            "betreff":   (20*mm, 178*mm, 170*mm, 5*mm),
            "einleitung":(20*mm, 159*mm, 170*mm, 15*mm),
            "fusszeile": (20*mm, 10*mm, 170*mm, 10*mm),
        }

        rand_links = 20 * mm  # wird mehrfach genutzt

        # Schriftfarbe
        c.setFillColorRGB(*[v / 255 for v in self.layout_config["farbe_text"]])

        # Logo
        x_logo, y_logo, w_logo, h_logo = blocks["logo"]
        logo_pfad = self.layout_config.get("logo_datei")
        if logo_pfad and os.path.exists(logo_pfad):
            try:
                from PIL import Image
                with Image.open(logo_pfad) as img:
                    original_breite, original_hoehe = img.size
                faktor = min((w_logo / original_breite), (h_logo / original_hoehe), 1.0) * (self.layout_config.get("logo_skala", 100) / 100.0)
                logo_breite = original_breite * faktor
                logo_hoehe = original_hoehe * faktor
                logo_x = x_logo
                logo_y = y_logo + h_logo - logo_hoehe
                c.drawImage(logo_pfad, logo_x, logo_y, width=logo_breite, height=logo_hoehe, mask='auto', preserveAspectRatio=True)
            except Exception as e:
                print("Logo-Fehler:", e)

        # Kundenadresse
        x, y, w, h = blocks["adresse"]
        firma = rechnung.get("firma", "")
        kunde_name = rechnung.get("kunde", "")
        adresse = rechnung.get("adresse", "")
        c.setFont(self.layout_config["schrift_bold"], self.layout_config["schriftgroesse"])
        textobj = c.beginText()
        textobj.setTextOrigin(x, y + h - self.layout_config["schriftgroesse"])
        textobj.setLeading(self.layout_config["schriftgroesse"] * 1.2)
        if firma: textobj.textLine(firma)
        if kunde_name: textobj.textLine(kunde_name)
        for zeile in adresse.splitlines():
            textobj.textLine(zeile)
        c.drawText(textobj)

        # Details
        x_det, y_det, w_det, h_det = blocks["details"]
        c.setFont(self.layout_config["schrift"], self.layout_config["schriftgroesse"])
        details = []
        uid = rechnung.get("uid", "")
        if uid: details.append(f"UID: {uid}")
        details.append(f"Rechnungsnummer: {rechnung.get('rechnung_nr','')}")
        details.append(f"Datum: {rechnung.get('datum','')}")
        textobj = c.beginText()
        textobj.setTextOrigin(x_det, y_det + h_det - self.layout_config["schriftgroesse"])
        textobj.setLeading(self.layout_config["schriftgroesse"] * 1.2)
        for zeile in details:
            textobj.textLine(zeile)
        c.drawText(textobj)

        # Betreff
        x_betreff, y_betreff, w_betreff, h_betreff = blocks["betreff"]
        c.setFont(self.layout_config["schrift_bold"], self.layout_config["schriftgroesse_betreff"])
        c.drawString(
            x_betreff,
            y_betreff + h_betreff - self.layout_config["schriftgroesse_betreff"],
            self.layout_config.get("betreff", "Rechnung")
        )

        # Einleitung
        x_einl, y_einl, w_einl, h_einl = blocks["einleitung"]
        c.setFont(self.layout_config["schrift"], self.layout_config["schriftgroesse"])
        einleitung = self.layout_config.get("einleitung", "")
        textobj = c.beginText()
        textobj.setTextOrigin(x_einl, y_einl + h_einl - self.layout_config["schriftgroesse"])
        textobj.setLeading(self.layout_config["schriftgroesse"] * 1.2)
        for zeile in einleitung.splitlines():
            textobj.textLine(zeile)
        c.drawText(textobj)

        # Positionen-Tabelle
        positionen = rechnung.get("positionen", [])
        spalten = ["Pos", "Beschreibung", "Anzahl", "Einzelpreis", "Gesamtpreis"]
        daten_tabelle = [spalten]

        gesamtbetrag_netto = 0.0
        for i, pos in enumerate(positionen, start=1):
            beschreibung = pos.get("beschreibung", "")
            try:
                anzahl = float(pos.get("menge"))
            except (TypeError, ValueError):
                anzahl = 0.0
            try:
                einzelpreis = float(pos.get("einzelpreis"))
            except (TypeError, ValueError):
                einzelpreis = 0.0
            gesamtpreis = anzahl * einzelpreis
            gesamtbetrag_netto += gesamtpreis
            daten_tabelle.append([
                str(i),
                beschreibung,
                f"{anzahl:.2f}",
                f"{einzelpreis:.2f} CHF",
                f"{gesamtpreis:.2f} CHF"
            ])

        t = Table(daten_tabelle, colWidths=[10*mm, 95*mm, 15*mm, 25*mm, 25*mm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('ALIGN', (2,1), (4,-1), 'RIGHT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('FONTSIZE', (0,0), (-1,-1), self.layout_config["schriftgroesse"])
        ]))
        t_w, t_h = t.wrap(0,0)
        y_pos = A4[1] - 140 * mm - t_h
        t.drawOn(c, rand_links, y_pos)

        # MWST-Berechnung
        mwst_prozent = float(rechnung.get("mwst", self.mwst))
        mwst_betrag = gesamtbetrag_netto * mwst_prozent / 100.0
        gesamtbetrag_brutto = gesamtbetrag_netto + mwst_betrag

        # Summen
        summen_x = rand_links + 40 * mm
        summen_y = y_pos - 5 * mm
        gesamt_x = summen_x + 128 * mm
        label_x = summen_x + 103 * mm

        c.setFont(self.layout_config["schrift_bold"], self.layout_config["schriftgroesse"])
        if abs(mwst_prozent) < 0.01:
            c.drawRightString(label_x, summen_y, "Total:")
            c.setFont(self.layout_config["schrift"], self.layout_config["schriftgroesse"])
            c.drawRightString(gesamt_x, summen_y, f"{gesamtbetrag_netto:.2f} CHF")
        else:
            c.drawRightString(label_x, summen_y, "Netto:")
            c.drawRightString(label_x, summen_y - 10, f"MWST ({mwst_prozent:.2f}%):")
            c.drawRightString(label_x, summen_y - 20, "Total brutto:")
            c.setFont(self.layout_config["schrift"], self.layout_config["schriftgroesse"])
            c.drawRightString(gesamt_x, summen_y, f"{gesamtbetrag_netto:.2f} CHF")
            c.drawRightString(gesamt_x, summen_y - 10, f"{mwst_betrag:.2f} CHF")
            c.drawRightString(gesamt_x, summen_y - 20, f"{gesamtbetrag_brutto:.2f} CHF")

        # Zahlungsbedingungen
        zahlungstext = rechnung.get("zahlungskonditionen", "")
        if zahlungstext:
            c.setFont(self.layout_config["schrift"], self.layout_config["schriftgroesse"])
            textobj = c.beginText()
            textobj.setTextOrigin(rand_links, summen_y - 30)
            textobj.setLeading(self.layout_config["schriftgroesse"] * 1.3)
            for zeile in zahlungstext.splitlines():
                textobj.textLine(zeile)
            c.drawText(textobj)

        # Abschiedsgruss (optional)
        abschluss_text = (rechnung.get('abschluss_text','') or '').strip()
        if abschluss_text:
            c.setFont(self.layout_config['schrift'], self.layout_config['schriftgroesse'])
            textobj2 = c.beginText()
            textobj2.setTextOrigin(rand_links, (summen_y - 30) - 30)
            textobj2.setLeading(self.layout_config['schriftgroesse'] * 1.3)
            for zeile in abschluss_text.splitlines():
                textobj2.textLine(zeile)
            c.drawText(textobj2)

        # QR-Code Seite
        c.showPage()
        self.zeichne_swiss_qr(c, rechnung, gesamtbetrag_brutto)

        c.showPage()
        c.save()

    def zeichne_swiss_qr(self, canvas_obj, rechnung, betrag):
        """Generiert einen Swiss QR-Code und platziert ihn im PDF (via qrbill)."""
        try:
            with open("config/qr_daten.json", "r", encoding="utf-8") as f:
                qr_data = json.load(f)
            creditor = qr_data["creditor"]
            iban = qr_data["iban"]
            currency = qr_data.get("currency", "CHF")
        except Exception as e:
            creditor = {
                'name': "Deine Firma GmbH",
                'street': "Musterstrasse 1",
                'pcode': "8000",
                'city': "Zürich",
                'country': "CH",
            }
            iban = "CH5800791123000889012"
            currency = "CHF"
            print("Fehler beim Laden von qr_daten.json:", e)

        debtor = {
            'name': rechnung.get("kunde", ""),
            'street': "",
            'pcode': "",
            'city': "",
            'country': "CH",
        }
        adresse = rechnung.get("adresse", "")
        if adresse:
            addr_lines = adresse.split("\n")
            if len(addr_lines) >= 2:
                debtor['street'] = addr_lines[0].strip()
                try:
                    debtor['pcode'], debtor['city'] = addr_lines[1].strip().split(" ", 1)
                except Exception:
                    debtor['city'] = addr_lines[1].strip()

        from qrbill import QRBill
        # Betrag als Decimal
        amount = Decimal(str(betrag)) if betrag is not None else Decimal("0")

        my_bill = QRBill(
            account=iban,
            creditor=creditor,
            amount=amount,
            debtor=debtor,
            currency=currency,
            language='de'
        )

        # SVG generieren und ins PDF einfügen
        fd, tmp_svg_path = tempfile.mkstemp(suffix=".svg")
        os.close(fd)
        try:
            my_bill.as_svg(tmp_svg_path)

            drawing = svg2rlg(tmp_svg_path)
            x = 20 * mm
            y = -5 * mm
            w = 180 * mm
            h = 90 * mm
            canvas_obj.saveState()
            canvas_obj.translate(x, y)
            canvas_obj.scale(w / drawing.width, h / drawing.height)
            renderPDF.draw(drawing, canvas_obj, 0, 0)
            canvas_obj.restoreState()
        finally:
            try:
                os.remove(tmp_svg_path)
            except Exception:
                pass

