from __future__ import annotations

from typing import Iterable, Sequence, Tuple

from PyQt5.QtWidgets import (
    QLabel,
    QComboBox,
    QSpinBox,
    QDialogButtonBox,
)
from PyQt5.QtCore import Qt

from .base_dialog import BaseDialog


class _BasePromptDialog(BaseDialog):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(420)
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

    def _finalize_layout(self):
        self.content_layout.addWidget(self.button_box, alignment=Qt.AlignRight)


class ItemSelectionDialog(_BasePromptDialog):
    def __init__(self, parent, title: str, label: str, items: Sequence[str], current: int, editable: bool):
        super().__init__(title, parent)
        self.label = QLabel(label)
        self.label.setWordWrap(True)
        self.combo = QComboBox()
        self.combo.setEditable(editable)
        self.combo.addItems([str(i) for i in items])
        if 0 <= current < self.combo.count():
            self.combo.setCurrentIndex(current)
        self.content_layout.setSpacing(12)
        self.content_layout.addWidget(self.label)
        self.content_layout.addWidget(self.combo)
        self._finalize_layout()

    def value(self) -> str:
        return self.combo.currentText()


class IntegerInputDialog(_BasePromptDialog):
    def __init__(self, parent, title: str, label: str, value: int, minimum: int, maximum: int, step: int):
        super().__init__(title, parent)
        self.label = QLabel(label)
        self.label.setWordWrap(True)
        self.spin = QSpinBox()
        self.spin.setRange(minimum, maximum)
        self.spin.setSingleStep(step)
        self.spin.setValue(value)
        self.content_layout.setSpacing(12)
        self.content_layout.addWidget(self.label)
        self.content_layout.addWidget(self.spin)
        self._finalize_layout()

    def value(self) -> int:
        return int(self.spin.value())


def get_item(
    parent,
    title: str,
    label: str,
    items: Sequence[str] | Iterable[str],
    current: int = 0,
    editable: bool = False,
) -> Tuple[str, bool]:
    data = list(items)
    dialog = ItemSelectionDialog(parent, title, label, data, current, editable)
    ok = dialog.exec_() == dialog.Accepted
    return dialog.value(), ok


def get_int(
    parent,
    title: str,
    label: str,
    value: int = 0,
    min_value: int = 0,
    max_value: int = 2147483647,
    step: int = 1,
) -> Tuple[int, bool]:
    dialog = IntegerInputDialog(parent, title, label, value, min_value, max_value, step)
    ok = dialog.exec_() == dialog.Accepted
    return dialog.value(), ok
