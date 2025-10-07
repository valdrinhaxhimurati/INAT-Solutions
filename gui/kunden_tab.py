from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QHBoxLayout, QDialog
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import pyqtSignal
import sqlite3
from PyQt5.QtWidgets import QToolButton
from db_connection import get_db, dict_cursor



class KundenTab(QWidget):
    kunde_aktualisiert = pyqtSignal()  # Signal für neue/aktualisierte Kunden

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()

        self.table = QTableWidget()
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)

        self.lade_kunden()

        btn_layout = QVBoxLayout()


        btn_hinzufuegen = QToolButton()
        btn_hinzufuegen.setText('Kunde hinzufügen')
        btn_hinzufuegen.setProperty("role", "add")


        btn_bearbeiten = QToolButton()
        btn_bearbeiten.setText('Kunde bearbeiten')
        btn_bearbeiten.setProperty("role", "edit")


        btn_loeschen = QToolButton()
        btn_loeschen.setText('Kunde löschen')
        btn_loeschen.setProperty("role", "delete")

 
        btn_layout.addWidget(btn_hinzufuegen)
        btn_layout.addWidget(btn_bearbeiten)
        btn_layout.addWidget(btn_loeschen)
        btn_layout.addStretch()

        main_layout = QHBoxLayout()
        main_layout.addWidget(self.table)
        main_layout.addLayout(btn_layout)

        self.setLayout(main_layout)

        btn_hinzufuegen.clicked.connect(self.kunde_hinzufuegen)
        btn_bearbeiten.clicked.connect(self.kunde_bearbeiten)
        btn_loeschen.clicked.connect(self.kunde_loeschen)

    def lade_kunden(self):
        conn = get_db()
        cursor = conn.cursor(cursor_factory=dict_cursor(conn))
        cursor.execute("""
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
        # Spalten in der richtigen Reihenfolge abfragen
        cursor.execute("SELECT * FROM kunden")
        daten = cursor.fetchall()

        self.table.setRowCount(len(daten))
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["Kundennr.", "Anrede", "Name", "PLZ", "Strasse", "Stadt", "E-Mail", "Firma"])

        self.table.setColumnWidth(0, 80)
        self.table.setColumnWidth(1, 80)
        self.table.setColumnWidth(2, 200)
        self.table.setColumnWidth(3, 60)
        self.table.setColumnWidth(4, 220)
        self.table.setColumnWidth(5, 120)
        self.table.setColumnWidth(6, 250)
        self.table.setColumnWidth(7, 180)

        for row_idx, row in enumerate(daten):
            for col_idx, value in enumerate(row):
                self.table.setItem(row_idx, col_idx, QTableWidgetItem(str(value)))
        conn.close()

    def kunde_hinzufuegen(self):
        from gui.kunden_dialog import KundenDialog  # import hier, falls Modul separat
        dialog = KundenDialog(self, kunde=None)  # Neu: None übergeben bei neuem Kunden
        if dialog.exec_() == QDialog.Accepted:
            daten = dialog.get_daten()
            conn = get_db()
            cursor = conn.cursor(cursor_factory=dict_cursor(conn))
            cursor.execute("""
                INSERT INTO kunden (name, plz, strasse, stadt, email, firma, anrede) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (daten["name"], daten["plz"], daten["strasse"], daten["stadt"], daten["email"], daten["firma"], daten["anrede"]))
            conn.commit()
            conn.close()
            self.lade_kunden()
            self.kunde_aktualisiert.emit()

    def kunde_bearbeiten(self):
        from gui.kunden_dialog import KundenDialog
        zeile = self.table.currentRow()
        if zeile < 0:
            return
        kunde = {
            "kundennr": int(self.table.item(zeile, 0).text()),
            "anrede": self.table.item(zeile, 1).text(),
            "name": self.table.item(zeile, 2).text(),
            "plz": self.table.item(zeile, 3).text(),
            "strasse": self.table.item(zeile, 4).text(),
            "stadt": self.table.item(zeile, 5).text(),
            "email": self.table.item(zeile, 6).text(),
            "firma": self.table.item(zeile, 7).text()
        }
        dialog = KundenDialog(self, kunde=kunde)
        if dialog.exec_() == QDialog.Accepted:
            daten = dialog.get_daten()
            conn = get_db()
            cursor = conn.cursor(cursor_factory=dict_cursor(conn))
            cursor.execute("""
                UPDATE kunden SET anrede= %s, name= %s, plz= %s, strasse= %s, stadt= %s, email= %s, firma= %s WHERE kundennr= %s
            """, (daten["anrede"], daten["name"], daten["plz"], daten["strasse"], daten["stadt"], daten["email"], daten["firma"], kunde["kundennr"]))
            conn.commit()
            conn.close()
            self.lade_kunden()
            self.kunde_aktualisiert.emit()

    def kunde_loeschen(self):
        zeile = self.table.currentRow()
        if zeile < 0:
            return
        kunde_id = int(self.table.item(zeile, 0).text())
        conn = get_db()
        cursor = conn.cursor(cursor_factory=dict_cursor(conn))
        cursor.execute("DELETE FROM kunden WHERE kundennr= %s", (kunde_id,))
        conn.commit()
        conn.close()
        self.lade_kunden()
        self.kunde_aktualisiert.emit()
