# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QCheckBox, QPushButton, QHBoxLayout, QMessageBox
from db_connection import get_db

class LagerEinstellungenDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Lager-Module aktivieren")
        layout = QVBoxLayout()

        self.checkboxes = {}
        lager_typen = ["material", "reifen", "artikel", "dienstleistungen"]
        for typ in lager_typen:
            cb = QCheckBox(f"{typ.capitalize()}lager aktivieren")
            self.checkboxes[typ] = cb
            layout.addWidget(cb)

        # Lade aktuelle Einstellungen
        self._load_einstellungen()

        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("Speichern")
        btn_ok.clicked.connect(self._save_einstellungen)
        btn_cancel = QPushButton("Abbrechen")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def _load_einstellungen(self):
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT lager_typ, aktiv FROM lager_einstellungen")
            rows = cur.fetchall()
            conn.close()
            for row in rows:
                typ, aktiv = row
                if typ in self.checkboxes:
                    self.checkboxes[typ].setChecked(aktiv)
        except Exception as e:
            print(f"Fehler beim Laden der Einstellungen: {e}")

    def _save_einstellungen(self):
        try:
            conn = get_db()
            cur = conn.cursor()
            for typ, cb in self.checkboxes.items():
                aktiv = cb.isChecked()
                # Prüfe, ob deaktiviert wird
                cur.execute("SELECT aktiv FROM lager_einstellungen WHERE lager_typ = %s", (typ,))
                row = cur.fetchone()
                war_aktiv = row[0] if row else False
                if war_aktiv and not aktiv:
                    # Warnung für Deaktivierung
                    msg = QMessageBox()
                    msg.setWindowTitle("Modul deaktivieren")
                    msg.setText(f"Modul '{typ}' deaktivieren? Alle Daten werden gelöscht!")
                    msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                    msg.button(QMessageBox.Yes).setText("Ja")
                    msg.button(QMessageBox.No).setText("Nein")
                    resp = msg.exec_()
                    if resp != QMessageBox.Yes:
                        # Nicht speichern, Checkbox zurücksetzen
                        cb.setChecked(True)
                        continue
                    # Daten löschen
                    tabelle = f"{typ}lager" if typ != "dienstleistungen" else "dienstleistungen"
                    cur.execute(f"DELETE FROM {tabelle}")
                # Speichere Einstellung
                cur.execute("""
                    INSERT INTO lager_einstellungen (lager_typ, aktiv)
                    VALUES (%s, %s)
                    ON CONFLICT (lager_typ) DO UPDATE SET aktiv = EXCLUDED.aktiv
                """, (typ, aktiv))
            conn.commit()
            conn.close()
            self.accept()
        except Exception as e:
            print(f"Fehler beim Speichern: {e}")