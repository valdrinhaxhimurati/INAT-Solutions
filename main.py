import sys
from db_connection import get_db, dict_cursor_factory


# --- Erststart: DB-Verbindung sicherstellen ---
from PyQt5.QtWidgets import QDialog
try:
    from db_setup_dialog import DBSetupDialog
except Exception:
    DBSetupDialog = None
from db_connection import get_db

def ensure_db_on_first_start():
    try:
        conn = get_db()
        conn.close()
        return True
    except Exception:
        pass
    if DBSetupDialog is None:
        return False
    dlg = DBSetupDialog()
    if dlg.exec_() == QDialog.Accepted:
        conn = get_db()
        conn.close()
        return True
    return False


# Zuerst, bevor alles andere passiert:
if "--do-update" in sys.argv:
    # sys.argv = ["INAT Solutions.exe", "--do-update", src_path, dst_path, parent_pid]
    import time, os, shutil, subprocess

    _, _, src, dst, parent_pid = sys.argv
    parent_pid = int(parent_pid)

    # 1) Warten, bis der Parent (die alte App) wirklich beendet ist
    while True:
        try:
            # für Windows: prüfen, ob PID noch existiert
            os.kill(parent_pid, 0)
        except OSError:
            break
        time.sleep(0.5)

    # 2) Backup & Überschreiben
    try:
        shutil.copy2(dst, dst + ".old")   # Sicherung der alten EXE
    except:
        pass
    shutil.copy2(src, dst)

    # 3) Neue EXE starten
    subprocess.Popen([dst])
    sys.exit(0)

import sqlite3
import traceback
import json
import os
import resources_rc


from PyQt5.QtWidgets import QApplication, QFileDialog, QMessageBox, QDialog
from gui.main_window import MainWindow
from gui.benutzer_dialog import BenutzerVerwaltenDialog
from login import init_db as init_login_db, LoginDialog
#from migration import migration_ausfuehren
from gui.kunden_tab import KundenTab
from gui.rechnungen_tab import RechnungenTab
from logo_splash import LogoSplash 
import requests, tempfile, shutil, subprocess, sys
from version import __version__
from PyQt5.QtWidgets import QMessageBox
import requests
from packaging import version
from PyQt5.QtWidgets import QApplication, QMessageBox, QProgressDialog
from PyQt5.QtCore    import Qt
from PyQt5.QtGui import QIcon




LOCAL_FOLDER  = r"C:\Users\V.Haxhimurati\Documents\TEST\dist\INAT Solutions"
LOCAL_EXE    = "INAT Solutions.exe"


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

CONFIG_PATH = resource_path("config.json")
DEFAULT_DB_PATH = resource_path(os.path.join("db", "datenbank.sqlite"))
LOGIN_DB_PATH = resource_path(os.path.join("db", "users.db"))
main_window = None


def lade_stylesheet(dateipfad="style.qss"):
    pfad = resource_path(dateipfad)
    with open(pfad, "r", encoding="utf-8") as f:
        return f.read()

def config_laden():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    return {}

def config_speichern(config):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=4)

def frage_datenbank_pfad():
    info_box = QMessageBox()
    info_box.setWindowTitle("Datenbank speichern")
    info_box.setText(
        "Willkommen! Bitte wählen Sie im nächsten Dialog den Speicherort für die Datenbank-Datei aus.\n\n"
        "Falls Sie noch keine Datenbank haben, wird dort eine neue angelegt."
    )
    info_box.setIcon(QMessageBox.Information)
    info_box.exec_()

    datei, _ = QFileDialog.getSaveFileName(
        None,
        "Speicherort für Datenbank wählen",
        DEFAULT_DB_PATH,
        "SQLite Dateien (*.sqlite *.db)"
    )
    return datei if datei else None

def benutzer_existieren():
    try:
        conn = sqlite3.connect(LOGIN_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT)")
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0
    except sqlite3.Error as e:
        print(f"Fehler beim Prüfen der Benutzer: {e}")
        return False




def sync_from_local():
    # 0) Progress-Dialog anzeigen
    progress = QProgressDialog("Suche nach Updates…", None, 0, 0)
    progress.resize(400, 120)
    progress.setWindowModality(Qt.ApplicationModal)
    progress.setWindowTitle("Update prüfen")
    progress.setWindowIcon(QIcon(resource_path("favicon.ico")))
    progress.setCancelButton(None)
    progress.show()
    QApplication.processEvents()

    # 1) Ordner und Datei prüfen
    candidate = os.path.join(LOCAL_FOLDER, LOCAL_EXE)
    if not os.path.isfile(candidate):
        progress.close()
        return

    # 2) Versionsvergleich
    current_ver = version.parse(__version__)
    try:
        out = subprocess.check_output(
            [candidate, "--version"],
            stderr=subprocess.DEVNULL,
            universal_newlines=True,
            timeout=3
        ).strip()
        local_ver = version.parse(out)
    except Exception:
        progress.close()
        return

    if local_ver <= current_ver:
        progress.close()
        return

    # 3) Update-Dialog mit Favicon
    progress.close()
    dlg = QMessageBox(None)
    dlg.setWindowIcon(QIcon(resource_path("favicon.ico")))
    answer = dlg.question(
        None,
        "Update verfügbar",
        f"Deine lokale Version {local_ver} ist neuer als {current_ver}.\nJetzt aktualisieren?",
        QMessageBox.Yes | QMessageBox.No
    )
    if answer != QMessageBox.Yes:
        return

    # 4) Backup und Batch-Update-Skript erzeugen
    import tempfile

    dst         = sys.executable
    backup_path = dst + ".old"
    new_exe     = candidate

    try:
        shutil.copy2(dst, backup_path)
    except Exception:
        pass

    bat_path = os.path.join(tempfile.gettempdir(), "inat_update.bat")
    with open(bat_path, "w") as bat:
        bat.write(f"""@echo off
:WAIT
tasklist /FI "IMAGENAME eq {os.path.basename(dst)}" | find /I "{os.path.basename(dst)}" >nul
if %ERRORLEVEL%==0 (
    timeout /t 1 >nul
    goto WAIT
)
if exist "{backup_path}" del /F /Q "{backup_path}"
copy /Y "{new_exe}" "{dst}"
start "" "{dst}"
del "%~f0"
""")

    # 5) Batch-Skript starten und aktuelle App beenden
    subprocess.Popen(["cmd", "/c", bat_path], creationflags=subprocess.CREATE_NEW_CONSOLE)
    sys.exit(0)



if __name__ == "__main__":
    try:
         # GUI aufsetzen
        app = QApplication(sys.argv)
        with open("style.qss", "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())


        app.setStyle("Fusion")
        stylesheet = lade_stylesheet()
        app.setStyleSheet(stylesheet)
        
        
        # CLI-Flag für --version abfangen
        if "--version" in sys.argv:
            print(__version__)
            sys.exit(0)

        # Lokalen Update-Check durchführen
        sync_from_local()

                
        config = config_laden()

        # --- Datenbank sicherstellen (nur PostgreSQL) ---
        from db_connection import get_db
        from db_setup_dialog import DBSetupDialog

        try:
            conn = get_db()
            conn.close()
        except Exception:
            # Wenn keine Verbindung aufgebaut werden kann -> Setup-Dialog öffnen
            dlg = DBSetupDialog()
            if dlg.exec_() != QDialog.Accepted:
                QMessageBox.critical(None, "Abbruch", "Keine Datenbankverbindung konfiguriert.")
                sys.exit(1)


        init_login_db(LOGIN_DB_PATH)

        while not benutzer_existieren():
            hinweis = QMessageBox()
            hinweis.setWindowTitle("Benutzer anlegen")
            hinweis.setText("Es sind noch keine Benutzer vorhanden.\nBitte legen Sie nun einen Benutzer an.")
            hinweis.setIcon(QMessageBox.Information)
            hinweis.exec_()

            benutzer_dialog = BenutzerVerwaltenDialog(LOGIN_DB_PATH)
            result = benutzer_dialog.exec_()
            if result != QDialog.Accepted:
                print("Benutzererstellung abgebrochen. Programm wird beendet.")
                sys.exit()

            if not benutzer_existieren(LOGIN_DB_PATH):
                warnung = QMessageBox()
                warnung.setWindowTitle("Fehler")
                warnung.setText("Es wurde kein Benutzer angelegt.\nBitte versuchen Sie es erneut.")
                warnung.setIcon(QMessageBox.Warning)
                warnung.exec_()

        login_dialog = LoginDialog(LOGIN_DB_PATH)
        
        if login_dialog.exec_() and login_dialog.login_ok:
            angemeldeter_benutzer = login_dialog.logged_in_user

            #migration_ausfuehren(db_pfad)
            stylesheet = lade_stylesheet()
            app.setStyleSheet(stylesheet)

            # ========== SPLASH ========== #
            splash = LogoSplash(resource_path("INAT SOLUTIONS.png"))
            splash.show()

            def zeige_mainwindow():
                global main_window
                main_window = MainWindow(benutzername=angemeldeter_benutzer)
                main_window.show()
                # splash.close() – wird vom Splash selbst gemacht



            # Splash beendet → MainWindow zeigen
            splash.finished.connect(zeige_mainwindow)

            sys.exit(app.exec_())
        else:
            print("Login fehlgeschlagen oder abgebrochen.")
            sys.exit()



    except Exception as e:
        with open("error.log", "w", encoding="utf-8") as f:
            f.write("Fehler beim Start der Anwendung:\n\n")
            f.write(traceback.format_exc())
        print("Ein Fehler ist aufgetreten. Details wurden in 'error.log' gespeichert.")

