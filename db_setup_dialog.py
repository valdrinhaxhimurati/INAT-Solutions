# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QRadioButton, QButtonGroup, QMessageBox,
    QWidget, QFormLayout, QCheckBox
)
import json, os, psycopg2
# init_db wird bei Bedarf lokal importiert, um zirkuläre Importe zu vermeiden

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
        self.setWindowTitle("Datenbank einrichten")
        self.setMinimumWidth(520)

        # Modi
        self.mode_existing = QRadioButton("Mit bestehender PostgreSQL-Instanz verbinden (Connection-URL)")
        self.mode_local = QRadioButton("Lokale PostgreSQL-Datenbank anlegen (auf diesem PC)")
        self.mode_existing.setChecked(True)
        self.grp = QButtonGroup(self)
        self.grp.addButton(self.mode_existing)
        self.grp.addButton(self.mode_local)

        # Remote-URL
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("postgresql://user:pass@host:5432/dbname?sslmode=require")

        # Lokale DB-Einstellungen
        self.local_user = QLineEdit("inat_user")
        self.local_pass = QLineEdit()
        self.local_pass.setEchoMode(QLineEdit.Password)
        self.local_db = QLineEdit("inatdb")
        self.apply_schema_cb = QCheckBox("Initiales Schema anlegen")
        self.apply_schema_cb.setChecked(True)
        self.super_url = QLineEdit("postgresql://postgres:PASSWORT@localhost:5432/postgres")

        # Layouts
        form_existing = QFormLayout()
        form_existing.addRow("Connection-URL:", self.url_edit)

        form_local = QFormLayout()
        form_local.addRow("DB-Name:", self.local_db)
        form_local.addRow("App-Benutzer:", self.local_user)
        form_local.addRow("App-Passwort:", self.local_pass)
        form_local.addRow("", self.apply_schema_cb)
        form_local.addRow("Superuser-URL:", self.super_url)

        btn_ok = QPushButton("Speichern und verbinden")
        btn_cancel = QPushButton("Abbrechen")
        btn_ok.clicked.connect(self.on_accept)
        btn_cancel.clicked.connect(self.reject)

        lay = QVBoxLayout()
        lay.addWidget(self.mode_existing)
        lay.addLayout(form_existing)
        lay.addSpacing(12)
        lay.addWidget(self.mode_local)
        lay.addLayout(form_local)
        lay.addSpacing(12)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(btn_cancel)
        row.addWidget(btn_ok)
        lay.addLayout(row)
        self.setLayout(lay)

        cfg, _ = _load_cfg()
        if cfg.get("postgres_url"):
            self.url_edit.setText(cfg["postgres_url"])

        # Defaultwerte setzen (anpassen nach Wunsch)
        try:
            self.super_user_input.setText("postgres")
            self.super_pass_input.setText("")        # leer: gib Passwort ein
            self.app_user_input.setText("inat")
            self.app_pass_input.setText("inatpass")  # ändere für Produktion
            self.dbname_input.setText("inat_db")
            if hasattr(self, "host_input"):
                self.host_input.setText("localhost")
            if hasattr(self, "port_input"):
                try:
                    self.port_input.setValue(5432)
                except Exception:
                    # falls port_input ein QLineEdit ist:
                    self.port_input.setText("5432")
            if not hasattr(self, "apply_schema_cb"):
                # optional: Default für Schema-Anwendung
                pass
        except Exception:
            # Falls Widgetnamen anders sind, ruhig bleiben und Debug-Meldung loggen
            import traceback, sys
            print("Fehler beim Setzen der Default-Werte für DB-Dialog:", file=sys.stderr)
            traceback.print_exc()

        # --- Fallback: sicherstellen, dass die erwarteten Eingabefelder existieren ---
        # Verwende QtWidgets.<Klasse>, damit keine Namen im lokalen Scope
        from PyQt5 import QtWidgets

        if not hasattr(self, "super_user_input"):
            self.super_user_input = QtWidgets.QLineEdit(self)
            self.super_user_input.setText("postgres")
        if not hasattr(self, "super_pass_input"):
            self.super_pass_input = QtWidgets.QLineEdit(self)
            self.super_pass_input.setEchoMode(QtWidgets.QLineEdit.Password)
        if not hasattr(self, "app_user_input"):
            self.app_user_input = QtWidgets.QLineEdit(self)
            self.app_user_input.setText("inat")
        if not hasattr(self, "app_pass_input"):
            self.app_pass_input = QtWidgets.QLineEdit(self)
            self.app_pass_input.setEchoMode(QtWidgets.QLineEdit.Password)
        if not hasattr(self, "dbname_input"):
            self.dbname_input = QtWidgets.QLineEdit(self)
            self.dbname_input.setText("inat_db")
        if not hasattr(self, "host_input"):
            self.host_input = QtWidgets.QLineEdit(self)
            self.host_input.setText("localhost")
        if not hasattr(self, "port_input"):
            self.port_input = QtWidgets.QSpinBox(self)
            self.port_input.setRange(1, 65535)
            self.port_input.setValue(5432)
        if not hasattr(self, "apply_schema_cb"):
            self.apply_schema_cb = QtWidgets.QCheckBox("Schema anwenden", self)
            self.apply_schema_cb.setChecked(False)

        # --- Defensive Default-Werte (erst prüfen / ggf. anlegen) ---
        from PyQt5 import QtWidgets

        def _ensure_lineedit(name, default="", password=False):
            w = getattr(self, name, None)
            if w is None:
                w = QtWidgets.QLineEdit(self)
                setattr(self, name, w)
            try:
                if password:
                    w.setEchoMode(QtWidgets.QLineEdit.Password)
                w.setText(default)
            except Exception:
                pass
            return w

        def _ensure_spinbox(name, default=5432):
            w = getattr(self, name, None)
            if w is None:
                w = QtWidgets.QSpinBox(self)
                setattr(self, name, w)
            try:
                w.setRange(1, 65535)
                w.setValue(int(default))
            except Exception:
                pass
            return w

        # setze Defaults (sorgt dafür, dass die Attribute existieren)
        _ensure_lineedit("super_user_input", "postgres")
        _ensure_lineedit("super_pass_input", "", password=True)
        _ensure_lineedit("app_user_input", "inat")
        _ensure_lineedit("app_pass_input", "inatpass", password=True)
        _ensure_lineedit("dbname_input", "inat_db")
        _ensure_lineedit("host_input", "localhost")
        _ensure_spinbox("port_input", 5432)

        if not hasattr(self, "apply_schema_cb"):
            cb = QtWidgets.QCheckBox("Schema anwenden", self)
            cb.setChecked(False)
            self.apply_schema_cb = cb

    def on_accept(self):
        """
        Einheitlicher Handler: nutzt get_db() (standard: SQLite).
        Liest schema.sql mit Encoding-Fallback und führt Statements nacheinander aus.
        Fehler bei einzelnen Statements werden protokolliert, der Prozess bricht nicht ab.
        """
        try:
            from PyQt5.QtWidgets import QInputDialog, QLineEdit, QMessageBox
            import os, traceback

            # Werte optional per Widget/Dialog abfragen (bestehende Widgets werden benutzt)
            def _widget_text_or_ask(attr_name, title, prompt, is_password=False, default=""):
                w = getattr(self, attr_name, None)
                if w is not None and hasattr(w, "text"):
                    val = w.text().strip()
                    if val:
                        return val
                flags = QLineEdit.Password if is_password else QLineEdit.Normal
                text, ok = QInputDialog.getText(self, title, prompt, flags, default)
                if not ok:
                    raise RuntimeError("Eingabe abgebrochen.")
                return text.strip()

            # Für lokalen Default reichen diese Werte als Fallback
            app_user = _widget_text_or_ask("app_user_input", "App-User", "Anwendungs-Benutzername:", False, "inat")
            app_pass = _widget_text_or_ask("app_pass_input", "App-Passwort", "Passwort für Anwendungs-Benutzer:", True, "inatpass")
            dbname   = _widget_text_or_ask("dbname_input", "Datenbankname", "Name der anzulegenden Datenbank:", False, "inat_db")

            # Versuche die konfigurierte DB (get_db liefert SQLite standardmäßig)
            from db_connection import get_db
            conn = get_db()

            # Lies schema (falls vorhanden) mit Encoding-Fallback
            def _read_schema(path):
                encs = ("utf-8", "cp1252", "latin-1")
                b = None
                try:
                    with open(path, "rb") as f:
                        b = f.read()
                except Exception:
                    return None
                for enc in encs:
                    try:
                        return b.decode(enc), enc
                    except UnicodeDecodeError:
                        continue
                return b.decode("utf-8", errors="replace"), "utf-8(replace)"

            # Versuche schema.sql im Projektroot zu finden
            schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
            if not os.path.exists(schema_path):
                # fallback: one level up (project root)
                schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "schema.sql")
            sql_text = None
            used_enc = None
            if os.path.exists(schema_path):
                sql_text, used_enc = _read_schema(schema_path)

            # Falls SQL-Text vorhanden: Statements ausführen (split auf ;)
            try:
                cur = conn.cursor()
                if sql_text:
                    for stmt in sql_text.split(";"):
                        stmt = stmt.strip()
                        if not stmt:
                            continue
                        try:
                            # bei sqlite/psycopg2 wird ConnectionWrapper.cursor().execute genutzt
                            cur.execute(stmt)
                        except Exception as e_stmt:
                            # log, aber weitermachen
                            try:
                                with open(os.path.join(os.path.dirname(__file__), "error.log"), "a", encoding="utf-8") as ef:
                                    ef.write("Schema statement failed (ignored):\n")
                                    ef.write(str(e_stmt) + "\n")
                            except Exception:
                                pass
                            continue
                # falls ConnectionWrapper hat commit
                try:
                    conn.commit()
                except Exception:
                    pass
            finally:
                try:
                    cur.close()
                except Exception:
                    pass
                try:
                    conn.close()
                except Exception:
                    pass

            QMessageBox.information(self, "Erfolg", "Datenbank erfolgreich eingerichtet (lokal).")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Fehler beim Einrichten der Datenbank", str(e))
            return

    def _try_connect(self, url: str):
        with psycopg2.connect(url) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")

    def _write_config(self, url: str):
        cfg, path = _load_cfg()
        cfg["db_backend"] = "postgres"
        cfg["postgres_url"] = url
        cfg["pg_mode"] = "remote" if "aivencloud" in url else "local"
        _save_cfg(cfg, path)
