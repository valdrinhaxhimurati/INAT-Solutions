from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QDoubleSpinBox,
    QComboBox, QMessageBox, QFileDialog, QSlider, QFormLayout, QDateEdit
)
from db_connection import get_db, dict_cursor
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QPixmap
import os
import json
import sys 



from gui.select_inventory_item import SelectInventoryItemDialog



class RechnungLayoutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Rechnungslayout bearbeiten")
        self.setMinimumSize(800, 600)

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.dateipfad = "config/rechnung_layout.json"
        self.logo_pfad = ""
        self.logo_skala = 100  # default 100%

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

        # Slider für Logo-Größe (%)
        layout.addWidget(QLabel("Logo-Größe (%):"))
        h_slider = QHBoxLayout()
        self.logo_groesse_slider = QSlider(Qt.Horizontal)
        self.logo_groesse_slider.setRange(10, 200)
        self.logo_groesse_slider.setValue(self.logo_skala)
        self.logo_groesse_slider.setTickInterval(10)
        self.logo_groesse_slider.setTickPosition(QSlider.TicksBelow)
        self.logo_groesse_slider.setSingleStep(10)
        h_slider.addWidget(self.logo_groesse_slider)

        self.label_slider_wert = QLabel(f"{self.logo_skala}%")
        self.label_slider_wert.setFixedWidth(40)
        h_slider.addWidget(self.label_slider_wert)

        layout.addLayout(h_slider)

        self.logo_groesse_slider.valueChanged.connect(self.logo_groesse_aendern)

        # Buttons Speichern / Abbrechen
        btn_layout = QHBoxLayout()
        self.btn_speichern = QPushButton("Speichern")
        self.btn_abbrechen = QPushButton("Abbrechen")
        btn_layout.addWidget(self.btn_speichern)
        btn_layout.addWidget(self.btn_abbrechen)
        layout.addLayout(btn_layout)

        self.btn_speichern.clicked.connect(self.speichern)
        self.btn_abbrechen.clicked.connect(self.reject)

        self.lade_layout()

    
    def speichern(self):
        daten = {
            "kopfzeile": self.text_kopf.toPlainText(),
            "einleitung": self.text_einleitung.toPlainText(),
            "fusszeile": self.text_fuss.toPlainText(),
            "logo_pfad": self.logo_pfad if hasattr(self, "logo_pfad") else "",
            "logo_skala": self.logo_skala
        }
        os.makedirs(os.path.dirname(self.dateipfad), exist_ok=True)
        with open(self.dateipfad, "w", encoding="utf-8") as f:
            json.dump(daten, f, indent=2, ensure_ascii=False)
        QMessageBox.information(self, "Gespeichert", "Rechnungslayout wurde gespeichert.")
        self.accept()
        self.lade_layout()

    def lade_layout(self):
        if os.path.exists(self.dateipfad):
            with open(self.dateipfad, "r", encoding="utf-8") as f:
                daten = json.load(f)
            # Inhalte in UI-Elemente setzen
            self.text_kopf.setPlainText(daten.get("kopfzeile", ""))
            self.text_einleitung.setPlainText(daten.get("einleitung", ""))
            self.text_fuss.setPlainText(daten.get("fusszeile", ""))
            self.logo_pfad = daten.get("logo_pfad", "")
            self.logo_skala = daten.get("logo_skala", 100)
            self.logo_groesse_slider.setValue(self.logo_skala)

            if self.logo_pfad and os.path.exists(self.logo_pfad):
                self.zeige_logo()
            else:
                self.logo_vorschau.clear()
        else:
            # Datei existiert nicht — UI zurücksetzen
            self.text_kopf.clear()
            self.text_einleitung.clear()
            self.text_fuss.clear()
            self.logo_vorschau.clear()

    def logo_auswaehlen(self):
        dateipfad, _ = QFileDialog.getOpenFileName(self, "Logo auswählen", "", "Bilder (*.png *.jpg *.jpeg *.bmp)")
        if dateipfad:
            self.logo_pfad = dateipfad
            self.zeige_logo()
            
            
    def logo_groesse_aendern(self, wert):
        gerundet = round(wert / 10) * 10
        if gerundet < 10:
            gerundet = 10
        elif gerundet > 200:
            gerundet = 200
        
        if gerundet != self.logo_groesse_slider.value():
            self.logo_groesse_slider.blockSignals(True)
            self.logo_groesse_slider.setValue(gerundet)
            self.logo_groesse_slider.blockSignals(False)

        self.logo_skala = gerundet
        self.label_slider_wert.setText(f"{self.logo_skala}%")
        self.zeige_logo()
        
    def zeige_logo(self):
        if self.logo_pfad and os.path.exists(self.logo_pfad):
            pixmap = QPixmap(self.logo_pfad)
            faktor = self.logo_skala / 100
            neue_breite = int(pixmap.width() * faktor)
            neue_hoehe = int(pixmap.height() * faktor)

            max_breite = 150
            max_hoehe = 100

            if neue_breite > max_breite or neue_hoehe > max_hoehe:
                if neue_breite / max_breite > neue_hoehe / max_hoehe:
                    neue_hoehe = int(neue_hoehe * max_breite / neue_breite)
                    neue_breite = max_breite
                else:
                    neue_breite = int(neue_breite * max_hoehe / neue_hoehe)
                    neue_hoehe = max_hoehe

            skaliertes_pixmap = pixmap.scaled(neue_breite, neue_hoehe, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.logo_vorschau.setPixmap(skaliertes_pixmap)
        else:
            self.logo_vorschau.clear()


    def get_logo_skala(self):
        # Hier liest du den aktuellen Wert aus
        # Falls du einen Slider oder Eingabefeld hast, liest du den Wert hier aus
        return self.logo_skala

      

class RechnungDialog(QDialog):
    def __init__(self, kunden_liste, kunden_firmen, kunden_adressen, rechnung=None, mwst_voreinstellung=8.1, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Rechnung erstellen/bearbeiten")
        self.setMinimumSize(800, 600)

        self.kunden_liste = kunden_liste
        self.kunden_firmen = kunden_firmen
        self.kunden_adressen = kunden_adressen
        self.rechnung = rechnung
        self.mwst_voreinstellung = mwst_voreinstellung
        

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        form_top_layout = QFormLayout()
        self.layout.addLayout(form_top_layout)

        # Kunde Auswahl
        self.combo_kunde = QComboBox()
        self.combo_kunde.addItems(self.kunden_liste)
        form_top_layout.addRow(QLabel("Kunde:"), self.combo_kunde)

        # Rechnungsnummer
        self.input_nr = QLineEdit()
        form_top_layout.addRow(QLabel("Rechnungs-Nr:"), self.input_nr)

        # Datum mit QDateEdit im Schweizer Format
        self.input_datum = QDateEdit(QDate.currentDate())
        self.input_datum.setDisplayFormat("dd.MM.yyyy")
        self.input_datum.setCalendarPopup(True)
        form_top_layout.addRow(QLabel("Datum:"), self.input_datum)

        # Adresse (editierbar)
        self.text_adresse = QTextEdit()
        self.text_adresse.setFixedHeight(70)
        form_top_layout.addRow(QLabel("Adresse:"), self.text_adresse)

        self.combo_kunde.currentIndexChanged.connect(self.kunde_gewechselt)

        # Positionen Tabelle
        self.tabelle_pos = QTableWidget(0, 4)
        self.tabelle_pos.setHorizontalHeaderLabels(["Beschreibung", "Menge", "Einzelpreis (CHF)", "Total (CHF)"])
        self.tabelle_pos.setColumnWidth(0, 350)
        self.tabelle_pos.setColumnWidth(1, 80)
        self.tabelle_pos.setColumnWidth(2, 160)
        self.tabelle_pos.setColumnWidth(3, 100)
        self.layout.addWidget(self.tabelle_pos)

        # Buttons Positionen hinzufügen/entfernen
        h_pos_buttons = QHBoxLayout()
        self.btn_pos_hinzufuegen = QPushButton("Position hinzufügen")
        self.btn_pos_entfernen = QPushButton("Markierte Position entfernen")
        self.btn_pos_aus_lager = QPushButton("Aus Lager")
        h_pos_buttons.addWidget(self.btn_pos_hinzufuegen)
        h_pos_buttons.addWidget(self.btn_pos_entfernen)
        h_pos_buttons.addWidget(self.btn_pos_aus_lager)
        self.layout.addLayout(h_pos_buttons)

        self.btn_pos_hinzufuegen.clicked.connect(self.position_hinzufuegen)
        self.btn_pos_entfernen.clicked.connect(self.position_entfernen)
        self.btn_pos_aus_lager.clicked.connect(self.on_pos_aus_lager)
        
        
        # MwSt Auswahl
        h_mwst = QHBoxLayout()
        h_mwst.addWidget(QLabel("MwSt in %:"))
        self.input_mwst = QDoubleSpinBox()
        self.input_mwst.setRange(0, 100)
        self.input_mwst.setValue(self.mwst_voreinstellung)
        self.input_mwst.setSingleStep(0.1)
        h_mwst.addWidget(self.input_mwst)
        h_mwst.addStretch()
        self.layout.addLayout(h_mwst)

        # UID einstellen
        h_uid = QHBoxLayout()
        h_uid.addWidget(QLabel("UID-Nummer:"))
        self.input_uid = QLineEdit()
        h_uid.addWidget(self.input_uid)
        self.layout.addLayout(h_uid)

        # UID aus den Einstellungen laden (wenn noch keine Rechnung geladen wird)
        if not rechnung:
            self.input_uid.setText(self.lade_uid_aus_einstellungen())

        # Zahlungsbedingungen
        self.text_zahlungskonditionen = QTextEdit()
        self.text_zahlungskonditionen.setPlaceholderText("z.B. Zahlbar innert 30 Tagen ohne Abzug.")
        self.text_zahlungskonditionen.setFixedHeight(50)
        form_top_layout.addRow(QLabel("Zahlungskonditionen:"), self.text_zahlungskonditionen)

        # Abschiedsgruss
        self.text_abschluss = QTextEdit()
        self.text_abschluss.setPlaceholderText("z.B. Freundliche Grüße\nIhr Team")
        self.text_abschluss.setFixedHeight(75)
        form_top_layout.addRow(QLabel("Abschiedsgruss:"), self.text_abschluss)


        # Gesamtsumme
        h_gesamt = QHBoxLayout()
        self.label_gesamt = QLabel("Gesamt: CHF 0.00")
        font = self.label_gesamt.font()
        font.setBold(True)
        self.label_gesamt.setFont(font)
        h_gesamt.addStretch()
        h_gesamt.addWidget(self.label_gesamt)
        self.layout.addLayout(h_gesamt)

        # Buttons Speichern / Abbrechen / Layout bearbeiten
        h_buttons = QHBoxLayout()
        self.btn_speichern = QPushButton("Speichern")
        self.btn_abbrechen = QPushButton("Abbrechen")
        self.btn_layout_bearbeiten = QPushButton("Rechnungslayout bearbeiten")
        h_buttons.addWidget(self.btn_layout_bearbeiten)
        h_buttons.addStretch()
        h_buttons.addWidget(self.btn_speichern)
        h_buttons.addWidget(self.btn_abbrechen)
        self.layout.addLayout(h_buttons)

        self.btn_layout_bearbeiten.clicked.connect(self.rechnungslayout_dialog_oeffnen)
        self.btn_speichern.clicked.connect(self.speichern)
        self.btn_abbrechen.clicked.connect(self.reject)
        self.tabelle_pos.cellChanged.connect(self.position_geaendert)
        self.input_mwst.valueChanged.connect(self.berechne_gesamt)
        self.combo_kunde.currentIndexChanged.connect(self.kunde_gewechselt)

        # Initiale Daten laden
        self.position_hinzufuegen()
        if self.rechnung:
            self.lade_rechnung(self.rechnung)
        else:
            self.kunde_gewechselt(0)

    def lade_uid_aus_einstellungen(self):
        pfad = "config.json"
        if os.path.exists(pfad):
            try:
                with open(pfad, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    return config.get("uid", "")
            except Exception:
                pass
        return ""


    def kunde_gewechselt(self, index):
        kunde = self.combo_kunde.currentText()
        adresse = self.kunden_adressen.get(kunde, "")
        self.text_adresse.setPlainText(adresse)

    def position_hinzufuegen(self):
        if self.tabelle_pos.rowCount() >= 10:
            QMessageBox.warning(self, "Maximale Anzahl erreicht", "Es können maximal 10 Positionen hinzugefügt werden.")
            return
        zeile = self.tabelle_pos.rowCount()
        self.tabelle_pos.insertRow(zeile)
        # Anfangswerte setzen
        self.tabelle_pos.setItem(zeile, 0, QTableWidgetItem("Neue Position"))
        self.tabelle_pos.setItem(zeile, 1, QTableWidgetItem("1"))
        self.tabelle_pos.setItem(zeile, 2, QTableWidgetItem("0.00"))
        self.tabelle_pos.setItem(zeile, 3, QTableWidgetItem("0.00"))

    def position_entfernen(self):
        zeilen = sorted(set(item.row() for item in self.tabelle_pos.selectedItems()), reverse=True)
        for zeile in zeilen:
            self.tabelle_pos.removeRow(zeile)
        self.berechne_gesamt()

    def position_geaendert(self, row, column):
        if column in (1, 2):
            try:
                menge = float(self.tabelle_pos.item(row, 1).text())
            except Exception:
                menge = 0
            try:
                preis = float(self.tabelle_pos.item(row, 2).text())
            except Exception:
                preis = 0
            total = menge * preis
            self.tabelle_pos.blockSignals(True)
            self.tabelle_pos.setItem(row, 3, QTableWidgetItem(f"{total:.2f}"))
            self.tabelle_pos.blockSignals(False)
            self.berechne_gesamt()

    def berechne_gesamt(self):
        gesamt = 0.0
        for row in range(self.tabelle_pos.rowCount()):
            try:
                total = float(self.tabelle_pos.item(row, 3).text())
            except Exception:
                total = 0
            gesamt += total
        mwst = self.input_mwst.value()
        gesamt_mit_mwst = gesamt * (1 + mwst / 100)
        self.label_gesamt.setText(f"Gesamt: CHF {gesamt_mit_mwst:.2f}")

    def lade_rechnung(self, rechnung):
        self.input_nr.setText(rechnung.get("rechnung_nr", ""))
        datum_str = rechnung.get("datum", "")
        if datum_str:
            datum = QDate.fromString(datum_str, "dd.MM.yyyy")
            if datum.isValid():
                self.input_datum.setDate(datum)
        kunde = rechnung.get("kunde", "")
        index = self.combo_kunde.findText(kunde)
        if index >= 0:
            self.combo_kunde.setCurrentIndex(index)
        self.text_adresse.setPlainText(rechnung.get("adresse", ""))
        self.input_mwst.setValue(rechnung.get("mwst", self.mwst_voreinstellung))
        self.input_uid.setText(rechnung.get("uid", ""))
        self.text_zahlungskonditionen.setPlainText(rechnung.get("zahlungskonditionen", ""))
        self.text_abschluss.setPlainText(rechnung.get("abschluss", ""))


        self.tabelle_pos.setRowCount(0)
        for pos in rechnung.get("positionen", []):
            self.position_hinzufuegen()
            row = self.tabelle_pos.rowCount() - 1
            self.tabelle_pos.setItem(row, 0, QTableWidgetItem(pos.get("beschreibung", "")))
            self.tabelle_pos.setItem(row, 1, QTableWidgetItem(str(pos.get("menge", 1))))
            self.tabelle_pos.setItem(row, 2, QTableWidgetItem(f"{pos.get('einzelpreis', 0):.2f}"))
            total = pos.get("menge", 1) * pos.get("einzelpreis", 0)
            self.tabelle_pos.setItem(row, 3, QTableWidgetItem(f"{total:.2f}"))

        self.berechne_gesamt()

    def speichern(self):
        nummer = self.input_nr.text().strip()
        if not nummer:
            QMessageBox.warning(self, "Fehler", "Bitte geben Sie eine Rechnungsnummer ein.")
            return

        kunde = self.combo_kunde.currentText().strip()
        if not kunde:
            QMessageBox.warning(self, "Fehler", "Bitte wählen Sie einen Empfänger/Kunden aus.")
            return

        firma = self.kunden_firmen.get(kunde, "")

        rechnung = dict(self.rechnung) if self.rechnung else {}  # <<---- HIER!
        rechnung.update({
            "rechnung_nr": nummer,
            "datum": self.input_datum.date().toString("dd.MM.yyyy"),
            "kunde": kunde,
            "firma": firma,   
            "adresse": self.text_adresse.toPlainText(),
            "mwst": self.input_mwst.value(),
            "uid": self.input_uid.text().strip(),
            "zahlungskonditionen": self.text_zahlungskonditionen.toPlainText().strip(),
            "abschluss": self.text_abschluss.toPlainText().strip(),
            "positionen": []
        })

        for row in range(self.tabelle_pos.rowCount()):
            beschreibung = self.tabelle_pos.item(row, 0).text() if self.tabelle_pos.item(row, 0) else ""
            try:
                menge = float(self.tabelle_pos.item(row, 1).text())
            except Exception:
                menge = 0
            try:
                einzelpreis = float(self.tabelle_pos.item(row, 2).text())
            except Exception:
                einzelpreis = 0
            if beschreibung.strip():
                rechnung["positionen"].append({
                    "beschreibung": beschreibung,
                    "menge": menge,
                    "einzelpreis": einzelpreis
                })

        # Hier könntest du die Rechnung speichern oder weiterverarbeiten

        QMessageBox.information(self, "Gespeichert", "Rechnung wurde gespeichert.")
        self.accept()

   

    def rechnungslayout_dialog_oeffnen(self):
        dialog = RechnungLayoutDialog(self)
        dialog.exec_() 

    def on_pos_aus_lager(self):
        dlg = SelectInventoryItemDialog(self)
        ok, row = dlg.exec_and_get()
        if not ok or not row:
            return
        # Neue Tabellenzeile bauen:
        beschreibung = f"{row['artikelnummer']} – {row['bezeichnung']}"
        zeile = self.tabelle_pos.rowCount()
        self.tabelle_pos.insertRow(zeile)
        # Beschreibung
        self.tabelle_pos.setItem(zeile, 0, QTableWidgetItem(beschreibung))
        # Menge default 1
        self.tabelle_pos.setItem(zeile, 1, QTableWidgetItem("1"))
        # Preis leer (0.00), da im Lager kein Preis geführt wird
        self.tabelle_pos.setItem(zeile, 2, QTableWidgetItem("0.00"))
        # Total = Menge * Preis
        self.tabelle_pos.setItem(zeile, 3, QTableWidgetItem("0.00"))
        # falls du sofort recalculen willst:
        self.berechne_gesamt()



    def get_rechnung(self):
        nummer = self.input_nr.text().strip()
        if not nummer:
            return None  # Oder Fehlerbehandlung

        kunde = self.combo_kunde.currentText()
        firma = self.kunden_firmen.get(kunde, "")

        rechnung = dict(self.rechnung) if self.rechnung else {}  
        rechnung.update({
            "rechnung_nr": nummer,
            "datum": self.input_datum.date().toString("dd.MM.yyyy"),
            "kunde": kunde,
            "firma": firma,   
            "adresse": self.text_adresse.toPlainText(),
            "mwst": self.input_mwst.value(),
            "uid": self.input_uid.text().strip(),
            "zahlungskonditionen": self.text_zahlungskonditionen.toPlainText().strip(),
            "abschluss": self.text_abschluss.toPlainText().strip(),
            "positionen": []
        })
        for row in range(self.tabelle_pos.rowCount()):
            beschreibung = self.tabelle_pos.item(row, 0).text() if self.tabelle_pos.item(row, 0) else ""
            try:
                menge = float(self.tabelle_pos.item(row, 1).text())
            except Exception:
                menge = 0
            try:
                einzelpreis = float(self.tabelle_pos.item(row, 2).text())
            except Exception:
                einzelpreis = 0
            if beschreibung.strip():
                rechnung["positionen"].append({
                    "beschreibung": beschreibung,
                    "menge": menge,
                    "einzelpreis": einzelpreis
                })
        return rechnung
