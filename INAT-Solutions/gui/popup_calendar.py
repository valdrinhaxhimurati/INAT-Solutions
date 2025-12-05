from PyQt5.QtWidgets import QCalendarWidget, QWidget, QToolButton, QLabel, QComboBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QBrush, QColor, QFont

class PopupCalendarWidget(QCalendarWidget):
    """Popup calendar used for QDateEdit popups. Shows the standard navigation
    bar (month/year) and draws appointment dots like the main calendar.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.appointment_dates = set()
        # Ensure navigation bar is visible for popups
        try:
            nav = self.findChild(QWidget, "qt_calendar_navigationbar")
            if nav is not None:
                nav.setVisible(True)
                # name nav buttons so QSS rules for Auftragskalender apply
                try:
                    for tb in nav.findChildren(QToolButton):
                        tb.setObjectName("calendarNavButton")
                except Exception:
                    pass
                # try to find month/year label/combo and set name for styling
                try:
                    for w in nav.findChildren((QLabel, QComboBox)):
                        w.setObjectName("calendarTitleLabel")
                except Exception:
                    pass
        except Exception:
            pass

    def set_appointment_dates(self, dates):
        self.appointment_dates = set(dates)
        self.updateCells()

    def paintCell(self, painter, rect, date):
        super().paintCell(painter, rect, date)
        if date in self.appointment_dates:
            painter.save()
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setBrush(QBrush(QColor("#e53935")))  # red dot
            painter.setPen(Qt.NoPen)
            dot_diameter = 6
            x = rect.x() + (rect.width() / 2) - (dot_diameter / 2)
            y = rect.y() + rect.height() - dot_diameter - 4
            painter.drawEllipse(int(x), int(y), dot_diameter, dot_diameter)
            painter.restore()
