from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QPushButton, QDialogButtonBox, QGridLayout,
)

from northdiary.models import ExportSelection


class ExportDialog(QDialog):
    """Check chapters and move rows; the visible order is the export order."""
    def __init__(self, articles, parent=None):
        super().__init__(parent)
        self.setWindowTitle('导出 EPUB')
        self.resize(680, 620)
        self.setMinimumSize(560, 480)
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        fields = QGridLayout()
        fields.addWidget(QLabel('文集名称'), 0, 0)
        fields.addWidget(QLabel('作者（选填）'), 0, 1)
        self.title = QLineEdit('NorthDiary 文集')
        fields.addWidget(self.title, 1, 0)
        self.author = QLineEdit()
        fields.addWidget(self.author, 1, 1)
        fields.setColumnStretch(0, 2)
        fields.setColumnStretch(1, 1)
        layout.addLayout(fields)
        self.scope_label = QLabel('选择文章；勾选的文章按列表顺序导出。')
        self.scope_label.setWordWrap(True)
        layout.addWidget(self.scope_label)
        self.search = QLineEdit()
        self.search.setPlaceholderText('搜索文章标题或日期')
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.filter_chapters)
        layout.addWidget(self.search)
        actions = QHBoxLayout()
        self.select_all = QPushButton('全选当前列表')
        self.select_none = QPushButton('取消当前列表')
        self.invert = QPushButton('反选当前列表')
        self.select_all.clicked.connect(lambda: self.set_checks('all'))
        self.select_none.clicked.connect(lambda: self.set_checks('none'))
        self.invert.clicked.connect(lambda: self.set_checks('invert'))
        for button in (self.select_all, self.select_none, self.invert):
            button.setToolTip('仅操作当前显示的文章，筛选之外的勾选会保留')
            actions.addWidget(button)
        actions.addStretch()
        layout.addLayout(actions)
        self.chapters = QListWidget()
        owner = getattr(parent, 'main_window', parent)
        outside = bool(owner and getattr(owner, 'outside', False))
        for article in articles:
            item = QListWidgetItem(article.title if outside else f'{article.diary_date}  {article.title}')
            item.setData(Qt.ItemDataRole.UserRole, article.id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self.chapters.addItem(item)
        self.chapters.itemChanged.connect(self.update_selection)
        self.chapters.currentRowChanged.connect(self.update_selection)
        layout.addWidget(self.chapters, 1)
        summary = QHBoxLayout()
        self.count_label = QLabel()
        summary.addWidget(self.count_label, 1)
        self.clear_all = QPushButton('清空全部选择')
        self.clear_all.clicked.connect(lambda: self.set_checks('clear'))
        summary.addWidget(self.clear_all)
        layout.addLayout(summary)
        row = QHBoxLayout()
        row.addWidget(QLabel('调整所选行的导出顺序'), 1)
        self.move_buttons = []
        for title, delta in (('上移', -1), ('下移', 1)):
            button = QPushButton(title)
            button.clicked.connect(lambda checked=False, step=delta: self.move_chapter(step))
            row.addWidget(button)
            self.move_buttons.append(button)
        layout.addLayout(row)
        self.error = QLabel()
        self.error.setStyleSheet('color: #b03030')
        layout.addWidget(self.error)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText('导出')
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText('取消')
        self.confirm_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.update_selection()

    def filter_chapters(self, query):
        query = query.strip().casefold()
        for row in range(self.chapters.count()):
            item = self.chapters.item(row)
            item.setHidden(query not in item.text().casefold())
        self.update_selection()

    def set_checks(self, action):
        self.chapters.blockSignals(True)
        try:
            for row in range(self.chapters.count()):
                item = self.chapters.item(row)
                if item.isHidden() and action != 'clear':
                    continue
                checked = action == 'all' or (
                    action == 'invert' and item.checkState() != Qt.CheckState.Checked)
                item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        finally:
            self.chapters.blockSignals(False)
        self.update_selection()

    def update_selection(self, *_):
        items = [self.chapters.item(row) for row in range(self.chapters.count())]
        visible = [item for item in items if not item.isHidden()]
        selected = sum(item.checkState() == Qt.CheckState.Checked for item in items)
        visible_selected = sum(item.checkState() == Qt.CheckState.Checked for item in visible)
        self.count_label.setText(
            f'已选 {selected} / {len(items)} 篇 · 当前显示 {len(visible)} 篇'
            + (f'（已选 {visible_selected} 篇）' if self.search.text().strip() else ''))
        self.select_all.setEnabled(visible_selected < len(visible))
        self.select_none.setEnabled(visible_selected > 0)
        self.invert.setEnabled(bool(visible))
        self.clear_all.setEnabled(selected > 0)
        self.confirm_button.setEnabled(selected > 0)
        filtering = bool(self.search.text().strip())
        current = self.chapters.currentRow()
        self.move_buttons[0].setEnabled(not filtering and current > 0)
        self.move_buttons[1].setEnabled(not filtering and 0 <= current < len(items) - 1)
        for button in self.move_buttons:
            button.setToolTip('清除搜索后可调整完整列表顺序' if filtering else '')
        self.error.clear()

    def move_chapter(self, delta):
        current = self.chapters.currentRow()
        target = current + delta
        if current >= 0 and 0 <= target < self.chapters.count():
            item = self.chapters.takeItem(current)
            self.chapters.insertItem(target, item)
            self.chapters.setCurrentRow(target)
        self.update_selection()

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
