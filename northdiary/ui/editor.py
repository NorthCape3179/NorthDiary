from PySide6.QtCore import Signal, Qt, QTimer, QRectF, QPointF
from PySide6.QtGui import QTextDocument, QTextCharFormat, QColor, QTextCursor, QFontMetricsF, QPainter, QPen
from PySide6.QtWidgets import QTextEdit


class ArticleEditor(QTextEdit):
    imageActivated = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.end_marker_visible = False
        self._updating_end_range = False
        self._end_timer = QTimer(self)
        self._end_timer.setSingleShot(True)
        self._end_timer.timeout.connect(self._refresh_end_range)
        self.document().documentLayout().documentSizeChanged.connect(self._queue_end_range)
        self.verticalScrollBar().rangeChanged.connect(self._queue_end_range)

    def set_end_marker_visible(self, visible):
        self.end_marker_visible = bool(visible)
        self._refresh_end_range()
        self.viewport().update()

    def _queue_end_range(self, *_):
        if not self._updating_end_range and self.end_marker_visible:
            self._end_timer.start(0)

    def _refresh_end_range(self):
        if self._updating_end_range: return
        from math import ceil
        self._updating_end_range = True
        try:
            extra = 60 if self.end_marker_visible else 0
            height = self.document().documentLayout().documentSize().height()
            self.verticalScrollBar().setMaximum(max(0, ceil(height + extra - self.viewport().height())))
        finally:
            self._updating_end_range = False
        self.viewport().update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_end_timer'): self._queue_end_range()

    def scrollContentsBy(self, dx, dy):
        super().scrollContentsBy(dx, dy)
        if getattr(self, 'end_marker_visible', False): self.viewport().update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.end_marker_visible: return
        # Paint outside the document: the decoration is never saved or copied.
        y = self.document().documentLayout().documentSize().height() + 25 - self.verticalScrollBar().value()
        if y < -20 or y > self.viewport().height() + 20: return
        from northdiary.ui.theme import color
        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        font = painter.font()
        font.setPointSizeF(10)
        font.setLetterSpacing(font.SpacingType.AbsoluteSpacing, 2)
        painter.setFont(font)
        metrics = QFontMetricsF(font)
        width = metrics.horizontalAdvance('END')
        center = self.viewport().width()/2
        tint = color('#75827a', self)
        painter.setPen(QPen(tint, 1))
        margin, gap = 28, 16
        if center-width/2-gap > margin:
            painter.drawLine(QPointF(margin, y), QPointF(center-width/2-gap, y))
            painter.drawLine(QPointF(center+width/2+gap, y), QPointF(self.viewport().width()-margin, y))
        painter.drawText(QRectF(center-width/2-2, y-metrics.height()/2, width+4, metrics.height()), Qt.AlignmentFlag.AlignCenter, 'END')
        painter.end()


    def mouseReleaseEvent(self, event):
        href = self.anchorAt(event.position().toPoint())
        if event.button() == Qt.MouseButton.LeftButton and href.startswith('ndiary-image:'):
            self.imageActivated.emit(href.removeprefix('ndiary-image:'))
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def indent_paragraphs(self):
        original = self.textCursor()
        cursor = QTextCursor(self.document())
        cursor.beginEditBlock()
        block = self.document().begin()
        while block.isValid():
            cursor.setPosition(block.position())
            font = cursor.charFormat().font().resolve(self.document().defaultFont())
            fmt = block.blockFormat()
            fmt.setTextIndent(QFontMetricsF(font).horizontalAdvance('中') * 2)
            cursor.setBlockFormat(fmt)
            block = block.next()
        cursor.endEditBlock()
        self.setTextCursor(original)

    def insert_image_link(self, attachment_id, caption):
        cursor = self.textCursor()
        fmt = QTextCharFormat()
        fmt.setAnchor(True)
        fmt.setAnchorHref('ndiary-image:' + attachment_id)
        fmt.setForeground(QColor('#315c4d'))
        fmt.setFontUnderline(True)
        cursor.insertText('▧ ' + caption + ' ↗', fmt)
        cursor.insertText(' ', QTextCharFormat())
        self.setTextCursor(cursor)

    def image_links(self, attachment_id):
        href = 'ndiary-image:' + attachment_id
        block = self.document().begin()
        spans = []
        while block.isValid():
            iterator = block.begin()
            while not iterator.atEnd():
                fragment = iterator.fragment()
                if fragment.isValid() and fragment.charFormat().anchorHref() == href:
                    start, end = fragment.position(), fragment.position() + fragment.length()
                    if spans and spans[-1][1] == start:
                        spans[-1] = (spans[-1][0], end)
                    else:
                        spans.append((start, end))
                iterator += 1
            block = block.next()
        return spans

    def locate_image(self, attachment_id):
        spans = self.image_links(attachment_id)
        if not spans:
            return False
        cursor = self.textCursor()
        cursor.setPosition(spans[0][0])
        cursor.setPosition(spans[0][1], QTextCursor.MoveMode.KeepAnchor)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()
        self.setFocus()
        return True

    def remove_image_links(self, attachment_id):
        cursor = self.textCursor()
        cursor.beginEditBlock()
        for start, end in reversed(self.image_links(attachment_id)):
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()
        cursor.endEditBlock()

    """Paste text only; images must enter through the managed attachment flow."""
    def insertFromMimeData(self, source):
        if source.hasText():
            self.insertPlainText(source.text())

    def loadResource(self, resource_type, name):
        if resource_type == QTextDocument.ResourceType.ImageResource:
            if name.isRelative() and name.toString().startswith('attachments/'):
                from pathlib import PurePosixPath
                if '..' not in PurePosixPath(name.toString()).parts:
                    return super().loadResource(resource_type, name)
            return None
        return super().loadResource(resource_type, name)
