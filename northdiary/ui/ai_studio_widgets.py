"""Small painted stationery accents for the native Qt studio."""
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from northdiary.ui.theme import color


class Stationery(QWidget):
    def __init__(self, kind, parent=None):
        super().__init__(parent)
        self.kind = kind
        self.setFixedSize(78, 64)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(color('#7d9b89', self), 1.5, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.setBrush(color('#f0f1eb', self))
        if self.kind == 'appreciation':
            painter.drawRoundedRect(QRectF(12, 8, 46, 49), 3, 3)
            for y in (22, 30, 38, 46):
                painter.drawLine(QPointF(22, y), QPointF(48 if y != 46 else 38, y))
            painter.drawLine(QPointF(54, 45), QPointF(67, 20))
            painter.drawLine(QPointF(54, 45), QPointF(53, 51))
        elif self.kind == 'analysis':
            painter.drawRoundedRect(QRectF(10, 10, 40, 47), 3, 3)
            for y in (23, 31, 39):
                painter.drawLine(QPointF(19, y), QPointF(40, y))
            painter.setBrush(color('#fffefa', self))
            painter.drawEllipse(QRectF(37, 24, 24, 24))
            painter.drawLine(QPointF(58, 45), QPointF(68, 56))
        elif self.kind == 'writing':
            path = QPainterPath(QPointF(10, 16))
            path.cubicTo(22, 10, 28, 12, 38, 18)
            path.cubicTo(49, 12, 59, 10, 70, 16)
            path.lineTo(70, 53)
            path.cubicTo(58, 47, 49, 49, 38, 55)
            path.cubicTo(28, 49, 20, 47, 10, 53)
            path.closeSubpath()
            painter.drawPath(path)
            painter.drawLine(QPointF(38, 18), QPointF(38, 55))
            for y in (27, 35, 43):
                painter.drawLine(QPointF(17, y), QPointF(30, y + 1))
                painter.drawLine(QPointF(46, y + 1), QPointF(62, y))
        else:
            painter.drawRoundedRect(QRectF(10, 10, 45, 31), 7, 7)
            painter.drawLine(QPointF(19, 41), QPointF(17, 49))
            painter.drawLine(QPointF(17, 49), QPointF(29, 41))
            for x in (23, 32, 41):
                painter.drawPoint(QPointF(x, 26))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawArc(QRectF(35, 29, 33, 27), 190 * 16, 250 * 16)
        painter.end()


class ModeCard(QPushButton):
    def __init__(self, kind, title, description, parent=None):
        super().__init__(parent)
        self.setObjectName('studioCard')
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(172)
        self.setAccessibleName(title)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 16, 20, 18)
        layout.setSpacing(6)
        layout.addWidget(Stationery(kind))
        heading = QLabel(title + '  →')
        heading.setStyleSheet('font-size: 18px; font-weight: 600;')
        heading.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(heading)
        detail = QLabel(description)
        detail.setObjectName('muted')
        detail.setWordWrap(True)
        detail.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(detail)
