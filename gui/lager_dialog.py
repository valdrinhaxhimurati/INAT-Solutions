from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
)
# NEU: BaseDialog importieren
from .base_dialog import BaseDialog
from db_connection import get_db, dict_cursor_factory

# ÄNDERUNG: Von BaseDialog erben
class LagerDialog(BaseDialog):
    def __init__(self, parent=None, artikel=None):
        super().__init__(parent)
        self.setWindowTitle("Artikel erfassen" if artikel is None else "Artikel bearbeiten")
        self.resize(400, 350) # Höhe leicht angepasst für Titelleiste

        # WICHTIG: Das Layout vom BaseDialog verwenden
        layout = self.content_layout

        layout.addWidget(QLabel("Artikelnummer:"))
        self.artikelnummer_input = QLineEdit()
        layout.addWidget(self.artikelnummer_input) # Hinzugefügt, damit es angezeigt wird

        layout.addWidget(QLabel("Bezeichnung:"))
        self.bezeichnung_input = QLineEdit()
        layout.addWidget(self.bezeichnung_input) # Hinzugefügt, damit es angezeigt wird

        layout.addWidget(QLabel("Bestand:"))
        self.bestand_input = QLineEdit()
        layout.addWidget(self.bestand_input) # Hinzugefügt, damit es angezeigt wird

        layout.addWidget(QLabel("Lagerort:"))
        self.lagerort_input = QLineEdit()
        layout.addWidget(self.lagerort_input) # Hinzugefügt, damit es angezeigt wird

        if artikel:
            self.artikelnummer_input.setText(artikel.get("artikelnummer", ""))
            self.bezeichnung_input.setText(artikel.get("bezeichnung", ""))
            self.bestand_input.setText(str(artikel.get("bestand", "")))
            self.lagerort_input.setText(artikel.get("lagerort", ""))

        # Die folgenden Zeilen sind nicht mehr nötig, da sie oben schon hinzugefügt wurden
        # layout.addWidget(self.artikelnummer_input)
        # layout.addWidget(self.bezeichnung_input)
        # layout.addWidget(self.bestand_input)
        # layout.addWidget(self.lagerort_input)

        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("OK")
        btn_cancel = QPushButton("Abbrechen")
        btn_ok.clicked.connect(self.accept_dialog)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)

        layout.addLayout(btn_layout)
        # ÄNDERUNG: self.setLayout() entfernen
        # self.setLayout(layout)

    def accept_dialog(self):
        # DIESE METHODE BLEIBT UNVERÄNDERT
        # Pflichtfelder pr�fen
        if not self.artikelnummer_input.text().strip():
            QMessageBox.warning(self, "Pflichtfeld", "Bitte Artikelnummer eingeben!")
            return
        if not self.bestand_input.text().strip().isdigit():
            QMessageBox.warning(self, "Pflichtfeld", "Bitte Bestand als Zahl eingeben!")
            return
        self.accept()

    def get_daten(self):
        # DIESE METHODE BLEIBT UNVERÄNDERT
        return {
            "artikelnummer": self.artikelnummer_input.text().strip(),
            "bezeichnung": self.bezeichnung_input.text().strip(),
            "bestand": int(self.bestand_input.text().strip()),
            "lagerort": self.lagerort_input.text().strip()
        }




