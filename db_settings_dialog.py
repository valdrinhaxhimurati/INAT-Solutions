# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QRadioButton, QFormLayout, QMessageBox, QWidget
)
from PyQt5.QtCore import Qt
from urllib.parse import quote
import json, os, re, psycopg2, sys, sqlite3


CONFIG_PATHS = [
    os.path.join(os.getcwd(), "config.json"),
    os.path.join(os.path.dirname(__file__), "config.json"),
]


def _load_cfg_with_fallback():
    """config.json robust laden (utf-8 -> cp1252 -> latin-1) und ggf. zurück auf utf-8 schreiben."""
    for p in CONFIG_PATHS:
        if os.path.exists(p):
            for enc in ("utf-8", "cp1252", "latin-1"):
                try:
                    with open(p, "r", encoding=enc) as f:
                        cfg = json.load(f)
                    if enc != "utf-8":
                        with open(p, "w", encoding="utf-8") as fw:
                            json.dump(cfg, fw, indent=4, ensure_ascii=False)
                    return cfg, p
                except UnicodeDecodeError:
                    continue
                except Exception:
                    break
    return {}, CONFIG_PATHS[0]


def _save_cfg(cfg: dict, path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4, ensure_ascii=False)


class DBSettingsDialog(QDialog):
    """Dialog: Lokale vs. externe PostgreSQL-Verbindung konfigurieren."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Datenbank-Einstellungen")
        self.setMinimumWidth(520)
        self.setStyleSheet("""
            QLineEdit { padding: 6px; border-radius: 6px; border: 1px solid #bfbfbf; font-size: 10pt; }
            QPushButton { padding: 6px 14px; border-radius: 6px; background-color: #e6e6e6; }
            QPushButton:hover { background-color: #dcdcdc; }
            QPushButton:pressed { background-color: #cccccc; }
            QRadioButton, QLabel { font-size: 10pt; }
        """)

        # Modus
        self.radio_local = QRadioButton("Lokale PostgreSQL-Datenbank")
        self.radio_remote = QRadioButton("Externe Verbindung (z. B. Aiven Cloud)")
        self.radio_remote.setChecked(True)
        self.radio_local.toggled.connect(self._toggle_mode)

        mode_row = QHBoxLayout()
        mode_row.addWidget(self.radio_local)
        mode_row.addSpacing(10)
        mode_row.addWidget(self.radio_remote)

        # Lokale Felder
        self.local_host = QLineEdit("localhost")
        self.local_port = QLineEdit("5432")
        self.local_db   = QLineEdit("inatdb")
        self.local_user = QLineEdit("inat_user")
        self.local_pass = QLineEdit()
        self.local_pass.setEchoMode(QLineEdit.Password)

        form_local = QFormLayout()
        form_local.addRow("Host:",      self.local_host)
        form_local.addRow("Port:",      self.local_port)
        form_local.addRow("Datenbank:", self.local_db)
        form_local.addRow("Benutzer:",  self.local_user)
        form_local.addRow("Passwort:",  self.local_pass)
        self.local_form = QWidget(); self.local_form.setLayout(form_local)

        # Remote-URL
        self.pg_url = QLineEdit()
        self.pg_url.setPlaceholderText("postgresql://user:pass@host:port/dbname?sslmode=require")

        # Buttons
        self.test_btn   = QPushButton("Verbindung testen")
        self.save_btn   = QPushButton("Speichern")
        self.cancel_btn = QPushButton("Abbrechen")
        self.test_btn.clicked.connect(self._test_connection)
        self.save_btn.clicked.connect(self._save)
        self.cancel_btn.clicked.connect(self.reject)

        # Layout
        layout = QVBoxLayout()
        layout.addLayout(mode_row)
        layout.addSpacing(8)
        layout.addWidget(self.local_form)
        layout.addWidget(self.pg_url)
        layout.addSpacing(12)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self.test_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(self.cancel_btn)
        btn_row.addWidget(self.save_btn)
        layout.addLayout(btn_row)

        self.info_label = QLabel("")
        self.info_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.info_label.setStyleSheet("color: gray; font-size: 9pt; margin-top: 8px;")
        layout.addWidget(self.info_label)

        self.setLayout(layout)
        self._load_into_ui()
        self._toggle_mode()

    # --- intern ---
    def _toggle_mode(self):
        is_local = self.radio_local.isChecked()
        self.local_form.setVisible(is_local)
        self.pg_url.setVisible(not is_local)

    def _load_into_ui(self):
        cfg, path = _load_cfg_with_fallback()
        self.info_label.setText(f"Gespeichert in: {os.path.abspath(path)}")
        url = (cfg.get("postgres_url") or "").strip()
        # einfache Heuristik: localhost -> lokaler Modus
        if "localhost" in url or "127.0.0.1" in url:
            self.radio_local.setChecked(True)
            try:
                m = re.match(r".*://(.*?):(.*?)@(.*?):(\d+)/(.*)", url)
                if m:
                    self.local_user.setText(m.group(1))
                    self.local_pass.setText(m.group(2))
                    self.local_host.setText(m.group(3))
                    self.local_port.setText(m.group(4))
                    self.local_db.setText(m.group(5))
            except Exception:
                pass
        else:
            self.radio_remote.setChecked(True)
            self.pg_url.setText(url)

    def _current_url(self) -> str:
        if self.radio_local.isChecked():
            host = self.local_host.text().strip()
            port = self.local_port.text().strip() or "5432"
            db   = self.local_db.text().strip()
            # user/pass percent-encoden (wichtig für Umlaute / Sonderzeichen)
            user = quote(self.local_user.text().strip(), safe="")
            pwd  = quote(self.local_pass.text().strip(), safe="")
            return f"postgresql://{user}:{pwd}@{host}:{port}/{db}"
        return self.pg_url.text().strip()

    def _test_connection(self):
        url = self._current_url()
        if not url:
            QMessageBox.warning(self, "Fehler", "Bitte Verbindung eingeben.")
            return
        try:
            with psycopg2.connect(url) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT version()")
                    v = cur.fetchone()[0]
            QMessageBox.information(self, "Erfolg", f"Verbindung erfolgreich:\n{v}")
        except Exception as e:
            QMessageBox.critical(self, "Fehler", str(e))

    def _save(self):
        url = self._current_url()
        if not url:
            QMessageBox.warning(self, "Fehler", "Bitte vollständige Daten eingeben.")
            return
        cfg, path = _load_cfg_with_fallback()
        cfg["db_backend"]  = "postgres"
        cfg["postgres_url"] = url
        cfg["pg_mode"]     = "local" if self.radio_local.isChecked() else "remote"
        _save_cfg(cfg, path)
        QMessageBox.information(self, "Gespeichert", "Einstellungen gespeichert.")
        self.accept()


# bevorzugt: ./db/users.db neben der EXE; Fallback: %APPDATA%\INAT Solutions\users.db
def _app_dir():
    return os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(sys.argv[0]))


def _appdata_dir():
    return os.path.join(os.environ.get("APPDATA", _app_dir()), "INAT Solutions")


def _resolve_login_db_path() -> str:
    db_dir = os.path.join(_app_dir(), "db")
    try:
        os.makedirs(db_dir, exist_ok=True)
        return os.path.join(db_dir, "users.db")
    except Exception:
        os.makedirs(_appdata_dir(), exist_ok=True)
        return os.path.join(_appdata_dir(), "users.db")


_SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  role TEXT DEFAULT 'user',
  active INTEGER DEFAULT 1,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


def init_login_db(path: str) -> None:
    con = sqlite3.connect(path)
    try:
        con.executescript(_SCHEMA)
        con.commit()
    finally:
        con.close()


# Globale Variable: überall gleich verwenden
LOGIN_DB_PATH = _resolve_login_db_path()
init_login_db(LOGIN_DB_PATH)
