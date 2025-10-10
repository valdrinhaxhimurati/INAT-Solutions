# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QToolButton, QDialog, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from db_connection import get_db, dict_cursor_factory
from gui.kunden_dialog import KundenDialog


class KundenTab(QWidget):
    kunde_aktualisiert = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.table = QTableWidget()
        self.table.setSelectionBehavior(self.table.SelectRows)
        self.table.setSelectionMode(self.table.SingleSelection)

        btn_layout = QVBoxLayout()
        btn_add = QToolButton(); btn_add.setText("Kunde hinzufügen"); btn_add.setProperty("role", "add")
        btn_edit = QToolButton(); btn_edit.setText("Kunde bearbeiten"); btn_edit.setProperty("role", "edit")
        btn_del = QToolButton(); btn_del.setText("Kunde löschen"); btn_del.setProperty("role", "delete")
        btn_layout.addWidget(btn_add); btn_layout.addWidget(btn_edit); btn_layout.addWidget(btn_del); btn_layout.addStretch()

        main = QHBoxLayout(); main.addWidget(self.table); main.addLayout(btn_layout)
        self.setLayout(main)

        btn_add.clicked.connect(self.kunde_hinzufuegen)
        btn_edit.clicked.connect(self.kunde_bearbeiten)
        btn_del.clicked.connect(self.kunde_loeschen)

        self._ensure_table()
        self.lade_kunden()

    def _ensure_table(self):
        with get_db() as con:
            with con.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS public.kunden (
                        kundennr BIGSERIAL PRIMARY KEY,
                        name     TEXT,
                        firma    TEXT,
                        plz      TEXT,
                        strasse  TEXT,
                        stadt    TEXT,
                        email    TEXT,
                        anrede   TEXT
                    )
                """)
            con.commit()

    def lade_kunden(self):
        headers = ["ID", "Anrede", "Name", "PLZ", "Strasse", "Stadt", "Email", "Firma"]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)

        with get_db() as con:
            with con.cursor(cursor_factory=dict_cursor_factory(con)) as cur:
                cur.execute("""
                    SELECT kundennr, COALESCE(anrede,'') AS anrede, COALESCE(name,'') AS name,
                           COALESCE(plz,'') AS plz, COALESCE(strasse,'') AS strasse,
                           COALESCE(stadt,'') AS stadt, COALESCE(email,'') AS email,
                           COALESCE(firma,'') AS firma
                    FROM public.kunden
                    ORDER BY name
                """)
                rows = cur.fetchall()

        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            rid = int(r["kundennr"])
            it_id = QTableWidgetItem(str(rid))
            it_id.setData(Qt.UserRole, rid)
            self.table.setItem(i, 0, it_id)
            self.table.setItem(i, 1, QTableWidgetItem(r["anrede"] or ""))
            self.table.setItem(i, 2, QTableWidgetItem(r["name"] or ""))
            self.table.setItem(i, 3, QTableWidgetItem(r["plz"] or ""))
            self.table.setItem(i, 4, QTableWidgetItem(r["strasse"] or ""))
            self.table.setItem(i, 5, QTableWidgetItem(r["stadt"] or ""))
            self.table.setItem(i, 6, QTableWidgetItem(r["email"] or ""))
            self.table.setItem(i, 7, QTableWidgetItem(r["firma"] or ""))
        self.table.resizeColumnsToContents()

    def _get_selected_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        it = self.table.item(row, 0)
        if it is None:
            return None
        rid = it.data(Qt.UserRole)
        if rid is not None:
            try:
                return int(rid)
            except Exception:
                pass
        try:
            return int(it.text())
        except Exception:
            return None

    def kunde_hinzufuegen(self):
        dlg = KundenDialog(self, kunde=None)
        if dlg.exec_() == QDialog.Accepted:
            d = dlg.get_daten()
            with get_db() as con:
                with con.cursor() as cur:
                    cur.execute("""
                        INSERT INTO public.kunden (name, plz, strasse, stadt, email, firma, anrede)
                        VALUES (%s,%s,%s,%s,%s,%s,%s)
                    """, (d["name"], d["plz"], d["strasse"], d["stadt"], d["email"], d["firma"], d["anrede"]))
                con.commit()
            self.lade_kunden()
            self.kunde_aktualisiert.emit()

    def kunde_bearbeiten(self):
        rid = self._get_selected_id()
        if rid is None:
            QMessageBox.warning(self, "Keine Auswahl", "Bitte zuerst einen Kunden auswählen.")
            return
        row = self.table.currentRow()
        kunde = {
            "kundennr": rid,
            "anrede": self.table.item(row, 1).text(),
            "name": self.table.item(row, 2).text(),
            "plz": self.table.item(row, 3).text(),
            "strasse": self.table.item(row, 4).text(),
            "stadt": self.table.item(row, 5).text(),
            "email": self.table.item(row, 6).text(),
            "firma": self.table.item(row, 7).text(),
        }
        dlg = KundenDialog(self, kunde=kunde)
        if dlg.exec_() == QDialog.Accepted:
            d = dlg.get_daten()
            with get_db() as con:
                with con.cursor() as cur:
                    cur.execute("""
                        UPDATE public.kunden
                           SET anrede=%s, name=%s, plz=%s, strasse=%s, stadt=%s, email=%s, firma=%s
                         WHERE kundennr=%s
                    """, (d["anrede"], d["name"], d["plz"], d["strasse"], d["stadt"], d["email"], d["firma"], rid))
                con.commit()
            self.lade_kunden()
            self.kunde_aktualisiert.emit()

    def kunde_loeschen(self):
        rid = self._get_selected_id()
        if rid is None:
            QMessageBox.warning(self, "Keine Auswahl", "Bitte zuerst einen Kunden auswählen.")
            return
        if QMessageBox.question(self, "Löschen", "Kunde wirklich löschen?") != QMessageBox.Yes:
            return
        with get_db() as con:
            with con.cursor() as cur:
                cur.execute("DELETE FROM public.kunden WHERE kundennr=%s", (rid,))
            con.commit()
        self.lade_kunden()
        self.kunde_aktualisiert.emit()
