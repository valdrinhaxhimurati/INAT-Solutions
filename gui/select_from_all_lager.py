# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QPushButton, QTableWidget, QTableWidgetItem, QMessageBox
from PyQt5.QtCore import Qt
from db_connection import get_db

class SelectFromAllLagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Aus Lager auswählen")
        self.resize(800, 600)
        self.selected_item = None

        layout = QVBoxLayout()
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

        self.setLayout(layout)

    def _load_aktive_lager_tabs(self):
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT lager_typ FROM lager_einstellungen WHERE aktiv = TRUE")
            aktive = [row[0] for row in cur.fetchall()]
            conn.close()
        except Exception:
            aktive = []

        if "material" in aktive:
            self.material_table = QTableWidget()
            self._load_materiallager()
            self.tabs.addTab(self.material_table, "Materiallager")

        if "reifen" in aktive:
            self.reifen_table = QTableWidget()
            self._load_reifenlager()
            self.tabs.addTab(self.reifen_table, "Reifenlager")

        if "artikel" in aktive:
            self.artikel_table = QTableWidget()
            self._load_artikellager()
            self.tabs.addTab(self.artikel_table, "Artikellager")

        if "dienstleistungen" in aktive:
            self.dienst_table = QTableWidget()
            self._load_dienstleistungen()
            self.tabs.addTab(self.dienst_table, "Dienstleistungen")

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
        current_tab = self.tabs.currentIndex()
        aktive = []
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT lager_typ FROM lager_einstellungen WHERE aktiv = TRUE ORDER BY lager_typ")
            aktive = [row[0] for row in cur.fetchall()]
            conn.close()
        except Exception:
            aktive = []

        if current_tab < len(aktive):
            typ = aktive[current_tab]
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
        else:
            return

        row = table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Keine Auswahl", "Bitte ein Item auswählen.")
            return

        self.selected_item = {}
        for c_idx, col in enumerate(cols):
            item = table.item(row, c_idx)
            self.selected_item[col] = item.text() if item else ""
        self.accept()