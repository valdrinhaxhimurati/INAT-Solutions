// ...existing code...
    # Start batch in neuer Konsole, dann beenden die App damit das Batch ersetzen kann
    subprocess.Popen(["cmd", "/k", bat_path], creationflags=subprocess.CREATE_NEW_CONSOLE)
    sys.exit(0)

def sync_from_remote():
    import urllib.request, json, hashlib, tempfile, os, shutil, subprocess, sys
    from packaging import version
    from PyQt5.QtWidgets import QMessageBox, QProgressDialog
    from PyQt5.QtCore import Qt

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
        # --- NEU: Dynamischen Dateinamen aus der version.json holen ---
        installer_filename = meta.get("filename", "INAT-Solutions-Setup.exe")

        if not url:
            dbg("no url in meta")
            QMessageBox.critical(None, "Update fehlgeschlagen", "Keine Download-URL in version.json")
            return

        tmp_dir = tempfile.gettempdir()
        installer_path = os.path.join(tmp_dir, installer_filename)
        dbg(f"downloading to {installer_path}")

        # --- NEU: Download mit Fortschrittsanzeige ---
        progress_dialog = QProgressDialog("Update wird heruntergeladen...", "Abbrechen", 0, 100)
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.show()
        
        response = urllib.request.urlopen(url)
        total_size = int(response.headers.get('content-length', 0))
        downloaded_size = 0
        
        with open(installer_path, 'wb') as f:
            while True:
                if progress_dialog.wasCanceled():
                    dbg("download canceled by user")
                    return
                chunk = response.read(8192)
                if not chunk:
                    break
                f.write(chunk)
                downloaded_size += len(chunk)
                if total_size > 0:
                    progress = (downloaded_size / total_size) * 100
                    progress_dialog.setValue(int(progress))
        
        progress_dialog.setValue(100)

        # Checksum
        h = hashlib.sha256()
        with open(installer_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        got = h.hexdigest().lower()
        dbg(f"got_sha={got} expected_sha={expected_sha}")
        if expected_sha and got != expected_sha:
            dbg("sha mismatch")
            QMessageBox.critical(None, "Integritätsfehler", "SHA256 stimmt nicht überein.")
            return

        # --- KORREKTUR: Installer starten und Anwendung beenden ---
        QMessageBox.information(None, "Download abgeschlossen", "Der Installer wird nun gestartet. Die Anwendung wird geschlossen.")
        
        # Starte den Installer als separaten Prozess
        subprocess.Popen([installer_path])
        
        # Schließe die aktuelle Anwendung
        dbg("starting installer and quitting application")
        QApplication.instance().quit()

    except Exception as e:
        dbg("exception: " + repr(e))
        try:
            QMessageBox.critical(None, "Update-Fehler", str(e))
        except Exception:
            pass

def apply_stylesheet(app, filename="style.qss"):
    import sys, os, re
// ...existing code...