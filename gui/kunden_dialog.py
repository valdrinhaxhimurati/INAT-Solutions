from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton
from db_connection import get_db, dict_cursor_factory

class KundenDialog(QDialog):
    def __init__(self, parent=None, kunde=None):
        super().__init__(parent)
        self.setWindowTitle("Kunde bearbeiten" if kunde else "Neuen Kunden hinzufügen")
        self.resize(800, 600)

        kunde = kunde or {}  # Falls None, leeres Dict

        layout = QVBoxLayout()

        # Anrede
        self.input_anrede = QLineEdit(kunde.get("anrede", ""))
        layout.addWidget(QLabel("Anrede"))
        layout.addWidget(self.input_anrede)

        # Name
        self.input_name = QLineEdit(kunde.get("name", ""))
        layout.addWidget(QLabel("Name"))
        layout.addWidget(self.input_name)

        # Firma
        self.input_firma = QLineEdit(kunde.get("firma", ""))
        layout.addWidget(QLabel("Firma"))
        layout.addWidget(self.input_firma)

        # PLZ
        self.input_plz = QLineEdit(kunde.get("plz", ""))
        layout.addWidget(QLabel("PLZ"))
        layout.addWidget(self.input_plz)

        # Strasse
        self.input_strasse = QLineEdit(kunde.get("strasse", ""))
        layout.addWidget(QLabel("Strasse"))
        layout.addWidget(self.input_strasse)

        # Stadt
        self.input_stadt = QLineEdit(kunde.get("stadt", ""))
        layout.addWidget(QLabel("Stadt"))
        layout.addWidget(self.input_stadt)

        # Email
        self.input_email = QLineEdit(kunde.get("email", ""))
        layout.addWidget(QLabel("E-Mail"))
        layout.addWidget(self.input_email)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("OK")
        btn_abbrechen = QPushButton("Abbrechen")
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_abbrechen)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

        btn_ok.clicked.connect(self.accept)
        btn_abbrechen.clicked.connect(self.reject)

    def get_daten(self):
        return {
            "anrede": self.input_anrede.text(),
            "name": self.input_name.text(),
            "firma": self.input_firma.text(),
            "plz": self.input_plz.text(),
            "strasse": self.input_strasse.text(),
            "stadt": self.input_stadt.text(),
            "email": self.input_email.text(),
        }



