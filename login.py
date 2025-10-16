import os
import sys
import sqlite3
import bcrypt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QFrame, QSizePolicy, QHBoxLayout
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def _app_dir():
    return os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(sys.argv[0]))

def _db_dir():
    d = os.path.join(_app_dir(), "db")
    os.makedirs(d, exist_ok=True)
    return d

LOGIN_DB_PATH = os.path.join(_db_dir(), "users.db")

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

# beim Import sicherstellen
init_login_db(LOGIN_DB_PATH)

def get_login_db_path() -> str:
    return LOGIN_DB_PATH

def get_conn():
    return sqlite3.connect(LOGIN_DB_PATH)

class LoginDialog(QDialog):
    def __init__(self, db_path, parent=None):
        super().__init__(parent)
        self.db_path = db_path
        self.setWindowIcon(QIcon(resource_path("favicon.ico")))
        self.setWindowTitle("Login")
        self.setFixedSize(400, 250)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        self.login_ok = False
        self.logged_in_user = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)

        title = QLabel("Anmeldung")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        layout.addWidget(title)

        self.input_user = QLineEdit()
        self.input_user.setPlaceholderText("Benutzername")
        self.input_user.setMinimumHeight(36)
        layout.addWidget(self.input_user)

        self.input_pass = QLineEdit()
        self.input_pass.setPlaceholderText("Passwort")
        self.input_pass.setEchoMode(QLineEdit.Password)
        self.input_pass.setMinimumHeight(36)
        layout.addWidget(self.input_pass)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.btn_login = QPushButton("Anmelden")
        self.btn_login.setCursor(Qt.PointingHandCursor)
        self.btn_login.setMinimumHeight(36)
        self.btn_login.setMinimumWidth(120)
        self.btn_login.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        button_layout.addWidget(self.btn_login)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        self.btn_login.clicked.connect(self.check_login)

    def check_login(self):
        username = self.input_user.text()
        password = self.input_pass.text()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()
        conn.close()

        if result and bcrypt.checkpw(password.encode(), result[0]):
            self.logged_in_user = username
            self.login_ok = True
            self.accept()
        else:
            QMessageBox.warning(self, "Fehler", "Benutzername oder Passwort falsch")

# SQLite-Initfunktion (falls nicht vorhanden) und Legacy-Alias bereitstellen
try:
    init_login_db  # type: ignore[name-defined]
except NameError:
    import os, sys, sqlite3
    def _app_dir():
        return os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(sys.argv[0]))
    def _db_dir():
        d = os.path.join(_app_dir(), "db"); os.makedirs(d, exist_ok=True); return d
    LOGIN_DB_PATH = os.path.join(_db_dir(), "users.db")
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
    def init_login_db(path: str = None):
        if path is None:
            path = LOGIN_DB_PATH
        con = sqlite3.connect(path)
        try:
            con.executescript(_SCHEMA)
            con.commit()
        finally:
            con.close()

# Legacy-Name, den main.py erwartet
def init_db(path: str = None):
    return init_login_db(path)
