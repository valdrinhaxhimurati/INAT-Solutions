# datei: gui/rechnung_layout_dialog.py
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QTextEdit, QPushButton, QHBoxLayout, QMessageBox, QFileDialog, QSlider, QSpinBox
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
from db_connection import get_db, dict_cursor_factory
import json
import os
import sys
import mimetypes


def _row_val(row, key, default=None):
    # Verträgt dict, sqlite3.Row und Sequenzen
    try:
        if isinstance(row, dict):
            return row.get(key, default)
        return row[key]
    except Exception:
        return default


class RechnungLayoutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
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

    def _init_db_table(self):
        conn = get_db()
        try:
            with conn.cursor() as cur:
                if getattr(conn, "is_sqlite", False):
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
                else:
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
                # Eintrag id=1 sicherstellen (ON CONFLICT ist in SQLite und PG verfügbar)
                cur.execute("""
                    INSERT INTO rechnung_layout (id, kopfzeile, einleitung, fusszeile, logo, logo_mime, logo_skala)
                    VALUES (1, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                """, ("", "", "", None, None, 100.0))
            conn.commit()
        finally:
            try:
                conn.close()
            except Exception:
                pass

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

            with conn.cursor() as cur:
                if is_sqlite:
                    # Tabelle sicherstellen
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
                    # Einfach und robust in SQLite
                    cur.execute("""
                        INSERT OR REPLACE INTO rechnung_layout
                            (id, kopfzeile, einleitung, fusszeile, logo, logo_mime, logo_skala)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (1, kopf, einl, fuss, logo_param, self.logo_mime, scale))
                else:
                    # PostgreSQL unverändert
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
        dateipfad, _ = QFileDialog.getOpenFileName(self, "Logo auswählen", "", "Bilder (*.png *.jpg *.jpeg *.bmp)")
        if dateipfad:
            self.logo_mime = mimetypes.guess_type(dateipfad)[0] or "application/octet-stream"
            try:
                with open(dateipfad, "rb") as f:
                    self.logo_bytes = f.read()
            except Exception as e:
                QMessageBox.critical(self, "Fehler", f"Logo konnte nicht gelesen werden:\n{e}")
                return
            pm = QPixmap()
            if pm.loadFromData(self.logo_bytes):
                self.logo_vorschau.setPixmap(pm)
                self.btn_logo_entfernen.setEnabled(True)
            else:
                QMessageBox.warning(self, "Warnung", "Bild konnte nicht geladen werden.")
                self.logo_vorschau.clear()
                self.btn_logo_entfernen.setEnabled(False)

    def logo_entfernen(self):
        # Logo aus UI und Pending-Status entfernen (DB-Clear passiert beim Speichern)
        self.logo_bytes = None
        self.logo_mime = None
        self.logo_vorschau.clear()
        self.btn_logo_entfernen.setEnabled(False)

