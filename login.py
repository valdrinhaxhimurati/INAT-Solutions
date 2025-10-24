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

from paths import data_dir, users_db_path  # NEU: Fallback auf ProgramData

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

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

LOGIN_DB_PATH = str(users_db_path())

def init_login_db(path: str | None = None) -> None:
    if path is None:
        path = LOGIN_DB_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    con = sqlite3.connect(path)
    try:
        con.executescript(_SCHEMA)
        con.commit()
    finally:
        con.close()

def get_conn(db_path: str):
    return sqlite3.connect(db_path)

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
        username = self.input_user.text().strip()
        password = self.input_pass.text()

        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
        finally:
            conn.close()

        if row:
            stored = row[0]
            # Sicherstellen, dass bytes an bcrypt gehen
            if isinstance(stored, str):
                stored = stored.encode("utf-8")
            if bcrypt.checkpw(password.encode("utf-8"), stored):
                self.logged_in_user = username
                self.login_ok = True
                self.accept()
                return

        QMessageBox.warning(self, "Fehler", "Benutzername oder Passwort falsch")

