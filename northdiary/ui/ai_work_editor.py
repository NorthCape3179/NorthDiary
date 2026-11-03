from PySide6.QtGui import QFont, QTextCharFormat, QTextListFormat
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QTextEdit, QVBoxLayout, QWidget

from northdiary.storage.ai_works import CATEGORIES
from northdiary.ui.ai_sources import inherit_theme
from northdiary.ui.controls import ComboBox


class WorkEditor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.toolbar = QWidget()
        row = QHBoxLayout(self.toolbar)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(5)
        for title, attribute in [('加粗', 'bold'), ('斜体', 'italic'), ('下划线', 'underline')]:
            button = QPushButton(title)
            button.clicked.connect(lambda checked=False, kind=attribute: self.format_text(kind))
            row.addWidget(button)
        self.paragraph = ComboBox()
        self.paragraph.addItems(['正文', '标题一', '标题二', '引用'])
        self.paragraph.activated.connect(self.format_paragraph)
        row.addWidget(self.paragraph)
        for title, style in [('列表', QTextListFormat.Style.ListDisc), ('编号', QTextListFormat.Style.ListDecimal)]:
            button = QPushButton(title)
            button.clicked.connect(lambda checked=False, chosen=style: self.make_list(chosen))
            row.addWidget(button)
        row.addStretch()
        layout.addWidget(self.toolbar)
        self.editor = QTextEdit()
        self.editor.setObjectName('studioResult')
        self.editor.setAcceptRichText(True)
        layout.addWidget(self.editor, 1)

    def set_read_only(self, value):
        self.editor.setReadOnly(value)
        self.toolbar.setVisible(not value)

    def format_text(self, kind):
        current = self.editor.currentCharFormat()
        fmt = QTextCharFormat()
        if kind == 'bold':
            fmt.setFontWeight(QFont.Weight.Normal if current.fontWeight() >= QFont.Weight.Bold else QFont.Weight.Bold)
        elif kind == 'italic':
            fmt.setFontItalic(not current.fontItalic())
        else:
            fmt.setFontUnderline(not current.fontUnderline())
        self.editor.mergeCurrentCharFormat(fmt)
        self.editor.setFocus()

    def format_paragraph(self, index):
        cursor = self.editor.textCursor()
        fmt = cursor.blockFormat()
        fmt.setHeadingLevel(index if index in (1, 2) else 0)
        fmt.setLeftMargin(18 if index == 3 else 0)
        cursor.mergeBlockFormat(fmt)
        char = QTextCharFormat()
        char.setFontPointSize({0: 11, 1: 20, 2: 16, 3: 11}[index])
        char.setFontWeight(QFont.Weight.Bold if index in (1, 2) else QFont.Weight.Normal)
        char.setFontItalic(index == 3)
        cursor.mergeCharFormat(char)
        self.editor.setTextCursor(cursor)
        self.editor.setFocus()

    def make_list(self, style):
        fmt = QTextListFormat()
        fmt.setStyle(style)
        self.editor.textCursor().createList(fmt)
        self.editor.setFocus()


class SaveWorkDialog(QDialog):
    def __init__(self, repository, data, parent=None, target=None):
        super().__init__(parent)
        self.repository, self.data = repository, dict(data)
        self.work_id = None
        self.setWindowTitle('保存 AI 作品')
        self.resize(840, 660)
        self.setMinimumSize(650, 480)
        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        self.title = QLineEdit(data['title'])
        self.title.setPlaceholderText('作品标题')
        row.addWidget(self.title, 1)
        self.category = ComboBox()
        self.category.addItems(CATEGORIES)
        self.category.setCurrentText(data['category'])
        row.addWidget(self.category)
        layout.addLayout(row)
        destination = QHBoxLayout()
        destination.addWidget(QLabel('保存到'))
        self.target = ComboBox()
        self.target.addItem('新建独立作品', None)
        for work in repository.list():
            self.target.addItem(f"{work['title']} · 新增版本", work['id'])
        self.target.currentIndexChanged.connect(self.choose_target)
        self.target.setCurrentIndex(max(0, self.target.findData(target)))
        destination.addWidget(self.target, 1)
        layout.addLayout(destination)
        self.content = WorkEditor()
        self.content.editor.setHtml(data['body_html'])
        layout.addWidget(self.content, 1)
        hint = QLabel('保存为独立作品；追加到已有作品时会新增版本，原文和对话回复保留。')
        hint.setObjectName('muted')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        footer = QHBoxLayout()
        footer.addStretch()
        cancel = QPushButton('取消')
        cancel.clicked.connect(self.reject)
        save = QPushButton('保存作品')
        save.setObjectName('primary')
        save.clicked.connect(self.save_work)
        footer.addWidget(cancel)
        footer.addWidget(save)
        layout.addLayout(footer)
        inherit_theme(self, parent)

    def choose_target(self):
        key = self.target.currentData()
        if key:
            version = self.repository.get(key)
            self.title.setText(version['title'])
            self.category.setCurrentText(version['category'])

    def save_work(self):
        self.data.update(title=self.title.text().strip(), category=self.category.currentText(),
                         body_html=self.content.editor.toHtml(), body_text=self.content.editor.toPlainText())
        try:
            self.work_id, _ = self.repository.save(self.data, self.target.currentData(), '保存回复')
        except Exception as error:
            QMessageBox.warning(self, '未能保存作品', str(error))
            return
        self.accept()
