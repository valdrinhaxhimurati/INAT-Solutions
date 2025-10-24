# gui/artikellager_tab.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QDialog, QMessageBox, QToolButton
)
from db_connection import get_db, dict_cursor_factory


class ArtikellagerTab(QWidget):
    def __init__(self):
        super().__init__()
        self.table = QTableWidget()
        self.table.setSelectionBehavior(self.table.SelectRows)
        self.table.setSelectionMode(self.table.SingleSelection)

        self._ensure_table()
        self.lade_artikel()

        btn_layout = QVBoxLayout()
        btn_hinzufuegen = QToolButton(); btn_hinzufuegen.setText('Artikel hinzufügen'); btn_hinzufuegen.setProperty("role", "add")
        btn_bearbeiten = QToolButton(); btn_bearbeiten.setText('Artikel bearbeiten'); btn_bearbeiten.setProperty("role", "edit")
        btn_loeschen   = QToolButton(); btn_loeschen.setText('Artikel löschen');     btn_loeschen.setProperty("role", "delete")

        btn_layout.addWidget(btn_hinzufuegen)
        btn_layout.addWidget(btn_bearbeiten)
        btn_layout.addWidget(btn_loeschen)
        btn_layout.addStretch()

        main_layout = QHBoxLayout()
        main_layout.addWidget(self.table)
        main_layout.addLayout(btn_layout)
        self.setLayout(main_layout)

        btn_hinzufuegen.clicked.connect(self.artikel_hinzufuegen)
        btn_bearbeiten.clicked.connect(self.artikel_bearbeiten)
        btn_loeschen.clicked.connect(self.artikel_loeschen)

    # ---------- DB ----------
    def _ensure_table(self):
        conn = get_db()
        is_sqlite = getattr(conn, "is_sqlite", False) or getattr(conn, "is_sqlite_conn", False)
        if is_sqlite:
            sql = """
            CREATE TABLE IF NOT EXISTS artikellager (
                artikel_id     INTEGER PRIMARY KEY AUTOINCREMENT,
                artikelnummer  TEXT,
                bezeichnung    TEXT,
                bestand        INTEGER,
                lagerort       TEXT
            )
            """
        else:
            sql = """
            CREATE TABLE IF NOT EXISTS artikellager (
                artikel_id     BIGSERIAL PRIMARY KEY,
                artikelnummer  TEXT,
                bezeichnung    TEXT,
                bestand        INTEGER,
                lagerort       TEXT
            )
            """
        try:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def lade_artikel(self):
        with get_db() as con:
            with con.cursor() as cur:
                cur.execute("""
                    SELECT artikel_id, artikelnummer, bezeichnung, COALESCE(bestand,0), COALESCE(lagerort,'')
                    FROM public.artikellager
                    ORDER BY bezeichnung
                """)
                daten = cur.fetchall()

        self.table.setRowCount(len(daten))
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Artikelnummer", "Bezeichnung", "Bestand", "Lagerort"])
        for r, row in enumerate(daten):
            for c, val in enumerate(row):
                self.table.setItem(r, c, QTableWidgetItem(str(val)))
        self.table.setColumnWidth(0, 60)
        self.table.setColumnWidth(1, 140)
        self.table.setColumnWidth(2, 260)
        self.table.setColumnWidth(3, 90)
        self.table.setColumnWidth(4, 120)

    def artikel_hinzufuegen(self):
        from gui.lager_dialog import LagerDialog
        dlg = LagerDialog(self, artikel=None)
        if dlg.exec_() == QDialog.Accepted:
            d = dlg.get_daten()
            with get_db() as con:
                with con.cursor() as cur:
                    cur.execute("""
                        INSERT INTO public.artikellager (artikelnummer, bezeichnung, bestand, lagerort)
                        VALUES (%s, %s, %s, %s)
                    """, (d["artikelnummer"], d["bezeichnung"], d["bestand"], d["lagerort"]))
                con.commit()
            self.lade_artikel()

    def artikel_bearbeiten(self):
        from gui.lager_dialog import LagerDialog
        z = self.table.currentRow()
        if z < 0:
            return
        artikel = {
            "artikel_id": int(self.table.item(z, 0).text()),
            "artikelnummer": self.table.item(z, 1).text(),
            "bezeichnung": self.table.item(z, 2).text(),
            "bestand": int(self.table.item(z, 3).text()),
            "lagerort": self.table.item(z, 4).text()
        }
        dlg = LagerDialog(self, artikel=artikel)
        if dlg.exec_() == QDialog.Accepted:
            d = dlg.get_daten()
            with get_db() as con:
                with con.cursor() as cur:
                    cur.execute("""
                        UPDATE public.artikellager
                           SET artikelnummer=%s, bezeichnung=%s, bestand=%s, lagerort=%s
                         WHERE artikel_id=%s
                    """, (d["artikelnummer"], d["bezeichnung"], d["bestand"], d["lagerort"], artikel["artikel_id"]))
                con.commit()
            self.lade_artikel()

    def artikel_loeschen(self):
        z = self.table.currentRow()
        if z < 0:
            return
        artikel_id = int(self.table.item(z, 0).text())
        with get_db() as con:
            with con.cursor() as cur:
                cur.execute("DELETE FROM public.artikellager WHERE artikel_id=%s", (artikel_id,))
            con.commit()
        self.lade_artikel()



