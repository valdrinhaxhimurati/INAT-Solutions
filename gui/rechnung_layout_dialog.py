# datei: gui/rechnung_layout_dialog.py
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QTextEdit, QPushButton, QHBoxLayout, QMessageBox, QFileDialog
from PyQt5.QtGui import QPixmap
import json
import os
import sys
from db_connection import get_db, dict_cursor


class RechnungLayoutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Rechnungslayout bearbeiten")
        self.setMinimumSize(600, 500)

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.dateipfad = "config/rechnung_layout.json"
        self.logo_pfad = ""
        self.logo_skala = 100.0  # default 100%

        # Kopfzeile
        layout.addWidget(QLabel("Kopfzeile (z. B. Firmeninfo):"))
        self.text_kopf = QTextEdit()
        layout.addWidget(self.text_kopf) 

        # Einleitung
        layout.addWidget(QLabel("Einleitungstext:"))
        self.text_einleitung = QTextEdit()
        layout.addWidget(self.text_einleitung)

        # Fußzeile
        layout.addWidget(QLabel("Fußzeile:"))
        self.text_fuss = QTextEdit()
        layout.addWidget(self.text_fuss)

        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_speichern = QPushButton("Speichern")
        self.btn_abbrechen = QPushButton("Abbrechen")
        btn_layout.addWidget(self.btn_speichern)
        btn_layout.addWidget(self.btn_abbrechen)
        layout.addLayout(btn_layout)

        self.btn_speichern.clicked.connect(self.speichern)
        self.btn_abbrechen.clicked.connect(self.reject)

        # Logo
        layout.addWidget(QLabel("Logo (Pfad):"))
        h_logo = QHBoxLayout()
        self.logo_vorschau = QLabel()
        self.logo_vorschau.setFixedSize(150, 100)
        self.logo_vorschau.setStyleSheet("border: 1px solid #ccc;")
        self.logo_vorschau.setScaledContents(True)

        self.btn_logo_auswaehlen = QPushButton("Logo auswählen")
        self.btn_logo_auswaehlen.clicked.connect(self.logo_auswaehlen)

        h_logo.addWidget(self.logo_vorschau)
        h_logo.addWidget(self.btn_logo_auswaehlen)

        layout.addLayout(h_logo)

        self.lade_layout()

    def lade_layout(self):
        if os.path.exists(self.dateipfad):
            with open(self.dateipfad, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.text_kopf.setPlainText(data.get("kopfzeile", ""))
            self.text_einleitung.setPlainText(data.get("einleitung", ""))
            self.text_fuss.setPlainText(data.get("fusszeile", ""))
            self.logo_skala = data.get("logo_skala", 100)

            logo_pfad = data.get("logo_pfad", "")
            if logo_pfad:
                app_root = os.path.dirname(os.path.abspath(sys.argv[0]))
                abs_logo_pfad = os.path.join(app_root, logo_pfad)
                if os.path.exists(abs_logo_pfad):
                    self.logo_pfad = abs_logo_pfad
                    self.logo_vorschau.setPixmap(QPixmap(abs_logo_pfad))
                else:
                    self.logo_pfad = ""
                    self.logo_vorschau.clear()
            else:
                self.logo_pfad = ""
                self.logo_vorschau.clear()
        else:
            self.logo_pfad = ""
            self.logo_vorschau.clear()




    def speichern(self):
        app_root = os.path.dirname(os.path.abspath(sys.argv[0]))
        if self.logo_pfad:
            rel_logo_pfad = os.path.relpath(self.logo_pfad, app_root)
        else:
            rel_logo_pfad = ""

        daten = {
            "kopfzeile": self.text_kopf.toPlainText(),
            "einleitung": self.text_einleitung.toPlainText(),
            "fusszeile": self.text_fuss.toPlainText(),
            "logo_pfad": rel_logo_pfad,
            "logo_skala": self.logo_skala
        }
        os.makedirs(os.path.dirname(self.dateipfad), exist_ok=True)
        with open(self.dateipfad, "w", encoding="utf-8") as f:
            json.dump(daten, f, indent=2, ensure_ascii=False)
        QMessageBox.information(self, "Gespeichert", "Rechnungslayout wurde gespeichert.")
        self.accept()


    def logo_auswaehlen(self):
        dateipfad, _ = QFileDialog.getOpenFileName(self, "Logo auswählen", "", "Bilder (*.png *.jpg *.jpeg *.bmp)")
        if dateipfad:
            self.logo_pfad = dateipfad
            self.logo_vorschau.setPixmap(QPixmap(dateipfad))
