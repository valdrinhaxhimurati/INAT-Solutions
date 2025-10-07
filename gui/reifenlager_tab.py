from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QDialog, QMessageBox
)
from db_connection import get_db, dict_cursor
import sqlite3
import datetime
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLabel, QHBoxLayout
from PyQt5.QtGui import QPixmap, QPainter, QColor
from PyQt5.QtWidgets import QToolButton


class ReifenlagerTab(QWidget):
    def __init__(self):
        super().__init__()
        self.table = QTableWidget()
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)

        self.lade_reifen()

        btn_layout = QVBoxLayout()

        btn_hinzufuegen = QToolButton()
        btn_hinzufuegen.setText('Reifen erfassen')
        btn_hinzufuegen.setProperty("role", "add")

        btn_bearbeiten = QToolButton()
        btn_bearbeiten.setText('Reifen bearbeiten')
        btn_bearbeiten.setProperty("role", "edit")

        btn_loeschen = QToolButton()
        btn_loeschen.setText('Reifen löschen')
        btn_loeschen.setProperty("role", "delete")

        btn_layout.addWidget(btn_hinzufuegen)
        btn_layout.addWidget(btn_bearbeiten)
        btn_layout.addWidget(btn_loeschen)

        # ----------- Legende als einfache Labels -----------
        label_gruen = QLabel("DOT < 5 Jahre")
        label_gruen.setStyleSheet("background-color: #e6ffe6; padding:3px; border-radius:4px;")
        btn_layout.addWidget(label_gruen)

        label_orange = QLabel("DOT ≥ 5 Jahre")
        label_orange.setStyleSheet("background-color: #ffe6b3; padding:3px; border-radius:4px;")
        btn_layout.addWidget(label_orange)

        label_rot = QLabel("DOT ≥ 6 Jahre")
        label_rot.setStyleSheet("background-color: #ffe6e6; padding:3px; border-radius:4px;")
        btn_layout.addWidget(label_rot)
        btn_layout.addStretch()

        main_layout = QHBoxLayout()
        main_layout.addWidget(self.table)
        main_layout.addLayout(btn_layout)
        self.setLayout(main_layout)

 
        btn_hinzufuegen.clicked.connect(self.reifen_hinzufuegen)
        btn_bearbeiten.clicked.connect(self.reifen_bearbeiten)
        btn_loeschen.clicked.connect(self.reifen_loeschen)
    

    def lade_reifen(self):
        conn = get_db()
        cursor = conn.cursor(cursor_factory=dict_cursor(conn))
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reifenlager (
                reifen_id SERIAL PRIMARY KEY,
                kundennr INTEGER,
                kunde_anzeige TEXT,
                fahrzeug TEXT,
                dimension TEXT,
                typ TEXT,
                dot TEXT,
                lagerort TEXT,
                eingelagert_am TEXT,
                ausgelagert_am TEXT,
                bemerkung TEXT
            )
        """)
        cursor.execute("""SELECT * FROM reifenlager""")
        daten = cursor.fetchall()

        self.table.setRowCount(len(daten))
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "ID", "Kunde", "Fahrzeug", "Dimension", "Typ", "DOT",
            "Lagerort", "Eingelagert am", "Ausgelagert am", "Bemerkung"
        ])
        
        for row_idx, row in enumerate(daten):
            # --- DOT-Logik für Farbe ---
            dot_jahr = None
            dot_wert = str(row[5]).strip()
            # DOT als Jahr oder als KW/Jahr
            if len(dot_wert) == 4 and dot_wert.isdigit():
                if dot_wert.startswith("19") or dot_wert.startswith("20"):
                    dot_jahr = int(dot_wert)
                else:
                    dot_jahr = 2000 + int(dot_wert[2:])
            zeilenfarbe = QColor(230, 255, 230)  # #e6ffe6 green
            if dot_jahr:
                aktuelles_jahr = datetime.datetime.now().year
                alter = aktuelles_jahr - dot_jahr
                if alter >= 6:
                    zeilenfarbe = QColor(255, 230, 230)  # #ffe6e6 red
                elif alter >= 5:
                    zeilenfarbe_orange = QColor(255, 230, 179)  # #ffe6b3 orange

            for col_idx, value in enumerate(row):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                item.setBackground(zeilenfarbe)
                self.table.setItem(row_idx, col_idx, item)

                
        #Alle Spaltenbreiten 
        self.table.setColumnWidth(0, 40)    # ID
        self.table.setColumnWidth(1, 250)   # Kunde
        self.table.setColumnWidth(2, 130)   # Fahrzeug
        self.table.setColumnWidth(3, 90)   # Dimension
        self.table.setColumnWidth(4, 80)   # Typ
        self.table.setColumnWidth(5, 80)    # DOT
        self.table.setColumnWidth(6, 120)   # Lagerort
        self.table.setColumnWidth(7, 125)   # Eingelagert am
        self.table.setColumnWidth(8, 125)   # Ausgelagert am
        self.table.setColumnWidth(9, 170)   # Bemerkung        
        
        conn.close()

    def reifen_hinzufuegen(self):
        from gui.reifenlager_dialog import ReifenlagerDialog
        dialog = ReifenlagerDialog(self, reifen=None)
        if dialog.exec_() == QDialog.Accepted:
            daten = dialog.get_daten()
            conn = get_db()
            cursor = conn.cursor(cursor_factory=dict_cursor(conn))
            cursor.execute("""
                INSERT INTO reifenlager (kundennr, kunde_anzeige, fahrzeug, dimension, typ, dot, lagerort, eingelagert_am, ausgelagert_am, bemerkung)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                daten["kundennr"], daten["kunde_anzeige"], daten["fahrzeug"], daten["dimension"],
                daten["typ"], daten["dot"], daten["lagerort"],
                daten["eingelagert_am"], daten["ausgelagert_am"], daten["bemerkung"]
            ))
            conn.commit()
            conn.close()
            self.lade_reifen()

    def reifen_bearbeiten(self):
        from gui.reifenlager_dialog import ReifenlagerDialog
        zeile = self.table.currentRow()
        if zeile < 0:
            return
        reifen = {
            "reifen_id": int(self.table.item(zeile, 0).text()),
            "kunde_anzeige": self.table.item(zeile, 1).text(),
            "fahrzeug": self.table.item(zeile, 2).text(),
            "dimension": self.table.item(zeile, 3).text(),
            "typ": self.table.item(zeile, 4).text(),
            "dot": self.table.item(zeile, 5).text(),
            "lagerort": self.table.item(zeile, 6).text(),
            "eingelagert_am": self.table.item(zeile, 7).text(),
            "ausgelagert_am": self.table.item(zeile, 8).text(),
            "bemerkung": self.table.item(zeile, 9).text()
        }
        dialog = ReifenlagerDialog(self, reifen=reifen)
        if dialog.exec_() == QDialog.Accepted:
            daten = dialog.get_daten()
            conn = get_db()
            cursor = conn.cursor(cursor_factory=dict_cursor(conn))
            cursor.execute("""
                UPDATE reifenlager
                SET kundennr= %s, kunde_anzeige= %s, fahrzeug= %s, dimension= %s, typ= %s, dot= %s, lagerort= %s, eingelagert_am= %s, ausgelagert_am= %s, bemerkung= %s
                WHERE reifen_id= %s
            """, (
                daten["kundennr"], daten["kunde_anzeige"], daten["fahrzeug"], daten["dimension"],
                daten["typ"], daten["dot"], daten["lagerort"],
                daten["eingelagert_am"], daten["ausgelagert_am"], daten["bemerkung"], reifen["reifen_id"]
            ))
            conn.commit()
            conn.close()
            self.lade_reifen()

    def reifen_loeschen(self):
        zeile = self.table.currentRow()
        if zeile < 0:
            return
        reifen_id = int(self.table.item(zeile, 0).text())
        conn = get_db()
        cursor = conn.cursor(cursor_factory=dict_cursor(conn))
        cursor.execute("DELETE FROM reifenlager WHERE reifen_id= %s", (reifen_id,))
        conn.commit()
        conn.close()
        self.lade_reifen()
