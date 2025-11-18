from __future__ import annotations

import hashlib
import json
import os
import random
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from packaging import version
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QApplication, QMessageBox

from gui.progress_dialog import ThemedProgressDialog
from paths import updates_dir

DEFAULT_MANIFEST_URL = "https://valdrinhaxhimurati.github.io/INAT-Solutions-Updates/update_manifest.json"
DEFAULT_USER_AGENT = "INAT-Solutions-Updater"
DOWNLOAD_CHUNK_SIZE = 128 * 1024
SILENT_INSTALL_ARGS = ("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART")


@dataclass
class UpdateManifest:
    version: str
    installer_url: str
    installer_filename: str
    sha256: str
    notes_url: str | None = None
    release_notes: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "UpdateManifest":
        installer = data.get("installer") or {}
        return cls(
            version=str(data.get("version", "0")),
            installer_url=str(installer.get("url", "")).strip(),
            installer_filename=str(installer.get("filename", "INAT-Solutions-Setup.exe")),
            sha256=str(installer.get("sha256", "")).strip(),
            notes_url=data.get("notes_url"),
            release_notes=data.get("release_notes"),
        )


class UpdateCheckWorker(QObject):
    finished = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, manifest_url: str):
        super().__init__()
        self._manifest_url = manifest_url

    @pyqtSlot()
    def run(self) -> None:
        try:
            sep = "&" if "?" in self._manifest_url else "?"
            cache_buster = f"{sep}cb={random.randint(1000, 9999)}"
            url = f"{self._manifest_url}{cache_buster}"
            req = urllib.request.Request(url, headers={"User-Agent": DEFAULT_USER_AGENT})
            with urllib.request.urlopen(req, timeout=12) as resp:
                payload = resp.read()
            manifest = json.loads(payload.decode("utf-8"))
            self.finished.emit(manifest)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class DownloadWorker(QObject):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, url: str, target_path: Path):
        super().__init__()
        self._url = url
        self._target_path = str(target_path)
        self._should_cancel = False

    @pyqtSlot()
    def run(self) -> None:
        try:
            req = urllib.request.Request(self._url, headers={"User-Agent": DEFAULT_USER_AGENT})
            with urllib.request.urlopen(req, timeout=20) as resp:
                total_size = int(resp.headers.get("Content-Length", "0"))
                downloaded = 0
                with open(self._target_path, "wb") as fh:
                    while True:
                        if self._should_cancel:
                            raise RuntimeError("Download durch Benutzer abgebrochen")
                        chunk = resp.read(DOWNLOAD_CHUNK_SIZE)
                        if not chunk:
                            break
                        fh.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            pct = max(0, min(100, int(downloaded * 100 / total_size)))
                            self.progress.emit(pct)
                self.finish_progress()
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))
            try:
                os.remove(self._target_path)
            except OSError:
                pass
        else:
            self.finished.emit(self._target_path)

    @pyqtSlot()
    def cancel(self) -> None:
        self._should_cancel = True

    def finish_progress(self) -> None:
        self.progress.emit(100)


class ChecksumWorker(QObject):
    finished = pyqtSignal()
    failed = pyqtSignal(str)

    def __init__(self, file_path: Path, expected_sha256: str):
        super().__init__()
        self._file_path = str(file_path)
        self._expected = expected_sha256.lower()

    @pyqtSlot()
    def run(self) -> None:
        try:
            hasher = hashlib.sha256()
            with open(self._file_path, "rb") as fh:
                for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                    hasher.update(chunk)
            digest = hasher.hexdigest().lower()
            if self._expected and digest != self._expected:
                raise ValueError("SHA256 stimmt nicht überein.")
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))
        else:
            self.finished.emit()


class UpdateManager(QObject):
    def __init__(
        self,
        current_version: str,
        manifest_url: str = DEFAULT_MANIFEST_URL,
        parent=None,
        silent_install_args: tuple[str, ...] | None = SILENT_INSTALL_ARGS,
    ):
        super().__init__(parent)
        self._current_version = current_version
        self._manifest_url = manifest_url
        self._silent_install_args = silent_install_args or tuple()

        self._check_thread: QThread | None = None
        self._check_worker: UpdateCheckWorker | None = None

        self._download_thread: QThread | None = None
        self._download_worker: DownloadWorker | None = None
        self._download_dialog: ThemedProgressDialog | None = None
        self._download_target: Path | None = None
        self._download_canceled = False

        self._checksum_thread: QThread | None = None
        self._checksum_worker: ChecksumWorker | None = None

        self._interactive_request = False
        self._pending_manifest: UpdateManifest | None = None

    def check_for_updates(self, interactive: bool = False) -> None:
        if self._check_thread is not None:
            return
        self._interactive_request = interactive
        worker = UpdateCheckWorker(self._manifest_url)
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)  # type: ignore[arg-type]
        worker.finished.connect(self._on_manifest_loaded)
        worker.failed.connect(self._on_manifest_failed)
        worker.finished.connect(lambda *_: self._cleanup_check_thread())
        worker.failed.connect(lambda *_: self._cleanup_check_thread())
        self._check_worker = worker
        self._check_thread = thread
        thread.start()

    def _on_manifest_loaded(self, data: dict) -> None:
        manifest = UpdateManifest.from_dict(data)
        if not manifest.installer_url or not manifest.sha256:
            self._show_error("Manifest unvollständig: URL oder SHA256 fehlt")
            return
        current = version.parse(str(self._current_version))
        remote = version.parse(str(manifest.version))
        if remote <= current:
            if self._interactive_request:
                QMessageBox.information(self.parent(), "Keine Updates", "Sie verwenden bereits die neueste Version.")
            return
        self._pending_manifest = manifest
        self._prompt_update(manifest)

    def _on_manifest_failed(self, message: str) -> None:
        if self._interactive_request:
            self._show_error(f"Update-Suche fehlgeschlagen: {message}")

    def _cleanup_check_thread(self) -> None:
        if self._check_thread:
            self._check_thread.quit()
            self._check_thread.wait(2000)
            self._check_thread.deleteLater()
            self._check_thread = None
        if self._check_worker:
            self._check_worker.deleteLater()
            self._check_worker = None

    def _prompt_update(self, manifest: UpdateManifest) -> None:
        msg = [f"Version {manifest.version} ist verfügbar (aktuell {self._current_version})."]
        if manifest.release_notes:
            msg.append("")
            msg.append(manifest.release_notes)
        if manifest.notes_url:
            msg.append("")
            msg.append(f"Weitere Informationen: {manifest.notes_url}")

        answer = QMessageBox.question(
            self.parent(),
            "Update verfügbar",
            "\n".join(msg),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if answer == QMessageBox.Yes:
            self._start_download(manifest)

    def _start_download(self, manifest: UpdateManifest) -> None:
        target_dir = updates_dir()
        safe_name = f"{manifest.version}_{manifest.installer_filename}"
        target = target_dir / safe_name
        if target.exists():
            try:
                target.unlink()
            except OSError:
                pass

        dialog = ThemedProgressDialog("Update wird heruntergeladen…", "Abbrechen", 0, 100, parent=self.parent())
        dialog.setModal(True)
        dialog.show()
        dialog.rejected.connect(self._cancel_download)

        worker = DownloadWorker(manifest.installer_url, target)
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)  # type: ignore[arg-type]
        worker.progress.connect(dialog.setValue)
        worker.finished.connect(lambda path: self._on_download_finished(Path(path), manifest))
        worker.failed.connect(self._on_download_failed)
        worker.finished.connect(lambda *_: self._cleanup_download_thread())
        worker.failed.connect(lambda *_: self._cleanup_download_thread())

        self._download_thread = thread
        self._download_worker = worker
        self._download_dialog = dialog
        self._download_target = target
        self._download_canceled = False
        thread.start()

    def _cancel_download(self) -> None:
        self._download_canceled = True
        if self._download_worker:
            self._download_worker.cancel()

    def _on_download_finished(self, file_path: Path, manifest: UpdateManifest) -> None:
        self._close_download_dialog()
        self._start_checksum(file_path, manifest)

    def _on_download_failed(self, message: str) -> None:
        self._close_download_dialog()
        if not self._download_canceled:
            self._show_error(f"Download fehlgeschlagen: {message}")
        self._download_canceled = False

    def _cleanup_download_thread(self) -> None:
        if self._download_thread:
            self._download_thread.quit()
            self._download_thread.wait(2000)
            self._download_thread.deleteLater()
            self._download_thread = None
        if self._download_worker:
            self._download_worker.deleteLater()
            self._download_worker = None

    def _start_checksum(self, file_path: Path, manifest: UpdateManifest) -> None:
        worker = ChecksumWorker(file_path, manifest.sha256)
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)  # type: ignore[arg-type]
        worker.finished.connect(lambda: self._on_checksum_ok(file_path, manifest))
        worker.failed.connect(self._on_checksum_failed)
        worker.finished.connect(lambda *_: self._cleanup_checksum_thread())
        worker.failed.connect(lambda *_: self._cleanup_checksum_thread())

        self._checksum_thread = thread
        self._checksum_worker = worker
        thread.start()

    def _on_checksum_ok(self, file_path: Path, manifest: UpdateManifest) -> None:
        self._prompt_install(file_path, manifest)

    def _on_checksum_failed(self, message: str) -> None:
        if self._download_target and self._download_target.exists():
            try:
                self._download_target.unlink()
            except OSError:
                pass
        self._show_error(f"Prüfsumme ungültig: {message}")

    def _cleanup_checksum_thread(self) -> None:
        if self._checksum_thread:
            self._checksum_thread.quit()
            self._checksum_thread.wait(2000)
            self._checksum_thread.deleteLater()
            self._checksum_thread = None
        if self._checksum_worker:
            self._checksum_worker.deleteLater()
            self._checksum_worker = None

    def _prompt_install(self, installer_path: Path, manifest: UpdateManifest) -> None:
        msg = (
            f"Das Update {manifest.version} wurde erfolgreich heruntergeladen.\n\n"
            "Die Anwendung muss jetzt geschlossen werden, damit der Installer gestartet werden kann."
        )
        answer = QMessageBox.question(
            self.parent(),
            "Update installieren",
            msg,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if answer != QMessageBox.Yes:
            return
        self._launch_installer(installer_path)

    def _launch_installer(self, installer_path: Path) -> None:
        args = [str(installer_path)]
        if self._silent_install_args:
            args.extend(self._silent_install_args)
        try:
            subprocess.Popen(args, close_fds=True)
        except Exception as exc:  # noqa: BLE001
            self._show_error(f"Installer konnte nicht gestartet werden: {exc}")
            return
        app = QApplication.instance()
        if app is not None:
            app.quit()

    def _close_download_dialog(self) -> None:
        if self._download_dialog:
            self._download_dialog.close()
            self._download_dialog = None

    def _show_error(self, message: str) -> None:
        QMessageBox.critical(self.parent(), "Update", message)