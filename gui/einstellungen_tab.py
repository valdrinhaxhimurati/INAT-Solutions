# -*- coding: utf-8 -*-
import os, json, csv, importlib
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFrame, QLabel,
    QLineEdit, QSizePolicy, QFileDialog, QScrollArea, QMessageBox, QInputDialog, QDialog
)
from PyQt5.QtCore import Qt
from db_connection import get_db, get_remote_status, clear_business_database, get_config_value, set_config_value
from gui.clear_database_dialog import ClearDatabaseDialog
from paths import data_dir

# Standardpfad für die Benutzer-DB (Dev: .var, Build: ProgramData)
USERS_DB_PATH = str(data_dir() / "users.db")


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
    def __init__(self, parent=None, login_db_path=None):
        super().__init__(parent)
        self.login_db_path = login_db_path

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

        # Modus-Anzeige (ohne URL)
        self.db_mode_label = QLabel("Modus:")  # wird in _refresh_db_label gesetzt
        lay2.addWidget(self.db_mode_label)

        # Buttons linksbündig untereinander
        self.btn_db_settings = QPushButton("Datenbank-Einstellungen…"); self.btn_db_settings.clicked.connect(self.open_db_settings)
        self.export_button = QPushButton("CSV Export"); self.export_button.clicked.connect(self.csv_export_dialog)
        self.import_button = QPushButton("CSV Import"); self.import_button.clicked.connect(self.csv_import_dialog)
        self.clear_db_button = QPushButton("Datenbank löschen"); self.clear_db_button.clicked.connect(self._on_clear_database)
        btn_col = QVBoxLayout()
        btn_col.setSpacing(8)
        btn_col.addWidget(self.btn_db_settings, alignment=Qt.AlignLeft)
        btn_col.addWidget(self.export_button, alignment=Qt.AlignLeft)
        btn_col.addWidget(self.import_button, alignment=Qt.AlignLeft)
        btn_col.addWidget(self.clear_db_button, alignment=Qt.AlignLeft)
        lay2.addLayout(btn_col)

        main.addWidget(box2)

        # --- Verwaltung ---
        box3 = QFrame(); box3.setFrameShape(QFrame.StyledPanel); box3.setObjectName("settingsBox")
        lay3 = QVBoxLayout(box3)
        title3 = QLabel("Verwaltung"); title3.setObjectName("settingsTitle")
        lay3.addWidget(title3); lay3.addSpacing(8)

        self.kategorien_button = QPushButton("Kategorien verwalten")
        self.kategorien_button.clicked.connect(self._open_kategorien_dialog)
        self.benutzer_button = QPushButton("Benutzer verwalten")
        self.benutzer_button.clicked.connect(self._open_benutzer_dialog)
        self.qr_button = QPushButton("QR-Rechnungsdaten verwalten")
        self.qr_button.clicked.connect(self._open_qr_dialog)
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
        # ALT: return os.path.join(os.getcwd(), "config.json")
        # NEU:
        return str(data_dir() / "config.json")

    def _load_config(self):
        self.firmenname_input.setText(get_config_value("firmenname") or "")
        self.uid_input.setText(get_config_value("uid") or "")

    def _save_org(self):
        set_config_value("firmenname", self.firmenname_input.text().strip())
        set_config_value("uid", self.uid_input.text().strip())
        QMessageBox.information(self, "Gespeichert", "Firmeninformationen gespeichert.")

    # --- DB-Settings ---
    def open_db_settings(self):
        try:
            from gui.db_settings_dialog import DBSettingsDialog
        except Exception as e:
            QMessageBox.warning(self, "Datenbank-Einstellungen", f"Dialog nicht gefunden:\n{e}")
            return
        dlg = DBSettingsDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            # Anzeige aktualisieren (Modus Lokal/Remote)
            self._refresh_db_label()

    def _refresh_db_label(self):
        # Status aus der DB-Konfiguration lesen (ohne URL anzuzeigen)
        is_remote = False
        try:
            status = get_remote_status()
            is_remote = bool(status.get("use_remote", False))
        except Exception:
            # Fallback auf config.json
            p = self._cfg_path()
            cfg = _load_cfg_with_fallback(p) if os.path.exists(p) else {}
            is_remote = bool(cfg.get("use_remote")) or bool(cfg.get("db_url") or cfg.get("postgres_url"))
        self.db_mode_label.setText("Modus: Remote" if is_remote else "Modus: Lokal")

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

    def _login_db_path(self) -> str:
        # Verwende den vom Login mitgegebenen Pfad, sonst Standardpfad
        if self.login_db_path:
            return self.login_db_path
        return USERS_DB_PATH

    def _on_clear_database(self):
        dlg = ClearDatabaseDialog(self)
        dlg.exec_()

    def _open_qr_dialog(self):
        try:
            from gui.qr_daten_dialog import QRDatenDialog  # passe den Pfad an, falls abweichend
        except Exception as e:
            QMessageBox.warning(self, "QR-Daten", f"QR-Daten-Dialog nicht gefunden:\n{e}")
            return
        QRDatenDialog(self).exec_()

    def _open_kategorien_dialog(self):
        try:
            from gui.kategorien_dialog import KategorienDialog
        except Exception as e:
            QMessageBox.warning(self, "Kategorien", f"Dialog nicht gefunden:\n{e}")
            return
        KategorienDialog(self).exec_()

    def _open_benutzer_dialog(self):
        from gui.benutzer_dialog import BenutzerVerwaltenDialog
        dlg = BenutzerVerwaltenDialog(self.login_db_path or USERS_DB_PATH, self)
        dlg.exec_()

