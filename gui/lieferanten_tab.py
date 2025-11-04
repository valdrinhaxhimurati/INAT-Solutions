from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QDialog, QMessageBox
)
from db_connection import get_db, dict_cursor_factory
import sqlite3
import webbrowser
from PyQt5.QtWidgets import QToolButton
from PyQt5.QtCore import Qt

class LieferantenTab(QWidget):
    def __init__(self):
        super().__init__()
        self.table = QTableWidget()
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        # Keine Zeilennummern anzeigen
        try:
            self.table.verticalHeader().setVisible(False)
        except Exception:
            pass

        self.lade_lieferanten()

        btn_layout = QVBoxLayout()

        btn_hinzufuegen = QToolButton()
        btn_hinzufuegen.setText('Lieferant hinzufügen')
        btn_hinzufuegen.setProperty("role", "add")

        btn_bearbeiten = QToolButton()
        btn_bearbeiten.setText('Lieferant bearbeiten')
        btn_bearbeiten.setProperty("role", "edit")

        btn_loeschen = QToolButton()
        btn_loeschen.setText('Lieferant löschen')
        btn_loeschen.setProperty("role", "delete")

        btn_portal = QToolButton()
        btn_portal.setText('Link öffnen')
        btn_portal.setProperty("role", "preview")  

        btn_layout.addWidget(btn_hinzufuegen)
        btn_layout.addWidget(btn_bearbeiten)
        btn_layout.addWidget(btn_loeschen)
        btn_layout.addWidget(btn_portal)
        btn_layout.addStretch()

        main_layout = QHBoxLayout()
        main_layout.addWidget(self.table)
        main_layout.addLayout(btn_layout)

        self.setLayout(main_layout)

        btn_hinzufuegen.clicked.connect(self.lieferant_hinzufuegen)
        btn_bearbeiten.clicked.connect(self.lieferant_bearbeiten)
        btn_loeschen.clicked.connect(self.lieferant_loeschen)
        btn_portal.clicked.connect(self.portal_link_oeffnen)

    def lade_lieferanten(self):
        conn = get_db()
        try:
            try:
                cur = conn.cursor(cursor_factory=dict_cursor_factory(conn))
            except Exception:
                cur = conn.cursor()

            # Entferne CREATE TABLE (wird von ensure_app_schema() gehandhabt)
            # Hole alle Spalten
            cur.execute("SELECT * FROM lieferanten")
            rows = cur.fetchall()
            desc = getattr(cur, "description", None)
            col_names = [d[0].lower() for d in desc] if desc else []

        except Exception as e:
            print("Fehler beim Laden der Lieferanten (DB):", e)
            rows = []
            col_names = []
        finally:
            try:
                conn.close()
            except Exception:
                pass

        # Verwende id als ID (konsistent mit Schema)
        id_candidates = ("id", "lieferant_id")
        daten = []
        for r in rows:
            if isinstance(r, dict) or hasattr(r, "keys"):
                try:
                    rd = dict(r)
                except Exception:
                    rd = {k: getattr(r, k) for k in getattr(r, "keys", lambda: [])()}
                rd_lower = {k.lower(): v for k, v in rd.items()}
                id_val = None
                for cand in id_candidates:
                    if cand in rd_lower and rd_lower[cand] is not None:
                        id_val = rd_lower[cand]
                        break
                daten.append((
                    id_val,
                    rd_lower.get("lieferantnr"),
                    rd_lower.get("name"),
                    rd_lower.get("portal_link"),
                    rd_lower.get("login"),
                    rd_lower.get("passwort")
                ))
                continue

            # sequence fallback
            try:
                seq = list(r)
            except Exception:
                seq = []
            if col_names and len(col_names) == len(seq):
                m = dict(zip(col_names, seq))
                m = {k.lower(): v for k, v in m.items()}
                id_val = None
                for cand in id_candidates:
                    if cand in m and m[cand] is not None:
                        id_val = m[cand]
                        break
                daten.append((
                    id_val,
                    m.get("lieferantnr"),
                    m.get("name"),
                    m.get("portal_link"),
                    m.get("login"),
                    m.get("passwort")
                ))
            else:
                while len(seq) < 6:
                    seq.append(None)
                daten.append((seq[0], seq[1], seq[2], seq[3], seq[4], seq[5]))

        # UI: 6 Spalten (ID, LieferantNr, Name, Portal-Link, Login, Passwort)
        self.table.setRowCount(len(daten))
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "LieferantNr", "Name", "Portal-Link", "Login", "Passwort"])
        self.table.setColumnHidden(0, False)
        self.table.setColumnWidth(0, 60)
        self.table.setColumnWidth(1, 100)
        self.table.setColumnWidth(2, 250)
        self.table.setColumnWidth(3, 400)
        self.table.setColumnWidth(4, 150)
        self.table.setColumnWidth(5, 150)

        for ri, row in enumerate(daten):
            for ci, val in enumerate(row):
                txt = "" if val is None else str(val)
                item = QTableWidgetItem(txt)
                if ci == 0:
                    try:
                        item.setData(Qt.UserRole, int(val) if val is not None and str(val).strip() != "" else None)
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    except Exception:
                        item.setData(Qt.UserRole, None)
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                self.table.setItem(ri, ci, item)

    def lieferant_hinzufuegen(self):
        from gui.lieferanten_dialog import LieferantenDialog
        dialog = LieferantenDialog(self, lieferant=None)
        if dialog.exec_() == QDialog.Accepted:
            daten = dialog.get_daten()
            conn = get_db()
            cursor = conn.cursor(cursor_factory=dict_cursor_factory(conn))
            cursor.execute("""
                INSERT INTO lieferanten (name, portal_link, login, passwort)
                VALUES (%s, %s, %s, %s)
            """, (daten["name"], daten["portal_link"], daten["login"], daten["passwort"]))
            conn.commit()
            conn.close()
            self.lade_lieferanten()

    def lieferant_bearbeiten(self):
        from gui.lieferanten_dialog import LieferantenDialog
        zeile = self.table.currentRow()
        if zeile < 0:
            return
        lieferant = {
            "id": int(self.table.item(zeile, 0).text()),
            "lieferantnr": self.table.item(zeile, 1).text(),
            "name": self.table.item(zeile, 2).text(),
            "portal_link": self.table.item(zeile, 3).text(),
            "login": self.table.item(zeile, 4).text(),
            "passwort": self.table.item(zeile, 5).text()
        }
        dialog = LieferantenDialog(self, lieferant=lieferant)
        if dialog.exec_() == QDialog.Accepted:
            daten = dialog.get_daten()
            conn = get_db()
            cursor = conn.cursor(cursor_factory=dict_cursor_factory(conn))
            cursor.execute("""
                UPDATE lieferanten
                SET lieferantnr= %s, name= %s, portal_link= %s, login= %s, passwort= %s
                WHERE id= %s
            """, (daten["lieferantnr"], daten["name"], daten["portal_link"], daten["login"], daten["passwort"], lieferant["id"]))
            conn.commit()
            conn.close()
            self.lade_lieferanten()

    def lieferant_loeschen(self):
        z = self.table.currentRow()
        if z < 0:
            return
        item = self.table.item(z, 0)
        if item is None:
            return
        id_val = item.data(Qt.UserRole)
        if id_val is None:
            txt = item.text().strip()
            try:
                id_val = int(txt) if txt != "" else None
            except Exception:
                id_val = None

        if id_val is None:
            QMessageBox.warning(self, "Keine Auswahl", "Keine gültige ID ausgewählt.")
            return

        resp = QMessageBox.question(self, "Löschen bestätigen",
                                    f"Lieferant mit ID {id_val} wirklich löschen?",
                                    QMessageBox.Yes | QMessageBox.No)
        if resp != QMessageBox.Yes:
            return

        try:
            conn = get_db()
            is_sqlite = getattr(conn, "is_sqlite", False) or getattr(conn, "is_sqlite_conn", False) or ("sqlite" in conn.__class__.__module__.lower())
            if is_sqlite:
                sql = "DELETE FROM lieferanten WHERE id=?"
                params = (id_val,)
            else:
                sql = "DELETE FROM public.lieferanten WHERE id=%s"
                params = (id_val,)
            try:
                with conn.cursor() as cur:
                    cur.execute(sql, params)
                conn.commit()
            except Exception:
                cur = conn.cursor()
                cur.execute(sql, params)
                conn.commit()
                cur.close()
        finally:
            try:
                conn.close()
            except Exception:
                pass

        self.lade_lieferanten()

    def portal_link_oeffnen(self):
        zeile = self.table.currentRow()
        if zeile < 0:
            return
        link = self.table.item(zeile, 2).text()
        if link:
            webbrowser.open(link)
        else:
            QMessageBox.information(self, "Kein Link", "Kein Link hinterlegt.")



