from __future__ import annotations

from dataclasses import dataclass

from PyQt5.QtWidgets import (
    QLabel,
    QHBoxLayout,
    QDialogButtonBox,
    QMessageBox as QtQMessageBox,
)
from PyQt5.QtCore import Qt

from .base_dialog import BaseDialog


@dataclass(frozen=True)
class _IconMeta:
    symbol: str
    tooltip: str


class StyledMessageBox(BaseDialog):
    """Frameless, themed replacement for the default QMessageBox widgets."""

    _ICON_META = {
        "information": _IconMeta("i", "Information"),
        "warning": _IconMeta("!", "Warnung"),
        "critical": _IconMeta("×", "Fehler"),
        "question": _IconMeta("?", "Bestätigung"),
    }

    _BUTTON_LABELS = {
        QtQMessageBox.Ok: "OK",
        QtQMessageBox.Close: "Schließen",
        QtQMessageBox.Cancel: "Abbrechen",
        QtQMessageBox.Yes: "Ja",
        QtQMessageBox.No: "Nein",
        QtQMessageBox.Apply: "Anwenden",
        QtQMessageBox.Retry: "Erneut versuchen",
        QtQMessageBox.Help: "Hilfe",
        QtQMessageBox.Ignore: "Ignorieren",
        QtQMessageBox.Abort: "Abbrechen",
        QtQMessageBox.Save: "Speichern",
        QtQMessageBox.Open: "Öffnen",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowModality(Qt.ApplicationModal)
        self.setMinimumWidth(420)

        self._clicked_button: QtQMessageBox.StandardButton = QtQMessageBox.NoButton

        self.icon_label = QLabel()
        self.icon_label.setObjectName("messageBoxIcon")
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setFixedSize(60, 60)

        self.message_label = QLabel()
        self.message_label.setObjectName("messageBoxText")
        self.message_label.setWordWrap(True)
        self.message_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        body_layout = QHBoxLayout()
        body_layout.setSpacing(14)
        body_layout.addWidget(self.icon_label, 0, Qt.AlignTop)
        body_layout.addWidget(self.message_label, 1)

        self.button_box = QDialogButtonBox()
        self.button_box.setObjectName("messageBoxButtons")
        # PyQt5 exposes the signal as "clicked(QAbstractButton*)"
        self.button_box.clicked.connect(self._handle_button_clicked)

        self.content_layout.setSpacing(18)
        self.content_layout.addLayout(body_layout)
        self.content_layout.addWidget(self.button_box, alignment=Qt.AlignRight)

    def _prepare(self, level: str, title: str, text: str,
                 buttons: QtQMessageBox.StandardButtons,
                 default_button: QtQMessageBox.StandardButton) -> None:
        meta = self._ICON_META.get(level, self._ICON_META["information"])
        self.setWindowTitle(title)
        self.title_label.setText(title)

        self.icon_label.setText(meta.symbol)
        self.icon_label.setProperty("state", level)
        self.icon_label.setToolTip(meta.tooltip)
        self.icon_label.style().unpolish(self.icon_label)
        self.icon_label.style().polish(self.icon_label)

        self.message_label.setText(text)

        if not buttons:
            buttons = QtQMessageBox.Ok
        if isinstance(buttons, QtQMessageBox.StandardButton):
            buttons = QtQMessageBox.StandardButtons(buttons)
        button_mask = QDialogButtonBox.StandardButtons(int(buttons))
        self.button_box.setStandardButtons(button_mask)
        for button in self.button_box.buttons():
            button.setAutoDefault(False)
            button.setDefault(False)
            button.setCursor(Qt.PointingHandCursor)
            std_button = self.button_box.standardButton(button)
            custom_label = self._BUTTON_LABELS.get(QtQMessageBox.StandardButton(int(std_button)))
            if custom_label:
                button.setText(custom_label)

        self._assign_default_button(default_button)

    def _assign_default_button(self, default_button: QtQMessageBox.StandardButton) -> None:
        if default_button == QtQMessageBox.NoButton:
            buttons = self._available_standard_buttons()
            default_button = buttons[0] if buttons else QtQMessageBox.NoButton

        if default_button != QtQMessageBox.NoButton:
            qt_button = QDialogButtonBox.StandardButton(int(default_button))
            button = self.button_box.button(qt_button)
            if button:
                button.setDefault(True)
                button.setAutoDefault(True)
                button.setFocus()

    def _available_standard_buttons(self) -> list[QtQMessageBox.StandardButton]:
        ordered: list[QtQMessageBox.StandardButton] = []
        for button in self.button_box.buttons():
            std_button = self.button_box.standardButton(button)
            ordered.append(QtQMessageBox.StandardButton(int(std_button)))
        return [btn for btn in ordered if btn != QtQMessageBox.NoButton]

    def _handle_button_clicked(self, button) -> None:
        std_button = self.button_box.standardButton(button)
        self._clicked_button = QtQMessageBox.StandardButton(int(std_button))
        self.accept()

    def exec_(self) -> int:
        result = super().exec_()
        if self._clicked_button == QtQMessageBox.NoButton:
            buttons = self._available_standard_buttons()
            if buttons:
                self._clicked_button = buttons[0]
        return result

    def reject(self) -> None:
        if self._clicked_button == QtQMessageBox.NoButton:
            fallback_order = [
                QtQMessageBox.Cancel,
                QtQMessageBox.No,
                QtQMessageBox.Close,
            ]
            available = set(self._available_standard_buttons())
            for candidate in fallback_order:
                if candidate in available:
                    self._clicked_button = candidate
                    break
        super().reject()

    @property
    def clicked_button(self) -> QtQMessageBox.StandardButton:
        return self._clicked_button

    @classmethod
    def information(
        cls,
        parent,
        title: str,
        text: str,
        buttons: QtQMessageBox.StandardButtons = QtQMessageBox.Ok,
        defaultButton: QtQMessageBox.StandardButton = QtQMessageBox.NoButton,
    ) -> QtQMessageBox.StandardButton:
        return cls._show("information", parent, title, text, buttons, defaultButton)

    @classmethod
    def warning(
        cls,
        parent,
        title: str,
        text: str,
        buttons: QtQMessageBox.StandardButtons = QtQMessageBox.Ok,
        defaultButton: QtQMessageBox.StandardButton = QtQMessageBox.NoButton,
    ) -> QtQMessageBox.StandardButton:
        return cls._show("warning", parent, title, text, buttons, defaultButton)

    @classmethod
    def critical(
        cls,
        parent,
        title: str,
        text: str,
        buttons: QtQMessageBox.StandardButtons = QtQMessageBox.Ok,
        defaultButton: QtQMessageBox.StandardButton = QtQMessageBox.NoButton,
    ) -> QtQMessageBox.StandardButton:
        return cls._show("critical", parent, title, text, buttons, defaultButton)

    @classmethod
    def question(
        cls,
        parent,
        title: str,
        text: str,
        buttons: QtQMessageBox.StandardButtons = QtQMessageBox.Yes | QtQMessageBox.No,
        defaultButton: QtQMessageBox.StandardButton = QtQMessageBox.NoButton,
    ) -> QtQMessageBox.StandardButton:
        return cls._show("question", parent, title, text, buttons, defaultButton)

    @classmethod
    def _show(
        cls,
        level: str,
        parent,
        title: str,
        text: str,
        buttons: QtQMessageBox.StandardButtons,
        default_button: QtQMessageBox.StandardButton,
    ) -> QtQMessageBox.StandardButton:
        dialog = cls(parent)
        dialog._prepare(level, title, text, buttons, default_button)
        dialog.exec_()
        return dialog.clicked_button


_is_patched = False


def install_styled_messagebox() -> None:
    global _is_patched
    if _is_patched:
        return

    QtQMessageBox.information = StyledMessageBox.information
    QtQMessageBox.warning = StyledMessageBox.warning
    QtQMessageBox.critical = StyledMessageBox.critical
    QtQMessageBox.question = StyledMessageBox.question
    _is_patched = True


install_styled_messagebox()
