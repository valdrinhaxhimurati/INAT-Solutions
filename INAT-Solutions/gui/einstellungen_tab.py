# -*- coding: utf-8 -*-
import os, json, csv, importlib
import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFrame, QLabel,
    QLineEdit, QSizePolicy, QFileDialog, QScrollArea, QMessageBox, QDialog, QComboBox, QApplication
)
from PyQt5.QtCore import Qt, QObject, pyqtSignal, QThread
from PyQt5.QtGui import QIcon
from db_connection import get_db, get_remote_status, clear_business_database, get_config_value, set_config_value
from i18n import _
from gui.clear_database_dialog import ClearDatabaseDialog
from gui.kategorien_dialog import KategorienDialog
from gui.backup_dialog import BackupRestoreDialog, create_auto_backup

from gui.rechnung_layout_dialog import RechnungLayoutDialog
from paths import data_dir, resource_path
from gui.device_login_dialog import DeviceLoginDialog  # <-- NEUER IMPORT
from gui.themed_input_dialog import get_item as themed_get_item
from i18n import _, set_language, get_language
from settings_store import get_text, set_text

from gui.base_dialog import BaseDialog
from gui.dialog_styles import GROUPBOX_STYLE

def get_current_theme():
    try:
        from PyQt5 import QtGui
        app = QtGui.QGuiApplication.instance()
        if app:
            palette = app.palette()
            if palette:
                color = palette.color(palette.Window)
                if color:
                    r, g, b, _alpha = color.getRgb()
                    # Helligkeit berechnen (Durchschnitt von R, G, B)
                    brightness = (r + g + b) / 3
                    # Schwellenwert für den Wechsel zwischen hell und dunkel
                    threshold = 200
                    return "dark" if brightness < threshold else "light"
    except Exception:
        pass
    return "light"  # Fallback-Wert

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


try:
    import ms_graph
except Exception:
    ms_graph = None

class OutlookLoginWorker(QObject):
    """Worker, der den blockierenden Login-Prozess in einem Thread ausführt."""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, flow):
        super().__init__()
        self.flow = flow

    def run(self):
        try:
            # Diese blockierende Funktion wird jetzt im Hintergrund ausgeführt
            result = ms_graph.acquire_token_by_device_flow(self.flow)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

class EinstellungenTab(QWidget):
    # NEU: Signal definieren
    kategorien_geaendert = pyqtSignal()

    def __init__(self, parent=None, login_db_path=None):
        super().__init__(parent)
        self.login_db_path = login_db_path

        main = QVBoxLayout()
        main.setContentsMargins(30, 30, 30, 30)
        main.setSpacing(20)

        from PyQt5.QtWidgets import QGridLayout, QGroupBox

        # === NEUES LAYOUT ===
        # Oberer Bereich: Firmeninfo (volle Breite)
        group_firma = QGroupBox(_("Firmeninformationen"))
        group_firma.setStyleSheet(GROUPBOX_STYLE)
        lay_firma = QHBoxLayout(group_firma)
        lay_firma.setContentsMargins(15, 20, 15, 15)
        lay_firma.setSpacing(15)
        
        # Firmenname
        firma_col1 = QVBoxLayout()
        firma_col1.addWidget(QLabel(_("Name der Firma:")))
        self.firmenname_input = QLineEdit()
        self.firmenname_input.setPlaceholderText(_("Firmenname"))
        self.firmenname_input.setMinimumWidth(250)
        firma_col1.addWidget(self.firmenname_input)
        lay_firma.addLayout(firma_col1)
        
        # UID
        firma_col2 = QVBoxLayout()
        firma_col2.addWidget(QLabel(_("UID-Nummer:")))
        self.uid_input = QLineEdit()
        self.uid_input.setPlaceholderText(_("UID-Nummer"))
        self.uid_input.setMinimumWidth(200)
        firma_col2.addWidget(self.uid_input)
        lay_firma.addLayout(firma_col2)
        
        # Speichern-Button
        self.btn_save_org = QPushButton(_("Speichern"))
        self.btn_save_org.setMinimumWidth(120)
        self.btn_save_org.clicked.connect(self._save_org)
        lay_firma.addWidget(self.btn_save_org, alignment=Qt.AlignBottom)
        lay_firma.addStretch()
        
        main.addWidget(group_firma)

        # === Grid für die restlichen Bereiche (3 Spalten) ===
        grid = QGridLayout()
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(20)

        # --- Datenbank ---
        group_db = QGroupBox(_("Datenbank"))
        group_db.setStyleSheet(GROUPBOX_STYLE)
        lay_db = QVBoxLayout(group_db)
        lay_db.setContentsMargins(15, 20, 15, 15)
        lay_db.setSpacing(10)
        
        self.db_mode_label = QLabel(_("Modus:"))
        lay_db.addWidget(self.db_mode_label)
        
        self.btn_db_settings = QPushButton(_("Datenbank-Einstellungen…"))
        self.btn_db_settings.clicked.connect(self.open_db_settings)
        lay_db.addWidget(self.btn_db_settings)
        
        self.btn_open_db_sync = QPushButton(_("Datenbank synchronisieren"))
        self.btn_open_db_sync.clicked.connect(self._open_db_sync_dialog)
        lay_db.addWidget(self.btn_open_db_sync)
        
        self.backup_button = QPushButton(_("Backup & Wiederherstellung"))
        self.backup_button.clicked.connect(self._open_backup_dialog)
        lay_db.addWidget(self.backup_button)
        
        self.clear_db_button = QPushButton(_("Datenbank löschen"))
        self.clear_db_button.clicked.connect(self._on_clear_database)
        lay_db.addWidget(self.clear_db_button)
        
        lay_db.addStretch()
        grid.addWidget(group_db, 0, 0)

        # --- Import/Export ---
        group_io = QGroupBox(_("Import / Export"))
        group_io.setStyleSheet(GROUPBOX_STYLE)
        lay_io = QVBoxLayout(group_io)
        lay_io.setContentsMargins(15, 20, 15, 15)
        lay_io.setSpacing(10)
        
        self.export_button = QPushButton(_("CSV Export"))
        self.export_button.clicked.connect(self.csv_export_dialog)
        lay_io.addWidget(self.export_button)
        
        self.import_button = QPushButton(_("CSV Import"))
        self.import_button.clicked.connect(self.csv_import_dialog)
        lay_io.addWidget(self.import_button)
        
        btn_export_invoices = QPushButton(_("Rechnungen exportieren"))
        btn_export_invoices.clicked.connect(self._export_invoices_dialog)
        lay_io.addWidget(btn_export_invoices)
        
        lay_io.addStretch()
        grid.addWidget(group_io, 0, 1)

        # --- Rechnungen ---
        group_rech = QGroupBox(_("Rechnungen"))
        group_rech.setStyleSheet(GROUPBOX_STYLE)
        lay_rech = QVBoxLayout(group_rech)
        lay_rech.setContentsMargins(15, 20, 15, 15)
        lay_rech.setSpacing(10)
        
        btn_qr = QPushButton(_("QR-Rechnungsdaten verwalten"))
        btn_qr.clicked.connect(self._open_qr_dialog)
        lay_rech.addWidget(btn_qr)
        
        btn_layout = QPushButton(_("Rechnungslayout bearbeiten"))
        btn_layout.clicked.connect(self._open_rechnungslayout_dialog)
        lay_rech.addWidget(btn_layout)
        
        lay_rech.addStretch()
        grid.addWidget(group_rech, 0, 2)

        # --- Buchhaltung ---
        group_buch = QGroupBox(_("Buchhaltung"))
        group_buch.setStyleSheet(GROUPBOX_STYLE)
        lay_buch = QVBoxLayout(group_buch)
        lay_buch.setContentsMargins(15, 20, 15, 15)
        lay_buch.setSpacing(10)
        
        btn_kategorien = QPushButton(_("Kategorien verwalten"))
        btn_kategorien.clicked.connect(self._open_kategorien_dialog)
        lay_buch.addWidget(btn_kategorien)
        
        lay_buch.addStretch()
        grid.addWidget(group_buch, 1, 0)

        # --- Lager ---
        group_lager = QGroupBox(_("Lager"))
        group_lager.setStyleSheet(GROUPBOX_STYLE)
        lay_lager = QVBoxLayout(group_lager)
        lay_lager.setContentsMargins(15, 20, 15, 15)
        lay_lager.setSpacing(10)
        
        btn_module = QPushButton(_("Module verwalten"))
        btn_module.clicked.connect(self._open_module_dialog)
        lay_lager.addWidget(btn_module)
        
        lay_lager.addStretch()
        grid.addWidget(group_lager, 1, 1)

        # --- Allgemein ---
        group_allg = QGroupBox(_("Allgemein"))
        group_allg.setStyleSheet(GROUPBOX_STYLE)
        lay_allg = QVBoxLayout(group_allg)
        lay_allg.setContentsMargins(15, 20, 15, 15)
        lay_allg.setSpacing(10)
        
        btn_benutzer = QPushButton(_("Benutzer verwalten"))
        btn_benutzer.clicked.connect(self._open_benutzer_dialog)
        lay_allg.addWidget(btn_benutzer)
        
        # Lizenz-Button (DEAKTIVIERT - später aktivieren)
        # btn_lizenz = QPushButton(_("Lizenz verwalten"))
        # btn_lizenz.clicked.connect(self._open_license_dialog)
        # lay_allg.addWidget(btn_lizenz)
        
        btn_outlook = QPushButton(_("Mit Outlook verbinden"))
        btn_outlook.clicked.connect(self._connect_outlook)
        lay_allg.addWidget(btn_outlook)
        
        self.language_btn = QPushButton(_("Sprache ändern"))
        self.language_btn.clicked.connect(self._on_language_change_clicked)
        lay_allg.addWidget(self.language_btn)
        
        lay_allg.addStretch()
        grid.addWidget(group_allg, 1, 2)

        # Spalten gleichmäßig dehnen
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)
        
        main.addLayout(grid)
        main.addStretch(1)

        container = QWidget()
        container.setLayout(main)
        scroll = QScrollArea()
        scroll.setWidget(container)
        scroll.setWidgetResizable(True)
        outer = QVBoxLayout()
        outer.addWidget(scroll)
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
        self.firmenname_input.setText(get_text("firmenname") or "")
        self.uid_input.setText(get_text("uid") or "")
        # Sprache wird über den Button geändert, kein Laden nötig

    def _save_org(self):
        set_text("firmenname", self.firmenname_input.text().strip())
        set_text("uid", self.uid_input.text().strip())
        QMessageBox.information(self, _("Gespeichert"), _("Firmeninformationen gespeichert."))

    # --- DB-Settings ---
    def open_db_settings(self):
        try:
            from gui.db_settings_dialog import DBSettingsDialog
        except Exception as e:
            QMessageBox.warning(self, _("Datenbank-Einstellungen"), _("Dialog nicht gefunden:\n{e}").format(e=e))
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
        self.db_mode_label.setText(_("Modus: Remote") if is_remote else _("Modus: Lokal"))

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
            QMessageBox.warning(self, _("Fehler"), _("Keine Tabellen gefunden!"))
            return

        tabelle, ok = themed_get_item(self, _("Tabelle wählen"), _("Welche Tabelle exportieren?"), tabellen, 0, False)
        if not ok or not tabelle: return

        ziel, _filter = QFileDialog.getSaveFileName(self, "CSV speichern unter", f"{tabelle}.csv", "CSV (*.csv)")
        if not ziel: return

        try:
            conn = get_db(); cur = conn.cursor()
            cur.execute(f'SELECT * FROM public."{tabelle}"')
            daten = cur.fetchall()
            spalten = [d[0] for d in cur.description]
            with open(ziel, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f); w.writerow(spalten); w.writerows(daten)
            conn.close()
            QMessageBox.information(self, _("Export"), _("Tabelle '{tabelle}' erfolgreich exportiert.").format(tabelle=tabelle))
        except Exception as e:
            QMessageBox.critical(self, _("Fehler"), str(e))

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
            QMessageBox.warning(self, _("Fehler"), _("Keine Tabellen gefunden!"))
            return

        tabelle, ok = themed_get_item(self, _("Tabelle wählen"), _("In welche Tabelle importieren?"), tabellen, 0, False)
        if not ok or not tabelle: return

        pfad, _filter = QFileDialog.getOpenFileName(self, "CSV Datei auswählen", "", "CSV (*.csv)")
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
                QMessageBox.information(self, _("Import"), _("{count} Zeilen importiert.").format(count=len(rows)))
            else:
                QMessageBox.warning(self, _("Import"), _("Keine Daten in CSV gefunden."))
            conn.close()
        except Exception as e:
            QMessageBox.critical(self, _("Fehler"), str(e))

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
            QMessageBox.warning(self, _("QR-Daten"), _("QR-Daten-Dialog nicht gefunden:\n{e}").format(e=e))
            return
        QRDatenDialog(self).exec_()

    def _open_rechnungslayout_dialog(self):
        try:
            from gui.rechnung_layout_dialog import RechnungLayoutDialog
        except Exception as e:
            QMessageBox.warning(self, _("Rechnungslayout"), _("Dialog nicht gefunden:\n{e}").format(e=e))
            return
        dlg = RechnungLayoutDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            QMessageBox.information(self, _("Rechnungslayout"), _("Layout gespeichert."))
            # Versuche, das Rechnungen-Tab zu benachrichtigen (wenn vorhanden)
            try:
                widget = self
                while widget and not hasattr(widget, 'rechnungen_tab'):
                    widget = widget.parent()
                if widget and hasattr(widget, 'rechnungen_tab'):
                    rt = widget.rechnungen_tab
                    if hasattr(rt, '_lade_rechnungslayout'):
                        rt._lade_rechnungslayout()
            except Exception:
                pass

    def _open_kategorien_dialog(self):
        try:
            from gui.kategorien_dialog import KategorienDialog
        except Exception as e:
            QMessageBox.warning(self, _("Kategorien"), _("Dialog nicht gefunden:\n{e}").format(e=e))
            return
        
        dialog = KategorienDialog(self)
        dialog.exec_() # Dialog wird ausgeführt und blockiert bis zur Schließung

        # NEU: Signal senden, nachdem der Dialog geschlossen wurde
        self.kategorien_geaendert.emit()

    def _open_benutzer_dialog(self):
        from gui.benutzer_dialog import BenutzerVerwaltenDialog
        dlg = BenutzerVerwaltenDialog(self.login_db_path or USERS_DB_PATH, self)
        dlg.exec_()

    def _open_license_dialog(self):
        """Öffnet den Lizenz-Dialog."""
        from gui.license_dialog import LicenseDialog
        dlg = LicenseDialog(self)
        dlg.exec_()

    def _open_module_dialog(self):
        try:
            from gui.lager_einstellungen_dialog import LagerEinstellungenDialog
        except Exception as e:
            QMessageBox.warning(self, _("Module"), _("Dialog nicht gefunden:\n{e}").format(e=e))
            return
        dlg = LagerEinstellungenDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            QMessageBox.information(self, _("Module"), _("Einstellungen gespeichert."))
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
                print(_("Fehler beim Aktualisieren: {e}"))

    def _export_invoices_dialog(self):
        """Exportiert alle Rechnungen (PDF) aus DB in einen Ordner.
           Benutzer wählt ein Jahr aus Dropdown mit tatsächlich vorhandenen Jahren.
        """
        from PyQt5.QtWidgets import QGroupBox, QDialogButtonBox
        from gui.dialog_styles import GROUPBOX_STYLE

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
            QMessageBox.information(self, _("Keine Rechnungen"), _("Es wurden keine Rechnungen mit Jahresangaben gefunden."))
            return

        # sortiere Jahre absteigend (aktuelles Jahr oben)
        years = sorted(set(years), key=lambda x: int(x), reverse=True)

        # Erstelle schönen Dialog mit GroupBox
        dialog = BaseDialog(self)
        dialog.setWindowTitle(_("Rechnungen exportieren"))
        dialog.setFixedSize(580, 450)
        layout = dialog.content_layout
        layout.setSpacing(20)
        layout.setContentsMargins(28, 28, 28, 28)

        # Info GroupBox
        info_group = QGroupBox(_("Steuerauszug — Rechnungen exportieren"))
        info_group.setStyleSheet(GROUPBOX_STYLE)
        info_layout = QVBoxLayout(info_group)
        info_layout.setSpacing(8)
        info_layout.setContentsMargins(16, 24, 16, 16)

        info_label = QLabel(
            _("Es werden alle in der Buchhaltung hinterlegten Rechnungen "
              "für das gewählte Jahr exportiert. Die Dateinamen erhalten die "
              "Buchungsnummer als Präfix (z.B. 1234_rechnung.pdf).")
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666;")
        info_layout.addWidget(info_label)

        layout.addWidget(info_group)

        # Jahr-Auswahl GroupBox
        year_group = QGroupBox(_("Jahr auswählen"))
        year_group.setStyleSheet(GROUPBOX_STYLE)
        year_layout = QHBoxLayout(year_group)
        year_layout.setContentsMargins(16, 24, 16, 16)

        year_label = QLabel(_("Jahr:"))
        year_combo = QComboBox()
        year_combo.addItems(years)
        year_combo.setMinimumWidth(120)

        year_layout.addWidget(year_label)
        year_layout.addWidget(year_combo)
        year_layout.addStretch()

        layout.addWidget(year_group)
        layout.addStretch(1)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton(_("Abbrechen"))
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)
        
        export_btn = QPushButton(_("Exportieren"))
        export_btn.clicked.connect(dialog.accept)
        btn_layout.addWidget(export_btn)
        
        layout.addLayout(btn_layout)

        if dialog.exec_() != QDialog.Accepted:
            return

        year = year_combo.currentText()
        if not year:
            return

        folder = QFileDialog.getExistingDirectory(self, _("Zielordner auswählen"), os.path.expanduser("~"))
        if not folder:
            return
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

            QMessageBox.information(self, _("Export fertig"), _("{count} Rechnungen exportiert nach:\n{folder}").format(count=count, folder=folder))
        except Exception as e:
            QMessageBox.critical(self, _("Fehler beim Export"), str(e))
        finally:
            try:
                if conn:
                    conn.close()
            except Exception:
                pass

    def _open_db_sync_dialog(self):
        # öffnet den Dialog aus gui/db_sync_dialog.py
        from gui.db_sync_dialog import DBSyncDialog
        dlg = DBSyncDialog(self)
        dlg.exec_()

    def _open_backup_dialog(self):
        """Öffnet den Backup & Wiederherstellungs-Dialog."""
        dlg = BackupRestoreDialog(self)
        dlg.exec_()

    def _connect_outlook(self):
        if ms_graph is None:
            QMessageBox.warning(self, _("Outlook"), _("ms_graph Modul nicht gefunden."))
            return
        try:
            if ms_graph.is_connected():
                # --- KORREKTUR: Trennen-Option anbieten ---
                antwort = QMessageBox.question(self, _("Outlook-Verbindung"),
                                               _("Sie sind bereits mit einem Outlook-Konto verbunden.\n\nMöchten Sie die Verbindung trennen, um das Konto zu wechseln?"),
                                               QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if antwort == QMessageBox.Yes:
                    if ms_graph.disconnect():
                        QMessageBox.information(self, _("Outlook"), _("Verbindung wurde erfolgreich getrennt."))
                    else:
                        QMessageBox.warning(self, _("Outlook"), _("Trennen der Verbindung fehlgeschlagen."))
                return  # In jedem Fall hier beenden

            # Wenn nicht verbunden, den normalen Anmeldevorgang starten
            flow = ms_graph.initiate_device_flow()
            
            dialog = DeviceLoginDialog(flow, self)
            dialog.exec_()

            self.thread = QThread()
            self.worker = OutlookLoginWorker(flow)
            self.worker.moveToThread(self.thread)

            # Verbinde die Signale
            self.thread.started.connect(self.worker.run)
            self.worker.finished.connect(self._handle_login_result)
            self.worker.error.connect(self._handle_login_error)
            
            # Starte den Thread
            self.thread.start()

        except Exception as e:
            QMessageBox.critical(self, _("Outlook"), str(e))

    def _handle_login_result(self, result):
        """Wird aufgerufen, wenn der Worker fertig ist."""
        if "access_token" in result:
            QMessageBox.information(self, _("Outlook"), _("Erfolgreich verbunden."))
        else:
            error_msg = result.get('error_description', 'Unbekannter Fehler bei der Anmeldung.')
            QMessageBox.warning(self, _("Outlook"), _("Anmeldung fehlgeschlagen:\n{}").format(error_msg))
        
        # Thread aufräumen
        self.thread.quit()
        self.thread.wait()

    def _handle_login_error(self, error_message):
        """Wird aufgerufen, wenn im Worker ein Fehler auftritt."""
        QMessageBox.critical(self, _("Outlook Fehler"), error_message)
        
        # Thread aufräumen
        self.thread.quit()
        self.thread.wait()

    def _on_language_changed(self):
        lang = self.language_combo.currentData()
        set_language(lang)
        QMessageBox.information(self, _("Sprache geändert"), _("Die Sprache wurde geändert. Starten Sie die Anwendung neu, um die Änderungen zu übernehmen."))

    def _on_language_change_clicked(self):
        from PyQt5.QtWidgets import QButtonGroup, QRadioButton, QDialogButtonBox, QGroupBox
        from i18n import get_language, set_language
        from gui.dialog_styles import GROUPBOX_STYLE

        dialog = BaseDialog(self)
        dialog.setWindowTitle(_("Sprache ändern"))
        dialog.setFixedSize(580,360)
        layout = dialog.content_layout
        layout.setSpacing(20)
        layout.setContentsMargins(28, 28, 28, 28)

        # Aktuelle Sprache
        current_lang = get_language()

        # GroupBox für Sprachauswahl
        lang_group = QGroupBox(_("Sprache auswählen"))
        lang_group.setStyleSheet(GROUPBOX_STYLE)
        lang_layout = QVBoxLayout(lang_group)
        lang_layout.setSpacing(16)
        lang_layout.setContentsMargins(20, 28, 20, 20)

        # Button Group für Sprachen
        button_group = QButtonGroup(dialog)
        languages = [
            ("Deutsch", "de"),
            ("English", "en"),
            ("Français", "fr")
        ]

        for name, code in languages:
            rb = QRadioButton(name)
            rb.setMinimumHeight(32)
            if code == current_lang:
                rb.setChecked(True)
            button_group.addButton(rb, id=languages.index((name, code)))
            lang_layout.addWidget(rb)

        layout.addWidget(lang_group, 1)
        layout.addSpacing(16)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, dialog)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec_() == QDialog.Accepted:
            selected_id = button_group.checkedId()
            if selected_id >= 0:
                selected_lang = languages[selected_id][1]
                if selected_lang != current_lang:
                    set_language(selected_lang)
                    # Hinweis und Neustart
                    reply = QMessageBox.question(
                        self, _("Neustart erforderlich"),
                        _("Die Sprache wurde geändert. Anwendung jetzt neu starten?"),
                        QMessageBox.Yes | QMessageBox.No
                    )
                    if reply == QMessageBox.Yes:
                        self._restart_application()

    def _restart_application(self):
        import sys
        import os
        import subprocess
        # Neustart der Anwendung
        python = sys.executable
        main_dir = os.path.dirname(os.path.dirname(__file__))  # gui/ -> INAT-Solutions/
        main_script = os.path.join(main_dir, 'main.py')
        # Starte neue Instanz
        subprocess.Popen([python, main_script])
        # Beende aktuelle Anwendung
        QApplication.quit()

