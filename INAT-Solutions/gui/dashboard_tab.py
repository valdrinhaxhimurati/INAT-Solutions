# -*- coding: utf-8 -*-
"""
Dashboard Tab - Übersicht über alle wichtigen Kennzahlen
Professionelles Design passend zur Anwendung
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QGridLayout, QScrollArea, QSizePolicy, QSpacerItem, QGraphicsDropShadowEffect
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor, QPalette, QLinearGradient, QPainter, QBrush
from db_connection import get_db
from gui.modern_widgets import COLORS, FONT_SIZES, SPACING, BORDER_RADIUS
from i18n import _
import datetime


def _to_bool(val):
    """Normalisiere DB-Werte zu bool."""
    if isinstance(val, bool):
        return val
    if val is None:
        return False
    try:
        return bool(int(val))
    except Exception:
        s = str(val).strip().lower()
        return s in ("1", "true", "t", "yes", "y", "on")


def get_active_modules():
    """Liest die aktiven Lager-Module aus der Datenbank."""
    aktive = {
        "material": False,
        "reifen": False,
        "artikel": False,
        "dienstleistungen": False
    }
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT lager_typ, aktiv FROM lager_einstellungen")
        for row in cur.fetchall():
            if isinstance(row, dict):
                lager_typ = row.get('lager_typ')
                aktiv_val = row.get('aktiv')
            else:
                if len(row) >= 2:
                    lager_typ, aktiv_val = row[0], row[1]
                else:
                    continue
            if lager_typ in aktive:
                aktive[lager_typ] = _to_bool(aktiv_val)
        conn.close()
    except Exception:
        pass
    return aktive


class StatCard(QFrame):
    """Statistik-Karte im modernen Design."""
    
    # Akzent-Farben für verschiedene Typen
    ACCENT_COLORS = {
        "default": "#4a6fa5",   # Blau
        "success": "#10b981",   # Grün
        "warning": "#f59e0b",   # Orange/Gelb
        "danger": "#ef4444",    # Rot
    }
    
    def __init__(self, title: str, value: str, icon: str = "", accent: str = "default", parent=None):
        super().__init__(parent)
        self.setObjectName("statCard")
        self.accent_color = self.ACCENT_COLORS.get(accent, self.ACCENT_COLORS["default"])
        
        # Modernes Design: Weiß mit leichtem Rahmen
        self.setStyleSheet(f"""
            QFrame#statCard {{
                background-color: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 12px;
            }}
        """)
        
        # Dezenter Schatten
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 15))
        self.setGraphicsEffect(shadow)
        
        self.setMinimumSize(200, 110)
        self.setMaximumHeight(130)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(20, 16, 20, 16)
        
        # Titel oben
        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: {FONT_SIZES['body']}px; font-weight: 500; background: transparent;")
        layout.addWidget(title_label)
        
        # Wert-Zeile mit Icon
        value_row = QHBoxLayout()
        value_row.setSpacing(12)
        
        self.value_label = QLabel(value)
        self.value_label.setStyleSheet(f"color: {self.accent_color}; font-size: {FONT_SIZES['h2']}px; font-weight: 700; background: transparent;")
        value_row.addWidget(self.value_label)
        
        value_row.addStretch()
        
        # Icon rechts (optional)
        if icon:
            icon_label = QLabel(icon)
            icon_label.setStyleSheet(f"font-size: {FONT_SIZES['h3']}px; background: transparent;")
            value_row.addWidget(icon_label)
        
        layout.addLayout(value_row)
        
        # Optionale Subtext-Zeile
        self.subtext_label = QLabel()
        self.subtext_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: {FONT_SIZES['small']}px; background: transparent;")
        self.subtext_label.hide()
        layout.addWidget(self.subtext_label)
        
        layout.addStretch()
    def set_value(self, value: str):
        self.value_label.setText(value)
    
    def set_subtext(self, text: str):
        """Setzt optionalen Subtext (z.B. '↑ 12% zum Vormonat')."""
        if text:
            self.subtext_label.setText(text)
            self.subtext_label.show()
        else:
            self.subtext_label.hide()


class AlertCard(QFrame):
    """Alert-Karte im Showcase-Design."""
    
    # Showcase Akzentfarben
    ACCENT_COLORS = {
        "warning": "#f59e0b",   # Amber
        "danger": "#ef4444",    # Red
        "info": "#4a6fa5",      # Blue
        "success": "#10b981",   # Green
    }
    
    def __init__(self, title: str, items: list, icon: str = "", accent: str = "info", parent=None):
        super().__init__(parent)
        self.setObjectName("alertCard")
        self.accent_color = self.ACCENT_COLORS.get(accent, self.ACCENT_COLORS["info"])
        
        self.setStyleSheet("""
            QFrame#alertCard {
                background-color: #ffffff;
                border: none;
                border-radius: 12px;
            }
        """)
        
        # Dezenter Schatten
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(16)
        shadow.setXOffset(0)
        shadow.setYOffset(2)
        shadow.setColor(QColor(0, 0, 0, 20))
        self.setGraphicsEffect(shadow)
        
        self.setMinimumHeight(160)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 14, 16, 14)
        
        # Header
        header = QHBoxLayout()
        header.setSpacing(10)
        
        # Farbiger Akzent-Streifen links
        accent_bar = QFrame()
        accent_bar.setFixedSize(4, 24)
        accent_bar.setStyleSheet(f"background-color: {self.accent_color}; border-radius: 2px;")
        header.addWidget(accent_bar)
        
        # Icon (optional)
        if icon:
            icon_label = QLabel(icon)
            icon_label.setStyleSheet(f"font-size: {FONT_SIZES['h4']}px; background: transparent;")
            header.addWidget(icon_label)
        
        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: {FONT_SIZES['h5']}px; font-weight: 600; background: transparent;")
        header.addWidget(title_label)
        header.addStretch()
        
        # Anzahl-Badge
        self.count_badge = QLabel("0")
        self.count_badge.setFixedSize(30, 30)
        self.count_badge.setAlignment(Qt.AlignCenter)
        self.count_badge.setStyleSheet(f"""
            background-color: {self.accent_color};
            color: white;
            font-size: {FONT_SIZES['small']}px;
            font-weight: bold;
            border-radius: 15px;
        """)
        header.addWidget(self.count_badge)
        
        layout.addLayout(header)
        
        # Trennlinie
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet("background-color: #e0e4ec;")
        layout.addWidget(line)
        
        # Items
        self.items_layout = QVBoxLayout()
        self.items_layout.setSpacing(5)
        layout.addLayout(self.items_layout)
        
        self.set_items(items)
    
    def set_items(self, items: list):
        # Clear existing
        while self.items_layout.count():
            child = self.items_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Update count
        self.count_badge.setText(str(len(items)))
        
        if not items:
            no_items = QLabel(_("Keine Einträge"))
            no_items.setStyleSheet(f"color: {COLORS['success']}; font-size: {FONT_SIZES['body']}px; padding: 4px 0; background: transparent;")
            self.items_layout.addWidget(no_items)
        else:
            for item in items[:4]:  # Max 4 Items
                item_row = QHBoxLayout()
                item_row.setSpacing(8)
                
                dot = QLabel("•")
                dot.setStyleSheet(f"color: {self.accent_color}; font-size: {FONT_SIZES['h5']}px; background: transparent;")
                dot.setFixedWidth(14)
                item_row.addWidget(dot)
                
                item_label = QLabel(item)
                item_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: {FONT_SIZES['body']}px; background: transparent;")
                item_label.setWordWrap(True)
                item_row.addWidget(item_label, 1)
                
                self.items_layout.addLayout(item_row)
            
            if len(items) > 4:
                more_label = QLabel(_("+ {} weitere...").format(len(items) - 4))
                more_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: {FONT_SIZES['small']}px; font-style: italic; padding-left: 20px; background: transparent;")
                self.items_layout.addWidget(more_label)


class DashboardTab(QWidget):
    """Das Dashboard mit Übersicht über alle wichtigen Kennzahlen."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Aktive Module laden
        self.active_modules = get_active_modules()
        
        self.init_ui()
        
        # Auto-Refresh alle 60 Sekunden
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_data)
        self.refresh_timer.start(60000)
        
        # Initial laden
        QTimer.singleShot(100, self.refresh_data)
    
    def init_ui(self):
        # Scroll-Bereich - Weißer Hintergrund
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("""
            QScrollArea { 
                background-color: #ffffff;
                border: none; 
            }
            QScrollBar:vertical {
                background: #e5e7eb;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: #9ca3af;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #6b7280;
            }
        """)
        
        # Container
        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.main_layout = QVBoxLayout(self.container)
        self.main_layout.setSpacing(20)
        self.main_layout.setContentsMargins(30, 20, 30, 25)
        
        # Letzte Aktualisierung (versteckt, für Kompatibilität)
        self.last_update_label = QLabel()
        self.last_update_label.hide()
        
        # === HAUPTSTATISTIKEN (immer sichtbar) ===
        stats_grid = QGridLayout()
        stats_grid.setSpacing(16)
        
        # Umsatz-Karte (Grün für Einnahmen)
        monatsnamen = ["Januar", "Februar", "März", "April", "Mai", "Juni", 
                       "Juli", "August", "September", "Oktober", "November", "Dezember"]
        aktueller_monat = monatsnamen[datetime.date.today().month - 1]
        self.card_umsatz = StatCard(_("Umsatz") + f" ({aktueller_monat[:3]})", "CHF 0", "💰", accent="success")
        
        # Offene Rechnungen (Orange für Warnung)
        self.card_offen = StatCard(_("Offene Rechnungen"), "0", "📄", accent="warning")
        
        # Neue Kunden (Blau/Standard)
        self.card_kunden = StatCard(_("Neue Kunden"), "0", "👥", accent="default")
        
        # Lagerwarnungen (Rot für Alarm)
        self.card_lagerwarnungen = StatCard(_("Lagerwarnungen"), "0", "📦", accent="danger")
        
        stats_grid.addWidget(self.card_umsatz, 0, 0)
        stats_grid.addWidget(self.card_offen, 0, 1)
        stats_grid.addWidget(self.card_kunden, 0, 2)
        stats_grid.addWidget(self.card_lagerwarnungen, 0, 3)
        
        self.main_layout.addLayout(stats_grid)
        
        # === ZWEITE REIHE STATISTIKEN (dynamisch) ===
        stats_grid2 = QGridLayout()
        stats_grid2.setSpacing(16)
        
        col = 0
        
        # Lieferanten (immer sichtbar)
        self.card_lieferanten = StatCard(_("Lieferanten"), "0", "🏭", accent="default")
        stats_grid2.addWidget(self.card_lieferanten, 0, col)
        col += 1
        
        # Termine (immer sichtbar)
        self.card_termine = StatCard(_("Termine heute"), "0", "📅", accent="default")
        stats_grid2.addWidget(self.card_termine, 0, col)
        col += 1
        
        # Reifen - nur wenn Modul aktiv
        self.card_reifen = None
        if self.active_modules.get("reifen", False):
            self.card_reifen = StatCard(_("Reifen eingelagert"), "0", "🛞", accent="default")
            stats_grid2.addWidget(self.card_reifen, 0, col)
            col += 1
        
        # Artikel - nur wenn Modul aktiv
        self.card_artikel = None
        if self.active_modules.get("artikel", False):
            self.card_artikel = StatCard(_("Artikel im Lager"), "0", "📦", accent="default")
            stats_grid2.addWidget(self.card_artikel, 0, col)
            col += 1
        
        self.main_layout.addLayout(stats_grid2)
        
        # === WARNUNGEN & HINWEISE ===
        # Nur anzeigen wenn mindestens eine Alert-Karte sichtbar ist
        has_alerts = True  # Überfällige Rechnungen und Termine sind immer sichtbar
        
        alerts_title = QLabel(_("Hinweise & Warnungen"))
        alerts_title.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: {FONT_SIZES['h4']}px; font-weight: 600; background: transparent; margin-top: 10px;")
        self.main_layout.addWidget(alerts_title)
        
        alerts_grid = QGridLayout()
        alerts_grid.setSpacing(15)
        
        row = 0
        col = 0
        
        # Überfällige Rechnungen (immer sichtbar)
        self.alert_rechnungen = AlertCard(
            _("Überfällige Rechnungen"),
            [],
            "💰",
            "danger"
        )
        alerts_grid.addWidget(self.alert_rechnungen, row, col)
        col += 1
        
        # Alte Reifen - nur wenn Modul aktiv
        self.alert_reifen = None
        if self.active_modules.get("reifen", False):
            self.alert_reifen = AlertCard(
                _("Alte Reifen (DOT > 5 Jahre)"),
                [],
                "🛞",
                "warning"
            )
            alerts_grid.addWidget(self.alert_reifen, row, col)
            col += 1
        
        # Neue Zeile starten
        if col >= 2:
            row += 1
            col = 0
        
        # Niedriger Lagerbestand - nur wenn Artikel-Modul aktiv
        self.alert_bestand = None
        if self.active_modules.get("artikel", False):
            self.alert_bestand = AlertCard(
                _("Niedriger Lagerbestand"),
                [],
                "📦",
                "warning"
            )
            alerts_grid.addWidget(self.alert_bestand, row, col)
            col += 1
        
        # Heutige Termine (immer sichtbar)
        self.alert_termine = AlertCard(
            _("Heutige Termine"),
            [],
            "📅",
            "info"
        )
        alerts_grid.addWidget(self.alert_termine, row, col)
        
        self.main_layout.addLayout(alerts_grid)
        
        self.main_layout.addStretch()
        
        scroll.setWidget(self.container)
        
        # Hauptlayout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)
    
    def refresh_data(self):
        """Lädt alle Dashboard-Daten neu."""
        try:
            conn = get_db()
            cur = conn.cursor()
            
            # Kunden zählen (neue Kunden diesen Monat)
            try:
                heute = datetime.date.today()
                monat_start = heute.replace(day=1).isoformat()
                # Versuche erst mit created_at, falls vorhanden
                try:
                    cur.execute(f"SELECT COUNT(*) FROM kunden WHERE created_at >= '{monat_start}'")
                    count = cur.fetchone()[0]
                except:
                    # Fallback: alle Kunden zählen
                    cur.execute("SELECT COUNT(*) FROM kunden")
                    count = cur.fetchone()[0]
                self.card_kunden.set_value(str(count))
                self.card_kunden.set_subtext(_("↑ {} diese Woche").format(count))
            except:
                self.card_kunden.set_value("—")
            
            # Offene Rechnungen
            try:
                cur.execute("SELECT COUNT(*) FROM rechnungen WHERE LOWER(COALESCE(abschluss, '')) != 'bezahlt'")
                count = cur.fetchone()[0]
                self.card_offen.set_value(str(count))
                # Summe der offenen Rechnungen berechnen
                try:
                    cur.execute("""
                        SELECT COALESCE(SUM(
                            CAST(REPLACE(REPLACE(positionen, 'CHF ', ''), '''', '') AS DECIMAL(10,2))
                        ), 0) FROM rechnungen WHERE LOWER(COALESCE(abschluss, '')) != 'bezahlt'
                    """)
                    summe = cur.fetchone()[0] or 0
                    self.card_offen.set_subtext(f"Total CHF {summe:,.0f}".replace(",", "'"))
                except:
                    pass
            except:
                self.card_offen.set_value("—")
            
            # Umsatz diesen Monat (aus Buchhaltung)
            try:
                heute = datetime.date.today()
                monat_start = heute.replace(day=1).isoformat()
                cur.execute("""
                    SELECT COALESCE(SUM(betrag), 0) FROM buchhaltung 
                    WHERE typ = 'Einnahme' AND datum >= %s
                """.replace("%s", "?") if hasattr(conn, 'is_sqlite') and conn.is_sqlite else """
                    SELECT COALESCE(SUM(betrag), 0) FROM buchhaltung 
                    WHERE typ = 'Einnahme' AND datum >= %s
                """, (monat_start,))
                umsatz = cur.fetchone()[0] or 0
                self.card_umsatz.set_value(f"CHF {umsatz:,.2f}".replace(",", "'"))
            except:
                self.card_umsatz.set_value("—")
            
            # Lieferanten zählen
            try:
                cur.execute("SELECT COUNT(*) FROM lieferanten")
                count = cur.fetchone()[0]
                self.card_lieferanten.set_value(str(count))
            except:
                self.card_lieferanten.set_value("—")
            
            # Termine heute
            try:
                heute = datetime.date.today().isoformat()
                cur.execute("""
                    SELECT COUNT(*) FROM auftraege 
                    WHERE DATE(start_zeit) = %s
                """.replace("%s", "?") if hasattr(conn, 'is_sqlite') and conn.is_sqlite else """
                    SELECT COUNT(*) FROM auftraege 
                    WHERE DATE(start_zeit) = %s
                """, (heute,))
                count = cur.fetchone()[0]
                self.card_termine.set_value(str(count))
            except:
                self.card_termine.set_value("—")
            
            # Lagerwarnungen zählen (Artikel unter Mindestbestand)
            lagerwarnung_count = 0
            try:
                # Materiallager
                try:
                    cur.execute("SELECT COUNT(*) FROM materiallager WHERE bestand <= min_bestand")
                    lagerwarnung_count += cur.fetchone()[0] or 0
                except:
                    pass
                # Artikellager
                try:
                    cur.execute("SELECT COUNT(*) FROM artikellager WHERE bestand <= min_bestand")
                    lagerwarnung_count += cur.fetchone()[0] or 0
                except:
                    pass
                self.card_lagerwarnungen.set_value(str(lagerwarnung_count))
                if lagerwarnung_count > 0:
                    self.card_lagerwarnungen.set_subtext(_("Artikel nachbestellen"))
            except:
                self.card_lagerwarnungen.set_value("—")
            
            # Reifen zählen - nur wenn Modul aktiv
            if self.card_reifen is not None:
                try:
                    cur.execute("SELECT COUNT(*) FROM reifenlager WHERE ausgelagert_am IS NULL OR ausgelagert_am = ''")
                    count = cur.fetchone()[0]
                    self.card_reifen.set_value(str(count))
                except:
                    self.card_reifen.set_value("—")
            
            # Artikel zählen - nur wenn Modul aktiv
            if self.card_artikel is not None:
                try:
                    cur.execute("SELECT COALESCE(SUM(bestand), 0) FROM artikellager")
                    count = cur.fetchone()[0] or 0
                    self.card_artikel.set_value(str(int(count)))
                except:
                    self.card_artikel.set_value("—")
            
            # === Warnungen laden ===
            
            # Überfällige Rechnungen (immer)
            try:
                cur.execute("""
                    SELECT rechnung_nr, kunde, datum, zahlungskonditionen, abschluss 
                    FROM rechnungen 
                    WHERE LOWER(COALESCE(abschluss, '')) != 'bezahlt'
                    ORDER BY datum DESC
                """)
                rows = cur.fetchall()
                items = []
                heute = datetime.date.today()
                for r in rows:
                    rechnung_nr, kunde, datum, zahlungskonditionen, abschluss = r[0], r[1], r[2], r[3], r[4]
                    status_man = (abschluss or "").strip().lower()
                    
                    # Manuell auf überfällig gesetzt
                    if status_man == "überfällig":
                        items.append(f"{rechnung_nr} - {kunde}")
                        continue
                    
                    # Bereits bezahlt -> überspringen
                    if status_man == "bezahlt":
                        continue
                    
                    # Automatische Berechnung: Datum + Zahlungsziel
                    rechnungsdatum = None
                    datum_str = str(datum) if datum else ""
                    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d.%m.%y"):
                        try:
                            rechnungsdatum = datetime.datetime.strptime(datum_str, fmt).date()
                            break
                        except:
                            pass
                    if not rechnungsdatum:
                        continue
                    
                    # Zahlungsziel aus zahlungskonditionen extrahieren (Standard: 10 Tage)
                    ziel_tage = 10
                    if isinstance(zahlungskonditionen, str) and zahlungskonditionen.strip():
                        import re
                        m = re.search(r"(\d+)", zahlungskonditionen)
                        if m:
                            try:
                                ziel_tage = int(m.group(1))
                            except:
                                pass
                    
                    faellig_am = rechnungsdatum + datetime.timedelta(days=ziel_tage)
                    if heute > faellig_am:
                        items.append(f"{rechnung_nr} - {kunde}")
                    
                    if len(items) >= 10:
                        break
                
                self.alert_rechnungen.set_items(items)
            except:
                self.alert_rechnungen.set_items([])
            
            # Alte Reifen (DOT > 5 Jahre) - nur wenn Modul aktiv
            if self.alert_reifen is not None:
                try:
                    aktuelles_jahr = datetime.date.today().year
                    alte_reifen = []
                    cur.execute("SELECT dimension, dot, kunde_anzeige FROM reifenlager WHERE ausgelagert_am IS NULL OR ausgelagert_am = ''")
                    for row in cur.fetchall():
                        try:
                            dot = str(row[1]).strip() if row[1] else ""
                            if len(dot) >= 4:
                                jahr = int(dot[-2:])
                                jahr = 2000 + jahr if jahr < 50 else 1900 + jahr
                                if aktuelles_jahr - jahr >= 5:
                                    alte_reifen.append(f"{row[0]} ({row[2]})")
                        except:
                            pass
                    self.alert_reifen.set_items(alte_reifen)
                except:
                    self.alert_reifen.set_items([])
            
            # Niedriger Lagerbestand (< 5) - nur wenn Modul aktiv
            if self.alert_bestand is not None:
                try:
                    cur.execute("""
                        SELECT bezeichnung, bestand FROM artikellager 
                        WHERE bestand < 5 
                        ORDER BY bestand
                        LIMIT 10
                    """)
                    rows = cur.fetchall()
                    items = [f"{r[0]} (Bestand: {r[1]})" for r in rows]
                    self.alert_bestand.set_items(items)
                except:
                    self.alert_bestand.set_items([])
            
            # Heutige Termine (immer)
            try:
                heute = datetime.date.today().isoformat()
                cur.execute("""
                    SELECT titel, start_zeit FROM auftraege 
                    WHERE DATE(start_zeit) = %s
                    ORDER BY start_zeit
                    LIMIT 10
                """.replace("%s", "?") if hasattr(conn, 'is_sqlite') and conn.is_sqlite else """
                    SELECT titel, start_zeit FROM auftraege 
                    WHERE DATE(start_zeit) = %s
                    ORDER BY start_zeit
                    LIMIT 10
                """, (heute,))
                rows = cur.fetchall()
                items = []
                for r in rows:
                    zeit = str(r[1])[11:16] if r[1] and len(str(r[1])) > 11 else ""
                    items.append(f"{zeit} - {r[0]}" if zeit else r[0])
                self.alert_termine.set_items(items)
            except:
                self.alert_termine.set_items([])
            
            conn.close()
            
        except Exception as e:
            print(f"Dashboard refresh error: {e}")
        
        # Zeitstempel aktualisieren
        jetzt = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        self.last_update_label.setText(_("Letzte Aktualisierung: {}").format(jetzt))
    
    def showEvent(self, event):
        """Aktualisiert Daten wenn Tab sichtbar wird."""
        super().showEvent(event)
        self.refresh_data()
