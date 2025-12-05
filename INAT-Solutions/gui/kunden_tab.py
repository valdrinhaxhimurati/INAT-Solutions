# -*- coding: utf-8 -*-
"""
Kunden-Tab mit modernem Layout
- Liste links mit Kunden als Karten
- Details rechts
- Moderne Toolbar
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QSizePolicy, QDialog, QMessageBox,
    QSplitter, QLineEdit, QStackedWidget
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from db_connection import get_db
from gui.kunden_dialog import KundenDialog
from gui.modern_widgets import (
    ModernCard, ModernToolbar, ListItem, AvatarLabel, 
    StatusBadge, COLORS, FONT_SIZES, SPACING, BORDER_RADIUS,
    get_button_primary_stylesheet, get_button_secondary_stylesheet, get_input_stylesheet
)
from i18n import _


class KundeDetailPanel(QFrame):
    """Detail-Ansicht für einen Kunden (rechte Seite)."""
    
    bearbeiten_clicked = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("detailPanel")
        self.setStyleSheet(f"""
            #detailPanel {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border_light']};
                border-radius: 12px;
            }}
        """)
        
        self._current_kunde = None
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # Platzhalter wenn nichts ausgewählt
        self.placeholder = QLabel(_("Wählen Sie einen Kunden aus der Liste"))
        self.placeholder.setAlignment(Qt.AlignCenter)
        self.placeholder.setStyleSheet(f"""
            color: {COLORS['text_muted']};
            font-size: {FONT_SIZES['body']}px;
            padding: 40px;
        """)
        layout.addWidget(self.placeholder)
        
        # Detail-Container
        self.detail_container = QWidget()
        self.detail_container.hide()
        detail_layout = QVBoxLayout(self.detail_container)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_layout.setSpacing(20)
        
        # Header mit Avatar und Name
        header = QHBoxLayout()
        header.setSpacing(16)
        
        self.avatar = AvatarLabel("", 64)
        header.addWidget(self.avatar)
        
        name_layout = QVBoxLayout()
        name_layout.setSpacing(4)
        
        self.name_label = QLabel()
        self.name_label.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            font-size: {FONT_SIZES['h2']}px;
            font-weight: 700;
        """)
        name_layout.addWidget(self.name_label)
        
        self.firma_label = QLabel()
        self.firma_label.setStyleSheet(f"""
            color: {COLORS['text_secondary']};
            font-size: {FONT_SIZES['body']}px;
        """)
        name_layout.addWidget(self.firma_label)
        
        header.addLayout(name_layout)
        header.addStretch()
        
        # Bearbeiten Button
        self.btn_edit = QPushButton(_("Bearbeiten"))
        self.btn_edit.setStyleSheet(get_button_primary_stylesheet())
        self.btn_edit.setCursor(Qt.PointingHandCursor)
        self.btn_edit.clicked.connect(self._on_edit)
        header.addWidget(self.btn_edit)
        
        detail_layout.addLayout(header)
        
        # Statistik-Karten
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(12)
        
        self.stat_rechnungen = self._create_stat_widget(_("Rechnungen"), "0")
        self.stat_umsatz = self._create_stat_widget(_("Umsatz gesamt"), "CHF 0")
        self.stat_offen = self._create_stat_widget(_("Offen"), "CHF 0", is_warning=True)
        
        stats_layout.addWidget(self.stat_rechnungen)
        stats_layout.addWidget(self.stat_umsatz)
        stats_layout.addWidget(self.stat_offen)
        
        detail_layout.addLayout(stats_layout)
        
        # Kontakt-Infos
        contact_label = QLabel(_("Kontakt"))
        contact_label.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            font-size: {FONT_SIZES['subtitle']}px;
            font-weight: 600;
            margin-top: 8px;
        """)
        detail_layout.addWidget(contact_label)
        
        self.contact_grid = QFrame()
        self.contact_grid.setStyleSheet(f"""
            background-color: {COLORS['background']};
            border-radius: 10px;
            padding: 16px;
        """)
        contact_grid_layout = QVBoxLayout(self.contact_grid)
        contact_grid_layout.setSpacing(12)
        
        self.email_row = self._create_info_row("📧", _("E-Mail"), "")
        self.phone_row = self._create_info_row("📞", _("Telefon"), "")
        self.address_row = self._create_info_row("📍", _("Adresse"), "")
        
        contact_grid_layout.addWidget(self.email_row)
        contact_grid_layout.addWidget(self.phone_row)
        contact_grid_layout.addWidget(self.address_row)
        
        detail_layout.addWidget(self.contact_grid)
        
        # Bemerkung
        self.bemerkung_label = QLabel(_("Bemerkung"))
        self.bemerkung_label.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            font-size: {FONT_SIZES['subtitle']}px;
            font-weight: 600;
            margin-top: 8px;
        """)
        detail_layout.addWidget(self.bemerkung_label)
        
        self.bemerkung_text = QLabel()
        self.bemerkung_text.setWordWrap(True)
        self.bemerkung_text.setStyleSheet(f"""
            background-color: {COLORS['background']};
            border-radius: {BORDER_RADIUS['md']}px;
            padding: {SPACING['lg']}px;
            color: {COLORS['text_secondary']};
            font-size: {FONT_SIZES['small']}px;
        """)
        detail_layout.addWidget(self.bemerkung_text)
        
        detail_layout.addStretch()
        
        layout.addWidget(self.detail_container)
    
    def _create_stat_widget(self, title: str, value: str, is_warning: bool = False) -> QFrame:
        widget = QFrame()
        widget.setStyleSheet(f"""
            background-color: {COLORS['background']};
            border-radius: 10px;
            padding: 16px;
        """)
        
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(4)
        
        value_label = QLabel(value)
        value_color = COLORS['warning'] if is_warning else COLORS['primary']
        value_label.setStyleSheet(f"""
            color: {value_color};
            font-size: {FONT_SIZES['h3']}px;
            font-weight: 700;
        """)
        value_label.setObjectName("value")
        layout.addWidget(value_label)
        
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            color: {COLORS['text_secondary']};
            font-size: {FONT_SIZES['caption']}px;
        """)
        layout.addWidget(title_label)
        
        return widget
    
    def _create_info_row(self, icon: str, label: str, value: str) -> QFrame:
        row = QFrame()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        icon_label = QLabel(icon)
        icon_label.setStyleSheet(f"font-size: {FONT_SIZES['subtitle']}px;")
        layout.addWidget(icon_label)
        
        label_widget = QLabel(label)
        label_widget.setStyleSheet(f"""
            color: {COLORS['text_secondary']};
            font-size: {FONT_SIZES['small']}px;
            min-width: 80px;
        """)
        layout.addWidget(label_widget)
        
        value_label = QLabel(value)
        value_label.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            font-size: {FONT_SIZES['small']}px;
        """)
        value_label.setObjectName("value")
        layout.addWidget(value_label)
        layout.addStretch()
        
        return row
    
    def show_kunde(self, kunde: dict):
        """Zeigt die Details eines Kunden an."""
        self._current_kunde = kunde
        self.placeholder.hide()
        self.detail_container.show()
        
        name = kunde.get("name", "")
        firma = kunde.get("firma", "")
        
        self.avatar.set_name(name or firma or "?")
        self.name_label.setText(name or _("Unbekannt"))
        self.firma_label.setText(firma or "")
        
        # Kontakt-Infos aktualisieren
        email = kunde.get("email", "")
        self.email_row.findChild(QLabel, "value").setText(email or "-")
        
        # Telefon (falls vorhanden)
        telefon = kunde.get("telefon", kunde.get("phone", ""))
        self.phone_row.findChild(QLabel, "value").setText(telefon or "-")
        
        # Adresse zusammenbauen
        strasse = kunde.get("strasse", "")
        plz = kunde.get("plz", "")
        stadt = kunde.get("stadt", "")
        adresse_parts = [strasse, f"{plz} {stadt}".strip()]
        adresse = ", ".join(p for p in adresse_parts if p)
        self.address_row.findChild(QLabel, "value").setText(adresse or "-")
        
        # Bemerkung
        bemerkung = kunde.get("bemerkung", "")
        if bemerkung:
            self.bemerkung_label.show()
            self.bemerkung_text.show()
            self.bemerkung_text.setText(bemerkung)
        else:
            self.bemerkung_label.hide()
            self.bemerkung_text.hide()
        
        # Statistiken laden
        self._load_stats(kunde.get("kundennr"))
    
    def _load_stats(self, kunde_id):
        """Lädt Statistiken für den Kunden."""
        if not kunde_id:
            return
        
        try:
            conn = get_db()
            cur = conn.cursor()
            
            # Anzahl Rechnungen und Umsatz (vereinfacht)
            # In einer vollständigen Implementierung würde man hier die echten Daten laden
            cur.execute("""
                SELECT COUNT(*), COALESCE(SUM(
                    CASE WHEN mwst IS NOT NULL THEN mwst ELSE 0 END
                ), 0)
                FROM rechnungen 
                WHERE kunde LIKE %s OR firma LIKE %s
            """, (f"%{kunde_id}%", f"%{kunde_id}%"))
            
            result = cur.fetchone()
            if result:
                anzahl = result[0] or 0
                # Umsatz müsste aus Positionen berechnet werden
                self.stat_rechnungen.findChild(QLabel, "value").setText(str(anzahl))
            
            cur.close()
            conn.close()
        except Exception as e:
            print(f"[DBG] Fehler beim Laden der Kundenstatistiken: {e}")
    
    def _on_edit(self):
        if self._current_kunde:
            self.bearbeiten_clicked.emit(self._current_kunde)
    
    def clear(self):
        """Setzt die Anzeige zurück."""
        self._current_kunde = None
        self.placeholder.show()
        self.detail_container.hide()


class KundenTab(QWidget):
    """Kunden-Tab mit Sidebar-Liste und Detail-Ansicht."""
    
    kunde_aktualisiert = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._kunden = []
        self._list_items = []
        self._selected_kunde = None
        
        self._setup_ui()
        self._ensure_table()
    
    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Toolbar
        self.toolbar = ModernToolbar()
        self.btn_add = self.toolbar.add_button(_("+ Neuer Kunde"), primary=True)
        self.btn_add.clicked.connect(self.kunde_hinzufuegen)
        
        self.btn_delete = self.toolbar.add_button(_("Löschen"))
        self.btn_delete.clicked.connect(self.kunde_loeschen)
        
        self.toolbar.search_changed.connect(self._filter_list)
        
        main_layout.addWidget(self.toolbar)
        
        # Content-Bereich
        content = QWidget()
        content.setStyleSheet(f"background-color: {COLORS['background']};")
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.setSpacing(24)
        
        # Linke Seite: Kundenliste
        list_container = QFrame()
        list_container.setObjectName("listContainer")
        list_container.setStyleSheet(f"""
            #listContainer {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border_light']};
                border-radius: 12px;
            }}
        """)
        list_container.setFixedWidth(380)
        
        list_layout = QVBoxLayout(list_container)
        list_layout.setContentsMargins(16, 16, 16, 16)
        list_layout.setSpacing(8)
        
        # Header
        list_header = QLabel(_("Kunden"))
        list_header.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            font-size: {FONT_SIZES['subtitle']}px;
            font-weight: 600;
            padding: 8px 0;
        """)
        list_layout.addWidget(list_header)
        
        self.count_label = QLabel("0 " + _("Kunden"))
        self.count_label.setStyleSheet(f"""
            color: {COLORS['text_muted']};
            font-size: {FONT_SIZES['caption']}px;
        """)
        list_layout.addWidget(self.count_label)
        
        # Scrollbare Liste
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollArea > QWidget > QWidget {
                background: transparent;
            }
        """)
        
        self.list_widget = QWidget()
        self.list_layout = QVBoxLayout(self.list_widget)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(8)
        self.list_layout.addStretch()
        
        scroll.setWidget(self.list_widget)
        list_layout.addWidget(scroll)
        
        content_layout.addWidget(list_container)
        
        # Rechte Seite: Details
        self.detail_panel = KundeDetailPanel()
        self.detail_panel.bearbeiten_clicked.connect(self._on_edit_kunde)
        content_layout.addWidget(self.detail_panel, stretch=1)
        
        main_layout.addWidget(content, stretch=1)
    
    def _ensure_table(self):
        """Stellt sicher dass die Tabelle existiert."""
        try:
            conn = get_db()
            is_sqlite = getattr(conn, "is_sqlite", False)
            cur = conn.cursor()
            
            if is_sqlite:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS kunden (
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
            
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"[DBG] _ensure_table error: {e}")
    
    def lade_kunden(self):
        """Lädt alle Kunden aus der Datenbank."""
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
                SELECT kundennr, anrede, name, firma, plz, strasse, stadt, email, bemerkung 
                FROM kunden ORDER BY name ASC
            """)
            rows = cur.fetchall()
            cur.close()
            conn.close()
            
            self._kunden = []
            for row in rows:
                if isinstance(row, dict):
                    self._kunden.append(row)
                else:
                    self._kunden.append({
                        "kundennr": row[0],
                        "anrede": row[1],
                        "name": row[2],
                        "firma": row[3],
                        "plz": row[4],
                        "strasse": row[5],
                        "stadt": row[6],
                        "email": row[7],
                        "bemerkung": row[8]
                    })
            
            self._update_list()
            
        except Exception as e:
            print(f"[DBG] lade_kunden error: {e}")
    
    def _update_list(self):
        """Aktualisiert die Kunden-Liste."""
        # Alte Items entfernen
        for item in self._list_items:
            item.deleteLater()
        self._list_items.clear()
        
        # Neue Items erstellen
        for kunde in self._kunden:
            item = ListItem()
            name = kunde.get("name", "")
            firma = kunde.get("firma", "")
            stadt = kunde.get("stadt", "")
            plz = kunde.get("plz", "")
            
            display_name = name or firma or _("Unbekannt")
            subtitle = f"{plz} {stadt}".strip() if plz or stadt else ""
            
            item.set_content(
                avatar_name=display_name,
                title=display_name,
                subtitle=subtitle
            )
            
            item.clicked.connect(lambda k=kunde: self._on_kunde_selected(k))
            
            # Vor dem Stretch einfügen
            self.list_layout.insertWidget(self.list_layout.count() - 1, item)
            self._list_items.append(item)
        
        self.count_label.setText(f"{len(self._kunden)} " + _("Kunden"))
    
    def _filter_list(self, search_text: str):
        """Filtert die Liste nach Suchbegriff."""
        search = search_text.lower().strip()
        
        for i, item in enumerate(self._list_items):
            if i >= len(self._kunden):
                continue
            
            kunde = self._kunden[i]
            name = (kunde.get("name", "") or "").lower()
            firma = (kunde.get("firma", "") or "").lower()
            stadt = (kunde.get("stadt", "") or "").lower()
            email = (kunde.get("email", "") or "").lower()
            
            matches = (
                search in name or
                search in firma or
                search in stadt or
                search in email or
                not search
            )
            
            item.setVisible(matches)
    
    def _on_kunde_selected(self, kunde: dict):
        """Wird aufgerufen wenn ein Kunde ausgewählt wird."""
        self._selected_kunde = kunde
        self.detail_panel.show_kunde(kunde)
    
    def _on_edit_kunde(self, kunde: dict):
        """Öffnet den Bearbeiten-Dialog."""
        dlg = KundenDialog(self, kunde=kunde)
        if dlg.exec_() == QDialog.Accepted:
            d = dlg.get_daten()
            self._save_kunde(kunde.get("kundennr"), d)
            self.lade_kunden()
            self.kunde_aktualisiert.emit()
    
    def kunde_hinzufuegen(self):
        """Öffnet Dialog zum Hinzufügen eines Kunden."""
        dlg = KundenDialog(self, kunde=None)
        if dlg.exec_() == QDialog.Accepted:
            d = dlg.get_daten()
            self._insert_kunde(d)
            self.lade_kunden()
            self.kunde_aktualisiert.emit()
    
    def _insert_kunde(self, data: dict):
        """Fügt einen neuen Kunden ein."""
        try:
            conn = get_db()
            cur = conn.cursor()
            
            cur.execute("""
                INSERT INTO kunden (anrede, name, firma, plz, strasse, stadt, email, bemerkung)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                data.get("anrede", ""),
                data.get("name", ""),
                data.get("firma", ""),
                data.get("plz", ""),
                data.get("strasse", ""),
                data.get("stadt", ""),
                data.get("email", ""),
                data.get("bemerkung", "")
            ))
            
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"[DBG] _insert_kunde error: {e}")
    
    def _save_kunde(self, kunde_id: int, data: dict):
        """Speichert Änderungen an einem Kunden."""
        try:
            conn = get_db()
            cur = conn.cursor()
            
            cur.execute("""
                UPDATE kunden SET
                    anrede = %s, name = %s, firma = %s, plz = %s,
                    strasse = %s, stadt = %s, email = %s, bemerkung = %s
                WHERE kundennr = %s
            """, (
                data.get("anrede", ""),
                data.get("name", ""),
                data.get("firma", ""),
                data.get("plz", ""),
                data.get("strasse", ""),
                data.get("stadt", ""),
                data.get("email", ""),
                data.get("bemerkung", ""),
                kunde_id
            ))
            
            conn.commit()
            cur.close()
            conn.close()
            
            # Detail-Panel aktualisieren
            updated = dict(data)
            updated["kundennr"] = kunde_id
            self.detail_panel.show_kunde(updated)
            
        except Exception as e:
            print(f"[DBG] _save_kunde error: {e}")
    
    def kunde_loeschen(self):
        """Löscht den ausgewählten Kunden."""
        if not self._selected_kunde:
            QMessageBox.warning(self, _("Keine Auswahl"), _("Bitte zuerst einen Kunden auswählen."))
            return
        
        kunde_id = self._selected_kunde.get("kundennr")
        name = self._selected_kunde.get("name", "")
        
        if QMessageBox.question(
            self, _("Löschen"),
            _("Soll der Kunde '{}' wirklich gelöscht werden?").format(name),
            QMessageBox.Yes | QMessageBox.No
        ) != QMessageBox.Yes:
            return
        
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("DELETE FROM kunden WHERE kundennr = %s", (kunde_id,))
            conn.commit()
            cur.close()
            conn.close()
            
            self._selected_kunde = None
            self.detail_panel.clear()
            self.lade_kunden()
            self.kunde_aktualisiert.emit()
            
        except Exception as e:
            print(f"[DBG] kunde_loeschen error: {e}")
            QMessageBox.warning(self, _("Fehler"), str(e))
    
    # Kompatibilität mit altem Tab
    def append_rows(self, rows):
        """Für TabLoader-Kompatibilität."""
        pass
    
    def load_finished(self):
        """Für TabLoader-Kompatibilität."""
        self.lade_kunden()
