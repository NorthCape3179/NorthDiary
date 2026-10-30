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
        self.sort.setCurrentIndex(max(0, self.sort.findData(current_sort)))
        row.addWidget(self.search, 1); row.addWidget(self.sort)
        layout.addLayout(row)
        self.count_label = QLabel(); layout.addWidget(self.count_label)
        self.table = QTableWidget(0,4)
        self.table.setHorizontalHeaderLabels(['文章', '日记日期', '创建时间', '修改时间'])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column in (1,2,3): self.table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
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
        self.sort.currentIndexChanged.connect(self.change_sort)
        self.refresh()

    def refresh(self):
        rows=self.repository.list(query=self.search.text(), sort=self.sort.currentData(), pinned_first=False)
        self.table.setRowCount(0)
        for i, article in enumerate(rows):
            self.table.insertRow(i)
            for column, text in enumerate([article.title, article.diary_date,
                                           article.created_at[:19].replace('T',' '), article.updated_at[:19].replace('T',' ')]):
                item=QTableWidgetItem(text)
                item.setData(Qt.ItemDataRole.UserRole,article.id)
                self.table.setItem(i,column,item)
        self.count_label.setText(f'全部文章 · {len(rows)} 篇（双击打开）')
        if rows: self.table.selectRow(0)

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
        self.sortingChanged.emit(self.sort.currentData());self.refresh()

    def open_selected(self):
        item=self.table.item(self.table.currentRow(),0)
        if item:
            self.article_id=item.data(Qt.ItemDataRole.UserRole);self.accept()
