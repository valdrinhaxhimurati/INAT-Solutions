# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QDialog, QMessageBox, QToolButton
)
from db_connection import get_db, dict_cursor_factory
from gui.materiallager_dialog import MateriallagerDialog


class MateriallagerTab(QWidget):
    def __init__(self):
        super().__init__()
        self.table = QTableWidget()
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)

        self._ensure_table()
        self.lade_material()

        btn_layout = QVBoxLayout()
        btn_hinzufuegen = QToolButton(); btn_hinzufuegen.setText('Material hinzufügen'); btn_hinzufuegen.setProperty("role", "add")
        btn_bearbeiten = QToolButton(); btn_bearbeiten.setText('Material bearbeiten'); btn_bearbeiten.setProperty("role", "edit")
        btn_loeschen   = QToolButton(); btn_loeschen.setText('Material löschen');    btn_loeschen.setProperty("role", "delete")

        btn_layout.addWidget(btn_hinzufuegen)
        btn_layout.addWidget(btn_bearbeiten)
        btn_layout.addWidget(btn_loeschen)
        btn_layout.addStretch()

        main_layout = QHBoxLayout()
        main_layout.addWidget(self.table)
        main_layout.addLayout(btn_layout)
        self.setLayout(main_layout)

        btn_hinzufuegen.clicked.connect(self.material_hinzufuegen)
        btn_bearbeiten.clicked.connect(self.material_bearbeiten)
        btn_loeschen.clicked.connect(self.material_loeschen)

    def _ensure_table(self):
        conn = get_db()
        is_sqlite = getattr(conn, "is_sqlite", False) or getattr(conn, "is_sqlite_conn", False)
        if is_sqlite:
            sql = """
            CREATE TABLE IF NOT EXISTS materiallager (
                material_id     INTEGER PRIMARY KEY AUTOINCREMENT,
                materialnummer  TEXT,
                bezeichnung     TEXT,
                menge           INTEGER,
                einheit         TEXT,
                lagerort        TEXT,
                lieferantnr     INTEGER,
                bemerkung       TEXT
            )
            """
        else:
            sql = """
            CREATE TABLE IF NOT EXISTS materiallager (
                material_id     BIGSERIAL PRIMARY KEY,
                materialnummer  TEXT,
                bezeichnung     TEXT,
                menge           INTEGER,
                einheit         TEXT,
                lagerort        TEXT,
                lieferantnr     INTEGER,
                bemerkung       TEXT
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

    def lade_material(self):
        try:
            with get_db() as con:
                with con.cursor(cursor_factory=dict_cursor_factory(con)) as cur:
                    cur.execute("""
                        SELECT m.material_id, m.materialnummer, m.bezeichnung, COALESCE(m.menge,0) AS menge,
                               COALESCE(m.einheit,'') AS einheit, COALESCE(m.lagerort,'') AS lagerort,
                               COALESCE(l.name, '') AS lieferant_name, COALESCE(m.preis,0) AS preis,
                               COALESCE(m.waehrung,'EUR') AS waehrung, COALESCE(m.bemerkung,'') AS bemerkung
                        FROM public.materiallager m
                        LEFT JOIN public.lieferanten l ON m.lieferantnr = l.id
                        ORDER BY m.bezeichnung
                    """)
                    rows = cur.fetchall()
        except Exception:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
                SELECT m.material_id, m.materialnummer, m.bezeichnung, COALESCE(m.menge,0) AS menge,
                       COALESCE(m.einheit,'') AS einheit, COALESCE(m.lagerort,'') AS lagerort,
                       COALESCE(l.name, '') AS lieferant_name, COALESCE(m.preis,0) AS preis,
                       COALESCE(m.waehrung,'EUR') AS waehrung, COALESCE(m.bemerkung,'') AS bemerkung
                FROM materiallager m
                LEFT JOIN lieferanten l ON m.lieferantnr = l.id
                ORDER BY m.bezeichnung
            """)
            rows = cur.fetchall()
            conn.close()

        print("Rows:", rows)
        # Normalisiere Reihen (dict oder sequence)
        daten = []
        cols = ["material_id", "materialnummer", "bezeichnung", "menge", "einheit", "lagerort", "lieferant_name", "preis", "waehrung", "bemerkung"]
        for r in rows:
            if isinstance(r, dict):
                daten.append(tuple(r.get(c) for c in cols))
            else:
                try:
                    daten.append(tuple(r))
                except Exception:
                    # fallback: konvertiere iterierbar zu tuple
                    daten.append(tuple(list(r)))

        self.table.setRowCount(len(daten))
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels(["ID", "Materialnr.", "Bezeichnung", "Menge", "Einheit", "Lagerort", "Lieferant", "Preis", "Währung", "Bemerkung"])
        self.table.setColumnWidth(0, 60)
        self.table.setColumnWidth(1, 140)
        self.table.setColumnWidth(2, 260)
        self.table.setColumnWidth(3, 90)
        self.table.setColumnWidth(4, 80)
        self.table.setColumnWidth(5, 120)
        self.table.setColumnWidth(6, 120)  # angepasst für "Lieferant"
        self.table.setColumnWidth(7, 100)  # Preis
        self.table.setColumnWidth(8, 80)   # Währung
        self.table.setColumnWidth(9, 180)  # Bemerkung

        for r_idx, row in enumerate(daten):
            for c_idx, val in enumerate(row):
                txt = "" if val is None else str(val)
                self.table.setItem(r_idx, c_idx, QTableWidgetItem(txt))

    def material_hinzufuegen(self):
        dlg = MateriallagerDialog(self, material=None)
        if dlg.exec_() == QDialog.Accepted:
            d = dlg.get_daten()
            try:
                with get_db() as con:
                    with con.cursor() as cur:
                        cur.execute("""
                            INSERT INTO public.materiallager (materialnummer, bezeichnung, menge, einheit, lagerort, lieferantnr, bemerkung, preis, waehrung)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (d["materialnummer"], d["bezeichnung"], d["menge"], d["einheit"], d["lagerort"], d["lieferantnr"], d["bemerkung"], d["preis"], d["waehrung"]))
                    con.commit()
            except Exception:
                conn = get_db()
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO public.materiallager (materialnummer, bezeichnung, menge, einheit, lagerort, lieferantnr, bemerkung, preis, waehrung)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (d["materialnummer"], d["bezeichnung"], d["menge"], d["einheit"], d["lagerort"], d["lieferantnr"], d["bemerkung"], d["preis"], d["waehrung"]))
                conn.commit()
                conn.close()
            self.lade_material()

    def material_bearbeiten(self):
        z = self.table.currentRow()
        if z < 0:
            return
        material_id = int(self.table.item(z, 0).text())
        # Lade die vollständigen Daten aus DB (inkl. lieferantnr), nicht aus der Tabelle
        try:
            with get_db() as con:
                with con.cursor(cursor_factory=dict_cursor_factory(con)) as cur:
                    cur.execute("""
                        SELECT material_id, materialnummer, bezeichnung, COALESCE(menge,0) AS menge,
                               COALESCE(einheit,'') AS einheit, COALESCE(lagerort,'') AS lagerort,
                               lieferantnr, COALESCE(bemerkung,'') AS bemerkung, COALESCE(preis,0) AS preis,
                               COALESCE(waehrung,'EUR') AS waehrung
                        FROM public.materiallager WHERE material_id = %s
                    """, (material_id,))
                    row = cur.fetchone()
        except Exception:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
                SELECT material_id, materialnummer, bezeichnung, COALESCE(menge,0) AS menge,
                       COALESCE(einheit,'') AS einheit, COALESCE(lagerort,'') AS lagerort,
                       lieferantnr, COALESCE(bemerkung,'') AS bemerkung, COALESCE(preis,0) AS preis,
                       COALESCE(waehrung,'EUR') AS waehrung
                FROM materiallager WHERE material_id = %s
            """, (material_id,))
            row = cur.fetchone()
            conn.close()
        if not row:
            return
        if isinstance(row, dict):
            material = row
        else:
            material = {
                "material_id": row[0],
                "materialnummer": row[1],
                "bezeichnung": row[2],
                "menge": row[3],
                "einheit": row[4],
                "lagerort": row[5],
                "lieferantnr": row[6],
                "bemerkung": row[7],
                "preis": row[8],
                "waehrung": row[9]
            }
        dlg = MateriallagerDialog(self, material=material)
        if dlg.exec_() == QDialog.Accepted:
            d = dlg.get_daten()
            try:
                with get_db() as con:
                    with con.cursor() as cur:
                        cur.execute("""
                            UPDATE public.materiallager
                            SET materialnummer=%s, bezeichnung=%s, menge=%s, einheit=%s, lagerort=%s, lieferantnr=%s, bemerkung=%s, preis=%s, waehrung=%s
                            WHERE material_id=%s
                        """, (d["materialnummer"], d["bezeichnung"], d["menge"], d["einheit"], d["lagerort"], d["lieferantnr"], d["bemerkung"], d["preis"], d["waehrung"], material["material_id"]))
                    con.commit()
            except Exception:
                conn = get_db()
                cur = conn.cursor()
                cur.execute("""
                    UPDATE public.materiallager
                    SET materialnummer=%s, bezeichnung=%s, menge=%s, einheit=%s, lagerort=%s, lieferantnr=%s, bemerkung=%s, preis=%s, waehrung=%s
                    WHERE material_id=%s
                """, (d["materialnummer"], d["bezeichnung"], d["menge"], d["einheit"], d["lagerort"], d["lieferantnr"], d["bemerkung"], d["preis"], d["waehrung"], material["material_id"]))
                conn.commit()
                conn.close()
            self.lade_material()

    def material_loeschen(self):
        z = self.table.currentRow()
        if z < 0:
            return
        material_id = int(self.table.item(z, 0).text())
        try:
            with get_db() as con:
                with con.cursor() as cur:
                    cur.execute("DELETE FROM public.materiallager WHERE material_id=%s", (material_id,))
                con.commit()
        except Exception:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("DELETE FROM public.materiallager WHERE material_id=%s", (material_id,))
            conn.commit()
            conn.close()
        self.lade_material()

    def lade_lieferanten(self):
        try:
            with get_db() as con:
                with con.cursor(cursor_factory=dict_cursor_factory(con)) as cur:
                    cur.execute("""
                        SELECT lieferantnr, name FROM public.lieferanten ORDER BY name
                    """)
                    rows = cur.fetchall()
        except Exception:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
                SELECT lieferantnr, name FROM lieferanten ORDER BY name
            """)
            rows = cur.fetchall()
            conn.close()
        print("Lieferanten rows:", rows)
        return rows
