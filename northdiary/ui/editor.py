from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QTextDocument, QTextCharFormat, QColor, QTextCursor, QFontMetricsF
from PySide6.QtWidgets import QTextEdit


class ArticleEditor(QTextEdit):
    imageActivated = Signal(str)

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
