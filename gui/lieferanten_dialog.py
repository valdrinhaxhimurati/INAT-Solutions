from .base_dialog import BaseDialog
from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit
)

class LieferantenDialog(BaseDialog):
    def __init__(self, parent=None, lieferant=None):
        super().__init__(parent)
        self.setWindowTitle("Lieferant bearbeiten" if lieferant else "Neuen Lieferant hinzufügen")
        self.resize(500, 550)

        lieferant = lieferant or {}

        layout = self.content_layout

        # Name
        self.input_name = QLineEdit(lieferant.get("name", ""))
        layout.addWidget(QLabel("Name"))
        layout.addWidget(self.input_name)

        # Adresse
        self.input_adresse = QLineEdit(lieferant.get("adresse", ""))
        layout.addWidget(QLabel("Adresse"))
        layout.addWidget(self.input_adresse)

        # Kontaktperson
        self.input_kontaktperson = QLineEdit(lieferant.get("kontaktperson", ""))
        layout.addWidget(QLabel("Kontaktperson"))
        layout.addWidget(self.input_kontaktperson)

        # Email
        self.input_email = QLineEdit(lieferant.get("email", ""))
        layout.addWidget(QLabel("E-Mail"))
        layout.addWidget(self.input_email)

        # Telefon
        self.input_telefon = QLineEdit(lieferant.get("telefon", ""))
        layout.addWidget(QLabel("Telefon"))
        layout.addWidget(self.input_telefon)

        # Portal Link
        self.input_portal_link = QLineEdit(lieferant.get("portal_link", ""))
        layout.addWidget(QLabel("Portal Link"))
        layout.addWidget(self.input_portal_link)

        # Notizen
        self.input_notizen = QTextEdit(lieferant.get("notizen", ""))
        self.input_notizen.setPlaceholderText("Notizen zum Lieferanten...")
        self.input_notizen.setFixedHeight(100)
        layout.addWidget(QLabel("Notizen"))
        layout.addWidget(self.input_notizen)

        layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("OK")
        btn_abbrechen = QPushButton("Abbrechen")
        btn_layout.addStretch()
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_abbrechen)
        layout.addLayout(btn_layout)

        btn_ok.clicked.connect(self.accept)
        btn_abbrechen.clicked.connect(self.reject)

    def get_daten(self):
        return {
            "name": self.input_name.text(),
            "adresse": self.input_adresse.text(),
            "kontaktperson": self.input_kontaktperson.text(),
            "email": self.input_email.text(),
            "telefon": self.input_telefon.text(),
            "portal_link": self.input_portal_link.text(),
            "notizen": self.input_notizen.toPlainText()
        }



