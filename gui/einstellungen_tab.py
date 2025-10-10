# -*- coding: utf-8 -*-
import os, json, csv, shutil
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFrame, QLabel,
    QLineEdit, QSizePolicy, QFileDialog, QScrollArea, QMessageBox, QInputDialog
)
from PyQt5.QtCore import Qt
from db_connection import get_db, dict_cursor_factory
from db_settings_dialog import DBSettingsDialog
from gui.kategorien_dialog import KategorienDialog
from gui.benutzer_dialog import BenutzerVerwaltenDialog
from gui.qr_daten_dialog import QRDatenDialog


class EinstellungenTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        main = QVBoxLayout()
        main.setContentsMargins(30, 30, 30, 30)
        main.setSpacing(18)

        # --- Firmeninformationen ---
        firma_box = QFrame()
        firma_box.setFrameShape(QFrame.StyledPanel)
        firma_box.setObjectName("settingsBox")
        firma_box.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        firma_layout = QVBoxLayout(firma_box)

        titel = QLabel("Firmeninformationen")
        titel.setObjectName("settingsTitle")
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
        self.speichern_button.clicked.connect(self.speichere_firmeninfo)
        firma_layout.addWidget(self.speichern_button)

        main.addWidget(firma_box)

        # --- Datenbank ---
        db_box = QFrame()
        db_box.setFrameShape(QFrame.StyledPanel)
        db_box.setObjectName("settingsBox")
        db_box.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        db_layout = QVBoxLayout(db_box)

        db_title = QLabel("Datenbank")
        db_title.setObjectName("settingsTitle")
        db_layout.addWidget(db_title)
        db_layout.addSpacing(8)

        db_layout.addWidget(QLabel("Aktuelle PostgreSQL-Verbindung:"))
        self.db_url_label = QLineEdit()
        self.db_url_label.setReadOnly(True)
        self.db_url_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        db_layout.addWidget(self.db_url_label)

        self.btn_db_settings = QPushButton("Datenbank-Einstellungen…")
        self.btn_db_settings.clicked.connect(self.open_db_settings)
        db_layout.addWidget(self.btn_db_settings)

        self.backup_button = QPushButton("Backup erstellen")
        self.backup_button.clicked.connect(self.backup_database)
        self.export_button = QPushButton("CSV Export")
        self.export_button.clicked.connect(self.csv_export_dialog)
        self.import_button = QPushButton("CSV Import")
        self.import_button.clicked.connect(self.csv_import_dialog)
        for b in (self.backup_button, self.export_button, self.import_button):
            db_layout.addWidget(b)

        main.addWidget(db_box)

        # --- Verwaltung ---
        verw_box = QFrame()
        verw_box.setFrameShape(QFrame.StyledPanel)
        verw_box.setObjectName("settingsBox")
        verw_box.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        verw_layout = QVBoxLayout(verw_box)

        verw_titel = QLabel("Verwaltung")
        verw_titel.setObjectName("settingsTitle")
        verw_layout.addWidget(verw_titel)
        verw_layout.addSpacing(8)

        self.kategorien_button = QPushButton("Kategorien verwalten")
        self.kategorien_button.clicked.connect(lambda: KategorienDialog(self).exec_())
        self.benutzer_button = QPushButton("Benutzer verwalten")
        self.benutzer_button.clicked.connect(lambda: BenutzerVerwaltenDialog(None).exec_())
        self.qr_button = QPushButton("QR-Rechnungsdaten verwalten")
        self.qr_button.clicked.connect(lambda: QRDatenDialog(self).exec_())

        for b in (self.kategorien_button, self.benutzer_button, self.qr_button):
            verw_layout.addWidget(b)

        main.addWidget(verw_box)
        main.addStretch(1)

        container = QWidget(); container.setLayout(main)
        scroll = QScrollArea(); scroll.setWidget(container); scroll.setWidgetResizable(True)
        outer = QVBoxLayout(); outer.addWidget(scroll)
        self.setLayout(outer)

        # Initial laden
        self.lade_config()
        self.refresh_db_label()

    # --------------------------------------------------
    # Config laden / speichern
    # --------------------------------------------------
    def cfg_path(self):
        return os.path.join(os.getcwd(), "config.json")

    def lade_config(self):
        p = self.cfg_path()
        if not os.path.exists(p): return
        with open(p, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        self.firmenname_input.setText(cfg.get("firmenname", ""))
        self.uid_input.setText(cfg.get("uid", ""))

    def speichere_firmeninfo(self):
        p = self.cfg_path()
        cfg = {}
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        cfg["firmenname"] = self.firmenname_input.text().strip()
        cfg["uid"] = self.uid_input.text().strip()
        with open(p, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4, ensure_ascii=False)
        QMessageBox.information(self, "Gespeichert", "Firmeninformationen gespeichert.")

    # --------------------------------------------------
    # Datenbank-Einstellungen
    # --------------------------------------------------
    def open_db_settings(self):
        dlg = DBSettingsDialog(self)
        if dlg.exec_():
            self.refresh_db_label()

    def refresh_db_label(self):
        p = self.cfg_path()
        if not os.path.exists(p):
            self.db_url_label.setText("(keine config.json gefunden)")
            return
        with open(p, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        url = cfg.get("postgres_url", "")
        self.db_url_label.setText(url or "(keine Verbindung eingestellt)")
        self.db_url_label.setCursorPosition(0)

    # --------------------------------------------------
    # Backup / CSV
    # --------------------------------------------------
    def backup_database(self):
        ziel, _ = QFileDialog.getSaveFileName(
            self, "Backup speichern unter", "backup.sql", "SQL-Dump Dateien (*.sql)"
        )
        if not ziel:
            return
        try:
            conn = get_db()
            with conn.cursor() as cur, open(ziel, "w", encoding="utf-8") as f:
                cur.copy_expert("COPY (SELECT table_name FROM information_schema.tables WHERE table_schema='public') TO STDOUT", f)
            QMessageBox.information(self, "Backup", f"Backup gespeichert unter {ziel}")
        except Exception as e:
            QMessageBox.critical(self, "Fehler", str(e))

    def csv_export_dialog(self):
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema='public' AND table_type='BASE TABLE'
                ORDER BY table_name
            """)
            tabellen = [r[0] for r in cur.fetchall()]
            conn.close()
        except Exception:
            tabellen = []
        if not tabellen:
            QMessageBox.warning(self, "Fehler", "Keine Tabellen gefunden!")
            return
        tabelle, ok = QInputDialog.getItem(self, "Tabelle wählen", "Welche Tabelle exportieren?", tabellen, 0, False)
        if not ok or not tabelle: return
        ziel, _ = QFileDialog.getSaveFileName(self, "CSV speichern unter", f"{tabelle}.csv", "CSV (*.csv)")
        if not ziel: return
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute(f'SELECT * FROM public."{tabelle}"')
            daten = cur.fetchall()
            spalten = [d[0] for d in cur.description]
            with open(ziel, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f); w.writerow(spalten); w.writerows(daten)
            conn.close()
            QMessageBox.information(self, "Export", f"Tabelle '{tabelle}' erfolgreich exportiert.")
        except Exception as e:
            QMessageBox.critical(self, "Fehler", str(e))

    def csv_import_dialog(self):
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema='public' AND table_type='BASE TABLE'
                ORDER BY table_name
            """)
            tabellen = [r[0] for r in cur.fetchall()]
            conn.close()
        except Exception:
            tabellen = []
        if not tabellen:
            QMessageBox.warning(self, "Fehler", "Keine Tabellen gefunden!")
            return
        tabelle, ok = QInputDialog.getItem(self, "Tabelle wählen", "In welche Tabelle importieren?", tabellen, 0, False)
        if not ok or not tabelle: return
        pfad, _ = QFileDialog.getOpenFileName(self, "CSV Datei auswählen", "", "CSV (*.csv)")
        if not pfad: return
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute(f'SELECT column_name FROM information_schema.columns WHERE table_name=%s', (tabelle,))
            spalten = [r[0] for r in cur.fetchall()]
            with open(pfad, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = [tuple(row.get(sp) for sp in spalten) for row in reader]
            if rows:
                placeholders = ",".join(["%s"] * len(spalten))
                cur.executemany(
                    f'INSERT INTO public."{tabelle}" ({",".join(spalten)}) VALUES ({placeholders})', rows)
                conn.commit()
                QMessageBox.information(self, "Import", f"{len(rows)} Zeilen importiert.")
            else:
                QMessageBox.warning(self, "Import", "Keine Daten in CSV gefunden.")
            conn.close()
        except Exception as e:
            QMessageBox.critical(self, "Fehler", str(e))
