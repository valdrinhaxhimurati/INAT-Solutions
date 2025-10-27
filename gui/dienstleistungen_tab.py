# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QDialog, QMessageBox, QToolButton
)
from PyQt5.QtCore import Qt
from db_connection import get_db

class DienstleistungenTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.table = QTableWidget()
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)

        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Beschreibung", "Preis", "Einheit", "Währung", "Bemerkung"])
        self.table.setColumnWidth(0, 60)
        self.table.setColumnWidth(1, 200)
        self.table.setColumnWidth(2, 300)
        self.table.setColumnWidth(3, 100)
        self.table.setColumnWidth(4, 100)
        self.table.setColumnWidth(5, 80)   # Währung
        self.table.setColumnWidth(6, 200)

        self._ensure_table()
        self.lade_dienstleistungen()

        btn_layout = QVBoxLayout()
        btn_hinzufuegen = QToolButton(); btn_hinzufuegen.setText('Dienstleistung hinzufügen'); btn_hinzufuegen.setProperty("role", "add")
        btn_bearbeiten = QToolButton(); btn_bearbeiten.setText('Dienstleistung bearbeiten'); btn_bearbeiten.setProperty("role", "edit")
        btn_loeschen   = QToolButton(); btn_loeschen.setText('Dienstleistung löschen');    btn_loeschen.setProperty("role", "delete")

        btn_layout.addWidget(btn_hinzufuegen)
        btn_layout.addWidget(btn_bearbeiten)
        btn_layout.addWidget(btn_loeschen)
        btn_layout.addStretch()

        main_layout = QHBoxLayout()
        main_layout.addWidget(self.table)
        main_layout.addLayout(btn_layout)
        self.setLayout(main_layout)

        btn_hinzufuegen.clicked.connect(self.dienstleistung_hinzufuegen)
        btn_bearbeiten.clicked.connect(self.dienstleistung_bearbeiten)
        btn_loeschen.clicked.connect(self.dienstleistung_loeschen)

    def _ensure_table(self):
        conn = get_db()
        is_sqlite = getattr(conn, "is_sqlite", False) or getattr(conn, "is_sqlite_conn", False)
        if is_sqlite:
            sql = """
            CREATE TABLE IF NOT EXISTS dienstleistungen (
                dienstleistung_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                beschreibung TEXT,
                preis NUMERIC,
                einheit TEXT,
                waehrung TEXT,
                bemerkung TEXT
            )
            """
        else:
            sql = """
            CREATE TABLE IF NOT EXISTS dienstleistungen (
                dienstleistung_id BIGSERIAL PRIMARY KEY,
                name TEXT,
                beschreibung TEXT,
                preis NUMERIC,
                einheit TEXT,
                waehrung TEXT,
                bemerkung TEXT
            )
            """
        try:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def lade_dienstleistungen(self):
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT dienstleistung_id, name, beschreibung, preis, einheit, waehrung, bemerkung FROM dienstleistungen ORDER BY name")
            rows = cur.fetchall()
            conn.close()
        except Exception as e:
            QMessageBox.warning(self, "Fehler", f"Fehler beim Laden: {e}")
            return

        self.table.setRowCount(len(rows))
        for r_idx, row in enumerate(rows):
            for c_idx, val in enumerate(row):
                txt = "" if val is None else str(val)
                item = QTableWidgetItem(txt)
                self.table.setItem(r_idx, c_idx, item)

    def dienstleistung_hinzufuegen(self):
        from gui.dienstleistungen_dialog import DienstleistungenDialog
        dialog = DienstleistungenDialog(self, dienstleistung=None)
        if dialog.exec_() == QDialog.Accepted:
            daten = dialog.get_daten()
            try:
                conn = get_db()
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO dienstleistungen (name, beschreibung, preis, einheit, waehrung, bemerkung)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (daten["name"], daten["beschreibung"], daten["preis"], daten["einheit"], daten["waehrung"], daten["bemerkung"]))
                conn.commit()
                conn.close()
                self.lade_dienstleistungen()
            except Exception as e:
                QMessageBox.warning(self, "Fehler", f"Fehler beim Speichern: {e}")

    def dienstleistung_bearbeiten(self):
        z = self.table.currentRow()
        if z < 0:
            return
        dienstleistung_id = int(self.table.item(z, 0).text())
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT dienstleistung_id, name, beschreibung, preis, einheit, waehrung, bemerkung FROM dienstleistungen WHERE dienstleistung_id = %s", (dienstleistung_id,))
            row = cur.fetchone()
            conn.close()
        except Exception as e:
            QMessageBox.warning(self, "Fehler", f"Fehler beim Laden: {e}")
            return
        if not row:
            return
        dienstleistung = {
            "dienstleistung_id": row[0],
            "name": row[1],
            "beschreibung": row[2],
            "preis": row[3],
            "einheit": row[4],
            "waehrung": row[5],
            "bemerkung": row[6]
        }
        from gui.dienstleistungen_dialog import DienstleistungenDialog
        dialog = DienstleistungenDialog(self, dienstleistung=dienstleistung)
        if dialog.exec_() == QDialog.Accepted:
            daten = dialog.get_daten()
            try:
                conn = get_db()
                cur = conn.cursor()
                cur.execute("""
                    UPDATE dienstleistungen
                    SET name=%s, beschreibung=%s, preis=%s, einheit=%s, waehrung=%s, bemerkung=%s
                    WHERE dienstleistung_id=%s
                """, (daten["name"], daten["beschreibung"], daten["preis"], daten["einheit"], daten["waehrung"], daten["bemerkung"], dienstleistung["dienstleistung_id"]))
                conn.commit()
                conn.close()
                self.lade_dienstleistungen()
            except Exception as e:
                QMessageBox.warning(self, "Fehler", f"Fehler beim Speichern: {e}")

    def dienstleistung_loeschen(self):
        z = self.table.currentRow()
        if z < 0:
            return
        dienstleistung_id = int(self.table.item(z, 0).text())
        resp = QMessageBox.question(self, "Löschen bestätigen", f"Dienstleistung mit ID {dienstleistung_id} wirklich löschen?", QMessageBox.Yes | QMessageBox.No)
        if resp != QMessageBox.Yes:
            return
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("DELETE FROM dienstleistungen WHERE dienstleistung_id = %s", (dienstleistung_id,))
            conn.commit()
            conn.close()
            self.lade_dienstleistungen()
        except Exception as e:
            QMessageBox.warning(self, "Fehler", f"Fehler beim Löschen: {e}")