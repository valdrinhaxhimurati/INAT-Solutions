import sys
import os
from PyQt5.QtWidgets import QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel
# NEU: QPoint importieren
from PyQt5.QtCore import Qt, QEvent, QPoint
from PyQt5.QtGui import QIcon, QPixmap

# Wiederverwendbare Komponenten importieren
from .widgets import WindowButtons

# Logik für das Verschieben und Ändern der Größe (aus MainWindow kopiert)
if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes
    from PyQt5.QtWinExtras import QtWin

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class CustomTitleBar(QWidget):
    """Ein Widget, das nur als Platzhalter für den Titelbereich dient."""
    def __init__(self, parent):
        super().__init__(parent)
        self.parent_window = parent

class BaseDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Fenstereigenschaften für rahmenloses Design
        self.setWindowFlags(Qt.FramelessWindowHint | self.windowFlags())
        self.setWindowIcon(QIcon(resource_path("icons/logo.svg")))

        # Hauptlayout
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(1, 1, 1, 1) # Dünner Rahmen
        self._main_layout.setSpacing(0)

        # Titel-Leiste
        self.title_bar = CustomTitleBar(self)
        self.title_bar.setFixedHeight(48)
        self.title_bar.setObjectName("dialogTitleBar")
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(10, 0, 0, 0)
        title_layout.setSpacing(10)

        # Logo
        icon_label = QLabel()
        icon_pixmap = QPixmap(resource_path("icons/logo.svg")).scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        icon_label.setPixmap(icon_pixmap)
        title_layout.addWidget(icon_label)

        # Titel-Text
        self.title_label = QLabel("Dialog")
        self.title_label.setObjectName("dialogTitleLabel")
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()

        # Fenster-Buttons (Dialoge nur mit Schließen)
        self.window_buttons = WindowButtons(self, show_minimize=False, show_maximize=False)
        title_layout.addWidget(self.window_buttons)
        
        self._main_layout.addWidget(self.title_bar)

        # Inhaltsbereich für Subklassen
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(15, 15, 15, 15)
        self._main_layout.addWidget(self.content_widget)

    def setWindowTitle(self, title):
        """Überschreibt die Standardmethode, um unser Label zu aktualisieren."""
        super().setWindowTitle(title)
        self.title_label.setText(title)

    def changeEvent(self, event):
        """Sorgt dafür, dass das Maximize-Icon korrekt aktualisiert wird."""
        if event.type() == QEvent.WindowStateChange:
            if hasattr(self, 'window_buttons'):
                self.window_buttons.update_maximize_icon()
        super().changeEvent(event)

    def nativeEvent(self, eventType, message):
        """Fängt native Windows-Nachrichten für Drag & Resize ab."""
        retval, result = super().nativeEvent(eventType, message)
        
        if sys.platform == "win32" and eventType == b"windows_generic_MSG":
            msg = ctypes.wintypes.MSG.from_address(message.__int__())

            if msg.message == 0x0084:  # WM_NCHITTEST
                # Korrekte Extraktion der globalen Mausposition
                x_global = ctypes.c_short(msg.lParam & 0xFFFF).value
                y_global = ctypes.c_short((msg.lParam >> 16) & 0xFFFF).value
                
                # KORREKTUR: Globale Position in ein QPoint-Objekt umwandeln
                global_pos = QPoint(x_global, y_global)
                local_pos = self.mapFromGlobal(global_pos)
                
                # Größenänderung an den Fensterrändern (höchste Priorität)
                border_width = 8
                rect = self.rect()
                
                # Ecken haben Vorrang
                if local_pos.x() < border_width and local_pos.y() < border_width: 
                    return True, 13  # HTTOPLEFT
                if local_pos.x() > rect.width() - border_width and local_pos.y() < border_width: 
                    return True, 14  # HTTOPRIGHT
                if local_pos.x() < border_width and local_pos.y() > rect.height() - border_width: 
                    return True, 16  # HTBOTTOMLEFT
                if local_pos.x() > rect.width() - border_width and local_pos.y() > rect.height() - border_width: 
                    return True, 17  # HTBOTTOMRIGHT
                
                # Kanten
                if local_pos.y() < border_width: 
                    return True, 12  # HTTOP
                if local_pos.y() > rect.height() - border_width: 
                    return True, 15  # HTBOTTOM
                if local_pos.x() < border_width: 
                    return True, 10  # HTLEFT
                if local_pos.x() > rect.width() - border_width: 
                    return True, 11  # HTRIGHT
                
                # Titelleiste (nur wenn nicht an den Rändern)
                if self.title_bar.rect().contains(self.title_bar.mapFromGlobal(global_pos)):
                    # Prüfen, ob die Maus über den Fenster-Buttons ist
                    if self.window_buttons.rect().contains(self.window_buttons.mapFromGlobal(global_pos)):
                        return retval, result # Qt übernimmt
                    
                    # Ansonsten ist es die Titelleiste zum Verschieben
                    return True, 2  # HTCAPTION

        return retval, result