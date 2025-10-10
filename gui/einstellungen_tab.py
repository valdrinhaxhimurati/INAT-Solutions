# -*- coding: utf-8 -*-
import os, json, csv
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFrame, QLabel,
    QLineEdit, QSizePolicy, QFileDialog, QScrollArea, QMessageBox, QInputDialog
)
from PyQt5.QtCore import Qt
from db_connection import get_db
from db_settings_dialog import DBSettingsDialog
from gui.kategorien_dialog import KategorienDialog
from gui.benutzer_dialog import BenutzerVerwaltenDialog
from gui.qr_daten_dialog import QRDatenDialog


def _load_cfg_with_fallback(path):
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            with open(path, "r", encoding=enc) as f:
                cfg = json.load(f)
            if enc != "utf-8":
                with open(path, "w", encoding="utf-8") as fw:
                    json.dump(cfg, fw, indent=4, ensure_ascii=False)
            return cfg
        except UnicodeDecodeError:
            continue
        except Exception:
            break
    return {}


class EinstellungenTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        main = QVBoxLayout()
        main.setContentsMargins(30, 30, 30, 30)
        main.setSpacing(18)

        # --- Firmeninformationen ---
        box1 = QFrame(); box1.setFrameShape(QFrame.StyledPanel); box1.setObjectName("settingsBox")
        box1.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        lay1 = QVBoxLayout(box1)

        title1 = QLabel("Firmeninformationen"); title1.setObjectName("settingsTitle")
        lay1.addWidget(title1); lay1.addSpacing(8)

        self.firmenname_input = QLineEdit(); self.firmenname_input.setPlaceholderText("Firmenname")
        self.uid_input = QLineEdit(); self.uid_input.setPlaceholderText("UID-Nummer")
        lay1.addWidget(QLabel("Name der Firma:")); lay1.addWidget(self.firmenname_input)
        lay1.addWidget(QLabel("UID-Nummer:"));    lay1.addWidget(self.uid_input)

        self.btn_save_org = QPushButton("Speichern"); self.btn_save_org.clicked.connect(self._save_org)
        lay1.addWidget(self.btn_save_org)

        main.addWidget(box1)

        # --- Datenbank ---
        box2 = QFrame(); box2.setFrameShape(QFrame.StyledPanel); box2.setObjectName("settingsBox")
        lay2 = QVBoxLayout(box2)

        title2 = QLabel("Datenbank"); title2.setObjectName("settingsTitle")
        lay2.addWidget(title2); lay2.addSpacing(8)

        row = QHBoxLayout()
        row.addWidget(QLabel("Aktuelle PostgreSQL-Verbindung:"))
        self.db_url_label = QLineEdit(); self.db_url_label.setReadOnly(True); self.db_url_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        row.addWidget(self.db_url_label, 1)
        self.btn_db_settings = QPushButton("Datenbank-Einstellungen…"); self.btn_db_settings.clicked.connect(self.open_db_settings)
        row.addWidget(self.btn_db_settings)
        lay2.addLayout(row)

        # CSV / Backup (einfach)
        self.export_button = QPushButton("CSV Export"); self.export_button.clicked.connect(self.csv_export_dialog)
        self.import_button = QPushButton("CSV Import"); self.import_button.clicked.connect(self.csv_import_dialog)
        lay2.addWidget(self.export_button); lay2.addWidget(self.import_button)

        main.addWidget(box2)

        # --- Verwaltung ---
        box3 = QFrame(); box3.setFrameShape(QFrame.StyledPanel); box3.setObjectName("settingsBox")
        lay3 = QVBoxLayout(box3)
        title3 = QLabel("Verwaltung"); title3.setObjectName("settingsTitle")
        lay3.addWidget(title3); lay3.addSpacing(8)

        self.kategorien_button = QPushButton("Kategorien verwalten")
        self.kategorien_button.clicked.connect(lambda: KategorienDialog(self).exec_())
        self.benutzer_button = QPushButton("Benutzer verwalten")
        self.benutzer_button.clicked.connect(lambda: BenutzerVerwaltenDialog(self).exec_())
        self.qr_button = QPushButton("QR-Rechnungsdaten verwalten")
        self.qr_button.clicked.connect(lambda: QRDatenDialog(self).exec_())
        for b in (self.kategorien_button, self.benutzer_button, self.qr_button):
            lay3.addWidget(b)

        main.addWidget(box3)
        main.addStretch(1)

        container = QWidget(); container.setLayout(main)
        scroll = QScrollArea(); scroll.setWidget(container); scroll.setWidgetResizable(True)
        outer = QVBoxLayout(); outer.addWidget(scroll)
        self.setLayout(outer)

        # Init laden
        self._load_config()
        self._refresh_db_label()

    # --- Config ---
    def _cfg_path(self):
        return os.path.join(os.getcwd(), "config.json")

    def _load_config(self):
        p = self._cfg_path()
        if not os.path.exists(p):
            return
        cfg = _load_cfg_with_fallback(p)
        self.firmenname_input.setText(cfg.get("firmenname", ""))
        self.uid_input.setText(cfg.get("uid", ""))

    def _save_org(self):
        p = self._cfg_path()
        cfg = {}
        if os.path.exists(p):
            cfg = _load_cfg_with_fallback(p)
        cfg["firmenname"] = self.firmenname_input.text().strip()
        cfg["uid"] = self.uid_input.text().strip()
        with open(p, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4, ensure_ascii=False)
        QMessageBox.information(self, "Gespeichert", "Firmeninformationen gespeichert.")

    # --- DB-Settings ---
    def open_db_settings(self):
        dlg = DBSettingsDialog(self)
        if dlg.exec_():
            self._refresh_db_label()

    def _refresh_db_label(self):
        p = self._cfg_path()
        if not os.path.exists(p):
            self.db_url_label.setText("(keine config.json gefunden)"); return
        cfg = _load_cfg_with_fallback(p)
        url = cfg.get("postgres_url", "") or "(keine Verbindung eingestellt)"
        self.db_url_label.setText(url)
        self.db_url_label.setCursorPosition(0)

    # --- CSV ---
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
            conn = get_db(); cur = conn.cursor()
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
            conn = get_db(); cur = conn.cursor()
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
            conn = get_db(); cur = conn.cursor()
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name=%s ORDER BY ordinal_position", (tabelle,))
            spalten = [r[0] for r in cur.fetchall()]

            with open(pfad, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = [tuple(row.get(sp) for sp in spalten) for row in reader]

            if rows:
                placeholders = ",".join(["%s"] * len(spalten))
                cur.executemany(f'INSERT INTO public."{tabelle}" ({",".join(spalten)}) VALUES ({placeholders})', rows)
                conn.commit()
                QMessageBox.information(self, "Import", f"{len(rows)} Zeilen importiert.")
            else:
                QMessageBox.warning(self, "Import", "Keine Daten in CSV gefunden.")
            conn.close()
        except Exception as e:
            QMessageBox.critical(self, "Fehler", str(e))
