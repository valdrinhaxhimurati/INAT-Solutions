from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, QTextEdit, QComboBox,
    QPushButton, QDateEdit
)
from PyQt5.QtCore import QDate
from gui.utils import create_button_bar
from db_connection import get_db, dict_cursor_factory

class BuchhaltungDialog(QDialog):
    def __init__(self, eintrag=None, kategorien=None):
        super().__init__()
        self.setWindowTitle("Buchhaltungseintrag")
        self.resize(800, 600)

        layout = QVBoxLayout()

        # NEU: Editierbares Feld für Nr
        layout.addWidget(QLabel("Nr"))
        self.input_nr = QLineEdit()
        layout.addWidget(self.input_nr)

        # Datumseingabe im Schweizer Format
        self.input_datum = QDateEdit()
        self.input_datum.setDisplayFormat("dd.MM.yyyy")
        self.input_datum.setCalendarPopup(True)
        self.input_datum.setDate(QDate.currentDate())

        self.dropdown_typ = QComboBox()
        self.dropdown_typ.addItems(["Einnahme", "Ausgabe"])

        self.dropdown_kategorie = QComboBox()
        if kategorien:
            self.dropdown_kategorie.addItems(kategorien)

        self.input_betrag = QLineEdit()
        self.input_beschreibung = QTextEdit()

        layout.addWidget(QLabel("Datum (TT.MM.JJJJ)"))
        layout.addWidget(self.input_datum)

        layout.addWidget(QLabel("Typ"))
        layout.addWidget(self.dropdown_typ)

        layout.addWidget(QLabel("Kategorie"))
        layout.addWidget(self.dropdown_kategorie)

        layout.addWidget(QLabel("Betrag (CHF)"))
        layout.addWidget(self.input_betrag)

        layout.addWidget(QLabel("Beschreibung"))
        layout.addWidget(self.input_beschreibung)

        # Buttons
        self.btn_speichern = QPushButton("Speichern")

        self.btn_abbrechen = QPushButton("Abbrechen")


        self.btn_speichern.clicked.connect(self.accept)
        self.btn_abbrechen.clicked.connect(self.reject)

        layout.addLayout(create_button_bar(self.btn_speichern, self.btn_abbrechen))
        self.setLayout(layout)

        # Eintrag initialisieren (wenn vorhanden)
        if isinstance(eintrag, dict):
            self.input_nr.setText(str(eintrag.get("id", "")))  # <--- HIER FEHLTE ES!

            # Datum im Format YYYY-MM-DD erwartet
            datum_str = eintrag.get("datum", "")
            qdate = QDate.fromString(datum_str, "yyyy-MM-dd")
            if qdate.isValid():
                self.input_datum.setDate(qdate)

            self.dropdown_typ.setCurrentText(eintrag.get("typ", "Einnahme"))
            self.dropdown_kategorie.setCurrentText(eintrag.get("kategorie", ""))
            self.input_betrag.setText(str(eintrag.get("betrag", "")))
            self.input_beschreibung.setPlainText(eintrag.get("beschreibung", ""))


    def get_daten(self):
        """Rückgabe der eingegebenen Daten als Dictionary"""
        return {
            "id": self.input_nr.text(),
            "datum": self.input_datum.date().toString("yyyy-MM-dd"),
            "typ": self.dropdown_typ.currentText(),
            "kategorie": self.dropdown_kategorie.currentText(),
            "betrag": self.input_betrag.text(),
            "beschreibung": self.input_beschreibung.toPlainText(),
        }


