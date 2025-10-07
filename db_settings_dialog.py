# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox, QFileDialog, QMessageBox, QWidget)
from PyQt5.QtCore import Qt
import os, json
try:
    import psycopg2
except Exception:
    psycopg2 = None

CONFIG_CANDIDATES = [os.path.join(os.getcwd(), "config.json"), os.path.join(os.path.dirname(__file__), "config.json")]
def _load_config():
    for p in CONFIG_CANDIDATES:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f), p
    return {}, CONFIG_CANDIDATES[0]
def _save_config(cfg, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

class DBSettingsDialog(QDialog):
    def __init__(self, parent: QWidget = None):
        super().__init__(parent); self.setWindowTitle("Datenbank-Einstellungen"); self.setMinimumWidth(560)
        self.backend_combo = QComboBox(); self.backend_combo.addItems(["SQLite", "PostgreSQL"]); self.backend_combo.currentIndexChanged.connect(self._on_backend_changed)
        self.sqlite_path = QLineEdit(); self.sqlite_browse = QPushButton("Pfad wählen …"); self.sqlite_browse.clicked.connect(self._choose_sqlite)
        self.pg_url = QLineEdit(); self.pg_url.setPlaceholderText("postgresql://user:pass@host:5432/dbname?sslmode=require")
        self.pg_test = QPushButton("Verbindung testen"); self.pg_test.clicked.connect(self._test_pg)
        self.btn_save = QPushButton("Speichern"); self.btn_cancel = QPushButton("Abbrechen"); self.btn_save.clicked.connect(self._on_save); self.btn_cancel.clicked.connect(self.reject)
        lay = QVBoxLayout()
        row0 = QHBoxLayout(); row0.addWidget(QLabel("Datenbank-Typ:")); row0.addWidget(self.backend_combo); row0.addStretch(1); lay.addLayout(row0)
        row_sqlite = QHBoxLayout(); row_sqlite.addWidget(self.sqlite_path, 1); row_sqlite.addWidget(self.sqlite_browse); lay.addLayout(row_sqlite); self.row_sqlite = row_sqlite
        lay.addWidget(QLabel("PostgreSQL-URL:")); lay.addWidget(self.pg_url); lay.addWidget(self.pg_test, alignment=Qt.AlignLeft)
        row_btns = QHBoxLayout(); row_btns.addStretch(1); row_btns.addWidget(self.btn_cancel); row_btns.addWidget(self.btn_save); lay.addLayout(row_btns)
        self.setLayout(lay); self._load_into_ui(); self._on_backend_changed(self.backend_combo.currentIndex())
    def _load_into_ui(self):
        cfg, _ = _load_config(); backend = (cfg.get("db_backend") or "sqlite").lower()
        self.backend_combo.setCurrentText("PostgreSQL" if backend == "postgres" else "SQLite")
        self.sqlite_path.setText(cfg.get("db_pfad","datenbank.sqlite")); self.pg_url.setText(cfg.get("postgres_url",""))
    def _on_backend_changed(self, _):
        is_pg = (self.backend_combo.currentText() == "PostgreSQL")
        for i in range(self.row_sqlite.count()):
            w = self.row_sqlite.itemAt(i).widget()
            if w: w.setVisible(not is_pg)
        self.pg_url.setVisible(is_pg); self.pg_test.setVisible(is_pg)
    def _choose_sqlite(self):
        path, _ = QFileDialog.getSaveFileName(self, "SQLite-Datei wählen", "datenbank.sqlite", "SQLite DB (*.sqlite)")
        if path: self.sqlite_path.setText(path)
    def _test_pg(self):
        if not psycopg2: QMessageBox.warning(self, "psycopg2 fehlt", "Bitte 'pip install psycopg2-binary' installieren."); return
        url = self.pg_url.text().strip()
        if not url: QMessageBox.warning(self, "URL fehlt", "Bitte eine PostgreSQL-URL eingeben."); return
        try:
            with psycopg2.connect(url) as conn:
                with conn.cursor() as cur: cur.execute("SELECT 1"); cur.fetchone()
            QMessageBox.information(self, "Erfolg", "Verbindung erfolgreich.")
        except Exception as e:
            QMessageBox.critical(self, "Fehler", str(e))
    def _on_save(self):
        cfg, path = _load_config()
        if self.backend_combo.currentText() == "PostgreSQL":
            url = self.pg_url.text().strip()
            if not url: QMessageBox.warning(self, "URL fehlt", "Bitte eine PostgreSQL-URL eingeben."); return
            cfg["db_backend"] = "postgres"; cfg["postgres_url"] = url
        else:
            dbpfad = self.sqlite_path.text().strip() or "datenbank.sqlite"
            cfg["db_backend"] = "sqlite"; cfg["db_pfad"] = dbpfad
        _save_config(cfg, path); self.accept()
