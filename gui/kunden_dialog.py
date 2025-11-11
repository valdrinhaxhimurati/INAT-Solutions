from .base_dialog import BaseDialog
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton

class KundenDialog(BaseDialog):
    def __init__(self, parent=None, kunde=None):
        super().__init__(parent)
        self.setWindowTitle("Kunde bearbeiten" if kunde else "Neuen Kunden hinzufügen")
        self.resize(500, 450)

        kunde = kunde or {}

        # WICHTIG: Das Layout vom BaseDialog verwenden (self.content_layout)
        layout = self.content_layout

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

        # --- NEU: Bemerkungsfeld hinzufügen ---
        self.input_bemerkung = QLineEdit(kunde.get("bemerkung", ""))
        layout.addWidget(QLabel("Bemerkung"))
        layout.addWidget(self.input_bemerkung)

        layout.addStretch() # Platzhalter, damit die Buttons unten bleiben

        # Buttons
        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("OK")
        btn_abbrechen = QPushButton("Abbrechen")
        btn_layout.addStretch()
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_abbrechen)

        layout.addLayout(btn_layout)
        # WICHTIG: self.setLayout(layout) wird nicht mehr benötigt, da wir das Layout des BaseDialog verwenden.

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
            # --- NEU: Bemerkung zurückgeben ---
            "bemerkung": self.input_bemerkung.text(),
        }



