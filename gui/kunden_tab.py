# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QToolButton, QDialog, QMessageBox, QLabel, QHeaderView, QLineEdit,
    QPushButton, QComboBox
)
from PyQt5.QtCore import Qt, pyqtSignal
# KORREKTUR: DBConnection entfernt, da es nicht existiert. Wir verwenden get_db().
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


        self.table.setColumnHidden(0, True)


        header = self.table.horizontalHeader()
        for i in range(1, 8):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(8, QHeaderView.Stretch)


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
        
        # --- NEU: Layout für Suche und Tabelle ---
        table_layout = QVBoxLayout()
        filter_row = QHBoxLayout()
        filter_row.setSpacing(12)
        self.suchfeld = QLineEdit()
        self.suchfeld.setPlaceholderText("Suchen...")
        self.suchfeld.textChanged.connect(self.filter_tabelle)
        filter_row.addWidget(self.suchfeld, stretch=2)

        filter_row.addWidget(QLabel("PLZ:"))
        self.filter_plz = QComboBox()
        self.filter_plz.addItem("Alle", "")
        filter_row.addWidget(self.filter_plz)
        self.filter_plz.currentIndexChanged.connect(self._apply_filters)

        filter_row.addWidget(QLabel("Ort:"))
        self.filter_stadt = QComboBox()
        self.filter_stadt.addItem("Alle", "")
        filter_row.addWidget(self.filter_stadt)
        self.filter_stadt.currentIndexChanged.connect(self._apply_filters)

        filter_row.addStretch(1)

        self.btn_filter = QPushButton("Filter anwenden")
        self.btn_filter.clicked.connect(self._apply_filters)
        filter_row.addWidget(self.btn_filter)

        table_layout.addLayout(filter_row)
        table_layout.addWidget(self.table)

        main.addLayout(table_layout);
        main.addLayout(btn_layout)
        self.setLayout(main)

        btn_add.clicked.connect(self.kunde_hinzufuegen)
        btn_edit.clicked.connect(self.kunde_bearbeiten)
        btn_del.clicked.connect(self.kunde_loeschen)

        self._ensure_table()

        try:
            self.table.verticalHeader().setVisible(False)
        except Exception:
            pass

    # --- NEU: Filterfunktion für die Tabelle ---
    def filter_tabelle(self, text):
        self._apply_filters()

    def _apply_filters(self):
        search = self.suchfeld.text().strip().lower()
        plz_filter = getattr(self, "filter_plz", None)
        ort_filter = getattr(self, "filter_stadt", None)
        plz = plz_filter.currentData() if plz_filter else ""
        ort = ort_filter.currentData() if ort_filter else ""
        plz = (plz or "").strip().lower()
        ort = (ort or "").strip().lower()

        for row in range(self.table.rowCount()):
            matches_search = True
            if search:
                matches_search = any(
                    search in (self.table.item(row, col).text().lower() if self.table.item(row, col) else "")
                    for col in range(self.table.columnCount())
                )

            matches_plz = True
            if plz:
                plz_item = self.table.item(row, 4)
                matches_plz = plz in (plz_item.text().lower() if plz_item else "")

            matches_ort = True
            if ort:
                ort_item = self.table.item(row, 6)
                matches_ort = ort in (ort_item.text().lower() if ort_item else "")

            self.table.setRowHidden(row, not (matches_search and matches_plz and matches_ort))

    def _populate_filter_values(self):
        combo_plz = getattr(self, "filter_plz", None)
        combo_ort = getattr(self, "filter_stadt", None)
        if not combo_plz or not combo_ort:
            return

        plz_values = set()
        ort_values = set()
        for row in range(self.table.rowCount()):
            plz_item = self.table.item(row, 4)
            ort_item = self.table.item(row, 6)
            if plz_item:
                txt = plz_item.text().strip()
                if txt:
                    plz_values.add(txt)
            if ort_item:
                txt = ort_item.text().strip()
                if txt:
                    ort_values.add(txt)

        self._reload_combo(combo_plz, sorted(plz_values, key=str.lower))
        self._reload_combo(combo_ort, sorted(ort_values, key=str.lower))

    def _reload_combo(self, combo, values):
        current_value = combo.currentData()
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("Alle", "")
        for value in values:
            combo.addItem(value, value)

        idx = combo.findData(current_value)
        combo.setCurrentIndex(idx if idx > -1 else 0)
        combo.blockSignals(False)

    # --- Helpers: Spalten erkennen und Adressausdruck bauen ---
    def _detect_kunden_columns(self, conn_wrapper):
        names = set()
        # --- KORREKTUR: Die Prüfung auf SQLite muss auf dem Wrapper stattfinden ---
        is_sqlite = getattr(conn_wrapper, "is_sqlite", False)
        conn = getattr(conn_wrapper, "raw", conn_wrapper) # Die rohe Verbindung für die Abfrage holen

        cur = conn.cursor()
        try:
            if is_sqlite:
                # PRAGMA für SQLite
                cur.execute(f"PRAGMA table_info(kunden)")
                # Spaltennamen aus dem Ergebnis extrahieren (Index 1)
                names = {r[1].lower() for r in cur.fetchall()}
            else:
                # information_schema für PostgreSQL
                cur.execute("""
                    SELECT column_name FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = 'kunden'
                """)
                names = {r[0].lower() for r in cur.fetchall()}
        except Exception:
            pass
        finally:
            cur.close()

        def pick(cands):
            for c in cands:
                if c in names:
                    return c
            return None
        return {
            "kundennr": pick(["kundennr", "id", "kunde_id"]) or "kundennr",
            "name":     pick(["name", "kundenname"]) or "name",
            "anrede":   pick(["anrede", "salutation"]) or "anrede",
            "email":    pick(["email", "e_mail", "mail"]) or "email",
            "firma":    pick(["firma", "company", "unternehmen"]) or "firma",
            "plz":      pick(["plz", "postleitzahl", "zip"]) or "plz",
            "strasse":  pick(["strasse", "straÃŸe", "street", "adresse", "address"]) or "strasse",
            "stadt":    pick(["stadt", "ort", "city", "ortschaft"]) or "stadt",
            "bemerkung": pick(["bemerkung", "notes"]) or "bemerkung",
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
        try:
            conn = get_db()
            cursor = conn.cursor()
            # --- KORREKTUR: Alphabetische Sortierung nach Namen hinzufügen ---
            cursor.execute("SELECT kundennr, anrede, name, firma, plz, strasse, stadt, email, bemerkung FROM kunden ORDER BY name ASC")
            self.kunden = cursor.fetchall()
            col_order = [0, 1, 2, 3, 4, 5, 6, 7, 8]
            norm_rows = []
            for r in self.kunden:
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
            self.table.setColumnHidden(0, True)


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


            try:
                header = self.table.horizontalHeader()
                for i in range(self.table.columnCount() - 1):
                    if not self.table.isColumnHidden(i):
                        header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
                header.setSectionResizeMode(self.table.columnCount() - 1, QHeaderView.Stretch)
            except Exception:
                pass

            self._populate_filter_values()

        finally:
             try:
                 conn.close()
             except Exception:
                 pass

    # ---------------- Async UI helpers (like Buchhaltung/Rechnungen) ----------------
    def get_row_id(self, row_index) -> int | None:
        try:
            if row_index < 0 or row_index >= self.table.rowCount():
                return None
            it = self.table.item(row_index, 0)
            if it is not None:
                d = it.data(Qt.UserRole)
                if isinstance(d, int):
                    return d
                txt = (it.text() or "").strip()
                if txt.lstrip("-").isdigit():
                    return int(txt)
        except Exception:
            pass
        return None

    def append_rows(self, rows):
        """Append rows (dict or sequence) into table. Newest-first by default (insert at top)."""
        try:
            if not rows:
                return
            # no loading label in KundenTab; append rows directly

            expected_cols = ["kundennr", "anrede", "name", "firma", "plz", "strasse", "stadt", "email", "bemerkung"]

            # --- ENTFERNT: Fehlerhafter Code, der das Layout überschreibt ---

            try:
                self.table.setSortingEnabled(False)
                self.table.setUpdatesEnabled(False)
            except Exception:
                pass

            for r in reversed(rows):
                if isinstance(r, dict):
                    vals = [r.get(c, "") for c in expected_cols]
                else:
                    seq = list(r)
                    if len(seq) < len(expected_cols):
                        seq += [""] * (len(expected_cols) - len(seq))
                    vals = seq[:len(expected_cols)]

                # insert row at top
                try:
                    self.table.insertRow(0)
                    idx = 0
                except Exception:
                    idx = self.table.rowCount()
                    self.table.setRowCount(idx + 1)

                for ci, val in enumerate(vals):
                    txt = "" if val is None else str(val)
                    item = QTableWidgetItem(txt)
                    if ci == 0:
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                        try:
                            item.setData(Qt.UserRole, int(val) if val is not None and str(val).strip() != "" else None)
                        except Exception:
                            item.setData(Qt.UserRole, None)
                    item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                    self.table.setItem(idx, ci, item)

                # keep internal cache consistent
                try:
                    rec = {
                        "kundennr": vals[0],
                        "anrede": vals[1],
                        "name": vals[2],
                        "firma": vals[3],
                        "plz": vals[4],
                        "strasse": vals[5],
                        "stadt": vals[6],
                        "email": vals[7],
                        "bemerkung": vals[8]
                    }
                except Exception:
                    rec = {}
                try:
                    self.kunden.insert(0, rec)
                except Exception:
                    self.kunden = [rec] + getattr(self, "kunden", [])

            try:
                self.table.setUpdatesEnabled(True)
                self.table.setSortingEnabled(True)

            except Exception:
                pass

            self._populate_filter_values()

        except Exception as e:
            print(f"[DBG] KundenTab.append_rows error: {e}", flush=True)

    def load_finished(self):
        """Called when loader finished. No UI placeholder for this tab."""
        return

    # ------------------------------------------------------------------------
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
            conn = get_db()
            try:
                # --- KORREKTUR: Den Wrapper übergeben, nicht conn.raw ---
                cols = self._detect_kunden_columns(conn)
                field_map = {
                    "anrede": cols.get("anrede"), "name": cols.get("name"), "firma": cols.get("firma"),
                    "plz": cols.get("plz"), "strasse": cols.get("strasse"), "stadt": cols.get("stadt"),
                    "email": cols.get("email"), "bemerkung": cols.get("bemerkung"),
                }
                # --- KORREKTUR: Die Bedingung wurde geändert ---
                insert_cols = [dbcol for key, dbcol in field_map.items() if dbcol and key in d]
                insert_vals = [d.get(key) for key, dbcol in field_map.items() if dbcol and key in d]

                if insert_cols:
                    placeholders = ", ".join(["%s"] * len(insert_cols))
                    sql = f"INSERT INTO kunden ({', '.join(insert_cols)}) VALUES ({placeholders})"
                    
                    cur = conn.cursor()
                    cur.execute(sql, insert_vals)
                    conn.commit()
            finally:
                conn.close()

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
            conn = get_db()
            try:
                # --- KORREKTUR: Den Wrapper übergeben, nicht conn.raw ---
                cols = self._detect_kunden_columns(conn)
                field_map = {
                    "anrede": cols.get("anrede"), "name": cols.get("name"), "plz": cols.get("plz"),
                    "strasse": cols.get("strasse"), "stadt": cols.get("stadt"), "email": cols.get("email"),
                    "firma": cols.get("firma"), "bemerkung": cols.get("bemerkung"),
                }
                sets, params = [], []
                for key, dbcol in field_map.items():
                    if dbcol is not None and key in d:
                        sets.append(f"{dbcol}=%s")
                        params.append(d.get(key, ""))
                
                if sets:
                    sql = f"UPDATE kunden SET {', '.join(sets)} WHERE {cols['kundennr']}=%s"
                    params.append(rid)
                    
                    cur = conn.cursor()
                    cur.execute(sql, tuple(params))
                    conn.commit()
            finally:
                conn.close()

            self.lade_kunden()
            self.kunde_aktualisiert.emit()

    def kunde_loeschen(self):
        rid = self._get_selected_id()
        if rid is None:
            QMessageBox.warning(self, "Keine Auswahl", "Bitte zuerst einen Kunden auswählen.")
            return
        if QMessageBox.question(self, "Löschen", "Kunde wirklich löschen?") != QMessageBox.Yes:
            return
        
        conn = get_db()
        try:
            cols = self._detect_kunden_columns(conn.raw)
            # KORREKTUR: Immer %s verwenden
            sql = f"DELETE FROM kunden WHERE {cols['kundennr']}=%s"
            
            cur = conn.cursor()
            cur.execute(sql, (rid,))
            conn.commit()
        finally:
            conn.close()

        self.lade_kunden()
        self.kunde_aktualisiert.emit()

