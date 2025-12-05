from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QTextEdit, QDateTimeEdit, QPushButton, QComboBox, QMessageBox, QFrame, QGroupBox, QFormLayout
)
from PyQt5.QtCore import QDateTime, Qt
from .base_dialog import BaseDialog
from .dialog_styles import GROUPBOX_STYLE
from db_connection import get_db
from datetime import datetime, timezone, date
from i18n import _

try:
    import ms_graph
except Exception:
    ms_graph = None


class AuftragDialog(BaseDialog):
    def __init__(self, parent=None, auftrag_id=None):
        super().__init__(parent)
        self.auftrag_id = auftrag_id
        self.outlook_event_id = None
        self.setWindowTitle(_("Neuer Termin") if auftrag_id is None else _("Termin bearbeiten"))
        self.resize(550, 520)
        self.init_ui()
        
        if auftrag_id:
            self.load_auftrag()

    def init_ui(self):
        layout = self.content_layout
        layout.setSpacing(15)

        # === Termindaten ===
        termin_group = QGroupBox(_("Termindaten"))
        termin_group.setStyleSheet(GROUPBOX_STYLE)
        termin_layout = QFormLayout(termin_group)
        termin_layout.setSpacing(10)

        self.titel_edit = QLineEdit()
        self.titel_edit.setPlaceholderText(_("z.B. Reifenwechsel"))
        termin_layout.addRow(_("Titel:"), self.titel_edit)

        self.beschreibung_edit = QTextEdit()
        self.beschreibung_edit.setPlaceholderText(_("Zusätzliche Informationen..."))
        self.beschreibung_edit.setMaximumHeight(70)
        termin_layout.addRow(_("Beschreibung:"), self.beschreibung_edit)

        layout.addWidget(termin_group)

        # === Zeit & Ort ===
        zeit_group = QGroupBox(_("Zeit & Ort"))
        zeit_group.setStyleSheet(GROUPBOX_STYLE)
        zeit_layout = QFormLayout(zeit_group)
        zeit_layout.setSpacing(10)

        self.start_edit = QDateTimeEdit()
        self.start_edit.setCalendarPopup(True)
        self.start_edit.setDisplayFormat("dd.MM.yyyy HH:mm")
        self.start_edit.setDateTime(QDateTime.currentDateTime())
        zeit_layout.addRow(_("Start:"), self.start_edit)

        self.end_edit = QDateTimeEdit()
        self.end_edit.setCalendarPopup(True)
        self.end_edit.setDisplayFormat("dd.MM.yyyy HH:mm")
        self.end_edit.setDateTime(QDateTime.currentDateTime().addSecs(3600))
        zeit_layout.addRow(_("Ende:"), self.end_edit)

        self.ort_edit = QLineEdit()
        self.ort_edit.setPlaceholderText(_("z.B. Werkstatt"))
        zeit_layout.addRow(_("Ort:"), self.ort_edit)

        layout.addWidget(zeit_group)

        # === Kunde ===
        kunde_group = QGroupBox(_("Kunde"))
        kunde_group.setStyleSheet(GROUPBOX_STYLE)
        kunde_layout = QFormLayout(kunde_group)
        kunde_layout.setSpacing(10)

        self.kunde_combo = QComboBox()
        self.kunde_combo.addItem(_("(Kein Kunde)"), None)
        self.load_kunden()
        kunde_layout.addRow(_("Kunde:"), self.kunde_combo)

        # Outlook Status
        if ms_graph and ms_graph.is_connected():
            outlook_label = QLabel(_("Mit Outlook synchronisieren (verbunden)"))
            outlook_label.setStyleSheet("color: #27ae60;")
        else:
            outlook_label = QLabel(_("Outlook nicht verbunden"))
            outlook_label.setStyleSheet("color: #e67e22;")
        kunde_layout.addRow(_("Outlook:"), outlook_label)

        layout.addWidget(kunde_group)

        layout.addStretch()

        # === Buttons (zentriert) ===
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_cancel = QPushButton(_("Abbrechen"))
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        
        btn_save = QPushButton(_("Speichern"))
        btn_save.setDefault(True)
        btn_save.clicked.connect(self.save_auftrag)
        btn_layout.addWidget(btn_save)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
    def load_kunden(self):
        """Lädt alle Kunden aus der Datenbank."""
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT kundennr, name, firma FROM kunden ORDER BY name")
            for row in cur.fetchall():
                # Korrigiert: Funktioniert jetzt für SQLite (Row) und PostgreSQL (Tuple)
                if hasattr(row, 'keys'): # SQLite
                    kundennr, name, firma = row['kundennr'], row['name'], row['firma']
                else: # PostgreSQL
                    kundennr, name, firma = row
                
                display = f"{name} ({firma})" if firma else name
                self.kunde_combo.addItem(display, kundennr) # kundennr als UserData speichern
            conn.close()
        except Exception as e:
            print(_("Fehler beim Laden der Kunden: {e}"))

    def load_auftrag(self):
        """Lädt einen bestehenden Auftrag zum Bearbeiten."""
        try:
            conn = get_db()
            cur = conn.cursor()
            ph = "?" if conn.is_sqlite else "%s"
            cur.execute(f"""
                SELECT titel, beschreibung, start_zeit, end_zeit, ort, kunden_id, outlook_event_id
                FROM auftraege WHERE id = {ph}
            """, (self.auftrag_id,))
            row = cur.fetchone()
            conn.close()
            
            if row:
                self.titel_edit.setText(row[0] or "")
                self.beschreibung_edit.setPlainText(row[1] or "")
                
                # Zeitstempel parsen
                start_val, end_val = row[2], row[3]
                if isinstance(start_val, str):
                    start_dt = datetime.fromisoformat(start_val.replace('Z', '+00:00')) if start_val else datetime.now()
                    end_dt = datetime.fromisoformat(end_val.replace('Z', '+00:00')) if end_val else datetime.now()
                else:
                    start_dt, end_dt = start_val, end_val

                self.start_edit.setDateTime(QDateTime(start_dt.year, start_dt.month, start_dt.day, start_dt.hour, start_dt.minute))
                self.end_edit.setDateTime(QDateTime(end_dt.year, end_dt.month, end_dt.day, end_dt.hour, end_dt.minute))
                
                self.ort_edit.setText(row[4] or "")
                
                # Kunde auswählen
                if row[5]:
                    for i in range(self.kunde_combo.count()):
                        if self.kunde_combo.itemData(i) == row[5]:
                            self.kunde_combo.setCurrentIndex(i)
                            break
                
                # Outlook-ID speichern
                self.outlook_event_id = row[6]

        except Exception as e:
            QMessageBox.critical(self, _("Fehler"), _("Auftrag konnte nicht geladen werden:\n") + f"{e}")

    def save_auftrag(self):
        """Speichert den Auftrag in der Datenbank und optional in Outlook."""
        titel = self.titel_edit.text().strip()
        if not titel:
            QMessageBox.warning(
                self,
                _("Pflichtfelder fehlen"),
                _("Bitte fülle folgende Pflichtfelder aus:") + "\n\n• " + _("Titel")
            )
            return
        
        beschreibung = self.beschreibung_edit.toPlainText().strip()
        start_dt = self.start_edit.dateTime().toPyDateTime()
        end_dt = self.end_edit.dateTime().toPyDateTime()
        ort = self.ort_edit.text().strip()
        kunden_id = self.kunde_combo.currentData()
        
        # In UTC konvertieren für Outlook
        start_utc = start_dt.replace(tzinfo=timezone.utc)
        end_utc = end_dt.replace(tzinfo=timezone.utc)
        
        outlook_event_id = self.outlook_event_id # Bestehende ID verwenden
        
        # Outlook-Synchronisation
        if ms_graph and ms_graph.is_connected():
            try:
                body_html = f"<p>{beschreibung}</p>" if beschreibung else ""
                if kunden_id:
                    body_html += f"<p><strong>Kunde:</strong> {self.kunde_combo.currentText()}</p>"
                
                if self.outlook_event_id:
                    # Bestehenden Termin aktualisieren
                    ms_graph.update_event(
                        event_id=self.outlook_event_id,
                        subject=titel,
                        start_dt_utc=start_utc,
                        end_dt_utc=end_utc,
                        location=ort,
                        body_html=body_html
                    )
                else:
                    # Neuen Termin erstellen
                    event = ms_graph.create_event(
                        subject=titel,
                        start_dt_utc=start_utc,
                        end_dt_utc=end_utc,
                        location=ort,
                        body_html=body_html
                    )
                    outlook_event_id = event.get("id")

            except Exception as e:
                QMessageBox.warning(self, _("Outlook"), _("Outlook-Synchronisation fehlgeschlagen:\n{e}\n\nDer Termin wird nur lokal gespeichert."))
        
        # In Datenbank speichern
        try:
            conn = get_db()
            cur = conn.cursor()
            ph = "?" if conn.is_sqlite else "%s"
            
            if self.auftrag_id:
                # Update
                cur.execute(f"""
                    UPDATE auftraege 
                    SET titel={ph}, beschreibung={ph}, start_zeit={ph}, end_zeit={ph}, ort={ph}, kunden_id={ph}, outlook_event_id={ph}
                    WHERE id={ph}
                """, (titel, beschreibung, start_dt.isoformat(), end_dt.isoformat(), ort, kunden_id, outlook_event_id, self.auftrag_id))
            else:
                # Insert
                cur.execute(f"""
                    INSERT INTO auftraege (titel, beschreibung, start_zeit, end_zeit, ort, kunden_id, outlook_event_id)
                    VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
                """, (titel, beschreibung, start_dt.isoformat(), end_dt.isoformat(), ort, kunden_id, outlook_event_id))
            
            conn.commit()
            conn.close()
            
            QMessageBox.information(self, _("Erfolg"), _("Termin gespeichert!"))
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, _("Fehler"), _("Termin konnte nicht gespeichert werden:\n") + f"{e}")