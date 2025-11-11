# -*- coding: utf-8 -*-
import os, json, csv, importlib
import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFrame, QLabel,
    QLineEdit, QSizePolicy, QFileDialog, QScrollArea, QMessageBox, QInputDialog, QDialog
)
from PyQt5.QtCore import Qt, QObject, pyqtSignal, QThread
from db_connection import get_db, get_remote_status, clear_business_database, get_config_value, set_config_value
from gui.clear_database_dialog import ClearDatabaseDialog
from gui.kategorien_dialog import KategorienDialog

from gui.rechnung_layout_dialog import RechnungLayoutDialog
from paths import data_dir
from gui.device_login_dialog import DeviceLoginDialog  # <-- NEUER IMPORT

def get_current_theme():
    try:
        from PyQt5 import QtGui
        app = QtGui.QGuiApplication.instance()
        if app:
            palette = app.palette()
            if palette:
                color = palette.color(palette.Window)
                if color:
                    r, g, b, _ = color.getRgb()
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

        # Arrange sections in a 2-column grid: top row (Firma | Datenbank), bottom full-width Buchhaltung
        from PyQt5.QtWidgets import QGridLayout

        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(16)

        # left-top: Firmeninformationen (box1)
        grid.addWidget(box1, 0, 0)

        # right-top: Datenbank (box2)
        box2 = QFrame(); box2.setFrameShape(QFrame.StyledPanel); box2.setObjectName("settingsBox")
        lay2 = QVBoxLayout(box2)
        title2 = QLabel("Datenbank"); title2.setObjectName("settingsTitle")
        lay2.addWidget(title2); lay2.addSpacing(8)
        # Modus-Anzeige (ohne URL)
        self.db_mode_label = QLabel("Modus:")  # wird in _refresh_db_label gesetzt
        lay2.addWidget(self.db_mode_label)
        self.btn_db_settings = QPushButton("Datenbank-Einstellungen…"); self.btn_db_settings.clicked.connect(self.open_db_settings)
        self.export_button = QPushButton("CSV Export"); self.export_button.clicked.connect(self.csv_export_dialog)
        self.import_button = QPushButton("CSV Import"); self.import_button.clicked.connect(self.csv_import_dialog)
        self.clear_db_button = QPushButton("Datenbank löschen"); self.clear_db_button.clicked.connect(self._on_clear_database)
        btn_col = QVBoxLayout(); btn_col.setSpacing(8)
        btn_col.addWidget(self.btn_db_settings, alignment=Qt.AlignLeft)
        btn_col.addWidget(self.export_button, alignment=Qt.AlignLeft)
        btn_col.addWidget(self.import_button, alignment=Qt.AlignLeft)
        btn_col.addWidget(self.clear_db_button, alignment=Qt.AlignLeft)
        lay2.addLayout(btn_col)
        # DB Sync launcher button
        self.btn_open_db_sync = QPushButton("Datenbank synchronisieren")
        self.btn_open_db_sync.clicked.connect(self._open_db_sync_dialog)
        btn_col.addWidget(self.btn_open_db_sync, alignment=Qt.AlignLeft)
        lay2.addSpacing(8)
        grid.addWidget(box2, 0, 1)

        # bottom: Buchhaltung | Rechnungen  (gleich hohe eingerahmte Boxen), darunter Lager + Allgemein
        # Buttons-Definitionen (ändert Reihenfolge/Zuordnung hier zentral)
        buch_buttons = [
            ("Kategorien verwalten", self._open_kategorien_dialog),
            ("Rechnungen exportieren", self._export_invoices_dialog),
        ]
        rech_buttons = [
            ("QR-Rechnungsdaten verwalten", self._open_qr_dialog),
            ("Rechnungslayout bearbeiten", self._open_rechnungslayout_dialog),
        ]
        allgemein_buttons = [
            ("Benutzer verwalten", self._open_benutzer_dialog),
            ("Mit Outlook verbinden", self._connect_outlook),
        ]
        lager_buttons = [
            ("Module verwalten", self._open_module_dialog),
        ]

        # Berechne Höhe so, dass die Boxen Buchhaltung/Rechnungen gleich groß sind
        max_rows = max(len(buch_buttons), len(rech_buttons), 1)
        approx_button_h = 34
        title_h = 36
        min_box_h = title_h + max_rows * (approx_button_h + 6) + 20

        # Buchhaltung-Box (links)
        box_buchhaltung = QFrame(); box_buchhaltung.setFrameShape(QFrame.StyledPanel); box_buchhaltung.setObjectName("settingsBox")
        box_buchhaltung.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        box_buchhaltung.setMinimumHeight(min_box_h)
        lay_buchhaltung = QVBoxLayout(box_buchhaltung)
        title_buch = QLabel("Buchhaltung"); title_buch.setObjectName("settingsTitle")
        lay_buchhaltung.addWidget(title_buch); lay_buchhaltung.addSpacing(8)
        # Buttons in einer Spalte
        for text, handler in buch_buttons:
            btn = QPushButton(text); btn.clicked.connect(handler)
            lay_buchhaltung.addWidget(btn)
        lay_buchhaltung.addStretch(1)
        grid.addWidget(box_buchhaltung, 1, 0)

        # Rechnungen-Box (rechts) - gleiche Höhe wie Buchhaltung
        box_rechnungen = QFrame(); box_rechnungen.setFrameShape(QFrame.StyledPanel); box_rechnungen.setObjectName("settingsBox")
        box_rechnungen.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        box_rechnungen.setMinimumHeight(min_box_h)
        lay_rechnungen = QVBoxLayout(box_rechnungen)
        title_rech = QLabel("Rechnungen"); title_rech.setObjectName("settingsTitle")
        lay_rechnungen.addWidget(title_rech); lay_rechnungen.addSpacing(8)
        for text, handler in rech_buttons:
            btn = QPushButton(text); btn.clicked.connect(handler)
            lay_rechnungen.addWidget(btn)
        lay_rechnungen.addStretch(1)
        grid.addWidget(box_rechnungen, 1, 1)

        # Lager (unterhalb, links)
        box_lager = QFrame(); box_lager.setFrameShape(QFrame.StyledPanel); box_lager.setObjectName("settingsBox")
        lay_lager = QVBoxLayout(box_lager)
        title_lager = QLabel("Lager"); title_lager.setObjectName("settingsTitle")
        lay_lager.addWidget(title_lager); lay_lager.addSpacing(8)
        for text, handler in lager_buttons:
            btn = QPushButton(text); btn.clicked.connect(handler)
            lay_lager.addWidget(btn)
        grid.addWidget(box_lager, 2, 0)

        # Allgemein (unterhalb, rechts) - Benutzerverwaltungen separat
        box_allgemein = QFrame(); box_allgemein.setFrameShape(QFrame.StyledPanel); box_allgemein.setObjectName("settingsBox")
        lay_allgemein = QVBoxLayout(box_allgemein)
        title_allg = QLabel("Allgemein"); title_allg.setObjectName("settingsTitle")
        lay_allgemein.addWidget(title_allg); lay_allgemein.addSpacing(8)
        for text, handler in allgemein_buttons:
            btn = QPushButton(text); btn.clicked.connect(handler)
            lay_allgemein.addWidget(btn)
        grid.addWidget(box_allgemein, 2, 1)

        # Spalten gleichmäßig dehnen
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        # Zeilenverteilung: damit die oberen Boxen gleiche Höhe bekommen
        grid.setRowStretch(0, 0)
        grid.setRowStretch(1, 0)
        grid.setRowStretch(2, 0)
        main.addLayout(grid)
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

    def _open_rechnungslayout_dialog(self):
        try:
            from gui.rechnung_layout_dialog import RechnungLayoutDialog
        except Exception as e:
            QMessageBox.warning(self, "Rechnungslayout", f"Dialog nicht gefunden:\n{e}")
            return
        dlg = RechnungLayoutDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            QMessageBox.information(self, "Rechnungslayout", "Layout gespeichert.")
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
            QMessageBox.warning(self, "Kategorien", f"Dialog nicht gefunden:\n{e}")
            return
        
        dialog = KategorienDialog(self)
        dialog.exec_() # Dialog wird ausgeführt und blockiert bis zur Schließung

        # NEU: Signal senden, nachdem der Dialog geschlossen wurde
        self.kategorien_geaendert.emit()

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

    def _open_db_sync_dialog(self):
        # öffnet den Dialog aus gui/db_sync_dialog.py
        from gui.db_sync_dialog import DBSyncDialog
        dlg = DBSyncDialog(self)
        dlg.exec_()

    def _connect_outlook(self):
        if ms_graph is None:
            QMessageBox.warning(self, "Outlook", "ms_graph Modul nicht gefunden.")
            return
        try:
            if ms_graph.is_connected():
                QMessageBox.information(self, "Outlook", "Bereits mit Outlook verbunden.")
                return
            
            flow = ms_graph.initiate_device_flow()
            
            # --- ALT ---
            # QMessageBox.information(self, "Outlook anmelden", flow.get("message", "Bitte Anweisungen im Browser folgen."))
            
            # --- NEU: Unseren benutzerdefinierten Dialog verwenden ---
            dialog = DeviceLoginDialog(flow, self)
            dialog.exec_() # Zeigt den Dialog an und wartet, bis der Benutzer OK klickt

            # Erstelle den Worker und den Thread, um das Warten auszulagern
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
            QMessageBox.critical(self, "Outlook", str(e))

    def _handle_login_result(self, result):
        """Wird aufgerufen, wenn der Worker fertig ist."""
        if "access_token" in result:
            QMessageBox.information(self, "Outlook", "Erfolgreich verbunden.")
        else:
            error_msg = result.get('error_description', 'Unbekannter Fehler bei der Anmeldung.')
            QMessageBox.warning(self, "Outlook", f"Anmeldung fehlgeschlagen:\n{error_msg}")
        
        # Thread aufräumen
        self.thread.quit()
        self.thread.wait()

    def _handle_login_error(self, error_message):
        """Wird aufgerufen, wenn im Worker ein Fehler auftritt."""
        QMessageBox.critical(self, "Outlook Fehler", error_message)
        
        # Thread aufräumen
        self.thread.quit()
        self.thread.wait()

