# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QRadioButton, QFormLayout, QMessageBox, QWidget
)
from PyQt5.QtCore import Qt
import json, os, psycopg2


CONFIG_PATHS = [
    os.path.join(os.getcwd(), "config.json"),
    os.path.join(os.path.dirname(__file__), "config.json"),
]

def _load_cfg():
    for p in CONFIG_PATHS:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f), p
    return {}, CONFIG_PATHS[0]

def _save_cfg(cfg, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4, ensure_ascii=False)


class DBSettingsDialog(QDialog):
    """Dialog zum Umschalten zwischen lokaler und externer PostgreSQL-Verbindung"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Datenbank-Einstellungen")
        self.setMinimumWidth(520)

        # ---------- Moduswahl ----------
        self.radio_local = QRadioButton("Lokale PostgreSQL-Datenbank")
        self.radio_remote = QRadioButton("Externe Verbindung (z. B. Aiven Cloud)")
        self.radio_remote.setChecked(True)
        self.radio_local.toggled.connect(self._toggle_mode)

        mode_row = QHBoxLayout()
        mode_row.addWidget(self.radio_local)
        mode_row.addWidget(self.radio_remote)

        # ---------- Lokale Felder ----------
        self.local_host = QLineEdit("localhost")
        self.local_port = QLineEdit("5432")
        self.local_db = QLineEdit("inatdb")
        self.local_user = QLineEdit("inat_user")
        self.local_pass = QLineEdit()
        self.local_pass.setEchoMode(QLineEdit.Password)

        form_local = QFormLayout()
        form_local.addRow("Host:", self.local_host)
        form_local.addRow("Port:", self.local_port)
        form_local.addRow("Datenbank:", self.local_db)
        form_local.addRow("Benutzer:", self.local_user)
        form_local.addRow("Passwort:", self.local_pass)
        self.local_form = QWidget()
        self.local_form.setLayout(form_local)

        # ---------- Remote-Feld ----------
        self.pg_url = QLineEdit()
        self.pg_url.setPlaceholderText("postgresql://user:pass@host:port/dbname?sslmode=require")

        # ---------- Buttons ----------
        self.test_btn = QPushButton("Verbindung testen")
        self.save_btn = QPushButton("Speichern")
        self.cancel_btn = QPushButton("Abbrechen")

        self.test_btn.clicked.connect(self._test_connection)
        self.save_btn.clicked.connect(self._save)
        self.cancel_btn.clicked.connect(self.reject)

        # ---------- Layout ----------
        layout = QVBoxLayout()
        layout.addLayout(mode_row)
        layout.addSpacing(10)
        layout.addWidget(self.local_form)
        layout.addWidget(self.pg_url)
        layout.addSpacing(10)

        # Buttonreihe unten
        btn_row = QHBoxLayout()
        btn_row.addWidget(self.test_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(self.cancel_btn)
        btn_row.addWidget(self.save_btn)
        layout.addLayout(btn_row)

        # Infozeile unten (Pfad zur config.json)
        self.info_label = QLabel("")
        self.info_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.info_label.setStyleSheet("color: gray; font-size: 10pt;")
        layout.addWidget(self.info_label)

        self.setLayout(layout)
        self._load_into_ui()
        self._toggle_mode()

    # ---------- Helper ----------
    def _toggle_mode(self):
        """Zeigt nur die relevanten Felder"""
        is_local = self.radio_local.isChecked()
        self.local_form.setVisible(is_local)
        self.pg_url.setVisible(not is_local)

    def _load_into_ui(self):
        cfg, path = _load_cfg()
        self.info_label.setText(f"Gespeichert in: {os.path.abspath(path)}")
        url = cfg.get("postgres_url", "")
        if "localhost" in url or "127.0.0.1" in url:
            self.radio_local.setChecked(True)
            import re
            m = re.match(r".*://(.*?):(.*?)@(.*?):(\d+)/(.*)", url)
            if m:
                self.local_user.setText(m.group(1))
                self.local_pass.setText(m.group(2))
                self.local_host.setText(m.group(3))
                self.local_port.setText(m.group(4))
                self.local_db.setText(m.group(5))
        else:
            self.radio_remote.setChecked(True)
            self.pg_url.setText(url)

    def _current_url(self):
        if self.radio_local.isChecked():
            host = self.local_host.text().strip()
            port = self.local_port.text().strip() or "5432"
            db = self.local_db.text().strip()
            user = self.local_user.text().strip()
            pwd = self.local_pass.text().strip()
            return f"postgresql://{user}:{pwd}@{host}:{port}/{db}"
        else:
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
        cfg, path = _load_cfg()
        cfg["db_backend"] = "postgres"
        cfg["postgres_url"] = url
        cfg["pg_mode"] = "local" if self.radio_local.isChecked() else "remote"
        _save_cfg(cfg, path)
        QMessageBox.information(self, "Gespeichert", "Einstellungen gespeichert.")
        self.accept()
