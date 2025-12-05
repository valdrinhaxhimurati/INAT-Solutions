# -*- coding: utf-8 -*-
"""
Backup & Restore Dialog - Sicherung und Wiederherstellung der Datenbank
"""
import os
import shutil
import datetime
import json
import sqlite3
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QFileDialog, QMessageBox, QProgressBar, QListWidget, QListWidgetItem,
    QGroupBox, QCheckBox, QSpinBox, QComboBox
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QFont
from gui.base_dialog import BaseDialog
from gui.dialog_styles import GROUPBOX_STYLE
from db_connection import get_db, get_config_value, set_config_value
from paths import data_dir, local_db_path
from i18n import _


def get_backup_dir():
    """Gibt das Standard-Backup-Verzeichnis zurück."""
    backup_path = get_config_value("backup_directory")
    if backup_path and os.path.isdir(backup_path):
        return backup_path
    # Standard: im data_dir
    default_path = str(data_dir() / "backups")
    os.makedirs(default_path, exist_ok=True)
    return default_path


def list_backups(backup_dir=None):
    """Listet alle vorhandenen Backups auf."""
    if backup_dir is None:
        backup_dir = get_backup_dir()
    
    backups = []
    if not os.path.isdir(backup_dir):
        return backups
    
    for filename in os.listdir(backup_dir):
        if filename.startswith("backup_") and filename.endswith(".db"):
            filepath = os.path.join(backup_dir, filename)
            try:
                stat = os.stat(filepath)
                size_mb = stat.st_size / (1024 * 1024)
                mtime = datetime.datetime.fromtimestamp(stat.st_mtime)
                backups.append({
                    "filename": filename,
                    "filepath": filepath,
                    "size_mb": size_mb,
                    "date": mtime
                })
            except:
                pass
    
    # Sortieren nach Datum (neueste zuerst)
    backups.sort(key=lambda x: x["date"], reverse=True)
    return backups


class BackupWorker(QThread):
    """Worker-Thread für Backup-Operationen."""
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, operation, source_path, target_path):
        super().__init__()
        self.operation = operation  # "backup" oder "restore"
        self.source_path = source_path
        self.target_path = target_path
    
    def run(self):
        try:
            if self.operation == "backup":
                self.progress.emit(10, _("Verbindung wird geschlossen..."))
                
                self.progress.emit(30, _("Datenbank wird kopiert..."))
                
                # SQLite-Datei kopieren
                shutil.copy2(self.source_path, self.target_path)
                
                self.progress.emit(80, _("Backup wird verifiziert..."))
                
                # Verifizieren
                conn = sqlite3.connect(self.target_path)
                conn.execute("SELECT 1")
                conn.close()
                
                self.progress.emit(100, _("Backup erfolgreich erstellt!"))
                self.finished.emit(True, self.target_path)
                
            elif self.operation == "restore":
                self.progress.emit(10, _("Backup wird geprüft..."))
                
                # Backup verifizieren
                conn = sqlite3.connect(self.source_path)
                conn.execute("SELECT 1")
                conn.close()
                
                self.progress.emit(30, _("Aktuelle Datenbank wird gesichert..."))
                
                # Aktuelle DB sichern (falls Restore fehlschlägt)
                if os.path.exists(self.target_path):
                    temp_backup = self.target_path + ".temp_restore_backup"
                    shutil.copy2(self.target_path, temp_backup)
                
                self.progress.emit(50, _("Backup wird wiederhergestellt..."))
                
                # Backup wiederherstellen
                shutil.copy2(self.source_path, self.target_path)
                
                self.progress.emit(80, _("Wiederherstellung wird verifiziert..."))
                
                # Verifizieren
                conn = sqlite3.connect(self.target_path)
                conn.execute("SELECT 1")
                conn.close()
                
                # Temp-Backup löschen
                if os.path.exists(self.target_path + ".temp_restore_backup"):
                    os.remove(self.target_path + ".temp_restore_backup")
                
                self.progress.emit(100, _("Wiederherstellung erfolgreich!"))
                self.finished.emit(True, "")
                
        except Exception as e:
            self.finished.emit(False, str(e))


class BackupRestoreDialog(BaseDialog):
    """Dialog für Backup und Restore der Datenbank."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Backup & Wiederherstellung"))
        self.resize(600, 500)
        
        self.worker = None
        
        layout = self.content_layout
        layout.setSpacing(15)
        
        # === Backup erstellen ===
        backup_group = QGroupBox(_("Backup erstellen"))
        backup_group.setStyleSheet(GROUPBOX_STYLE)
        backup_layout = QVBoxLayout(backup_group)
        
        # Backup-Verzeichnis
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel(_("Speicherort:")))
        self.backup_dir_label = QLabel(get_backup_dir())
        self.backup_dir_label.setStyleSheet("color: #666;")
        self.backup_dir_label.setWordWrap(True)
        dir_layout.addWidget(self.backup_dir_label, 1)
        self.btn_change_dir = QPushButton(_("Ändern..."))
        self.btn_change_dir.clicked.connect(self._change_backup_dir)
        dir_layout.addWidget(self.btn_change_dir)
        backup_layout.addLayout(dir_layout)
        
        # Backup-Button
        self.btn_backup = QPushButton(_("Backup jetzt erstellen"))
        self.btn_backup.setMinimumHeight(40)
        self.btn_backup.setStyleSheet("""
            QPushButton {
                background-color: green;
                color: white;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
        """)
        self.btn_backup.clicked.connect(self._create_backup)
        backup_layout.addWidget(self.btn_backup)
        
        layout.addWidget(backup_group)
        
        # === Backup wiederherstellen ===
        restore_group = QGroupBox(_("Backup wiederherstellen"))
        restore_group.setStyleSheet(GROUPBOX_STYLE)
        restore_layout = QVBoxLayout(restore_group)
        
        restore_layout.addWidget(QLabel(_("Verfügbare Backups:")))
        
        self.backup_list = QListWidget()
        self.backup_list.setMinimumHeight(120)
        self.backup_list.itemSelectionChanged.connect(self._on_backup_selected)
        restore_layout.addWidget(self.backup_list)
        
        # Buttons
        btn_row = QHBoxLayout()
        self.btn_restore = QPushButton(_("Ausgewähltes Backup wiederherstellen"))
        self.btn_restore.setEnabled(False)
        self.btn_restore.clicked.connect(self._restore_backup)
        btn_row.addWidget(self.btn_restore)
        
        self.btn_delete = QPushButton(_("Löschen"))
        self.btn_delete.setEnabled(False)
        self.btn_delete.clicked.connect(self._delete_backup)
        btn_row.addWidget(self.btn_delete)
        
        self.btn_import = QPushButton(_("Andere Datei..."))
        self.btn_import.clicked.connect(self._import_backup)
        btn_row.addWidget(self.btn_import)
        
        restore_layout.addLayout(btn_row)
        
        layout.addWidget(restore_group)
        
        # === Fortschrittsanzeige ===
        self.progress_frame = QFrame()
        self.progress_frame.setVisible(False)
        progress_layout = QVBoxLayout(self.progress_frame)
        
        self.progress_label = QLabel()
        progress_layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        progress_layout.addWidget(self.progress_bar)
        
        layout.addWidget(self.progress_frame)
        
        # === Automatische Backups ===
        auto_group = QGroupBox(_("Automatische Backups"))
        auto_group.setStyleSheet(GROUPBOX_STYLE)
        auto_layout = QHBoxLayout(auto_group)
        
        self.auto_backup_check = QCheckBox(_("Automatisches Backup aktivieren"))
        self.auto_backup_check.setChecked(get_config_value("auto_backup_enabled") == "true")
        self.auto_backup_check.stateChanged.connect(self._on_auto_backup_changed)
        auto_layout.addWidget(self.auto_backup_check)
        
        auto_layout.addWidget(QLabel(_("Aufbewahren:")))
        self.keep_backups_spin = QSpinBox()
        self.keep_backups_spin.setMinimum(1)
        self.keep_backups_spin.setMaximum(100)
        self.keep_backups_spin.setValue(int(get_config_value("keep_backups") or "10"))
        self.keep_backups_spin.valueChanged.connect(self._on_keep_backups_changed)
        auto_layout.addWidget(self.keep_backups_spin)
        auto_layout.addWidget(QLabel(_("Backups")))
        
        auto_layout.addStretch()
        
        layout.addWidget(auto_group)
        
        # Schließen-Button
        self.btn_close = QPushButton(_("Schließen"))
        self.btn_close.clicked.connect(self.accept)
        layout.addWidget(self.btn_close)
        
        # Backups laden
        self._refresh_backup_list()
    
    def _change_backup_dir(self):
        """Ändert das Backup-Verzeichnis."""
        current = get_backup_dir()
        new_dir = QFileDialog.getExistingDirectory(
            self, _("Backup-Verzeichnis wählen"), current
        )
        if new_dir:
            set_config_value("backup_directory", new_dir)
            self.backup_dir_label.setText(new_dir)
            self._refresh_backup_list()
    
    def _refresh_backup_list(self):
        """Aktualisiert die Liste der Backups."""
        self.backup_list.clear()
        backups = list_backups()
        
        for backup in backups:
            date_str = backup["date"].strftime("%d.%m.%Y %H:%M")
            size_str = f"{backup['size_mb']:.1f} MB"
            text = f"{date_str}  —  {size_str}  —  {backup['filename']}"
            
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, backup["filepath"])
            self.backup_list.addItem(item)
        
        if not backups:
            item = QListWidgetItem(_("Keine Backups vorhanden"))
            item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
            item.setForeground(Qt.gray)
            self.backup_list.addItem(item)
    
    def _on_backup_selected(self):
        """Aktiviert/deaktiviert Buttons basierend auf Auswahl."""
        selected = self.backup_list.currentItem()
        has_selection = selected is not None and selected.data(Qt.UserRole) is not None
        self.btn_restore.setEnabled(has_selection)
        self.btn_delete.setEnabled(has_selection)
    
    def _create_backup(self):
        """Erstellt ein neues Backup."""
        try:
            # SQLite-Pfad ermitteln
            db_path = local_db_path()
            if not os.path.exists(db_path):
                QMessageBox.warning(
                    self, _("Fehler"),
                    _("Keine lokale Datenbank gefunden.\nBackup ist nur für SQLite-Datenbanken verfügbar.")
                )
                return
            
            # Backup-Dateiname
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"backup_{timestamp}.db"
            backup_path = os.path.join(get_backup_dir(), backup_filename)
            
            # Progress anzeigen
            self.progress_frame.setVisible(True)
            self.btn_backup.setEnabled(False)
            self.btn_restore.setEnabled(False)
            
            # Worker starten
            self.worker = BackupWorker("backup", db_path, backup_path)
            self.worker.progress.connect(self._on_progress)
            self.worker.finished.connect(self._on_backup_finished)
            self.worker.start()
            
        except Exception as e:
            QMessageBox.critical(self, _("Fehler"), str(e))
    
    def _on_progress(self, percent, message):
        """Aktualisiert die Fortschrittsanzeige."""
        self.progress_bar.setValue(percent)
        self.progress_label.setText(message)
    
    def _on_backup_finished(self, success, message):
        """Wird aufgerufen wenn Backup fertig ist."""
        self.progress_frame.setVisible(False)
        self.btn_backup.setEnabled(True)
        
        if success:
            QMessageBox.information(
                self, _("Backup erstellt"),
                _("Backup erfolgreich erstellt:\n{}").format(message)
            )
            self._refresh_backup_list()
            self._cleanup_old_backups()
        else:
            QMessageBox.critical(
                self, _("Fehler"),
                _("Backup fehlgeschlagen:\n{}").format(message)
            )
    
    def _restore_backup(self):
        """Stellt ein Backup wieder her."""
        selected = self.backup_list.currentItem()
        if not selected:
            return
        
        backup_path = selected.data(Qt.UserRole)
        if not backup_path or not os.path.exists(backup_path):
            QMessageBox.warning(self, _("Fehler"), _("Backup-Datei nicht gefunden."))
            return
        
        # Bestätigung
        reply = QMessageBox.warning(
            self, _("Wiederherstellung bestätigen"),
            _("ACHTUNG: Die aktuelle Datenbank wird durch das Backup ersetzt!\n\n"
              "Alle Änderungen seit dem Backup gehen verloren.\n\n"
              "Fortfahren?"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            db_path = local_db_path()
            
            # Progress anzeigen
            self.progress_frame.setVisible(True)
            self.btn_backup.setEnabled(False)
            self.btn_restore.setEnabled(False)
            
            # Worker starten
            self.worker = BackupWorker("restore", backup_path, db_path)
            self.worker.progress.connect(self._on_progress)
            self.worker.finished.connect(self._on_restore_finished)
            self.worker.start()
            
        except Exception as e:
            QMessageBox.critical(self, _("Fehler"), str(e))
    
    def _on_restore_finished(self, success, message):
        """Wird aufgerufen wenn Restore fertig ist."""
        self.progress_frame.setVisible(False)
        self.btn_backup.setEnabled(True)
        
        if success:
            QMessageBox.information(
                self, _("Wiederherstellung erfolgreich"),
                _("Die Datenbank wurde erfolgreich wiederhergestellt.\n\n"
                  "Bitte starten Sie die Anwendung neu, um die Änderungen zu laden.")
            )
        else:
            QMessageBox.critical(
                self, _("Fehler"),
                _("Wiederherstellung fehlgeschlagen:\n{}").format(message)
            )
    
    def _delete_backup(self):
        """Löscht das ausgewählte Backup."""
        selected = self.backup_list.currentItem()
        if not selected:
            return
        
        backup_path = selected.data(Qt.UserRole)
        if not backup_path:
            return
        
        reply = QMessageBox.question(
            self, _("Backup löschen"),
            _("Soll dieses Backup wirklich gelöscht werden?"),
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                os.remove(backup_path)
                self._refresh_backup_list()
            except Exception as e:
                QMessageBox.critical(self, _("Fehler"), str(e))
    
    def _import_backup(self):
        """Importiert ein Backup von einem anderen Speicherort."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, _("Backup-Datei auswählen"),
            "", _("SQLite Datenbank (*.db);;Alle Dateien (*)")
        )
        
        if filepath:
            # Kopiere ins Backup-Verzeichnis
            try:
                filename = os.path.basename(filepath)
                if not filename.startswith("backup_"):
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"backup_imported_{timestamp}.db"
                
                target = os.path.join(get_backup_dir(), filename)
                shutil.copy2(filepath, target)
                
                QMessageBox.information(
                    self, _("Import erfolgreich"),
                    _("Backup wurde importiert.")
                )
                self._refresh_backup_list()
            except Exception as e:
                QMessageBox.critical(self, _("Fehler"), str(e))
    
    def _on_auto_backup_changed(self, state):
        """Speichert die Auto-Backup-Einstellung."""
        set_config_value("auto_backup_enabled", "true" if state else "false")
    
    def _on_keep_backups_changed(self, value):
        """Speichert die Anzahl der aufzubewahrenden Backups."""
        set_config_value("keep_backups", str(value))
    
    def _cleanup_old_backups(self):
        """Löscht alte Backups wenn zu viele vorhanden sind."""
        try:
            keep = int(get_config_value("keep_backups") or "10")
            backups = list_backups()
            
            if len(backups) > keep:
                # Älteste Backups löschen
                for backup in backups[keep:]:
                    try:
                        os.remove(backup["filepath"])
                    except:
                        pass
        except:
            pass


def create_auto_backup():
    """Erstellt ein automatisches Backup (wird beim App-Start aufgerufen)."""
    try:
        if get_config_value("auto_backup_enabled") != "true":
            return
        
        db_path = local_db_path()
        if not os.path.exists(db_path):
            return
        
        # Prüfen ob heute schon ein Backup erstellt wurde
        backup_dir = get_backup_dir()
        today = datetime.date.today().strftime("%Y%m%d")
        
        for filename in os.listdir(backup_dir):
            if filename.startswith(f"backup_{today}"):
                return  # Heute schon ein Backup vorhanden
        
        # Backup erstellen
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup_{timestamp}.db"
        backup_path = os.path.join(backup_dir, backup_filename)
        
        shutil.copy2(db_path, backup_path)
        
        # Alte Backups aufräumen
        keep = int(get_config_value("keep_backups") or "10")
        backups = list_backups()
        
        if len(backups) > keep:
            for backup in backups[keep:]:
                try:
                    os.remove(backup["filepath"])
                except:
                    pass
        
        print(f"[Backup] Auto-backup created: {backup_filename}")
        
    except Exception as e:
        print(f"[Backup] Auto-backup failed: {e}")
