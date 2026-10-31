"""Persistent pending articles with explicit confirmation and drag-to-confirm."""
from PySide6.QtCore import Qt, Signal, QMimeData, QSize
from PySide6.QtGui import QDrag
from PySide6.QtWidgets import QWidget, QListWidget, QListWidgetItem, QHBoxLayout, QLabel, QToolButton, QApplication, QStyledItemDelegate

DRAFT_MIME = 'application/x-northdiary-draft'


class DraftBackgroundDelegate(QStyledItemDelegate):
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        # The embedded row draws text; retain native selection without painting
        # the same item text underneath it a second time.
        option.text = ''


class DraftRow(QWidget):
    def __init__(self, listing, item, text):
        super().__init__()
        self.listing, self.item = listing, item
        self.key = item.data(Qt.ItemDataRole.UserRole)
        self.press = None
        layout = QHBoxLayout(self); layout.setContentsMargins(7, 3, 3, 3)
        self.label = QLabel(text); self.label.setTextFormat(Qt.TextFormat.PlainText)
        self.label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.label.setMinimumWidth(0)
        layout.addWidget(self.label, 1)
        self.confirm = QToolButton(); self.confirm.setText('✓'); self.confirm.setFixedSize(28, 28)
        self.confirm.setAccessibleName('确认文章：' + text.split('\n')[0])
        self.confirm.setToolTip('确认后加入上方文章列表')
        self.confirm.clicked.connect(lambda: listing.confirmRequested.emit(self.key))
        layout.addWidget(self.confirm)
        self.setToolTip('点击继续编辑；拖到上方文章栏也可确认')

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.press = event.position().toPoint()
            self.listing.setCurrentItem(self.item)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.press is not None and event.buttons() & Qt.MouseButton.LeftButton and (event.position().toPoint()-self.press).manhattanLength() >= QApplication.startDragDistance():
            self.press = None
            payload = QMimeData(); payload.setData(DRAFT_MIME, self.key.encode('ascii'))
            drag = QDrag(self.listing); drag.setMimeData(payload)
            drag.exec(Qt.DropAction.MoveAction)
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.press = None
        super().mouseReleaseEvent(event)


class DraftList(QListWidget):
    confirmRequested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('draftArticleList')
        self.setStyleSheet('QListWidget#draftArticleList::item { padding: 0; margin: 2px 0; }')
        self.setItemDelegate(DraftBackgroundDelegate(self))
        self.setFixedHeight(60)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setAccessibleName('待确认的新文章')

    def ids(self):
        return [self.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.count())]

    def add_article(self, key, text):
        item = QListWidgetItem(text)
        item.setData(Qt.ItemDataRole.UserRole, key)
        item.setSizeHint(QSize(160, 54))
        self.addItem(item)
        row = DraftRow(self, item, text)
        self.setItemWidget(item, row)
        return item
