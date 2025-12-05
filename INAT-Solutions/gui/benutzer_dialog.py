# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QLineEdit,
    QPushButton, QLabel, QMessageBox, QGroupBox, QFormLayout
)
from .base_dialog import BaseDialog
from .dialog_styles import GROUPBOX_STYLE
from db_connection import connect_sqlite_at
from PyQt5.QtWidgets import QLineEdit
import bcrypt
from paths import users_db_path
from i18n import _

USERS_TABLE = "users"

def _conn(db_path: str = None):
    if db_path is None:
        db_path = str(users_db_path())
    return connect_sqlite_at(db_path)

def _has_column(conn, table: str, col: str) -> bool:
    try:
        with conn.cursor() as cur:
            cur.execute(f"PRAGMA table_info({table})")
            return any((r["name"] if isinstance(r, dict) else r[1]).lower() == col.lower() for r in cur.fetchall())
    except Exception:
        return False

def init_db(db_path):
    conn = _conn(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {USERS_TABLE} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash BLOB NOT NULL
                )
            """)
        conn.commit()
    finally:
        conn.close()

def get_users(db_path):
    conn = _conn(db_path)
    try:
        pw_col = "password_hash"
        has_active = _has_column(conn, USERS_TABLE, "active")
        aktiv_expr = "active" if has_active else "1"
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT id,
                       username       AS benutzername,
                       {pw_col}       AS rolle,
                       {aktiv_expr}   AS aktiv
                FROM {USERS_TABLE}
                ORDER BY username ASC
            """)
            return cur.fetchall()
    finally:
        conn.close()

def add_user(benutzername, passwort, rolle="user", aktiv=True, db_path=None):
    conn = _conn(db_path)
    try:
        try:
            from login import hash_password
            pw_val = hash_password(passwort)
        except Exception:
            pw_val = passwort
        cols = ["username", "password_hash"]
        vals = [benutzername, pw_val]
        sql = f"INSERT INTO {USERS_TABLE} ({', '.join(cols)}) VALUES (%s, %s)"
        with conn.cursor() as cur:
            cur.execute(sql, tuple(vals))
        conn.commit()
    finally:
        conn.close()

def update_user(user_id, benutzername=None, rolle=None, aktiv=None, db_path=None):
    conn = _conn(db_path)
    try:
        sets, params = [], []
        if benutzername is not None:
            sets.append("username=%s"); params.append(benutzername)
        if rolle is not None:
            try:
                from login import hash_password
                pw_val = hash_password(rolle)
            except Exception:
                pw_val = rolle
            sets.append("password_hash=%s"); params.append(pw_val)
        if aktiv is not None and _has_column(conn, USERS_TABLE, "active"):
            sets.append("active=%s"); params.append(bool(aktiv))
        if not sets:
            return
        params.append(user_id)
        with conn.cursor() as cur:
            cur.execute(f"UPDATE {USERS_TABLE} SET {', '.join(sets)} WHERE id=%s", tuple(params))
        conn.commit()
    finally:
        conn.close()

def set_password(user_id, neues_passwort, db_path=None):
    conn = _conn(db_path)
    try:
        try:
            from login import hash_password
            pw_val = hash_password(neues_passwort)
        except Exception:
            pw_val = neues_passwort
        with conn.cursor() as cur:
            cur.execute(f"UPDATE {USERS_TABLE} SET password_hash=%s WHERE id=%s", (pw_val, user_id))
        conn.commit()
    finally:
        conn.close()

def delete_user(user_id, db_path=None):
    conn = _conn(db_path)
    try:
        with conn.cursor() as cur:
            cur.execute(f"DELETE FROM {USERS_TABLE} WHERE id=%s", (user_id,))
        conn.commit()
    finally:
        conn.close()


class BenutzerVerwaltenDialog(BaseDialog):
    def __init__(self, db_path, parent=None):
        super().__init__(parent)
        self.db_path = db_path
        self.setWindowTitle(_("Benutzer verwalten"))
        self.resize(480, 450)

        init_db(self.db_path)

        layout = self.content_layout
        layout.setSpacing(15)

        # === Vorhandene Benutzer ===
        liste_group = QGroupBox(_("Vorhandene Benutzer"))
        liste_group.setStyleSheet(GROUPBOX_STYLE)
        liste_layout = QVBoxLayout(liste_group)
        
        self.list = QListWidget()
        self.list.setMinimumHeight(150)
        liste_layout.addWidget(self.list)
        
        layout.addWidget(liste_group)

        # === Neuer Benutzer ===
        neu_group = QGroupBox(_("Neuer Benutzer"))
        neu_group.setStyleSheet(GROUPBOX_STYLE)
        neu_layout = QFormLayout(neu_group)
        neu_layout.setSpacing(10)

        self.ed_user = QLineEdit()
        self.ed_user.setPlaceholderText(_("Benutzername eingeben"))
        neu_layout.addRow(_("Benutzername:"), self.ed_user)

        self.ed_role = QLineEdit()
        self.ed_role.setPlaceholderText(_("Passwort eingeben"))
        self.ed_role.setEchoMode(QLineEdit.Password)
        neu_layout.addRow(_("Passwort:"), self.ed_role)

        layout.addWidget(neu_group)

        layout.addStretch()

        # === Buttons ===
        btn_layout = QHBoxLayout()
        
        self.btn_del = QPushButton(_("Ausgewählten löschen"))
        self.btn_del.clicked.connect(self._delete)
        btn_layout.addWidget(self.btn_del)
        
        btn_layout.addStretch()
        
        btn_cancel = QPushButton(_("Schliessen"))
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        
        self.btn_add = QPushButton(_("Hinzufügen"))
        self.btn_add.clicked.connect(self._add)
        btn_layout.addWidget(self.btn_add)

        layout.addLayout(btn_layout)

        self._reload()

    def _reload(self):
        self.list.clear()
        try:
            rows = get_users(self.db_path)
            for r in rows:
                uid, name, _role, _aktiv = r
                self.list.addItem(f"{uid} - {name}")
        except Exception as e:
            QMessageBox.critical(self, _("Fehler"), str(e))

    def _add(self):
        name = self.ed_user.text().strip()
        pw_plain = self.ed_role.text().strip()
        if not name:
            QMessageBox.warning(self, _("Fehler"), _("Bitte Benutzernamen eingeben."))
            return
        pw_hash = bcrypt.hashpw(pw_plain.encode("utf-8"), bcrypt.gensalt()) if pw_plain else bcrypt.hashpw(b" ", bcrypt.gensalt())
        try:
            conn = _conn(self.db_path)
            with conn.cursor() as cur:
                cur.execute(f"INSERT INTO {USERS_TABLE} (username, password_hash) VALUES (%s, %s)", (name, pw_hash))
            conn.commit()
            conn.close()
            self.ed_user.clear()
            self.ed_role.clear()
            self._reload()
            QMessageBox.information(self, _("Erfolg"), _("Benutzer wurde hinzugefügt."))
        except Exception as e:
            QMessageBox.critical(self, _("Fehler"), str(e))

    def _delete(self):
        item = self.list.currentItem()
        if not item:
            QMessageBox.warning(self, _("Hinweis"), _("Bitte wählen Sie einen Benutzer aus."))
            return
        try:
            uid = int(item.text().split("-", 1)[0].strip())
            delete_user(uid, db_path=self.db_path)
            self._reload()
        except Exception as e:
            QMessageBox.critical(self, _("Fehler"), str(e))

