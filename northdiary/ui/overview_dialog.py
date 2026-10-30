from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QPushButton, QLabel, QMenu
from northdiary.ui.controls import ComboBox


class OverviewDialog(QDialog):
    sortingChanged = Signal(str)
    deleteRequested = Signal(str)

    def __init__(self, repository, options, current_sort, parent=None):
        super().__init__(parent)
        self.repository = repository
        self.article_id = None
        self.setWindowTitle('文章总览'); self.resize(900, 580)
        self.setMinimumSize(650, 420)
        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        self.search = QLineEdit(); self.search.setPlaceholderText('搜索全部文章标题和正文…')
        self.sort = ComboBox()
        for title, key in options: self.sort.addItem(title, key)
        self.sort.addItem('分类排序', 'category')
        self.category_combo = ComboBox()
        self.category_combo.setFixedWidth(142)
        self.category_combo.setAccessibleName('总览分类筛选')
        self.category_combo.addItem('全部分类', None)
        self.category_combo.addItem('未分类', '')
        for name in repository.categories(): self.category_combo.addItem(name, name)
        self.category_combo.hide()
        self.sort.setCurrentIndex(max(0, self.sort.findData(current_sort)))
        row.addWidget(self.search, 1); row.addWidget(self.category_combo); row.addWidget(self.sort)
        layout.addLayout(row)
        self.count_label = QLabel(); layout.addWidget(self.count_label)
        self.table = QTableWidget(0,5)
        self.table.setHorizontalHeaderLabels(['文章', '分类', '日记日期', '创建时间', '修改时间'])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column in (1,2,3,4): self.table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.cellDoubleClicked.connect(lambda *_: self.open_selected())
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_article_menu)
        layout.addWidget(self.table, 1)
        footer=QHBoxLayout(); footer.addStretch()
        close=QPushButton('关闭');close.clicked.connect(self.reject)
        opened=QPushButton('打开文章');opened.setObjectName('primary');opened.clicked.connect(self.open_selected)
        footer.addWidget(close);footer.addWidget(opened);layout.addLayout(footer)
        self.search.textChanged.connect(self.refresh)
        self.category_combo.currentIndexChanged.connect(self.refresh)
        self.sort.currentIndexChanged.connect(self.change_sort)
        self.refresh()

    def refresh(self):
        category_mode = self.sort.currentData() == 'category'
        self.category_combo.setVisible(category_mode)
        selected_category = self.category_combo.currentData() if category_mode else None
        rows = self.repository.list(query=self.search.text(), category=selected_category or None,
                                    sort='title' if category_mode else self.sort.currentData(), pinned_first=False)
        categories = {}
        for article_id, name in self.repository.db.execute(
                'SELECT ac.article_id,c.name FROM article_categories ac JOIN categories c ON c.id=ac.category_id ORDER BY c.name'):
            categories.setdefault(article_id, []).append(name)
        if category_mode:
            if selected_category == '': rows = [a for a in rows if not categories.get(a.id)]
            rows.sort(key=lambda a: (tuple(categories.get(a.id) or ['\uffff']), a.title.casefold(), a.diary_date, a.created_at, a.id))
        old_item = self.table.item(self.table.currentRow(), 0)
        selected_id = old_item.data(Qt.ItemDataRole.UserRole) if old_item else None
        selected_row = 0
        self.table.setRowCount(0)
        for i, article in enumerate(rows):
            self.table.insertRow(i)
            if article.id == selected_id: selected_row = i
            texts = [article.title, '、'.join(categories.get(article.id, [])) or '未分类', article.diary_date,
                     article.created_at[:19].replace('T',' '), article.updated_at[:19].replace('T',' ')]
            for column, text in enumerate(texts):
                item=QTableWidgetItem(text)
                item.setData(Qt.ItemDataRole.UserRole,article.id)
                self.table.setItem(i,column,item)
        scope = self.category_combo.currentText() if category_mode else '全部文章'
        self.count_label.setText(f'{scope} · {len(rows)} 篇（双击打开，右键删除）')
        if rows: self.table.selectRow(selected_row)

    def show_article_menu(self, point):
        item = self.table.itemAt(point)
        if item is None:
            return
        self.table.selectRow(item.row())
        article_id = item.data(Qt.ItemDataRole.UserRole)
        menu = QMenu(self)
        menu.addAction('删除', lambda: self.delete_article(article_id))
        try:
            menu.exec(self.table.viewport().mapToGlobal(point))
        finally:
            menu.deleteLater()

    def delete_article(self, article_id):
        # The main window handles saving, confirmation, trash and error reporting.
        self.deleteRequested.emit(article_id)
        self.refresh()

    def change_sort(self):
        if self.sort.currentData() != 'category':
            self.sortingChanged.emit(self.sort.currentData())
        self.refresh()

    def open_selected(self):
        item=self.table.item(self.table.currentRow(),0)
        if item:
            self.article_id=item.data(Qt.ItemDataRole.UserRole);self.accept()
