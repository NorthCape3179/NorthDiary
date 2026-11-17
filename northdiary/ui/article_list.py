from PySide6.QtCore import Signal, Qt, QTimer, QModelIndex, QRectF, QSize, QElapsedTimer
import math
from PySide6.QtGui import QPainter, QPainterPath, QPen, QColor
from PySide6.QtWidgets import QListWidget, QAbstractItemView, QApplication, QLabel, QFrame, QStyledItemDelegate, QStyle, QStyleOptionViewItem
from northdiary.ui.theme import color


class ArticleDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):
        return QSize(0, 66)

    def paint(self, painter, option, index):
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        title, _, metadata = str(index.data(Qt.ItemDataRole.DisplayRole) or '').partition('\n')
        from PySide6.QtGui import QIcon
        icon = QIcon(opt.icon)
        opt.text = ''
        opt.icon = QIcon()
        painter.save()
        opt.widget.style().drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter, opt.widget)
        painter.restore()
        painter.save()
        box = option.rect.adjusted(12, 9, -12, -9)
        if not icon.isNull():
            icon.paint(painter, box.left(), box.center().y()-10, 20, 20)
            box.adjust(28, 0, 0, 0)
        selected = bool(opt.state & QStyle.StateFlag.State_Selected)
        painter.setFont(opt.font)
        painter.setPen(color('#234735' if selected else '#273b37', opt.widget))
        title_rect = box.adjusted(0, 0, 0, -box.height()//2)
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignVCenter,
                         painter.fontMetrics().elidedText(title, Qt.TextElideMode.ElideRight, box.width()))
        small = painter.font(); small.setPixelSize(11); painter.setFont(small)
        painter.setPen(color('#526959' if selected else '#75827a', opt.widget))
        meta_rect = box.adjusted(0, box.height()//2, 0, 0)
        painter.drawText(meta_rect, Qt.AlignmentFlag.AlignVCenter,
                         painter.fontMetrics().elidedText(metadata, Qt.TextElideMode.ElideRight, box.width()))
        painter.restore()


class DragCard(QLabel):
    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setStyleSheet('background: transparent; border: none;')

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        bounds = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        clip = QPainterPath()
        clip.addRoundedRect(bounds, 8, 8)
        painter.setClipPath(clip)
        painter.setOpacity(.68)
        if self.pixmap() and not self.pixmap().isNull():
            painter.drawPixmap(self.rect(), self.pixmap())
        painter.setOpacity(1)
        painter.setPen(QPen(QColor('#c5c7cb'), 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(bounds, 8, 8)


class ArticleList(QListWidget):
    orderRequested = Signal(list)
    draftConfirmRequested = Signal(str)
    WHEEL_STEP = 42.0
    MAX_SCROLL_SPEED = 420.0
    MAX_WHEEL_BACKLOG = 126.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QAbstractItemView.DragDropMode.NoDragDrop)
        self.setItemDelegate(ArticleDelegate(self))
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.setWordWrap(False)
        self.wheel_position = 0.0
        self.wheel_target = 0.0
        self.applying_wheel = False
        self.wheel_clock = QElapsedTimer()
        self.wheel_timer = QTimer(self)
        self.wheel_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.wheel_timer.setInterval(16)
        self.wheel_timer.timeout.connect(self.advance_wheel_scroll)
        scrollbar = self.verticalScrollBar()
        scrollbar.sliderPressed.connect(self.stop_wheel_scroll)
        scrollbar.actionTriggered.connect(self.stop_wheel_scroll)
        scrollbar.rangeChanged.connect(lambda *_: self.stop_wheel_scroll())
        scrollbar.valueChanged.connect(self.track_scroll_position)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setToolTip('按住文章在框内上下移动，松手保存顺序')
        self.moving_item = None
        self.sliding = False
        self.sorting_allowed = True
        self.scroll_timer = QTimer(self)
        self.scroll_timer.setInterval(40)
        self.scroll_timer.timeout.connect(self.slide_step)
        self.ghost = DragCard(self.viewport())
        self.ghost.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.ghost.hide()
        self.drop_line = QFrame(self.viewport())
        self.drop_line.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.drop_line.setStyleSheet('background: #527c61; border-radius: 1px;')
        self.drop_line.hide()

    def stop_wheel_scroll(self):
        self.wheel_timer.stop()
        self.wheel_position = float(self.verticalScrollBar().value())
        self.wheel_target = self.wheel_position

    def track_scroll_position(self, value):
        if not self.applying_wheel:
            self.stop_wheel_scroll()

    def wheelEvent(self, event):
        scrollbar = self.verticalScrollBar()
        if self.sliding or scrollbar.isSliderDown():
            self.stop_wheel_scroll()
            super().wheelEvent(event)
            return
        pixels = event.pixelDelta().y()
        angle = event.angleDelta().y()
        if not pixels and not angle:
            event.ignore()
            return
        if scrollbar.maximum() <= scrollbar.minimum():
            event.ignore()
            return
        delta = -float(pixels)*.8 if pixels else -angle/120.0*self.WHEEL_STEP
        if not self.wheel_timer.isActive():
            self.wheel_position = float(scrollbar.value())
        # Reverse immediately rather than finishing an old queue first.
        if delta*(self.wheel_target-self.wheel_position) < 0:
            self.wheel_target = self.wheel_position
        target = self.wheel_target+delta
        backlog = min(self.MAX_WHEEL_BACKLOG, max(self.WHEEL_STEP, self.viewport().height()*.6))
        target = max(self.wheel_position-backlog, min(self.wheel_position+backlog, target))
        self.wheel_target = max(float(scrollbar.minimum()), min(float(scrollbar.maximum()), target))
        if abs(self.wheel_target-self.wheel_position) >= .5 and not self.wheel_timer.isActive():
            self.wheel_clock.start()
            self.wheel_timer.start()
        event.accept()

    def advance_wheel_scroll(self):
        dt = min(50, max(1, self.wheel_clock.restart()))/1000.0
        remaining = self.wheel_target-self.wheel_position
        step = remaining*(1-math.exp(-dt/.065))
        speed_limit = self.MAX_SCROLL_SPEED*dt
        self.wheel_position += max(-speed_limit, min(speed_limit, step))
        finished = abs(self.wheel_target-self.wheel_position) < .5
        if finished:
            self.wheel_position = self.wheel_target
        self.applying_wheel = True
        try:
            self.verticalScrollBar().setValue(round(self.wheel_position))
        finally:
            self.applying_wheel = False
        if finished:
            self.stop_wheel_scroll()

    def keyPressEvent(self, event):
        self.stop_wheel_scroll()
        super().keyPressEvent(event)

    def hideEvent(self, event):
        self.stop_wheel_scroll()
        super().hideEvent(event)

    def accepts_draft(self, event):
        from northdiary.ui.draft_list import DRAFT_MIME, DraftList
        return isinstance(event.source(), DraftList) and event.source().window() is self.window() and event.mimeData().hasFormat(DRAFT_MIME)

    def dragEnterEvent(self, event):
        if self.accepts_draft(event): event.acceptProposedAction()
        else: event.ignore()

    def dragMoveEvent(self, event):
        if self.accepts_draft(event): event.acceptProposedAction()
        else: event.ignore()

    def dropEvent(self, event):
        from northdiary.ui.draft_list import DRAFT_MIME
        if not self.accepts_draft(event):
            event.ignore(); return
        try:
            key = bytes(event.mimeData().data(DRAFT_MIME)).decode('ascii')
            if len(key) != 36: raise ValueError('invalid article id')
        except (ValueError, UnicodeError):
            event.ignore(); return
        self.draftConfirmRequested.emit(key)
        event.acceptProposedAction()

    def ids(self):
        return [self.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.count())]

    def clear(self):
        self.stop_wheel_scroll()
        self.scroll_timer.stop()
        self.moving_item = None
        self.sliding = False
        self.viewport().unsetCursor()
        self.ghost.hide()
        self.drop_line.hide()
        super().clear()

    def mousePressEvent(self, event):
        self.stop_wheel_scroll()
        super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton and self.sorting_allowed:
            self.moving_item = self.itemAt(event.position().toPoint())
            self.press_position = event.position().toPoint()
            self.before_order = self.ids()
            self.sliding = False
            if self.moving_item:
                rect = self.visualItemRect(self.moving_item)
                self.grab_offset = self.press_position.y()-rect.top()
                self.pending_row = self.row(self.moving_item)

    def mouseMoveEvent(self, event):
        if self.moving_item is None or not event.buttons() & Qt.MouseButton.LeftButton:
            return
        self.pointer_y = event.position().y()
        # Only vertical motion initiates sorting. No native drag or floating pixmap.
        if not self.sliding and abs(self.pointer_y-self.press_position.y()) < QApplication.startDragDistance():
            return
        if not self.sliding:
            rect = self.visualItemRect(self.moving_item)
            self.ghost.setPixmap(self.viewport().grab(rect))
            self.ghost.resize(rect.size())
            self.ghost.show()
        self.sliding = True
        self.viewport().setCursor(Qt.CursorShape.SizeVerCursor)
        if not self.scroll_timer.isActive():
            self.scroll_timer.start()
        self.slide_step()
        event.accept()

    def slide_step(self):
        if self.moving_item is None or not self.sliding:
            return
        height = self.viewport().height()
        y = max(1, min(height-2, int(self.pointer_y)))
        if self.pointer_y < 20:
            self.verticalScrollBar().setValue(self.verticalScrollBar().value()-12)
        elif self.pointer_y > height-20:
            self.verticalScrollBar().setValue(self.verticalScrollBar().value()+12)
        from PySide6.QtCore import QPoint
        target = self.itemAt(QPoint(self.viewport().width()//2, y))
        group_role = Qt.ItemDataRole.UserRole + 1
        group = self.moving_item.data(group_role)
        allowed = [i for i in range(self.count()) if self.item(i).data(group_role) == group]
        if not allowed:
            return
        destination = self.row(target) if target else allowed[-1]
        destination = max(allowed[0], min(allowed[-1], destination))
        self.pending_row = destination
        top = max(0, min(height-self.ghost.height(), int(self.pointer_y-self.grab_offset)))
        self.ghost.move(0, top)
        rect = self.visualItemRect(self.item(destination))
        line_y = rect.bottom() if destination > self.row(self.moving_item) else rect.top()
        self.drop_line.setGeometry(4, max(0, min(height-2, line_y)), self.viewport().width()-8, 2)
        self.drop_line.show()
        self.drop_line.raise_()
        self.ghost.raise_()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return super().mouseReleaseEvent(event)
        self.scroll_timer.stop()
        if self.sliding and self.moving_item is not None:
            source = self.row(self.moving_item)
            destination = self.pending_row
            self.blockSignals(True)
            try:
                if source != destination:
                    self.model().moveRows(QModelIndex(), source, 1, QModelIndex(), destination+1 if destination > source else destination)
            finally:
                self.blockSignals(False)
        changed = self.sliding and self.ids() != getattr(self, 'before_order', [])
        self.ghost.hide()
        self.drop_line.hide()
        self.moving_item = None
        self.sliding = False
        self.viewport().unsetCursor()
        super().mouseReleaseEvent(event)
        if changed:
            self.orderRequested.emit(self.ids())
