import os
import json
import csv
import shutil
import sqlite3

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QGroupBox, QFileDialog, QLabel, QLineEdit,
    QSizePolicy, QSpacerItem, QFrame, QScrollArea
)
from PyQt5.QtGui import QFont
from db_connection import get_db, dict_cursor
from db_settings_dialog import DBSettingsDialog
from gui.kategorien_dialog import KategorienDialog
from gui.benutzer_dialog import BenutzerVerwaltenDialog
from gui.qr_daten_dialog import QRDatenDialog


STANDARD_DB_PFAD = "db/datenbank.sqlite"

class EinstellungenTab(QWidget):
    def __init__(self, db_path, parent=None):
        try:
            from PyQt5.QtWidgets import QPushButton
            self.btn_db_settings = QPushButton('Datenbank einstellen …')
            self.btn_db_settings.clicked.connect(self.open_db_settings)
            try:
                self.layout().addWidget(self.btn_db_settings)
            except Exception:
                pass
        except Exception:
            pass
        super().__init__(parent)
        self.db_pfad = db_path

        # =========================
        # Inneres Layout (Content)
        # =========================
        main = QVBoxLayout()
        main.setContentsMargins(30, 30, 30, 30)
        main.setSpacing(18)

        # --- Firmeninfo Block ---
        firma_box = QFrame()
        firma_box.setFrameShape(QFrame.StyledPanel)
        firma_box.setObjectName("settingsBox")
        # CHANGED: Box soll sich vertikal nicht sinnlos dehnen
        firma_box.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)

        firma_layout = QVBoxLayout(firma_box)
        titel = QLabel("Firmeninformationen")
        titel.setObjectName("settingsTitle")
        # CHANGED: Titel nicht umbrechen, fixe Höhe
        titel.setWordWrap(False)
        titel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        firma_layout.addWidget(titel)
        firma_layout.addSpacing(8)

        self.firmenname_input = QLineEdit()
        self.firmenname_input.setPlaceholderText("Firmenname (z. B. DeineFirma AG)")
        self.uid_input = QLineEdit()
        self.uid_input.setPlaceholderText("UID-Nummer (z. B. CHE-123.456.789 MWST)")
        firma_layout.addWidget(QLabel("Name der Firma:"))
        firma_layout.addWidget(self.firmenname_input)
        firma_layout.addWidget(QLabel("UID-Nummer:"))
        firma_layout.addWidget(self.uid_input)

        self.speichern_button = QPushButton("Speichern")
        self.speichern_button.clicked.connect(self.speichere_firmenname)
        self.speichern_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        firma_layout.addWidget(self.speichern_button)

        main.addWidget(firma_box)

        # --- Datenbank Block ---
        db_box = QFrame()
        db_box.setFrameShape(QFrame.StyledPanel)
        db_box.setObjectName("settingsBox")
        # CHANGED: vertikal nicht ausdehnen
        db_box.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)

        db_layout = QVBoxLayout(db_box)
        db_title = QLabel("Datenbank")
        db_title.setObjectName("settingsTitle")
        # CHANGED: Titel nicht umbrechen
        db_title.setWordWrap(False)
        db_title.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        db_layout.addWidget(db_title)
        db_layout.addSpacing(8)

        # CHANGED: DB-Pfad als einzeilige, read-only Zeile (kein WordWrap)
        db_layout.addWidget(QLabel("Aktueller Datenbank-Pfad:"))
        self.db_pfad_label = QLineEdit()
        self.db_pfad_label.setReadOnly(True)
        self.db_pfad_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        db_layout.addWidget(self.db_pfad_label)

        self.db_pfad_button = QPushButton("Datenbank-Pfad ändern")
        self.db_pfad_button.clicked.connect(self.datenbank_pfad_waehlen)
        self.backup_button = QPushButton("Backup")
        self.backup_button.clicked.connect(self.backup_datenbank)
        self.export_csv_button = QPushButton("CSV Export")
        self.export_csv_button.clicked.connect(self.csv_export_dialog)
        self.import_csv_button = QPushButton("CSV Import")
        self.import_csv_button.clicked.connect(self.csv_import_dialog)

        for btn in [self.db_pfad_button, self.backup_button, self.export_csv_button, self.import_csv_button]:
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            db_layout.addWidget(btn)

        main.addWidget(db_box)

        # --- Verwaltung Block ---
        verw_box = QFrame()
        verw_box.setFrameShape(QFrame.StyledPanel)
        verw_box.setObjectName("settingsBox")
        # CHANGED: vertikal nicht ausdehnen
        verw_box.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)

        verw_layout = QVBoxLayout(verw_box)
        verw_titel = QLabel("Verwaltung")
        verw_titel.setObjectName("settingsTitle")
        # CHANGED: Titel nicht umbrechen
        verw_titel.setWordWrap(False)
        verw_titel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        verw_layout.addWidget(verw_titel)
        verw_layout.addSpacing(8)

        self.kategorien_button = QPushButton("Kategorien verwalten")
        self.kategorien_button.clicked.connect(self.kategorien_verwalten)
        self.btn_benutzer = QPushButton("Benutzer verwalten")
        self.btn_benutzer.clicked.connect(self.benutzer_verwalten)
        self.qr_daten_button = QPushButton("QR-Rechnungsdaten verwalten")
        self.qr_daten_button.clicked.connect(self.qr_daten_verwalten)

        for btn in [self.kategorien_button, self.btn_benutzer, self.qr_daten_button]:
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            verw_layout.addWidget(btn)

        main.addWidget(verw_box)

        # CHANGED: freier Platz geht nach unten
        main.addStretch(1)
        # optional, zur Sicherheit:
        main.setStretch(main.indexOf(firma_box), 0)
        main.setStretch(main.indexOf(db_box),   0)
        main.setStretch(main.indexOf(verw_box), 0)

        # =========================
        # Scrollbarer Außenrahmen
        # =========================
        container = QWidget()
        container.setLayout(main)

        scroll = QScrollArea()
        scroll.setWidget(container)
        scroll.setWidgetResizable(True)

        outer = QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        self.setLayout(outer)

        # Felder initialisieren
        self.db_pfad = self.lade_db_pfad()
        self.db_pfad_label.setText(self.db_pfad)
        self.db_pfad_label.setCursorPosition(0)  # Anfang anzeigen
        self.lade_firmenname()

    # === Aktionen ===

    def kategorien_verwalten(self):
        dialog = KategorienDialog(self)
        dialog.exec_()

    def benutzer_verwalten(self):
        dialog = BenutzerVerwaltenDialog(self.db_pfad)
        dialog.exec_()

    def datenbank_pfad_waehlen(self):
        ordner = QFileDialog.getExistingDirectory(
            self, "Datenbank-Ordner auswählen", ""
        )
        if ordner:
            datei = os.path.join(ordner, "datenbank.sqlite")
            self.db_pfad = datei
            # CHANGED: nur Pfad setzen (keine mehrzeilige Beschriftung)
            self.db_pfad_label.setText(self.db_pfad)
            self.db_pfad_label.setCursorPosition(0)
            self.speichere_db_pfad()

    def speichere_db_pfad(self):
        config = {}
        if os.path.exists("config.json"):
            try:
                with open("config.json", "r", encoding="utf-8") as f:
                    config = json.load(f)
            except (json.JSONDecodeError, IOError):
                config = {}

        rel_pfad = os.path.relpath(self.db_pfad, start=os.getcwd())
        pfad_fuer_config = rel_pfad.replace("\\", "/")
        config["db_pfad"] = pfad_fuer_config
        config["firmenname"] = self.firmenname_input.text().strip()

        with open("config.json", "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)

    def speichere_firmenname(self):
        config = {}
        if os.path.exists("config.json"):
            try:
                with open("config.json", "r", encoding="utf-8") as f:
                    config = json.load(f)
            except (json.JSONDecodeError, IOError):
                config = {}

        config["firmenname"] = self.firmenname_input.text().strip()
        config["uid"] = self.uid_input.text().strip()
        config["db_pfad"] = config.get("db_pfad", self.db_pfad)

        with open("config.json", "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)

        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.information(self, "Einstellungen", "Firmeninformationen gespeichert.")

    def lade_db_pfad(self):
        if os.path.exists("config.json"):
            try:
                with open("config.json", "r", encoding="utf-8") as f:
                    config = json.load(f)
                    return config.get("db_pfad", STANDARD_DB_PFAD)
            except (json.JSONDecodeError, IOError):
                return STANDARD_DB_PFAD
        return STANDARD_DB_PFAD

    def lade_firmenname(self):
        if os.path.exists("config.json"):
            try:
                with open("config.json", "r", encoding="utf-8") as f:
                    config = json.load(f)
                    self.firmenname_input.setText(config.get("firmenname", ""))
                    self.uid_input.setText(config.get("uid", ""))
            except (json.JSONDecodeError, IOError):
                pass

    def qr_daten_verwalten(self):
        dialog = QRDatenDialog(self)
        dialog.exec_()

    def backup_datenbank(self):
        ziel, _ = QFileDialog.getSaveFileName(self, "Backup speichern unter", "datenbank_backup.sqlite", "SQLite DB (*.sqlite)")
        if ziel:
            try:
                shutil.copy2(self.db_pfad, ziel)
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.information(self, "Backup", "Backup erfolgreich gespeichert.")
            except Exception as e:
                QMessageBox.critical(self, "Fehler", f"Backup fehlgeschlagen:\n{e}")

    def csv_export_dialog(self):
        import sqlite3
        tabellen = []
        try:
            conn = get_db()
            cursor = conn.cursor(cursor_factory=dict_cursor(conn))
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tabellen = [row[0] for row in cursor.fetchall()]
            conn.close()
        except Exception:
            pass
        from PyQt5.QtWidgets import QInputDialog
        if not tabellen:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Fehler", "Keine Tabellen gefunden!")
            return

        tabelle, ok = QInputDialog.getItem(self, "Tabelle wählen", "Welche Tabelle exportieren?", tabellen, 0, False)
        if ok and tabelle:
            ziel, _ = QFileDialog.getSaveFileName(self, "CSV-Datei speichern unter", f"{tabelle}.csv", "CSV-Dateien (*.csv)")
            if ziel:
                self.exportiere_tabelle_als_csv(tabelle, ziel)

    def exportiere_tabelle_als_csv(self, tabelle, ziel_pfad):
        try:
            conn = get_db()
            cursor = conn.cursor(cursor_factory=dict_cursor(conn))
            cursor.execute(f"SELECT * FROM {tabelle}")
            daten = cursor.fetchall()
            spalten = [desc[0] for desc in cursor.description]
            with open(ziel_pfad, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(spalten)
                writer.writerows(daten)
            conn.close()
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.information(self, "Export", f"Tabelle '{tabelle}' erfolgreich exportiert.")
        except Exception as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Fehler", f"Export fehlgeschlagen:\n{e}")

    def csv_import_dialog(self):
        # Zuerst Ziel-Tabelle auswählen
        try:
            conn = get_db()
            cursor = conn.cursor(cursor_factory=dict_cursor(conn))
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tabellen = [row[0] for row in cursor.fetchall()]
            conn.close()
        except Exception:
            tabellen = []
        from PyQt5.QtWidgets import QInputDialog, QFileDialog, QMessageBox

        if not tabellen:
            QMessageBox.warning(self, "Fehler", "Keine Tabellen gefunden!")
            return

        tabelle, ok = QInputDialog.getItem(self, "Tabelle wählen", "In welche Tabelle soll importiert werden?", tabellen, 0, False)
        if ok and tabelle:
            pfad, _ = QFileDialog.getOpenFileName(self, "CSV-Datei auswählen", "", "CSV-Dateien (*.csv)")
            if pfad:
                self.importiere_csv_in_tabelle(pfad, tabelle)

    def importiere_csv_in_tabelle(self, csv_pfad, tabelle):
        from PyQt5.QtWidgets import QMessageBox
        import csv
        try:
            # Lade Spaltennamen aus DB
            conn = get_db()
            cursor = conn.cursor(cursor_factory=dict_cursor(conn))
            cursor.execute(f"PRAGMA table_info({tabelle})")
            spalten = [row[1] for row in cursor.fetchall()]
            # Lese CSV
            with open(csv_pfad, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                zeilen = [tuple(row.get(sp) for sp in spalten) for row in reader]
            # Importiere Zeilen
            if zeilen:
                platzhalter = ",".join("?" * len(spalten))
                cursor.executemany(f"INSERT INTO {tabelle} ({','.join(spalten)}) VALUES ({platzhalter})", zeilen)
                conn.commit()
                QMessageBox.information(self, "Import", f"{len(zeilen)} Zeilen in '{tabelle}' importiert.")
            else:
                QMessageBox.warning(self, "Import", "Keine Daten in CSV gefunden.")
            conn.close()
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Import fehlgeschlagen:\n{e}")


# --- hinzugefügt: Dialog zum Umstellen der DB ---
def open_db_settings(self):
    from PyQt5.QtWidgets import QMessageBox, QDialog, QPushButton
    dlg = DBSettingsDialog(self)
    if dlg.exec_() == QDialog.Accepted:
        try:
            from db_connection import get_db
            c = get_db(); c.close()
            QMessageBox.information(self, "Datenbank", "Einstellungen gespeichert. Verbindung erfolgreich. Bitte Anwendung neu starten.")
        except Exception as e:
            QMessageBox.warning(self, "Hinweis", "Einstellungen gespeichert, aber Verbindung fehlgeschlagen: %s" % e)
