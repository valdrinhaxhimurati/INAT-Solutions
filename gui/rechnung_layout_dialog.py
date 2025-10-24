# datei: gui/rechnung_layout_dialog.py
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QTextEdit, QPushButton, QHBoxLayout,
    QMessageBox, QFileDialog, QSlider, QSpinBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from db_connection import get_db
import os, mimetypes, sqlite3

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
        is_sqlite = isinstance(conn, sqlite3.Connection) or "sqlite" in conn.__class__.__module__.lower()
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
        is_sqlite = isinstance(con, sqlite3.Connection) or "sqlite" in con.__class__.__module__.lower()
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

class RechnungLayoutDialog(QDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle("Rechnungslayout bearbeiten")
        self.setMinimumSize(600, 520)

        layout = QVBoxLayout(self)

        # Felder
        layout.addWidget(QLabel("Kopfzeile (z. B. Firmeninfo):"))
        self.text_kopf = QTextEdit(); layout.addWidget(self.text_kopf)

        layout.addWidget(QLabel("Einleitungstext:"))
        self.text_einleitung = QTextEdit(); layout.addWidget(self.text_einleitung)

        layout.addWidget(QLabel("Fußzeile:"))
        self.text_fuss = QTextEdit(); layout.addWidget(self.text_fuss)

        # Logo Bereich
        layout.addWidget(QLabel("Logo:"))
        h_logo = QHBoxLayout()
        self.logo_vorschau = QLabel()
        self.logo_vorschau.setFixedSize(150, 100)
        self.logo_vorschau.setStyleSheet("border: 1px solid #ccc;")
        self.logo_vorschau.setScaledContents(True)

        right_box = QVBoxLayout()
        btn_row = QHBoxLayout()
        self.btn_logo_auswaehlen = QPushButton("Logo auswählen")
        self.btn_logo_entfernen = QPushButton("Logo entfernen")
        btn_row.addWidget(self.btn_logo_auswaehlen)
        btn_row.addWidget(self.btn_logo_entfernen)
        right_box.addLayout(btn_row)

        scale_row = QHBoxLayout()
        scale_row.addWidget(QLabel("Logo-Größe (%)"))
        self.scale_slider = QSlider(Qt.Horizontal); self.scale_slider.setRange(10, 300); self.scale_slider.setTickInterval(10)
        self.scale_spin = QSpinBox(); self.scale_spin.setRange(10, 300)
        self.scale_slider.setValue(100); self.scale_spin.setValue(100)
        self.scale_slider.valueChanged.connect(self._on_slider_change)
        self.scale_spin.valueChanged.connect(self._on_spin_change)
        scale_row.addWidget(self.scale_slider, 1)
        scale_row.addWidget(self.scale_spin)
        right_box.addLayout(scale_row)

        h_logo.addWidget(self.logo_vorschau)
        h_logo.addLayout(right_box)
        layout.addLayout(h_logo)

        # Buttons unten
        btn_layout = QHBoxLayout()
        self.btn_speichern = QPushButton("Speichern")
        self.btn_abbrechen = QPushButton("Abbrechen")
        btn_layout.addWidget(self.btn_speichern)
        btn_layout.addWidget(self.btn_abbrechen)
        layout.addLayout(btn_layout)

        # State
        self.logo_bytes = None
        self.logo_mime = None
        self.logo_skala = 100.0

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

    def _on_spin_change(self, v: int):
        s = self._snap10(v)
        if s != v:
            self.scale_spin.blockSignals(True); self.scale_spin.setValue(s); self.scale_spin.blockSignals(False)
        self.scale_slider.blockSignals(True); self.scale_slider.setValue(s); self.scale_slider.blockSignals(False)

    # --- DB I/O ---
    def lade_layout(self):
        con = get_db()
        try:
            with con.cursor() as cur:
                # Prefer latest row: try sqlite rowid ordering first, fallback to id ordering (Postgres)
                try:
                    cur.execute("SELECT kopfzeile, einleitung, fusszeile, logo, logo_mime, logo_skala FROM rechnung_layout ORDER BY rowid DESC LIMIT 1")
                except Exception:
                    try:
                        cur.execute("SELECT kopfzeile, einleitung, fusszeile, logo, logo_mime, logo_skala FROM rechnung_layout ORDER BY id DESC LIMIT 1")
                    except Exception:
                        # last resort: try selecting any row
                        cur.execute("SELECT kopfzeile, einleitung, fusszeile, logo, logo_mime, logo_skala FROM rechnung_layout LIMIT 1")
                row = cur.fetchone()
                data = _row_to_dict(cur, row)
        finally:
            try: con.close()
            except Exception: pass

        self.text_kopf.setPlainText(data.get("kopfzeile") or "")
        self.text_einleitung.setPlainText(data.get("einleitung") or "")
        self.text_fuss.setPlainText(data.get("fusszeile") or "")
        try:
            self.logo_skala = float(data.get("logo_skala") or 100.0)
        except Exception:
            self.logo_skala = 100.0
        s = int(round(self.logo_skala / 10.0) * 10)
        self.scale_slider.setValue(self._snap10(s))
        self.scale_spin.setValue(self._snap10(s))

        v = data.get("logo")
        if isinstance(v, memoryview):
            v = v.tobytes()
        self.logo_bytes = v if isinstance(v, (bytes, bytearray)) else None
        self.logo_mime = data.get("logo_mime") or None

        pm = QPixmap()
        if self.logo_bytes and pm.loadFromData(bytes(self.logo_bytes)):
            self.logo_vorschau.setPixmap(pm)
        else:
            self.logo_vorschau.clear()
        self.btn_logo_entfernen.setEnabled(bool(self.logo_bytes))

    def speichern(self):
        kopf = self.text_kopf.toPlainText().strip()
        einl = self.text_einleitung.toPlainText().strip()
        fuss = self.text_fuss.toPlainText().strip()
        scale = float(self._snap10(self.scale_spin.value()))

        # Bytes direkt übergeben (SQLite und PostgreSQL unterstützen bytes)
        logo_param = self.logo_bytes

        con = get_db()
        try:
            with con.cursor() as cur:
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
                        INSERT INTO rechnung_layout (kopfzeile, einleitung, fusszeile, logo, logo_mime, logo_skala)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (kopf, einl, fuss, logo_param, self.logo_mime, scale))
                except Exception:
                    try:
                        cur.execute("""
                            INSERT INTO rechnung_layout (kopfzeile, einleitung, fusszeile, logo, logo_mime, logo_skala)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (kopf, einl, fuss, logo_param, self.logo_mime, scale))
                    except Exception as e_inner:
                        # As last resort try INSERT OR REPLACE with sqlite style
                        try:
                            cur.execute("""
                                INSERT OR REPLACE INTO rechnung_layout (id, kopfzeile, einleitung, fusszeile, logo, logo_mime, logo_skala)
                                VALUES (1, ?, ?, ?, ?, ?, ?)
                            """, (kopf, einl, fuss, logo_param, self.logo_mime, scale))
                        except Exception:
                            raise  # re-raise to show error to user
            con.commit()
        except Exception as e:
            try: con.rollback()
            except Exception: pass
            QMessageBox.critical(self, "Fehler", f"Speichern fehlgeschlagen:\n{e}")
            return
        finally:
            try: con.close()
            except Exception: pass

        QMessageBox.information(self, "Gespeichert", "Rechnungslayout wurde gespeichert.")
        self.accept()

    # --- Logo-Aktionen ---
    def logo_auswaehlen(self):
        pfad, _ = QFileDialog.getOpenFileName(self, "Logo auswählen", "", "Bilder (*.png *.jpg *.jpeg *.bmp *.gif *.ico)")
        if not pfad:
            return
        mime = mimetypes.guess_type(pfad)[0] or "application/octet-stream"
        try:
            with open(pfad, "rb") as f:
                data = f.read()
        except Exception as e:
            QMessageBox.warning(self, "Fehler", f"Logo konnte nicht gelesen werden:\n{e}")
            return
        self.logo_bytes = data
        self.logo_mime = mime
        pm = QPixmap()
        if pm.loadFromData(self.logo_bytes):
            self.logo_vorschau.setPixmap(pm)
        self.btn_logo_entfernen.setEnabled(True)

    def logo_entfernen(self):
        self.logo_bytes = None
        self.logo_mime = None
        self.logo_vorschau.clear()
        self.btn_logo_entfernen.setEnabled(False)


