from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QDialog, QMessageBox, QLineEdit, QComboBox, QLabel, QPushButton
)
from db_connection import get_db, dict_cursor_factory
import sqlite3
import webbrowser
from PyQt5.QtWidgets import QToolButton
from PyQt5.QtCore import Qt, pyqtSignal

class LieferantenTab(QWidget):
    lieferant_aktualisiert = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._all_rows = []

        self.table = QTableWidget()
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setSortingEnabled(True)
        try:
            self.table.verticalHeader().setVisible(False)
        except Exception:
            pass

        # Data will be loaded asynchronously via TabLoader

        # Filter-/Suchleiste analog zu Buchhaltung/Rechnungen
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Suchen…")

        filter_panel = QHBoxLayout()
        filter_panel.setSpacing(12)
        filter_panel.addWidget(self.search_input, stretch=2)

        self.filter_field = QComboBox()
        self.filter_field.addItem("Alle Felder", None)
        self.filter_field.addItem("Lieferantennummer", 1)
        self.filter_field.addItem("Name", 2)
        self.filter_field.addItem("Portal-Link", 3)
        self.filter_field.addItem("Login", 4)

        self.portal_filter = QComboBox()
        self.portal_filter.addItem("Alle", "all")
        self.portal_filter.addItem("Portal-Link vorhanden", "with")
        self.portal_filter.addItem("Kein Portal-Link", "without")

        self.btn_apply_filter = QPushButton("Filter anwenden")

        filter_panel.addWidget(QLabel("Feld:"))
        filter_panel.addWidget(self.filter_field)
        filter_panel.addWidget(QLabel("Portal-Link:"))
        filter_panel.addWidget(self.portal_filter)
        filter_panel.addStretch()
        filter_panel.addWidget(self.btn_apply_filter)

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

        left_layout = QVBoxLayout()
        left_layout.setSpacing(12)
        left_layout.addLayout(filter_panel)
        left_layout.addWidget(self.table)

        main_layout = QHBoxLayout()
        main_layout.addLayout(left_layout, stretch=1)
        main_layout.addLayout(btn_layout)

        self.setLayout(main_layout)

        btn_hinzufuegen.clicked.connect(self.lieferant_hinzufuegen)
        btn_bearbeiten.clicked.connect(self.lieferant_bearbeiten)
        btn_loeschen.clicked.connect(self.lieferant_loeschen)
        btn_portal.clicked.connect(self.portal_link_oeffnen)
        self.search_input.textChanged.connect(self._apply_filters)
        self.btn_apply_filter.clicked.connect(self._apply_filters)

    def lade_lieferanten(self):
        conn = get_db()
        try:
            try:
                cur = conn.cursor(cursor_factory=dict_cursor_factory(conn))
            except Exception:
                cur = conn.cursor()

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

        self._all_rows = daten
        self._apply_filters()

    def _apply_filters(self):
        rows = list(self._all_rows)
        query = self.search_input.text().strip().lower()
        field_idx = self.filter_field.currentData()
        portal_filter = self.portal_filter.currentData()

        filtered = []
        for row in rows:
            if portal_filter == "with" and not (row[3] or "").strip():
                continue
            if portal_filter == "without" and (row[3] or "").strip():
                continue

            if query:
                haystacks = []
                if field_idx is None:
                    haystacks = [str(val or "") for val in row[1:]]
                else:
                    haystacks = [str(row[field_idx] or "")]
                if not any(query in h.lower() for h in haystacks):
                    continue
            filtered.append(row)

        self._populate_table(filtered)

    def _populate_table(self, daten):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(daten))
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "LieferantNr", "Name", "Portal-Link", "Login", "Passwort"])
        self.table.setColumnHidden(0, False)
        self.table.setColumnWidth(0, 60)
        self.table.setColumnWidth(1, 110)
        self.table.setColumnWidth(2, 250)
        self.table.setColumnWidth(3, 360)
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
        self.table.setSortingEnabled(True)

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
            self.lieferant_aktualisiert.emit()

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
            self.lieferant_aktualisiert.emit()

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
        self.lieferant_aktualisiert.emit()

    def portal_link_oeffnen(self):
        zeile = self.table.currentRow()
        if zeile < 0:
            return
        link_item = self.table.item(zeile, 3)
        link = link_item.text() if link_item else ""
        if link:
            webbrowser.open(link)
        else:
            QMessageBox.information(self, "Kein Link", "Kein Link hinterlegt.")

    def get_row_id(self, row_index) -> int | None:
        try:
            item = self.table.item(row_index, 0)
            if item:
                data = item.data(Qt.UserRole)
                if isinstance(data, int):
                    return data
                return int(item.text()) if item.text().strip() else None
        except Exception:
            pass
        return None

    def append_rows(self, rows):
        try:
            normalized = []
            for row_data in rows:
                row = list(row_data)
                while len(row) < 6:
                    row.append("")
                normalized.append(tuple(row[:6]))
            self._all_rows = list(normalized) + self._all_rows
            self._apply_filters()
        except Exception as e:
            print(f"[DBG] LieferantenTab.append_rows error: {e}", flush=True)

    def load_finished(self):
        self.table.resizeColumnsToContents()



