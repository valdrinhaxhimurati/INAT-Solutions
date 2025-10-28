# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QToolButton, QDialog, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from db_connection import get_db, dict_cursor_factory
from settings_store import load_config
from gui.kunden_dialog import KundenDialog
import sqlite3


class KundenTab(QWidget):
    kunde_aktualisiert = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.table = QTableWidget()
        self.table.setSelectionBehavior(self.table.SelectRows)
        self.table.setSelectionMode(self.table.SingleSelection)
        # Spalten fix definieren, damit das UI konsistent ist
        # jetzt 9 Spalten: ID + die sichtbaren Felder inklusive "Bemerkung"
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels(["ID", "Anrede", "Name", "Firma", "PLZ", "Straße", "Stadt", "E-Mail", "Bemerkung"])

        btn_layout = QVBoxLayout()
        btn_add = QToolButton();
        btn_add.setText("Kunde hinzufügen");
        btn_add.setProperty("role", "add")
        btn_edit = QToolButton();
        btn_edit.setText("Kunde bearbeiten");
        btn_edit.setProperty("role", "edit")
        btn_del = QToolButton();
        btn_del.setText("Kunde löschen");
        btn_del.setProperty("role", "delete")
        btn_layout.addWidget(btn_add);
        btn_layout.addWidget(btn_edit);
        btn_layout.addWidget(btn_del);
        btn_layout.addStretch()

        main = QHBoxLayout();
        main.addWidget(self.table);
        main.addLayout(btn_layout)
        self.setLayout(main)

        btn_add.clicked.connect(self.kunde_hinzufuegen)
        btn_edit.clicked.connect(self.kunde_bearbeiten)
        btn_del.clicked.connect(self.kunde_loeschen)

        self._ensure_table()
        self.lade_kunden()

    # --- Helpers: Spalten erkennen und Adressausdruck bauen ---
    def _detect_kunden_columns(self, conn):
        names = set()
        with conn.cursor() as cur:
            try:
                if getattr(conn, "is_sqlite", False):
                    cur.execute("PRAGMA table_info(kunden)")
                    rows = cur.fetchall()
                    for r in rows:
                        name = r["name"] if isinstance(r, dict) else (r[1] if len(r) > 1 else r[0])
                        names.add(str(name).lower())
                else:
                    cur.execute(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_schema = current_schema() AND table_name = %s",
                        ("kunden",)
                    )
                    rows = cur.fetchall()
                    for r in rows:
                        name = r["column_name"] if isinstance(r, dict) else r[0]
                        names.add(str(name).lower())
            except Exception:
                pass
        def pick(cands):
            for c in cands:
                if c in names:
                    return c
            return None
        return {
            "kundennr": pick(["kundennr", "id", "kunde_id"]) or "kundennr",
            "name":     pick(["name", "kundenname"]) or "name",
            "anrede":   pick(["anrede", "salutation"]),
            "email":    pick(["email", "e_mail", "mail"]),
            "firma":    pick(["firma", "company", "unternehmen"]),
            "plz":      pick(["plz", "postleitzahl", "zip"]),
            "strasse":  pick(["strasse", "straÃŸe", "street", "adresse", "address"]),
            "stadt":    pick(["stadt", "ort", "city", "ortschaft"]),
        }

    def _adresse_expr(self, cols):
        def coalesce(col): return f"COALESCE({col}, '')"
        plz = cols.get("plz")
        stadt = cols.get("stadt")
        strasse = cols.get("strasse")
        if plz and stadt:
            zip_city = f"({coalesce(plz)} || CASE WHEN ({coalesce(plz)} <> '' AND {coalesce(stadt)} <> '') THEN ' ' ELSE '' END || {coalesce(stadt)})"
        elif plz:
            zip_city = coalesce(plz)
        elif stadt:
            zip_city = coalesce(stadt)
        else:
            zip_city = "''"
        if strasse and zip_city != "''":
            return f"({coalesce(strasse)} || CASE WHEN LENGTH(TRIM({zip_city})) > 0 THEN ', ' ELSE '' END || {zip_city})"
        return (coalesce(strasse) if strasse else zip_city)

    def _ensure_table(self):
        con = get_db()
        try:
            is_sqlite = getattr(con, "is_sqlite", False)
            with con.cursor() as cur:
                if is_sqlite:
                    # nur anlegen, wenn noch nicht vorhanden (kein DROP!)
                    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='kunden'")
                    exists = cur.fetchone() is not None
                    if not exists:
                        cur.execute("""
                            CREATE TABLE kunden (
                                kundennr INTEGER PRIMARY KEY AUTOINCREMENT,
                                anrede TEXT,
                                name TEXT,
                                firma TEXT,
                                plz TEXT,
                                strasse TEXT,
                                stadt TEXT,
                                email TEXT,
                                bemerkung TEXT
                            )
                        """)
                else:
                    # Postgres: create if not exists
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS kunden (
                            kundennr BIGSERIAL PRIMARY KEY,
                            anrede TEXT,
                            name TEXT,
                            firma TEXT,
                            plz TEXT,
                            strasse TEXT,
                            stadt TEXT,
                            email TEXT,
                            bemerkung TEXT
                        )
                    """)
            con.commit()
        finally:
            try:
                con.close()
            except Exception:
                pass

    def lade_kunden(self):
        conn = get_db()
        try:
            cols = self._detect_kunden_columns(conn)
            def alias_or_empty(dbcol, alias): return f"{dbcol} AS {alias}" if dbcol else f"NULL AS {alias}"
            bemerkung_expr = alias_or_empty(cols.get('bemerkung'), 'bemerkung')
            sql = f"""
                SELECT
                    {cols['kundennr']} AS kundennr,
                    {alias_or_empty(cols.get('anrede'), 'anrede')},
                    {cols['name']}     AS name,
                    {alias_or_empty(cols.get('firma'), 'firma')},
                    {alias_or_empty(cols.get('plz'), 'plz')},
                    {alias_or_empty(cols.get('strasse'), 'strasse')},
                    {alias_or_empty(cols.get('stadt'), 'stadt')},
                    {alias_or_empty(cols.get('email'), 'email')},
                    {bemerkung_expr}
                FROM kunden
                ORDER BY {cols['kundennr']}
            """
            with conn.cursor() as cur:
                cur.execute(sql)
                rows = cur.fetchall()
                if rows and not isinstance(rows[0], dict):
                    desc = getattr(cur, "description", None)
                    if desc:
                        cols_desc = [d[0] for d in desc]
                        rows = [dict(zip(cols_desc, row)) for row in rows]
                    else:
                        rows = [dict(r) if hasattr(r, "keys") else r for r in rows]

            col_order = ["kundennr", "anrede", "name", "firma", "plz", "strasse", "stadt", "email", "bemerkung"]

            norm_rows = []
            for r in rows:
                if isinstance(r, dict):
                    vals = tuple(r.get(c) for c in col_order)
                    norm_rows.append(vals)
                    continue
                vals = list(r)
                if len(vals) < len(col_order):
                    vals += [None] * (len(col_order) - len(vals))
                norm_rows.append(tuple(vals[:len(col_order)]))

            self.table.setRowCount(len(norm_rows))
            self.table.setColumnCount(len(col_order))
            self.table.setHorizontalHeaderLabels(["ID","Anrede","Name","Firma","PLZ","Strasse","Stadt","E-Mail","Bemerkung"])
            self.table.setColumnHidden(0, False)
            self.table.setColumnWidth(0, 60)

            for ri, row in enumerate(norm_rows):
                for ci, val in enumerate(row):
                    txt = "" if val is None else str(val)
                    item = QTableWidgetItem(txt)
                    if ci == 0:
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                        try:
                            item.setData(Qt.UserRole, int(val) if val is not None and str(val).strip() != "" else None)
                        except Exception:
                            item.setData(Qt.UserRole, None)
                    item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                    self.table.setItem(ri, ci, item)

            try:
                self.table.verticalHeader().setVisible(False)
            except Exception:
                pass

            self.table.resizeColumnsToContents()
        finally:
            try:
                conn.close()
            except Exception:
                pass

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
                config = load_config()
                db_type = config.get("db_type", "sqlite")
                is_sqlite = db_type == "sqlite"
                cols = self._detect_kunden_columns(con)
                field_map = {
                    "anrede": cols.get("anrede"),
                    "name": cols.get("name"),
                    "firma": cols.get("firma"),
                    "plz": cols.get("plz"),
                    "strasse": cols.get("strasse"),
                    "stadt": cols.get("stadt"),
                    "email": cols.get("email"),
                    "bemerkung": cols.get("bemerkung"),
                }
                insert_cols = [dbcol for key, dbcol in field_map.items() if dbcol]
                insert_vals = [d.get(key, "") for key, dbcol in field_map.items() if dbcol]
                if insert_cols:
                    if is_sqlite:
                        placeholders = ", ".join(["?"] * len(insert_cols))
                    else:
                        placeholders = ", ".join(["%s"] * len(insert_cols))
                    sql = f"INSERT INTO kunden ({', '.join(insert_cols)}) VALUES ({placeholders})"
                    with con.cursor() as cur:
                        cur.execute(sql, insert_vals)
                con.commit()
            self.lade_kunden()
            self.kunde_aktualisiert.emit()

    def kunde_bearbeiten(self):
        rid = self._get_selected_id()
        if rid is None:
            QMessageBox.warning(self, "Keine Auswahl", "Bitte zuerst einen Kunden auswählen.")
            return
        row = self.table.currentRow()

        def cell_text(r, c):
            it = self.table.item(r, c)
            return it.text() if it is not None else ""

        # Spalten-Layout: 0=ID,1=Anrede,2=Name,3=Firma,4=PLZ,5=Strasse,6=Stadt,7=E-Mail,8=Bemerkung
        kunde = {
            "kundennr": rid,
            "anrede": cell_text(row, 1),
            "name": cell_text(row, 2),
            "firma": cell_text(row, 3),
            "plz": cell_text(row, 4),
            "strasse": cell_text(row, 5),
            "stadt": cell_text(row, 6),
            "email": cell_text(row, 7),
            "bemerkung": cell_text(row, 8)
        }

        dlg = KundenDialog(self, kunde=kunde)
        if dlg.exec_() == QDialog.Accepted:
            d = dlg.get_daten()
            with get_db() as con:
                cols = self._detect_kunden_columns(con)
                field_map = {
                    "anrede": cols.get("anrede"),
                    "name": cols.get("name"),
                    "plz": cols.get("plz"),
                    "strasse": cols.get("strasse"),
                    "stadt": cols.get("stadt"),
                    "email": cols.get("email"),
                    "firma": cols.get("firma"),
                    "bemerkung": cols.get("bemerkung"),
                }
                sets, params = [], []
                for key, dbcol in field_map.items():
                    if dbcol is not None:
                        sets.append(f"{dbcol}=%s")
                        params.append(d.get(key, ""))
                if sets:
                    with con.cursor() as cur:
                        cur.execute(f"UPDATE kunden SET {', '.join(sets)} WHERE {cols['kundennr']}=%s", tuple(params + [rid]))
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
            cols = self._detect_kunden_columns(con)
            with con.cursor() as cur:
                cur.execute(f"DELETE FROM kunden WHERE {cols['kundennr']}=%s", (rid,))
            con.commit()
        self.lade_kunden()
        self.kunde_aktualisiert.emit()

