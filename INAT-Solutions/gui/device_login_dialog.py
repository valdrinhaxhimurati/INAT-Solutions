from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QApplication, QDialogButtonBox, QGroupBox
)
from PyQt5.QtCore import Qt
from .base_dialog import BaseDialog
from .dialog_styles import GROUPBOX_STYLE
from i18n import _


class DeviceLoginDialog(BaseDialog):
    """
    Ein Dialog, der den Device-Code-Flow benutzerfreundlich darstellt.
    - Zeigt die URL als klickbaren Link an.
    - Zeigt den Code in einem Feld an und bietet einen Kopieren-Button.
    """
    def __init__(self, flow_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Outlook anmelden"))
        self.resize(480, 280)

        # Extrahieren der Daten aus dem Flow-Dictionary
        user_code = flow_data.get("user_code", "CODE NICHT GEFUNDEN")
        verification_uri = flow_data.get("verification_uri", "https://microsoft.com/devicelogin")

        layout = self.content_layout
        layout.setSpacing(15)

        # === Anmeldung ===
        login_group = QGroupBox(_("Anmeldung erforderlich"))
        login_group.setStyleSheet(GROUPBOX_STYLE)
        login_layout = QVBoxLayout(login_group)
        login_layout.setSpacing(10)

        # Anweisungstext
        info_label = QLabel(_("Um sich anzumelden, öffnen Sie die folgende Seite im Browser und geben Sie den Code ein:"))
        info_label.setWordWrap(True)
        login_layout.addWidget(info_label)

        # Klickbarer Link
        link_label = QLabel(f'<a href="{verification_uri}">{verification_uri}</a>')
        link_label.setTextFormat(Qt.RichText)
        link_label.setOpenExternalLinks(True)
        login_layout.addWidget(link_label)

        # Layout für Code und Kopieren-Button
        code_layout = QHBoxLayout()
        
        self.code_edit = QLineEdit(user_code)
        self.code_edit.setReadOnly(True)
        self.code_edit.setStyleSheet("font-size: 14px; font-weight: bold;")

        copy_button = QPushButton(_("Kopieren"))
        copy_button.clicked.connect(self.copy_code_to_clipboard)

        code_layout.addWidget(self.code_edit)
        code_layout.addWidget(copy_button)
        login_layout.addLayout(code_layout)

        layout.addWidget(login_group)

        layout.addStretch()

        # === Buttons (zentriert) ===
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_ok = QPushButton(_("OK"))
        btn_ok.clicked.connect(self.accept)
        btn_layout.addWidget(btn_ok)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def copy_code_to_clipboard(self):
        """Kopiert den Code in die Zwischenablage."""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.code_edit.text())
        self.code_edit.selectAll()