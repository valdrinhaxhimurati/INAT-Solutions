from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QDialog, QMessageBox
)
from db_connection import get_db, dict_cursor_factory
import sqlite3
import webbrowser
from PyQt5.QtWidgets import QToolButton

class LieferantenTab(QWidget):
    def __init__(self):
        super().__init__()
        self.table = QTableWidget()
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)

        self.lade_lieferanten()

        btn_layout = QVBoxLayout()

        btn_hinzufuegen = QToolButton()
        btn_hinzufuegen.setText('Lieferant hinzufügen')
        btn_hinzufuegen.setProperty("role", "add")

        btn_bearbeiten = QToolButton()
        btn_bearbeiten.setText('Lieferant bearbeiten')
        btn_bearbeiten.setProperty("role", "edit")

        btn_loeschen = QToolButton()
        btn_loeschen.setText('Lieferant löschen')
        btn_loeschen.setProperty("role", "delete")

        btn_portal = QToolButton()
        btn_portal.setText('Link öffnen')
        btn_portal.setProperty("role", "preview")  

        btn_layout.addWidget(btn_hinzufuegen)
        btn_layout.addWidget(btn_bearbeiten)
        btn_layout.addWidget(btn_loeschen)
        btn_layout.addWidget(btn_portal)
        btn_layout.addStretch()

        main_layout = QHBoxLayout()
        main_layout.addWidget(self.table)
        main_layout.addLayout(btn_layout)

        self.setLayout(main_layout)

        btn_hinzufuegen.clicked.connect(self.lieferant_hinzufuegen)
        btn_bearbeiten.clicked.connect(self.lieferant_bearbeiten)
        btn_loeschen.clicked.connect(self.lieferant_loeschen)
        btn_portal.clicked.connect(self.portal_link_oeffnen)

    def lade_lieferanten(self):
        conn = get_db()
        cursor = conn.cursor(cursor_factory=dict_cursor_factory(conn))
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lieferanten (
                lieferantnr INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                portal_link TEXT,
                login TEXT,
                passwort TEXT
            )
        """)
        cursor.execute("SELECT lieferantnr, name, portal_link, login, passwort FROM lieferanten")
        daten = cursor.fetchall()

        self.table.setRowCount(len(daten))
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Nr.", "Name", "Portal-Link", "Login", "Passwort"
        ])
        self.table.setColumnWidth(0, 40)   # "Nr." Spalte
        self.table.setColumnWidth(1, 250)  # "Name" Spalte
        self.table.setColumnWidth(2, 500)  # "Portal-Link" Spalte
        self.table.setColumnWidth(3, 150)  # "Login" Spalte
        self.table.setColumnWidth(4, 150)  # "Passwort" Spalte
        for row_idx, row in enumerate(daten):
            for col_idx, value in enumerate(row):
                self.table.setItem(row_idx, col_idx, QTableWidgetItem(str(value)))
        conn.close()

    def lieferant_hinzufuegen(self):
        from gui.lieferanten_dialog import LieferantenDialog
        dialog = LieferantenDialog(self, lieferant=None)
        if dialog.exec_() == QDialog.Accepted:
            daten = dialog.get_daten()
            conn = get_db()
            cursor = conn.cursor(cursor_factory=dict_cursor_factory(conn))
            cursor.execute("""
                INSERT INTO lieferanten (name, portal_link, login, passwort)
                VALUES (%s, %s, %s, %s)
            """, (daten["name"], daten["portal_link"], daten["login"], daten["passwort"]))
            conn.commit()
            conn.close()
            self.lade_lieferanten()

    def lieferant_bearbeiten(self):
        from gui.lieferanten_dialog import LieferantenDialog
        zeile = self.table.currentRow()
        if zeile < 0:
            return
        lieferant = {
            "lieferantnr": int(self.table.item(zeile, 0).text()),
            "name": self.table.item(zeile, 1).text(),
            "portal_link": self.table.item(zeile, 2).text(),
            "login": self.table.item(zeile, 3).text(),
            "passwort": self.table.item(zeile, 4).text()
        }
        dialog = LieferantenDialog(self, lieferant=lieferant)
        if dialog.exec_() == QDialog.Accepted:
            daten = dialog.get_daten()
            conn = get_db()
            cursor = conn.cursor(cursor_factory=dict_cursor_factory(conn))
            cursor.execute("""
                UPDATE lieferanten
                SET name= %s, portal_link= %s, login= %s, passwort= %s
                WHERE lieferantnr= %s
            """, (daten["name"], daten["portal_link"], daten["login"], daten["passwort"], lieferant["lieferantnr"]))
            conn.commit()
            conn.close()
            self.lade_lieferanten()

    def lieferant_loeschen(self):
        zeile = self.table.currentRow()
        if zeile < 0:
            return
        lieferant_id = int(self.table.item(zeile, 0).text())
        conn = get_db()
        cursor = conn.cursor(cursor_factory=dict_cursor_factory(conn))
        cursor.execute("DELETE FROM lieferanten WHERE lieferantnr= %s", (lieferant_id,))
        conn.commit()
        conn.close()
        self.lade_lieferanten()

    def portal_link_oeffnen(self):
        zeile = self.table.currentRow()
        if zeile < 0:
            return
        link = self.table.item(zeile, 2).text()
        if link:
            webbrowser.open(link)
        else:
            QMessageBox.information(self, "Kein Link", "Kein Link hinterlegt.")


