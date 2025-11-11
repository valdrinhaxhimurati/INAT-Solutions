from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QApplication, QDialogButtonBox
)
from PyQt5.QtCore import Qt
# NEU: BaseDialog importieren
from .base_dialog import BaseDialog

# ÄNDERUNG: Von BaseDialog erben
class DeviceLoginDialog(BaseDialog):
    """
    Ein Dialog, der den Device-Code-Flow benutzerfreundlich darstellt.
    - Zeigt die URL als klickbaren Link an.
    - Zeigt den Code in einem Feld an und bietet einen Kopieren-Button.
    """
    def __init__(self, flow_data, parent=None):
        # ÄNDERUNG: super() für BaseDialog aufrufen
        super().__init__(parent)
        self.setWindowTitle("Outlook anmelden")
        self.setMinimumWidth(450)

        # Extrahieren der Daten aus dem Flow-Dictionary
        user_code = flow_data.get("user_code", "CODE NICHT GEFUNDEN")
        verification_uri = flow_data.get("verification_uri", "https://microsoft.com/devicelogin")

        # WICHTIG: Das Layout vom BaseDialog verwenden
        main_layout = self.content_layout

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
        # DIESE METHODE BLEIBT UNVERÄNDERT
        clipboard = QApplication.clipboard()
        clipboard.setText(self.code_edit.text())
        # Optional: Visuelles Feedback geben
        self.code_edit.selectAll()