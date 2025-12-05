# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QDialog, QMessageBox, QToolButton,
    QFrame, QPushButton, QLineEdit, QAbstractItemView
)
from PyQt5.QtCore import Qt
from db_connection import get_db
from i18n import _
from gui.modern_widgets import (
    COLORS, FONT_SIZES, SPACING, BORDER_RADIUS,
    get_table_stylesheet, get_button_primary_stylesheet,
    get_button_secondary_stylesheet, get_input_stylesheet
)

class DienstleistungenTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_rows = []
        self.init_ui()
        self._ensure_table()
        self.lade_dienstleistungen()

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
        self.btn_hinzufuegen = QPushButton(_("+ Dienstleistung hinzufügen"))
        self.btn_hinzufuegen.setStyleSheet(get_button_primary_stylesheet())
        self.btn_hinzufuegen.setCursor(Qt.PointingHandCursor)
        toolbar_layout.addWidget(self.btn_hinzufuegen)

        for btn_text, btn_name in [
            (_("Bearbeiten"), "btn_bearbeiten"),
            (_("Löschen"), "btn_loeschen"),
        ]:
            btn = QPushButton(btn_text)
            btn.setStyleSheet(get_button_secondary_stylesheet())
            btn.setCursor(Qt.PointingHandCursor)
            setattr(self, btn_name, btn)
            toolbar_layout.addWidget(btn)

        toolbar_layout.addStretch()

        # Suchfeld
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(_("🔍 Suchen..."))
        self.search_input.setStyleSheet(get_input_stylesheet() + "QLineEdit { min-width: 200px; max-width: 280px; }")
        self.search_input.textChanged.connect(self._filter_table)
        toolbar_layout.addWidget(self.search_input)

        main_layout.addWidget(toolbar)

        # Content
        content = QWidget()
        content.setStyleSheet(f"background-color: {COLORS['background']};")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(SPACING['xl'], SPACING['xl'], SPACING['xl'], SPACING['xl'])
        content_layout.setSpacing(SPACING['lg'])

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
        self.table.verticalHeader().setVisible(False)
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([_("ID"), _("Name"), _("Beschreibung"), _("Preis"), _("Einheit"), _("Währung"), _("Bemerkung")])
        self.table.setColumnHidden(0, True)
        self.table.setColumnWidth(1, 200)
        self.table.setColumnWidth(2, 300)
        self.table.setColumnWidth(3, 100)
        self.table.setColumnWidth(4, 100)
        self.table.setColumnWidth(5, 80)
        self.table.setColumnWidth(6, 200)
        table_layout.addWidget(self.table)

        content_layout.addWidget(table_card, stretch=1)
        main_layout.addWidget(content, stretch=1)

        # Verbindungen
        self.btn_hinzufuegen.clicked.connect(self.dienstleistung_hinzufuegen)
        self.btn_bearbeiten.clicked.connect(self.dienstleistung_bearbeiten)
        self.btn_loeschen.clicked.connect(self.dienstleistung_loeschen)

    def _filter_table(self):
        query = self.search_input.text().strip().lower()
        for row in range(self.table.rowCount()):
            match = False
            for col in range(1, self.table.columnCount()):
                item = self.table.item(row, col)
                if item and query in item.text().lower():
                    match = True
                    break
            self.table.setRowHidden(row, not match if query else False)

    def _ensure_table(self):
        conn = get_db()
        is_sqlite = getattr(conn, "is_sqlite", False) or getattr(conn, "is_sqlite_conn", False)
        if is_sqlite:
            sql = """
            CREATE TABLE IF NOT EXISTS dienstleistungen (
                dienstleistung_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                beschreibung TEXT,
                preis NUMERIC,
                einheit TEXT,
                waehrung TEXT,
                bemerkung TEXT
            )
            """
        else:
            sql = """
            CREATE TABLE IF NOT EXISTS dienstleistungen (
                dienstleistung_id BIGSERIAL PRIMARY KEY,
                name TEXT,
                beschreibung TEXT,
                preis NUMERIC,
                einheit TEXT,
                waehrung TEXT,
                bemerkung TEXT
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

    def lade_dienstleistungen(self):
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT dienstleistung_id, name, beschreibung, preis, einheit, waehrung, bemerkung FROM dienstleistungen ORDER BY name")
            rows = cur.fetchall()
            conn.close()
        except Exception as e:
            QMessageBox.warning(self, _("Fehler"), _("Fehler beim Laden: {}").format(e))
            return

        self.table.setRowCount(len(rows))
        for r_idx, row in enumerate(rows):
            for c_idx, val in enumerate(row):
                txt = "" if val is None else str(val)
                item = QTableWidgetItem(txt)
                self.table.setItem(r_idx, c_idx, item)

    def dienstleistung_hinzufuegen(self):
        from gui.dienstleistungen_dialog import DienstleistungenDialog
        dialog = DienstleistungenDialog(self, dienstleistung=None)
        if dialog.exec_() == QDialog.Accepted:
            daten = dialog.get_daten()
            try:
                conn = get_db()
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO dienstleistungen (name, beschreibung, preis, einheit, waehrung, bemerkung)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (daten["name"], daten["beschreibung"], daten["preis"], daten["einheit"], daten["waehrung"], daten["bemerkung"]))
                conn.commit()
                conn.close()
                self.lade_dienstleistungen()
            except Exception as e:
                QMessageBox.warning(self, _("Fehler"), _("Fehler beim Speichern: {}").format(e))

    def dienstleistung_bearbeiten(self):
        z = self.table.currentRow()
        if z < 0:
            return
        dienstleistung_id = int(self.table.item(z, 0).text())
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT dienstleistung_id, name, beschreibung, preis, einheit, waehrung, bemerkung FROM dienstleistungen WHERE dienstleistung_id = %s", (dienstleistung_id,))
            row = cur.fetchone()
            conn.close()
        except Exception as e:
            QMessageBox.warning(self, _("Fehler"), _("Fehler beim Laden: {}").format(e))
            return
        if not row:
            return
        dienstleistung = {
            "dienstleistung_id": row[0],
            "name": row[1],
            "beschreibung": row[2],
            "preis": row[3],
            "einheit": row[4],
            "waehrung": row[5],
            "bemerkung": row[6]
        }
        from gui.dienstleistungen_dialog import DienstleistungenDialog
        dialog = DienstleistungenDialog(self, dienstleistung=dienstleistung)
        if dialog.exec_() == QDialog.Accepted:
            daten = dialog.get_daten()
            try:
                conn = get_db()
                cur = conn.cursor()
                cur.execute("""
                    UPDATE dienstleistungen
                    SET name=%s, beschreibung=%s, preis=%s, einheit=%s, waehrung=%s, bemerkung=%s
                    WHERE dienstleistung_id=%s
                """, (daten["name"], daten["beschreibung"], daten["preis"], daten["einheit"], daten["waehrung"], daten["bemerkung"], dienstleistung["dienstleistung_id"]))
                conn.commit()
                conn.close()
                self.lade_dienstleistungen()
            except Exception as e:
                QMessageBox.warning(self, _("Fehler"), _("Fehler beim Speichern: {}").format(e))

    def dienstleistung_loeschen(self):
        # bulk delete support
        sel = self.table.selectionModel().selectedRows()
        if not sel:
            return
        ids = []
        for idx in sel:
            try:
                ids.append(int(self.table.item(idx.row(), 0).text()))
            except Exception:
                pass
        if not ids:
            return
        resp = QMessageBox.question(self, _("Löschen bestätigen"), _("Soll(en) die ausgewählten {0} Dienstleistung(en) wirklich gelöscht werden?").format(len(ids)), QMessageBox.Yes | QMessageBox.No)
        if resp != QMessageBox.Yes:
            return
        try:
            conn = get_db()
            cur = conn.cursor()
            try:
                placeholders = ','.join(['%s'] * len(ids))
                cur.execute(f"DELETE FROM dienstleistungen WHERE dienstleistung_id IN ({placeholders})", tuple(ids))
            except Exception:
                placeholders = ','.join(['?'] * len(ids))
                cur.execute(f"DELETE FROM dienstleistungen WHERE dienstleistung_id IN ({placeholders})", tuple(ids))
            conn.commit()
            conn.close()
            self.lade_dienstleistungen()
        except Exception as e:
            QMessageBox.warning(self, _("Fehler"), _("Fehler beim Löschen: {}").format(e))
