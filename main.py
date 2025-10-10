import os
import sys
import json
import sqlite3
import shutil
import subprocess
import tempfile
import traceback

# PyQt
from PyQt5.QtWidgets import (
    QApplication, QMessageBox, QFileDialog, QDialog, QProgressDialog
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

# Projekt
import resources_rc  # Ressourcen aus resources_rc.py
from gui.main_window import MainWindow
from gui.benutzer_dialog import BenutzerVerwaltenDialog
from login import init_db as init_login_db, LoginDialog

# DB-Setup optional laden
try:
    from db_setup_dialog import DBSetupDialog
except Exception:
    DBSetupDialog = None

# DB-Verbindung
from db_connection import get_db

# Version sicher laden
try:
    from version import __version__
except Exception:
    __version__ = "0.0.0"


# ---------------------- Pfade & Helpers ----------------------
def app_base_dir() -> str:
    # Ordner der laufenden EXE oder des Skripts
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def resource_path(*parts) -> str:
    return os.path.join(app_base_dir(), *parts)

# Schreibbares Benutzerverzeichnis (AppData)
APPDATA_DIR = os.path.join(os.environ.get("APPDATA", app_base_dir()), "INAT Solutions")
os.makedirs(APPDATA_DIR, exist_ok=True)

# Konfig & Login-DB
CONFIG_PATH_DEFAULT = resource_path("config.json")
CONFIG_PATH = os.path.join(APPDATA_DIR, "config.json")
LOGIN_DB_PATH = os.path.join(APPDATA_DIR, "users.db")
DEFAULT_DB_PATH = os.path.join(APPDATA_DIR, "datenbank.sqlite")  # Fallback für lokale DB

def lade_stylesheet(filename="style.qss") -> str:
    qss = resource_path(filename)
    try:
        with open(qss, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""  # Stylesheet optional

def config_laden() -> dict:
    # Nutzer-Konfig bevorzugen, sonst Default
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    if os.path.exists(CONFIG_PATH_DEFAULT):
        try:
            with open(CONFIG_PATH_DEFAULT, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def config_speichern(cfg: dict) -> None:
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

def frage_datenbank_pfad() -> str:
    info = QMessageBox()
    info.setWindowTitle("Datenbank speichern")
    info.setText(
        "Willkommen! Bitte wählen Sie im nächsten Dialog den Speicherort für die Datenbank-Datei aus.\n\n"
        "Falls Sie noch keine Datenbank haben, wird dort eine neue angelegt."
    )
    info.setIcon(QMessageBox.Information)
    info.exec_()

    datei, _ = QFileDialog.getSaveFileName(
        None, "Speicherort für Datenbank wählen", DEFAULT_DB_PATH, "SQLite Dateien (*.sqlite *.db)"
    )
    return datei or ""

def benutzer_existieren(db_path: str) -> bool:
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT)")
        cur.execute("SELECT COUNT(*) FROM users")
        cnt = cur.fetchone()[0]
        conn.close()
        return cnt > 0
    except sqlite3.Error:
        return False


# ---------------------- Lokales Update (optional) ----------------------
LOCAL_FOLDER = r"C:\Users\V.Haxhimurati\Documents\TEST\dist\INAT Solutions"
LOCAL_EXE = "INAT Solutions.exe"

def sync_from_local():
    # Progress nur, wenn GUI läuft
    progress = QProgressDialog("Suche nach Updates…", None, 0, 0)
    progress.resize(400, 120)
    progress.setWindowModality(Qt.ApplicationModal)
    progress.setWindowTitle("Update prüfen")
    progress.setWindowIcon(QIcon(resource_path("favicon.ico")))
    progress.setCancelButton(None)
    progress.show()
    QApplication.processEvents()

    candidate = os.path.join(LOCAL_FOLDER, LOCAL_EXE)
    if not os.path.isfile(candidate):
        progress.close()
        return

    from packaging import version
    current_ver = version.parse(__version__)
    try:
        out = subprocess.check_output(
            [candidate, "--version"], stderr=subprocess.DEVNULL, universal_newlines=True, timeout=3
        ).strip()
        local_ver = version.parse(out)
    except Exception:
        progress.close()
        return

    if local_ver <= current_ver:
        progress.close()
        return

    progress.close()
    ans = QMessageBox.question(
        None,
        "Update verfügbar",
        f"Deine lokale Version {local_ver} ist neuer als {current_ver}.\nJetzt aktualisieren?",
        QMessageBox.Yes | QMessageBox.No,
    )
    if ans != QMessageBox.Yes:
        return

    dst = sys.executable
    backup = dst + ".old"
    try:
        shutil.copy2(dst, backup)
    except Exception:
        pass

    bat_path = os.path.join(tempfile.gettempdir(), "inat_update.bat")
    with open(bat_path, "w", encoding="utf-8") as bat:
        bat.write(f"""@echo off
:WAIT
tasklist /FI "IMAGENAME eq {os.path.basename(dst)}" | find /I "{os.path.basename(dst)}" >nul
if %ERRORLEVEL%==0 (
  timeout /t 1 >nul
  goto WAIT
)
if exist "{backup}" del /F /Q "{backup}"
copy /Y "{candidate}" "{dst}"
start "" "{dst}"
del "%~f0"
""")
    subprocess.Popen(["cmd", "/c", bat_path], creationflags=subprocess.CREATE_NEW_CONSOLE)
    sys.exit(0)


# ---------------------- Main ----------------------
if __name__ == "__main__":
    try:
        # --version für Updater/Checks
        if "--version" in sys.argv:
            print(__version__)
            sys.exit(0)

        app = QApplication(sys.argv)
        app.setStyle("Fusion")
        ss = lade_stylesheet("style.qss")
        if ss:
            app.setStyleSheet(ss)

        # Optionaler Update-Check
        sync_from_local()

        # DB-Verbindung sicherstellen (PostgreSQL/SQLite per get_db)
        try:
            conn = get_db()
            conn.close()
        except Exception:
            if DBSetupDialog is None:
                QMessageBox.critical(None, "Abbruch", "Keine Datenbankverbindung konfiguriert.")
                sys.exit(1)
            dlg = DBSetupDialog()
            if dlg.exec_() != QDialog.Accepted:
                QMessageBox.critical(None, "Abbruch", "Keine Datenbankverbindung konfiguriert.")
                sys.exit(1)

        # Login-DB initialisieren (lokal, schreibbar)
        init_login_db(LOGIN_DB_PATH)

        # Benutzer sicherstellen
        while not benutzer_existieren(LOGIN_DB_PATH):
            QMessageBox.information(
                None, "Benutzer anlegen", "Es sind noch keine Benutzer vorhanden.\nBitte legen Sie nun einen Benutzer an."
            )
            dlg = BenutzerVerwaltenDialog(LOGIN_DB_PATH)
            if dlg.exec_() != QDialog.Accepted:
                print("Benutzererstellung abgebrochen. Programm wird beendet.")
                sys.exit(0)
            if not benutzer_existieren(LOGIN_DB_PATH):
                QMessageBox.warning(None, "Fehler", "Es wurde kein Benutzer angelegt.\nBitte versuchen Sie es erneut.")

        # Login
        login_dialog = LoginDialog(LOGIN_DB_PATH)
        if login_dialog.exec_() and getattr(login_dialog, "login_ok", False):
            angemeldeter_benutzer = getattr(login_dialog, "logged_in_user", "")

            # Splash
            splash_png = resource_path("INAT SOLUTIONS.png")
            try:
                from logo_splash import LogoSplash
                splash = LogoSplash(splash_png)
                splash.show()

                def _show_main():
                    mw = MainWindow(benutzername=angemeldeter_benutzer)
                    mw.show()

                splash.finished.connect(_show_main)
            except Exception:
                # Fallback: direkt öffnen
                mw = MainWindow(benutzername=angemeldeter_benutzer)
                mw.show()

            sys.exit(app.exec_())
        else:
            print("Login fehlgeschlagen oder abgebrochen.")
            sys.exit(0)

    except Exception:
        try:
            with open(os.path.join(APPDATA_DIR, "error.log"), "w", encoding="utf-8") as f:
                f.write("Fehler beim Start der Anwendung:\n\n")
                f.write(traceback.format_exc())
        except Exception:
            pass
        print("Ein Fehler ist aufgetreten. Details wurden in 'error.log' gespeichert.")

