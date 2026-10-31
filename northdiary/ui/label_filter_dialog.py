from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, QListWidgetItem, QDialogButtonBox, QMenu
from northdiary.ui.definition_menu import delete_from_widget


class LabelFilterDialog(QDialog):
    def __init__(self, owner, kind, selected):
        super().__init__(owner)
        self.owner, self.kind = owner, kind
        self.setWindowTitle('选择显示的分类' if kind == 'categories' else '选择显示的标签')
        self.resize(360, 460)
        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        all_button = QPushButton('全部勾选'); none_button = QPushButton('全部取消')
        row.addWidget(all_button); row.addWidget(none_button); layout.addLayout(row)
        self.list = QListWidget(); layout.addWidget(self.list)
        self.list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self.context_menu)
        self.populate(selected)
        all_button.clicked.connect(lambda: self.check_all(True))
        none_button.clicked.connect(lambda: self.check_all(False))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText('应用')
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText('取消')
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject); layout.addWidget(buttons)

    def populate(self, selected):
        self.list.clear()
        names = self.owner.repository.categories() if self.kind == 'categories' else self.owner.repository.tags()
        for name in [''] + names:
            item = QListWidgetItem(name or ('未分类' if self.kind == 'categories' else '无标签'))
            item.setData(Qt.ItemDataRole.UserRole, name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if selected is None or name in selected else Qt.CheckState.Unchecked)
            self.list.addItem(item)

    def selection(self):
        return {self.list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.list.count()) if self.list.item(i).checkState() == Qt.CheckState.Checked}

    def check_all(self, checked):
        for i in range(self.list.count()):
            self.list.item(i).setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)

    def context_menu(self, point):
        item = self.list.itemAt(point)
        if item is None: return
        name = item.data(Qt.ItemDataRole.UserRole)
        if not name: return
        popup = QMenu(self)
        def remove():
            selected = self.selection()
            delete_from_widget(self, self.kind, name)
            self.populate(selected)
        popup.addAction('删除定义：' + name, remove)
        popup.exec(self.list.viewport().mapToGlobal(point))


def filter_articles(repository, rows, categories, tags):
    if categories is None and tags is None: return rows
    category_map, tag_map = {}, {}
    for key, name in repository.db.execute('SELECT ac.article_id,c.name FROM article_categories ac JOIN categories c ON c.id=ac.category_id'):
        category_map.setdefault(key, set()).add(name)
    for key, name in repository.db.execute('SELECT at.article_id,t.name FROM article_tags at JOIN tags t ON t.id=at.tag_id'):
        tag_map.setdefault(key, set()).add(name)
    def matches(values, checked):
        return checked is None or bool((values or {''}) & checked)
    return [article for article in rows if matches(category_map.get(article.id), categories) and matches(tag_map.get(article.id), tags)]
