# -*- coding: utf-8 -*-
"""
Gemeinsame Styles für alle Dialoge
"""

# GroupBox-Styling für konsistentes Aussehen
GROUPBOX_STYLE = """
    QGroupBox {
        font-weight: 600;
        font-size: 14px;
        color: #1f2937;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        margin-top: 12px;
        padding: 16px;
        background-color: #ffffff;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 6px;
        color: #1f2937;
    }
    QGroupBox QPushButton {
        background-color: #4a6fa5;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 10px 24px;
        font-weight: 500;
        font-size: 14px;
        min-height: 36px;
        min-width: 120px;
    }
    QGroupBox QPushButton:hover {
        background-color: #3d5d8a;
    }
"""

# Primärer Button (Speichern, OK, Start)
PRIMARY_BUTTON_STYLE = """
    QPushButton {
        background-color: #4a6fa5;
        color: white;
        font-weight: 500;
        font-size: 14px;
        border-radius: 6px;
        border: none;
        padding: 8px 16px;
        min-height: 32px;
    }
    QPushButton:hover {
        background-color: #3d5d8a;
    }
    QPushButton:disabled {
        background-color: #9ca3af;
    }
"""

# Erfolgs-Button (Grün)
SUCCESS_BUTTON_STYLE = """
    QPushButton {
        background-color: #10b981;
        color: white;
        font-weight: 500;
        font-size: 14px;
        border-radius: 6px;
        border: none;
        padding: 8px 16px;
        min-height: 32px;
    }
    QPushButton:hover {
        background-color: #059669;
    }
    QPushButton:disabled {
        background-color: #9ca3af;
    }
"""

# Gefahr-Button (Löschen)
DANGER_BUTTON_STYLE = """
    QPushButton {
        background-color: #ef4444;
        color: white;
        font-weight: 500;
        font-size: 14px;
        border-radius: 6px;
        border: none;
        padding: 8px 16px;
        min-height: 32px;
    }
    QPushButton:hover {
        background-color: #dc2626;
    }
"""

# Sekundärer Button (Abbrechen)
SECONDARY_BUTTON_STYLE = """
    QPushButton {
        background-color: #ffffff;
        color: #374151;
        border: 1px solid #e5e7eb;
        border-radius: 6px;
        font-weight: 500;
        font-size: 14px;
        padding: 8px 16px;
        min-height: 32px;
    }
    QPushButton:hover {
        background-color: #f9fafb;
        border-color: #d1d5db;
    }
"""

# Info-Label Styling
INFO_LABEL_STYLE = "color: #6b7280; font-size: 13px;"

# Pflichtfeld-Label Styling
REQUIRED_LABEL_STYLE = "color: #ef4444; font-weight: 600;"
