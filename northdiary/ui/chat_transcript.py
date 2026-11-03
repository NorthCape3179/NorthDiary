"""Native message cards with GitHub Markdown, tables and incremental reply updates."""
import math

from PySide6.QtCore import QEvent, QTimer, Qt
from PySide6.QtGui import QBrush, QColor, QDesktopServices, QImage, QTextDocument, QTextTable, QTextLength, QTextOption
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QScrollArea, QTextBrowser, QToolButton, QVBoxLayout, QWidget
from shiboken6 import isValid

from northdiary.ui.theme import color, style_local


class MessageText(QTextBrowser):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        self.setOpenLinks(False)
        self.anchorClicked.connect(self.open_link)
        self.document().setDocumentMargin(0)
        self.document().documentLayout().documentSizeChanged.connect(self.fit_height)
        self._fitting = False

    def loadResource(self, kind, url):
        # A model's Markdown must not load local files or remote images implicitly.
        return QImage() if kind == QTextDocument.ResourceType.ImageResource else None

    def open_link(self, url):
        if url.scheme().lower() in ('https', 'http'):
            QDesktopServices.openUrl(url)

    def wheelEvent(self, event):
        if event.angleDelta().x() or event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            super().wheelEvent(event)
        else:
            event.ignore()  # Let the conversation scroll when hovering over a message.

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fit_height()

    def fit_height(self, *_):
        if self._fitting:
            return
        self._fitting = True
        try:
            width = max(60, self.viewport().width())
            if abs(self.document().textWidth() - width) > 1:
                self.document().setTextWidth(width)
            height = math.ceil(self.document().size().height()) + 6
            if self.horizontalScrollBar().maximum() > 0:
                height += self.horizontalScrollBar().sizeHint().height()
            height = max(26, height)
            if self.height() != height:
                self.setFixedHeight(height)
        finally:
            self._fitting = False


class MessageCard(QFrame):
    def __init__(self, role, content, model='', stamp='', status='', parent=None):
        super().__init__(parent)
        self.role, self.raw_text = role, content
        self.setObjectName('messageCard')
        background = '#dbe7d8' if role == 'user' else '#fffefa'
        self.setStyleSheet(f'''
            QFrame#messageCard {{ background: {background}; border: 1px solid #dce2d8; border-radius: 12px; }}
            QTextBrowser {{ background: transparent; color: #273b37; border: none; padding: 0; font-size: 15px; }}
            QLabel {{ background: transparent; border: none; }}
            QLabel#messageAvatar {{ background: #315c4d; color: white; border-radius: 14px; font-size: 11px; font-weight: 700; }}
            QLabel#messageRole {{ color: #244d42; font-weight: 600; font-size: 13px; }}
            QLabel#messageMeta {{ color: #75827a; font-size: 11px; }}
            QToolButton {{ border: none; background: transparent; color: #75827a; padding: 4px 6px; border-radius: 5px; }}
            QToolButton:hover {{ background: #e0e8db; }}
        ''')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(9)
        header = QHBoxLayout()
        header.setSpacing(8)
        avatar = QLabel('我' if role == 'user' else 'AI')
        avatar.setObjectName('messageAvatar')
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setFixedSize(28, 28)
        header.addWidget(avatar)
        if role != 'user':
            name = QLabel('DeepSeek')
            name.setObjectName('messageRole')
            header.addWidget(name)
        info = QLabel((model if role != 'user' else '') + (' · ' if model and stamp and role != 'user' else '') + stamp)
        info.setObjectName('messageMeta')
        header.addWidget(info, 1)
        self.copy_button = QToolButton()
        self.copy_button.setText('复制')
        self.copy_button.setToolTip('复制这条消息的原始文字')
        self.copy_button.clicked.connect(lambda: QApplication.clipboard().setText(self.raw_text))
        header.addWidget(self.copy_button)
        layout.addLayout(header)
        self.body = MessageText()
        layout.addWidget(self.body)
        if status:
            footer = QLabel(status)
            footer.setWordWrap(True)
            footer.setObjectName('messageMeta')
            layout.addWidget(footer)
        self._render_pending = False
        style_local(self, self.palette().color(self.palette().ColorRole.Window).lightness() < 128)
        self.render_content()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (QEvent.Type.PaletteChange, QEvent.Type.StyleChange, QEvent.Type.FontChange) and hasattr(self, 'body'):
            if not getattr(self, '_render_pending', False):
                self._render_pending = True
                QTimer.singleShot(0, self.render_content)

    def set_content(self, text):
        self.raw_text = text
        self.render_content()

    def render_content(self):
        if not isValid(self) or not isValid(self.body):
            return
        self._render_pending = False
        ink = color('#273b37', self).name()
        muted = color('#75827a', self).name()
        paper = color('#f0f1eb', self).name()
        border = color('#dce2d8', self).name()
        self.body.document().setDefaultStyleSheet(f'''
            body {{ color: {ink}; }} p {{ margin-top: 5px; margin-bottom: 9px; }}
            h1 {{ font-size: 23px; margin: 10px 0; }} h2 {{ font-size: 20px; margin: 10px 0; }}
            h3 {{ font-size: 17px; margin: 8px 0; }}
            pre {{ background-color: {paper}; padding: 9px; white-space: pre-wrap; }}
            code {{ font-family: Consolas, monospace; background-color: {paper}; }}
            blockquote {{ color: {muted}; margin-left: 14px; }}
            table {{ border: 1px solid {border}; border-collapse: collapse; }}
            th,td {{ padding: 7px; border: 1px solid {border}; }}
        ''')
        if self.role == 'user':
            self.body.setPlainText(self.raw_text)
        elif self.raw_text:
            flags = QTextDocument.MarkdownFeature.MarkdownDialectGitHub | QTextDocument.MarkdownFeature.MarkdownNoHTML
            self.body.document().setMarkdown(self.raw_text, flags)
            self.format_tables(self.body.document().rootFrame())
        else:
            self.body.setPlainText('正在等待回复…')
        self.copy_button.setEnabled(bool(self.raw_text))
        self.body.fit_height()

    def format_tables(self, frame):
        for child in frame.childFrames():
            if isinstance(child, QTextTable):
                fmt = child.format()
                fmt.setWidth(QTextLength(QTextLength.Type.PercentageLength, 100))
                fmt.setBorder(1)
                fmt.setBorderBrush(QBrush(color('#dce2d8', self)))
                fmt.setCellPadding(7)
                fmt.setCellSpacing(0)
                child.setFormat(fmt)
                for row in range(child.rows()):
                    for column in range(child.columns()):
                        cell = child.cellAt(row, column)
                        cell_fmt = cell.format().toTableCellFormat()
                        cell_fmt.setBorder(0.5)
                        cell_fmt.setBorderBrush(QBrush(color('#dce2d8', self)))
                        if row == 0:
                            cell_fmt.setBackground(QBrush(color('#e9ede7', self)))
                        cell.setFormat(cell_fmt)
            self.format_tables(child)

    def fit_width(self, available):
        maximum = max(160, available)
        if self.role == 'user':
            text_width = max((self.body.fontMetrics().horizontalAdvance(line[:200]) for line in self.raw_text.splitlines()), default=160)
            maximum = min(maximum, max(210, text_width + 38), max(210, round(available * .82)))
        self.setFixedWidth(maximum)
        self.body.fit_height()


class ChatTranscript(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('chatTranscript')
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setMinimumHeight(80)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet('QScrollArea#chatTranscript { border: 1px solid #e3e5dd; border-radius: 10px; background: #f6f5f1; }')
        self.canvas = QWidget()
        self.canvas.setObjectName('chatCanvas')
        self.rows = QVBoxLayout(self.canvas)
        self.rows.setContentsMargins(12, 12, 12, 14)
        self.rows.setSpacing(14)
        self.setWidget(self.canvas)
        self.cards = []
        self.last_reply = None
        self.conversation_id = None
        self._stick_bottom = True
        self.verticalScrollBar().rangeChanged.connect(self.on_range_changed)
        self.verticalScrollBar().sliderPressed.connect(lambda: setattr(self, '_stick_bottom', False))
        self.set_turns([])

    def set_turns(self, turns, describe_status=None):
        old_position = self.verticalScrollBar().value()
        same = bool(turns) and turns[0]['conversation_id'] == self.conversation_id
        follow = not same or old_position >= self.verticalScrollBar().maximum() - 35
        self.conversation_id = turns[0]['conversation_id'] if turns else None
        self.cards.clear()
        self.last_reply = None
        while self.rows.count():
            item = self.rows.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not turns:
            empty = QLabel('选择文章，写下你的想法。\n回复将直接显示表格、加粗和列表。')
            empty.setObjectName('muted')
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.rows.addStretch()
            self.rows.addWidget(empty)
        for turn in turns:
            question = turn['instruction'].split('\n自定义指令：\n')[-1]
            if question == '未填写':
                question = turn['instruction'].splitlines()[0]
            stamp = turn['created_at'][11:16]
            self.add_card('user', question, stamp=stamp)
            status = describe_status(turn) if describe_status and turn['status'] not in ('complete', 'running') else ''
            self.last_reply = self.add_card('assistant', turn['response'], turn['model'], stamp, status)
        self.rows.addStretch()
        self._stick_bottom = follow
        self.resize_cards()
        QTimer.singleShot(0, self.scroll_to_bottom if follow else lambda: self.verticalScrollBar().setValue(old_position))

    def add_card(self, role, text, model='', stamp='', status=''):
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        card = MessageCard(role, text, model, stamp, status, row)
        if role == 'user':
            layout.addStretch()
        layout.addWidget(card, 0)
        if role != 'user':
            layout.addStretch()
        self.rows.addWidget(row)
        self.cards.append(card)
        return card

    def append_stream(self, text):
        if self.last_reply is None:
            return
        self._stick_bottom = self.verticalScrollBar().value() >= self.verticalScrollBar().maximum() - 35
        self.last_reply.set_content(self.last_reply.raw_text + text)
        if self._stick_bottom:
            QTimer.singleShot(0, self.scroll_to_bottom)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.resize_cards()

    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            self._stick_bottom = False
        super().wheelEvent(event)

    def resize_cards(self):
        for card in getattr(self, 'cards', []):
            card.fit_width(max(160, self.viewport().width() - 38))

    def scroll_to_bottom(self):
        if isValid(self) and self._stick_bottom:
            self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())

    def on_range_changed(self, *_):
        if self._stick_bottom:
            self.scroll_to_bottom()

    def toPlainText(self):
        return '\n\n'.join(card.raw_text for card in self.cards)
