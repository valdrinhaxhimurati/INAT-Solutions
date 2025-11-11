from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QTextEdit, QDateTimeEdit, QPushButton, QComboBox, QMessageBox, QFrame
)
from PyQt5.QtCore import QDateTime, Qt
# NEU: BaseDialog importieren
from .base_dialog import BaseDialog
from db_connection import get_db
from datetime import datetime, timezone, date

try:
    import ms_graph
except Exception:
    ms_graph = None

# ÄNDERUNG: Von BaseDialog erben
class AuftragDialog(BaseDialog):
    def __init__(self, parent=None, auftrag_id=None):
        super().__init__(parent)
        self.auftrag_id = auftrag_id
        self.outlook_event_id = None  # Wichtig: Outlook-ID speichern
        self.setWindowTitle("Neuer Termin" if auftrag_id is None else "Termin bearbeiten")
        self.setMinimumWidth(500)
        self.init_ui()
        
        if auftrag_id:
            self.load_auftrag()

    def init_ui(self):
        # WICHTIG: Das Layout vom BaseDialog verwenden
        layout = self.content_layout
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # Titel
        titel_layout = QHBoxLayout()
        titel_layout.addWidget(QLabel("Titel:"))
        self.titel_edit = QLineEdit()
        self.titel_edit.setPlaceholderText("z.B. Reifenwechsel")
        titel_layout.addWidget(self.titel_edit)
        layout.addLayout(titel_layout)
        
        # Beschreibung
        layout.addWidget(QLabel("Beschreibung:"))
        self.beschreibung_edit = QTextEdit()
        self.beschreibung_edit.setPlaceholderText("Zusätzliche Informationen...")
        self.beschreibung_edit.setMaximumHeight(80)
        layout.addWidget(self.beschreibung_edit)
        
        # Start- und Endzeit
        zeit_layout = QHBoxLayout()
        
        # Startzeit
        start_layout = QVBoxLayout()
        start_layout.addWidget(QLabel("Start:"))
        self.start_edit = QDateTimeEdit()
        self.start_edit.setCalendarPopup(True)
        self.start_edit.setDisplayFormat("dd.MM.yyyy HH:mm")
        self.start_edit.setDateTime(QDateTime.currentDateTime())
        start_layout.addWidget(self.start_edit)
        zeit_layout.addLayout(start_layout)
        
        # Endzeit
        end_layout = QVBoxLayout()
        end_layout.addWidget(QLabel("Ende:"))
        self.end_edit = QDateTimeEdit()
        self.end_edit.setCalendarPopup(True)
        self.end_edit.setDisplayFormat("dd.MM.yyyy HH:mm")
        self.end_edit.setDateTime(QDateTime.currentDateTime().addSecs(3600))  # +1 Stunde
        end_layout.addWidget(self.end_edit)
        zeit_layout.addLayout(end_layout)
        
        layout.addLayout(zeit_layout)
        
        # Ort
        ort_layout = QHBoxLayout()
        ort_layout.addWidget(QLabel("Ort:"))
        self.ort_edit = QLineEdit()
        self.ort_edit.setPlaceholderText("z.B. Werkstatt")
        ort_layout.addWidget(self.ort_edit)
        layout.addLayout(ort_layout)
        
        # Kunde (Optional)
        kunde_layout = QHBoxLayout()
        kunde_layout.addWidget(QLabel("Kunde:"))
        self.kunde_combo = QComboBox()
        self.kunde_combo.addItem("(Kein Kunde)", None)
        self.load_kunden()
        kunde_layout.addWidget(self.kunde_combo)
        layout.addLayout(kunde_layout)
        
        # Checkbox für Outlook-Synchronisation
        if ms_graph and ms_graph.is_connected():
            self.outlook_checkbox = QLabel("✅ Mit Outlook synchronisieren")
        else:
            self.outlook_checkbox = QLabel("⚠️ Outlook nicht verbunden")
        layout.addWidget(self.outlook_checkbox)
        
        # Buttons (Standard-Implementierung)
        button_layout = QHBoxLayout()
        button_layout.addStretch() # Buttons nach rechts schieben
        
        btn_cancel = QPushButton("Abbrechen")
        btn_cancel.clicked.connect(self.reject)
        
        btn_save = QPushButton("Speichern")
        btn_save.setDefault(True) # Macht Speichern zum Standard-Button (Enter-Taste)
        btn_save.clicked.connect(self.save_auftrag)
        
        button_layout.addWidget(btn_cancel)
        button_layout.addWidget(btn_save)
        
        layout.addLayout(button_layout)
        
        # ÄNDERUNG: self.setLayout() entfernen
        
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
            print(f"Fehler beim Laden der Kunden: {e}")

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
            QMessageBox.critical(self, "Fehler", f"Auftrag konnte nicht geladen werden:\n{e}")

    def save_auftrag(self):
        """Speichert den Auftrag in der Datenbank und optional in Outlook."""
        titel = self.titel_edit.text().strip()
        if not titel:
            QMessageBox.warning(self, "Validation", "Bitte geben Sie einen Titel ein.")
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
                QMessageBox.warning(self, "Outlook", f"Outlook-Synchronisation fehlgeschlagen:\n{e}\n\nDer Termin wird nur lokal gespeichert.")
        
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
            
            QMessageBox.information(self, "Erfolg", "Termin gespeichert!")
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Termin konnte nicht gespeichert werden:\n{e}")