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
        try:
            with get_db() as con:
                with con.cursor() as cur:
                    cur.execute(sql)
                con.commit()
        except Exception:
            # Fallback: offene Verbindung verwenden
            conn = get_db()
            cur = conn.cursor()
            cur.execute(sql)
            conn.commit()
            conn.close()

    def lade_material(self):
        try:
            with get_db() as con:
                with con.cursor(cursor_factory=dict_cursor_factory(con)) as cur:
                    cur.execute("""
                        SELECT material_id, materialnummer, bezeichnung, COALESCE(menge,0) AS menge,
                               COALESCE(einheit,'') AS einheit, COALESCE(lagerort,'') AS lagerort,
                               COALESCE(lieferantnr, NULL) AS lieferantnr, COALESCE(bemerkung,'') AS bemerkung
                        FROM public.materiallager
                        ORDER BY bezeichnung
                    """)
                    rows = cur.fetchall()
        except Exception:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
                SELECT material_id, materialnummer, bezeichnung, COALESCE(menge,0) AS menge,
                       COALESCE(einheit,'') AS einheit, COALESCE(lagerort,'') AS lagerort,
                       COALESCE(lieferantnr, NULL) AS lieferantnr, COALESCE(bemerkung,'') AS bemerkung
                FROM public.materiallager
                ORDER BY bezeichnung
            """)
            rows = cur.fetchall()
            conn.close()

        # Normalisiere Reihen (dict oder sequence)
        daten = []
        cols = ["material_id", "materialnummer", "bezeichnung", "menge", "einheit", "lagerort", "lieferantnr", "bemerkung"]
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
        self.table.setColumnCount(len(cols))
        self.table.setHorizontalHeaderLabels(["ID", "Materialnr.", "Bezeichnung", "Menge", "Einheit", "Lagerort", "LieferantNr", "Bemerkung"])
        self.table.setColumnWidth(0, 60)
        self.table.setColumnWidth(1, 140)
        self.table.setColumnWidth(2, 260)
        self.table.setColumnWidth(3, 90)
        self.table.setColumnWidth(4, 80)
        self.table.setColumnWidth(5, 120)
        self.table.setColumnWidth(6, 80)
        self.table.setColumnWidth(7, 180)

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
                            INSERT INTO public.materiallager (materialnummer, bezeichnung, menge, einheit, lagerort, lieferantnr, bemerkung)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, (d["materialnummer"], d["bezeichnung"], d["menge"], d["einheit"], d["lagerort"], d["lieferantnr"], d["bemerkung"]))
                    con.commit()
            except Exception:
                conn = get_db()
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO public.materiallager (materialnummer, bezeichnung, menge, einheit, lagerort, lieferantnr, bemerkung)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (d["materialnummer"], d["bezeichnung"], d["menge"], d["einheit"], d["lagerort"], d["lieferantnr"], d["bemerkung"]))
                conn.commit()
                conn.close()
            self.lade_material()

    def material_bearbeiten(self):
        z = self.table.currentRow()
        if z < 0:
            return
        material = {
            "material_id": int(self.table.item(z, 0).text()),
            "materialnummer": self.table.item(z, 1).text(),
            "bezeichnung": self.table.item(z, 2).text(),
            "menge": int(self.table.item(z, 3).text()),
            "einheit": self.table.item(z, 4).text(),
            "lagerort": self.table.item(z, 5).text(),
            "lieferantnr": None if self.table.item(z,6) is None or self.table.item(z,6).text()=="" else int(self.table.item(z,6).text()),
            "bemerkung": self.table.item(z, 7).text()
        }
        dlg = MateriallagerDialog(self, material=material)
        if dlg.exec_() == QDialog.Accepted:
            d = dlg.get_daten()
            try:
                with get_db() as con:
                    with con.cursor() as cur:
                        cur.execute("""
                            UPDATE public.materiallager
                            SET materialnummer=%s, bezeichnung=%s, menge=%s, einheit=%s, lagerort=%s, lieferantnr=%s, bemerkung=%s
                            WHERE material_id=%s
                        """, (d["materialnummer"], d["bezeichnung"], d["menge"], d["einheit"], d["lagerort"], d["lieferantnr"], d["bemerkung"], material["material_id"]))
                    con.commit()
            except Exception:
                conn = get_db()
                cur = conn.cursor()
                cur.execute("""
                    UPDATE public.materiallager
                    SET materialnummer=%s, bezeichnung=%s, menge=%s, einheit=%s, lagerort=%s, lieferantnr=%s, bemerkung=%s
                    WHERE material_id=%s
                """, (d["materialnummer"], d["bezeichnung"], d["menge"], d["einheit"], d["lagerort"], d["lieferantnr"], d["bemerkung"], material["material_id"]))
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