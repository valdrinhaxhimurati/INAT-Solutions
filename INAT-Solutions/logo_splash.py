from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer, pyqtSignal
import sys
import os

# Hilfsfunktion, damit PyInstaller-EXE Ressourcen findet:
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

class LogoSplash(QWidget):
    finished = pyqtSignal()

    def __init__(self, logo_path, fadein_ms=1000, fadeout_ms=1200, display_ms=1700, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent;")
        self.setFixedSize(1100, 1100)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        self.logo = QLabel(self)
        # <-- ANPASSUNG: resource_path verwenden!
        pixmap = QPixmap(resource_path(logo_path))
        self.logo.setPixmap(pixmap.scaled(1000, 1000, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.logo.setAlignment(Qt.AlignCenter)
        self.logo.setStyleSheet("background: transparent;")
        layout.addWidget(self.logo)

        self.setWindowOpacity(0.0)

        self.fade_in = QPropertyAnimation(self, b"windowOpacity")
        self.fade_in.setDuration(fadein_ms)
        self.fade_in.setStartValue(0.0)
        self.fade_in.setEndValue(1.0)
        self.fade_in.setEasingCurve(QEasingCurve.InOutQuad)

        self.fade_out = QPropertyAnimation(self, b"windowOpacity")
        self.fade_out.setDuration(fadeout_ms)
        self.fade_out.setStartValue(1.0)
        self.fade_out.setEndValue(0.0)
        self.fade_out.setEasingCurve(QEasingCurve.InOutQuad)
        self.fade_out.finished.connect(self._on_finished)

        self.fade_in.finished.connect(lambda: QTimer.singleShot(display_ms, self.fade_out.start))

    def show(self):
        super().show()
        self.center()
        self.fade_in.start()

    def center(self):
        desktop = self.screen().geometry()
        x = (desktop.width() - self.width()) // 2
        y = (desktop.height() - self.height()) // 2
        self.move(x, y)

    def _on_finished(self):
        self.finished.emit()
        self.close()

