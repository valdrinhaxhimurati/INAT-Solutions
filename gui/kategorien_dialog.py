from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit, QPushButton,
    QListWidget, QHBoxLayout, QMessageBox, QLabel,
    QSpacerItem, QSizePolicy
)
from paths import data_dir
import json, os
from db_connection import get_db, dict_cursor_factory
class KategorienDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Kategorien verwalten")
        self.resize(450, 350)

        main_layout = QVBoxLayout(self)

        # Label für die Liste
        lbl_vorhanden = QLabel("Vorhandene Kategorien:")
        main_layout.addWidget(lbl_vorhanden)

        # Liste der Kategorien mit größerer Höhe
        self.liste = QListWidget()
        self.liste.setMinimumHeight(180)
        main_layout.addWidget(self.liste)

        # Eingabezeile mit Label
        input_layout = QHBoxLayout()
        lbl_neu = QLabel("Neue Kategorie:")
        lbl_neu.setFixedWidth(110)
        input_layout.addWidget(lbl_neu)

        self.input_kategorie = QLineEdit()
        self.input_kategorie.setPlaceholderText("Kategorie hier eingeben")
        input_layout.addWidget(self.input_kategorie, 1)  # Stretch damit größer

        main_layout.addLayout(input_layout)

        # Buttons in einer Zeile, rechtsbündig
        btn_layout = QHBoxLayout()
        btn_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        btn_hinzufuegen = QPushButton("Hinzufügen")
        btn_hinzufuegen.setFixedWidth(100)
        btn_loeschen = QPushButton("Löschen")
        btn_loeschen.setFixedWidth(100)

        btn_layout.addWidget(btn_hinzufuegen)
        btn_layout.addWidget(btn_loeschen)

        main_layout.addLayout(btn_layout)

        btn_hinzufuegen.clicked.connect(self.kategorie_hinzufuegen)
        btn_loeschen.clicked.connect(self.kategorie_loeschen)

        self.lade_kategorien()

    def lade_kategorien(self):
        einstellungen_path = str(data_dir() / "einstellungen.json")
        if not os.path.exists(einstellungen_path):
            self.kategorien = []
        else:
            with open(einstellungen_path, "r") as f:
                daten = json.load(f)
                self.kategorien = daten.get("buchhaltungs_kategorien", [])
        self.aktualisiere_liste()

    def aktualisiere_liste(self):
        self.liste.clear()
        for kat in self.kategorien:
            self.liste.addItem(kat)

    def kategorie_hinzufuegen(self):
        neue = self.input_kategorie.text().strip()
        if neue and neue not in self.kategorien:
            self.kategorien.append(neue)
            self.aktualisiere_liste()
            self.input_kategorie.clear()
            self.speichern()
        elif neue in self.kategorien:
            QMessageBox.information(self, "Hinweis", "Kategorie existiert bereits.")

    def kategorie_loeschen(self):
        ausgewählt = self.liste.currentItem()
        if ausgewählt:
            text = ausgewählt.text()
            self.kategorien.remove(text)
            self.aktualisiere_liste()
            self.speichern()

    def speichern(self):
        einstellungen_path = str(data_dir() / "einstellungen.json")
        if not os.path.exists(data_dir()):
            os.makedirs(data_dir())
        try:
            with open(einstellungen_path, "r") as f:
                daten = json.load(f)
        except FileNotFoundError:
            daten = {}
        daten["buchhaltungs_kategorien"] = self.kategorien
        with open(einstellungen_path, "w") as f:
            json.dump(daten, f, indent=4)


