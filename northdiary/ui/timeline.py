from PySide6.QtCore import Qt, QDate, Signal, QPointF, QRectF, QVariantAnimation, QEasingCurve, QTimer, QElapsedTimer
from PySide6.QtGui import QPainter, QColor, QPen, QFont
from PySide6.QtWidgets import QWidget, QDialog, QVBoxLayout, QCalendarWidget
from northdiary.ui.theme import color
from northdiary.ui.date_picker import DateDialog
from northdiary.ui.radio_theme import RadioDial, paint_tuner
import math


class Timeline(QWidget):
    dateSelected = Signal(QDate)
    datePreviewed = Signal(QDate)
    REST_SPACING = 34.0
    DRAG_SPACING = 24.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected = QDate.currentDate()
        self.origin = QDate(self.selected)
        self.position_days = 0.0
        self.view_center = 0.0
        self.spacing = self.REST_SPACING
        self.pressed = False
        self.dragging = False
        self.radio = False
        self.tune_dirty = False
        self.radio_dial = RadioDial(self)
        self.radio_dial.hide()
        self.radio_dial.dayStepped.connect(self.tune_days)
        self.radio_dial.tuningFinished.connect(self.finish_tuning)
        self.setMinimumWidth(160)
        self.setFixedHeight(40)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setToolTip('拖动浏览日期，超过三天后轻微平滑缩放；轻点打开日历')
        self.setAccessibleName('文章时间线')
        self.animation = QVariantAnimation(self)
        self.animation.setDuration(200)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.valueChanged.connect(self.animate_frame)
        self.zoom_target = self.REST_SPACING
        self.drag_pointer = 0.0
        self.zoom_clock = QElapsedTimer()
        self.zoom_timer = QTimer(self)
        self.zoom_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.zoom_timer.setInterval(16)
        self.zoom_timer.timeout.connect(self.animate_zoom)

    def set_radio(self, enabled):
        self.radio = bool(enabled)
        self.radio_dial.setVisible(self.radio)
        self.setMinimumWidth(220 if self.radio else 160)
        self.setFixedHeight(56 if self.radio else 40)
        self.radio_dial.move(self.width()-57, 2)
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.radio_dial.move(self.width()-57, 2)

    def tune_days(self, days):
        date = self.selected.addDays(days)
        if not date.isValid() or not 1753 <= date.year() <= 9999:
            return
        self.selected = date
        self.position_days = self.origin.daysTo(date)
        self.tune_dirty = True
        self.animate_to(self.REST_SPACING, self.position_days)
        self.datePreviewed.emit(date)

    def finish_tuning(self):
        if self.tune_dirty:
            self.tune_dirty = False
            self.dateSelected.emit(QDate(self.selected))

    def animate_zoom(self):
        # Keep one frame clock running; mouse events only update its target.
        # Restarting an animation on every mouse event can starve its frames.
        dt = max(1, self.zoom_clock.restart())
        self.spacing += (self.zoom_target-self.spacing) * (1-math.exp(-dt/55.0))
        if abs(self.zoom_target-self.spacing) < .03:
            self.spacing = self.zoom_target
            self.zoom_timer.stop()
        if self.pressed:
            self.view_center = self.position_days-self.drag_pointer/self.spacing
        self.update()

    def target_zoom(self, spacing):
        self.zoom_target = spacing
        if abs(self.spacing-spacing) > .03 and not self.zoom_timer.isActive():
            self.zoom_clock.start()
            self.zoom_timer.start()

    def drag_scale(self, distance):
        extra = max(0.0, abs(distance)-3*self.REST_SPACING)
        progress = min(1.0, extra/(2*self.REST_SPACING))
        blend = progress*progress*(3-2*progress)
        spacing = self.REST_SPACING+(self.DRAG_SPACING-self.REST_SPACING)*blend
        offset = min(abs(distance), 3*self.REST_SPACING)/self.REST_SPACING + extra/spacing
        return spacing, math.copysign(offset, distance)

    def animate_to(self, spacing, center):
        self.zoom_timer.stop()
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
        if self.radio:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            paint_tuner(self, painter)
            return
        colors = {value: color(value, self) for value in ('#dce2d8', '#e9eee7', '#f1f3ed', '#c5d2c5', '#a1b3a4', '#788b7c', '#d1e1d3', '#315c4d', '#244d42')}
        QColor = colors.__getitem__
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor('#dce2d8'), 1))
        painter.setBrush(QColor('#e9eee7') if self.pressed else QColor('#f1f3ed'))
        painter.drawRoundedRect(QRectF(.5, .5, self.width()-1, self.height()-1), 10, 10)
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
        self.tune_dirty = False
        self.animation.stop()
        self.zoom_timer.stop()
        self.selected = QDate(date)
        self.origin = QDate(date)
        self.position_days = self.view_center = 0.0
        self.spacing = self.REST_SPACING
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_x = event.position().x()
            self.start_position = self.position_days
            self.start_pointer = (self.position_days-self.view_center)*self.spacing
            self.pressed = True
            self.dragging = False
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            self.animation.stop()
            self.zoom_timer.stop()
            self.update()
            event.accept()

    def mouseMoveEvent(self, event):
        if not self.pressed:
            return
        distance = event.position().x()-self.start_x
        self.dragging |= abs(distance) > 4
        if not self.dragging:
            return
        # Date picking is deterministic; visual interpolation never changes it.
        spacing, offset = self.drag_scale(distance)
        proposed = self.start_position + offset
        date = self.origin.addDays(round(proposed))
        if not date.isValid() or not 1753 <= date.year() <= 9999:
            return
        changed = date != self.selected
        self.position_days = proposed
        self.selected = date
        limit = self.width()*.24
        self.drag_pointer = max(-limit, min(limit, self.start_pointer+distance))
        self.view_center = self.position_days-self.drag_pointer/self.spacing
        self.target_zoom(spacing)
        self.update()
        if changed: self.datePreviewed.emit(date)

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton or not self.pressed:
            return
        self.pressed = False
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        if self.dragging:
            self.zoom_timer.stop()
            self.dateSelected.emit(self.selected)
            # Start after synchronous article loading, so it cannot consume the
            # return animation's entire duration before its first frame.
            self.animate_to(self.REST_SPACING, self.position_days)
            return
        self.animate_to(self.REST_SPACING, self.position_days)
        dialog = DateDialog(self.selected, self, '浏览日期')
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.setDate(dialog.selected)
            self.dateSelected.emit(self.selected)
