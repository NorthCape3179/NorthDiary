from PySide6.QtCore import Qt, QUrl
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, QWidget, QMessageBox, QSplitter, QAbstractItemView
from northdiary.ui.editor import ArticleEditor
from northdiary.ui.image_viewer import ImageViewer


class TrashDialog(QDialog):
    def __init__(self, repository, parent=None):
        super().__init__(parent)
        self.repository = repository
        self.current_id = None
        self.setWindowTitle('回收站')
        self.resize(920, 660)
        self.setMinimumSize(640, 480)
        layout = QVBoxLayout(self)
        self.summary = QLabel()
        layout.addWidget(self.summary)
        splitter = QSplitter(Qt.Orientation.Vertical)
        layout.addWidget(splitter, 1)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(['文章 / 日记日期', '删除时间', '操作'])
        self.table.verticalHeader().hide()
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setColumnWidth(2, 200)
        self.table.currentCellChanged.connect(self.preview_article)
        splitter.addWidget(self.table)
        self.preview = ArticleEditor()
        self.preview.setReadOnly(True)
        self.preview.document().setBaseUrl(QUrl.fromLocalFile(str(repository.database.root)+'/'))
        self.preview.imageActivated.connect(self.open_image)
        splitter.addWidget(self.preview)
        splitter.setSizes([300, 280])
        close = QPushButton('关闭')
        close.clicked.connect(self.accept)
        layout.addWidget(close, alignment=Qt.AlignmentFlag.AlignRight)
        self.refresh()

    def refresh(self):
        self.table.blockSignals(True)
        articles = self.repository.list(trash=True)
        self.table.setRowCount(0)
        for row, article in enumerate(articles):
            self.table.insertRow(row)
            title = QTableWidgetItem(article.title+'\n'+article.diary_date)
            title.setData(Qt.ItemDataRole.UserRole, article.id)
            self.table.setItem(row, 0, title)
            self.table.setItem(row, 1, QTableWidgetItem(article.deleted_at[:19].replace('T', ' ')))
            actions = QWidget()
            controls = QHBoxLayout(actions)
            controls.setContentsMargins(4, 3, 4, 3)
            for text, callback in [('恢复', self.restore), ('永久删除', self.purge)]:
                button = QPushButton(text)
                button.setStyleSheet('QPushButton { padding: 5px 8px; }')
                if text == '永久删除':
                    button.setStyleSheet('QPushButton { padding: 5px 8px; color: #9a5348; }')
                button.clicked.connect(lambda checked=False, key=article.id, action=callback: action(key))
                controls.addWidget(button)
            self.table.setCellWidget(row, 2, actions)
            self.table.setRowHeight(row, 58)
        self.table.blockSignals(False)
        self.summary.setText(f'回收站 · {len(articles)} 篇文章  ｜  点击一行查看预览')
        self.current_id = None
        self.preview.clear()
        self.preview.setPlaceholderText('回收站为空' if not articles else '选择文章查看预览')
        if articles:
            self.table.setCurrentCell(0, 0)

    def preview_article(self, row, *_):
        item = self.table.item(row, 0)
        if item:
            self.current_id = item.data(Qt.ItemDataRole.UserRole)
            article = self.repository.get(self.current_id)
            self.preview.setHtml(article.body_html)

    def open_image(self, attachment_id):
        rows = list(self.repository.db.execute("SELECT * FROM attachments WHERE article_id=? AND mime_type LIKE 'image/%'", (self.current_id,)))
        index = next((i for i, row in enumerate(rows) if row['id'] == attachment_id), None)
        if index is not None:
            ImageViewer(rows, index, self.repository.database.root, self).exec()

    def restore(self, article_id):
        try:
            self.repository.set_deleted(article_id, False)
            self.refresh()
        except Exception as error:
            QMessageBox.warning(self, '恢复失败', str(error))

    def purge(self, article_id):
        article = self.repository.get(article_id)
        answer = QMessageBox.question(self, '永久删除文章',
            f'永久删除「{article.title}」及其托管附件？此操作无法撤销，电脑上的原文件不受影响。',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            failed = self.repository.permanently_delete(article_id)
            self.refresh()
            if failed:
                QMessageBox.warning(self, '文章已删除', '部分托管附件未能清理，文件仍保留在数据目录。')
        except Exception as error:
            QMessageBox.warning(self, '删除失败', str(error))
