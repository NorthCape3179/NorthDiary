from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QPushButton, QDialogButtonBox, QMenu,
)

from northdiary.models import ExportSelection


class ExportDialog(QDialog):
    """Check chapters and move rows; the visible order is the export order."""
    def __init__(self, articles, parent=None, *, repository=None):
        super().__init__(parent)
        articles = list(articles)
        repository = repository if repository is not None else getattr(parent, 'repository', None)
        self.setWindowTitle('导出 EPUB')
        self.resize(560, 560)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('书名'))
        self.title = QLineEdit('NorthDiary 文集')
        layout.addWidget(self.title)
        layout.addWidget(QLabel('作者（选填）'))
        self.author = QLineEdit()
        layout.addWidget(self.author)
        layout.addWidget(QLabel('勾选章节，选中一行后可上下移动调整顺序'))
        selection_tools = QHBoxLayout()
        self.category_button = QPushButton('按分类选择')
        self.tag_button = QPushButton('按标签选择')
        for button, kind in ((self.category_button, 'categories'), (self.tag_button, 'tags')):
            menu = QMenu(button)
            groups = {}
            if repository is not None:
                for article in articles:
                    names = repository.labels(article.id, kind)
                    if kind == 'tags':
                        names += repository.temporary_tags(article.id)
                    for name in names:
                        groups.setdefault(name, set()).add(article.id)
            for name in sorted(groups):
                action = menu.addAction(f'{name.replace("&", "&&")}（{len(groups[name])} 篇）')
                action.setData(name)
                action.triggered.connect(lambda checked=False, ids=frozenset(groups[name]): self.select_articles(ids))
            button.setMenu(menu)
            button.setEnabled(bool(groups))
            button.setToolTip('仅勾选所选项目对应的文章，替换当前勾选；章节顺序保持不变')
            selection_tools.addWidget(button)
        self.select_all_button = QPushButton('全选')
        self.clear_selection_button = QPushButton('取消全选')
        self.select_all_button.clicked.connect(lambda: self.select_articles(None))
        self.clear_selection_button.clicked.connect(lambda: self.select_articles(set()))
        selection_tools.addWidget(self.select_all_button)
        selection_tools.addWidget(self.clear_selection_button)
        layout.addLayout(selection_tools)
        layout.addWidget(QLabel('按分类或标签选择会替换当前勾选，可继续逐篇调整。'))
        self.chapters = QListWidget()
        for article in articles:
            outside = bool(parent and getattr(parent, 'outside', False))
            item = QListWidgetItem(article.title if outside else f'{article.diary_date}  {article.title}')
            item.setData(Qt.ItemDataRole.UserRole, article.id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self.chapters.addItem(item)
        layout.addWidget(self.chapters)
        self.selection_count = QLabel()
        layout.addWidget(self.selection_count)
        self.chapters.itemChanged.connect(self.update_selection_count)
        self.update_selection_count()
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

    def select_articles(self, article_ids):
        self.chapters.blockSignals(True)
        try:
            for row in range(self.chapters.count()):
                item = self.chapters.item(row)
                selected = article_ids is None or item.data(Qt.ItemDataRole.UserRole) in article_ids
                item.setCheckState(Qt.CheckState.Checked if selected else Qt.CheckState.Unchecked)
        finally:
            self.chapters.blockSignals(False)
        self.update_selection_count()

    def update_selection_count(self, *_):
        self.selection_count.setText(f'已选择 {len(self.selection().article_ids)} / {self.chapters.count()} 篇')
        if hasattr(self, 'error'):
            self.error.clear()

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

