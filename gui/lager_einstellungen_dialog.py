# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QCheckBox, QPushButton, QHBoxLayout, QMessageBox
from db_connection import get_db
import sqlite3

def _to_bool(val):
    """Normalisiere DB-Werte zu bool. Akzeptiert bool, int, '0'/'1', 'true'/'false'."""
    if isinstance(val, bool):
        return val
    if val is None:
        return False
    try:
        return bool(int(val))
    except Exception:
        s = str(val).strip().lower()
        return s in ("1", "true", "t", "yes", "y")

class LagerEinstellungenDialog(QDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle("Lager-Module aktivieren")
        layout = QVBoxLayout()

        # Ein einziges Mapping für alle Checkboxen
        self.checkboxes = {}
        lager_typen = ["material", "reifen", "artikel", "dienstleistungen"]
        for typ in lager_typen:
            cb = QCheckBox(f"{typ.capitalize()}lager aktivieren")
            self.checkboxes[typ] = cb
            layout.addWidget(cb)

        # Lade aktuelle Einstellungen
        self._load_einstellungen()

        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("Speichern")
        btn_ok.clicked.connect(self._save_einstellungen)
        btn_cancel = QPushButton("Abbrechen")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def _load_einstellungen(self):
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT lager_typ, aktiv FROM lager_einstellungen")
            rows = cur.fetchall()
            # rows können Tupel (lager_typ, aktiv) oder Dicts sein
            for row in rows:
                if isinstance(row, dict):
                    lager_typ = row.get('lager_typ')
                    aktiv_val = row.get('aktiv')
                else:
                    # Tuple: index 0 = lager_typ, index 1 = aktiv
                    if len(row) >= 2:
                        lager_typ, aktiv_val = row[0], row[1]
                    else:
                        continue
                chk = self.checkboxes.get(lager_typ)
                if chk is not None:
                    try:
                        chk.setChecked(_to_bool(aktiv_val))
                    except Exception:
                        chk.setChecked(False)
            conn.close()
        except Exception as e:
            QMessageBox.warning(self, "Fehler", f"Fehler beim Laden der Einstellungen: {e}")

    def _save_einstellungen(self):
        try:
            conn = get_db()
            cur = conn.cursor()

            # Detect sqlite connection to choose paramstyle / upsert
            is_sqlite = isinstance(conn, sqlite3.Connection) or "sqlite" in conn.__class__.__module__.lower()

            for lager_typ, chk in self.checkboxes.items():
                aktiv_val = 1 if chk.isChecked() else 0
                if is_sqlite:
                    # SQLite: INSERT OR REPLACE works with UNIQUE index on lager_typ
                    cur.execute(
                        "INSERT OR REPLACE INTO lager_einstellungen (lager_typ, aktiv) VALUES (?, ?)",
                        (lager_typ, aktiv_val)
                    )
                else:
                    # Postgres (psycopg2): use %s placeholders and ON CONFLICT
                    cur.execute(
                        "INSERT INTO lager_einstellungen (lager_typ, aktiv) VALUES (%s, %s) "
                        "ON CONFLICT (lager_typ) DO UPDATE SET aktiv = EXCLUDED.aktiv",
                        (lager_typ, aktiv_val)
                    )
            conn.commit()
            conn.close()
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Fehler beim Speichern: {e}")