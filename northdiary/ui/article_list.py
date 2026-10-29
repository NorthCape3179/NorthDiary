from PySide6.QtCore import Signal, Qt, QTimer, QModelIndex, QRectF
from PySide6.QtGui import QPainter, QPainterPath, QPen, QColor
from PySide6.QtWidgets import QListWidget, QAbstractItemView, QApplication, QLabel, QFrame


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

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QAbstractItemView.DragDropMode.NoDragDrop)
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

    def ids(self):
        return [self.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.count())]

    def clear(self):
        self.scroll_timer.stop()
        self.moving_item = None
        self.sliding = False
        self.viewport().unsetCursor()
        self.ghost.hide()
        self.drop_line.hide()
        super().clear()

    def mousePressEvent(self, event):
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
