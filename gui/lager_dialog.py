from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
)
from db_connection import get_db, dict_cursor
class LagerDialog(QDialog):
    def __init__(self, parent=None, artikel=None):
        super().__init__(parent)
        self.setWindowTitle("Artikel erfassen" if artikel is None else "Artikel bearbeiten")
        self.resize(400, 200)
        layout = QVBoxLayout()

        self.artikelnummer_input = QLineEdit()
        self.artikelnummer_input.setPlaceholderText("Artikelnummer")
        self.bezeichnung_input = QLineEdit()
        self.bezeichnung_input.setPlaceholderText("Bezeichnung")
        self.bestand_input = QLineEdit()
        self.bestand_input.setPlaceholderText("Bestand (Zahl)")
        self.lagerort_input = QLineEdit()
        self.lagerort_input.setPlaceholderText("Lagerort")

        if artikel:
            self.artikelnummer_input.setText(artikel.get("artikelnummer", ""))
            self.bezeichnung_input.setText(artikel.get("bezeichnung", ""))
            self.bestand_input.setText(str(artikel.get("bestand", "")))
            self.lagerort_input.setText(artikel.get("lagerort", ""))

        layout.addWidget(QLabel("Artikelnummer:"))
        layout.addWidget(self.artikelnummer_input)
        layout.addWidget(QLabel("Bezeichnung:"))
        layout.addWidget(self.bezeichnung_input)
        layout.addWidget(QLabel("Bestand:"))
        layout.addWidget(self.bestand_input)
        layout.addWidget(QLabel("Lagerort:"))
        layout.addWidget(self.lagerort_input)

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
        # Pflichtfelder prüfen
        if not self.artikelnummer_input.text().strip():
            QMessageBox.warning(self, "Pflichtfeld", "Bitte Artikelnummer eingeben!")
            return
        if not self.bestand_input.text().strip().isdigit():
            QMessageBox.warning(self, "Pflichtfeld", "Bitte Bestand als Zahl eingeben!")
            return
        self.accept()

    def get_daten(self):
        return {
            "artikelnummer": self.artikelnummer_input.text().strip(),
            "bezeichnung": self.bezeichnung_input.text().strip(),
            "bestand": int(self.bestand_input.text().strip()),
            "lagerort": self.lagerort_input.text().strip()
        }
