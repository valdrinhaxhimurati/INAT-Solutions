# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QToolButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QDialog, QFileDialog, QLabel, QHeaderView, QAbstractItemView, QFrame,
    QLineEdit, QPushButton, QSizePolicy
)
from PyQt5.QtGui import QBrush, QColor, QFont, QIcon
from PyQt5.QtCore import Qt, QDate, pyqtSignal, QSize
from reportlab.lib.utils import ImageReader
import re
import io
from db_connection import get_db, dict_cursor_factory, get_rechnung_layout
import json, os, subprocess, tempfile
from gui.rechnung_dialog import RechnungDialog
from gui.rechnung_layout_dialog import RechnungLayoutDialog
from gui.zahlung_erfassen_dialog import ZahlungErfassenDialog
from gui.rechnung_styles import get_stil, RECHNUNG_STYLES
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from invoice_assets import get_invoice_logo_imagereader
from settings_store import get_json, import_json_if_missing
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF
from decimal import Decimal
from datetime import datetime, timedelta
from gui.themed_input_dialog import get_item as themed_get_item
from gui.popup_calendar import PopupCalendarWidget
from gui.modern_widgets import (
    COLORS, FONT_SIZES, SPACING, BORDER_RADIUS,
    get_table_stylesheet, get_button_primary_stylesheet, 
    get_button_secondary_stylesheet, get_input_stylesheet,
    get_toolbar_button_stylesheet, create_gray_icon
)
from i18n import _

# Pastell-Farben wie im Buchhaltungstab
PASTELL_GRUEN  = QColor(230, 255, 230)   # bezahlt
PASTELL_ROT    = QColor(255, 230, 230)   # überfällig
PASTELL_ORANGE = QColor(255, 245, 230)   # offen

class RechnungenTab(QWidget):
    # Signal das emittiert wird wenn eine Zahlung erfasst wurde
    zahlung_erfasst = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        # Default-MWST (Schutz falls importierte Daten keine mwst liefern)
        self.mwst = 0.0
        self._known_invoice_ids = set()

        self.initialisiere_datenbank()
        self.init_ui()
        self.lade_rechnungen()


    def init_ui(self):
        # Modernes Layout wie auf der Website
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Einstellungen und Layout laden
        self._lade_einstellungen()
        self._lade_rechnungslayout()

        # Kundeninformationen
        self.kunden_liste = self._lade_kundennamen()
        self.kunden_adressen = self._lade_kunden_adressen()
        self.kunden_firmen = self._lade_kunden_firmen()

        # Grauer Container-Hintergrund
        container = QFrame()
        container.setStyleSheet(f"background-color: {COLORS['background']}; border-radius: {BORDER_RADIUS['lg']}px;")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(SPACING['xl'], SPACING['xl'], SPACING['xl'], SPACING['xl'])
        container_layout.setSpacing(SPACING['lg'])

        # Toolbar: Neue Rechnung Button links, Suchfeld rechts
        toolbar = QHBoxLayout()
        
        self.btn_neu = QPushButton(_("+ Neue Rechnung"))
        self.btn_neu.setStyleSheet(get_button_primary_stylesheet())
        self.btn_neu.setCursor(Qt.PointingHandCursor)
        self.btn_neu.clicked.connect(self.neue_rechnung)
        toolbar.addWidget(self.btn_neu)
        
        # Suchfeld - volle Breite
        self.suchfeld = QLineEdit()
        self.suchfeld.setPlaceholderText(_("🔍 Suchen..."))
        self.suchfeld.setStyleSheet(get_input_stylesheet())
        self.suchfeld.textChanged.connect(self.filter_tabelle)
        toolbar.addWidget(self.suchfeld, 1)  # stretch=1 für volle Breite
        
        container_layout.addLayout(toolbar)

        # Tabelle
        self.table = QTableWidget()
        self.table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.table.setMouseTracking(True)  # Für Hover-Effekte
        self.table.setStyleSheet(get_table_stylesheet())
        self._setup_table()
        self.table.doubleClicked.connect(self._on_double_click)
        container_layout.addWidget(self.table)
        
        main_layout.addWidget(container)

        # Hidden buttons for compatibility
        self.btn_bearbeiten = QPushButton()
        self.btn_bearbeiten.hide()
        self.btn_bearbeiten.clicked.connect(self.bearbeite_rechnung)
        self.btn_loeschen = QPushButton()
        self.btn_loeschen.hide()
        self.btn_loeschen.clicked.connect(self.loesche_rechnung)
        self.btn_set_status = QPushButton()
        self.btn_set_status.hide()
        self.btn_set_status.clicked.connect(self._status_aendern)
        self.btn_zahlung = QPushButton()
        self.btn_zahlung.hide()
        self.btn_zahlung.clicked.connect(self._zahlung_erfassen)
        self.btn_exportieren = QPushButton()
        self.btn_exportieren.hide()
        self.btn_exportieren.clicked.connect(self.exportiere_ausgewaehlte_rechnung)
        self.btn_vorschau = QPushButton()
        self.btn_vorschau.hide()
        self.btn_vorschau.clicked.connect(self.vorschau_ausgewaehlte_rechnung)

        self._loading_label = None
    
    def _on_double_click(self, index):
        """Doppelklick öffnet Rechnung zum Bearbeiten."""
        self.bearbeite_rechnung()

    def aktualisiere_kunden_liste(self):
        """Vom Kunden-Tab getriggert: Kunden-Cache + Tabelle neu laden."""
        self.kunden_liste = self._lade_kundennamen()
        self.kunden_adressen = self._lade_kunden_adressen()
        self.kunden_firmen = self._lade_kunden_firmen()
        self.lade_rechnungen()

# ---------------- DB / Settings ----------------

    def initialisiere_datenbank(self):
        with get_db() as conn:
            # robust: check wrapper flags instead of isinstance on the wrapper object
            is_sqlite = getattr(conn, "is_sqlite", None)
            if is_sqlite is None:
                is_sqlite = getattr(conn, "is_sqlite_conn", False)
            with conn.cursor() as cursor:
                if is_sqlite:
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS kunden (
                            kundennr INTEGER PRIMARY KEY AUTOINCREMENT,
                            name     TEXT,
                            firma    TEXT,
                            plz      TEXT,
                            strasse  TEXT,
                            stadt    TEXT,
                            email    TEXT,
                            anrede   TEXT
                        )
                    """)
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS rechnungen (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            rechnung_nr TEXT,
                            kunde TEXT,
                            firma TEXT,
                            adresse TEXT,
                            datum TEXT,
                            mwst REAL,
                            zahlungskonditionen TEXT,
                            positionen TEXT,
                            uid TEXT,
                            abschluss TEXT,
                            abschluss_text TEXT
                        )
                    """)
                else:
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS kunden (
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
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS rechnungen (
                            id BIGSERIAL PRIMARY KEY,
                            rechnung_nr TEXT,
                            kunde TEXT,
                            firma TEXT,
                            adresse TEXT,
                            datum TEXT,
                            mwst REAL,
                            zahlungskonditionen TEXT,
                            positionen TEXT,
                            uid TEXT,
                            abschluss TEXT,
                            abschluss_text TEXT
                        )
                    """)
                    # NEU: Synchronisiere die ID-Sequenzen mit den maximal vorhandenen Werten.
                    # Dies behebt den UniqueViolation-Fehler.
                    try:
                        # KORREKTUR: Der dritte Parameter muss 'true' sein, damit der n�chste Wert MAX(id) + 1 ist.
                        # Korrigiert die Z�hlung f�r die 'rechnungen'-Tabelle
                        cursor.execute("SELECT setval('rechnungen_id_seq', COALESCE((SELECT MAX(id) FROM rechnungen), 1), true)")
                        # Korrigiert vorsorglich auch die 'kunden'-Tabelle
                        cursor.execute("SELECT setval('kunden_kundennr_seq', COALESCE((SELECT MAX(kundennr) FROM kunden), 1), true)")

                    except Exception as e:
                        # Fehler ignorieren, falls die Tabelle/Sequenz noch nicht existiert, was beim allerersten Start normal ist.
                        print(f"Info: Konnte Sequenz nicht synchronisieren (normal beim ersten Start): {e}")

            conn.commit()

    def oeffne_rechnungslayout_dialog(self):
        dialog = RechnungLayoutDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self._lade_rechnungslayout()

    def _lade_einstellungen(self):
        # MWST aus DB laden (config-Tabelle)
        try:
            con = get_db()
            with con.cursor() as cur:
                cur.execute("SELECT value FROM config WHERE key = %s LIMIT 1", ["mwst_default"])
                row = cur.fetchone()
                if row:
                    mwst = float(row["value"] if isinstance(row, dict) else row[0])
                else:
                    mwst = 0.0  # Fallback
        except Exception:
            mwst = 0.0  # Fallback bei Fehler
        self.mwst_voreinstellung = mwst

    def _lade_rechnungslayout(self):
        import json, os, base64
        from db_connection import get_db

        defaults = {
            "logo_skala": 100,
            "schrift": "Helvetica",
            "schrift_bold": "Helvetica-Bold",
            "schriftgroesse": 10,
            "schriftgroesse_betreff": 12,
            "farbe_text": [0, 0, 0],
            "einleitung": "",
            "betreff": "Rechnung",
            "logo_bytes": None,
            "logo_datei": None,
            "fusszeile": {"text": ""},
            "stil": "classic"  # NEU: Default-Stil
        }

        layout = {}
        with get_db() as conn:
            with conn.cursor() as cur:
                # select a broad set of possible columns (works for both schemas)
                # Versuche mit stil-Spalte, fallback ohne
                try:
                    cur.execute("SELECT id, name, layout, kopfzeile, einleitung, fusszeile, logo, logo_mime, logo_skala, stil FROM rechnung_layout ORDER BY id LIMIT 1")
                    row = cur.fetchone()
                except Exception:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                    try:
                        cur.execute("SELECT id, name, layout, kopfzeile, einleitung, fusszeile, logo, logo_mime, logo_skala FROM rechnung_layout ORDER BY id LIMIT 1")
                        row = cur.fetchone()
                    except Exception:
                        row = None

                # normalize row -> dict
                if not row:
                    dbrow = {}
                else:
                    if isinstance(row, dict):
                        dbrow = row
                    elif hasattr(row, "keys"):
                        try:
                            dbrow = dict(row)
                        except Exception:
                            dbrow = {}
                    else:
                        desc = getattr(cur, "description", None)
                        if desc:
                            cols = [d[0] for d in desc]
                            dbrow = dict(zip(cols, row))
                        else:
                            dbrow = {}

                # First prefer a single 'layout' JSON field
                raw_layout = dbrow.get("layout")
                if raw_layout:
                    if isinstance(raw_layout, str):
                        try:
                            layout = json.loads(raw_layout)
                        except Exception:
                            layout = {}
                    elif isinstance(raw_layout, (dict, list)):
                        layout = raw_layout if isinstance(raw_layout, dict) else {}
                    else:
                        layout = {}
                else:
                    # fallback: assemble layout from separate columns (from RechnungLayoutDialog)
                    layout = {}
                    if dbrow.get("kopfzeile"):
                        layout["kopfzeile"] = dbrow.get("kopfzeile")
                    if dbrow.get("einleitung"):
                        layout["einleitung"] = dbrow.get("einleitung")
                    if dbrow.get("fusszeile"):
                        # fusszeile may be JSON string or plain text
                        f = dbrow.get("fusszeile")
                        if isinstance(f, str):
                            try:
                                layout["fusszeile"] = json.loads(f)
                            except Exception:
                                layout["fusszeile"] = {"text": f}
                        elif isinstance(f, dict):
                            layout["fusszeile"] = f
                        else:
                            layout["fusszeile"] = {"text": str(f)}
                    # logo as bytes
                    logo_db = dbrow.get("logo")
                    if isinstance(logo_db, (bytes, bytearray, memoryview)):
                        layout["logo_bytes"] = bytes(logo_db)
                    if dbrow.get("logo_skala") is not None:
                        try:
                            layout["logo_skala"] = float(dbrow.get("logo_skala"))
                        except Exception:
                            layout["logo_skala"] = defaults["logo_skala"]
                    # Stil laden
                    if dbrow.get("stil"):
                        layout["stil"] = dbrow.get("stil")

        # merge defaults + loaded layout and normalize
        if not isinstance(layout, dict):
            layout = {}
        merged = {}
        merged.update(defaults)
        merged.update(layout)
        # normalize possible base64 logo string
        if merged.get("logo_bytes") and isinstance(merged["logo_bytes"], str):
            try:
                merged["logo_bytes"] = base64.b64decode(merged["logo_bytes"])
            except Exception:
                merged["logo_bytes"] = None

        # ensure fusszeile is dict with "text"
        f = merged.get("fusszeile") or {}
        if isinstance(f, str):
            merged["fusszeile"] = {"text": f}
        elif not isinstance(f, dict):
            merged["fusszeile"] = {"text": ""}

        self.layout_config = merged
        return layout

    # ---------------- Kunden Daten ----------------

    def _lade_kunden_adressen(self):
        with get_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT name, firma, plz, strasse, stadt FROM kunden ORDER BY name")
                daten = cursor.fetchall()
        return {name: f"{strasse}\n{plz} {stadt}" for name, firma, plz, strasse, stadt in daten}

    def _lade_kunden_firmen(self):
        with get_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT name, firma FROM kunden ORDER BY name")
                daten = cursor.fetchall()
        return {name: firma for name, firma in daten}

    def _lade_kundennamen(self):
        with get_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT name FROM kunden ORDER BY name")
                namen = [row[0] for row in cursor.fetchall()]
        return namen

    # ---------------- Tabelle / UI ----------------

    def filter_tabelle(self, text):
        """Filtert die Tabelle basierend auf dem Suchtext."""
        for row in range(self.table.rowCount()):
            match = any(text.lower() in self.table.item(row, col).text().lower()
                        for col in range(self.table.columnCount())
                        if self.table.item(row, col))
            self.table.setRowHidden(row, not match)

    def _setup_table(self):
        # 7 Spalten wie auf der Website: ID, Nummer, Kunde, Datum, Betrag, Status, Aktionen
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([_("ID"), _("Nummer"), _("Kunde"), _("Datum"), _("Betrag"), _("Status"), _("Aktionen")])
        self.table.setColumnHidden(0, True)
        
        # Schriftgröße 20% kleiner (von 15px auf 12px)
        table_font = self.table.font()
        table_font.setPointSize(9)  # ca. 12px
        self.table.setFont(table_font)

        header = self.table.horizontalHeader()
        
        # Spaltenbreiten an Inhalt anpassen (User-Wunsch)
        # Kunde war vorher Stretch, deshalb "extrem lang". Jetzt passt es sich dem Inhalt an.
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)    # Nummer
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)    # Kunde
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)    # Datum
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)    # Betrag
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)    # Status
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)    # Aktionen
        
        # Damit die Spalten nicht zu zusammengequetscht wirken, geben wir etwas Mindestbreite
        header.setMinimumSectionSize(120)
        
        header.setStretchLastSection(False)
        
        # Zeilenh�he deutlich erh�ht (User-Wunsch: "zu wenig hoch")
        self.table.verticalHeader().setDefaultSectionSize(75)
        
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
    
    def _create_status_badge(self, status_text):
        """Erstellt Status-Badge wie auf der Website."""
        label = QLabel(status_text.capitalize())
        label.setAlignment(Qt.AlignCenter)
        
        badge_size = FONT_SIZES['badge']
        badge_radius = BORDER_RADIUS['lg']
        
        if status_text == "bezahlt":
            label.setStyleSheet(f"""
                background-color: {COLORS['success_light']};
                color: {COLORS['success_text']};
                border-radius: {badge_radius}px;
                padding: 6px 14px;
                font-size: {badge_size}px;
                font-weight: 600;
            """)
        elif status_text == "überfällig":
            label.setStyleSheet(f"""
                background-color: {COLORS['danger_light']};
                color: {COLORS['danger_text']};
                border-radius: {badge_radius}px;
                padding: 6px 14px;
                font-size: {badge_size}px;
                font-weight: 600;
            """)
        else:  # offen
            label.setStyleSheet(f"""
                background-color: {COLORS['warning_light']};
                color: {COLORS['warning_text']};
                border-radius: {badge_radius}px;
                padding: 6px 14px;
                font-size: {badge_size}px;
                font-weight: 600;
            """)
        
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(SPACING['xs'], 0, 0, 0)
        layout.addWidget(label)
        layout.addStretch()
        return container
    
    def _create_action_buttons(self, rechnung_id):
        """Erstellt Aktions-Buttons (Vorschau, Download, Zahlung, L�schen) wie auf der Website."""
        widget = QWidget()
        widget.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 0, 0, 0)
        layout.setSpacing(8)
        
        icons_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "icons")
        
        # Zentrale Button- und Icon-Styles verwenden
        btn_style = get_toolbar_button_stylesheet()
        icon_size = FONT_SIZES['icon_medium']
        btn_size = FONT_SIZES['btn_medium']
        
        # Vorschau-Button (Auge)
        btn_view = QToolButton()
        btn_view.setIcon(create_gray_icon(os.path.join(icons_path, "preview.svg")))
        btn_view.setIconSize(QSize(icon_size, icon_size))
        btn_view.setFixedSize(btn_size, btn_size)
        btn_view.setStyleSheet(btn_style)
        btn_view.setCursor(Qt.PointingHandCursor)
        btn_view.setToolTip(_("Vorschau"))
        btn_view.clicked.connect(lambda checked, rid=rechnung_id: self._vorschau_by_id(rid))
        layout.addWidget(btn_view)
        
        # Download-Button
        btn_dl = QToolButton()
        btn_dl.setIcon(create_gray_icon(os.path.join(icons_path, "download.svg")))
        btn_dl.setIconSize(QSize(icon_size, icon_size))
        btn_dl.setFixedSize(btn_size, btn_size)
        btn_dl.setStyleSheet(btn_style)
        btn_dl.setCursor(Qt.PointingHandCursor)
        btn_dl.setToolTip(_("PDF exportieren"))
        btn_dl.clicked.connect(lambda checked, rid=rechnung_id: self._export_by_id(rid))
        layout.addWidget(btn_dl)
        
        # Zahlung erfassen Button
        btn_pay = QToolButton()
        btn_pay.setIcon(create_gray_icon(os.path.join(icons_path, "payment.svg")))
        btn_pay.setIconSize(QSize(icon_size, icon_size))
        btn_pay.setFixedSize(btn_size, btn_size)
        btn_pay.setStyleSheet(btn_style)
        btn_pay.setCursor(Qt.PointingHandCursor)
        btn_pay.setToolTip(_("Zahlung erfassen"))
        btn_pay.clicked.connect(lambda checked, rid=rechnung_id: self._zahlung_by_id(rid))
        layout.addWidget(btn_pay)
        
        # Löschen Button
        btn_del = QToolButton()
        btn_del.setIcon(create_gray_icon(os.path.join(icons_path, "delete.svg")))
        btn_del.setIconSize(QSize(icon_size, icon_size))
        btn_del.setFixedSize(btn_size, btn_size)
        btn_del.setStyleSheet(btn_style)
        btn_del.setCursor(Qt.PointingHandCursor)
        btn_del.setToolTip(_("Löschen"))
        btn_del.clicked.connect(lambda checked, rid=rechnung_id: self._delete_by_id(rid))
        layout.addWidget(btn_del)
        
        layout.addStretch()
        return widget
    
    def _vorschau_by_id(self, rechnung_id):
        """Zeigt Vorschau f�r Rechnung."""
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0) and int(self.table.item(row, 0).text()) == rechnung_id:
                self.table.selectRow(row)
                break
        self.vorschau_ausgewaehlte_rechnung()
    
    def _export_by_id(self, rechnung_id):
        """Exportiert Rechnung als PDF."""
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0) and int(self.table.item(row, 0).text()) == rechnung_id:
                self.table.selectRow(row)
                break
        self.exportiere_ausgewaehlte_rechnung()
    
    def _zahlung_by_id(self, rechnung_id):
        """Erfasst Zahlung f�r Rechnung."""
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0) and int(self.table.item(row, 0).text()) == rechnung_id:
                self.table.selectRow(row)
                break
        self._zahlung_erfassen()
    
    def _delete_by_id(self, rechnung_id):
        """L�scht Rechnung."""
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0) and int(self.table.item(row, 0).text()) == rechnung_id:
                self.table.selectRow(row)
                break
        self.loesche_rechnung()

    def _setze_zeilenfarbe(self, row_idx, farbe: QColor):
        """F�rbt die komplette Tabellenzeile ein."""
        brush = QBrush(farbe)
        for c in range(self.table.columnCount()):
            it = self.table.item(row_idx, c)
            if it is None:
                it = QTableWidgetItem("")
                self.table.setItem(row_idx, c, it)
            it.setBackground(brush)

    def lade_rechnungen(self):
        # --- Suchfeld zurücksetzen, da die Daten neu geladen werden ---
        # Mark manual loading to avoid race with background TabLoader
        self._manual_loading = True
        self.suchfeld.blockSignals(True)
        self.suchfeld.clear()
        self.suchfeld.blockSignals(False)

        with get_db() as conn:
            is_sqlite = getattr(conn, "is_sqlite", False)
            with conn.cursor() as cursor:
                
                query = """
                    SELECT id, rechnung_nr, kunde, firma, adresse, datum, mwst, zahlungskonditionen, positionen, uid, abschluss, COALESCE(abschluss_text,'')
                    FROM rechnungen
                """

                # --- KORREKTUR: Sortierung nach Rechnungsnummer (numerisch) ---
                if is_sqlite:
                    # SQLite: CAST zu INTEGER für numerische Sortierung
                    order_clause = "ORDER BY CAST(rechnung_nr AS INTEGER) DESC, id DESC"
                else:
                    # PostgreSQL: CAST zu BIGINT für numerische Sortierung
                    order_clause = "ORDER BY CAST(NULLIF(regexp_replace(rechnung_nr, '\\D', '', 'g'), '') AS BIGINT) DESC NULLS LAST, id DESC"

                cursor.execute(f"{query} {order_clause}")
                daten = cursor.fetchall()

        # Blockiere Signale während des Ladens, um ungewollte Speicherungen zu verhindern
        self.table.blockSignals(True)
        self.rechnungen = []
        self._known_invoice_ids = set()
        self.table.setRowCount(0) # Tabelle leeren

        for (id_, nr, kunde, firma, adresse, datum, mwst, zahlungskonditionen, positionen_json, uid, abschluss, abschluss_text) in daten:
            status_text, farbe = self._berechne_status(str(datum or ""), zahlungskonditionen or "", abschluss or "")

            try:
                positionen = json.loads(positionen_json) if positionen_json else []
            except Exception:
                positionen = []
            
            # --- NEU: Gesamtsumme berechnen ---
            gesamtbetrag_netto = sum(float(pos.get("menge", 0)) * float(pos.get("einzelpreis", 0)) for pos in positionen)
            mwst_prozent = float(mwst or 0)
            mwst_betrag = gesamtbetrag_netto * mwst_prozent / 100.0
            gesamtbetrag_brutto = gesamtbetrag_netto + mwst_betrag


            # Zeile hinzufügen
            row_position = self.table.rowCount()
            self.table.insertRow(row_position)

            # ID (versteckt)
            self.table.setItem(row_position, 0, QTableWidgetItem(str(id_)))
            
            cell_font_size = FONT_SIZES['table_cell']
            
            # Nummer - blau und fett wie auf Website
            item_nr = QTableWidgetItem(nr or "")
            item_nr.setForeground(QColor(COLORS['primary']))
            font_nr = QFont()
            font_nr.setPointSize(cell_font_size)
            font_nr.setWeight(QFont.DemiBold)
            item_nr.setFont(font_nr)
            self.table.setItem(row_position, 1, item_nr)
            
            # Kunde
            item_kunde = QTableWidgetItem(kunde or "")
            item_kunde.setForeground(QColor(COLORS['text_primary']))
            font_kunde = QFont()
            font_kunde.setPointSize(cell_font_size)
            item_kunde.setFont(font_kunde)
            self.table.setItem(row_position, 2, item_kunde)
            
            # Datum formatiert
            datum_str = str(datum or "")
            try:
                if "-" in datum_str:
                    from datetime import datetime as dt
                    d = dt.strptime(datum_str, "%Y-%m-%d")
                    datum_str = d.strftime("%d.%m.%Y")
            except:
                pass
            item_datum = QTableWidgetItem(datum_str)
            item_datum.setForeground(QColor(COLORS['text_secondary']))
            font_datum = QFont()
            font_datum.setPointSize(cell_font_size)
            item_datum.setFont(font_datum)
            self.table.setItem(row_position, 3, item_datum)
            
            # Betrag
            item_betrag = QTableWidgetItem(f"CHF {gesamtbetrag_brutto:,.2f}".replace(",", "'"))
            font_betrag = QFont()
            font_betrag.setPointSize(cell_font_size)
            font_betrag.setWeight(QFont.DemiBold)
            item_betrag.setFont(font_betrag)
            item_betrag.setForeground(QColor(COLORS['text_primary']))
            self.table.setItem(row_position, 4, item_betrag)
            
            # Status-Badge als Widget
            status_widget = self._create_status_badge(status_text)
            self.table.setCellWidget(row_position, 5, status_widget)
            
            # Aktionen-Buttons als Widget
            action_widget = self._create_action_buttons(id_)
            self.table.setCellWidget(row_position, 6, action_widget)

            if id_ is not None:
                try:
                    self._known_invoice_ids.add(int(id_))
                except Exception:
                    pass

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
        
        # Signale wieder freigeben
        self.table.blockSignals(False)
        # Manual load finished - allow background loader to append again
        self._manual_loading = False



    # ---------------- Status-Logik ----------------

    def _berechne_status(self, datum_str, zahlungskonditionen, abschluss):
        """
        Gibt (status_text, farbe_qcolor) zurück.
        - 'abschluss' (bezahlt/offen/überfällig) = manuell -> Vorrang
        - sonst Automatik: Datum + Zahlungsziel (Standard 10 Tage)
        """
        status_man = (abschluss or "").strip().lower()
        if status_man in ("bezahlt", "offen", "überfällig"):
            if status_man == "bezahlt":
                return "bezahlt", PASTELL_GRUEN
            elif status_man == "überfällig":
                return "überfällig", PASTELL_ROT
            else:
                return "offen", PASTELL_ORANGE

        # Automatik
        rechnungsdatum = None
        for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d.%m.%y"):
            try:
                rechnungsdatum = datetime.strptime(datum_str, fmt).date()
                break
            except Exception:
                pass
        if not rechnungsdatum:
            rechnungsdatum = datetime.today().date()

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
        """Status per Button; manuelle Auswahl �berschreibt Automatik (in DB)."""
        zeile = self.table.currentRow()
        if zeile < 0:
            QMessageBox.warning(self, _("Keine Auswahl"), _("Bitte zuerst eine Rechnung ausw�hlen."))
            return
        rechnung_id = int(self.table.item(zeile, 0).text())

        status, ok = themed_get_item(
            self, _("Rechnungsstatus wählen"), _("Status:"),
            ["offen", "bezahlt", "überfällig"], 0, False
        )
        if not ok:
            return

        with get_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute("UPDATE rechnungen SET abschluss=%s WHERE id=%s", (status, rechnung_id))
            conn.commit()

        # UI aktualisieren
        datum = self.table.item(zeile, 3).text()
        zahlk = None
        for r in self.rechnungen:
            if r["id"] == rechnung_id:
                zahlk = r.get("zahlungskonditionen", "")
                r["abschluss"] = status
                break

        status_text, farbe = self._berechne_status(datum, zahlk or "", status)
        self.table.setItem(zeile, 5, QTableWidgetItem(status_text))
        self._setze_zeilenfarbe(zeile, farbe)
        QMessageBox.information(self, _("Rechnung"), _("Status ge�ndert zu: {}").format(status_text))

    def _zahlung_erfassen(self):
        """Zahlung f�r eine Rechnung erfassen und als Buchhaltungseintrag buchen."""
        zeile = self.table.currentRow()
        if zeile < 0:
            QMessageBox.warning(self, _("Keine Auswahl"), _("Bitte zuerst eine Rechnung ausw�hlen."))
            return

        rechnung_id = int(self.table.item(zeile, 0).text())
        rechnung_nr = self.table.item(zeile, 1).text()
        kunde = self.table.item(zeile, 2).text()
        betrag_text = self.table.item(zeile, 4).text()

        # Betrag parsen (z.B. "1'234.56 CHF" ? 1234.56)
        betrag_clean = betrag_text.replace("'", "").replace(" CHF", "").replace(",", ".").strip()
        try:
            betrag = float(betrag_clean)
        except ValueError:
            betrag = 0.0

        dialog = ZahlungErfassenDialog(rechnung_nr, kunde, betrag, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            daten = dialog.get_data()

            # Buchhaltungseintrag erstellen
            with get_db() as conn:
                with conn.cursor() as cursor:
                    # N�chste freie ID ermitteln (f�r Sequenz-Problem bei PostgreSQL)
                    cursor.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM buchhaltung")
                    next_id = cursor.fetchone()[0]
                    
                    cursor.execute("""
                        INSERT INTO buchhaltung (id, datum, typ, kategorie, beschreibung, betrag)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        next_id,
                        daten["datum"],
                        "Einnahme",
                        daten["kategorie"],
                        daten["beschreibung"],
                        daten["betrag"]
                    ))

                    # Rechnung als bezahlt markieren
                    cursor.execute("UPDATE rechnungen SET abschluss=%s WHERE id=%s", ("bezahlt", rechnung_id))

                conn.commit()

            # UI aktualisieren
            datum = self.table.item(zeile, 3).text()
            zahlk = None
            for r in self.rechnungen:
                if r["id"] == rechnung_id:
                    zahlk = r.get("zahlungskonditionen", "")
                    r["abschluss"] = "bezahlt"
                    break

            status_text, farbe = self._berechne_status(datum, zahlk or "", "bezahlt")
            self.table.setItem(zeile, 5, QTableWidgetItem(status_text))
            self._setze_zeilenfarbe(zeile, farbe)

            QMessageBox.information(
                self, _("Zahlung erfasst"),
                _("Zahlung von {} CHF wurde in der Buchhaltung als Einnahme gebucht.\nRechnung wurde als bezahlt markiert.").format(
                    f"{daten['betrag']:,.2f}".replace(",", "'")
                )
            )

            # Signal emittieren um Buchhaltung-Tab zu aktualisieren
            self.zahlung_erfasst.emit()



    # ---------------- CRUD Rechnungen ----------------

    def _ermittle_naechste_rechnungsnummer(self) -> str:
        """Bestimmt die n�chste Rechnungsnummer anhand vorhandener Rechnungen (6-stellig)."""
        with get_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT rechnung_nr FROM rechnungen WHERE rechnung_nr IS NOT NULL AND TRIM(rechnung_nr) <> ''"
                )
                rows = cursor.fetchall()

        max_wert = 0

        for row in rows:
            if isinstance(row, dict):
                wert = row.get("rechnung_nr")
            else:
                try:
                    wert = row[0]
                except Exception:
                    wert = row
            if not wert:
                continue
            if isinstance(wert, bytes):
                try:
                    wert = wert.decode("utf-8")
                except Exception:
                    wert = wert.decode("latin-1", "ignore")
            digits_only = "".join(ch for ch in str(wert).strip() if ch.isdigit())
            if not digits_only:
                continue
            try:
                numeric = int(digits_only)
            except ValueError:
                continue
            if numeric > max_wert:
                max_wert = numeric

        next_value = max_wert + 1 if max_wert > 0 else 1
        return f"{next_value:06d}"

    def neue_rechnung(self):
        vorschlag_nr = self._ermittle_naechste_rechnungsnummer()
        dialog = RechnungDialog(
            self.kunden_liste,
            self.kunden_firmen,
            self.kunden_adressen,
            {"rechnung_nr": vorschlag_nr},
            mwst_voreinstellung=self.mwst_voreinstellung
        )
        if dialog.exec_() == QDialog.Accepted:
            rechnung = dialog.get_rechnung()
            if not rechnung.get("zahlungskonditionen", "").strip():
                rechnung["zahlungskonditionen"] = "zahlbar innert 10 Tagen"
            if not rechnung.get("abschluss", ""):
                rechnung["abschluss"] = ""
            self.speichere_rechnung(rechnung)
            self.lade_rechnungen()

    def bearbeite_rechnung(self):
        zeile = self.table.currentRow()
        if zeile < 0:
            QMessageBox.warning(self, _("Keine Auswahl"), _("Bitte zuerst eine Rechnung ausw�hlen."))
            return
        rechnung_id = int(self.table.item(zeile, 0).text())
        rechnung = self.lade_rechnung_nach_id(rechnung_id)
        if not rechnung:
            QMessageBox.warning(self, _("Fehler"), _("Rechnung nicht gefunden."))
            return

        dialog = RechnungDialog(self.kunden_liste, self.kunden_firmen, self.kunden_adressen, rechnung, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            neue_rechnung = dialog.get_rechnung()
            if not neue_rechnung.get("zahlungskonditionen", "").strip():
                neue_rechnung["zahlungskonditionen"] = "zahlbar innert 10 Tagen"
            self.speichere_rechnung(neue_rechnung, rechnung_id)
            self.lade_rechnungen()

    def loesche_rechnung(self):
        # Support multiple selected rows for bulk delete
        sel = self.table.selectionModel().selectedRows()
        if not sel:
            QMessageBox.warning(self, _("Keine Auswahl"), _("Bitte zuerst eine oder mehrere Rechnungen ausw�hlen."))
            return
        ids = []
        for idx in sel:
            try:
                ids.append(int(self.table.item(idx.row(), 0).text()))
            except Exception:
                pass

        if not ids:
            QMessageBox.warning(self, _("Fehler"), _("Keine g�ltigen IDs in Auswahl gefunden."))
            return

        if QMessageBox.question(self, _("Rechnung(en) l�schen"), _("Soll(en) die ausgew�hlten {0} Rechnung(en) wirklich gel�scht werden?").format(len(ids)), QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return

        try:
            with get_db() as conn:
                with conn.cursor() as cursor:
                    # try postgres-style params
                    try:
                        placeholders = ','.join(['%s'] * len(ids))
                        cursor.execute(f"DELETE FROM rechnungen WHERE id IN ({placeholders})", tuple(ids))
                    except Exception:
                        placeholders = ','.join(['?'] * len(ids))
                        cursor.execute(f"DELETE FROM rechnungen WHERE id IN ({placeholders})", tuple(ids))
                conn.commit()
        except Exception:
            # fallback: delete one-by-one
            with get_db() as conn:
                with conn.cursor() as cursor:
                    for rid in ids:
                        try:
                            cursor.execute("DELETE FROM rechnungen WHERE id = %s", (rid,))
                        except Exception:
                            cursor.execute("DELETE FROM rechnungen WHERE id = ?", (rid,))
                conn.commit()
        self.lade_rechnungen()

    def speichere_rechnung(self, rechnung, rechnung_id=None):
        """Rechnung in DB speichern (neu oder update)"""
        positionen_json = json.dumps(rechnung.get("positionen", []), ensure_ascii=False)
        if rechnung_id is not None:
            with get_db() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE rechnungen SET
                            rechnung_nr = %s, kunde = %s, firma = %s, adresse = %s, datum = %s,
                            mwst = %s, zahlungskonditionen = %s, positionen = %s, uid = %s, abschluss = %s, abschluss_text=%s
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
                        rechnung.get("abschluss_text", ""),
                        rechnung_id
                    ))
                conn.commit()
        else:
            with get_db() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO rechnungen (
                            rechnung_nr, kunde, firma, adresse, datum,
                            mwst, zahlungskonditionen, positionen, uid, abschluss, abschluss_text
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                        rechnung.get("abschluss_text", ""),
                    ))
                conn.commit()

    # ---------------- Helpers ----------------

    def lade_rechnung_nach_id(self, rechnung_id):
        for rechnung in self.rechnungen:
            if rechnung["id"] == rechnung_id:
                return rechnung
        return None

    # ---------------- PDF Export / Vorschau ----------------

    def exportiere_ausgewaehlte_rechnung(self):
        zeile = self.table.currentRow()
        if zeile < 0:
            QMessageBox.warning(self, _("Keine Auswahl"), _("Bitte zuerst eine Rechnung ausw�hlen."))
            return
        rechnung_id = int(self.table.item(zeile, 0).text())
        rechnung = self.lade_rechnung_nach_id(rechnung_id)
        if not rechnung:
            QMessageBox.warning(self, _("Fehler"), _("Rechnung nicht gefunden."))
            return

        # Vorschlag: Rechnung_{nummer}-{kunde}.pdf (Kundenname bereinigt)
        def _make_filename(r):
            nr = r.get('rechnung_nr', '')
            kunde = r.get('kunde') or r.get('firma') or ''
            # Entferne f�r Dateinamen problematische Zeichen und ersetze Leerzeichen durch Unterstrich
            kunde_clean = re.sub(r'[<>:"/\\|\?\*\n\r\t]', '', str(kunde)).strip()
            # Ersetze mehrere Whitespace-Zeichen durch ein einzelnes Leerzeichen
            kunde_clean = re.sub(r'\s+', ' ', kunde_clean)
            base = f"Rechnung_{nr}"
            if kunde_clean:
                base = f"{base}-{kunde_clean}"
            return f"{base}.pdf"

        pfad, _filter = QFileDialog.getSaveFileName(self, "PDF speichern", _make_filename(rechnung), "PDF-Dateien (*.pdf)")
        if pfad:
            try:
                self._exportiere_pdf(rechnung, pfad, logo_skala=self.layout_config.get("logo_skala", 100))
                QMessageBox.information(self, _("Erfolg"), _("PDF wurde gespeichert unter:\n{}").format(pfad))
            except Exception as e:
                QMessageBox.critical(self, _("Fehler"), _("Fehler beim PDF Export:\n{}").format(str(e)))

    def vorschau_ausgewaehlte_rechnung(self):
        zeile = self.table.currentRow()
        if zeile < 0:
            QMessageBox.warning(self, _("Keine Auswahl"), _("Bitte zuerst eine Rechnung ausw�hlen."))
            return

        rechnung_id = int(self.table.item(zeile, 0).text())
        rechnung = self.lade_rechnung_nach_id(rechnung_id)
        if not rechnung:
            QMessageBox.warning(self, _("Fehler"), _("Rechnung nicht gefunden."))
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

    def _zeichne_kopf_design(self, c, width, height, stil, design_typ):
        """Zeichnet dekorative Kopfbereich-Elemente basierend auf dem Stil."""
        kopf_farbe = stil.get("kopf_farbe", stil.get("akzent_farbe", colors.Color(0.2, 0.2, 0.2)))
        kopf_farbe2 = stil.get("kopf_farbe2", kopf_farbe)
        kopf_akzent = stil.get("kopf_akzent", stil.get("akzent_farbe2", kopf_farbe))
        kopf_hoehe = stil.get("kopf_hoehe", 35) * mm
        gold_akzent = stil.get("gold_akzent")
        
        if design_typ == "full_width_bar":
            # Volle Breite Balken am oberen Rand
            c.setFillColor(kopf_farbe)
            c.rect(0, height - kopf_hoehe, width, kopf_hoehe, fill=True, stroke=False)
            
        elif design_typ == "double_lines":
            # Zwei horizontale Linien - oben und unter Logo-Bereich
            c.setStrokeColor(kopf_farbe)
            c.setLineWidth(2)
            c.line(20*mm, height - 15*mm, width - 20*mm, height - 15*mm)
            c.line(20*mm, height - 55*mm, width - 20*mm, height - 55*mm)
            
        elif design_typ == "diagonal_corners":
            # Diagonale Ecken wie in Bild 1 - Oben links + Unten rechts
            # Obere linke Ecke - Hauptfarbe
            c.setFillColor(kopf_farbe)
            path = c.beginPath()
            path.moveTo(0, height)
            path.lineTo(80*mm, height)
            path.lineTo(0, height - 50*mm)
            path.close()
            c.drawPath(path, fill=True, stroke=False)
            
            # Untere rechte Ecke - Akzentfarbe
            c.setFillColor(kopf_farbe2)
            path2 = c.beginPath()
            path2.moveTo(width, 0)
            path2.lineTo(width - 120*mm, 0)
            path2.lineTo(width, 70*mm)
            path2.close()
            c.drawPath(path2, fill=True, stroke=False)
            
            # Footer-Balken
            c.setFillColor(kopf_farbe)
            c.rect(0, 0, width - 120*mm, 25*mm, fill=True, stroke=False)
            
        elif design_typ == "right_stripe_diagonal":
            # Rechter Streifen + Diagonale Ecke wie in Bild 2
            # Rechter Streifen
            c.setFillColor(kopf_farbe)
            c.rect(width - 18*mm, 0, 18*mm, height, fill=True, stroke=False)
            
            # Diagonale Ecke oben rechts
            c.setFillColor(kopf_farbe2)
            path = c.beginPath()
            path.moveTo(width - 18*mm, height)
            path.lineTo(width - 80*mm, height)
            path.lineTo(width - 18*mm, height - 60*mm)
            path.close()
            c.drawPath(path, fill=True, stroke=False)
            
            # Header-Balken oben links
            c.setFillColor(kopf_farbe)
            c.rect(0, height - 30*mm, 110*mm, 30*mm, fill=True, stroke=False)
            
        elif design_typ == "gradient_bars":
            # Gradient-Balken oben und unten wie in Bild 4
            # Oberer Balken mit diagonalen Streifen-Effekt
            c.setFillColor(kopf_farbe)
            c.rect(0, height - 25*mm, width * 0.4, 25*mm, fill=True, stroke=False)
            c.setFillColor(kopf_farbe2)
            c.rect(width * 0.4, height - 25*mm, width * 0.6, 25*mm, fill=True, stroke=False)
            
            # Diagonale Streifen oben
            c.setFillColor(kopf_farbe)
            for i in range(3):
                x_start = width * 0.35 + i * 8*mm
                path = c.beginPath()
                path.moveTo(x_start, height)
                path.lineTo(x_start + 15*mm, height)
                path.lineTo(x_start + 15*mm - 25*mm, height - 25*mm)
                path.lineTo(x_start - 25*mm, height - 25*mm)
                path.close()
                c.drawPath(path, fill=True, stroke=False)
            
            # Unterer Balken
            c.setFillColor(kopf_farbe2)
            c.rect(0, 0, width * 0.6, 20*mm, fill=True, stroke=False)
            c.setFillColor(kopf_farbe)
            c.rect(width * 0.6, 0, width * 0.4, 20*mm, fill=True, stroke=False)
            
        elif design_typ == "wave_corners":
            # Wellenf�rmige Ecken wie in Bild 6
            # Obere linke Wellen-Ecke
            c.setFillColor(kopf_farbe)
            path = c.beginPath()
            path.moveTo(0, height)
            path.lineTo(90*mm, height)
            path.curveTo(70*mm, height - 30*mm, 50*mm, height - 50*mm, 0, height - 60*mm)
            path.close()
            c.drawPath(path, fill=True, stroke=False)
            
            # Untere rechte Wellen-Ecke
            c.setFillColor(kopf_farbe2)
            path2 = c.beginPath()
            path2.moveTo(width, 0)
            path2.lineTo(width - 90*mm, 0)
            path2.curveTo(width - 70*mm, 30*mm, width - 50*mm, 50*mm, width, 60*mm)
            path2.close()
            c.drawPath(path2, fill=True, stroke=False)
            
        elif design_typ == "top_bar":
            # Einfacher Balken oben
            c.setFillColor(kopf_farbe)
            c.rect(0, height - 20*mm, width, 20*mm, fill=True, stroke=False)
            
        elif design_typ == "left_stripe":
            # Linker Streifen
            c.setFillColor(kopf_farbe)
            c.rect(0, 0, 15*mm, height, fill=True, stroke=False)
            
        elif design_typ == "left_stripe_gold":
            # Linker Streifen mit Gold-Akzent
            c.setFillColor(kopf_farbe)
            c.rect(0, 0, 15*mm, height, fill=True, stroke=False)
            if gold_akzent:
                c.setFillColor(gold_akzent)
                c.rect(0, height - 50*mm, 15*mm, 50*mm, fill=True, stroke=False)
                c.rect(0, 0, 15*mm, 30*mm, fill=True, stroke=False)
                
        elif design_typ == "accent_lines":
            # Akzent-Linien oben und links
            c.setFillColor(kopf_farbe2)
            c.rect(0, height - 10*mm, width, 10*mm, fill=True, stroke=False)
            c.rect(0, 0, 8*mm, height - 10*mm, fill=True, stroke=False)
            
        elif design_typ == "diagonal_triangle":
            # Diagonales Dreieck
            c.setFillColor(kopf_farbe)
            path = c.beginPath()
            path.moveTo(0, height)
            path.lineTo(130*mm, height)
            path.lineTo(0, height - 110*mm)
            path.close()
            c.drawPath(path, fill=True, stroke=False)

    def _exportiere_pdf(self, rechnung, dateipfad, logo_skala=1.0):
        # Layout frisch laden, damit Vorschau das aktuelle Logo nutzt
        try:
            self._lade_rechnungslayout()
        except Exception:
            pass
        c = canvas.Canvas(dateipfad, pagesize=A4)
        width, height = A4
        
        # Stil laden f�r Kopfbereich-Design
        stil_name = self.layout_config.get("stil", "classic")
        stil = get_stil(stil_name)
        
        # === KOPFBEREICH-DESIGN ZEICHNEN ===
        kopf_design = stil.get("kopf_design")
        if kopf_design:
            self._zeichne_kopf_design(c, width, height, stil, kopf_design)

        # Bl�cke
        blocks = {
            "logo":      (20*mm, 250*mm, 170*mm, 35*mm),
            "adresse":   (20*mm, 200*mm, 70*mm, 25*mm),
            "details":   (140*mm, 215*mm, 70*mm, 25*mm),
            "betreff":   (20*mm, 178*mm, 170*mm, 5*mm),
            "einleitung":(20*mm, 159*mm, 170*mm, 15*mm),
            "fusszeile": (20*mm, 10*mm, 170*mm, 10*mm),
        }

        rand_links = 20 * mm

        # Schriftfarbe
        c.setFillColorRGB(*[v / 255 for v in self.layout_config["farbe_text"]])

        # Logo ODER Kopfzeile (im Logo-Block) - nicht beides!
        x_logo, y_logo, w_logo, h_logo = blocks["logo"]
        eff_scale = int(self.layout_config.get("logo_skala") or logo_skala or 100)
        logo_bytes = self.layout_config.get("logo_bytes")
        logo_pfad = self.layout_config.get("logo_datei")
        hat_logo = False
        
        try:
            if logo_bytes:
                reader = ImageReader(io.BytesIO(bytes(logo_bytes)))
                ow, oh = reader.getSize()
                factor = min(w_logo / ow, h_logo / oh, 1.0) * (eff_scale / 100.0)
                lw = max(1, ow * factor)
                lh = max(1, oh * factor)
                lx = x_logo
                ly = y_logo + h_logo - lh  # oben links im Block
                c.drawImage(reader, lx, ly, width=lw, height=lh, mask='auto')
                hat_logo = True
            elif logo_pfad and os.path.exists(logo_pfad):
                reader = ImageReader(logo_pfad)
                ow, oh = reader.getSize()
                factor = min(w_logo / ow, h_logo / oh, 1.0) * (eff_scale / 100.0)
                lw = max(1, ow * factor)
                lh = max(1, oh * factor)
                lx = x_logo
                ly = y_logo + h_logo - lh
                c.drawImage(reader, lx, ly, width=lw, height=lh, mask='auto')
                hat_logo = True
        except Exception as e:
            print(_("Logo-Fehler:"), e)

        # Kopfzeile (Firmeninfo) - NUR wenn kein Logo gesetzt ist!
        if not hat_logo:
            kopfzeile = self.layout_config.get("kopfzeile", "")
            if kopfzeile:
                schrift_sz = self.layout_config["schriftgroesse"]
                c.setFont(self.layout_config["schrift_bold"], schrift_sz + 2)
                c.setFillColor(colors.black)
                textobj = c.beginText()
                textobj.setTextOrigin(x_logo, y_logo + h_logo - schrift_sz - 2)
                textobj.setLeading((schrift_sz + 2) * 1.3)
                for zeile in kopfzeile.splitlines()[:4]:  # Max 4 Zeilen
                    textobj.textLine(zeile[:60])
                c.drawText(textobj)

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
        
        # Stil-basiertes Tabellen-Layout
        stil_name = self.layout_config.get("stil", "classic")
        stil = get_stil(stil_name)
        
        table_styles = [
            ('ALIGN', (2,1), (4,-1), 'RIGHT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('FONTSIZE', (0,0), (-1,-1), self.layout_config["schriftgroesse"]),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]
        
        # Header-Styling
        if stil.get("header_bg"):
            table_styles.append(('BACKGROUND', (0, 0), (-1, 0), stil["header_bg"]))
        if stil.get("header_text"):
            table_styles.append(('TEXTCOLOR', (0, 0), (-1, 0), stil["header_text"]))
        if stil.get("header_fett"):
            table_styles.append(('FONTNAME', (0, 0), (-1, 0), self.layout_config["schrift_bold"]))
        
        # Zeilen-Styling
        if stil.get("zeile_alternierend"):
            for i in range(2, len(daten_tabelle), 2):
                table_styles.append(('BACKGROUND', (0, i), (-1, i), stil["zeile_alternierend"]))
        
        # Linien-Styling
        if stil.get("tabelle_gitter"):
            table_styles.append(('GRID', (0,0), (-1,-1), stil.get("linien_staerke", 0.5), stil.get("linien_farbe", colors.black)))
        elif stil.get("nur_horizontale_linien"):
            # Nur horizontale Linien
            table_styles.append(('LINEBELOW', (0, 0), (-1, 0), stil.get("linien_staerke", 0.5), stil.get("linien_farbe", colors.grey)))
            table_styles.append(('LINEBELOW', (0, -1), (-1, -1), stil.get("linien_staerke", 0.5), stil.get("linien_farbe", colors.grey)))
            # D�nne Linien zwischen Zeilen
            for i in range(1, len(daten_tabelle) - 1):
                table_styles.append(('LINEBELOW', (0, i), (-1, i), 0.25, stil.get("linien_farbe", colors.Color(0.9, 0.9, 0.9))))
        
        if stil.get("header_linie_unten"):
            table_styles.append(('LINEBELOW', (0, 0), (-1, 0), 1.5, stil.get("akzent_farbe", colors.black)))
        
        t.setStyle(TableStyle(table_styles))
        t_w, t_h = t.wrap(0,0)
        y_pos = A4[1] - 140 * mm - t_h
        t.drawOn(c, rand_links, y_pos)

        # MWST-Berechnung
        mwst_prozent = float(rechnung.get("mwst", self.mwst))
        mwst_betrag = gesamtbetrag_netto * mwst_prozent / 100.0
        gesamtbetrag_brutto = gesamtbetrag_netto + mwst_betrag

        # Summen
        summen_x = rand_links + 40 * mm
        summen_y = y_pos - 8 * mm
        gesamt_x = summen_x + 128 * mm
        label_x = summen_x + 103 * mm

        # Total-Box f�r bestimmte Stile
        if stil.get("total_box"):
            total_betrag = gesamtbetrag_brutto if abs(mwst_prozent) >= 0.01 else gesamtbetrag_netto
            box_width = 60 * mm
            box_height = 12 * mm
            box_x = gesamt_x - box_width + 2 * mm
            box_y = summen_y - (25 if abs(mwst_prozent) >= 0.01 else 5) - box_height + 8
            
            # Box zeichnen
            if stil.get("total_bg"):
                c.setFillColor(stil["total_bg"])
                c.rect(box_x, box_y, box_width, box_height, fill=True, stroke=False)
            if stil.get("total_rahmen"):
                c.setStrokeColor(stil["total_rahmen"])
                c.rect(box_x, box_y, box_width, box_height, fill=False, stroke=True)
            
            # Text in Box
            if stil.get("total_text"):
                c.setFillColor(stil["total_text"])
            c.setFont(self.layout_config["schrift_bold"], self.layout_config["schriftgroesse"] + 1)
            c.drawString(box_x + 4, box_y + 4, f"Total: {total_betrag:.2f} CHF")
            
            # Netto und MWST dar�ber (wenn vorhanden)
            c.setFillColorRGB(*[v / 255 for v in self.layout_config["farbe_text"]])
            if abs(mwst_prozent) >= 0.01:
                c.setFont(self.layout_config["schrift"], self.layout_config["schriftgroesse"])
                c.drawRightString(label_x, summen_y, "Netto:")
                c.drawRightString(gesamt_x, summen_y, f"{gesamtbetrag_netto:.2f} CHF")
                c.drawRightString(label_x, summen_y - 12, f"MWST ({mwst_prozent:.2f}%):")
                c.drawRightString(gesamt_x, summen_y - 12, f"{mwst_betrag:.2f} CHF")
        else:
            # Klassische Summen-Darstellung
            c.setFont(self.layout_config["schrift_bold"], self.layout_config["schriftgroesse"])
            if abs(mwst_prozent) < 0.01:
                c.drawRightString(label_x, summen_y, "Total:")
                c.setFont(self.layout_config["schrift"], self.layout_config["schriftgroesse"])
                c.drawRightString(gesamt_x, summen_y, f"{gesamtbetrag_netto:.2f} CHF")
            else:
                c.drawRightString(label_x, summen_y, "Netto:")
                c.drawRightString(label_x, summen_y - 12, f"MWST ({mwst_prozent:.2f}%):")
                c.drawRightString(label_x, summen_y - 24, "Total brutto:")
                c.setFont(self.layout_config["schrift"], self.layout_config["schriftgroesse"])
                c.drawRightString(gesamt_x, summen_y, f"{gesamtbetrag_netto:.2f} CHF")
                c.drawRightString(gesamt_x, summen_y - 12, f"{mwst_betrag:.2f} CHF")
                c.drawRightString(gesamt_x, summen_y - 24, f"{gesamtbetrag_brutto:.2f} CHF")

        # Zahlungsbedingungen
        zahlungstext = (rechnung.get("zahlungskonditionen") or "").strip()
        c.setFont(self.layout_config["schrift"], self.layout_config["schriftgroesse"])
        leading = self.layout_config["schriftgroesse"] * 1.3

        y_zahlung = summen_y - 30  # Startpunkt beibehalten
        next_y = y_zahlung

        if zahlungstext:
            textobj = c.beginText()
            textobj.setTextOrigin(rand_links, y_zahlung)
            textobj.setLeading(leading)
            zahl_lines = zahlungstext.splitlines()
            for zeile in zahlungstext.splitlines():
                textobj.textLine(zeile)
            c.drawText(textobj)
            # genau 2 Zeilen Abstand; f�r 3 Zeilen �ndere zu gap_lines = 3
            gap_lines = 3
            next_y = y_zahlung - leading * (len(zahl_lines) + gap_lines)

        # Abschiedsgruss (oder "abschluss") genau 2 Zeilen unter Zahlungsbedingungen
        abschluss_text = (rechnung.get("abschluss_text") or rechnung.get("abschluss") or "").strip()
        if abschluss_text:
            textobj = c.beginText()
            textobj.setTextOrigin(rand_links, next_y)
            textobj.setLeading(leading)
            for zeile in abschluss_text.splitlines():
                textobj.textLine(zeile)
            c.drawText(textobj)

        # Fusszeile aus dem Layout-Dialog (JSON-Key 'fusszeile') – zentriert
        x_f, y_f, w_f, h_f = blocks["fusszeile"]
        fuss = self.layout_config.get("fusszeile", {}) or {}
        fuss_text  = (fuss.get("text") or "").strip()
        fuss_font  = fuss.get("schrift", self.layout_config["schrift"])
        fuss_size  = int(fuss.get("groesse", self.layout_config["schriftgroesse"]))
        fuss_farbe = fuss.get("farbe", [100, 100, 100])

        if isinstance(fuss, dict):
            fuss_text = (fuss.get("text") or "").strip()
        elif isinstance(fuss, str):
            fuss_text = fuss.strip()
        else:
            try:
                fuss_text = str(fuss).strip()
            except Exception:
                fuss_text = ""


        if fuss_text:
            # Farbe optional �bernehmen
            try:
                c.setFillColorRGB(*(v/255 for v in fuss_farbe))
            except Exception:
                pass

            c.setFont(fuss_font, fuss_size)
            leading = fuss_size * 1.15
            x_center = x_f + w_f / 2.0
            y_line = y_f + h_f - fuss_size  # obere Linie im Fusszeilen-Block

            for line in fuss_text.splitlines():
                c.drawCentredString(x_center, y_line, line)
                y_line -= leading

            # Schriftfarbe f�r nachfolgende Elemente zur�cksetzen
            c.setFillColorRGB(*[v/255 for v in self.layout_config["farbe_text"]])


        # QR-Code Seite
        c.showPage()
        self.zeichne_swiss_qr(c, rechnung, gesamtbetrag_brutto)

        c.showPage()
        c.save()

    def zeichne_swiss_qr(self, canvas_obj, rechnung, betrag):
        """Generiert einen Swiss QR-Code und platziert ihn im PDF (via qrbill)."""
        try:
            qr_data = _get_qr_daten()
            creditor = qr_data.get("creditor") or {
                'name': "Deine Firma GmbH", 'street': "Musterstrasse 1",
                'pcode': "8000", 'city': "Z�rich", 'country': "CH",
            }
            iban = qr_data.get("iban") or "CH5800791123000889012"
            currency = qr_data.get("currency", "CHF")
        except Exception as e:
            creditor = {
                'name': "Deine Firma GmbH",
                'street': "Musterstrasse 1",
                'pcode': "8000",
                'city': "Z�rich",
                'country': "CH",
            }
            iban = "CH5800791123000889012"
            currency = "CHF"
            print(_("Fehler beim Laden von qr_daten.json:"), e)

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

        try:
            from qrbill import QRBill
        except Exception as e:
            # qrbill nicht installiert -> zeige Hinweis und �berspringe QR-Code
            try:
                QMessageBox.warning(self, _("Fehler"), _("QR-Code Modul 'qrbill' ist nicht installiert. Bitte installieren Sie es (z.B. 'pip install qrbill'), um Swiss QR-Bills zu generieren."))
            except Exception:
                # Falls QMessageBox in diesem Kontext Probleme macht, nur Log
                print("qrbill fehlt:", e)
            return
        amount = Decimal(str(betrag)) if betrag is not None else Decimal("0")

        my_bill = QRBill(
            account=iban,
            creditor=creditor,
            amount=amount,
            debtor=debtor,
            currency=currency,
            language='de'
        )

        # SVG generieren und ins PDF einfügen (Textmodus für svgwrite)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".svg", mode="w", encoding="utf-8") as tmp_svg:
            try:
                my_bill.as_svg(tmp_svg)
            except Exception as e:
                try:
                    QMessageBox.warning(self, _("Fehler"), _("Fehler beim Erstellen des QR-Code SVG: {}").format(str(e)))
                except Exception:
                    print(_("Fehler beim Erstellen des QR-Code SVG:"), e)
                return
            tmp_svg_path = tmp_svg.name

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

        try:
            os.remove(tmp_svg_path)
        except Exception:
            pass

     # ---------------- Async UI helpers (moved inside class) ----------------
    def get_row_id(self, row_index) -> int | None:
        """Return numeric ID for given row or None if not found."""
        try:
            if row_index < 0 or row_index >= self.table.rowCount():
                return None
            it = self.table.item(row_index, 0)
            if it is not None:
                d = it.data(Qt.UserRole)
                if isinstance(d, int):
                    return d
                txt = (it.text() or "").strip()
                if txt.lstrip("-").isdigit():
                    return int(txt)
            for c in range(self.table.columnCount()):
                it = self.table.item(row_index, c)
                if it:
                    txt = (it.text() or "").strip()
                    if txt.lstrip("-").isdigit():
                        return int(txt)
        except Exception:
            pass
        return None

    def append_rows(self, rows):
        """Append a chunk of rows (dicts or sequences) into the Rechnungen table (newest first)."""
        try:
            # If a manual filtered load is in progress, skip background appends to avoid mixed state
            if getattr(self, "_manual_loading", False):
                return
            if not rows:
                return
            try:
                if hasattr(self, "_loading_label") and self._loading_label:
                    self._loading_label.hide()
            except Exception:
                pass

            expected_cols = ["id", "rechnung_nr", "kunde", "firma", "adresse", "datum", "mwst",
                             "zahlungskonditionen", "positionen", "uid", "abschluss", "abschluss_text"]

            if self.table.columnCount() == 0:
                try:
                    self._setup_table()
                    header = self.table.horizontalHeader()
                    header.setSectionResizeMode(2, QHeaderView.Stretch)
                except Exception:
                    pass

            try:
                self.table.setSortingEnabled(False)
                self.table.setUpdatesEnabled(False)
            except Exception:
                pass

            # insert newest-first: loader expected to deliver ORDER BY datum DESC
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

                id_val = values[0]
                try:
                    numeric_id = int(id_val)
                except Exception:
                    numeric_id = None
                if numeric_id is not None and numeric_id in getattr(self, "_known_invoice_ids", set()):
                    continue

                # insert a new top row
                try:
                    self.table.insertRow(0)
                    insert_index = 0
                except Exception:
                    start = self.table.rowCount()
                    self.table.setRowCount(start + 1)
                    insert_index = start

                id_text = "" if id_val is None else str(id_val)
                item_id = QTableWidgetItem(id_text)
                try:
                    if isinstance(id_val, int) or (isinstance(id_val, str) and id_text.lstrip("-").isdigit()):
                        item_id.setData(Qt.UserRole, int(id_text))
                except Exception:
                    pass
                self.table.setItem(insert_index, 0, item_id)

                # --- KORREKTUR: Spalten korrekt bef�llen ---
                try:
                    # Spalten 1-3: Rechnungs-Nr, Kunde, Datum
                    self.table.setItem(insert_index, 1, QTableWidgetItem(str(values[1] or "")))
                    self.table.setItem(insert_index, 2, QTableWidgetItem(str(values[2] or "")))
                    self.table.setItem(insert_index, 3, QTableWidgetItem(str(values[5] or "")))

                    # Spalte 4: Gesamtsumme berechnen
                    positionen = json.loads(values[8]) if isinstance(values[8], str) and values[8] else (values[8] if isinstance(values[8], list) else [])
                    mwst_prozent = float(values[6] or 0)
                    gesamtbetrag_netto = sum(float(pos.get("menge", 0)) * float(pos.get("einzelpreis", 0)) for pos in positionen)
                    mwst_betrag = gesamtbetrag_netto * mwst_prozent / 100.0
                    gesamtbetrag_brutto = gesamtbetrag_netto + mwst_betrag
                    # --- KORREKTUR: Item erstellen und zentrieren ---
                    item_summe = QTableWidgetItem(f"{gesamtbetrag_brutto:.2f} CHF")
                    item_summe.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(insert_index, 4, item_summe)

                    # Spalte 5: Status und Farbe
                    status_text, farbe = self._berechne_status(str(values[5] or ""), values[7] or "", values[10] or "")
                    self.table.setItem(insert_index, 5, QTableWidgetItem(status_text))
                    self._setze_zeilenfarbe(insert_index, farbe)
                except Exception:
                    pass

                # --- ENTFERNT: Alter, fehlerhafter Codeblock ---

                # keep internal cache consistent (prepend)
                try:
                    rec = {
                        "id": values[0],
                        "rechnung_nr": values[1],
                        "kunde": values[2],
                        "firma": values[3],
                        "adresse": values[4],
                        "datum": values[5],
                        "mwst": values[6],
                        "zahlungskonditionen": values[7],
                        "positionen": json.loads(values[8]) if isinstance(values[8], str) and values[8] else (values[8] if isinstance(values[8], list) else []),
                        "uid": values[9],
                        "abschluss": values[10],
                        "abschluss_text": values[11] if len(values) > 11 else ""
                    }
                except Exception:
                    rec = {}
                try:
                    self.rechnungen.insert(0, rec)
                except Exception:
                    self.rechnungen = [rec] + getattr(self, "rechnungen", [])

            # restore updates and one resize
                    if numeric_id is not None:
                        self._known_invoice_ids.add(numeric_id)
            try:
                self.table.setUpdatesEnabled(True)
                self.table.setSortingEnabled(True)
                self.table.resizeColumnsToContents()
            except Exception:
                pass

        except Exception as e:
            print(f"[DBG] RechnungenTab.append_rows error: {e}", flush=True)

    def load_finished(self):
        """Called when loader finished. Show 'Keine Rechnungen' if empty."""
        try:
            if self.table.rowCount() == 0:
                try:
                    if hasattr(self, "_loading_label") and self._loading_label:
                        self._loading_label.setText(_("Keine Rechnungen"))
                        self._loading_label.show()
                except Exception:
                    pass
            else:
                try:
                    if hasattr(self, "_loading_label") and self._loading_label:
                        self._loading_label.hide()
                except Exception:
                    pass
        except Exception as e:
            print(f"[DBG] RechnungenTab.load_finished error: {e}", flush=True)
    # ------------------------------------------------------------------------


    def draw_logo_from_db_or_path(c, x, y, w, h, file_path=None):
        """
        Zeichnet das Logo an (x,y) mit Breite w und Höhe h.
        Nimmt zuerst das Logo aus der DB, sonst (Fallback) den übergebenen Dateipfad.
        """
        img = get_invoice_logo_imagereader()
        try:
            if img is not None:
                c.drawImage(img, x, y, width=w, height=h, preserveAspectRatio=True, mask='auto')
            elif file_path:
                c.drawImage(file_path, x, y, width=w, height=h, preserveAspectRatio=True, mask='auto')
        except Exception as e:
            print("Logo-Zeichnung fehlgeschlagen:", e)

def _get_qr_daten():
    """L�dt QR-Daten aus DB (mit Fallback auf JSON)."""
    try:
        from db_connection import get_qr_daten
        return get_qr_daten()
    except Exception as e:
        print(_("Fehler beim Laden aus DB:"), e)
        # Fallback auf JSON
        qr = get_json("qr_daten")
        if qr is None:
            qr = import_json_if_missing("qr_daten", "config/qr_daten.json") or {}
        return qr


