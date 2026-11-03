from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTabWidget, QTextEdit, QVBoxLayout, QWidget

from northdiary.services.ai_tasks import STORY_FIELDS
from northdiary.ui.ai_sources import inherit_theme


class StorySettingsDialog(QDialog):
    def __init__(self, notes, parent=None, suggestion=None):
        super().__init__(parent)
        self.notes = dict(notes)
        self.setWindowTitle('故事设定')
        self.resize(650, 500)
        self.setMinimumSize(480, 380)
        layout = QVBoxLayout(self)
        hint = QLabel('设定随发送后的对话记录保存；这里只使用你填写的内容，不自动读取人物档案。')
        hint.setObjectName('muted')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.title = QLineEdit(notes.get('title', ''))
        self.title.setPlaceholderText('故事名称（可选）')
        layout.addWidget(self.title)
        tabs = QTabWidget()
        self.fields = {}
        for key, label, placeholder in [
            ('outline', '故事大纲', '主线、分章安排、重要伏笔…'),
            ('characters', '人物设定', '姓名、性格、目标、人物关系…'),
            ('continuity', '连续性备忘', '已发生的事件、人物现状、时间地点、未解线索…'),
        ]:
            editor = QTextEdit()
            editor.setAcceptRichText(False)
            editor.setPlainText(notes.get(key, ''))
            editor.setPlaceholderText(placeholder)
            tabs.addTab(editor, label)
            self.fields[key] = editor
        layout.addWidget(tabs, 1)
        footer = QHBoxLayout()
        if suggestion:
            key, content = suggestion
            fill = QPushButton('填入最近生成的设定')
            def use_suggestion():
                self.fields[key].setPlainText(content)
                tabs.setCurrentWidget(self.fields[key])
            fill.clicked.connect(use_suggestion)
            footer.addWidget(fill)
        footer.addStretch()
        cancel = QPushButton('取消')
        cancel.clicked.connect(self.reject)
        apply = QPushButton('应用')
        apply.setObjectName('primary')
        apply.clicked.connect(self.apply_notes)
        footer.addWidget(cancel)
        footer.addWidget(apply)
        layout.addLayout(footer)
        inherit_theme(self, parent)

    def apply_notes(self):
        self.notes = {'title': self.title.text().strip()}
        self.notes.update({key: editor.toPlainText().strip() for key, editor in self.fields.items()})
        self.accept()
