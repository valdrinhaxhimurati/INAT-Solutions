import os
import sys
import json
import sqlite3
import shutil
import subprocess
import tempfile
import traceback

from PyQt5.QtWidgets import QApplication, QMessageBox, QFileDialog, QDialog, QProgressDialog
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

import resources_rc
from gui.benutzer_dialog import BenutzerVerwaltenDialog
from login import init_login_db, LoginDialog
from migration import ensure_database
from paths import logs_dir, data_dir, users_db_path, local_db_path

CONFIG_PATH = str(data_dir() / "config.json")
LOGIN_DB_PATH = str(users_db_path())
DEFAULT_DB_PATH = str(local_db_path())

def lade_stylesheet(filename="style.qss") -> str:
    p = os.path.join(data_dir().parent, filename)
    try:
        with open(p, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""

def benutzer_existieren(db_path: str) -> bool:
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        # KEIN CREATE TABLE hier (sonst falsches Schema)!
        cur.execute("SELECT COUNT(*) FROM users")
        cnt = cur.fetchone()[0]
        conn.close()
        return cnt > 0
    except sqlite3.Error:
        return False

LOCAL_FOLDER = r"C:\Users\V.Haxhimurati\Documents\TEST\dist\INAT Solutions"
LOCAL_EXE = "INAT Solutions.exe"

def sync_from_local():
    progress = QProgressDialog("Suche nach Updates…", None, 0, 0)
    progress.resize(400, 120)
    progress.setWindowModality(Qt.ApplicationModal)
    progress.setWindowTitle("Update prüfen")
    ico = resource_path("favicon.ico")
    if os.path.exists(ico):
        progress.setWindowIcon(QIcon(ico))
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
        out = subprocess.check_output([candidate, "--version"], stderr=subprocess.DEVNULL, universal_newlines=True, timeout=3).strip()
        local_ver = version.parse(out)
    except Exception:
        progress.close()
        return

    if local_ver <= current_ver:
        progress.close()
        return

    progress.close()
    ans = QMessageBox.question(None, "Update verfügbar", f"Lokale Version {local_ver} > {current_ver}. Jetzt aktualisieren?", QMessageBox.Yes | QMessageBox.No)
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

def run():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    ss = lade_stylesheet("style.qss")
    if ss:
        app.setStyleSheet(ss)

    # Update-Check NACH Erzeugen der QApplication
    sync_from_local()

    # DB-Verbindung sicherstellen (Postgres falls konfiguriert, sonst automatisch SQLite)
    try:
        conn = get_db()
        conn.close()
    except Exception as e:
        QMessageBox.critical(None, "Abbruch", f"Datenbankverbindung fehlgeschlagen: {e}")
        return 1

    # Login-DB initialisieren
    init_login_db(LOGIN_DB_PATH)

    # Benutzer sicherstellen (dein Flow bleibt)
    while not benutzer_existieren(LOGIN_DB_PATH):
        QMessageBox.information(None, "Benutzer anlegen", "Es sind noch keine Benutzer vorhanden. Bitte jetzt anlegen.")
        dlg = BenutzerVerwaltenDialog(LOGIN_DB_PATH)
        if dlg.exec_() != QDialog.Accepted:
            return 0

    # Danach sofort Login-Dialog
    login = LoginDialog(LOGIN_DB_PATH)
    rc = login.exec_()
    if rc != QDialog.Accepted and not getattr(login, "login_ok", False):
        return 0

    user = getattr(login, "logged_in_user", "")

    from gui.main_window import MainWindow

    # Splash anzeigen
    splash = None
    try:
        from logo_splash import LogoSplash
        img = resource_path("INAT SOLUTIONS.png")
        if os.path.exists(img):
            splash = LogoSplash(img)
            splash.show()
    except Exception:
        splash = None

    def open_main():
        mw = MainWindow(benutzername=user, login_db_path=LOGIN_DB_PATH)
        app._main_window = mw  # Referenz halten
        mw.show()
        if splash:
            try:
                splash.finish(mw)  # schließt Splash, sobald MainWindow aktiv ist
            except Exception:
                try: splash.close()
                except Exception: pass

    # Öffne das MainWindow erst nach dem Splash
    if splash is not None and hasattr(splash, "finished"):
        splash.finished.connect(open_main)
    else:
        # Fallback: öffne nach kurzer Verzögerung (z. B. 1200 ms)
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(1200, open_main)

    app._splash = splash  # Referenz halten
    return app.exec_()

if __name__ == "__main__":
    try:
        if "--version" in sys.argv:
            print(__version__)
            sys.exit(0)
        code = run()
        sys.exit(code)
    except Exception:
        try:
            # Logging-Datei in einen beschreibbaren Ordner
            LOG_FILE = logs_dir() / "error.log"
            logging.basicConfig(filename=str(LOG_FILE), level=logging.INFO,
                                format="%(asctime)s %(levelname)s %(message)s")

            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write("Fehler beim Start der Anwendung:\n\n")
                f.write(traceback.format_exc())
        except Exception:
            pass
        print("Ein Fehler ist aufgetreten. Details wurden in 'error.log' gespeichert.")
        sys.exit(1)

