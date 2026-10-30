from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QPushButton, QDialogButtonBox,
)

from northdiary.models import ExportSelection


class ExportDialog(QDialog):
    """Check chapters and move rows; the visible order is the export order."""
    def __init__(self, articles, parent=None):
        super().__init__(parent)
        self.setWindowTitle('导出 EPUB')
        self.resize(480, 500)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('书名'))
        self.title = QLineEdit('NorthDiary 文集')
        layout.addWidget(self.title)
        layout.addWidget(QLabel('作者（选填）'))
        self.author = QLineEdit()
        layout.addWidget(self.author)
        layout.addWidget(QLabel('勾选章节，选中一行后可上下移动调整顺序'))
        self.chapters = QListWidget()
        for article in articles:
            item = QListWidgetItem(f'{article.diary_date}  {article.title}')
            item.setData(Qt.ItemDataRole.UserRole, article.id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self.chapters.addItem(item)
        layout.addWidget(self.chapters)
        row = QHBoxLayout()
        for title, delta in (('上移', -1), ('下移', 1)):
            button = QPushButton(title)
            button.clicked.connect(lambda checked=False, step=delta: self.move_chapter(step))
            row.addWidget(button)
        layout.addLayout(row)
        self.error = QLabel()
        self.error.setStyleSheet('color: #b03030')
        layout.addWidget(self.error)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText('导出')
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText('取消')
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def move_chapter(self, delta):
        current = self.chapters.currentRow()
        target = current + delta
        if current >= 0 and 0 <= target < self.chapters.count():
            item = self.chapters.takeItem(current)
            self.chapters.insertItem(target, item)
            self.chapters.setCurrentRow(target)

    def selection(self):
        ids = tuple(self.chapters.item(row).data(Qt.ItemDataRole.UserRole)
                    for row in range(self.chapters.count())
                    if self.chapters.item(row).checkState() == Qt.CheckState.Checked)
        return ExportSelection(ids, self.title.text().strip(), self.author.text().strip())

    def accept(self):
        selection = self.selection()
        if not selection.title or not selection.article_ids:
            self.error.setText('请填写书名，并至少勾选一篇文章。')
            return
        super().accept()
