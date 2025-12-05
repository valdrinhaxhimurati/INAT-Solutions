# datei: gui/rechnung_layout_dialog.py
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QTextEdit, QPushButton, QHBoxLayout,
    QMessageBox, QFileDialog, QSlider, QSpinBox, QGroupBox, QFormLayout,
    QComboBox, QFrame, QGridLayout, QScrollArea, QWidget, QSplitter
)
from PyQt5.QtCore import Qt, QTimer, QByteArray
from PyQt5.QtGui import QPixmap, QColor, QPainter, QFont, QImage
from .base_dialog import BaseDialog
from .dialog_styles import GROUPBOX_STYLE
from .rechnung_styles import RECHNUNG_STYLES, get_stil, get_alle_stile
from db_connection import get_db
import os, mimetypes, sqlite3, io, tempfile
from i18n import _

# ReportLab imports für PDF-Vorschau
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from reportlab.lib.utils import ImageReader

def _ensure_table(con):
    """Erstellt die Tabelle rechnung_layout, falls nötig (SQLite/PG)."""
    try:
        with con.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS rechnung_layout (
                    id INTEGER PRIMARY KEY,
                    kopfzeile   TEXT,
                    einleitung  TEXT,
                    fusszeile   TEXT,
                    logo        BLOB,
                    logo_mime   TEXT,
                    logo_skala  REAL
                )
            """)
        con.commit()
        return
    except Exception:
        con.rollback()
    # PostgreSQL-Fallback
    with con.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS rechnung_layout (
                id INTEGER PRIMARY KEY,
                kopfzeile   TEXT,
                einleitung  TEXT,
                fusszeile   TEXT,
                logo        BYTEA,
                logo_mime   TEXT,
                logo_skala  REAL
            )
        """)
    con.commit()

def _ensure_logo_columns(con):
    """Stellt sicher, dass die Spalten logo und logo_mime existieren (SQLite/PG)."""
    try:
        with con.cursor() as cur:
            cols = set()
            for r in cur.execute("PRAGMA table_info(rechnung_layout)"):
                name = r[1] if isinstance(r, tuple) else r["name"]
                cols.add(str(name).lower())
            if "logo" not in cols:
                cur.execute("ALTER TABLE rechnung_layout ADD COLUMN logo BLOB")
            if "logo_mime" not in cols:
                cur.execute("ALTER TABLE rechnung_layout ADD COLUMN logo_mime TEXT")
        con.commit()
        return
    except Exception:
        con.rollback()
    # PostgreSQL-Fallback
    with con.cursor() as cur:
        cur.execute("ALTER TABLE rechnung_layout ADD COLUMN IF NOT EXISTS logo bytea")
        cur.execute("ALTER TABLE rechnung_layout ADD COLUMN IF NOT EXISTS logo_mime text")
    con.commit()

def _ensure_rechnung_layout_table_exists(conn):
    """Stellt sicher, dass Tabelle 'rechnung_layout' und benötigte Spalten existieren."""
    try:
        # Connection may be a sqlite3.Connection or a ConnectionWrapper from get_db().
        is_sqlite = getattr(conn, "is_sqlite", False) or getattr(conn, "is_sqlite_conn", False) or "sqlite" in getattr(conn.__class__, "__module__", "")
    except Exception:
        is_sqlite = False

    cur = conn.cursor()
    try:
        if is_sqlite:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS rechnung_layout (
                id TEXT PRIMARY KEY,
                kopfzeile TEXT,
                einleitung TEXT,
                fusszeile TEXT,
                logo BLOB,
                logo_mime TEXT,
                logo_skala REAL
            )
            """)
            conn.commit()
            # prüfe vorhandene Spalten
            cur.execute("PRAGMA table_info(rechnung_layout)")
            existing = {r[1] for r in cur.fetchall()}
            needed = {
                "kopfzeile": "TEXT",
                "einleitung": "TEXT",
                "fusszeile": "TEXT",
                "logo": "BLOB",
                "logo_mime": "TEXT",
                "logo_skala": "REAL",
            }
            for col, typ in needed.items():
                if col not in existing:
                    try:
                        cur.execute(f"ALTER TABLE rechnung_layout ADD COLUMN {col} {typ}")
                    except Exception:
                        pass
            conn.commit()
        else:
            # Postgres / andere DBs
            cur.execute("""
            CREATE TABLE IF NOT EXISTS rechnung_layout (
                id TEXT PRIMARY KEY,
                kopfzeile TEXT,
                einleitung TEXT,
                fusszeile TEXT,
                logo BYTEA,
                logo_mime TEXT,
                logo_skala REAL
            )
            """)
            conn.commit()
            # versuche IF NOT EXISTS Varianten, fallback auf einfache ALTER
            alter_stmts = [
                "ALTER TABLE rechnung_layout ADD COLUMN IF NOT EXISTS kopfzeile TEXT",
                "ALTER TABLE rechnung_layout ADD COLUMN IF NOT EXISTS einleitung TEXT",
                "ALTER TABLE rechnung_layout ADD COLUMN IF NOT EXISTS fusszeile TEXT",
                "ALTER TABLE rechnung_layout ADD COLUMN IF NOT EXISTS logo BYTEA",
                "ALTER TABLE rechnung_layout ADD COLUMN IF NOT EXISTS logo_mime TEXT",
                "ALTER TABLE rechnung_layout ADD COLUMN IF NOT EXISTS logo_skala REAL",
            ]
            for s in alter_stmts:
                try:
                    cur.execute(s)
                except Exception:
                    try:
                        # Fallback ohne IF NOT EXISTS
                        simple = s.replace("ALTER TABLE rechnung_layout ADD COLUMN IF NOT EXISTS ", "ALTER TABLE rechnung_layout ADD COLUMN ")
                        cur.execute(simple)
                    except Exception:
                        pass
            conn.commit()
    finally:
        try:
            cur.close()
        except Exception:
            pass

def _ensure_default_row(con):
    """Sorgt dafür, dass eine Default-Zeile existiert. Robust gegen unterschiedlichen id-Typen."""
    try:
        _ensure_rechnung_layout_table_exists(con)
    except Exception:
        pass

    try:
        is_sqlite = getattr(con, "is_sqlite", False) or getattr(con, "is_sqlite_conn", False) or "sqlite" in getattr(con.__class__, "__module__", "")
    except Exception:
        is_sqlite = False

    cur = con.cursor()
    try:
        # Default-Werte
        defaults = ("", "", "", None, None, 100.0)

        if is_sqlite:
            # Bestimme Typ der id-Spalte, damit wir keinen datatype mismatch erzeugen
            try:
                cur.execute("PRAGMA table_info(rechnung_layout)")
                info = cur.fetchall()
                id_type = None
                for r in info:
                    # r[1]=name, r[2]=type
                    if r[1].lower() == "id":
                        id_type = (r[2] or "").lower()
                        break
                id_is_integer = id_type is not None and ("int" in id_type)
            except Exception:
                id_is_integer = False

            # Wähle einen id-Wert passend zum Typ
            id_val = 1 if id_is_integer else "default"

            # INSERT OR IGNORE (fügt nur ein, wenn noch kein Eintrag mit dieser id existiert)
            try:
                cur.execute(
                    "INSERT OR IGNORE INTO rechnung_layout (id, kopfzeile, einleitung, fusszeile, logo, logo_mime, logo_skala) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (id_val, *defaults)
                )
            except Exception:
                # Fallback: ohne id (falls id AUTOINCREMENT INTEGER PK und INSERT OR IGNORE scheitert)
                try:
                    cur.execute(
                        "INSERT OR IGNORE INTO rechnung_layout (kopfzeile, einleitung, fusszeile, logo, logo_mime, logo_skala) VALUES (?, ?, ?, ?, ?, ?)",
                        defaults
                    )
                except Exception:
                    pass

            # Aktualisiere fehlende Felder (nur wenn Spalten NULL sind)
            try:
                cur.execute(
                    """
                    UPDATE rechnung_layout
                    SET
                      kopfzeile = COALESCE(kopfzeile, ?),
                      einleitung = COALESCE(einleitung, ?),
                      fusszeile = COALESCE(fusszeile, ?),
                      logo = COALESCE(logo, ?),
                      logo_mime = COALESCE(logo_mime, ?),
                      logo_skala = COALESCE(logo_skala, ?)
                    WHERE id = ?
                    """,
                    (*defaults, id_val)
                )
            except Exception:
                # Falls WHERE id = ? nicht passt (z.B. es wurde ohne id eingefügt), versuche ein generelles UPDATE für NULL-Werte
                try:
                    cur.execute(
                        """
                        UPDATE rechnung_layout
                        SET
                          kopfzeile = COALESCE(kopfzeile, ?),
                          einleitung = COALESCE(einleitung, ?),
                          fusszeile = COALESCE(fusszeile, ?),
                          logo = COALESCE(logo, ?),
                          logo_mime = COALESCE(logo_mime, ?),
                          logo_skala = COALESCE(logo_skala, ?)
                        """,
                        defaults
                    )
                except Exception:
                    pass

        else:
            # Nicht-SQLite (z.B. Postgres) — benutzte Platzhalter %s und ON CONFLICT
            sql = """
            INSERT INTO rechnung_layout (id, kopfzeile, einleitung, fusszeile, logo, logo_mime, logo_skala)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT(id) DO UPDATE SET
                kopfzeile = COALESCE(rechnung_layout.kopfzeile, EXCLUDED.kopfzeile),
                einleitung = COALESCE(rechnung_layout.einleitung, EXCLUDED.einleitung),
                fusszeile = COALESCE(rechnung_layout.fusszeile, EXCLUDED.fusszeile),
                logo = COALESCE(rechnung_layout.logo, EXCLUDED.logo),
                logo_mime = COALESCE(rechnung_layout.logo_mime, EXCLUDED.logo_mime),
                logo_skala = COALESCE(rechnung_layout.logo_skala, EXCLUDED.logo_skala)
            """
            try:
                cur.execute(sql, ("default", *defaults))
            except Exception:
                # Fallback: falls id-Spalte numerisch ist, verwende 1
                try:
                    cur.execute(sql, (1, *defaults))
                except Exception:
                    pass

        con.commit()
    finally:
        try:
            cur.close()
        except Exception:
            pass

def _row_to_dict(cur, row):
    if row is None:
        return {}
    if isinstance(row, dict):
        return row
    cols = [d[0] for d in getattr(cur, "description", [])]
    try:
        # sqlite3.Row
        return {k: row[k] for k in row.keys()}
    except Exception:
        return dict(zip(cols, row)) if cols else {}


class RechnungLayoutDialog(BaseDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle(_("Rechnungslayout bearbeiten"))
        self.setMinimumSize(1450, 1000)
        self.resize(1450, 1000)
        
        # Timer für verzögerte Vorschau-Aktualisierung
        self._preview_timer = QTimer()
        self._preview_timer.setSingleShot(True)
        self._preview_timer.timeout.connect(self._update_live_preview)
        
        # Haupt-Layout mit Splitter
        main_layout = self.content_layout
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(8)
        
        # === LINKE SEITE: Einstellungen ===
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(12)
        left_layout.setContentsMargins(15, 15, 10, 15)
        
        # --- STIL-AUSWAHL ---
        stil_group = QGroupBox(_("Rechnungs-Stil"))
        stil_group.setStyleSheet(GROUPBOX_STYLE)
        stil_inner = QHBoxLayout(stil_group)
        stil_inner.setSpacing(15)
        stil_inner.setContentsMargins(15, 20, 15, 15)
        
        stil_left = QVBoxLayout()
        stil_label = QLabel(_("Design:"))
        stil_left.addWidget(stil_label)
        
        self.stil_dropdown = QComboBox()
        self.stil_dropdown.setMinimumWidth(180)
        for stil_key in get_alle_stile():
            stil_info = RECHNUNG_STYLES[stil_key]
            self.stil_dropdown.addItem(stil_info["name"], stil_key)
        self.stil_dropdown.currentIndexChanged.connect(self._on_stil_changed)
        stil_left.addWidget(self.stil_dropdown)
        
        self.stil_beschreibung = QLabel()
        self.stil_beschreibung.setStyleSheet("color: #666; font-size: 11px;")
        self.stil_beschreibung.setWordWrap(True)
        stil_left.addWidget(self.stil_beschreibung)
        stil_left.addStretch()
        stil_inner.addLayout(stil_left)
        
        left_layout.addWidget(stil_group)
        self.aktueller_stil = "klassisch"

        # --- TEXTFELDER ---
        text_group = QGroupBox(_("Texte für Rechnung"))
        text_group.setStyleSheet(GROUPBOX_STYLE)
        text_layout = QVBoxLayout(text_group)
        text_layout.setSpacing(8)
        text_layout.setContentsMargins(15, 20, 15, 15)

        kopf_label = QLabel(_("Kopfzeile (z. B. Firmeninfo):"))
        text_layout.addWidget(kopf_label)
        self.text_kopf = QTextEdit()
        self.text_kopf.setMinimumHeight(80)
        self.text_kopf.setMaximumHeight(100)
        self.text_kopf.setPlaceholderText(_("Ihre Firmenadresse, Kontaktdaten etc."))
        self.text_kopf.textChanged.connect(self._schedule_preview_update)
        text_layout.addWidget(self.text_kopf)
        
        # Hinweis wenn Logo aktiv ist
        self.kopf_hinweis = QLabel(_("⚠ Kopfzeile deaktiviert - Logo hat Priorität. Entfernen Sie das Logo um die Kopfzeile zu nutzen."))
        self.kopf_hinweis.setStyleSheet("color: #888; font-style: italic; font-size: 13px; padding: 5px;")
        self.kopf_hinweis.setWordWrap(True)
        self.kopf_hinweis.hide()
        text_layout.addWidget(self.kopf_hinweis)

        einl_label = QLabel(_("Einleitungstext:"))
        text_layout.addWidget(einl_label)
        self.text_einleitung = QTextEdit()
        self.text_einleitung.setMinimumHeight(80)
        self.text_einleitung.setMaximumHeight(100)
        self.text_einleitung.setPlaceholderText(_("Sehr geehrte Damen und Herren, ..."))
        self.text_einleitung.textChanged.connect(self._schedule_preview_update)
        text_layout.addWidget(self.text_einleitung)

        fuss_label = QLabel(_("Fußzeile:"))
        text_layout.addWidget(fuss_label)
        self.text_fuss = QTextEdit()
        self.text_fuss.setMinimumHeight(80)
        self.text_fuss.setMaximumHeight(100)
        self.text_fuss.setPlaceholderText(_("Bankverbindung, Zahlungshinweise etc."))
        self.text_fuss.textChanged.connect(self._schedule_preview_update)
        text_layout.addWidget(self.text_fuss)
        
        left_layout.addWidget(text_group)

        # --- LOGO ---
        logo_group = QGroupBox(_("Firmenlogo"))
        logo_group.setStyleSheet(GROUPBOX_STYLE)
        logo_layout = QVBoxLayout(logo_group)
        logo_layout.setSpacing(10)
        logo_layout.setContentsMargins(15, 20, 15, 15)
        
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        self.btn_logo_auswaehlen = QPushButton(_("Logo auswählen"))
        self.btn_logo_entfernen = QPushButton(_("Logo entfernen"))
        btn_row.addWidget(self.btn_logo_auswaehlen)
        btn_row.addWidget(self.btn_logo_entfernen)
        btn_row.addStretch()
        logo_layout.addLayout(btn_row)

        scale_row = QHBoxLayout()
        scale_row.setSpacing(10)
        scale_label = QLabel(_("Größe:"))
        scale_row.addWidget(scale_label)
        self.scale_slider = QSlider(Qt.Horizontal)
        self.scale_slider.setRange(10, 300)
        self.scale_slider.setTickInterval(10)
        self.scale_spin = QSpinBox()
        self.scale_spin.setRange(10, 300)
        self.scale_spin.setSuffix(" %")
        self.scale_spin.setMinimumWidth(80)
        self.scale_slider.setValue(100)
        self.scale_spin.setValue(100)
        self.scale_slider.valueChanged.connect(self._on_slider_change)
        self.scale_spin.valueChanged.connect(self._on_spin_change)
        scale_row.addWidget(self.scale_slider, 1)
        scale_row.addWidget(self.scale_spin)
        logo_layout.addLayout(scale_row)
        
        left_layout.addWidget(logo_group)
        left_layout.addStretch()

        # Buttons unten links (zentriert)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_abbrechen = QPushButton(_("Abbrechen"))
        self.btn_speichern = QPushButton(_("Speichern"))
        btn_layout.addWidget(self.btn_abbrechen)
        btn_layout.addWidget(self.btn_speichern)
        btn_layout.addStretch()
        left_layout.addLayout(btn_layout)
        
        splitter.addWidget(left_widget)

        # === RECHTE SEITE: Live-Vorschau ===
        right_widget = QWidget()
        right_widget.setStyleSheet("background-color: #f0f0f0;")
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(10)
        right_layout.setContentsMargins(10, 15, 15, 15)
        
        preview_header = QLabel(_("📄 Live-Vorschau"))
        preview_header.setStyleSheet("font-size: 14px; font-weight: bold; color: #333; background: transparent;")
        right_layout.addWidget(preview_header)
        
        # Scroll-Area für Vorschau
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea { 
                border: 1px solid #ccc; 
                border-radius: 4px; 
                background: #888;
            }
        """)
        
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        self.preview_label.setStyleSheet("background: white; padding: 10px;")
        self.preview_label.setTextFormat(Qt.RichText)
        self.preview_label.setWordWrap(True)
        scroll_area.setWidget(self.preview_label)
        
        right_layout.addWidget(scroll_area, 1)
        
        splitter.addWidget(right_widget)
        
        # Splitter-Größen setzen (35% links, 65% rechts)
        splitter.setSizes([500, 950])
        main_layout.addWidget(splitter)

        # State
        self.logo_bytes = None
        self.logo_mime = None
        self.logo_skala = 100.0
        
        # Beispiel-Rechnung für Vorschau (fiktive Daten mit 10 Positionen = Maximum)
        self._beispiel_rechnung = {
            "rechnung_nr": "2025-0042",
            "datum": "02.12.2025",
            "uid": "CHE-123.456.789",
            "firma": "Muster AG",
            "kunde": "Max Mustermann",
            "adresse": "Beispielstrasse 123\n3000 Bern",
            "mwst": 8.1,
            "positionen": [
                {"beschreibung": "Beratung und Konzeptentwicklung", "menge": 5, "einzelpreis": 120.00},
                {"beschreibung": "Technische Umsetzung Phase 1", "menge": 8, "einzelpreis": 95.00},
                {"beschreibung": "Technische Umsetzung Phase 2", "menge": 6, "einzelpreis": 95.00},
                {"beschreibung": "Dokumentation", "menge": 2, "einzelpreis": 80.00},
                {"beschreibung": "Schulung vor Ort", "menge": 4, "einzelpreis": 150.00},
                {"beschreibung": "Support-Paket (12 Monate)", "menge": 1, "einzelpreis": 480.00},
                {"beschreibung": "Materialkosten", "menge": 1, "einzelpreis": 250.00},
                {"beschreibung": "Reisekosten pauschal", "menge": 1, "einzelpreis": 120.00},
                {"beschreibung": "Projektmanagement", "menge": 3, "einzelpreis": 110.00},
                {"beschreibung": "Abschluss und Übergabe", "menge": 2, "einzelpreis": 90.00},
            ]
        }

        # Connects
        self.btn_logo_auswaehlen.clicked.connect(self.logo_auswaehlen)
        self.btn_logo_entfernen.clicked.connect(self.logo_entfernen)
        self.btn_speichern.clicked.connect(self.speichern)
        self.btn_abbrechen.clicked.connect(self.reject)

        # DB vorbereiten und laden
        con = get_db()
        try:
            _ensure_table(con)
            _ensure_logo_columns(con)
            _ensure_default_row(con)
        finally:
            try: con.close()
            except Exception: pass

        self.lade_layout()
        
        # Initiale Vorschau-Aktualisierung
        QTimer.singleShot(100, self._update_live_preview)
    
    def _schedule_preview_update(self):
        """Verzögert die Vorschau-Aktualisierung um 300ms (vermeidet zu häufige Updates)."""
        self._preview_timer.start(300)
    
    def _update_live_preview(self):
        """Generiert eine PDF-Vorschau der Rechnung und zeigt sie an."""
        try:
            # PDF in Speicher generieren
            pdf_bytes = self._generate_preview_pdf()
            print(f"[PREVIEW] PDF generiert: {len(pdf_bytes) if pdf_bytes else 0} bytes")
            
            if not pdf_bytes:
                self.preview_label.setText(_("PDF konnte nicht generiert werden"))
                return
            
            # PDF zu Bild konvertieren mit PyMuPDF
            pixmap = self._pdf_to_pixmap(pdf_bytes)
            print(f"[PREVIEW] Pixmap: {pixmap is not None}, isNull: {pixmap.isNull() if pixmap else 'N/A'}")
            
            if pixmap and not pixmap.isNull():
                self.preview_label.setPixmap(pixmap)
                print("[PREVIEW] Pixmap gesetzt!")
            else:
                self.preview_label.setText(_("Vorschau konnte nicht erstellt werden"))
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.preview_label.setText(f"Fehler: {str(e)}")
    
    def _show_html_preview(self):
        """Zeigt eine HTML-basierte Vorschau an (Fallback wenn PDF nicht funktioniert)."""
        stil = get_stil(self.aktueller_stil)
        farbe = stil.get("vorschau_farbe", "#4A6FA5")
        rechnung = self._beispiel_rechnung
        
        # Header-Styling
        if stil.get("header_bg"):
            header_style = f"background-color: {farbe}; color: white;"
        else:
            header_style = "background-color: #f5f5f5; color: #333;"
        
        # Berechne Total
        total = sum(float(p.get("menge", 0)) * float(p.get("einzelpreis", 0)) for p in rechnung.get("positionen", []))
        
        # Logo als Base64 (wenn vorhanden)
        logo_html = ""
        if self.logo_bytes:
            import base64
            logo_b64 = base64.b64encode(self.logo_bytes).decode('utf-8')
            mime = self.logo_mime or "image/png"
            scale = int(self.logo_skala)
            max_w = int(200 * scale / 100)
            max_h = int(80 * scale / 100)
            logo_html = f'<img src="data:{mime};base64,{logo_b64}" style="max-width: {max_w}px; max-height: {max_h}px;">'
        
        einleitung = self.text_einleitung.toPlainText() or "Sehr geehrte Damen und Herren"
        fusszeile = self.text_fuss.toPlainText() or ""
        
        # Zweite Einleitungszeile
        einleitung_zeile2 = "Wir erlauben uns, Ihnen wie folgt in Rechnung zu stellen:"
        
        html = f"""
        <div style="font-family: Arial, sans-serif; padding: 30px 40px; background: white; min-height: 700px; max-width: 595px; margin: 0 auto; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
            
            <!-- Kopfbereich: Logo links, Details rechts -->
            <table style="width: 100%; margin-bottom: 30px;">
                <tr>
                    <td style="vertical-align: top; width: 60%;">
                        {logo_html}
                    </td>
                    <td style="vertical-align: top; text-align: right; font-size: 11px; color: #555;">
                        UID: {rechnung.get('uid', '')}<br>
                        Rechnungsnummer: {rechnung.get('rechnung_nr', '')}<br>
                        Datum: {rechnung.get('datum', '')}
                    </td>
                </tr>
            </table>
            
            <!-- Kundenadresse -->
            <div style="margin-bottom: 40px; font-size: 12px;">
                <strong>{rechnung.get('firma', '')}</strong><br>
                {rechnung.get('kunde', '')}<br>
                {rechnung.get('adresse', '').replace(chr(10), '<br>')}
            </div>
            
            <!-- Betreff -->
            <h2 style="margin: 25px 0 15px 0; font-size: 18px; font-weight: bold;">Rechnung</h2>
            
            <!-- Einleitung -->
            <p style="font-size: 11px; color: #333; margin-bottom: 5px;">{einleitung}</p>
            <p style="font-size: 11px; color: #333; margin-bottom: 20px;">{einleitung_zeile2}</p>
            
            <!-- Positionen-Tabelle -->
            <table style="width: 100%; border-collapse: collapse; font-size: 11px;">
                <tr style="{header_style}">
                    <td style="padding: 10px 8px; font-weight: bold; width: 8%;">Pos</td>
                    <td style="padding: 10px 8px; font-weight: bold; width: 44%;">Beschreibung</td>
                    <td style="padding: 10px 8px; font-weight: bold; text-align: right; width: 12%;">Anzahl</td>
                    <td style="padding: 10px 8px; font-weight: bold; text-align: right; width: 18%;">Einzelpreis</td>
                    <td style="padding: 10px 8px; font-weight: bold; text-align: right; width: 18%;">Gesamtpreis</td>
                </tr>
        """
        
        for i, pos in enumerate(rechnung.get("positionen", []), 1):
            anzahl = float(pos.get("menge", 0))
            einzelpreis = float(pos.get("einzelpreis", 0))
            gesamtpreis = anzahl * einzelpreis
            row_style = "background-color: #f9f9f9;" if i % 2 == 0 and stil.get("zeile_alternierend") else ""
            html += f"""
                <tr style="{row_style}">
                    <td style="padding: 8px; border-bottom: 1px solid #ddd;">{i}</td>
                    <td style="padding: 8px; border-bottom: 1px solid #ddd;">{pos.get('beschreibung', '')}</td>
                    <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: right;">{anzahl:.2f}</td>
                    <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: right;">{einzelpreis:.2f} CHF</td>
                    <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: right;">{gesamtpreis:.2f} CHF</td>
                </tr>
            """
        
        html += "</table>"
        
        # Zahlungshinweis
        html += '<p style="margin-top: 25px; font-size: 11px;">Zahlbar inner 10 Tagen</p>'
        
        # Total-Box (wie im Beispielbild - breite farbige Box)
        if stil.get("total_box"):
            html += f"""
            <table style="width: 100%; margin-top: 10px;">
                <tr>
                    <td style="width: 50%;"></td>
                    <td style="background-color: {farbe}; color: white; padding: 12px 20px; font-weight: bold; font-size: 13px; text-align: left;">
                        Total: {total:.2f} CHF
                    </td>
                </tr>
            </table>
            """
        else:
            html += f"""
            <div style="margin-top: 20px; text-align: right; font-weight: bold; font-size: 13px;">
                Total: {total:.2f} CHF
            </div>
            """
        
        # Gruss
        html += f'<p style="margin-top: 35px; font-size: 11px;">Freundliche grüsse {fusszeile.split(chr(10))[0] if fusszeile else ""}</p>'
        
        # Fußzeile (zentriert unten)
        if fusszeile:
            html += f"""
            <div style="position: relative; margin-top: 80px; text-align: center; font-size: 10px; color: #555;">
                {fusszeile.replace(chr(10), '<br>')}
            </div>
            """
        
        html += "</div>"
        
        self.preview_label.setText(html)
    
    def _generate_preview_pdf(self):
        """Generiert ein PDF der Beispielrechnung mit aktuellen Einstellungen.
        WICHTIG: Verwendet das Standard-Layout, das mit rechnungen_tab.py übereinstimmt!
        Die verschiedenen Stile beeinflussen nur Farben, Kopf-Design, Tabellen-Styling etc."""
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        
        # Stil laden
        stil = get_stil(self.aktueller_stil)
        
        # Beispieldaten
        rechnung = self._beispiel_rechnung
        positionen = rechnung.get("positionen", [])
        gesamtbetrag = sum(float(p.get("menge", 0)) * float(p.get("einzelpreis", 0)) for p in positionen)
        mwst_satz = rechnung.get("mwst", 8.1)
        mwst_betrag = gesamtbetrag * mwst_satz / 100
        total_mit_mwst = gesamtbetrag + mwst_betrag
        
        kopfzeile = self.text_kopf.toPlainText() or ""
        einleitung = self.text_einleitung.toPlainText() or "Sehr geehrte Damen und Herren"
        fuss_text = self.text_fuss.toPlainText() or ""
        
        # Immer Standard-Layout verwenden (wie rechnungen_tab.py)
        # Die Stile beeinflussen nur: Kopf-Design, Farben, Tabellen-Styling
        self._render_standard_layout(c, width, height, stil, rechnung, positionen, gesamtbetrag, mwst_satz, mwst_betrag, total_mit_mwst, kopfzeile, einleitung, fuss_text)
        
        c.save()
        return buffer.getvalue()
    
    def _draw_logo(self, c, x, y, max_w, max_h, on_dark=False):
        """Zeichnet das Logo an der angegebenen Position."""
        if not self.logo_bytes:
            return 0, 0
        try:
            reader = ImageReader(io.BytesIO(bytes(self.logo_bytes)))
            ow, oh = reader.getSize()
            factor = min(max_w / ow, max_h / oh, 1.0) * (self.logo_skala / 100.0)
            lw = max(1, ow * factor)
            lh = max(1, oh * factor)
            c.drawImage(reader, x, y, width=lw, height=lh, mask='auto')
            return lw, lh
        except Exception:
            return 0, 0
    
    def _draw_positionen_tabelle(self, c, x, y, stil, positionen, gesamtbetrag):
        """Zeichnet die Positionen-Tabelle und gibt Höhe zurück.
        WICHTIG: Spaltenbreiten müssen mit rechnungen_tab.py übereinstimmen!"""
        spalten = ["Pos", "Beschreibung", "Anzahl", "Einzelpreis", "Gesamtpreis"]
        daten = [spalten]
        
        for i, pos in enumerate(positionen, 1):
            anzahl = float(pos.get("menge", 0))
            einzelpreis = float(pos.get("einzelpreis", 0))
            gesamt = anzahl * einzelpreis
            daten.append([str(i), pos.get("beschreibung", ""), f"{anzahl:.2f}", 
                         f"{einzelpreis:.2f} CHF", f"{gesamt:.2f} CHF"])
        
        # Gleiche Spaltenbreiten wie in rechnungen_tab.py!
        t = Table(daten, colWidths=[10*mm, 95*mm, 15*mm, 25*mm, 25*mm])
        
        # Kompaktere Zeilenhöhe für 10 Positionen
        styles = [
            ('ALIGN', (2,0), (-1,-1), 'RIGHT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('FONTNAME', (0,0), (-1,0), "Helvetica-Bold"),
        ]
        
        if stil.get("header_bg"):
            styles.append(('BACKGROUND', (0,0), (-1,0), stil["header_bg"]))
        if stil.get("header_text"):
            styles.append(('TEXTCOLOR', (0,0), (-1,0), stil["header_text"]))
        if stil.get("zeile_alternierend"):
            for i in range(2, len(daten), 2):
                styles.append(('BACKGROUND', (0,i), (-1,i), stil["zeile_alternierend"]))
        if stil.get("tabelle_gitter"):
            styles.append(('GRID', (0,0), (-1,-1), 0.5, stil.get("linien_farbe", colors.black)))
        elif stil.get("nur_horizontale_linien"):
            styles.append(('LINEBELOW', (0,0), (-1,0), 0.5, stil.get("linien_farbe", colors.grey)))
            for i in range(1, len(daten)):
                styles.append(('LINEBELOW', (0,i), (-1,i), 0.25, stil.get("linien_farbe", colors.Color(0.9,0.9,0.9))))
        
        t.setStyle(TableStyle(styles))
        tw, th = t.wrap(0, 0)
        t.drawOn(c, x, y - th)
        return th
    
    def _render_standard_layout(self, c, width, height, stil, rechnung, positionen, gesamtbetrag, mwst_satz, mwst_betrag, total_mit_mwst, kopfzeile, einleitung, fuss_text):
        """Standard-Layout: Verwendet die gleichen Block-Positionen wie rechnungen_tab.py"""
        # WICHTIG: Diese Block-Positionen müssen mit rechnungen_tab.py übereinstimmen!
        blocks = {
            "logo":      (20*mm, 250*mm, 170*mm, 35*mm),
            "adresse":   (20*mm, 200*mm, 70*mm, 25*mm),
            "details":   (140*mm, 215*mm, 70*mm, 25*mm),
            "betreff":   (20*mm, 178*mm, 170*mm, 5*mm),
            "einleitung":(20*mm, 159*mm, 170*mm, 15*mm),
            "fusszeile": (20*mm, 10*mm, 170*mm, 10*mm),
        }
        rand = 20*mm
        schriftgroesse = 10
        
        # Kopf-Design
        if stil.get("kopf_design"):
            self._draw_kopf_design(c, width, height, stil, stil["kopf_design"])
        
        # Logo ODER Kopfzeile (im Logo-Block) - nicht beides!
        x_logo, y_logo, w_logo, h_logo = blocks["logo"]
        
        if self.logo_bytes:
            # Logo anzeigen (hat Priorität)
            try:
                reader = ImageReader(io.BytesIO(bytes(self.logo_bytes)))
                ow, oh = reader.getSize()
                factor = min(w_logo / ow, h_logo / oh, 1.0) * (self.logo_skala / 100.0)
                lw = max(1, ow * factor)
                lh = max(1, oh * factor)
                lx = x_logo
                ly = y_logo + h_logo - lh  # oben links im Block
                c.drawImage(reader, lx, ly, width=lw, height=lh, mask='auto')
            except Exception:
                pass
        elif kopfzeile:
            # Kopfzeile anzeigen (nur wenn kein Logo)
            c.setFont("Helvetica-Bold", schriftgroesse + 2)
            c.setFillColor(colors.black)
            textobj = c.beginText()
            textobj.setTextOrigin(x_logo, y_logo + h_logo - schriftgroesse - 2)
            textobj.setLeading((schriftgroesse + 2) * 1.3)
            for z in kopfzeile.split("\n")[:4]:  # Max 4 Zeilen
                textobj.textLine(z[:60])
            c.drawText(textobj)
        
        # Rechnungsdetails (im Details-Block rechts)
        x_det, y_det, w_det, h_det = blocks["details"]
        c.setFont("Helvetica", schriftgroesse)
        c.setFillColor(colors.black)
        textobj = c.beginText()
        textobj.setTextOrigin(x_det, y_det + h_det - schriftgroesse)
        textobj.setLeading(schriftgroesse * 1.2)
        uid = rechnung.get("uid", "")
        if uid: textobj.textLine(f"UID: {uid}")
        textobj.textLine(f"Rechnungsnummer: {rechnung['rechnung_nr']}")
        textobj.textLine(f"Datum: {rechnung['datum']}")
        c.drawText(textobj)
        
        # Kundenadresse (im Adresse-Block)
        x_adr, y_adr, w_adr, h_adr = blocks["adresse"]
        c.setFont("Helvetica-Bold", schriftgroesse)
        textobj = c.beginText()
        textobj.setTextOrigin(x_adr, y_adr + h_adr - schriftgroesse)
        textobj.setLeading(schriftgroesse * 1.2)
        if rechnung.get("firma"): textobj.textLine(rechnung["firma"])
        if rechnung.get("kunde"): textobj.textLine(rechnung["kunde"])
        c.setFont("Helvetica", schriftgroesse)
        for z in rechnung.get("adresse", "").split("\n"):
            textobj.textLine(z)
        c.drawText(textobj)
        
        # Betreff (im Betreff-Block)
        x_betr, y_betr, w_betr, h_betr = blocks["betreff"]
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x_betr, y_betr + h_betr - 12, "Rechnung")
        
        # Einleitung (im Einleitung-Block)
        x_einl, y_einl, w_einl, h_einl = blocks["einleitung"]
        c.setFont("Helvetica", schriftgroesse)
        textobj = c.beginText()
        textobj.setTextOrigin(x_einl, y_einl + h_einl - schriftgroesse)
        textobj.setLeading(schriftgroesse * 1.2)
        for z in str(einleitung).split("\n")[:2]:  # Max 2 Zeilen
            textobj.textLine(z[:90])
        c.drawText(textobj)
        
        # Tabelle (startet bei 140mm vom oberen Rand, wie in rechnungen_tab.py)
        tabelle_y = height - 140*mm
        th = self._draw_positionen_tabelle(c, rand, tabelle_y, stil, positionen, gesamtbetrag)
        
        # Summen (direkt unter Tabelle)
        summen_y = tabelle_y - th - 8*mm
        gesamt_x = rand + 168*mm
        label_x = rand + 143*mm
        
        c.setFont("Helvetica-Bold", schriftgroesse)
        c.drawRightString(label_x, summen_y, "Netto:")
        c.drawRightString(label_x, summen_y - 12, f"MWST ({mwst_satz:.1f}%):")
        c.drawRightString(label_x, summen_y - 24, "Total brutto:")
        c.setFont("Helvetica", schriftgroesse)
        c.drawRightString(gesamt_x, summen_y, f"{gesamtbetrag:.2f} CHF")
        c.drawRightString(gesamt_x, summen_y - 12, f"{mwst_betrag:.2f} CHF")
        c.drawRightString(gesamt_x, summen_y - 24, f"{total_mit_mwst:.2f} CHF")
        
        # Fusszeile (im Fusszeile-Block)
        if fuss_text:
            x_f, y_f, w_f, h_f = blocks["fusszeile"]
            c.setFont("Helvetica", 8)
            c.setFillColor(colors.Color(0.4, 0.4, 0.4))
            x_center = x_f + w_f / 2.0
            y_line = y_f + h_f - 8
            for line in str(fuss_text).split("\n")[:2]:
                c.drawCentredString(x_center, y_line, line[:100])
                y_line -= 10
    
    def _render_dark_layout(self, c, width, height, stil, rechnung, positionen, gesamtbetrag, mwst_satz, mwst_betrag, total_mit_mwst, einleitung, fuss_text):
        """Dark Mode: Großer dunkler Header-Bereich."""
        rand = 25*mm
        kopf_h = 85*mm
        
        # Dunkler Header
        c.setFillColor(stil.get("kopf_farbe", colors.Color(0.12, 0.16, 0.22)))
        c.rect(0, height - kopf_h, width, kopf_h, fill=True, stroke=False)
        
        # Logo auf dunklem Hintergrund (zentriert oben)
        if self.logo_bytes:
            self._draw_logo(c, rand, height - 45*mm, 55*mm, 25*mm)
        
        # "INVOICE" groß rechts auf dunklem Hintergrund
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 28)
        c.drawRightString(width - rand, height - 35*mm, "RECHNUNG")
        
        # Details auf dunklem Hintergrund
        c.setFont("Helvetica", 10)
        c.drawString(width - 80*mm, height - 55*mm, f"Nr: {rechnung['rechnung_nr']}")
        c.drawString(width - 80*mm, height - 67*mm, f"Datum: {rechnung['datum']}")
        
        # Kundenadresse (auf weiß)
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(rand, height - kopf_h - 20*mm, "Rechnungsempfänger:")
        c.setFont("Helvetica", 10)
        c.drawString(rand, height - kopf_h - 32*mm, rechnung["firma"])
        c.drawString(rand, height - kopf_h - 44*mm, rechnung["kunde"])
        for i, z in enumerate(rechnung["adresse"].split("\n")):
            c.drawString(rand, height - kopf_h - 56*mm - i*12, z)
        
        # Tabelle
        tabelle_y = height - kopf_h - 90*mm
        th = self._draw_positionen_tabelle(c, rand, tabelle_y, stil, positionen, gesamtbetrag)
        
        # Total mit Aufschlüsselung
        total_y = tabelle_y - th - 10*mm
        c.setFont("Helvetica", 10)
        c.drawRightString(width - rand - 40*mm, total_y, "Zwischensumme:")
        c.drawRightString(width - rand, total_y, f"{gesamtbetrag:.2f} CHF")
        c.drawRightString(width - rand - 40*mm, total_y - 14, f"MwSt ({mwst_betrag:.1f}%):")
        c.drawRightString(width - rand, total_y - 14, f"{mwst_betrag:.2f} CHF")
        
        # Total-Box
        c.setFillColor(stil.get("total_bg", colors.Color(0.2, 0.24, 0.3)))
        c.rect(width - rand - 80*mm, total_y - 38*mm, 80*mm, 10*mm, fill=True, stroke=False)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 11)
        c.drawRightString(width - rand - 2*mm, total_y - 32*mm, f"Total: {total_mit_mwst:.2f} CHF")
        
        # Fußzeile
        if fuss_text:
            c.setFillColor(colors.Color(0.4,0.4,0.4))
            c.setFont("Helvetica", 8)
            fy = 20*mm
            for z in fuss_text.split("\n")[:2]:
                c.drawCentredString(width/2, fy, z)
                fy -= 10
    
    def _render_header_footer_layout(self, c, width, height, stil, rechnung, positionen, gesamtbetrag, mwst_satz, mwst_betrag, total_mit_mwst, einleitung, fuss_text):
        """Boutique: Header-Balken oben UND Footer-Balken unten."""
        rand = 20*mm
        kopf_h = 45*mm
        footer_h = 18*mm
        
        # Header
        c.setFillColor(stil.get("kopf_farbe", colors.Color(0.2, 0.26, 0.33)))
        c.rect(0, height - kopf_h, width, kopf_h, fill=True, stroke=False)
        
        # Footer
        c.rect(0, 0, width, footer_h, fill=True, stroke=False)
        
        # Logo im Header (weiß-freundlich)
        self._draw_logo(c, rand, height - 38*mm, 50*mm, 28*mm)
        
        # Firmeninfo rechts im Header
        c.setFillColor(colors.white)
        c.setFont("Helvetica", 9)
        c.drawRightString(width - rand, height - 18*mm, "Ihr Unternehmen")
        c.drawRightString(width - rand, height - 28*mm, "info@beispiel.ch")
        c.drawRightString(width - rand, height - 38*mm, "+41 00 000 00 00")
        
        # INVOICE Titel
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 11)
        c.drawString(rand, height - kopf_h - 20*mm, "RECHNUNG")
        c.setFont("Helvetica-Bold", 18)
        c.drawString(rand + 25*mm, height - kopf_h - 20*mm, f"#{rechnung['rechnung_nr']}")
        
        # Datum rechts
        c.setFont("Helvetica", 10)
        c.drawRightString(width - rand, height - kopf_h - 20*mm, rechnung['datum'])
        
        # Kundenadresse
        c.setFont("Helvetica", 10)
        c.drawString(rand, height - kopf_h - 40*mm, rechnung["firma"])
        c.drawString(rand, height - kopf_h - 52*mm, rechnung["kunde"])
        for i, z in enumerate(rechnung["adresse"].split("\n")):
            c.drawString(rand, height - kopf_h - 64*mm - i*12, z)
        
        # Tabelle
        tabelle_y = height - kopf_h - 100*mm
        th = self._draw_positionen_tabelle(c, rand, tabelle_y, stil, positionen, gesamtbetrag)
        
        # Total rechts
        total_y = tabelle_y - th - 15*mm
        c.setFont("Helvetica", 10)
        c.drawRightString(width - rand - 35*mm, total_y, "Subtotal:")
        c.drawRightString(width - rand, total_y, f"{gesamtbetrag:.2f} CHF")
        c.drawRightString(width - rand - 35*mm, total_y - 14, "MwSt:")
        c.drawRightString(width - rand, total_y - 14, f"{mwst_betrag:.2f} CHF")
        c.setFont("Helvetica-Bold", 11)
        c.drawRightString(width - rand - 35*mm, total_y - 32, "TOTAL:")
        c.drawRightString(width - rand, total_y - 32, f"{total_mit_mwst:.2f} CHF")
        
        # Footer-Text
        if fuss_text:
            c.setFillColor(colors.white)
            c.setFont("Helvetica", 8)
            c.drawCentredString(width/2, 8*mm, fuss_text.split("\n")[0][:60])
    
    def _render_geometric_layout(self, c, width, height, stil, rechnung, positionen, gesamtbetrag, mwst_satz, mwst_betrag, total_mit_mwst, einleitung, fuss_text):
        """Modern: Geometrische Dreiecke in Ecken."""
        rand = 25*mm
        
        # Dreieck oben links (dunkel)
        c.setFillColor(stil.get("sekundaer_farbe", colors.Color(0.2, 0.2, 0.25)))
        path = c.beginPath()
        path.moveTo(0, height)
        path.lineTo(0, height - 100*mm)
        path.lineTo(75*mm, height)
        path.close()
        c.drawPath(path, fill=True, stroke=False)
        
        # Dreieck unten rechts (Akzentfarbe)
        c.setFillColor(stil.get("akzent_farbe", colors.Color(0, 0.75, 0.65)))
        path = c.beginPath()
        path.moveTo(width, 0)
        path.lineTo(width, 55*mm)
        path.lineTo(width - 60*mm, 0)
        path.close()
        c.drawPath(path, fill=True, stroke=False)
        
        # Logo (auf dunklem Dreieck - weiß-freundlich)
        self._draw_logo(c, 15*mm, height - 50*mm, 45*mm, 30*mm)
        
        # RECHNUNG groß
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 24)
        c.drawString(85*mm, height - 35*mm, "RECHNUNG")
        
        # Details
        c.setFont("Helvetica", 10)
        c.drawRightString(width - rand, height - 25*mm, f"Nr: {rechnung['rechnung_nr']}")
        c.drawRightString(width - rand, height - 37*mm, f"Datum: {rechnung['datum']}")
        
        # Kundenadresse
        c.setFont("Helvetica-Bold", 10)
        c.drawString(rand, height - 75*mm, "An:")
        c.setFont("Helvetica", 10)
        c.drawString(rand, height - 87*mm, rechnung["firma"])
        c.drawString(rand, height - 99*mm, rechnung["kunde"])
        for i, z in enumerate(rechnung["adresse"].split("\n")):
            c.drawString(rand, height - 111*mm - i*12, z)
        
        # Tabelle
        tabelle_y = height - 145*mm
        th = self._draw_positionen_tabelle(c, rand, tabelle_y, stil, positionen, gesamtbetrag)
        
        # Total-Box
        total_y = tabelle_y - th - 12*mm
        c.setFillColor(stil.get("akzent_farbe", colors.Color(0, 0.75, 0.65)))
        c.rect(width - rand - 70*mm, total_y - 3*mm, 70*mm, 10*mm, fill=True, stroke=False)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 11)
        c.drawRightString(width - rand - 3*mm, total_y, f"Total: {total_mit_mwst:.2f} CHF")
    
    def _render_side_accent_layout(self, c, width, height, stil, rechnung, positionen, gesamtbetrag, mwst_satz, mwst_betrag, total_mit_mwst, einleitung, fuss_text):
        """Creative: Farbiger vertikaler Streifen links."""
        side_w = stil.get("side_width", 12) * mm
        rand = side_w + 15*mm
        
        # Seitenstreifen
        c.setFillColor(stil.get("akzent_farbe", colors.Color(0.49, 0.23, 0.93)))
        c.rect(0, 0, side_w, height, fill=True, stroke=False)
        
        # Logo
        self._draw_logo(c, rand, height - 40*mm, 50*mm, 25*mm)
        
        # Firmenname
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(rand + 55*mm, height - 25*mm, "Ihr Unternehmen")
        c.setFont("Helvetica", 9)
        c.drawString(rand + 55*mm, height - 36*mm, "Musterstrasse 1, 3000 Bern")
        
        # RECHNUNG Titel
        c.setFont("Helvetica-Bold", 20)
        c.drawString(rand, height - 65*mm, "RECHNUNG")
        c.setFont("Helvetica", 10)
        c.drawString(rand + 50*mm, height - 65*mm, f"#{rechnung['rechnung_nr']}")
        c.drawString(rand + 100*mm, height - 65*mm, rechnung['datum'])
        
        # Kundenadresse
        c.setFont("Helvetica-Bold", 10)
        c.drawString(rand, height - 85*mm, rechnung["firma"])
        c.setFont("Helvetica", 10)
        c.drawString(rand, height - 97*mm, rechnung["kunde"])
        for i, z in enumerate(rechnung["adresse"].split("\n")):
            c.drawString(rand, height - 109*mm - i*12, z)
        
        # Einleitung
        c.setFont("Helvetica", 9)
        y = height - 135*mm
        for z in einleitung.split("\n")[:2]:
            c.drawString(rand, y, z[:85])
            y -= 11
        
        # Tabelle
        tabelle_y = y - 10*mm
        th = self._draw_positionen_tabelle(c, rand, tabelle_y, stil, positionen, gesamtbetrag)
        
        # Total-Box (volle Breite)
        total_y = tabelle_y - th - 15*mm
        c.setFillColor(stil.get("akzent_farbe", colors.Color(0.49, 0.23, 0.93)))
        c.rect(rand, total_y - 4*mm, width - rand - 20*mm, 10*mm, fill=True, stroke=False)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 11)
        c.drawRightString(width - 22*mm, total_y, f"Gesamtbetrag: {total_mit_mwst:.2f} CHF")
        
        # Fußzeile
        if fuss_text:
            c.setFillColor(colors.Color(0.4,0.4,0.4))
            c.setFont("Helvetica", 8)
            c.drawString(rand, 20*mm, fuss_text.split("\n")[0][:70])
    
    def _render_invoice_pro_layout(self, c, width, height, stil, rechnung, positionen, gesamtbetrag, mwst_satz, mwst_betrag, total_mit_mwst, einleitung, fuss_text):
        """Invoice Pro: Großer Header mit INVOICE # Titel."""
        rand = 20*mm
        kopf_h = 40*mm
        
        # Header-Balken
        c.setFillColor(stil.get("kopf_farbe", colors.Color(0.22, 0.25, 0.32)))
        c.rect(0, height - kopf_h, width, kopf_h, fill=True, stroke=False)
        
        # Logo im Header
        self._draw_logo(c, rand, height - 32*mm, 45*mm, 22*mm)
        
        # Firmeninfo Mitte
        c.setFillColor(colors.white)
        c.setFont("Helvetica", 9)
        c.drawString(75*mm, height - 15*mm, "Muster GmbH")
        c.drawString(75*mm, height - 25*mm, "Hauptstrasse 42")
        c.drawString(75*mm, height - 35*mm, "8000 Zürich")
        
        # Kontakt rechts
        c.drawRightString(width - rand, height - 15*mm, "+41 44 000 00 00")
        c.drawRightString(width - rand, height - 25*mm, "info@muster.ch")
        c.drawRightString(width - rand, height - 35*mm, "www.muster.ch")
        
        # Großer INVOICE Titel
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 26)
        c.drawString(rand, height - kopf_h - 25*mm, "RECHNUNG")
        c.setFillColor(stil.get("akzent_farbe", colors.Color(0.22, 0.25, 0.32)))
        c.drawString(rand + 60*mm, height - kopf_h - 25*mm, f"#{rechnung['rechnung_nr']}")
        
        # Datum/Total Box rechts
        c.setFillColor(colors.Color(0.95, 0.95, 0.95))
        c.rect(width - rand - 55*mm, height - kopf_h - 35*mm, 55*mm, 25*mm, fill=True, stroke=False)
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(width - rand - 52*mm, height - kopf_h - 18*mm, "DATUM")
        c.drawString(width - rand - 52*mm, height - kopf_h - 32*mm, "GESAMT")
        c.setFont("Helvetica", 10)
        c.drawRightString(width - rand - 3*mm, height - kopf_h - 18*mm, rechnung['datum'])
        c.setFont("Helvetica-Bold", 11)
        c.drawRightString(width - rand - 3*mm, height - kopf_h - 32*mm, f"{total_mit_mwst:.2f} CHF")
        
        # Kundenadresse
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(rand, height - kopf_h - 50*mm, "RECHNUNGSADRESSE:")
        c.setFont("Helvetica", 10)
        c.drawString(rand, height - kopf_h - 62*mm, rechnung["firma"])
        c.drawString(rand, height - kopf_h - 74*mm, rechnung["kunde"])
        for i, z in enumerate(rechnung["adresse"].split("\n")):
            c.drawString(rand, height - kopf_h - 86*mm - i*12, z)
        
        # Tabelle
        tabelle_y = height - kopf_h - 115*mm
        th = self._draw_positionen_tabelle(c, rand, tabelle_y, stil, positionen, gesamtbetrag)
        
        # Aufschlüsselung rechts
        total_y = tabelle_y - th - 12*mm
        c.setFont("Helvetica", 10)
        c.drawRightString(width - rand - 35*mm, total_y, "Zwischensumme:")
        c.drawRightString(width - rand, total_y, f"{gesamtbetrag:.2f} CHF")
        c.drawRightString(width - rand - 35*mm, total_y - 14, "MwSt:")
        c.drawRightString(width - rand, total_y - 14, f"{mwst_betrag:.2f} CHF")
        
        # Total-Box
        c.setFillColor(stil.get("total_bg", colors.Color(0.22, 0.25, 0.32)))
        c.rect(width - rand - 75*mm, total_y - 38*mm, 75*mm, 10*mm, fill=True, stroke=False)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(width - rand - 72*mm, total_y - 32*mm, "TOTAL")
        c.drawRightString(width - rand - 2*mm, total_y - 32*mm, f"{total_mit_mwst:.2f} CHF")
        
        # Thank you
        c.setFillColor(stil.get("akzent_farbe", colors.Color(0.22, 0.25, 0.32)))
        c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(width/2, 25*mm, "VIELEN DANK FÜR IHREN AUFTRAG")
    
    def _render_header_bar_layout(self, c, width, height, stil, rechnung, positionen, gesamtbetrag, mwst_satz, mwst_betrag, total_mit_mwst, einleitung, fuss_text):
        """Corporate: Einfacher Header-Balken."""
        rand = 20*mm
        kopf_h = stil.get("kopf_hoehe", 35) * mm
        
        # Header
        c.setFillColor(stil.get("kopf_farbe", colors.Color(0.12, 0.23, 0.37)))
        c.rect(0, height - kopf_h, width, kopf_h, fill=True, stroke=False)
        
        # Logo
        self._draw_logo(c, rand, height - kopf_h + 5*mm, 45*mm, kopf_h - 10*mm)
        
        # Firmenname im Header
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 14)
        c.drawRightString(width - rand, height - 18*mm, "IHRE FIRMA")
        c.setFont("Helvetica", 9)
        c.drawRightString(width - rand, height - 30*mm, "Kontakt | info@firma.ch")
        
        # Rechnungsdetails
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 10)
        c.drawString(rand, height - kopf_h - 20*mm, f"Rechnung Nr: {rechnung['rechnung_nr']}")
        c.drawString(rand + 70*mm, height - kopf_h - 20*mm, f"Datum: {rechnung['datum']}")
        c.drawRightString(width - rand, height - kopf_h - 20*mm, f"UID: {rechnung['uid']}")
        
        # Kundenadresse
        c.setFont("Helvetica-Bold", 10)
        c.drawString(rand, height - kopf_h - 45*mm, rechnung["firma"])
        c.setFont("Helvetica", 10)
        c.drawString(rand, height - kopf_h - 57*mm, rechnung["kunde"])
        for i, z in enumerate(rechnung["adresse"].split("\n")):
            c.drawString(rand, height - kopf_h - 69*mm - i*12, z)
        
        # Tabelle
        tabelle_y = height - kopf_h - 105*mm
        th = self._draw_positionen_tabelle(c, rand, tabelle_y, stil, positionen, gesamtbetrag)
        
        # Total-Box (volle Breite)
        total_y = tabelle_y - th - 15*mm
        c.setFillColor(stil.get("total_bg", colors.Color(0.12, 0.23, 0.37)))
        c.rect(rand, total_y - 4*mm, width - 2*rand, 10*mm, fill=True, stroke=False)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(rand + 5*mm, total_y, f"Gesamtbetrag: {total_mit_mwst:.2f} CHF")
        
        # Fußzeile
        if fuss_text:
            c.setFillColor(colors.Color(0.4,0.4,0.4))
            c.setFont("Helvetica", 8)
            fy = 20*mm
            for z in fuss_text.split("\n")[:2]:
                c.drawCentredString(width/2, fy, z)
                fy -= 10
    
    def _render_summary_right_layout(self, c, width, height, stil, rechnung, positionen, gesamtbetrag, mwst_satz, mwst_betrag, total_mit_mwst, einleitung, fuss_text):
        """Elegant: Zusammenfassung rechts mit Aufschlüsselung."""
        rand = 20*mm
        
        # Logo
        self._draw_logo(c, rand, height - 40*mm, 50*mm, 25*mm)
        
        # Rechnungsdetails rechts
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 10)
        c.drawRightString(width - rand, height - 20*mm, f"Rechnung #{rechnung['rechnung_nr']}")
        c.drawRightString(width - rand, height - 32*mm, rechnung['datum'])
        
        # Horizontale Linie
        c.setStrokeColor(stil.get("linien_farbe", colors.Color(0.85, 0.85, 0.85)))
        c.setLineWidth(0.5)
        c.line(rand, height - 55*mm, width - rand, height - 55*mm)
        
        # Kundenadresse
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(rand, height - 70*mm, rechnung["firma"])
        c.setFont("Helvetica", 10)
        c.drawString(rand, height - 82*mm, rechnung["kunde"])
        for i, z in enumerate(rechnung["adresse"].split("\n")):
            c.drawString(rand, height - 94*mm - i*12, z)
        
        # Tabelle
        tabelle_y = height - 130*mm
        th = self._draw_positionen_tabelle(c, rand, tabelle_y, stil, positionen, gesamtbetrag)
        
        # Aufschlüsselung rechts (in Box)
        summary_x = width - rand - 65*mm
        summary_y = tabelle_y - th - 10*mm
        
        # Hintergrund für Summary
        c.setFillColor(colors.Color(0.97, 0.97, 0.97))
        c.rect(summary_x - 5*mm, summary_y - 45*mm, 70*mm, 50*mm, fill=True, stroke=False)
        
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 10)
        c.drawString(summary_x, summary_y, "Zwischensumme")
        c.drawRightString(width - rand, summary_y, f"{gesamtbetrag:.2f} CHF")
        c.drawString(summary_x, summary_y - 15, f"MwSt ({mwst_satz:.1f}%)")
        c.drawRightString(width - rand, summary_y - 15, f"{mwst_betrag:.2f} CHF")
        
        # Trennlinie
        c.line(summary_x, summary_y - 25, width - rand, summary_y - 25)
        
        # Total
        c.setFont("Helvetica-Bold", 12)
        c.drawString(summary_x, summary_y - 38, "TOTAL")
        c.drawRightString(width - rand, summary_y - 38, f"{total_mit_mwst:.2f} CHF")
        
        # Zahlungshinweis
        c.setFont("Helvetica", 9)
        c.setFillColor(colors.Color(0.4, 0.4, 0.4))
        c.drawString(rand, summary_y - 20*mm, "Zahlbar innert 30 Tagen")
        
        # Fußzeile
        if fuss_text:
            c.setFont("Helvetica", 8)
            fy = 20*mm
            for z in fuss_text.split("\n")[:2]:
                c.drawCentredString(width/2, fy, z)
                fy -= 10
    
    def _render_minimal_layout(self, c, width, height, stil, rechnung, positionen, gesamtbetrag, mwst_satz, mwst_betrag, total_mit_mwst, einleitung, fuss_text):
        """Minimalistisch: Sehr clean, viel Weißraum."""
        rand = 25*mm
        
        # Logo zentriert oben
        if self.logo_bytes:
            self._draw_logo(c, width/2 - 25*mm, height - 45*mm, 50*mm, 30*mm)
        
        # Firmenname zentriert unter Logo
        c.setFillColor(colors.Color(0.3, 0.3, 0.3))
        c.setFont("Helvetica", 10)
        c.drawCentredString(width/2, height - 55*mm, "MUSTER GMBH")
        
        # Trennlinie
        c.setStrokeColor(colors.Color(0.85, 0.85, 0.85))
        c.setLineWidth(0.5)
        c.line(rand + 30*mm, height - 65*mm, width - rand - 30*mm, height - 65*mm)
        
        # Rechnungsinfo links / Kundeninfo rechts
        c.setFillColor(colors.Color(0.5, 0.5, 0.5))
        c.setFont("Helvetica", 9)
        c.drawString(rand, height - 85*mm, "DATUM:")
        c.drawString(rand, height - 97*mm, "RECHNUNG #:")
        
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 10)
        c.drawString(rand + 35*mm, height - 85*mm, rechnung['datum'])
        c.drawString(rand + 35*mm, height - 97*mm, rechnung['rechnung_nr'])
        
        # Kundeninfo rechts
        c.setFillColor(colors.Color(0.5, 0.5, 0.5))
        c.setFont("Helvetica", 9)
        c.drawRightString(width - rand - 50*mm, height - 85*mm, "AN:")
        
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 10)
        c.drawRightString(width - rand, height - 85*mm, rechnung["firma"])
        c.drawRightString(width - rand, height - 97*mm, rechnung["kunde"])
        c.drawRightString(width - rand, height - 109*mm, rechnung["adresse"].replace("\n", ", "))
        
        # Tabelle
        tabelle_y = height - 140*mm
        th = self._draw_positionen_tabelle(c, rand, tabelle_y, stil, positionen, gesamtbetrag)
        
        # Total rechts, mit Linie
        total_y = tabelle_y - th - 15*mm
        c.setStrokeColor(colors.Color(0.7, 0.7, 0.7))
        c.line(width - rand - 60*mm, total_y + 5, width - rand, total_y + 5)
        
        c.setFont("Helvetica-Bold", 11)
        c.drawRightString(width - rand - 35*mm, total_y - 5, "Total:")
        c.drawRightString(width - rand, total_y - 5, f"{total_mit_mwst:.2f} CHF")
        
        # Danke zentriert
        c.setFillColor(colors.Color(0.5, 0.5, 0.5))
        c.setFont("Helvetica", 9)
        c.drawCentredString(width/2, 30*mm, "Vielen Dank für Ihr Vertrauen")
    
    def _draw_kopf_design(self, c, width, height, stil, design_typ):
        """Zeichnet dekorative Kopfbereich-Elemente basierend auf dem Stil.
        WICHTIG: Muss identisch mit _zeichne_kopf_design in rechnungen_tab.py sein!"""
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
            # Wellenförmige Ecken wie in Bild 6
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
    
    def _pdf_to_pixmap(self, pdf_bytes):
        """Konvertiert PDF-Bytes zu QPixmap."""
        try:
            # Versuche PyMuPDF (fitz)
            import fitz
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            page = doc[0]
            # Skalierung für gute Qualität
            zoom = 1.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            
            # Konvertiere zu PNG bytes und lade in QPixmap
            png_bytes = pix.tobytes("png")
            doc.close()
            
            pixmap = QPixmap()
            if pixmap.loadFromData(png_bytes, "PNG"):
                return pixmap
            else:
                print("Fehler beim Laden der PNG-Daten in QPixmap")
                return None
        except ImportError as e:
            print(f"PyMuPDF nicht verfügbar: {e}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"PyMuPDF Fehler: {e}")
        
        # Fallback: Placeholder wenn PyMuPDF nicht verfügbar
        return None

    # --- Skalierung 10er Schritte ---
    def _snap10(self, v: float) -> int:
        try:
            return max(10, min(300, int(round(float(v) / 10.0) * 10)))
        except Exception:
            return 100

    def _on_slider_change(self, v: int):
        s = self._snap10(v)
        if s != v:
            self.scale_slider.blockSignals(True); self.scale_slider.setValue(s); self.scale_slider.blockSignals(False)
        self.scale_spin.blockSignals(True); self.scale_spin.setValue(s); self.scale_spin.blockSignals(False)
        self.logo_skala = s
        self._schedule_preview_update()

    def _on_spin_change(self, v: int):
        s = self._snap10(v)
        if s != v:
            self.scale_spin.blockSignals(True); self.scale_spin.setValue(s); self.scale_spin.blockSignals(False)
        self.scale_slider.blockSignals(True); self.scale_slider.setValue(s); self.scale_slider.blockSignals(False)
        self.logo_skala = s
        self._schedule_preview_update()

    # --- Stil-Auswahl ---
    def _on_stil_changed(self, index):
        """Wird aufgerufen wenn ein Stil im Dropdown ausgewählt wird."""
        stil_key = self.stil_dropdown.itemData(index)
        if stil_key:
            self.aktueller_stil = stil_key
            self._update_stil_vorschau()
            self._schedule_preview_update()

    def _update_stil_vorschau(self):
        """Aktualisiert die Beschreibung für den gewählten Stil."""
        stil_info = RECHNUNG_STYLES.get(self.aktueller_stil, RECHNUNG_STYLES["classic"])
        self.stil_beschreibung.setText(stil_info["beschreibung"])

    # --- DB I/O ---
    def lade_layout(self):
        """Lädt Layout-Daten aus DB (backend-agnostisch)."""
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
                # backend-agnostische Abfrage: ORDER BY id DESC (funktioniert in SQLite und Postgres)
                # Versuche mit stil-Spalte, fallback ohne
                try:
                    cur.execute("SELECT id, name, layout, kopfzeile, einleitung, fusszeile, logo, logo_mime, logo_skala, stil FROM rechnung_layout ORDER BY id DESC LIMIT 1")
                    row = cur.fetchone()
                except Exception:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                    try:
                        cur.execute("SELECT id, name, layout, kopfzeile, einleitung, fusszeile, logo, logo_mime, logo_skala FROM rechnung_layout ORDER BY id DESC LIMIT 1")
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

        # UI-Felder füllen (neu hinzugefügt)
        self.text_kopf.setPlainText(merged.get("kopfzeile", ""))
        self.text_einleitung.setPlainText(merged.get("einleitung", ""))
        fuss_text = merged.get("fusszeile", {}).get("text", "")
        self.text_fuss.setPlainText(fuss_text)
        self.logo_skala = merged.get("logo_skala", 100.0)
        self.scale_slider.setValue(int(self.logo_skala))
        self.scale_spin.setValue(int(self.logo_skala))
        
        # Stil laden und UI aktualisieren
        self.aktueller_stil = merged.get("stil", "classic")
        if self.aktueller_stil not in get_alle_stile():
            self.aktueller_stil = "classic"
        # Dropdown auf aktuellen Stil setzen
        idx = self.stil_dropdown.findData(self.aktueller_stil)
        if idx >= 0:
            self.stil_dropdown.setCurrentIndex(idx)
        self._update_stil_vorschau()
        
        if merged.get("logo_bytes"):
            self.logo_bytes = merged["logo_bytes"]
            self.logo_mime = merged.get("logo_mime")
            self.btn_logo_entfernen.setEnabled(True)
        else:
            self.logo_entfernen()
        
        # Kopfzeilen-Status aktualisieren
        self._update_kopfzeile_status()

        return layout

    def speichern(self):
        kopf = self.text_kopf.toPlainText().strip()
        einl = self.text_einleitung.toPlainText().strip()
        fuss = self.text_fuss.toPlainText().strip()
        scale = float(self._snap10(self.scale_spin.value()))
        stil = self.aktueller_stil  # NEU: Stil speichern

        # Bytes direkt übergeben (SQLite und PostgreSQL unterstützen bytes)
        logo_param = self.logo_bytes

        con = get_db()
        try:
            with con.cursor() as cur:
                # Stelle sicher, dass stil-Spalte existiert
                try:
                    cur.execute("ALTER TABLE rechnung_layout ADD COLUMN IF NOT EXISTS stil TEXT DEFAULT 'classic'")
                    con.commit()
                except Exception:
                    try:
                        con.rollback()
                    except Exception:
                        pass

                # Simpler, deterministic approach:
                # remove existing layout rows and insert a single fresh row so readers always find the latest data
                try:
                    cur.execute("DELETE FROM rechnung_layout")
                except Exception:
                    # ignore errors (e.g. permission) and continue with insert attempts
                    try:
                        con.rollback()
                    except Exception:
                        pass

                # Try Postgres paramstyle first, fallback to sqlite paramstyle
                try:
                    cur.execute("""
                        INSERT INTO rechnung_layout (kopfzeile, einleitung, fusszeile, logo, logo_mime, logo_skala, stil)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (kopf, einl, fuss, logo_param, self.logo_mime, scale, stil))
                except Exception:
                    try:
                        cur.execute("""
                            INSERT INTO rechnung_layout (kopfzeile, einleitung, fusszeile, logo, logo_mime, logo_skala, stil)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (kopf, einl, fuss, logo_param, self.logo_mime, scale, stil))
                    except Exception as e_inner:
                        # As last resort try INSERT OR REPLACE with sqlite style
                        try:
                            cur.execute("""
                                INSERT OR REPLACE INTO rechnung_layout (id, kopfzeile, einleitung, fusszeile, logo, logo_mime, logo_skala, stil)
                                VALUES (1, ?, ?, ?, ?, ?, ?, ?)
                            """, (kopf, einl, fuss, logo_param, self.logo_mime, scale, stil))
                        except Exception:
                            raise  # re-raise to show error to user
            con.commit()
        except Exception as e:
            try: con.rollback()
            except Exception: pass
            QMessageBox.critical(self, _("Fehler"), _("Speichern fehlgeschlagen:\n{}").format(e))
            return
        finally:
            try: con.close()
            except Exception: pass

        QMessageBox.information(self, _("Gespeichert"), _("Rechnungslayout wurde gespeichert."))
        self.accept()

    # --- Logo-Aktionen ---
    def _update_kopfzeile_status(self):
        """Aktualisiert den Status des Kopfzeilen-Feldes basierend auf Logo-Zustand."""
        if self.logo_bytes:
            # Logo ist gesetzt -> Kopfzeile deaktivieren
            self.text_kopf.setEnabled(False)
            self.text_kopf.setStyleSheet("background-color: #f0f0f0; color: #999;")
            self.kopf_hinweis.show()
        else:
            # Kein Logo -> Kopfzeile aktivieren
            self.text_kopf.setEnabled(True)
            self.text_kopf.setStyleSheet("")
            self.kopf_hinweis.hide()
    
    def logo_auswaehlen(self):
        pfad, _filter = QFileDialog.getOpenFileName(self, "Logo auswählen", "", "Bilder (*.png *.jpg *.jpeg *.bmp *.gif *.ico)")
        if not pfad:
            return
        mime = mimetypes.guess_type(pfad)[0] or "application/octet-stream"
        try:
            with open(pfad, "rb") as f:
                data = f.read()
        except Exception as e:
            QMessageBox.warning(self, _("Fehler"), _("Logo konnte nicht gelesen werden:\n{}").format(e))
            return
        self.logo_bytes = data
        self.logo_mime = mime
        self.btn_logo_entfernen.setEnabled(True)
        self._update_kopfzeile_status()
        self._schedule_preview_update()

    def logo_entfernen(self):
        self.logo_bytes = None
        self.logo_mime = None
        self.btn_logo_entfernen.setEnabled(False)
        self._update_kopfzeile_status()
        self._schedule_preview_update()


