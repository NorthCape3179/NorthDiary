from PySide6.QtCore import Signal, Qt, QTimer, QRectF, QPointF, QEvent
from PySide6.QtGui import QTextDocument, QTextCharFormat, QColor, QTextCursor, QFont, QFontMetricsF, QPainter, QPen
from PySide6.QtWidgets import QTextEdit


class ArticleEditor(QTextEdit):
    imageActivated = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._preserve_document_font = True
        self.end_marker_visible = False
        self._updating_end_range = False
        self._end_timer = QTimer(self)
        self._end_timer.setSingleShot(True)
        self._end_timer.timeout.connect(self._refresh_end_range)
        self.document().documentLayout().documentSizeChanged.connect(self._queue_end_range)
        self.verticalScrollBar().rangeChanged.connect(self._queue_end_range)
        self._link_timer = QTimer(self)
        self._link_timer.setSingleShot(True)
        self._link_timer.timeout.connect(self.refresh_link_colors)
        self.textChanged.connect(lambda: self._link_timer.start(0))

    def refresh_link_colors(self):
        """Theme image references on screen without changing saved formatting."""
        from northdiary.ui.theme import color, theme_name
        name = theme_name(self)
        tint = QColor('#e1a9be' if name == 'wine' else '#a6cdb4') if name in ('dark', 'wine') else color('#315c4d', self)
        selections = []
        block = self.document().begin()
        while block.isValid():
            it = block.begin()
            while not it.atEnd():
                fragment = it.fragment()
                if fragment.isValid() and fragment.charFormat().anchorHref().startswith('ndiary-image:'):
                    selection = QTextEdit.ExtraSelection()
                    selection.cursor = QTextCursor(self.document())
                    selection.cursor.setPosition(fragment.position())
                    selection.cursor.setPosition(fragment.position()+fragment.length(), QTextCursor.MoveMode.KeepAnchor)
                    selection.format.setForeground(tint)
                    selections.append(selection)
                it += 1
            block = block.next()
        self.setExtraSelections(selections)

    def changeEvent(self, event):
        if event.type() == QEvent.Type.FontChange and getattr(self, '_preserve_document_font', False):
            # QWidget's UI stylesheet must not replace the diary's document font.
            font = QFont(self.document().defaultFont())
            super().changeEvent(event)
            self.document().setDefaultFont(font)
        else:
            super().changeEvent(event)

    def load_body(self, source, default_font):
        """Each saved document owns its typography; preferences seed new entries."""
        from PySide6.QtGui import QTextCharFormat
        self.document().setDefaultFont(default_font)
        self.setCurrentCharFormat(QTextCharFormat())
        self.setHtml(source or '')
        if not source:
            self.document().setDefaultFont(default_font)
            self.setCurrentCharFormat(QTextCharFormat())
        self.refresh_link_colors()

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
        from northdiary.ui.theme import theme_name
        if theme_name(self) == 'letter': self.viewport().update()
        if getattr(self, 'end_marker_visible', False): self.viewport().update()

    def paintEvent(self, event):
        from northdiary.ui.theme import theme_name
        if theme_name(self) == 'letter':
            from northdiary.ui.letter_theme import paint_stationery_rules
            painter = QPainter(self.viewport())
            paint_stationery_rules(self, painter)
            painter.end()
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

    def person_avatar_paths(self):
        from PySide6.QtGui import QTextFormat
        paths = set()
        block = self.document().begin()
        while block.isValid():
            iterator = block.begin()
            while not iterator.atEnd():
                fragment = iterator.fragment()
                fmt = fragment.charFormat()
                if fmt.isImageFormat():
                    image = fmt.toImageFormat()
                    if str(image.property(QTextFormat.Property.ImageAltText) or '').startswith('人物头像：'):
                        paths.add(image.name())
                iterator += 1
            block = block.next()
        return paths

    def insert_person_avatar(self, relative_path, name):
        from PySide6.QtGui import QTextImageFormat, QTextFormat
        if self.isReadOnly(): return
        cursor = self.textCursor()
        previous = cursor.charFormat()
        image = QTextImageFormat()
        image.setName(relative_path); image.setWidth(24); image.setHeight(24)
        image.setVerticalAlignment(QTextCharFormat.VerticalAlignment.AlignMiddle)
        image.setProperty(QTextFormat.Property.ImageAltText, '人物头像：' + name)
        cursor.insertImage(image)
        cursor.setCharFormat(previous if not previous.isImageFormat() else QTextCharFormat())
        self.setTextCursor(cursor)

    def image_links(self, attachment_id):
        href = 'ndiary-image:' + attachment_id
        block = self.document().begin()
        spans = []
        while block.isValid():
            iterator = block.begin()
            while not iterator.atEnd():
                fragment = iterator.fragment()
                fmt = fragment.charFormat()
                from pathlib import PurePosixPath
                image_path = PurePosixPath(fmt.toImageFormat().name()) if fmt.isImageFormat() else None
                inline_image = image_path is not None and image_path.parent.as_posix() == 'attachments' and image_path.stem == attachment_id
                if fragment.isValid() and (fmt.anchorHref() == href or inline_image):
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
