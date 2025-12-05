# -*- coding: utf-8 -*-
"""
Lizenz-Dialog für INAT Solutions
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QGridLayout, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPixmap, QIcon
from i18n import _
from license import (
    get_license_manager, LICENSE_TRIAL, LICENSE_PROFESSIONAL,
    LICENSE_ENTERPRISE, LICENSE_SUPERUSER
)


class LicenseDialog(QDialog):
    """Dialog zur Anzeige und Aktivierung der Lizenz."""
    
    def __init__(self, parent=None, show_trial_warning: bool = False):
        super().__init__(parent)
        self.setWindowTitle(_("INAT Solutions - Lizenz"))
        self.setMinimumSize(600, 500)
        self.resize(650, 550)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        self.license_manager = get_license_manager()
        self.show_trial_warning = show_trial_warning
        
        self._setup_ui()
        self._update_status()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Header
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #4a6fa5, stop:1 #6b8cbe);
                border-radius: 12px;
            }
        """)
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(25, 20, 25, 20)
        
        title = QLabel("💎 INAT Solutions")
        title.setStyleSheet("color: white; font-size: 29px; font-weight: bold; background: transparent;")
        header_layout.addWidget(title)
        
        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: rgba(255,255,255,0.9); font-size: 14px; background: transparent;")
        header_layout.addWidget(self.status_label)
        
        layout.addWidget(header)
        
        # Trial-Warnung wenn nötig
        if self.show_trial_warning:
            warning = QFrame()
            warning.setStyleSheet("""
                QFrame {
                    background-color: #fff3cd;
                    border: 1px solid #ffc107;
                    border-radius: 8px;
                    padding: 10px;
                }
            """)
            warning_layout = QHBoxLayout(warning)
            warning_label = QLabel(_("⚠️ Ihre Testversion läuft bald ab. Aktivieren Sie eine Lizenz um weiterhin alle Funktionen zu nutzen."))
            warning_label.setStyleSheet("color: #856404; font-size: 13px; background: transparent;")
            warning_label.setWordWrap(True)
            warning_layout.addWidget(warning_label)
            layout.addWidget(warning)
        
        # Pläne
        plans_label = QLabel(_("Verfügbare Pläne"))
        plans_label.setStyleSheet("color: #333; font-size: 16px; font-weight: 600;")
        layout.addWidget(plans_label)
        
        plans_frame = QFrame()
        plans_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 10px;
            }
        """)
        plans_layout = QHBoxLayout(plans_frame)
        plans_layout.setSpacing(15)
        plans_layout.setContentsMargins(15, 15, 15, 15)
        
        # Professional Plan
        pro_card = self._create_plan_card(
            "PROFESSIONAL",
            "$8",
            _("pro Monat"),
            [
                "✓ " + _("Alle Module"),
                "✓ " + _("1 Benutzer"),
                "✓ " + _("E-Mail Support"),
                "✓ " + _("Automatische Updates"),
            ],
            "#4a6fa5"
        )
        plans_layout.addWidget(pro_card)
        
        # Enterprise Plan
        ent_card = self._create_plan_card(
            "ENTERPRISE",
            "$14",
            _("pro Monat"),
            [
                "✓ " + _("Alle Module"),
                "✓ " + _("Unbegrenzte Benutzer"),
                "✓ " + _("Prioritäts-Support"),
                "✓ " + _("Telefon-Support"),
                "✓ " + _("Automatische Updates"),
            ],
            "#28a745",
            is_popular=True
        )
        plans_layout.addWidget(ent_card)
        
        layout.addWidget(plans_frame)
        
        # Lizenzschlüssel-Eingabe
        key_frame = QFrame()
        key_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #dee2e6;
                border-radius: 10px;
                padding: 5px;
            }
        """)
        key_layout = QVBoxLayout(key_frame)
        key_layout.setSpacing(10)
        key_layout.setContentsMargins(15, 15, 15, 15)
        
        key_label = QLabel(_("Lizenzschlüssel eingeben"))
        key_label.setStyleSheet("color: #333; font-size: 14px; font-weight: 500; background: transparent;")
        key_layout.addWidget(key_label)
        
        key_input_layout = QHBoxLayout()
        
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("INAT-XXXX-XXXX-XXXX-XXXX")
        self.key_input.setStyleSheet("""
            QLineEdit {
                padding: 12px 15px;
                font-size: 14px;
                font-family: 'Consolas', 'Courier New', monospace;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                background: white;
            }
            QLineEdit:focus {
                border-color: #4a6fa5;
            }
        """)
        self.key_input.returnPressed.connect(self._activate_license)
        key_input_layout.addWidget(self.key_input)
        
        self.btn_activate = QPushButton(_("Aktivieren"))
        self.btn_activate.setMinimumWidth(120)
        self.btn_activate.setStyleSheet("""
            QPushButton {
                background-color: #4a6fa5;
                color: white;
                border: none;
                padding: 12px 20px;
                font-size: 14px;
                font-weight: 500;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #3b5b85;
            }
            QPushButton:pressed {
                background-color: #2d4a6f;
            }
        """)
        self.btn_activate.clicked.connect(self._activate_license)
        key_input_layout.addWidget(self.btn_activate)
        
        key_layout.addLayout(key_input_layout)
        
        hint_label = QLabel(_("💡 Den Lizenzschlüssel erhalten Sie nach dem Kauf per E-Mail."))
        hint_label.setStyleSheet("color: #666; font-size: 12px; background: transparent;")
        key_layout.addWidget(hint_label)
        
        layout.addWidget(key_frame)
        
        # Footer Buttons
        footer = QHBoxLayout()
        footer.addStretch()
        
        self.btn_later = QPushButton(_("Später"))
        self.btn_later.setMinimumWidth(100)
        self.btn_later.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 10px 20px;
                font-size: 13px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        self.btn_later.clicked.connect(self.reject)
        footer.addWidget(self.btn_later)
        
        layout.addLayout(footer)
    
    def _create_plan_card(self, name: str, price: str, period: str, 
                          features: list, color: str, is_popular: bool = False) -> QFrame:
        """Erstellt eine Plan-Karte."""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border: 1px solid {color if is_popular else '#dee2e6'};
                border-radius: 10px;
            }}
        """)
        
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(8)
        card_layout.setContentsMargins(20, 20, 20, 20)
        
        if is_popular:
            popular = QLabel(_("⭐ BELIEBT"))
            popular.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: bold; background: transparent;")
            popular.setAlignment(Qt.AlignCenter)
            card_layout.addWidget(popular)
        
        title = QLabel(name)
        title.setStyleSheet(f"color: {color}; font-size: 18px; font-weight: bold; background: transparent;")
        title.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(title)
        
        price_label = QLabel(price)
        price_label.setStyleSheet("color: #333; font-size: 32px; font-weight: bold; background: transparent;")
        price_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(price_label)
        
        period_label = QLabel(period)
        period_label.setStyleSheet("color: #666; font-size: 12px; background: transparent;")
        period_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(period_label)
        
        card_layout.addSpacing(10)
        
        for feature in features:
            feat_label = QLabel(feature)
            feat_label.setStyleSheet("color: #444; font-size: 12px; background: transparent;")
            card_layout.addWidget(feat_label)
        
        card_layout.addStretch()
        
        return card
    
    def _update_status(self):
        """Aktualisiert die Status-Anzeige."""
        status = self.license_manager.get_license_status()
        
        type_display = {
            LICENSE_TRIAL: "🕐 " + _("Testversion"),
            LICENSE_PROFESSIONAL: "💼 Professional",
            LICENSE_ENTERPRISE: "🏢 Enterprise",
            LICENSE_SUPERUSER: "👑 Super User"
        }
        
        license_type = status["license_type"]
        display_type = type_display.get(license_type, license_type)
        
        if status["days_remaining"] is not None:
            days_text = _("Noch {} Tage").format(status["days_remaining"])
        else:
            days_text = _("Unbegrenzt")
        
        if status["is_valid"]:
            self.status_label.setText(f"{display_type} • {days_text}")
        else:
            self.status_label.setText(f"{display_type} • ❌ " + _("Abgelaufen"))
    
    def _activate_license(self):
        """Aktiviert den eingegebenen Lizenzschlüssel."""
        key = self.key_input.text().strip()
        
        if not key:
            QMessageBox.warning(
                self, 
                _("Hinweis"), 
                _("Bitte geben Sie einen Lizenzschlüssel ein.")
            )
            return
        
        success, message = self.license_manager.activate_license(key)
        
        if success:
            QMessageBox.information(self, _("Erfolg"), message)
            self._update_status()
            self.accept()
        else:
            QMessageBox.warning(self, _("Fehler"), message)
            self.key_input.selectAll()
            self.key_input.setFocus()


class TrialExpiredDialog(QDialog):
    """Dialog wenn die Trial-Version abgelaufen ist."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Testversion abgelaufen"))
        self.setMinimumSize(500, 350)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint | Qt.WindowStaysOnTopHint)
        self.setModal(True)
        
        self.license_manager = get_license_manager()
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Icon und Titel
        header_layout = QHBoxLayout()
        
        icon_label = QLabel("⏰")
        icon_label.setStyleSheet("font-size: 48px;")
        header_layout.addWidget(icon_label)
        
        title_layout = QVBoxLayout()
        title = QLabel(_("Testversion abgelaufen"))
        title.setStyleSheet("color: #dc3545; font-size: 22px; font-weight: bold;")
        title_layout.addWidget(title)
        
        subtitle = QLabel(_("Ihre 30-tägige Testversion ist beendet."))
        subtitle.setStyleSheet("color: #666; font-size: 14px;")
        title_layout.addWidget(subtitle)
        
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Info
        info = QLabel(_("Um INAT Solutions weiter zu verwenden, aktivieren Sie bitte eine Lizenz."))
        info.setStyleSheet("color: #333; font-size: 14px;")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        # Lizenzschlüssel-Eingabe
        key_layout = QHBoxLayout()
        
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("INAT-XXXX-XXXX-XXXX-XXXX")
        self.key_input.setStyleSheet("""
            QLineEdit {
                padding: 12px 15px;
                font-size: 14px;
                font-family: 'Consolas', 'Courier New', monospace;
                border: 1px solid #dee2e6;
                border-radius: 6px;
            }
            QLineEdit:focus {
                border-color: #4a6fa5;
            }
        """)
        self.key_input.returnPressed.connect(self._activate_license)
        key_layout.addWidget(self.key_input)
        
        btn_activate = QPushButton(_("Aktivieren"))
        btn_activate.setMinimumWidth(120)
        btn_activate.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 12px 20px;
                font-size: 14px;
                font-weight: 500;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        btn_activate.clicked.connect(self._activate_license)
        key_layout.addWidget(btn_activate)
        
        layout.addLayout(key_layout)
        
        layout.addStretch()
        
        # Footer
        footer = QHBoxLayout()
        
        buy_link = QLabel(_("💳 <a href='https://inat-solutions.ch/kaufen'>Lizenz kaufen</a>"))
        buy_link.setStyleSheet("color: #4a6fa5; font-size: 13px;")
        buy_link.setOpenExternalLinks(True)
        footer.addWidget(buy_link)
        
        footer.addStretch()
        
        btn_exit = QPushButton(_("Beenden"))
        btn_exit.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 10px 20px;
                font-size: 13px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        btn_exit.clicked.connect(self.reject)
        footer.addWidget(btn_exit)
        
        layout.addLayout(footer)
    
    def _activate_license(self):
        """Aktiviert den eingegebenen Lizenzschlüssel."""
        key = self.key_input.text().strip()
        
        if not key:
            QMessageBox.warning(
                self, 
                _("Hinweis"), 
                _("Bitte geben Sie einen Lizenzschlüssel ein.")
            )
            return
        
        success, message = self.license_manager.activate_license(key)
        
        if success:
            QMessageBox.information(self, _("Erfolg"), message)
            self.accept()
        else:
            QMessageBox.warning(self, _("Fehler"), message)
            self.key_input.selectAll()
            self.key_input.setFocus()


def check_license_on_startup(parent=None) -> bool:
    """
    Prüft die Lizenz beim App-Start.
    
    Returns: True wenn die App gestartet werden kann, False wenn beenden
    """
    manager = get_license_manager()
    status = manager.get_license_status()
    
    if not status["is_valid"]:
        # Trial abgelaufen - Lizenz-Dialog anzeigen
        dialog = TrialExpiredDialog(parent)
        result = dialog.exec_()
        
        if result == QDialog.Accepted:
            # Lizenz wurde aktiviert
            return True
        else:
            # Benutzer will beenden
            return False
    
    # Warnung wenn Trial bald abläuft (< 7 Tage)
    if status["license_type"] == LICENSE_TRIAL and status["days_remaining"] is not None:
        if status["days_remaining"] <= 7:
            dialog = LicenseDialog(parent, show_trial_warning=True)
            dialog.exec_()
    
    return True
