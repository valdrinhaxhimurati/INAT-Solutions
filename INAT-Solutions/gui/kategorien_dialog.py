from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit, QPushButton,
    QListWidget, QHBoxLayout, QMessageBox, QLabel,
    QSpacerItem, QSizePolicy, QGroupBox, QFormLayout
)
from paths import data_dir
import json, os
from db_connection import get_einstellungen, set_einstellungen
from .base_dialog import BaseDialog
from .dialog_styles import GROUPBOX_STYLE
from i18n import _


class KategorienDialog(BaseDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Kategorien verwalten"))
        self.resize(480, 450)

        layout = self.content_layout
        layout.setSpacing(15)

        # === Vorhandene Kategorien ===
        liste_group = QGroupBox(_("Vorhandene Kategorien"))
        liste_group.setStyleSheet(GROUPBOX_STYLE)
        liste_layout = QVBoxLayout(liste_group)

        self.liste = QListWidget()
        self.liste.setMinimumHeight(180)
        liste_layout.addWidget(self.liste)

        layout.addWidget(liste_group)

        # === Neue Kategorie ===
        neu_group = QGroupBox(_("Neue Kategorie hinzufügen"))
        neu_group.setStyleSheet(GROUPBOX_STYLE)
        neu_layout = QFormLayout(neu_group)
        neu_layout.setSpacing(10)

        self.input_kategorie = QLineEdit()
        self.input_kategorie.setPlaceholderText(_("Kategorie hier eingeben"))
        neu_layout.addRow(_("Name:"), self.input_kategorie)

        layout.addWidget(neu_group)

        layout.addStretch()

        # === Buttons ===
        btn_layout = QHBoxLayout()

        btn_loeschen = QPushButton(_("Ausgewählte löschen"))
        btn_loeschen.clicked.connect(self.kategorie_loeschen)
        btn_layout.addWidget(btn_loeschen)

        btn_layout.addStretch()

        btn_schliessen = QPushButton(_("Schliessen"))
        btn_schliessen.clicked.connect(self.reject)
        btn_layout.addWidget(btn_schliessen)

        btn_hinzufuegen = QPushButton(_("Hinzufügen"))
        btn_hinzufuegen.clicked.connect(self.kategorie_hinzufuegen)
        btn_layout.addWidget(btn_hinzufuegen)

        layout.addLayout(btn_layout)

        self.lade_kategorien()

    def lade_kategorien(self):
        try:
            daten = get_einstellungen()
            self.kategorien = daten.get("buchhaltungs_kategorien", [])
        except Exception:
            self.kategorien = []
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
            QMessageBox.information(self, _("Hinweis"), _("Kategorie existiert bereits."))

    def kategorie_loeschen(self):
        ausgewählt = self.liste.currentItem()
        if ausgewählt:
            text = ausgewählt.text()
            self.kategorien.remove(text)
            self.aktualisiere_liste()
            self.speichern()
        else:
            QMessageBox.warning(self, _("Hinweis"), _("Bitte wählen Sie eine Kategorie aus."))

    def speichern(self):
        try:
            daten = get_einstellungen()
            daten["buchhaltungs_kategorien"] = self.kategorien
            set_einstellungen(daten)
        except Exception as e:
            QMessageBox.critical(self, _("Fehler"), _("Speichern fehlgeschlagen: {e}"))



