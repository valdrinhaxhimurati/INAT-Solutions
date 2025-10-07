# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QRadioButton, QButtonGroup, QMessageBox, QWidget, QFormLayout, QCheckBox)
import json, os, psycopg2
from init_db import ensure_role, ensure_database, apply_schema

CONFIG_PATHS = [os.path.join(os.getcwd(), "config.json"), os.path.join(os.path.dirname(__file__), "config.json")]

def _load_cfg():
    for p in CONFIG_PATHS:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f), p
    return {}, CONFIG_PATHS[0]

def _save_cfg(cfg, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

class DBSetupDialog(QDialog):
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setWindowTitle("Datenbank einrichten"); self.setMinimumWidth(520)
        from PyQt5.QtWidgets import QFormLayout
        self.mode_existing = QRadioButton("Mit bestehender PostgreSQL-Instanz verbinden (Connection-URL)")
        self.mode_local = QRadioButton("Lokale PostgreSQL-Datenbank anlegen (auf diesem PC)")
        self.mode_existing.setChecked(True)
        self.grp = QButtonGroup(self); self.grp.addButton(self.mode_existing); self.grp.addButton(self.mode_local)
        self.url_edit = QLineEdit(); self.url_edit.setPlaceholderText("postgresql://user:pass@host:5432/dbname?sslmode=require")
        form_existing = QFormLayout(); form_existing.addRow(QLabel("Connection-URL:"), self.url_edit)
        self.local_user = QLineEdit("inat_user"); self.local_pass = QLineEdit(); self.local_pass.setEchoMode(QLineEdit.Password)
        self.local_db = QLineEdit("inatdb"); self.apply_schema_cb = QCheckBox("Initiales Schema anlegen (Sequenz, Beispieltabellen)"); self.apply_schema_cb.setChecked(True)
        self.super_url = QLineEdit("postgresql://postgres:PASSWORT@localhost:5432/postgres")
        form_local = QFormLayout(); form_local.addRow("DB-Name:", self.local_db); form_local.addRow("App-Benutzer:", self.local_user); form_local.addRow("App-Passwort:", self.local_pass); form_local.addRow("", self.apply_schema_cb); form_local.addRow("Superuser-URL:", self.super_url)
        btn_ok = QPushButton("Speichern und verbinden"); btn_cancel = QPushButton("Abbrechen"); btn_ok.clicked.connect(self.on_accept); btn_cancel.clicked.connect(self.reject)
        lay = QVBoxLayout(); lay.addWidget(self.mode_existing); lay.addLayout(form_existing); lay.addSpacing(12); lay.addWidget(self.mode_local); lay.addLayout(form_local); lay.addSpacing(12)
        row = QHBoxLayout(); row.addStretch(1); row.addWidget(btn_cancel); row.addWidget(btn_ok); lay.addLayout(row); self.setLayout(lay)
        cfg, _ = _load_cfg(); 
        if cfg.get("postgres_url"): self.url_edit.setText(cfg["postgres_url"])
    def on_accept(self):
        try:
            if self.mode_existing.isChecked():
                url = self.url_edit.text().strip()
                if not url: from PyQt5.QtWidgets import QMessageBox; QMessageBox.warning(self, "Fehlende URL", "Bitte eine PostgreSQL-URL eingeben."); return
                self._try_connect(url); self._write_config(url); self.accept(); return
            super_url = self.super_url.text().strip()
            if not super_url: from PyQt5.QtWidgets import QMessageBox; QMessageBox.warning(self, "Fehlende Superuser-URL", "Bitte Superuser-URL angeben (postgres auf localhost)."); return
            dbname = self.local_db.text().strip(); app_user = self.local_user.text().strip(); app_pass = self.local_pass.text().strip()
            if not (dbname and app_user and app_pass): from PyQt5.QtWidgets import QMessageBox; QMessageBox.warning(self, "Angaben unvollständig", "Bitte DB-Name, App-Benutzer und Passwort ausfüllen."); return
            ensure_role(super_url, app_user, app_pass); ensure_database(super_url, dbname, owner=app_user)
            app_url = f"postgresql://{app_user}:{app_pass}@localhost:5432/{dbname}"
            if self.apply_schema_cb.isChecked(): apply_schema(app_url)
            self._try_connect(app_url); self._write_config(app_url); self.accept()
        except Exception as e:
            from PyQt5.QtWidgets import QMessageBox; QMessageBox.critical(self, "Fehler", f"{e}")
    def _try_connect(self, url: str):
        with psycopg2.connect(url) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1"); cur.fetchone()
    def _write_config(self, url: str):
        cfg, path = _load_cfg(); cfg["db_backend"] = "postgres"; cfg["postgres_url"] = url; _save_cfg(cfg, path)
