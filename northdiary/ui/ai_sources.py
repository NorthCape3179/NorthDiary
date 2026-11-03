"""Local, explicit article selection and request preview. No network or credentials."""
from dataclasses import dataclass

from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QAbstractItemView, QDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QPushButton, QSplitter, QTextBrowser, QVBoxLayout,
    QStyledItemDelegate, QStyle, QStyleOptionViewItem,
)

from northdiary.ui.controls import ComboBox
from northdiary.ui.theme import apply_theme, color, theme_name


class SourceDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        super().paint(painter, option, index)
        styled = QStyleOptionViewItem(option)
        self.initStyleOption(styled, index)
        rect = option.widget.style().subElementRect(QStyle.SubElement.SE_ItemViewItemCheckIndicator,
                                                    styled, option.widget)
        if not rect.isValid():
            return
        checked = index.data(Qt.ItemDataRole.CheckStateRole) == Qt.CheckState.Checked.value
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(rect.adjusted(-1, -1, 1, 1), color('#d5e1d0' if selected else '#f6f5f1', option.widget))
        painter.setPen(QPen(color('#315c4d' if checked else '#a1b3a4', option.widget), 1.2))
        painter.setBrush(color('#315c4d' if checked else '#fffefa', option.widget))
        box = QRectF(rect).adjusted(0.5, 0.5, -0.5, -0.5)
        painter.drawRoundedRect(box, 3, 3)
        if checked:
            painter.setPen(QPen(Qt.GlobalColor.white, 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            path = QPainterPath(QPointF(box.left() + 3, box.center().y()))
            path.lineTo(box.left() + 5.5, box.bottom() - 3)
            path.lineTo(box.right() - 2.5, box.top() + 3)
            painter.drawPath(path)
        painter.restore()


@dataclass(frozen=True)
class SourceArticle:
    id: str
    title: str
    diary_date: str
    outside: bool
    text: str = ''

    @property
    def description(self):
        return '时间线之外' if self.outside else self.diary_date


class ArticleSources:
    """Listing reads metadata only; bodies are resolved only for explicit IDs."""
    def __init__(self, database):
        self.db = database.connection

    def list(self, query='', space=None, category=None, tag=None):
        outside = 'EXISTS (SELECT 1 FROM outside_articles o WHERE o.article_id=a.id)'
        sql = f'''SELECT a.id,a.title,a.diary_date,{outside} AS outside
                  FROM articles a WHERE a.deleted_at IS NULL
                  AND NOT EXISTS (SELECT 1 FROM draft_articles d WHERE d.article_id=a.id)'''
        args = []
        if space is not None:
            sql += f' AND {outside}=?'
            args.append(int(space))
        if query.strip():
            sql += ' AND (instr(lower(a.title),lower(?))>0 OR instr(lower(a.body_text),lower(?))>0)'
            args.extend([query.strip(), query.strip()])
        if category:
            sql += ''' AND EXISTS (SELECT 1 FROM article_categories r JOIN categories c
                       ON c.id=r.category_id WHERE r.article_id=a.id AND c.name=?)'''
            args.append(category)
        if tag:
            sql += ''' AND EXISTS (SELECT 1 FROM article_tags r JOIN tags t
                       ON t.id=r.tag_id WHERE r.article_id=a.id AND t.name=?)'''
            args.append(tag)
        sql += ' ORDER BY a.diary_date DESC,a.created_at DESC,a.id'
        return [SourceArticle(r['id'], r['title'], r['diary_date'], bool(r['outside']))
                for r in self.db.execute(sql, args)]

    def resolve(self, ids):
        # A source moved to the trash since selection must not appear in a request.
        rows = []
        for key in dict.fromkeys(ids):
            row = self.db.execute('''SELECT a.id,a.title,a.diary_date,a.body_text,
                EXISTS (SELECT 1 FROM outside_articles o WHERE o.article_id=a.id) AS outside
                FROM articles a WHERE a.id=? AND a.deleted_at IS NULL
                AND NOT EXISTS (SELECT 1 FROM draft_articles d WHERE d.article_id=a.id)''', (key,)).fetchone()
            if row is not None:
                rows.append(SourceArticle(row['id'], row['title'], row['diary_date'],
                                          bool(row['outside']), row['body_text']))
        return rows


def inherit_theme(dialog, parent):
    if parent is not None:
        name = theme_name(parent) or 'light'
        apply_theme(dialog, name in ('dark', 'wine'), name)


class ArticleSelectionDialog(QDialog):
    def __init__(self, database, selected=(), parent=None):
        super().__init__(parent)
        self.sources = ArticleSources(database)
        self.selected = dict.fromkeys(selected)
        self.article_ids = tuple(selected)
        self.setWindowTitle('选择文章 · AI 工作室')
        self.resize(820, 610)
        self.setMinimumSize(650, 450)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(14)
        title = QLabel('这一次，想读哪些文章？')
        title.setStyleSheet('font-size: 22px; font-weight: 600;')
        layout.addWidget(title)
        hint = QLabel('仅勾选的文章进入本次范围；不包含人物资料和附件。')
        hint.setObjectName('muted')
        layout.addWidget(hint)
        filters = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText('搜索标题或正文')
        self.search.setClearButtonEnabled(True)
        self.space = ComboBox()
        for text, value in [('全部文章', None), ('时间线之内', False), ('时间线之外', True)]:
            self.space.addItem(text, value)
        self.category = ComboBox()
        self.category.addItem('所有分类', None)
        self.tag = ComboBox()
        self.tag.addItem('所有标签', None)
        for name, in self.sources.db.execute('SELECT name FROM categories ORDER BY name'):
            self.category.addItem(name, name)
        for name, in self.sources.db.execute('SELECT name FROM tags ORDER BY name'):
            self.tag.addItem(name, name)
        filters.addWidget(self.search, 2)
        for combo in (self.space, self.category, self.tag):
            combo.setMinimumWidth(115)
            filters.addWidget(combo, 1)
            combo.currentIndexChanged.connect(self.refresh)
        layout.addLayout(filters)
        self.list = QListWidget()
        self.list.setItemDelegate(SourceDelegate(self.list))
        self.list.setAccessibleName('可授权文章列表')
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list.itemChanged.connect(self.change_selection)
        layout.addWidget(self.list, 1)
        row = QHBoxLayout()
        self.count = QLabel()
        self.count.setObjectName('muted')
        row.addWidget(self.count, 1)
        self.select_all = QPushButton('全选当前结果')
        self.select_all.setToolTip('只勾选当前分类、标签、空间及搜索条件下的全部结果；保留其他已选文章')
        self.select_all.clicked.connect(self.select_visible)
        row.addWidget(self.select_all)
        clear = QPushButton('清空已选')
        clear.clicked.connect(self.clear_selection)
        row.addWidget(clear)
        layout.addLayout(row)
        footer = QHBoxLayout()
        footer.addStretch()
        cancel = QPushButton('取消')
        cancel.clicked.connect(self.reject)
        footer.addWidget(cancel)
        self.confirm = QPushButton('使用所选文章')
        self.confirm.setObjectName('primary')
        self.confirm.clicked.connect(self.confirm_selection)
        footer.addWidget(self.confirm)
        layout.addLayout(footer)
        self.search.textChanged.connect(self.refresh)
        self.refresh()
        inherit_theme(self, parent)

    def refresh(self):
        rows = self.sources.list(self.search.text(), self.space.currentData(),
                                 self.category.currentData(), self.tag.currentData())
        self.list.blockSignals(True)
        self.list.clear()
        for article in rows:
            item = QListWidgetItem(article.title + '\n' + article.description)
            item.setData(Qt.ItemDataRole.UserRole, article.id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if article.id in self.selected else Qt.CheckState.Unchecked)
            self.list.addItem(item)
        self.list.blockSignals(False)
        self.update_count()

    def change_selection(self, item):
        key = item.data(Qt.ItemDataRole.UserRole)
        if item.checkState() == Qt.CheckState.Checked:
            self.selected[key] = None
        else:
            self.selected.pop(key, None)
        self.update_count()

    def update_count(self):
        visible = self.list.count()
        self.count.setText(f'当前结果 {visible} 篇 · 已选 {len(self.selected)} 篇（跨筛选保留）'
                           if visible else f'没有符合条件的文章 · 已选 {len(self.selected)} 篇')
        self.confirm.setText(f'使用所选文章 · {len(self.selected)}')
        self.select_all.setEnabled(bool(visible))

    def select_visible(self):
        self.list.blockSignals(True)
        for index in range(self.list.count()):
            item = self.list.item(index)
            self.selected[item.data(Qt.ItemDataRole.UserRole)] = None
            item.setCheckState(Qt.CheckState.Checked)
        self.list.blockSignals(False)
        self.update_count()

    def clear_selection(self):
        self.selected.clear()
        self.refresh()

    def confirm_selection(self):
        self.article_ids = tuple(self.selected)
        self.accept()


class RequestPreviewDialog(QDialog):
    """Inspectable local preview; accepting never grants a reusable permission."""
    def __init__(self, articles, instruction, parent=None, *, history=(), system_prompt='', payload=None,
                 confirm_send=False, settings_summary='', extra_notice=''):
        super().__init__(parent)
        self.articles = articles
        self.setWindowTitle('确认本次发送范围' if confirm_send else '本次使用范围 · 仅预览')
        self.resize(870, 640)
        self.setMinimumSize(650, 450)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        title = QLabel('查看本次使用范围')
        title.setStyleSheet('font-size: 22px; font-weight: 600;')
        layout.addWidget(title)
        summary = QLabel(f'{len(articles)} 篇文章 · 不含人物资料、附件 · 历史消息 {len(history)} 条' + ('\n' + settings_summary if settings_summary else ''))
        summary.setWordWrap(True)
        summary.setObjectName('muted')
        layout.addWidget(summary)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.list = QListWidget()
        self.list.setMinimumWidth(190)
        self.list.addItem('本次指令')
        for article in articles:
            self.list.addItem(article.title + '\n' + article.description)
        self.body = QTextBrowser()
        self.body.setOpenExternalLinks(False)
        splitter.addWidget(self.list)
        splitter.addWidget(self.body)
        splitter.setSizes([230, 560])
        layout.addWidget(splitter, 1)
        texts = [instruction] + [f'标题：{a.title}\n日期 / 范围：{a.description}\n\n{a.text}' for a in articles]
        if system_prompt:
            self.list.addItem('功能提示词')
            texts.append(system_prompt)
        if history:
            self.list.addItem(f'历史消息 · {len(history)} 条')
            texts.append('\n\n'.join(('你：' if m['role'] == 'user' else 'DeepSeek：') + m['content'] for m in history))
        if payload is not None:
            import json
            self.list.addItem('完整请求（不含密钥）')
            texts.append(json.dumps(json.loads(payload), ensure_ascii=False, indent=2))
        self.list.currentRowChanged.connect(lambda row: self.body.setPlainText(texts[row]) if 0 <= row < len(texts) else None)
        self.list.setCurrentRow(0)
        footer = QHBoxLayout()
        notice = QLabel(('确认后仅将所示内容发送到 DeepSeek。' if confirm_send else '本地预览，不会发送内容。') + ('\n' + extra_notice if extra_notice else ''))
        notice.setObjectName('muted')
        notice.setWordWrap(True)
        footer.addWidget(notice, 1)
        if confirm_send:
            cancel = QPushButton('返回修改')
            cancel.clicked.connect(self.reject)
            footer.addWidget(cancel)
        close = QPushButton('确认并发送' if confirm_send else '完成预览')
        close.setObjectName('primary')
        close.clicked.connect(self.accept)
        footer.addWidget(close)
        layout.addLayout(footer)
        inherit_theme(self, parent)
