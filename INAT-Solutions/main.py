import os
import sys
import sqlite3
import traceback
import logging
from db_connection import get_db, ensure_database_and_tables

from PyQt5.QtWidgets import QApplication, QMessageBox, QFileDialog, QDialog
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from paths import resource_path
from updater import UpdateManager

app = QApplication(sys.argv)

# setze globales App-Icon, damit alle Fenster/Dialogs das Favicon erben
app.setWindowIcon(QIcon(resource_path("icons/logo.svg")))
from gui.benutzer_dialog import BenutzerVerwaltenDialog
from login import init_login_db, LoginDialog
from migration import ensure_database
from paths import logs_dir, data_dir, users_db_path, local_db_path, resource_path
from i18n import _
from version import __version__

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


def bootstrap_updater(window):
    try:
        updater = UpdateManager(current_version=__version__, parent=window)
        setattr(window, "_update_manager", updater)
        updater.check_for_updates()
    except Exception as exc:
        print(f"[UPDATE] Initialisierung fehlgeschlagen: {exc}", flush=True)

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

    try:
     pass   
    except Exception as e:
        QMessageBox.critical(None, _("Abbruch"), _("Datenbank/Schema Fehler:") + f" {e}")
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
        QMessageBox.information(None, _("Benutzer anlegen"), _("Es sind noch keine Benutzer vorhanden. Bitte jetzt anlegen."))
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

    # Lizenzprüfung nach erfolgreichem Login (DEAKTIVIERT - später aktivieren)
    # try:
    #     from gui.license_dialog import check_license_on_startup
    #     if not check_license_on_startup():
    #         return 0  # Benutzer hat beendet gewählt
    # except Exception as e:
    #     print(f"[LICENSE] Prüfung fehlgeschlagen: {e}", flush=True)

    # Auto-Backup erstellen (falls aktiviert)
    try:
        from gui.backup_dialog import create_auto_backup
        create_auto_backup()
    except Exception as e:
        print(f"[BACKUP] Auto-backup check failed: {e}", flush=True)

    from gui.main_window import MainWindow

    # Release Notes anzeigen wenn Update durchgeführt wurde
    try:
        from release_notes import show_release_notes_if_needed
        show_release_notes_if_needed()
    except Exception as e:
        print(f"[RELEASE-NOTES] Anzeige fehlgeschlagen: {e}", flush=True)

    # Splash anzeigen
    splash = None
    try:
        from logo_splash import LogoSplash
        # Korrigiere den Pfad, um das PNG-Logo für den Splash-Screen zu verwenden
        splash = LogoSplash(logo_path="INAT SOLUTIONS.png")
    except Exception:
        splash = None

    def open_main():
        nonlocal splash
        mw = MainWindow(benutzername=user, login_db_path=LOGIN_DB_PATH)
        
        # --- ÄNDERUNG: Explizit "normal" anzeigen, nicht maximiert ---
        mw.showNormal()

        bootstrap_updater(mw)
        
        app._main_window = mw
        if splash is not None:
            splash.close()
            splash = None
 
 
    if splash is not None and hasattr(splash, "finished"):
        splash.finished.connect(open_main)
        splash.show() # WICHTIG: Starte den Splash-Screen und die Animation
    else:
        # Fallback, falls der Splash-Screen nicht geladen werden kann
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(100, open_main)

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


