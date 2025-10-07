# gui/select_inventory_item.py
import os
import psycopg2
from PyQt5 import QtWidgets, QtCore

def get_pg_conn():
    return psycopg2.connect(
        host=os.getenv("PGHOST"),
        port=os.getenv("PGPORT"),
        dbname=os.getenv("PGDATABASE"),
        user=os.getenv("PGUSER"),
        password=os.getenv("PGPASSWORD"),
        sslmode=os.getenv("PGSSLMODE"),
    )

class SelectInventoryItemDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Artikel aus Lager auswählen")
        self._items = []
        self.selected_item = None  # dict: artikel_id, artikelnummer, bezeichnung, bestand, lagerort

        self.search = QtWidgets.QLineEdit(self)
        self.search.setPlaceholderText("Suche (Bezeichnung, Artikelnummer)")
        self.only_in_stock = QtWidgets.QCheckBox("Nur mit Bestand", self)
        self.only_in_stock.setChecked(True)

        self.table = QtWidgets.QTableWidget(self)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Artikelnummer", "Bezeichnung", "Bestand", "Lagerort"])
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.doubleClicked.connect(self.accept_selection)

        btn_ok = QtWidgets.QPushButton("Übernehmen")
        btn_cancel = QtWidgets.QPushButton("Abbrechen")
        btn_ok.clicked.connect(self.accept_selection)
        btn_cancel.clicked.connect(self.reject)

        top = QtWidgets.QHBoxLayout()
        top.addWidget(self.search)
        top.addWidget(self.only_in_stock)

        buttons = QtWidgets.QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(btn_ok)
        buttons.addWidget(btn_cancel)

        lay = QtWidgets.QVBoxLayout(self)
        lay.addLayout(top)
        lay.addWidget(self.table)
        lay.addLayout(buttons)

        self.search.textChanged.connect(self.refresh)
        self.only_in_stock.stateChanged.connect(self.refresh)
        self.refresh()

    # ---------- DB ----------
    def _list_inventory(self, query: str, only_in_stock: bool):
        sql = """
            SELECT artikel_id, artikelnummer, bezeichnung,
                   COALESCE(bestand, 0) AS bestand,
                   COALESCE(lagerort, '') AS lagerort
              FROM public.artikellager
             WHERE 1=1
        """
        args = []
        if query:
            sql += " AND (LOWER(bezeichnung) LIKE %s OR LOWER(artikelnummer) LIKE %s)"
            q = f"%{query.lower()}%"
            args.extend([q, q])
        if only_in_stock:
            sql += " AND COALESCE(bestand,0) > 0"
        sql += " ORDER BY bezeichnung LIMIT 200"

        with get_pg_conn() as con:
            with con.cursor() as cur:
                cur.execute(sql, args)
                cols = [d[0] for d in cur.description]
                rows = cur.fetchall()
        return [dict(zip(cols, row)) for row in rows]

    def refresh(self):
        items = self._list_inventory(self.search.text().strip(), self.only_in_stock.isChecked())
        self._items = items
        self.table.setRowCount(len(items))
        for r, x in enumerate(items):
            values = [x["artikelnummer"], x["bezeichnung"], x["bestand"], x["lagerort"]]
            for c, val in enumerate(values):
                it = QtWidgets.QTableWidgetItem(str(val))
                it.setFlags(it.flags() ^ QtCore.Qt.ItemIsEditable)
                self.table.setItem(r, c, it)
        self.table.resizeColumnsToContents()

    def _current_item(self):
        r = self.table.currentRow()
        return self._items[r] if 0 <= r < len(self._items) else None

    def accept_selection(self, *args):
        row = self._current_item()
        if row:
            self.selected_item = row
            self.accept()

    def exec_and_get(self):
        return self.exec_() == QtWidgets.QDialog.Accepted, self.selected_item
