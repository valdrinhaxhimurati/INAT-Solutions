# datei: gui/rechnung_layout_dialog.py
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QTextEdit, QPushButton, QHBoxLayout, QMessageBox, QFileDialog, QSlider, QSpinBox
from PyQt5.QtCore import Qt
import mimetypes

from db_connection import get_db, dict_cursor_factory
from settings_store import get_json, set_json, save_logo_from_file, get_blob
from PyQt5.QtGui import QPixmap


def _row_val(row, key, default=None):
    # Verträgt dict, sqlite3.Row und Sequenzen
    try:
        if isinstance(row, dict):
            return row.get(key, default)
        return row[key]
    except Exception:
        return default


class RechnungLayoutDialog(QDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle("Rechnungslayout bearbeiten")
        self.setMinimumSize(600, 500)

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.dateipfad = "config/rechnung_layout.json"
        # DB-Felder
        self.logo_bytes = None
        self.logo_mime = None
        self.logo_skala = 100.0  # default 100%

        # Kopfzeile
        layout.addWidget(QLabel("Kopfzeile (z. B. Firmeninfo):"))
        self.text_kopf = QTextEdit()
        layout.addWidget(self.text_kopf)

        # Einleitung
        layout.addWidget(QLabel("Einleitungstext:"))
        self.text_einleitung = QTextEdit()
        layout.addWidget(self.text_einleitung)

        # Fußzeile
        layout.addWidget(QLabel("Fußzeile:"))
        self.text_fuss = QTextEdit()
        layout.addWidget(self.text_fuss)

        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_speichern = QPushButton("Speichern")
        self.btn_abbrechen = QPushButton("Abbrechen")
        btn_layout.addWidget(self.btn_speichern)
        btn_layout.addWidget(self.btn_abbrechen)
        layout.addLayout(btn_layout)

        self.btn_speichern.clicked.connect(self.speichern)
        self.btn_abbrechen.clicked.connect(self.reject)

        # Logo
        layout.addWidget(QLabel("Logo:"))
        h_logo = QHBoxLayout()
        self.logo_vorschau = QLabel()
        self.logo_vorschau.setFixedSize(150, 100)
        self.logo_vorschau.setStyleSheet("border: 1px solid #ccc;")
        self.logo_vorschau.setScaledContents(True)

        # Rechts neben der Vorschau: Buttons + Skalierung
        right_box = QVBoxLayout()
        btn_row = QHBoxLayout()
        self.btn_logo_auswaehlen = QPushButton("Logo auswählen")
        self.btn_logo_auswaehlen.clicked.connect(self.logo_auswaehlen)
        self.btn_logo_entfernen = QPushButton("Logo entfernen")
        self.btn_logo_entfernen.clicked.connect(self.logo_entfernen)
        btn_row.addWidget(self.btn_logo_auswaehlen)
        btn_row.addWidget(self.btn_logo_entfernen)
        right_box.addLayout(btn_row)

        scale_row = QHBoxLayout()
        lbl_scale = QLabel("Logo-Größe (%)")
        self.scale_slider = QSlider(Qt.Horizontal)
        self.scale_slider.setRange(10, 300)
        self.scale_slider.setSingleStep(10)
        self.scale_slider.setPageStep(10)
        self.scale_slider.setTickInterval(10)
        self.scale_slider.setTickPosition(QSlider.TicksBelow)

        self.scale_spin = QSpinBox()
        self.scale_spin.setRange(10, 300)
        self.scale_spin.setSingleStep(10)

        # Initialwerte (werden in lade_layout überschrieben)
        self.scale_slider.setValue(100)
        self.scale_spin.setValue(100)

        # Sync mit Einrasten auf 10er-Schritte
        self.scale_slider.valueChanged.connect(self._on_slider_change)
        self.scale_spin.valueChanged.connect(self._on_spin_change)
        self.scale_spin.editingFinished.connect(self._ensure_step_10)

        scale_row.addWidget(lbl_scale)
        scale_row.addWidget(self.scale_slider, 1)
        scale_row.addWidget(self.scale_spin)
        right_box.addLayout(scale_row)

        h_logo.addWidget(self.logo_vorschau)
        h_logo.addLayout(right_box)
        layout.addLayout(h_logo)

        self._init_db_table()
        self.lade_layout()

        # Beim Start: Logo-Vorschau aus DB setzen (falls vorhanden)
        try:
            data, _ = get_blob("invoice_logo")
            if data:
                pm = QPixmap()
                if pm.loadFromData(data):
                    self.logo_vorschau.setPixmap(pm)
        except Exception:
            pass

    def _init_db_table(self):
        conn = get_db()
        try:
            is_sqlite = getattr(conn, "is_sqlite", False)
            if is_sqlite:
                cur = conn.cursor()
                try:
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
                    cur.execute("""
                        INSERT OR IGNORE INTO rechnung_layout (id, kopfzeile, einleitung, fusszeile, logo, logo_mime, logo_skala)
                        VALUES (1, ?, ?, ?, ?, ?, ?)
                    """, ("", "", "", None, None, 100.0))
                finally:
                    try: cur.close()
                    except Exception: pass
            else:
                with conn.cursor() as cur:
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
                    cur.execute("""
                        INSERT INTO rechnung_layout (id, kopfzeile, einleitung, fusszeile, logo, logo_mime, logo_skala)
                        VALUES (1, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO NOTHING
                    """, ("", "", "", None, None, 100.0))
            conn.commit()
        finally:
            try: conn.close()
            except Exception: pass

    # --- Helpers für 10%-Schritte ---
    def _snap10(self, v: float) -> int:
        try:
            return max(10, min(300, int(round(float(v) / 10.0) * 10)))
        except Exception:
            return 100

    def _on_slider_change(self, v: int):
        snapped = self._snap10(v)
        if snapped != v:
            self.scale_slider.blockSignals(True)
            self.scale_slider.setValue(snapped)
            self.scale_slider.blockSignals(False)
        self.scale_spin.blockSignals(True)
        self.scale_spin.setValue(snapped)
        self.scale_spin.blockSignals(False)

    def _on_spin_change(self, v: int):
        snapped = self._snap10(v)
        if snapped != v:
            self.scale_spin.blockSignals(True)
            self.scale_spin.setValue(snapped)
            self.scale_spin.blockSignals(False)
        self.scale_slider.blockSignals(True)
        self.scale_slider.setValue(snapped)
        self.scale_slider.blockSignals(False)

    def _ensure_step_10(self):
        v = self.scale_spin.value()
        snapped = self._snap10(v)
        if snapped != v:
            self.scale_spin.setValue(snapped)

    def lade_layout(self):
        conn = get_db()
        try:
            is_sqlite = getattr(conn, "is_sqlite", False)
            cur = conn.cursor() if is_sqlite else conn.cursor(cursor_factory=dict_cursor_factory)
            cur.execute("SELECT kopfzeile, einleitung, fusszeile, logo, logo_mime, logo_skala FROM rechnung_layout WHERE id=1")
            row = cur.fetchone()
            # Zeile robust in Dict mappen (sqlite3.Row, tuple, dict)
            if row is None:
                return
            if isinstance(row, dict):
                data = row
            else:
                cols = [d[0] for d in cur.description]
                try:
                    data = {k: row[k] if hasattr(row, "__getitem__") else None for k in cols}
                except Exception:
                    data = dict(zip(cols, row))

            self.text_kopf.setPlainText((data.get("kopfzeile") or ""))
            self.text_einleitung.setPlainText((data.get("einleitung") or ""))
            self.text_fuss.setPlainText((data.get("fusszeile") or ""))

            try:
                self.logo_skala = float(data.get("logo_skala") or 100.0)
            except Exception:
                self.logo_skala = 100.0
            v = int(round(self.logo_skala / 10.0) * 10)
            if hasattr(self, "scale_slider"): self.scale_slider.setValue(v)
            if hasattr(self, "scale_spin"): self.scale_spin.setValue(v)

            self.logo_bytes = data.get("logo")
            self.logo_mime = data.get("logo_mime")
            pm = QPixmap()
            if self.logo_bytes and pm.loadFromData(bytes(self.logo_bytes)):
                self.logo_vorschau.setPixmap(pm)
            else:
                self.logo_vorschau.clear()
            if hasattr(self, "btn_logo_entfernen"):
                self.btn_logo_entfernen.setEnabled(bool(self.logo_bytes))
        finally:
            try: conn.close()
            except Exception: pass

    def _lade_layout_from_db(self):
        layout = get_json("rechnung_layout")
        if layout is None:
            # einmalig aus Datei importieren (falls vorhanden)
            from settings_store import import_json_if_missing
            layout = import_json_if_missing("rechnung_layout", "config/rechnung_layout.json") or {}
        # Widgets füllen (Namen anpassen!)
        if hasattr(self, "text_kopf"): self.text_kopf.setPlainText(layout.get("kopfzeile", ""))
        if hasattr(self, "text_einleitung"): self.text_einleitung.setPlainText(layout.get("einleitung", ""))
        if hasattr(self, "text_fuss"): self.text_fuss.setPlainText(layout.get("fusszeile", ""))
        # Logo-Vorschau aus DB
        data, _ = get_blob("invoice_logo")
        if data and hasattr(self, "logo_vorschau"):
            pm = QPixmap(); 
            if pm.loadFromData(data): self.logo_vorschau.setPixmap(pm)

    def speichern(self):
        kopf = self.text_kopf.toPlainText()
        einl = self.text_einleitung.toPlainText()
        fuss = self.text_fuss.toPlainText()
        scale = float(int(round((self.scale_spin.value() if hasattr(self, "scale_spin") else (self.logo_skala or 100.0)) / 10.0) * 10))

        conn = get_db()
        try:
            is_sqlite = getattr(conn, "is_sqlite", False)
            logo_param = self.logo_bytes
            if not is_sqlite and logo_param is not None:
                try:
                    import psycopg2  # type: ignore
                    logo_param = psycopg2.Binary(logo_param)
                except Exception:
                    logo_param = bytes(logo_param)

            if is_sqlite:
                cur = conn.cursor()
                try:
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
                    cur.execute("""
                        INSERT OR REPLACE INTO rechnung_layout
                            (id, kopfzeile, einleitung, fusszeile, logo, logo_mime, logo_skala)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (1, kopf, einl, fuss, logo_param, self.logo_mime, scale))
                finally:
                    try: cur.close()
                    except Exception: pass
            else:
                with conn.cursor() as cur:
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
                    cur.execute("""
                        INSERT INTO rechnung_layout (id, kopfzeile, einleitung, fusszeile, logo, logo_mime, logo_skala)
                        VALUES (1, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                            kopfzeile=EXCLUDED.kopfzeile,
                            einleitung=EXCLUDED.einleitung,
                            fusszeile=EXCLUDED.fusszeile,
                            logo=EXCLUDED.logo,
                            logo_mime=EXCLUDED.logo_mime,
                            logo_skala=EXCLUDED.logo_skala
                    """, (kopf, einl, fuss, logo_param, self.logo_mime, scale))
            conn.commit()
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Speichern fehlgeschlagen:\n{e}")
            return
        finally:
            try: conn.close()
            except Exception: pass

        QMessageBox.information(self, "Gespeichert", "Rechnungslayout wurde gespeichert.")
        self.accept()

    def logo_auswaehlen(self):
        pfad, _ = QFileDialog.getOpenFileName(self, "Logo auswählen", "", "Bilder (*.png *.jpg *.jpeg *.bmp)")
        if not pfad: return
        save_logo_from_file(pfad)
        # Vorschau aktualisieren
        data, _ = get_blob("invoice_logo")
        if data and hasattr(self, "logo_vorschau"):
            pm = QPixmap(); 
            if pm.loadFromData(data): self.logo_vorschau.setPixmap(pm)

    def logo_entfernen(self):
        # Logo aus UI und Pending-Status entfernen (DB-Clear passiert beim Speichern)
        self.logo_bytes = None
        self.logo_mime = None
        self.logo_vorschau.clear()
        self.btn_logo_entfernen.setEnabled(False)

