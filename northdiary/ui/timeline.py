from PySide6.QtCore import Qt, QDate, Signal, QPointF, QRectF, QVariantAnimation, QEasingCurve
from PySide6.QtGui import QPainter, QColor, QPen, QFont
from PySide6.QtWidgets import QWidget, QDialog, QVBoxLayout, QCalendarWidget
from northdiary.ui.theme import color
from northdiary.ui.date_picker import DateDialog
import math


class Timeline(QWidget):
    dateSelected = Signal(QDate)
    datePreviewed = Signal(QDate)
    REST_SPACING = 34.0
    DRAG_SPACING = 12.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected = QDate.currentDate()
        self.origin = QDate(self.selected)
        self.position_days = 0.0
        self.view_center = 0.0
        self.spacing = self.REST_SPACING
        self.pressed = False
        self.dragging = False
        self.setMinimumWidth(160)
        self.setFixedHeight(40)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setToolTip('前后三天内保持刻度，超过三天缩放；轻点打开日历')
        self.setAccessibleName('文章时间线')
        self.animation = QVariantAnimation(self)
        self.animation.setDuration(140)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.valueChanged.connect(self.animate_frame)

    def animate_to(self, spacing, center):
        self.animation.stop()
        self.from_spacing, self.to_spacing = self.spacing, spacing
        self.from_center, self.to_center = self.view_center, center
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.start()

    def animate_frame(self, value):
        self.spacing = self.from_spacing + (self.to_spacing-self.from_spacing)*value
        self.view_center = self.from_center + (self.to_center-self.from_center)*value
        self.update()

    def paintEvent(self, event):
        QColor = lambda value: color(value, self)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor('#e9eee7') if self.pressed else QColor('#f1f3ed'))
        painter.drawRoundedRect(QRectF(0, 0, self.width(), self.height()), 10, 10)
        mid = self.width()/2
        y = 25
        painter.setPen(QPen(QColor('#c5d2c5'), 1))
        painter.drawLine(QPointF(12, y), QPointF(self.width()-12, y))
        half = self.width()/2/self.spacing
        step = 7 if self.spacing < 20 else 2
        font = QFont(painter.font())
        font.setPointSize(8)
        painter.setFont(font)
        for day in range(math.floor(self.view_center-half), math.ceil(self.view_center+half)+1):
            x = mid + (day-self.view_center)*self.spacing
            if not 12 <= x <= self.width()-12:
                continue
            date = self.origin.addDays(day)
            painter.setPen(QColor('#a1b3a4'))
            major = date.day() == 1 or day % step == 0
            painter.drawLine(QPointF(x, y-4 if major else y-2), QPointF(x, y+3))
            if major:
                painter.setPen(QColor('#788b7c'))
                painter.drawText(QRectF(x-22, 28, 44, 11), Qt.AlignmentFlag.AlignCenter,
                                 date.toString('M/d') if date.day() == 1 else str(date.day()))
        pointer = mid + (self.position_days-self.view_center)*self.spacing
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor('#d1e1d3'))
        painter.drawEllipse(QPointF(pointer, y), 5.5, 5.5)
        painter.setBrush(QColor('#315c4d'))
        painter.drawEllipse(QPointF(pointer, y), 3, 3)
        painter.setPen(QColor('#244d42'))
        caption_x = max(4, min(self.width()-104, pointer-50))
        painter.drawText(QRectF(caption_x, 2, 100, 20), Qt.AlignmentFlag.AlignCenter, self.selected.toString('yyyy / MM / dd'))

    def setDate(self, date):
        self.animation.stop()
        self.selected = QDate(date)
        self.origin = QDate(date)
        self.position_days = self.view_center = 0.0
        self.spacing = self.REST_SPACING
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_x = event.position().x()
            self.start_position = self.position_days
            self.pressed = True
            self.dragging = False
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            self.animation.stop()
            self.spacing = self.REST_SPACING
            self.update()
            event.accept()

    def mouseMoveEvent(self, event):
        if not self.pressed:
            return
        distance = event.position().x()-self.start_x
        self.dragging |= abs(distance) > 4
        if not self.dragging:
            return
        # Floating point position keeps the pointer continuous between date ticks.
        self.animation.stop()
        threshold = 3*self.REST_SPACING
        if abs(distance) <= threshold:
            self.spacing = self.REST_SPACING
            offset = distance/self.REST_SPACING
        else:
            self.spacing = self.DRAG_SPACING
            offset = math.copysign(3+(abs(distance)-threshold)/self.DRAG_SPACING, distance)
        proposed = self.start_position + offset
        date = self.origin.addDays(round(proposed))
        if not date.isValid() or not 1753 <= date.year() <= 9999:
            return
        changed = date != self.selected
        self.position_days = proposed
        self.selected = date
        limit = self.width()*.24/self.spacing
        self.view_center = max(self.position_days-limit, min(self.position_days+limit, self.view_center))
        self.update()
        if changed: self.datePreviewed.emit(date)

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton or not self.pressed:
            return
        self.pressed = False
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        if self.dragging:
            self.animate_to(self.REST_SPACING, self.position_days)
            self.dateSelected.emit(self.selected)
            return
        self.animate_to(self.REST_SPACING, self.position_days)
        dialog = DateDialog(self.selected, self, '浏览日期')
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.setDate(dialog.selected)
            self.dateSelected.emit(self.selected)
