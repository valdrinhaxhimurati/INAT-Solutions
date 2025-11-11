from PyQt5.QtWidgets import QLineEdit, QWidget, QHBoxLayout, QToolButton
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QIntValidator, QDoubleValidator

class NumericLineEdit(QLineEdit):
    """Simple numeric input that mimics a SpinBox API:
       - value() -> float
       - setValue(x)
       - setRange(min, max)
       - setDecimals(n)
       - emits valueChanged(float) on text change
    """
    valueChanged = pyqtSignal(float)

    def __init__(self, parent=None, decimals: int = 0):
        super().__init__(parent)
        self._decimals = int(decimals or 0)
        self._min = None
        self._max = None
        self._update_validator()
        self.textChanged.connect(self._on_text_changed)

    def _update_validator(self):
        if self._decimals == 0:
            self._validator = QIntValidator(self)
            self.setValidator(self._validator)
        else:
            dv = QDoubleValidator(self)
            dv.setDecimals(self._decimals)
            dv.setNotation(QDoubleValidator.StandardNotation)
            self._validator = dv
            self.setValidator(self._validator)

    def _on_text_changed(self, txt: str):
        try:
            v = float(txt) if txt.strip() != "" else 0.0
        except Exception:
            v = 0.0
        # enforce range if set
        if self._min is not None and v < self._min:
            v = self._min
        if self._max is not None and v > self._max:
            v = self._max
        # do not alter user typing, only emit normalized value
        self.valueChanged.emit(float(v))

    def value(self) -> float:
        txt = self.text().strip()
        if txt == "":
            return 0.0
        try:
            return float(txt)
        except Exception:
            return 0.0

    def setValue(self, v):
        if v is None:
            v = 0.0
        if self._decimals == 0:
            self.setText(str(int(round(float(v)))))
        else:
            fmt = f"{{:.{self._decimals}f}}"
            self.setText(fmt.format(float(v)))

    def setRange(self, minimum, maximum):
        try:
            self._min = float(minimum)
            self._max = float(maximum)
        except Exception:
            self._min = None
            self._max = None

    def setDecimals(self, n: int):
        try:
            self._decimals = int(n)
            self._update_validator()
        except Exception:
            pass

# --- NEU: WindowButtons aus main_window.py hierher verschoben ---
class WindowButtons(QWidget):
    """Ein Widget, das nur die Fenster-Buttons (Min, Max, Close) enthält."""
    def __init__(self, parent):
        super().__init__(parent)
        self.parent_window = parent

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.minimize_btn = QToolButton()
        self.minimize_btn.setObjectName("windowButton")
        self.minimize_btn.setProperty("buttonRole", "minimize")
        
        self.maximize_btn = QToolButton()
        self.maximize_btn.setObjectName("windowButton")
        self.maximize_btn.setProperty("buttonRole", "maximize")
        
        self.close_btn = QToolButton()
        self.close_btn.setObjectName("windowButton")
        self.close_btn.setProperty("buttonRole", "close")

        layout.addWidget(self.minimize_btn)
        layout.addWidget(self.maximize_btn)
        layout.addWidget(self.close_btn)

        self.minimize_btn.clicked.connect(self.parent_window.showMinimized)
        self.maximize_btn.clicked.connect(self.toggle_maximize)
        self.close_btn.clicked.connect(self.parent_window.close)
        
        self.update_maximize_icon()

    def toggle_maximize(self):
        if self.parent_window.isMaximized():
            self.parent_window.showNormal()
        else:
            self.parent_window.showMaximized()
        self.update_maximize_icon()

    def update_maximize_icon(self):
        if self.parent_window.isMaximized():
            self.maximize_btn.setProperty("buttonRole", "restore")
        else:
            self.maximize_btn.setProperty("buttonRole", "maximize")
        # Stil neu anwenden, um das Icon zu ändern
        if self.maximize_btn.style():
            self.maximize_btn.style().unpolish(self.maximize_btn)
            self.maximize_btn.style().polish(self.maximize_btn)