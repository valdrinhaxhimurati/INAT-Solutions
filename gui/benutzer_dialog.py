# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QLineEdit,
    QPushButton, QLabel, QMessageBox
)
# NEU: BaseDialog importieren
from .base_dialog import BaseDialog
from db_connection import connect_sqlite_at
from PyQt5.QtWidgets import QLineEdit
import bcrypt
from paths import users_db_path

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
        pw_col = "password_hash"  # in deiner DB vorhanden
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
    # rolle wird ignoriert; wir speichern password_hash
    conn = _conn(db_path)
    try:
        try:
            from login import hash_password  # falls vorhanden, wie im Login verwenden
            pw_val = hash_password(passwort)
        except Exception:
            pw_val = passwort  # Fallback: im Klartext (nicht empfohlen)
        cols = ["username", "password_hash"]
        vals = [benutzername, pw_val]
        sql = f"INSERT INTO {USERS_TABLE} ({', '.join(cols)}) VALUES (%s, %s)"
        with conn.cursor() as cur:
            cur.execute(sql, tuple(vals))
        conn.commit()
    finally:
        conn.close()

def update_user(user_id, benutzername=None, rolle=None, aktiv=None, db_path=None):
    # rolle ist hier das Passwort (-> password_hash)
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


# Optional: Passwortfeld-UI als Password anzeigen (falls Attribut vorhanden)
def _configure_password_field(self):
    if hasattr(self, "passwort_edit") and isinstance(self.passwort_edit, QLineEdit):
        self.passwort_edit.setEchoMode(QLineEdit.Password)
        self.passwort_edit.setReadOnly(False)


# ÄNDERUNG: Von BaseDialog erben
class BenutzerVerwaltenDialog(BaseDialog):
    def __init__(self, db_path, parent=None):
        super().__init__(parent)
        self.db_path = db_path
        self.setWindowTitle("Benutzer verwalten")
        self.setMinimumWidth(400)

        # Tabelle users sicherstellen und Liste laden
        init_db(self.db_path)

        # UI
        # WICHTIG: Das Layout vom BaseDialog verwenden
        lay = self.content_layout
        self.list = QListWidget()
        lay.addWidget(self.list)

        row = QHBoxLayout()
        self.ed_user = QLineEdit(); self.ed_user.setPlaceholderText("Benutzername")
        self.ed_role = QLineEdit(); self.ed_role.setPlaceholderText("Passwort")
        row.addWidget(self.ed_user); row.addWidget(self.ed_role)
        lay.addLayout(row)

        row2 = QHBoxLayout()
        self.btn_add = QPushButton("Hinzufügen")
        self.btn_del = QPushButton("Löschen")
        # linksbündig: Stretch ans Ende
        row2.addWidget(self.btn_del); row2.addWidget(self.btn_add); row2.addStretch(1)
        lay.addLayout(row2)

        self.btn_add.clicked.connect(self._add)
        self.btn_del.clicked.connect(self._delete)

        self._reload()
        self._fix_password_field()

    def _load_users(self):
        rows = get_users(self.db_path)        # statt get_users()
        # rows: [(id, benutzername, passwort_hash, rolle), ...]
        for r in rows:
            uid, name, _, rolle = r
            txt = f"{name}  ({rolle})" if rolle else name
            self.list.addItem(f"{uid} – {txt}")

    def _fix_password_field(self):
        if hasattr(self, "passwort_edit") and isinstance(self.passwort_edit, QLineEdit):
            self.passwort_edit.setEchoMode(QLineEdit.Password)
            self.passwort_edit.setReadOnly(False)

    def init_db(self, db_path=None):
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS benutzer (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        benutzername TEXT UNIQUE NOT NULL,
                        passwort TEXT NOT NULL,
                        rolle TEXT NOT NULL DEFAULT 'user',
                        aktiv INTEGER NOT NULL DEFAULT 1
                    )
                """)
                # Default-User, falls Tabelle leer
                cur.execute("SELECT COUNT(1) FROM benutzer")
                if (cur.fetchone() or [0])[0] == 0:
                    cur.execute(
                        "INSERT INTO benutzer (benutzername, passwort, rolle, aktiv) VALUES (%s, %s, %s, %s)",
                        ("admin", "admin", "admin", True)
                    )
            conn.commit()
        finally:
            conn.close()

    def _reload(self):
        self.list.clear()
        try:
            rows = get_users(self.db_path)
            # rows: (id, benutzername, rolle=password_hash, aktiv)
            for r in rows:
                uid, name, _, _ = r
                self.list.addItem(f"{uid} – {name}")
        except Exception as e:
            QMessageBox.critical(self, "Fehler", str(e))

    def _add(self):
        name = self.ed_user.text().strip()
        pw_plain = self.ed_role.text().strip()
        if not name:
            QMessageBox.warning(self, "Fehler", "Bitte Benutzernamen eingeben.")
            return
        # Passwort-Hash wie im Login (bcrypt)
        pw_hash = bcrypt.hashpw(pw_plain.encode("utf-8"), bcrypt.gensalt()) if pw_plain else bcrypt.hashpw(b" ", bcrypt.gensalt())
        try:
            # direkte Insert, damit der Hash sicher Bytes bleibt
            conn = _conn(self.db_path)
            with conn.cursor() as cur:
                cur.execute(f"INSERT INTO {USERS_TABLE} (username, password_hash) VALUES (%s, %s)", (name, pw_hash))
            conn.commit(); conn.close()
            self.ed_user.clear(); self.ed_role.clear()
            self._reload()
            # Füge hinzu: Schließe den Dialog automatisch nach dem Hinzufügen
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Fehler", str(e))

    def _delete(self):
        item = self.list.currentItem()
        if not item:
            return
        try:
            uid = int(item.text().split("–", 1)[0].strip())
            delete_user(uid, db_path=self.db_path)
            self._reload()
        except Exception as e:
            QMessageBox.critical(self, "Fehler", str(e))

