from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QDialog, QMessageBox
)
from db_connection import get_db, dict_cursor_factory
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
        cursor = conn.cursor(cursor_factory=dict_cursor_factory(conn))
        # create table with DB-appropriate id type (auto-incrementing primary key)
        try:
            is_sqlite = getattr(conn, "is_sqlite", False) or getattr(conn, "is_sqlite_conn", False)
        except Exception:
            is_sqlite = False
        if is_sqlite:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reifenlager (
                    reifen_id INTEGER PRIMARY KEY AUTOINCREMENT,
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
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reifenlager (
                    reifen_id BIGSERIAL PRIMARY KEY,
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
        # Explizite Spalten in der gewünschten Reihenfolge (10 Spalten für die Tabelle)
        cursor.execute("""
            SELECT reifen_id, kundennr, kunde_anzeige, fahrzeug, dimension, typ, dot, lagerort, eingelagert_am, ausgelagert_am, preis, waehrung, bemerkung
            FROM reifenlager ORDER BY dimension
        """)
        daten = cursor.fetchall()

        self.table.setRowCount(len(daten))
        self.table.setColumnCount(13)
        self.table.setHorizontalHeaderLabels(["ID", "Kundennr", "Kunde", "Fahrzeug", "Dimension", "Typ", "DOT", "Lagerort", "Eingelagert", "Ausgelagert", "Preis", "Währung", "Bemerkung"])
        
        for row_idx, row in enumerate(daten):
            # Reihe als dict oder Sequence behandeln und Werte in festgelegter Reihenfolge holen
            if isinstance(row, dict):
                vals = [
                    row.get("reifen_id"),
                    row.get("kundennr"),
                    row.get("kunde_anzeige"),
                    row.get("fahrzeug"),
                    row.get("dimension"),
                    row.get("typ"),
                    row.get("dot"),
                    row.get("lagerort"),
                    row.get("eingelagert_am"),
                    row.get("ausgelagert_am"),
                    row.get("preis"),
                    row.get("waehrung"),
                    row.get("bemerkung"),
                ]
            else:
                # Sequence / sqlite3.Row
                vals = [row[i] for i in range(13)]

            # --- DOT-Logik für Farbe ---
            dot_jahr = None
            dot_wert = "" if vals[5] is None else str(vals[5]).strip()
            # DOT als Jahr oder als KW/Jahr
            if len(dot_wert) == 4 and dot_wert.isdigit():
                if dot_wert.startswith("19") or dot_wert.startswith("20"):
                    dot_jahr = int(dot_wert)
                else:
                    # falls Format wie "KW/YY" erwartet wird, hier ggf. anpassen
                    try:
                        dot_jahr = 2000 + int(dot_wert[2:])
                    except Exception:
                        dot_jahr = None

            zeilenfarbe = QColor(230, 255, 230)  # #e6ffe6 green
            if dot_jahr:
                aktuelles_jahr = datetime.datetime.now().year
                alter = aktuelles_jahr - dot_jahr
                if alter >= 6:
                    zeilenfarbe = QColor(255, 230, 230)  # #ffe6e6 red
                elif alter >= 5:
                    zeilenfarbe = QColor(255, 230, 179)  # #ffe6b3 orange

            for col_idx, value in enumerate(vals):
                txt = "" if value is None else str(value)
                item = QTableWidgetItem(txt)
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                item.setBackground(zeilenfarbe)
                self.table.setItem(row_idx, col_idx, item)

                
        #Alle Spaltenbreiten 
        self.table.setColumnWidth(0, 40)    # ID
        self.table.setColumnWidth(1, 80)    # Kundennr
        self.table.setColumnWidth(2, 250)   # Kunde
        self.table.setColumnWidth(3, 130)   # Fahrzeug
        self.table.setColumnWidth(4, 90)   # Dimension
        self.table.setColumnWidth(5, 80)   # Typ
        self.table.setColumnWidth(6, 80)    # DOT
        self.table.setColumnWidth(7, 120)   # Lagerort
        self.table.setColumnWidth(8, 125)   # Eingelagert am
        self.table.setColumnWidth(9, 125)   # Ausgelagert am
        self.table.setColumnWidth(10, 100)  # Preis
        self.table.setColumnWidth(11, 80)   # Währung
        self.table.setColumnWidth(12, 170)   # Bemerkung        
        # keine Zeilennummern (vertical header) anzeigen
        try:
            self.table.verticalHeader().setVisible(False)
        except Exception:
            pass
        conn.close()

    def reifen_hinzufuegen(self):
        from gui.reifenlager_dialog import ReifenlagerDialog
        dialog = ReifenlagerDialog(self, reifen=None)
        if dialog.exec_() == QDialog.Accepted:
            daten = dialog.get_daten()
            conn = get_db()
            cursor = conn.cursor(cursor_factory=dict_cursor_factory(conn))
            # IMPORTANT: reifen_id wird nicht übergeben — DB erzeugt sie automatisch
            cursor.execute("""
                INSERT INTO reifenlager (kundennr, kunde_anzeige, fahrzeug, dimension, typ, dot, lagerort, eingelagert_am, ausgelagert_am, bemerkung, preis, waehrung)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                daten["kundennr"], daten["kunde_anzeige"], daten["fahrzeug"], daten["dimension"],
                daten["typ"], daten["dot"], daten["lagerort"],
                daten["eingelagert_am"], daten["ausgelagert_am"], daten["bemerkung"],
                daten["preis"], daten["waehrung"]
            ))
            conn.commit()
            conn.close()
            self.lade_reifen()  # zeigt nach Reload die automatisch vergebene ID

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
            "bemerkung": self.table.item(zeile, 9).text(),
            "preis": self.table.item(zeile, 10).text(),
            "waehrung": self.table.item(zeile, 11).text()
        }
        dialog = ReifenlagerDialog(self, reifen=reifen)
        if dialog.exec_() == QDialog.Accepted:
            daten = dialog.get_daten()
            conn = get_db()
            cursor = conn.cursor(cursor_factory=dict_cursor_factory(conn))
            cursor.execute("""
                UPDATE reifenlager
                SET kundennr= %s, kunde_anzeige= %s, fahrzeug= %s, dimension= %s, typ= %s, dot= %s, lagerort= %s, eingelagert_am= %s, ausgelagert_am= %s, bemerkung= %s, preis= %s, waehrung= %s
                WHERE reifen_id= %s
            """, (
                daten["kundennr"], daten["kunde_anzeige"], daten["fahrzeug"], daten["dimension"],
                daten["typ"], daten["dot"], daten["lagerort"],
                daten["eingelagert_am"], daten["ausgelagert_am"], daten["bemerkung"], daten["preis"], daten["waehrung"], reifen["reifen_id"]
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
        cursor = conn.cursor(cursor_factory=dict_cursor_factory(conn))
        cursor.execute("DELETE FROM reifenlager WHERE reifen_id= %s", (reifen_id,))
        conn.commit()
        conn.close()
        self.lade_reifen()



