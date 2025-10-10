# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QLineEdit,
    QPushButton, QLabel, QMessageBox
)
from login import get_users, add_user, delete_user, init_db


class BenutzerVerwaltenDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Benutzer verwalten")
        self.setMinimumWidth(360)

        # stellt je nach Backend die nötige Tabelle bereit (SQLite oder PostgreSQL)
        init_db()

        # UI
        lay = QVBoxLayout(self)
        self.list = QListWidget()
        lay.addWidget(self.list)

        row = QHBoxLayout()
        self.ed_user = QLineEdit(); self.ed_user.setPlaceholderText("Benutzername")
        self.ed_role = QLineEdit(); self.ed_role.setPlaceholderText("Rolle (optional)")
        row.addWidget(self.ed_user); row.addWidget(self.ed_role)
        lay.addLayout(row)

        row2 = QHBoxLayout()
        self.btn_add = QPushButton("Hinzufügen")
        self.btn_del = QPushButton("Löschen")
        row2.addStretch(1); row2.addWidget(self.btn_del); row2.addWidget(self.btn_add)
        lay.addLayout(row2)

        self.btn_add.clicked.connect(self._add)
        self.btn_del.clicked.connect(self._delete)

        self._reload()

    def _reload(self):
        self.list.clear()
        try:
            rows = get_users()
            # rows: [(id, benutzername, passwort_hash, rolle), ...]
            for r in rows:
                uid, name, _, rolle = r
                txt = f"{name}  ({rolle})" if rolle else name
                self.list.addItem(f"{uid} – {txt}")
        except Exception as e:
            QMessageBox.critical(self, "Fehler", str(e))

    def _add(self):
        name = self.ed_user.text().strip()
        rolle = self.ed_role.text().strip() or None
        if not name:
            QMessageBox.warning(self, "Fehler", "Bitte Benutzernamen eingeben.")
            return
        # Demo: leeres Passwort-Hash – in deiner App sicher bereits vorhanden (Hashing/Setzen woanders)
        try:
            add_user(name, "", rolle)
            self.ed_user.clear(); self.ed_role.clear()
            self._reload()
        except Exception as e:
            QMessageBox.critical(self, "Fehler", str(e))

    def _delete(self):
        item = self.list.currentItem()
        if not item:
            return
        try:
            uid = int(item.text().split("–", 1)[0].strip())
            delete_user(uid)
            self._reload()
        except Exception as e:
            QMessageBox.critical(self, "Fehler", str(e))
