from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QCalendarWidget, QListWidget, 
    QMessageBox, QLabel, QListWidgetItem, QToolButton, QFrame, QDialog, QScrollArea, QSpinBox,
)
from PyQt5.QtCore import QDate, Qt
from PyQt5.QtGui import QFont, QTextCharFormat, QColor, QPainter, QBrush
from db_connection import get_db
from gui.auftrag_dialog import AuftragDialog
from gui.themed_input_dialog import get_int as themed_get_int
from datetime import datetime, date
import resources_rc

try:
    import ms_graph
except Exception:
    ms_graph = None


class CustomCalendarWidget(QCalendarWidget):
    """Ein Kalender-Widget, das rote Punkte für Termine zeichnen kann."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.appointment_dates = set()

        # Verstecke die Standard-Navigationsleiste komplett
        self.findChild(QWidget, "qt_calendar_navigationbar").setVisible(False)

    def set_appointment_dates(self, dates):
        self.appointment_dates = set(dates)
        self.updateCells()

    def paintCell(self, painter, rect, date):
        super().paintCell(painter, rect, date)
        if date in self.appointment_dates:
            painter.save()
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setBrush(QBrush(QColor("#e53935")))  # Roter Punkt
            painter.setPen(Qt.NoPen)
            dot_diameter = 6
            x = rect.x() + (rect.width() / 2) - (dot_diameter / 2)
            y = rect.y() + rect.height() - dot_diameter - 4
            painter.drawEllipse(int(x), int(y), dot_diameter, dot_diameter)
            painter.restore()


class TerminCard(QFrame):
    """Moderne Karten-Ansicht für einen einzelnen Termin"""
    def __init__(self, termin_data, show_weekday=False, parent=None):
        super().__init__(parent)
        self.termin_data = termin_data
        self.show_weekday = show_weekday
        self.setProperty("cardType", "termin")
        self.setProperty("selected", "false")
        self.setup_ui()
        
    def setup_ui(self):
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)
        
        # Wochentag und Datum (nur in Wochenansicht)
        if self.show_weekday:
            weekday_names = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag']
            weekday = weekday_names[self.termin_data['start_dt'].weekday()]
            date_str = self.termin_data['start_dt'].strftime('%d.%m.%Y')
            
            weekday_label = QLabel(f"{weekday}, {date_str}")
            weekday_label.setProperty("labelType", "terminWeekday")
            layout.addWidget(weekday_label)
        
        # Zeitbereich
        time_label = QLabel(f"{self.termin_data['start_dt'].strftime('%H:%M')} - {self.termin_data['end_dt'].strftime('%H:%M')}")
        time_label.setProperty("labelType", "terminTime")
        layout.addWidget(time_label)
        
        # Titel
        title_label = QLabel(self.termin_data['titel'])
        title_label.setProperty("labelType", "terminTitle")
        title_label.setWordWrap(True)
        layout.addWidget(title_label)
        
        # Kunde und Ort
        if self.termin_data['kunde_name'] or self.termin_data['ort']:
            info_layout = QHBoxLayout()
            info_layout.setSpacing(16)
            
            if self.termin_data['kunde_name']:
                kunde_label = QLabel(f"👤 {self.termin_data['kunde_name']}")
                kunde_label.setProperty("labelType", "terminMeta")
                info_layout.addWidget(kunde_label)
                
            if self.termin_data['ort']:
                ort_label = QLabel(f"📍 {self.termin_data['ort']}")
                ort_label.setProperty("labelType", "terminMeta")
                info_layout.addWidget(ort_label)
                
            info_layout.addStretch()
            layout.addLayout(info_layout)
        
        # Beschreibung
        if self.termin_data['beschreibung']:
            desc_label = QLabel(self.termin_data['beschreibung'])
            desc_label.setProperty("labelType", "terminDesc")
            desc_label.setWordWrap(True)
            layout.addWidget(desc_label)


class AuftragskalenderTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.highlight_dates_with_appointments()
        self.load_week_termine()
        self.load_day_termine()

    # --- NEUE METHODE ---
    def update_customer_data(self):
        """
        Wird aufgerufen, wenn sich Kundendaten geändert haben.
        Lädt die Terminansichten neu, um die Änderungen zu übernehmen.
        """
        print("[Auftragskalender] Aktualisiere Termine aufgrund von Kundenänderung...")
        self.load_day_termine()
        self.load_week_termine()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # LINKE SPALTE: Kalender + Tagesansicht
        left_column = QVBoxLayout()
        left_column.setSpacing(15)
        
        # Kalender Container
        calendar_container = QFrame()
        calendar_container.setObjectName("calendarContainer")
        calendar_layout = QVBoxLayout(calendar_container)
        calendar_layout.setContentsMargins(15, 15, 15, 15)
        
        calendar_title = QLabel("📅 Kalender")
        calendar_title.setProperty("labelType", "calendarTitle")
        calendar_layout.addWidget(calendar_title)

        # Eigene Navigationsleiste
        nav_layout = QHBoxLayout()
        self.prev_month_btn = QToolButton()
        self.prev_month_btn.setText("<")
        self.prev_month_btn.setObjectName("calendarNavButton")
        
        self.month_year_label = QLabel()
        self.month_year_label.setObjectName("calendarTitleLabel")
        self.month_year_label.setAlignment(Qt.AlignCenter)
        
        self.next_month_btn = QToolButton()
        self.next_month_btn.setText(">")
        self.next_month_btn.setObjectName("calendarNavButton")
        
        nav_layout.addWidget(self.prev_month_btn)
        nav_layout.addStretch()
        nav_layout.addWidget(self.month_year_label)
        nav_layout.addStretch()
        nav_layout.addWidget(self.next_month_btn)
        calendar_layout.addLayout(nav_layout)
        
        self.calendar = CustomCalendarWidget()
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.calendar.setGridVisible(True)
        
        # Signale verbinden
        self.prev_month_btn.clicked.connect(self.calendar.showPreviousMonth)
        self.next_month_btn.clicked.connect(self.calendar.showNextMonth)
        self.calendar.currentPageChanged.connect(self.update_month_year_label)
        self.month_year_label.mousePressEvent = self.select_year
        self.calendar.selectionChanged.connect(self.load_day_termine)
        
        self.update_month_year_label(self.calendar.yearShown(), self.calendar.monthShown())

        calendar_layout.addWidget(self.calendar)
        left_column.addWidget(calendar_container, 3)
        
        # Tagesansicht Container
        day_container = QFrame()
        day_container.setObjectName("calendarContainer")
        day_layout = QVBoxLayout(day_container)
        day_layout.setContentsMargins(15, 15, 15, 15)
        
        self.day_title = QLabel("📌 Termine des Tages")
        self.day_title.setProperty("labelType", "calendarSubtitle")
        day_layout.addWidget(self.day_title)
        
        self.day_scroll = QScrollArea()
        self.day_scroll.setWidgetResizable(True)
        self.day_scroll.setFrameShape(QFrame.NoFrame)
        
        self.day_content = QWidget()
        self.day_layout = QVBoxLayout(self.day_content)
        self.day_layout.setSpacing(8)
        self.day_layout.addStretch()
        self.day_scroll.setWidget(self.day_content)
        day_layout.addWidget(self.day_scroll)
        
        left_column.addWidget(day_container, 2)

        # MITTLERE SPALTE: Wochenansicht
        week_container = QFrame()
        week_container.setObjectName("calendarContainer")
        week_layout = QVBoxLayout(week_container)
        week_layout.setContentsMargins(15, 15, 15, 15)
        
        self.week_title = QLabel("📆 Termine der Woche")
        self.week_title.setProperty("labelType", "calendarTitle")
        week_layout.addWidget(self.week_title)
        
        self.week_scroll = QScrollArea()
        self.week_scroll.setWidgetResizable(True)
        self.week_scroll.setFrameShape(QFrame.NoFrame)
        
        self.week_content = QWidget()
        self.week_layout = QVBoxLayout(self.week_content)
        self.week_layout.setSpacing(8)
        self.week_layout.addStretch()
        self.week_scroll.setWidget(self.week_content)
        week_layout.addWidget(self.week_scroll)

        # RECHTE SPALTE: Buttons
        right_layout = QVBoxLayout()
        right_layout.setSpacing(12)
        
        btn_new = QToolButton()
        btn_new.setText("Neuer Termin")
        btn_new.setProperty("role", "add")
        btn_new.clicked.connect(self.create_new_termin)
        
        btn_edit = QToolButton()
        btn_edit.setText("Termin bearbeiten")
        btn_edit.setProperty("role", "edit")
        btn_edit.clicked.connect(self.edit_termin)
        
        btn_delete = QToolButton()
        btn_delete.setText("Termin löschen")
        btn_delete.setProperty("role", "delete")
        btn_delete.clicked.connect(self.delete_termin)
        
        right_layout.addWidget(btn_new)
        right_layout.addWidget(btn_edit)
        right_layout.addWidget(btn_delete)
        right_layout.addStretch()

        # Layouts zusammenfügen
        main_layout.addLayout(left_column, 2)
        main_layout.addWidget(week_container, 3)
        main_layout.addLayout(right_layout, 1)
        
        self.selected_card = None

    def update_month_year_label(self, year, month):
        """Aktualisiert das Label für Monat und Jahr."""
        locale = self.calendar.locale()
        month_name = locale.monthName(month)
        self.month_year_label.setText(f"{month_name} {year}")

    def select_year(self, event):
        """Öffnet einen Dialog zur Auswahl des Jahres."""
        current_year = self.calendar.yearShown()
        new_year, ok = themed_get_int(self, "Jahr auswählen", "Jahr:", current_year, 1900, 2100, 1)
        if ok:
            current_month = self.calendar.monthShown()
            self.calendar.setCurrentPage(new_year, current_month)

    def _clear_cards(self, layout):
        """Entfernt alle Karten aus einem Layout"""
        while layout.count() > 1:  # Behalte den Stretch
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _add_termine_cards(self, layout, termine):
        """Fügt Termin-Karten zu einem Layout hinzu"""
        self._clear_cards(layout)
        
        if not termine:
            no_data = QLabel("Keine Termine vorhanden")
            no_data.setProperty("labelType", "noData")
            no_data.setAlignment(Qt.AlignCenter)
            layout.insertWidget(0, no_data)
            return
        
        # Prüfen ob das die Wochenliste ist
        is_week_view = (layout == self.week_layout)
            
        for termin_row in termine:
            if hasattr(termin_row, 'keys'):
                auftrag_id, titel, beschreibung, start_zeit, end_zeit, ort, kunde_name = termin_row
            else:
                auftrag_id, titel, beschreibung, start_zeit, end_zeit, ort, kunde_name = termin_row

            if isinstance(start_zeit, str):
                start_dt = datetime.fromisoformat(start_zeit.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end_zeit.replace('Z', '+00:00'))
            else:
                start_dt, end_dt = start_zeit, end_zeit

            data = {
                'id': auftrag_id,
                'titel': titel,
                'beschreibung': beschreibung,
                'start_dt': start_dt,
                'end_dt': end_dt,
                'ort': ort,
                'kunde_name': kunde_name
            }
            
            card = TerminCard(data, show_weekday=is_week_view)
            card.mousePressEvent = lambda e, c=card: self.select_card(c)
            layout.insertWidget(layout.count() - 1, card)

    def select_card(self, card):
        """Markiert die ausgewählte Karte"""
        if self.selected_card:
            self.selected_card.setProperty("selected", "false")
            self.selected_card.style().unpolish(self.selected_card)
            self.selected_card.style().polish(self.selected_card)
        
        self.selected_card = card
        card.setProperty("selected", "true")
        card.style().unpolish(card)
        card.style().polish(card)

    def load_week_termine(self):
        today = QDate.currentDate()
        start_of_week = today.addDays(-today.dayOfWeek() + 1)
        end_of_week = start_of_week.addDays(6)
        self.week_title.setText(f"📆 Termine der Woche  ({start_of_week.toString('dd.MM')} - {end_of_week.toString('dd.MM')})")
        
        query = """
            SELECT a.id, a.titel, a.beschreibung, a.start_zeit, a.end_zeit, a.ort, k.name 
            FROM auftraege a LEFT JOIN kunden k ON a.kunden_id = k.kundennr
            WHERE DATE(a.start_zeit) BETWEEN {ph} AND {ph} ORDER BY a.start_zeit
        """
        params = (start_of_week.toString("yyyy-MM-dd"), end_of_week.toString("yyyy-MM-dd"))
        
        try:
            conn = get_db()
            cur = conn.cursor()
            ph = "?" if conn.is_sqlite else "%s"
            cur.execute(query.format(ph=ph), params)
            termine = cur.fetchall()
            conn.close()
            self._add_termine_cards(self.week_layout, termine)
        except Exception as e:
            print(f"Fehler beim Laden der Wochentermine: {e}")

    def load_day_termine(self):
        selected_date = self.calendar.selectedDate()
        self.day_title.setText(f"📌 Termine am {selected_date.toString('dd.MM.yyyy')}")
        
        query = """
            SELECT a.id, a.titel, a.beschreibung, a.start_zeit, a.end_zeit, a.ort, k.name 
            FROM auftraege a LEFT JOIN kunden k ON a.kunden_id = k.kundennr
            WHERE DATE(a.start_zeit) = {ph} ORDER BY a.start_zeit
        """
        params = (selected_date.toString("yyyy-MM-dd"),)

        try:
            conn = get_db()
            cur = conn.cursor()
            ph = "?" if conn.is_sqlite else "%s"
            cur.execute(query.format(ph=ph), params)
            termine = cur.fetchall()
            conn.close()
            self._add_termine_cards(self.day_layout, termine)
        except Exception as e:
            print(f"Fehler beim Laden der Tagestermine: {e}")

    def highlight_dates_with_appointments(self):
        # Formate zurücksetzen (optional, aber gute Praxis)
        default_format = QTextCharFormat()
        self.calendar.setDateTextFormat(QDate(), default_format)
        
        try:
            conn = get_db()
            cur = conn.cursor()
            query = "SELECT DISTINCT DATE(start_zeit) FROM auftraege" if conn.is_sqlite else "SELECT DISTINCT (start_zeit::date) FROM auftraege"
            cur.execute(query)
            db_dates = cur.fetchall()
            conn.close()
            
            q_dates = []
            for date_tuple in db_dates:
                date_val = date_tuple[0]
                if isinstance(date_val, (datetime, date)):
                    q_date = QDate(date_val.year, date_val.month, date_val.day)
                elif isinstance(date_val, str):
                    q_date = QDate.fromString(date_val, "yyyy-MM-dd")
                else:
                    continue
                q_dates.append(q_date)
            
            self.calendar.set_appointment_dates(q_dates)
        except Exception as e:
            print(f"Fehler beim Hervorheben: {e}")

    def create_new_termin(self):
        selected_date = self.calendar.selectedDate()
        dialog = AuftragDialog(self)
        dialog.start_edit.setDate(selected_date)
        dialog.start_edit.setTime(dialog.start_edit.time().fromString("09:00", "HH:mm"))
        dialog.end_edit.setDate(selected_date)
        dialog.end_edit.setTime(dialog.end_edit.time().fromString("10:00", "HH:mm"))
        if dialog.exec_() == QDialog.Accepted:
            self.load_day_termine()
            self.load_week_termine()
            self.highlight_dates_with_appointments()

    def edit_termin(self):
        if not self.selected_card:
            QMessageBox.warning(self, "Kein Termin", "Bitte wählen Sie einen Termin aus.")
            return
            
        auftrag_id = self.selected_card.termin_data['id']
        dialog = AuftragDialog(self, auftrag_id=auftrag_id)
        if dialog.exec_() == QDialog.Accepted:
            self.load_day_termine()
            self.load_week_termine()
            self.highlight_dates_with_appointments()
            self.selected_card = None

    def delete_termin(self):
        if not self.selected_card:
            QMessageBox.warning(self, "Kein Termin", "Bitte wählen Sie einen Termin aus.")
            return
            
        auftrag_id = self.selected_card.termin_data['id']
        reply = QMessageBox.question(self, "Termin löschen", "Möchten Sie diesen Termin wirklich löschen?", QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                conn = get_db()
                cur = conn.cursor()
                ph = "?" if conn.is_sqlite else "%s"
                cur.execute(f"SELECT outlook_event_id FROM auftraege WHERE id = {ph}", (auftrag_id,))
                result = cur.fetchone()
                outlook_id = result[0] if result else None
                
                cur.execute(f"DELETE FROM auftraege WHERE id = {ph}", (auftrag_id,))
                conn.commit()
                conn.close()
                
                if outlook_id and ms_graph and ms_graph.is_connected():
                    try:
                        ms_graph.delete_event(outlook_id)
                        QMessageBox.information(self, "Erfolg", "Termin lokal und in Outlook gelöscht.")
                    except Exception as e:
                        QMessageBox.warning(self, "Outlook Fehler", f"Termin lokal gelöscht, aber Fehler in Outlook:\n{e}")
                else:
                    QMessageBox.information(self, "Erfolg", "Termin gelöscht.")
                    
                self.load_day_termine()
                self.load_week_termine()
                self.highlight_dates_with_appointments()
                self.selected_card = None
            except Exception as e:
                QMessageBox.critical(self, "Fehler", f"Löschen fehlgeschlagen:\n{e}")
