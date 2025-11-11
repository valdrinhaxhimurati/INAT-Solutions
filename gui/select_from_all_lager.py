# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QPushButton, QTableWidget, QTableWidgetItem, QMessageBox
from PyQt5.QtCore import Qt
from db_connection import get_db
import sqlite3
# NEU: BaseDialog importieren
from .base_dialog import BaseDialog

def _to_bool(val):
    if isinstance(val, bool):
        return val
    if val is None:
        return False
    try:
        return bool(int(val))
    except Exception:
        s = str(val).strip().lower()
        return s in ("1", "true", "t", "yes", "y", "on")

# ÄNDERUNG: Von BaseDialog erben
class SelectFromAllLagerDialog(BaseDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Aus Lager auswählen")
        self.resize(800, 600)
        self.selected_item = None
        self.tab_map = {}  # NEU: Speichert die Zuordnung von Index zu Lagertyp

        # WICHTIG: Das Layout vom BaseDialog verwenden
        layout = self.content_layout
        self.tabs = QTabWidget()

        # Lade aktive Lager
        self._load_aktive_lager_tabs()

        layout.addWidget(self.tabs)

        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("Auswählen")
        btn_ok.clicked.connect(self._select_item)
        btn_cancel = QPushButton("Abbrechen")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

        # ÄNDERUNG: self.setLayout() entfernen

    def _load_aktive_lager_tabs(self):
        try:
            conn = get_db()
            cur = conn.cursor()
            # WICHTIG: ORDER BY für eine konsistente Reihenfolge
            cur.execute("SELECT lager_typ, aktiv FROM lager_einstellungen ORDER BY lager_typ")
            rows = cur.fetchall()
            conn.close()
            aktive = []
            for row in rows:
                # row may be tuple or dict
                if isinstance(row, dict):
                    lt = row.get("lager_typ")
                    av = row.get("aktiv")
                else:
                    if len(row) >= 2:
                        lt, av = row[0], row[1]
                    else:
                        continue
                if lt and _to_bool(av):
                    aktive.append(lt)
        except Exception:
            aktive = []

        tab_index = 0  # Zähler für die Tabs
        if "material" in aktive:
            self.material_table = QTableWidget()
            # make row-selection reliable and ensure full-row select on click
            self.material_table.setSelectionBehavior(QTableWidget.SelectRows)
            self.material_table.setSelectionMode(QTableWidget.SingleSelection)
            self.material_table.setEditTriggers(QTableWidget.NoEditTriggers)
            self.material_table.verticalHeader().setVisible(False)
            self.material_table.cellClicked.connect(lambda r, c, t=self.material_table: t.selectRow(r))
            self._load_materiallager()
            self.tabs.addTab(self.material_table, "Materiallager")
            self.tab_map[tab_index] = "material"  # Zuordnung speichern
            tab_index += 1

        if "reifen" in aktive:
            self.reifen_table = QTableWidget()
            self.reifen_table.setSelectionBehavior(QTableWidget.SelectRows)
            self.reifen_table.setSelectionMode(QTableWidget.SingleSelection)
            self.reifen_table.setEditTriggers(QTableWidget.NoEditTriggers)
            self.reifen_table.verticalHeader().setVisible(False)
            self.reifen_table.cellClicked.connect(lambda r, c, t=self.reifen_table: t.selectRow(r))
            self._load_reifenlager()
            self.tabs.addTab(self.reifen_table, "Reifenlager")
            self.tab_map[tab_index] = "reifen"  # Zuordnung speichern
            tab_index += 1

        if "artikel" in aktive:
            self.artikel_table = QTableWidget()
            self.artikel_table.setSelectionBehavior(QTableWidget.SelectRows)
            self.artikel_table.setSelectionMode(QTableWidget.SingleSelection)
            self.artikel_table.setEditTriggers(QTableWidget.NoEditTriggers)
            self.artikel_table.verticalHeader().setVisible(False)
            self.artikel_table.cellClicked.connect(lambda r, c, t=self.artikel_table: t.selectRow(r))
            self._load_artikellager()
            self.tabs.addTab(self.artikel_table, "Artikellager")
            self.tab_map[tab_index] = "artikel"  # Zuordnung speichern
            tab_index += 1

        if "dienstleistungen" in aktive:
            self.dienst_table = QTableWidget()
            self.dienst_table.setSelectionBehavior(QTableWidget.SelectRows)
            self.dienst_table.setSelectionMode(QTableWidget.SingleSelection)
            self.dienst_table.setEditTriggers(QTableWidget.NoEditTriggers)
            self.dienst_table.verticalHeader().setVisible(False)
            self.dienst_table.cellClicked.connect(lambda r, c, t=self.dienst_table: t.selectRow(r))
            self._load_dienstleistungen()
            self.tabs.addTab(self.dienst_table, "Dienstleistungen")
            self.tab_map[tab_index] = "dienstleistungen"  # Zuordnung speichern
            tab_index += 1

    def _load_materiallager(self):
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT material_id, materialnummer, bezeichnung, preis FROM materiallager ORDER BY bezeichnung")
            rows = cur.fetchall()
            conn.close()
        except Exception as e:
            QMessageBox.warning(self, "Fehler", f"Fehler beim Laden des Materiallagers: {e}")
            return

        self.material_table.setColumnCount(4)
        self.material_table.setHorizontalHeaderLabels(["ID", "Materialnr.", "Bezeichnung", "Preis"])
        self.material_table.setRowCount(len(rows))
        for r_idx, row in enumerate(rows):
            for c_idx, val in enumerate(row):
                txt = "" if val is None else str(val)
                item = QTableWidgetItem(txt)
                self.material_table.setItem(r_idx, c_idx, item)

    def _load_reifenlager(self):
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT reifen_id, dimension, typ, preis FROM reifenlager ORDER BY dimension")
            rows = cur.fetchall()
            conn.close()
        except Exception as e:
            QMessageBox.warning(self, "Fehler", f"Fehler beim Laden des Reifenlagers: {e}")
            return

        self.reifen_table.setColumnCount(4)
        self.reifen_table.setHorizontalHeaderLabels(["ID", "Dimension", "Typ", "Preis"])
        self.reifen_table.setRowCount(len(rows))
        for r_idx, row in enumerate(rows):
            for c_idx, val in enumerate(row):
                txt = "" if val is None else str(val)
                item = QTableWidgetItem(txt)
                self.reifen_table.setItem(r_idx, c_idx, item)

    def _load_dienstleistungen(self):
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT dienstleistung_id, name, beschreibung, preis FROM dienstleistungen ORDER BY name")
            rows = cur.fetchall()
            conn.close()
        except Exception as e:
            QMessageBox.warning(self, "Fehler", f"Fehler beim Laden der Dienstleistungen: {e}")
            return

        self.dienst_table.setColumnCount(4)
        self.dienst_table.setHorizontalHeaderLabels(["ID", "Name", "Beschreibung", "Preis"])
        self.dienst_table.setRowCount(len(rows))
        for r_idx, row in enumerate(rows):
            for c_idx, val in enumerate(row):
                txt = "" if val is None else str(val)
                item = QTableWidgetItem(txt)
                self.dienst_table.setItem(r_idx, c_idx, item)

    def _load_artikellager(self):
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT artikel_id, artikelnummer, bezeichnung, preis FROM artikellager ORDER BY bezeichnung")
            rows = cur.fetchall()
            conn.close()
        except Exception as e:
            QMessageBox.warning(self, "Fehler", f"Fehler beim Laden des Artikellagers: {e}")
            return

        self.artikel_table.setColumnCount(4)
        self.artikel_table.setHorizontalHeaderLabels(["ID", "Artikelnummer", "Bezeichnung", "Preis"])
        self.artikel_table.setRowCount(len(rows))
        for r_idx, row in enumerate(rows):
            for c_idx, val in enumerate(row):
                txt = "" if val is None else str(val)
                item = QTableWidgetItem(txt)
                self.artikel_table.setItem(r_idx, c_idx, item)

    def _select_item(self):
        current_tab_index = self.tabs.currentIndex()
        
        # Vereinfachte Logik: Direkter Zugriff über die gespeicherte Map
        typ = self.tab_map.get(current_tab_index)

        if not typ:
            QMessageBox.warning(self, "Fehler", "Der ausgewählte Tab konnte nicht zugeordnet werden.")
            return

        if typ == "material":
            table = self.material_table
            cols = ["material_id", "materialnummer", "bezeichnung", "preis"]
        elif typ == "reifen":
            table = self.reifen_table
            cols = ["reifen_id", "dimension", "typ", "preis"]
        elif typ == "artikel":
            table = self.artikel_table
            cols = ["artikel_id", "artikelnummer", "bezeichnung", "preis"]
        elif typ == "dienstleistungen":
            table = self.dienst_table
            cols = ["dienstleistung_id", "name", "beschreibung", "preis"]
        else:
            return

        # robust row detection: try currentRow, then selectedRows(), then currentIndex()
        row = table.currentRow()
        if row < 0:
            sel = table.selectionModel().selectedRows()
            if sel:
                row = sel[0].row()
            else:
                idx = table.currentIndex()
                row = idx.row() if idx.isValid() else -1
        if row < 0:
            QMessageBox.warning(self, "Keine Auswahl", "Bitte ein Item auswählen.")
            return

        self.selected_item = {}
        for c_idx, col in enumerate(cols):
            item = table.item(row, c_idx)
            self.selected_item[col] = item.text() if item else ""
        self.accept()