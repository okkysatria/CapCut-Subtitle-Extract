from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


class Spinner(QWidget):
    def __init__(self, parent=None, size: int = 22, color: str = "#10b981"):
        super().__init__(parent)
        self._angle = 0
        self._color = QColor(color)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self.setFixedSize(size, size)
        sp = self.sizePolicy()
        sp.setRetainSizeWhenHidden(True)
        self.setSizePolicy(sp)
        self.hide()

    def start(self) -> None:
        self._timer.start(25)
        self.show()

    def stop(self) -> None:
        self._timer.stop()
        self.hide()

    def _tick(self) -> None:
        self._angle = (self._angle + 8) % 360
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        try:
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            rect = QRectF(self.rect()).adjusted(3, 3, -3, -3)
            track = QColor(self._color)
            track.setAlpha(45)
            pen = QPen(track)
            pen.setWidth(3)
            p.setPen(pen)
            p.drawEllipse(rect)
            pen = QPen(self._color)
            pen.setWidth(3)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.drawArc(rect, int(-self._angle * 16), 100 * 16)
        finally:
            p.end()


class StatCard(QFrame):
    def __init__(self, title: str, accent: str = "#10b981", parent=None):
        super().__init__(parent)
        self.setObjectName("statCard")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(2)
        self._title = QLabel(title)
        self._title.setObjectName("statTitle")
        self._value = QLabel("0")
        self._value.setObjectName("statValue")
        self._value.setStyleSheet(f"color: {accent};")
        lay.addWidget(self._title)
        lay.addWidget(self._value)

    def set_value(self, n: int) -> None:
        self._value.setText(f"{n:,}".replace(",", "."))
