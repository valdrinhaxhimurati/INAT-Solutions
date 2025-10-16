# gui/select_inventory_item.py

from PyQt5 import QtWidgets, QtCore
from db_connection import get_db, dict_cursor_factory
import sqlite3

INVENTORY_TABLE = "artikellager"  # fester Tabellenname


def _is_sqlite(con) -> bool:
    base = getattr(con, "_con", con)  # unwrap evtl. Wrapper
    return isinstance(base, sqlite3.Connection)


class SelectInventoryItemDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Artikel aus Lager auswählen")
        self._items = []               # Liste von Dicts
        self.selected_item = None      # dict: artikel_id, artikelnummer, bezeichnung, bestand, lagerort, preis

        # Suche / Filter
        self.search = QtWidgets.QLineEdit(self)
        self.search.setPlaceholderText("Suche (Bezeichnung, Artikelnummer)")
        self.only_in_stock = QtWidgets.QCheckBox("Nur mit Bestand", self)
        self.only_in_stock.setChecked(True)

        # Tabelle
        self.table = QtWidgets.QTableWidget(self)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Artikelnummer", "Bezeichnung", "Bestand", "Lagerort", "Preis"])
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.doubleClicked.connect(self.accept_selection)

        # Buttons
        btn_ok = QtWidgets.QPushButton("Übernehmen")
        btn_cancel = QtWidgets.QPushButton("Abbrechen")
        btn_ok.clicked.connect(self.accept_selection)
        btn_cancel.clicked.connect(self.reject)

        # Layouts
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

        # Events
        self.search.textChanged.connect(self.refresh)
        self.only_in_stock.stateChanged.connect(self.refresh)

        # Initial laden
        self.refresh()

    # ---------- DB ----------
    def _list_inventory(self, search_text: str, only_in_stock: bool):
        """
        Liefert eine Liste von Dicts mit Keys:
        artikel_id, artikelnummer, bezeichnung, bestand, lagerort, preis
        """
        con = get_db()
        # evtl. vorherigen Fehlerzustand beenden
        try:
            with con.cursor() as c:
                c.execute("SELECT 1")
        except Exception:
            con.rollback()

        with con.cursor(cursor_factory=dict_cursor_factory(con)) as cur:
            where, args = [], []
            if search_text:
                like = f"%{search_text}%"
                where.append("(LOWER(bezeichnung) LIKE LOWER(%s) OR LOWER(artikelnummer) LIKE LOWER(%s))")
                args += [like, like]
            if only_in_stock:
                where.append("COALESCE(bestand,0) > 0")
            where_sql = f"WHERE {' AND '.join(where)}" if where else ""

            # Dialektfrei: kein "public.", kein "::numeric"
            sql = f"""
                SELECT
                    artikel_id,
                    COALESCE(artikelnummer,'') AS artikelnummer,
                    COALESCE(bezeichnung,'')   AS bezeichnung,
                    COALESCE(bestand,0)        AS bestand,
                    COALESCE(lagerort,'')      AS lagerort,
                    0.0                        AS preis
                FROM {INVENTORY_TABLE}
                {where_sql}
                ORDER BY bezeichnung ASC
                LIMIT 200
            """
            # SQLite nutzt "?"-Platzhalter; PostgreSQL "%s"
            if _is_sqlite(con):
                sql = sql.replace("%s", "?")

            try:
                cur.execute(sql, args)
                rows = cur.fetchall()
                # Rows -> Dicts normalisieren (sqlite3.Row, tuples, dicts)
                desc = [d[0] for d in cur.description] if getattr(cur, "description", None) else None
                norm = []
                for r in rows:
                    if isinstance(r, dict):
                        d = r
                    elif isinstance(r, sqlite3.Row):
                        d = {k: r[k] for k in r.keys()}
                    elif desc is not None:
                        d = dict(zip(desc, r))
                    else:
                        d = {}
                    if d.get("preis") is None:
                        d["preis"] = 0
                    norm.append(d)
                return norm
            except Exception:
                con.rollback()
                raise

    # ---------- UI/Logic ----------
    def refresh(self):
        items = self._list_inventory(self.search.text().strip(), self.only_in_stock.isChecked())
        self._items = items
        self.table.setRowCount(len(items))

        for r, x in enumerate(items):
            values = [
                x.get("artikelnummer", ""),
                x.get("bezeichnung", ""),
                x.get("bestand", 0),
                x.get("lagerort", ""),
                f"{float(x.get('preis', 0)):.2f}",
            ]
            for c, val in enumerate(values):
                it = QtWidgets.QTableWidgetItem(str(val))
                it.setFlags(it.flags() ^ QtCore.Qt.ItemIsEditable)
                if c in (2, 4):  # Bestand / Preis rechtsbündig
                    it.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
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
