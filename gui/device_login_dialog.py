from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QApplication, QDialogButtonBox
)
from PyQt5.QtCore import Qt

class DeviceLoginDialog(QDialog):
    """
    Ein Dialog, der den Device-Code-Flow benutzerfreundlich darstellt.
    - Zeigt die URL als klickbaren Link an.
    - Zeigt den Code in einem Feld an und bietet einen Kopieren-Button.
    """
    def __init__(self, flow_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Outlook anmelden")
        self.setMinimumWidth(400)

        # Extrahieren der Daten aus dem Flow-Dictionary
        message = flow_data.get("message", "")
        user_code = flow_data.get("user_code", "CODE NICHT GEFUNDEN")
        verification_uri = flow_data.get("verification_uri", "https://microsoft.com/devicelogin")

        # Layout
        main_layout = QVBoxLayout(self)

        # Anweisungstext
        info_label = QLabel("Um sich anzumelden, öffnen Sie die folgende Seite im Browser und geben Sie den Code ein:")
        info_label.setWordWrap(True)
        main_layout.addWidget(info_label)

        # Klickbarer Link
        link_label = QLabel(f'<a href="{verification_uri}">{verification_uri}</a>')
        link_label.setTextFormat(Qt.RichText)
        link_label.setOpenExternalLinks(True) # Wichtig, damit der Link im Browser öffnet
        main_layout.addWidget(link_label)

        # Layout für Code und Kopieren-Button
        code_layout = QHBoxLayout()
        
        self.code_edit = QLineEdit(user_code)
        self.code_edit.setReadOnly(True) # Nur zum Anzeigen und Kopieren
        self.code_edit.setStyleSheet("font-size: 14px; font-weight: bold;")

        copy_button = QPushButton("Kopieren")
        copy_button.clicked.connect(self.copy_code_to_clipboard)

        code_layout.addWidget(self.code_edit)
        code_layout.addWidget(copy_button)
        main_layout.addLayout(code_layout)

        # OK-Button am Ende
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        main_layout.addWidget(button_box)

    def copy_code_to_clipboard(self):
        """Kopiert den Code in die Zwischenablage."""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.code_edit.text())
        # Optional: Visuelles Feedback geben
        self.code_edit.selectAll()