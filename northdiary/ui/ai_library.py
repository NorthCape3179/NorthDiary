"""Independent work library, editable versions and explicit ordinary-article copies."""
from html import escape
import json
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QTextCursor, QTextDocument
from PySide6.QtWidgets import (QApplication, QDialog, QFileDialog, QHBoxLayout, QInputDialog,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton, QSplitter,
    QVBoxLayout, QWidget)

from northdiary.services.ai_work_export import export_work
from northdiary.storage.ai_works import AIWorkRepository, CATEGORIES
from northdiary.ui.ai_work_editor import WorkEditor
from northdiary.ui.controls import ComboBox


def label(value, name='muted'):
    widget = QLabel(value)
    widget.setWordWrap(True)
    widget.setObjectName(name)
    return widget


def action(title, callback):
    button = QPushButton(title)
    button.clicked.connect(callback)
    return button


class AIWorkLibrary(QWidget):
    articleRequested = Signal(str)

    def __init__(self, database, parent=None):
        super().__init__(parent)
        self.repo = AIWorkRepository(database)
        self.work_id = None
        self.version = None
        self.loading = False
        self.editing = False
        self.dirty = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 18, 24, 18)
        layout.setSpacing(10)
        layout.addWidget(label('AI 作品库', 'studioHeading'))
        filters = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText('搜索作品标题与正文')
        self.search.setClearButtonEnabled(True)
        self.category_filter = ComboBox()
        self.category_filter.addItem('全部作品', None)
        for category in CATEGORIES:
            self.category_filter.addItem(category, category)
        filters.addWidget(self.search, 1)
        filters.addWidget(self.category_filter)
        layout.addLayout(filters)
        self.count = label('还没有作品，可以从生成结果中保存。')
        layout.addWidget(self.count)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.list = QListWidget()
        self.list.setMinimumWidth(165)
        self.list.setWordWrap(True)
        splitter.addWidget(self.list)
        self.details = QWidget()
        detail = QVBoxLayout(self.details)
        detail.setContentsMargins(10, 0, 0, 0)
        detail.setSpacing(8)
        titles = QHBoxLayout()
        self.title = QLineEdit()
        self.title.setPlaceholderText('作品标题')
        self.category = ComboBox()
        self.category.addItems(CATEGORIES)
        titles.addWidget(self.title, 1)
        titles.addWidget(self.category)
        detail.addLayout(titles)
        history = QHBoxLayout()
        self.version_select = ComboBox()
        history.addWidget(self.version_select, 1)
        self.edit_button = action('编辑', self.begin_edit)
        self.save_button = action('保存新版', self.save_edit)
        self.cancel_button = action('取消编辑', self.cancel_edit)
        history.addWidget(self.edit_button)
        history.addWidget(self.save_button)
        history.addWidget(self.cancel_button)
        detail.addLayout(history)
        self.meta = label('')
        detail.addWidget(self.meta)
        self.content = WorkEditor()
        detail.addWidget(self.content, 1)
        sources = QHBoxLayout()
        sources.addWidget(label('关联原文'))
        self.sources = ComboBox()
        sources.addWidget(self.sources, 1)
        self.open_source_button = action('打开', self.open_source)
        sources.addWidget(self.open_source_button)
        detail.addLayout(sources)
        footer = QHBoxLayout()
        footer.addWidget(action('复制', lambda: QApplication.clipboard().setText(self.content.editor.toPlainText())))
        self.restore_button = action('恢复为新版', self.restore_version)
        self.delete_button = action('删除作品', self.delete_work)
        footer.addWidget(self.restore_button)
        footer.addWidget(self.delete_button)
        footer.addStretch()
        detail.addLayout(footer)
        exports = QHBoxLayout()
        self.export_txt = action('导出 TXT', lambda: self.export('txt'))
        self.export_epub = action('导出 EPUB', lambda: self.export('epub'))
        self.copy_article = action('另存普通文章', self.save_as_article)
        for widget in (self.export_txt, self.export_epub, self.copy_article):
            exports.addWidget(widget)
        exports.addStretch()
        detail.addLayout(exports)
        splitter.addWidget(self.details)
        splitter.setSizes([230, 680])
        layout.addWidget(splitter, 1)
        self.status = label('作品与原始日记、对话分别保存。')
        layout.addWidget(self.status)
        self.list.currentItemChanged.connect(self.select_work)
        self.version_select.currentIndexChanged.connect(self.select_version)
        self.sources.currentIndexChanged.connect(self.update_source_button)
        self.search.textChanged.connect(self.refresh)
        self.category_filter.currentIndexChanged.connect(self.refresh)
        for signal in (self.title.textChanged, self.category.currentIndexChanged, self.content.editor.textChanged):
            signal.connect(self.mark_dirty)
        self.refresh()

    def refresh(self, *_args, select_id=None):
        if self.editing:
            return
        wanted = select_id or self.work_id
        rows = self.repo.list(self.search.text(), self.category_filter.currentData())
        self.list.blockSignals(True)
        self.list.clear()
        selected = None
        for row in rows:
            item = QListWidgetItem(f"{row['title']}\n{row['category']} · v{row['number']} · {row['updated_at'][:10]}")
            item.setData(Qt.ItemDataRole.UserRole, row['id'])
            self.list.addItem(item)
            if row['id'] == wanted:
                selected = item
        self.list.blockSignals(False)
        self.count.setText(f'共 {len(rows)} 部作品' if rows else '暂无匹配作品；可从生成结果中保存。')
        if rows:
            self.list.setCurrentItem(selected or self.list.item(0))
        else:
            self.work_id = self.version = None
            self.details.hide()

    def show_work(self, work_id):
        if not self.can_leave():
            return
        self.search.blockSignals(True)
        self.category_filter.blockSignals(True)
        self.search.clear()
        self.category_filter.setCurrentIndex(0)
        self.search.blockSignals(False)
        self.category_filter.blockSignals(False)
        self.refresh(select_id=work_id)

    def generation_data(self, turn, title, category):
        document = QTextDocument()
        document.setMarkdown(turn['response'])
        return {'title': title, 'category': category, 'body_html': document.toHtml(),
                'body_text': document.toPlainText(), 'model': turn['response_model'] or turn['model'],
                'generated_at': turn['created_at'], 'origin_turn_id': turn['id'],
                'conversation_id': turn['conversation_id'],
                'sources': self.repo.source_references(json.loads(turn['article_ids']))}

    def append_generation(self, work_id, turn):
        old = self.repo.get(work_id)
        data = self.generation_data(turn, old['title'], old['category'])
        _, number = self.repo.save(data, work_id, '重新生成')
        self.refresh()
        return number

    def select_work(self, current, previous):
        if not current:
            return
        self.work_id = current.data(Qt.ItemDataRole.UserRole)
        self.loading = True
        self.version_select.blockSignals(True)
        self.version_select.clear()
        for version in self.repo.versions(self.work_id):
            self.version_select.addItem(f"v{version['number']} · {version['note']} · {version['created_at'][:19].replace('T', ' ')}", version['number'])
        self.version_select.blockSignals(False)
        self.loading = False
        self.details.show()
        self.select_version()

    def select_version(self, *_):
        if self.loading or not self.work_id:
            return
        try:
            self.version = self.repo.get(self.work_id, self.version_select.currentData())
        except KeyError:
            self.refresh()
            return
        self.loading = True
        data = self.version
        self.title.setText(data['title'])
        self.category.setCurrentText(data['category'])
        self.content.editor.setHtml(data['body_html'])
        self.meta.setText(f"{data['model'] or '模型未记录'} · 生成 {data['generated_at'][:19].replace('T', ' ')}\n"
                          f"本版保存 {data['created_at'][:19].replace('T', ' ')} · {data['note']}")
        self.sources.clear()
        for reference in data['sources']:
            row = self.repo.db.execute('SELECT title,deleted_at FROM articles WHERE id=?', (reference['id'],)).fetchone()
            name = row['title'] if row else reference.get('title', '原文已不存在')
            state = '（已删除）' if row is None or row['deleted_at'] else ''
            self.sources.addItem(name + state, reference['id'] if row and not row['deleted_at'] else None)
        if not data['sources']:
            self.sources.addItem('未关联原文', None)
        self.loading = False
        self.dirty = False
        self.set_editing(False)

    def set_editing(self, editing):
        self.editing = editing
        self.title.setReadOnly(not editing)
        self.category.setEnabled(editing)
        self.content.set_read_only(not editing)
        self.edit_button.setVisible(not editing)
        self.save_button.setVisible(editing)
        self.cancel_button.setVisible(editing)
        for widget in (self.list, self.search, self.category_filter, self.version_select,
                       self.restore_button, self.delete_button, self.export_txt, self.export_epub, self.copy_article):
            widget.setEnabled(not editing)
        self.update_source_button()

    def mark_dirty(self, *_):
        if self.editing and not self.loading:
            self.dirty = True

    def begin_edit(self):
        if self.version:
            self.set_editing(True)
            self.content.editor.setFocus()
            self.status.setText('保存会新增版本，旧版本始终保留。')

    def save_edit(self):
        if not self.version:
            return False
        data = dict(self.version)
        data.update(title=self.title.text().strip(), category=self.category.currentText(),
                    body_html=self.content.editor.toHtml(), body_text=self.content.editor.toPlainText())
        try:
            key, number = self.repo.save(data, self.work_id, f"编辑 v{self.version['number']}")
        except Exception as error:
            QMessageBox.warning(self, '未能保存新版', str(error))
            return False
        self.dirty = False
        self.set_editing(False)
        self.show_work(key)
        self.status.setText(f'已保存 v{number}，旧版本保留。')
        return True

    def cancel_edit(self):
        if self.dirty and QMessageBox.question(self, '取消编辑', '放弃本次尚未保存的修改？',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        self.select_version()

    def can_leave(self):
        if not self.editing:
            return True
        if not self.dirty:
            self.set_editing(False)
            return True
        choice = QMessageBox.question(self, '尚未保存作品', '保存为新版本后离开？',
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save)
        if choice == QMessageBox.StandardButton.Save:
            return self.save_edit()
        if choice == QMessageBox.StandardButton.Discard:
            self.select_version()
            return True
        return False

    def restore_version(self):
        if self.version:
            try:
                key, number = self.repo.save(self.version, self.work_id, f"从 v{self.version['number']} 恢复")
                self.show_work(key)
                self.status.setText(f'已恢复为 v{number}，其他版本保留。')
            except Exception as error:
                QMessageBox.warning(self, '未能恢复版本', str(error))

    def delete_work(self):
        if not self.work_id or QMessageBox.question(self, '删除作品', '删除此作品及其全部版本？原始日记和对话保留。',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        try:
            self.repo.delete(self.work_id)
            self.work_id = self.version = None
            self.refresh()
            self.status.setText('作品及版本已删除，原文和对话保留。')
        except Exception as error:
            QMessageBox.warning(self, '未能删除作品', str(error))

    def update_source_button(self, *_):
        self.open_source_button.setEnabled(bool(self.sources.currentData()) and not self.editing)

    def open_source(self):
        if self.sources.currentData():
            self.articleRequested.emit(self.sources.currentData())

    def export(self, kind):
        if not self.version:
            return
        import re
        safe_title = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', self.version['title']).strip(' .') or 'AI作品'
        path, _ = QFileDialog.getSaveFileName(self, '导出作品当前版本', safe_title[:100] + '.' + kind,
                                             'TXT 文本 (*.txt)' if kind == 'txt' else 'EPUB 电子书 (*.epub)')
        if not path:
            return
        target = Path(path)
        if target.suffix.lower() != '.' + kind:
            target = Path(path + '.' + kind)
            if target.exists() and QMessageBox.question(self, '覆盖文件', '目标文件已存在，是否替换？') != QMessageBox.StandardButton.Yes:
                return
        try:
            export_work(self.version, target, kind)
            self.status.setText('已导出：' + str(target))
        except Exception as error:
            QMessageBox.warning(self, '导出失败', str(error))

    def save_as_article(self):
        if not self.version:
            return
        title, ok = QInputDialog.getText(self, '另存普通文章', '新文章标题（原作品保留）', text=self.version['title'])
        if not ok or not title.strip():
            return
        space, ok = QInputDialog.getItem(self, '文章存放位置', '将创建带有“AI作品”分类和“AI生成”标签的新文章：',
                                       ['时间线之外', '时间线之内'], 0, False)
        if not ok:
            return
        document = QTextDocument()
        document.setHtml(self.version['body_html'])
        cursor = QTextCursor(document)
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        fiction = ' · 虚构创作' if self.version['category'] in ('故事', '创作草稿') else ''
        cursor.insertHtml('<p><em>AI 生成作品' + fiction + ' · ' + escape(self.version['model'] or '模型未记录') + '</em></p><p></p>')
        data = dict(self.version, body_html=document.toHtml(), body_text=document.toPlainText())
        try:
            key = self.repo.copy_to_article(data, title, space == '时间线之外')
            self.status.setText('已另存为新文章，原作品保留。')
            self.articleRequested.emit(key)
        except Exception as error:
            QMessageBox.warning(self, '另存文章失败', str(error))
