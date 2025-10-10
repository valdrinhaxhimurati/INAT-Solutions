# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QToolButton, QDialog, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from db_connection import get_db, dict_cursor_factory
from gui.kunden_dialog import KundenDialog


class KundenTab(QWidget):
    kunde_aktualisiert = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.table = QTableWidget()
        self.table.setSelectionBehavior(self.table.SelectRows)
        self.table.setSelectionMode(self.table.SingleSelection)
        # Spalten fix definieren, damit das UI konsistent ist
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["ID", "Anrede", "Name", "PLZ", "Straße", "Stadt", "E-Mail", "Firma"])

        btn_layout = QVBoxLayout()
        btn_add = QToolButton(); btn_add.setText("Kunde hinzufügen"); btn_add.setProperty("role", "add")
        btn_edit = QToolButton(); btn_edit.setText("Kunde bearbeiten"); btn_edit.setProperty("role", "edit")
        btn_del = QToolButton(); btn_del.setText("Kunde löschen"); btn_del.setProperty("role", "delete")
        btn_layout.addWidget(btn_add); btn_layout.addWidget(btn_edit); btn_layout.addWidget(btn_del); btn_layout.addStretch()

        main = QHBoxLayout(); main.addWidget(self.table); main.addLayout(btn_layout)
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
            "strasse":  pick(["strasse", "straße", "street", "adresse", "address"]),
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
        with get_db() as con:
            with con.cursor() as cur:
                cur.execute("""
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
            con.commit()

    def lade_kunden(self):
        conn = get_db()
        try:
            cols = self._detect_kunden_columns(conn)
            def alias_or_empty(dbcol, alias): return f"{dbcol} AS {alias}" if dbcol else f"'' AS {alias}"
            adresse_expr = self._adresse_expr(cols)

            with conn.cursor(cursor_factory=dict_cursor_factory) as cur:
                cur.execute(f"""
                    SELECT
                        {cols['kundennr']} AS kundennr,
                        {cols['name']}     AS name,
                        {alias_or_empty(cols.get('anrede'),  'anrede')},
                        {alias_or_empty(cols.get('email'),   'email')},
                        {alias_or_empty(cols.get('firma'),   'firma')},
                        {alias_or_empty(cols.get('plz'),     'plz')},
                        {alias_or_empty(cols.get('strasse'), 'strasse')},
                        {alias_or_empty(cols.get('stadt'),   'stadt')},
                        {adresse_expr} AS adresse
                    FROM kunden
                    ORDER BY {cols['kundennr']}
                """)
                rows = cur.fetchall()
                if rows and not isinstance(rows[0], dict):
                    cols_desc = [d[0] for d in cur.description]
                    rows = [dict(zip(cols_desc, row)) for row in rows]

            self.table.setRowCount(len(rows))
            for i, r in enumerate(rows):
                rid = int(r.get("kundennr", 0) or 0)
                it_id = QTableWidgetItem(str(rid)); it_id.setData(Qt.UserRole, rid)
                self.table.setItem(i, 0, it_id)
                self.table.setItem(i, 1, QTableWidgetItem(r.get("anrede", "") or ""))
                self.table.setItem(i, 2, QTableWidgetItem(r.get("name", "") or ""))
                self.table.setItem(i, 3, QTableWidgetItem(r.get("plz", "") or ""))
                self.table.setItem(i, 4, QTableWidgetItem(r.get("strasse", "") or ""))
                self.table.setItem(i, 5, QTableWidgetItem(r.get("stadt", "") or ""))
                self.table.setItem(i, 6, QTableWidgetItem(r.get("email", "") or ""))
                self.table.setItem(i, 7, QTableWidgetItem(r.get("firma", "") or ""))
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
                cols = self._detect_kunden_columns(con)
                field_map = {
                    "name": cols.get("name"),
                    "plz": cols.get("plz"),
                    "strasse": cols.get("strasse"),
                    "stadt": cols.get("stadt"),
                    "email": cols.get("email"),
                    "firma": cols.get("firma"),
                    "anrede": cols.get("anrede"),
                }
                insert_cols = [dbcol for key, dbcol in field_map.items() if dbcol]
                insert_vals = [d.get(key, "") for key, dbcol in field_map.items() if dbcol]
                if insert_cols:
                    placeholders = ", ".join(["%s"] * len(insert_cols))
                    sql = f"INSERT INTO kunden ({', '.join(insert_cols)}) VALUES ({placeholders})"
                    with con.cursor() as cur:
                        cur.execute(sql, tuple(insert_vals))
                con.commit()
            self.lade_kunden()
            self.kunde_aktualisiert.emit()

    def kunde_bearbeiten(self):
        rid = self._get_selected_id()
        if rid is None:
            QMessageBox.warning(self, "Keine Auswahl", "Bitte zuerst einen Kunden auswählen.")
            return
        row = self.table.currentRow()
        kunde = {
            "kundennr": rid,
            "anrede": self.table.item(row, 1).text(),
            "name": self.table.item(row, 2).text(),
            "plz": self.table.item(row, 3).text(),
            "strasse": self.table.item(row, 4).text(),
            "stadt": self.table.item(row, 5).text(),
            "email": self.table.item(row, 6).text(),
            "firma": self.table.item(row, 7).text(),
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
                }
                sets, params = [], []
                for key, dbcol in field_map.items():
                    if dbcol is not None:
                        sets.append(f"{dbcol}=%s"); params.append(d.get(key, ""))
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
