from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from db_connection import get_db, dict_cursor_factory

class LieferantenDialog(QDialog):
    def __init__(self, parent=None, lieferant=None):
        super().__init__(parent)
        self.setWindowTitle("Lieferant erfassen" if lieferant is None else "Lieferant bearbeiten")
        self.resize(400, 200)
        layout = QVBoxLayout()

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Name")
        self.link_input = QLineEdit()
        self.link_input.setPlaceholderText("Portal-Link")
        self.login_input = QLineEdit()
        self.login_input.setPlaceholderText("Benutzername")
        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("Passwort")
        self.pass_input.setEchoMode(QLineEdit.Password)

        if lieferant:
            self.name_input.setText(lieferant.get("name", ""))
            self.link_input.setText(lieferant.get("portal_link", ""))
            self.login_input.setText(lieferant.get("login", ""))
            self.pass_input.setText(lieferant.get("passwort", ""))

        layout.addWidget(QLabel("Name:"))
        layout.addWidget(self.name_input)
        layout.addWidget(QLabel("Portal-Link:"))
        layout.addWidget(self.link_input)
        layout.addWidget(QLabel("Benutzername:"))
        layout.addWidget(self.login_input)
        layout.addWidget(QLabel("Passwort:"))
        layout.addWidget(self.pass_input)

        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("OK")
        btn_cancel = QPushButton("Abbrechen")
        btn_ok.clicked.connect(self.accept_dialog)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def accept_dialog(self):
        # Optional: Pflichtfelder prüfen
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Pflichtfeld", "Bitte Name eingeben!")
            return
        self.accept()

    def get_daten(self):
        return {
            "name": self.name_input.text().strip(),
            "portal_link": self.link_input.text().strip(),
            "login": self.login_input.text().strip(),
            "passwort": self.pass_input.text().strip()
        }



