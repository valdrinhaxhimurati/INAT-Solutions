from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QDialog, QMessageBox, QLineEdit, QLabel, QPushButton, QSizePolicy,
    QFrame, QAbstractItemView, QHeaderView
)
from db_connection import get_db, dict_cursor_factory
import sqlite3
import webbrowser
from PyQt5.QtWidgets import QToolButton
from PyQt5.QtCore import Qt, pyqtSignal
from i18n import _
from gui.modern_widgets import (
    COLORS, FONT_SIZES, SPACING, BORDER_RADIUS,
    get_table_stylesheet, get_button_primary_stylesheet,
    get_button_secondary_stylesheet, get_input_stylesheet
)

class LieferantenTab(QWidget):
    lieferant_aktualisiert = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._all_rows = []
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Toolbar
        toolbar = QFrame()
        toolbar.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border-bottom: 1px solid {COLORS['border']};
            }}
        """)
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(SPACING['xl'], SPACING['lg'], SPACING['xl'], SPACING['lg'])
        toolbar_layout.setSpacing(SPACING['md'])

        # Buttons
        self.btn_hinzufuegen = QPushButton(_("+ Lieferant hinzufügen"))
        self.btn_hinzufuegen.setStyleSheet(get_button_primary_stylesheet())
        self.btn_hinzufuegen.setCursor(Qt.PointingHandCursor)
        toolbar_layout.addWidget(self.btn_hinzufuegen)

        for btn_text, btn_name in [
            (_("Bearbeiten"), "btn_bearbeiten"),
            (_("Löschen"), "btn_loeschen"),
            (_("Link öffnen"), "btn_portal"),
        ]:
            btn = QPushButton(btn_text)
            btn.setStyleSheet(get_button_secondary_stylesheet())
            btn.setCursor(Qt.PointingHandCursor)
            setattr(self, btn_name, btn)
            toolbar_layout.addWidget(btn)

        # Suchfeld - volle Breite
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(_("🔍 Suchen..."))
        self.search_input.setStyleSheet(get_input_stylesheet())
        toolbar_layout.addWidget(self.search_input, 1)  # stretch=1 für volle Breite

        main_layout.addWidget(toolbar)

        # Content
        content = QWidget()
        content.setStyleSheet(f"background-color: {COLORS['background']};")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(SPACING['xl'], SPACING['xl'], SPACING['xl'], SPACING['xl'])
        content_layout.setSpacing(16)

        # Tabellen-Karte
        table_card = QFrame()
        table_card.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: {BORDER_RADIUS['lg']}px;
            }}
        """)
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget()
        self.table.setStyleSheet(get_table_stylesheet())
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.table.setSortingEnabled(True)
        self.table.verticalHeader().setVisible(False)
        table_layout.addWidget(self.table)

        content_layout.addWidget(table_card, stretch=1)
        main_layout.addWidget(content, stretch=1)

        # Verbindungen
        self.btn_hinzufuegen.clicked.connect(self.lieferant_hinzufuegen)
        self.btn_bearbeiten.clicked.connect(self.lieferant_bearbeiten)
        self.btn_loeschen.clicked.connect(self.lieferant_loeschen)
        self.btn_portal.clicked.connect(self.portal_link_oeffnen)
        self.search_input.textChanged.connect(self._filter_table)

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
            print(_("Fehler beim Laden der Lieferanten (DB):"), e)
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
                    rd_lower.get("name"),
                    rd_lower.get("adresse"),
                    rd_lower.get("kontaktperson"),
                    rd_lower.get("email"),
                    rd_lower.get("telefon"),
                    rd_lower.get("portal_link"),
                    rd_lower.get("notizen")
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
                    m.get("name"),
                    m.get("adresse"),
                    m.get("kontaktperson"),
                    m.get("email"),
                    m.get("telefon"),
                    m.get("portal_link"),
                    m.get("notizen")
                ))
            else:
                while len(seq) < 8:
                    seq.append(None)
                daten.append((seq[0], seq[1], seq[2], seq[3], seq[4], seq[5], seq[6], seq[7]))

        self._all_rows = daten
        self._filter_table()

    def _filter_table(self):
        """Filtert die Tabelle basierend auf dem Suchtext."""
        rows = list(self._all_rows)
        query = self.search_input.text().strip().lower()

        filtered = []
        for row in rows:
            if query:
                # Suche in allen Feldern
                haystacks = [str(val or "") for val in row[1:]]
                if not any(query in h.lower() for h in haystacks):
                    continue
            filtered.append(row)

        self._populate_table(filtered)

    def _populate_table(self, daten):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(daten))
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([_("ID"), _("Name"), _("Adresse"), _("Kontaktperson"), _("E-Mail"), _("Telefon"), _("Portal-Link"), _("Notizen")])
        self.table.setColumnHidden(0, True)
        self.table.setColumnWidth(0, 60)
        self.table.setColumnWidth(1, 180)
        self.table.setColumnWidth(2, 200)
        self.table.setColumnWidth(3, 150)
        self.table.setColumnWidth(4, 180)
        self.table.setColumnWidth(5, 120)
        self.table.setColumnWidth(6, 200)
        self.table.setColumnWidth(7, 200)

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
                INSERT INTO lieferanten (name, adresse, kontaktperson, email, telefon, portal_link, notizen)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (daten["name"], daten["adresse"], daten["kontaktperson"], daten["email"], daten["telefon"], daten["portal_link"], daten["notizen"]))
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
            "id": int(self.table.item(zeile, 0).text()) if self.table.item(zeile, 0) else 0,
            "name": self.table.item(zeile, 1).text() if self.table.item(zeile, 1) else "",
            "adresse": self.table.item(zeile, 2).text() if self.table.item(zeile, 2) else "",
            "kontaktperson": self.table.item(zeile, 3).text() if self.table.item(zeile, 3) else "",
            "email": self.table.item(zeile, 4).text() if self.table.item(zeile, 4) else "",
            "telefon": self.table.item(zeile, 5).text() if self.table.item(zeile, 5) else "",
            "portal_link": self.table.item(zeile, 6).text() if self.table.item(zeile, 6) else "",
            "notizen": self.table.item(zeile, 7).text() if self.table.item(zeile, 7) else ""
        }
        dialog = LieferantenDialog(self, lieferant=lieferant)
        if dialog.exec_() == QDialog.Accepted:
            daten = dialog.get_daten()
            conn = get_db()
            cursor = conn.cursor(cursor_factory=dict_cursor_factory(conn))
            cursor.execute("""
                UPDATE lieferanten
                SET name= %s, adresse= %s, kontaktperson= %s, email= %s, telefon= %s, portal_link= %s, notizen= %s
                WHERE lieferantnr= %s
            """, (daten["name"], daten["adresse"], daten["kontaktperson"], daten["email"], daten["telefon"], daten["portal_link"], daten["notizen"], lieferant["id"]))
            conn.commit()
            conn.close()
            self.lade_lieferanten()
            self.lieferant_aktualisiert.emit()

    def lieferant_loeschen(self):
        sel = self.table.selectionModel().selectedRows()
        if not sel:
            return
        ids = []
        for idx in sel:
            try:
                it = self.table.item(idx.row(), 0)
                if it is None:
                    continue
                id_val = it.data(Qt.UserRole)
                if id_val is None:
                    txt = it.text().strip()
                    try:
                        id_val = int(txt) if txt != "" else None
                    except Exception:
                        id_val = None
                if id_val is not None:
                    ids.append(int(id_val))
            except Exception:
                pass
        if not ids:
            QMessageBox.warning(self, _("Keine Auswahl"), _("Keine gültigen IDs in Auswahl gefunden."))
            return
        resp = QMessageBox.question(self, _("Löschen bestätigen"), _("Soll(en) die ausgewählten {0} Lieferant(en) wirklich gelöscht werden?").format(len(ids)), QMessageBox.Yes | QMessageBox.No)
        if resp != QMessageBox.Yes:
            return

        try:
            conn = get_db()
            try:
                placeholders = ','.join(['%s'] * len(ids))
                with conn.cursor() as cur:
                    cur.execute(f"DELETE FROM public.lieferanten WHERE id IN ({placeholders})", tuple(ids))
                conn.commit()
            except Exception:
                # fallback to sqlite style
                placeholders = ','.join(['?'] * len(ids))
                with conn.cursor() as cur:
                    cur.execute(f"DELETE FROM lieferanten WHERE id IN ({placeholders})", tuple(ids))
                conn.commit()
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
        link_item = self.table.item(zeile, 6)  # Portal-Link ist Spalte 6
        link = link_item.text() if link_item else ""
        if link:
            webbrowser.open(link)
        else:
            QMessageBox.information(self, _("Kein Link"), _("Kein Link hinterlegt."))

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
                while len(row) < 8:
                    row.append("")
                normalized.append(tuple(row[:8]))
            self._all_rows = list(normalized) + self._all_rows
            self._filter_table()
        except Exception as e:
            print(f"[DBG] LieferantenTab.append_rows error: {e}", flush=True)

    def load_finished(self):
        self.table.resizeColumnsToContents()



