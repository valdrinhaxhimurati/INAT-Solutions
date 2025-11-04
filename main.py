import os
import sys
import json
import sqlite3
import shutil
import subprocess
import tempfile
import traceback
import logging
from db_connection import get_db, ensure_database_and_tables

from PyQt5.QtWidgets import QApplication, QMessageBox, QFileDialog, QDialog, QProgressDialog
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from gui.main_window import resource_path

app = QApplication(sys.argv)

# setze globales App-Icon, damit alle Fenster/Dialogs das Favicon erben
app.setWindowIcon(QIcon(resource_path("favicon.ico")))

import resources_rc
from gui.benutzer_dialog import BenutzerVerwaltenDialog
from login import init_login_db, LoginDialog
from migration import ensure_database
from paths import logs_dir, data_dir, users_db_path, local_db_path
from version import __version__

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.dirname(__file__)
    return os.path.join(base_path, relative_path)

CONFIG_PATH = str(data_dir() / "config.json")
LOGIN_DB_PATH = str(users_db_path())
DEFAULT_DB_PATH = str(local_db_path())

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
    # alte lokale Prüfung entfernen oder belassen als Fallback
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
    logpath = os.path.join(tempfile.gettempdir(), "inat_update.bat.log")
    dst_name = os.path.basename(dst).replace('"','')
    # robustes Batch: wartet, versucht mehrfach zu kopieren, loggt Fehler und öffnet Pause bei Fehler
    bat_contents = f'''@echo off
echo update started at %DATE% %TIME% > "{logpath}"
set "DST={dst}"
set "SRC={candidate}"
set "BACKUP=%DST%.old"
echo dst=%DST% >> "{logpath}"
echo src=%SRC% >> "{logpath}"
:WAIT_PROC
REM prüfe ob Prozess mit ImageName läuft
tasklist /FI "IMAGENAME eq {dst_name}" 2>> "{logpath}" | find /I "{dst_name}" >nul
if %ERRORLEVEL%==0 (
  timeout /t 1 >nul
  goto WAIT_PROC
)
echo process not running, attempting copy >> "{logpath}"

REM entferne altes Backup, versuche Copy mehrfach
if exist "%BACKUP%" del /F /Q "%BACKUP%" >> "{logpath}" 2>&1
set tries=0
:TRY_COPY
set /A tries+=1
echo try %tries% >> "{logpath}"
copy /Y "%SRC%" "%DST%" >> "{logpath}" 2>&1
if %ERRORLEVEL%==0 (
  echo copy succeeded >> "{logpath}"
  start "" "%DST%"
  del "%~f0"
  exit /B 0
) else (
  echo copy failed (exit %ERRORLEVEL%) >> "{logpath}"
  if %tries% GEQ 20 (
    echo giving up after %tries% attempts >> "{logpath}"
    echo Update failed. See "{logpath}"
    pause
    exit /B 1
  )
  timeout /t 1 >nul
  goto TRY_COPY
)
'''
    with open(bat_path, "w", encoding="utf-8") as bat:
        bat.write(bat_contents)

    # Start batch in neuer Konsole, dann beenden die App damit das Batch ersetzen kann
    subprocess.Popen(["cmd", "/k", bat_path], creationflags=subprocess.CREATE_NEW_CONSOLE)
    sys.exit(0)

def sync_from_remote():
    import urllib.request, json, hashlib, tempfile, os, shutil, subprocess, sys
    from packaging import version
    from PyQt5.QtWidgets import QMessageBox

    log = os.path.join(tempfile.gettempdir(), "inat_update_debug.log")
    def dbg(s):
        try:
            with open(log, "a", encoding="utf-8") as f:
                f.write(s + "\n")
        except Exception:
            pass

    dbg("sync_from_remote start")
    try:
        version_url = "https://valdrinhaxhimurati.github.io/INAT-Solutions-Updates/version.json"
        dbg(f"fetching {version_url}")
        with urllib.request.urlopen(version_url, timeout=10) as r:
            meta = json.load(r)
        dbg(f"meta: {meta!r}")

        # normalize version strings (strip leading 'v' or 'V')
        remote_ver_str = str(meta.get("version", "0")).lstrip("vV")
        current_ver_str = str(__version__).lstrip("vV")
        remote_ver = version.parse(remote_ver_str)
        current_ver = version.parse(current_ver_str)
        dbg(f"remote={remote_ver} current={current_ver}")

        if remote_ver <= current_ver:
            dbg("no update available")
            return

        ans = QMessageBox.question(None, "Update verfügbar",
            f"Neue Version {remote_ver} verfügbar (aktuell {current_ver}). Jetzt aktualisieren?",
            QMessageBox.Yes | QMessageBox.No)
        dbg(f"user_answer={ans}")
        if ans != QMessageBox.Yes:
            dbg("user declined")
            return

        url = meta.get("url")
        expected_sha = str(meta.get("sha256", "")).lower()
        if not url:
            dbg("no url in meta")
            QMessageBox.critical(None, "Update fehlgeschlagen", "Keine Download-URL in version.json")
            return

        tmp = tempfile.gettempdir()
        tmp_file = os.path.join(tmp, "INAT-Solutions-update.exe")
        dbg(f"downloading to {tmp_file}")
        urllib.request.urlretrieve(url, tmp_file)

        # checksum
        h = hashlib.sha256()
        with open(tmp_file, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        got = h.hexdigest().lower()
        dbg(f"got_sha={got} expected_sha={expected_sha}")
        if expected_sha and got != expected_sha:
            dbg("sha mismatch")
            QMessageBox.critical(None, "Integritätsfehler", "SHA256 stimmt nicht überein.")
            return

        dst = sys.executable
        backup = dst + ".old"
        try:
            shutil.copy2(dst, backup)
        except Exception:
            pass

        bat_path = os.path.join(tmp, "inat_update_remote.bat")
        with open(bat_path, "w", encoding="utf-8") as bat:
            bat.write(f"""@echo off
:WAIT
tasklist /FI "IMAGENAME eq {os.path.basename(dst)}" | find /I "{os.path.basename(dst)}" >nul
if %ERRORLEVEL%==0 (
  timeout /t 1 >nul
  goto WAIT
)
if exist "{backup}" del /F /Q "{backup}"
copy /Y "{tmp_file}" "{dst}"
start "" "{dst}"
del "%~f0"
""")
        subprocess.Popen(["cmd", "/c", bat_path], creationflags=subprocess.CREATE_NEW_CONSOLE)
        dbg("updater started")
        sys.exit(0)

    except Exception as e:
        dbg("exception: " + repr(e))
        try:
            QMessageBox.critical(None, "Update-Fehler", str(e))
        except Exception:
            pass

def apply_stylesheet(app, filename="style.qss"):
    import sys, os, re
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(__file__))

    # mögliche Orte für icons (einschließlich PyInstaller _internal)
    candidates = [
        os.path.join(base_path, "icons"),
        os.path.join(base_path, "_internal", "icons"),
    ]
    if getattr(sys, "frozen", False):
        candidates.append(os.path.join(os.path.dirname(sys.executable), "icons"))
    icons_dir = next((p for p in candidates if p and os.path.isdir(p)), None)

    qss_path = os.path.join(base_path, filename)
    if not os.path.exists(qss_path):
        return

    with open(qss_path, "r", encoding="utf-8") as f:
        qss = f.read()

    # Ersetze nur relative url(...) Einträge für icons/ (lässt :/ und file: unverändert)
    pattern = r'url\((["\']?)(?![:/]|file:)(?:icons/)?([^"\')]+)(["\']?)\)'
    def repl(m):
        icon_rel = m.group(2)
        if icons_dir:
            abs_path = os.path.join(icons_dir, icon_rel).replace("\\", "/")
        else:
            abs_path = os.path.join(base_path, "icons", icon_rel).replace("\\", "/")
        # zitierte Pfade, keine file:/// nötig wenn Pfad korrekt ist
        return f'url("{abs_path}")'

    qss_mod = re.sub(pattern, repl, qss)
    app.setStyleSheet(qss_mod)

def run():
    app = QApplication(sys.argv)

    # ensure compiled Qt resources are initialized (no harm if missing)
    try:
        import resources_rc  # optional, nur vorhanden wenn qrc kompiliert wurde
    except Exception:
        resources_rc = None

    # Stylesheet anwenden (sucht icons im Bundle/_internal/usw.)
    apply_stylesheet(app, "style.qss")

    import threading
    def _bg_run(fn, *a, **kw):
        try:
            fn(*a, **kw)
        except Exception as e:
            print(f"[BG] {fn.__name__} failed: {e}", flush=True)


    threading.Thread(target=_bg_run, args=(sync_from_remote,), daemon=True).start()

    try:
     pass   
    except Exception as e:
        QMessageBox.critical(None, "Abbruch", f"Datenbank/Schema Fehler: {e}")
        return 1

    # Login-DB initialisieren
    init_login_db(LOGIN_DB_PATH)

    from db_connection import get_db, ensure_database_and_tables  # ensure_database_and_tables will run in background
    import threading

    def ensure_minimal_login_schema():
        """Create only the minimal tables required for login quickly."""
        conn = None
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT DEFAULT 'user'
                )
            """)
            conn.commit()
        except Exception as e:
            print(f"[FAST-SCHEMA] ensure_minimal_login_schema failed: {e}", flush=True)
        finally:
            try:
                if conn:
                    cur.close()
                    conn.close()
            except Exception:
                pass

    # run minimal schema synchronously so login can proceed immediately
    ensure_minimal_login_schema()

    # Run the full schema/migrations in background (non-blocking).
    def _bg_full_schema():
        try:
            ensure_database_and_tables()
            print("[BG] ensure_database_and_tables finished", flush=True)
        except Exception as e:
            print(f"[BG] ensure_database_and_tables failed: {e}", flush=True)

    threading.Thread(target=_bg_full_schema, daemon=True).start()

    # Benutzer sicherstellen
    while not benutzer_existieren(LOGIN_DB_PATH):
        QMessageBox.information(None, "Benutzer anlegen", "Es sind noch keine Benutzer vorhanden. Bitte jetzt anlegen.")
        dlg = BenutzerVerwaltenDialog(LOGIN_DB_PATH)
        dlg.exec_()
        # Nach dem Dialog prüfe erneut, ob Benutzer existieren
        # Wenn ja, verlasse die Schleife; wenn nicht, zeige den Dialog erneut
        if benutzer_existieren(LOGIN_DB_PATH):
            break

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
        # ensure DB schema (inkl. invoices) existiert bevor UI geladen wird
      
  

        # Fenster öffnen
        mw = MainWindow(benutzername=user, login_db_path=LOGIN_DB_PATH)
        app._main_window = mw
        mw.showMaximized()  # Öffne das Fenster maximiert
        if splash:
            try:
                splash.finish(mw)
            except Exception:
                try: splash.close()
                except Exception: pass

    if splash is not None and hasattr(splash, "finished"):
        splash.finished.connect(open_main)
    else:
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(1200, open_main)

    app._splash = splash
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
            LOG_FILE = logs_dir() / "error.log"
            logging.basicConfig(filename=str(LOG_FILE), level=logging.INFO,
                                format="%(asctime)s %(levelname)s %(message)s", force=True)
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write("Fehler beim Start der Anwendung:\n\n")
                f.write(traceback.format_exc())
        except Exception:
            pass
        print(f"Ein Fehler ist aufgetreten. Details wurden in '{LOG_FILE}' gespeichert.")
        sys.exit(1)


