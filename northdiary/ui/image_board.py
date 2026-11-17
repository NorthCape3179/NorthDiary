import hashlib
from PySide6.QtCore import Qt, QSize, QRectF
from PySide6.QtGui import QPainter, QColor, QPalette, QPen
from PySide6.QtWidgets import QListWidget, QStyledItemDelegate, QWidget, QAbstractItemView
from northdiary.ui.theme import color


def photo_seed(item):
    return int(hashlib.sha256(str(item.data(Qt.ItemDataRole.UserRole)).encode()).hexdigest()[:8], 16)


def photo_size(item, bounds=QSize(80, 80)):
    pixmap = item.icon().pixmap(QSize(480, 480))
    size = pixmap.size() if not pixmap.isNull() else QSize(72, 90)
    return size.scaled(bounds, Qt.AspectRatioMode.KeepAspectRatio)


def paint_photo(painter, rect, item, selected=False, widget=None):
    seed = photo_seed(item)
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.translate(rect.center())
    painter.rotate((seed % 9)-4)
    image_size = photo_size(item, QSize(max(1, round(rect.width()-34)), max(1, round(rect.height()-52))))
    width, height = image_size.width()+14, image_size.height()+32
    card = QRectF(-width/2, -height/2, width, height)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(0, 0, 0, 45))
    painter.drawRoundedRect(card.translated(2, 3), 2, 2)
    accent = color('#315c4d', widget) if widget else QColor('#315c4d')
    painter.setBrush(accent if selected else QColor('#fffefa'))
    painter.setPen(QPen(accent if selected else QColor('#d1cec5'), 1.5 if selected else .6))
    painter.drawRoundedRect(card, 2, 2)
    photo = card.adjusted(7, 7, -7, -25)
    pixmap = item.icon().pixmap(QSize(240, 240))
    if not pixmap.isNull():
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawPixmap(photo, pixmap, QRectF(pixmap.rect()))
    else:
        painter.fillRect(photo, QColor('#d8d6ce'))
    painter.setPen(QColor('#ffffff') if selected else QColor('#515852'))
    font = painter.font()
    font.setPointSize(8)
    painter.setFont(font)
    title = painter.fontMetrics().elidedText(item.text(), Qt.TextElideMode.ElideRight, round(width-10))
    painter.drawText(QRectF(card.left()+5, card.bottom()-21, width-10, 18), Qt.AlignmentFlag.AlignCenter, title)
    if widget:
        from northdiary.ui.theme import theme_name
        if theme_name(widget) == 'letter':
            from northdiary.ui.letter_theme import paint_photo_tape
            paint_photo_tape(painter, card)
    painter.restore()


class PhotoDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        board = self.parent()
        item = board.item(index.row())
        if item:
            paint_photo(painter, QRectF(option.rect), item, item.isSelected(), board)


class PhotoHover(QWidget):
    def __init__(self, board):
        super().__init__(board.viewport())
        self.item = None
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setStyleSheet('background: transparent; border: none;')
        self.hide()

    def paintEvent(self, event):
        if self.item:
            painter = QPainter(self)
            paint_photo(painter, QRectF(self.rect()), self.item, self.item.isSelected(), self)


class ImageBoard(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setViewMode(QListWidget.ViewMode.IconMode)
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setMovement(QListWidget.Movement.Static)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setSpacing(2)
        self.setMouseTracking(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet('QListWidget { border: 1px solid #7f807a; border-radius: 8px; padding: 4px; } QListWidget::item { padding: 0; margin: 0; background: transparent; }')
        self.setItemDelegate(PhotoDelegate(self))
        self.hover_card = PhotoHover(self)
        self.currentItemChanged.connect(lambda *_: self.hover_card.update())
        self.verticalScrollBar().valueChanged.connect(lambda _: self.hover_card.hide())
        self.horizontalScrollBar().valueChanged.connect(lambda _: self.hover_card.hide())
        self.setToolTip('照片板：悬停放大，单击选中，双击查看大图')

    def set_horizontal(self, horizontal):
        self.setFlow(QListWidget.Flow.LeftToRight)
        self.setWrapping(not horizontal)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded if horizontal else Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff if horizontal else Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.doItemsLayout()

    def addItem(self, item):
        item.setSizeHint(photo_size(item) + QSize(34, 52))
        super().addItem(item)

    def clear(self):
        self.hover_card.hide()
        self.hover_card.item = None
        super().clear()

    def paintEvent(self, event):
        painter = QPainter(self.viewport())
        from northdiary.ui.theme import theme_name
        if theme_name(self) == 'letter':
            from northdiary.ui.letter_theme import paint_letter_photos
            paint_letter_photos(self, painter)
            painter.end()
            super().paintEvent(event)
            return
        if theme_name(self) == 'radio':
            painter.fillRect(self.viewport().rect(), QColor('#112230'))
            painter.setPen(QPen(QColor('#253b49'), .6))
            for y in range(6, self.viewport().height(), 7):
                painter.drawLine(5, y, self.viewport().width()-5, y)
            painter.end()
            super().paintEvent(event)
            return
        dark = self.palette().color(QPalette.ColorRole.Window).lightness() < 128
        painter.fillRect(self.viewport().rect(), QColor('#303136' if dark else '#d9d5cb'))
        painter.setPen(QPen(QColor('#3b3c40' if dark else '#ccc8be'), .6))
        for y in range(5, self.viewport().height(), 10):
            for x in range(4, self.viewport().width(), 12):
                offset = (x+y) % 5
                painter.drawLine(x, y+offset, x+3, y+offset+1)
        painter.end()
        super().paintEvent(event)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        item = self.itemAt(event.position().toPoint())
        if item is None:
            self.hover_card.hide()
            return
        rect = self.visualItemRect(item)
        width, height = round(rect.width()*1.22), round(rect.height()*1.22)
        left = max(0, min(self.viewport().width()-width, rect.center().x()-width//2))
        top = max(0, min(self.viewport().height()-height, rect.center().y()-height//2))
        self.hover_card.item = item
        self.hover_card.setGeometry(left, top, width, height)
        self.hover_card.show()
        self.hover_card.raise_()
        self.hover_card.update()

    def leaveEvent(self, event):
        self.hover_card.hide()
        super().leaveEvent(event)
