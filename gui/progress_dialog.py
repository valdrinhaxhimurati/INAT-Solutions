from __future__ import annotations

from PyQt5.QtWidgets import QLabel, QProgressBar, QPushButton, QHBoxLayout
from PyQt5.QtCore import Qt

from .base_dialog import BaseDialog


class ThemedProgressDialog(BaseDialog):
    def __init__(
        self,
        label_text: str = "",
        cancel_text: str | None = "Abbrechen",
        minimum: int = 0,
        maximum: int = 100,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Bitte warten")
        self._was_canceled = False

        self.label = QLabel(label_text)
        self.label.setObjectName("progressDialogLabel")
        self.label.setWordWrap(True)

        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("progressDialogBar")
        self.progress_bar.setRange(minimum, maximum)

        self.cancel_button = None
        if cancel_text:
            self.cancel_button = QPushButton(cancel_text)
            self.cancel_button.setCursor(Qt.PointingHandCursor)
            self.cancel_button.clicked.connect(self._on_cancel)

        layout = self.content_layout
        layout.setSpacing(12)
        layout.addWidget(self.label)
        layout.addWidget(self.progress_bar)

        if self.cancel_button:
            button_row = QHBoxLayout()
            button_row.addStretch(1)
            button_row.addWidget(self.cancel_button)
            layout.addLayout(button_row)

    def _on_cancel(self) -> None:
        self._was_canceled = True
        self.reject()

    def setLabelText(self, text: str) -> None:
        self.label.setText(text)

    def setRange(self, minimum: int, maximum: int) -> None:
        self.progress_bar.setRange(minimum, maximum)

    def setValue(self, value: int) -> None:
        self.progress_bar.setValue(value)
        if self.progress_bar.maximum() > self.progress_bar.minimum() and value >= self.progress_bar.maximum():
            self.close()

    def value(self) -> int:
        return int(self.progress_bar.value())

    def wasCanceled(self) -> bool:
        return self._was_canceled

    def reset(self) -> None:
        self.progress_bar.reset()
        self._was_canceled = False

    def setCancelButtonText(self, text: str | None) -> None:
        if not self.cancel_button:
            if text:
                self.cancel_button = QPushButton(text)
                self.cancel_button.setCursor(Qt.PointingHandCursor)
                self.cancel_button.clicked.connect(self._on_cancel)
                button_row = QHBoxLayout()
                button_row.addStretch(1)
                button_row.addWidget(self.cancel_button)
                self.content_layout.addLayout(button_row)
            return
        if text:
            self.cancel_button.setText(text)

    def setCancelButton(self, button) -> None:
        if button is None and self.cancel_button:
            self.cancel_button.hide()
            self.cancel_button.setDisabled(True)
        elif button is not None:
            # External buttons werden nicht unterstützt; stattdessen Text setzen
            self.setCancelButtonText(button.text())

    def setCancelButtonVisible(self, visible: bool) -> None:
        if self.cancel_button:
            self.cancel_button.setVisible(visible)
            self.cancel_button.setEnabled(visible)