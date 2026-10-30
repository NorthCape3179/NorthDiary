"""Read-only memories; displaying a memory never changes editor/recent state."""
from pathlib import PurePosixPath
import random

from lxml import html, etree
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QFont, QTextDocument
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QListWidgetItem

from northdiary.ui.date_picker import parse_partial
from northdiary.ui.image_board import ImageBoard
from northdiary.ui.image_viewer import ImageViewer, read_image
from northdiary.ui.season_background import SeasonPaper
from northdiary.ui.theme import apply_theme, theme_name


def plain_memory_text(source):
    document = html.document_fromstring(source or '<p></p>')
    for node in document.xpath('//head|//script|//style|//img|//a[starts-with(@href,"ndiary-image:")]'):
        # Keep adjacent paragraph text, but put images only on the photo board.
        if node.getparent() is not None:
            node.drop_tree()
    text = QTextDocument()
    text.setHtml(etree.tostring(document, encoding='unicode', method='html'))
    return text.toPlainText().replace('\ufffc', '')


class MemoryDialog(QDialog):
    def __init__(self, repository, attachments, parent=None, article_id=None, chooser=None):
        super().__init__(parent)
        self.repository, self.attachments = repository, attachments
        self.root = repository.database.root
        self.current_id = None
        self.images = []
        self.random_mode = article_id is None
        self.chooser = chooser or random.choice
        self.setWindowTitle('随机回忆' if self.random_mode else '回忆阅读')
        self.resize(950, 760)
        self.setMinimumSize(620, 480)
        layout = QVBoxLayout(self)
        self.paper = SeasonPaper()
        self.paper.setObjectName('paper')
        column = QVBoxLayout(self.paper)
        column.setContentsMargins(30, 24, 30, 18)
        self.title = QLabel()
        self.title.setTextFormat(Qt.TextFormat.PlainText)
        self.title.setWordWrap(True)
        font = QFont(self.font())
        font.setPixelSize(25)
        font.setWeight(QFont.Weight.DemiBold)
        self.title.setFont(font)
        self.title.setStyleSheet('QLabel { font-size: 25px; font-weight: 600; background: transparent; }')
        column.addWidget(self.title)
        self.date = QLabel()
        self.date.setObjectName('muted')
        self.date.setTextFormat(Qt.TextFormat.PlainText)
        column.addWidget(self.date)
        self.editor = QTextEdit()
        self.editor.setReadOnly(True)
        self.editor.setAcceptRichText(False)
        self.editor.setStyleSheet('QTextEdit { background: transparent; border: none; }')
        self.editor.viewport().setAutoFillBackground(False)
        self.editor.setAutoFillBackground(False)
        self.editor.setAccessibleName('回忆正文，只读')
        column.addWidget(self.editor, 1)
        self.image_list = ImageBoard()
        self.image_list.setIconSize(QSize(96, 72))
        self.image_list.set_horizontal(True)
        self.image_list.setFixedHeight(170)
        self.image_list.itemDoubleClicked.connect(self.open_image)
        column.addWidget(self.image_list)
        layout.addWidget(self.paper, 1)
        row = QHBoxLayout()
        row.addStretch()
        self.next_button = QPushButton('再看一篇')
        self.next_button.clicked.connect(self.next_memory)
        self.next_button.setVisible(self.random_mode)
        row.addWidget(self.next_button)
        close = QPushButton('关闭')
        close.clicked.connect(self.accept)
        row.addWidget(close)
        layout.addLayout(row)
        dark = parent.palette().color(parent.palette().ColorRole.Window).lightness() < 128 if parent else False
        apply_theme(self, dark, theme_name(parent) if parent else None)
        if self.random_mode:
            self.next_memory()
        else:
            self.show_article(article_id)

    def empty(self, text='还没有可回忆的文章'):
        self.current_id = None
        self.images = []
        self.title.setText(text)
        self.date.clear()
        self.editor.clear()
        self.image_list.clear()
        self.image_list.hide()
        self.next_button.setEnabled(False)

    def next_memory(self):
        articles = self.repository.list()
        if not articles:
            self.empty()
            return
        candidates = [article for article in articles if article.id != self.current_id] or articles
        self.show_article(self.chooser(candidates).id)
        self.next_button.setEnabled(len(articles) > 1)

    def show_article(self, article_id):
        try:
            article = self.repository.get(article_id)
        except KeyError:
            self.empty('这篇文章已不存在')
            return
        if article.deleted_at:
            self.empty('这篇文章已移入回收站')
            return
        self.current_id = article.id
        self.title.setText(article.title)
        self.date.setText(article.diary_date)
        self.editor.setPlainText(plain_memory_text(article.body_html))
        self.editor.verticalScrollBar().setValue(0)
        date, precision = parse_partial(article.diary_date)
        self.paper.month_unknown = precision == 'year' or not date.isValid()
        self.paper.set_article_date(date)
        self.paper.refresh_background(force=True)
        self.images = []
        self.image_list.clear()
        for row in self.attachments.list(article.id):
            relative = PurePosixPath(row['relative_path'])
            path = (self.root / row['relative_path']).resolve()
            if (not row['mime_type'].startswith('image/') or relative.is_absolute()
                    or not relative.parts or relative.parts[0] != 'attachments' or '..' in relative.parts
                    or not path.is_relative_to(self.root / 'attachments')):
                continue
            self.images.append(row)
            item = QListWidgetItem(row['caption'] or row['name'])
            item.setData(Qt.ItemDataRole.UserRole, row['id'])
            item.setToolTip(row['caption'] or row['name'])
            try:
                item.setIcon(QIcon(read_image(path, 180)))
            except ValueError:
                item.setText('图片缺失 · ' + item.text())
            self.image_list.addItem(item)
        self.image_list.setVisible(bool(self.images))

    def open_image(self, item):
        key = item.data(Qt.ItemDataRole.UserRole)
        index = next((index for index, row in enumerate(self.images) if row['id'] == key), None)
        if index is not None:
            viewer = ImageViewer(self.images, index, self.root, self)
            viewer.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
            viewer.exec()
