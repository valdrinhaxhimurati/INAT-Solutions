from PyQt5.QtWidgets import QLineEdit
from PyQt5.QtCore import pyqtSignal
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