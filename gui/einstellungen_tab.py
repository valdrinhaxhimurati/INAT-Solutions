# -*- coding: utf-8 -*-
import os, json, csv, importlib
import datetime
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
        self.module_button = QPushButton("Module verwalten")
        self.module_button.clicked.connect(self._open_module_dialog)

        # Export aller Rechnungen (Steuerauszug)
        self.export_invoices_button = QPushButton("Rechnungen exportieren")
        self.export_invoices_button.clicked.connect(self._export_invoices_dialog)
        
        for b in (self.kategorien_button, self.benutzer_button, self.qr_button, self.module_button):
            lay3.addWidget(b)

        # export button zuletzt in Verwaltung
        lay3.addWidget(self.export_invoices_button)
        
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

    def _open_module_dialog(self):
        try:
            from gui.lager_einstellungen_dialog import LagerEinstellungenDialog
        except Exception as e:
            QMessageBox.warning(self, "Module", f"Dialog nicht gefunden:\n{e}")
            return
        dlg = LagerEinstellungenDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            QMessageBox.information(self, "Module", "Einstellungen gespeichert.")
            # Lager-Tab aktualisieren
            try:
                # Versuche, MainWindow zu finden
                widget = self
                while widget and not hasattr(widget, 'lager_tab'):
                    widget = widget.parent()
                if widget and hasattr(widget, 'lager_tab'):
                    lager_tab = widget.lager_tab
                    if hasattr(lager_tab, 'tabs') and lager_tab.tabs:
                        lager_tab.tabs.clear()
                    lager_tab._load_aktive_lager()
            except Exception as e:
                print(f"Fehler beim Aktualisieren: {e}")

    def _export_invoices_dialog(self):
        """Exportiert alle Rechnungen (PDF) aus DB in einen Ordner.
           Benutzer wählt ein Jahr aus Dropdown mit tatsächlich vorhandenen Jahren.
        """
        # Ermittele vorhandene Jahre (zuerst aus buchhaltung.datum, sonst Fallback auf invoices.created_at)
        conn = None
        try:
            conn = get_db()
            cur = conn.cursor()
            years = []
            try:
                cur.execute("""
                    SELECT DISTINCT substr(COALESCE(buchhaltung.datum, ''), 1, 4) AS y
                    FROM invoices
                    LEFT JOIN buchhaltung ON invoices.buchung_id = buchhaltung.id
                    WHERE substr(COALESCE(buchhaltung.datum, ''), 1, 4) <> ''
                    ORDER BY y DESC
                """)
                years = [r[0] for r in cur.fetchall() if r[0]]
            except Exception:
                years = []

            # Fallback: falls keine Jahre in buchhaltung.datum gefunden, versuche invoices.created_at
            if not years:
                try:
                    # sqlite: strftime('%Y', created_at); Postgres: EXTRACT(YEAR FROM created_at)
                    try:
                        cur.execute("SELECT DISTINCT strftime('%Y', created_at) FROM invoices WHERE created_at IS NOT NULL ORDER BY 1 DESC")
                        years = [r[0] for r in cur.fetchall() if r[0]]
                    except Exception:
                        cur.execute("SELECT DISTINCT EXTRACT(YEAR FROM created_at)::text FROM invoices WHERE created_at IS NOT NULL ORDER BY 1 DESC")
                        years = [str(r[0]) for r in cur.fetchall() if r[0]]
                except Exception:
                    years = []
        finally:
            try:
                if conn:
                    conn.close()
            except Exception:
                pass

        if not years:
            QMessageBox.information(self, "Keine Rechnungen", "Es wurden keine Rechnungen mit Jahresangaben gefunden.")
            return

        # sortiere Jahre absteigend (aktuelles Jahr oben) und zeige ein Dropdown für das Jahr
        years = sorted(set(years), key=lambda x: int(x), reverse=True)
        label = (
            "Steuerauszug — Rechnungen exportieren\n\n"
            "Wähle ein Jahr: Es werden alle in der Buchhaltung hinterlegten Rechnungen\n"
            "für das gewählte Jahr exportiert. Die Dateinamen erhalten die Buchungsnummer\n"
            "als Präfix (z.B. 1234_rechnung.pdf).\n\n"
            "Jahr:"
        )
        year, ok = QInputDialog.getItem(self, "Rechnungen exportieren - Jahr wählen", label, years, 0, False)
        if not ok or not year:
            return

        folder = QFileDialog.getExistingDirectory(self, "Zielordner auswählen", os.path.expanduser("~"))
        if not folder:
            return

        # Query: hole Rechnungen für das ausgewählte Jahr (versuche Postgres-Variante, fallback auf SQLite)
        conn = None
        try:
            conn = get_db()
            cur = conn.cursor()
            # Postgres variant (uses EXTRACT for created_at)
            q_pg = """
                SELECT invoices.buchung_id, invoices.filename, invoices.content
                FROM invoices
                LEFT JOIN buchhaltung ON invoices.buchung_id = buchhaltung.id
                WHERE substr(COALESCE(buchhaltung.datum, ''),1,4) = %s
                   OR EXTRACT(YEAR FROM invoices.created_at)::text = %s
                ORDER BY invoices.buchung_id
            """
            try:
                cur.execute(q_pg, (year, year))
            except Exception:
                # SQLite variant (uses strftime)
                q_sqlite = """
                    SELECT invoices.buchung_id, invoices.filename, invoices.content
                    FROM invoices
                    LEFT JOIN buchhaltung ON invoices.buchung_id = buchhaltung.id
                    WHERE substr(COALESCE(buchhaltung.datum, ''),1,4) = ?
                       OR strftime('%Y', invoices.created_at) = ?
                    ORDER BY invoices.buchung_id
                """
                cur.execute(q_sqlite, (year, year))

            rows = cur.fetchall()
            count = 0
            for r in rows:
                bid = r[0] or 0
                fname = r[1] or "rechnung.pdf"
                data = r[2]
                if data is None:
                    continue
                outname = f"{bid}_{fname}"
                outpath = os.path.join(folder, outname)
                # falls Datei existiert, erweitere Zähler
                suffix = 1
                base, ext = os.path.splitext(outpath)
                while os.path.exists(outpath):
                    outpath = f"{base}_{suffix}{ext}"
                    suffix += 1
                with open(outpath, "wb") as fo:
                    fo.write(bytes(data))
                count += 1

            QMessageBox.information(self, "Export fertig", f"{count} Rechnungen exportiert nach:\n{folder}")
        except Exception as e:
            QMessageBox.critical(self, "Fehler beim Export", str(e))
        finally:
            try:
                if conn:
                    conn.close()
            except Exception:
                pass

