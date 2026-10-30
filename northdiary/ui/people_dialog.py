"""Person cards, profiles and the article person picker share one catalog."""
from PySide6.QtCore import Qt, QSize, Signal, QRectF
from PySide6.QtGui import QPainter, QPen, QFont, QColor
from PySide6.QtWidgets import (
    QAbstractButton, QDialog, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QScrollArea, QLineEdit, QPushButton, QLabel, QStackedWidget, QFormLayout,
    QDialogButtonBox, QMessageBox, QListWidget, QListWidgetItem, QTextEdit, QLayout,
)
from northdiary.storage.people import PeopleRepository
from northdiary.ui.tag_picker import TagPicker
from northdiary.ui.theme import color, themed_css, theme_name, apply_theme
from PySide6.QtGui import QPalette


def relationship_text(person):
    normal = person.get('relationships', [])
    temporary = [name + '（临时）' for name in person.get('temporary_relationships', [])]
    return '、'.join(normal + temporary) or '未设置关系'


def paint_avatar(painter, rect, widget, selected=False):
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color('#315c4d' if selected else '#e9ede7', widget))
    painter.drawEllipse(rect)
    painter.setBrush(QColor('white') if selected else color('#75827a', widget))
    x, y, w = rect.x(), rect.y(), rect.width()
    painter.drawEllipse(QRectF(x+w*.36, y+w*.20, w*.28, w*.28))
    painter.drawRoundedRect(QRectF(x+w*.23, y+w*.53, w*.54, w*.28), w*.13, w*.13)


class Avatar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(96, 96)
        self.setAccessibleName('人物默认头像')

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        paint_avatar(p, QRectF(4, 4, 88, 88), self)


class PersonCard(QAbstractButton):
    def __init__(self, person, selected=False, parent=None):
        super().__init__(parent)
        self.person = person
        self.setCheckable(True)
        self.setChecked(selected)
        self.setFixedSize(148, 202)
        self.setAccessibleName(person['name'] + ' ' + person['code'])
        self.setToolTip(person['name'] + '\n' + person['code'] + '\n关系：' + relationship_text(person))
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def sizeHint(self):
        return QSize(148, 202)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(color('#315c4d' if self.isChecked() else '#d4ddd1', self), 2 if self.hasFocus() else 1))
        p.setBrush(color('#fffefa', self))
        p.drawRoundedRect(QRectF(2, 2, 144, 198), 12, 12)
        paint_avatar(p, QRectF(36, 22, 76, 76), self, self.isChecked())
        p.setPen(color('#273b37', self))
        font = QFont(self.font()); font.setPointSize(12); font.setBold(True); p.setFont(font)
        p.drawText(QRectF(10, 111, 128, 30), Qt.AlignmentFlag.AlignCenter,
                   p.fontMetrics().elidedText(self.person['name'], Qt.TextElideMode.ElideRight, 126))
        font.setPointSize(9); font.setBold(False); p.setFont(font)
        p.setPen(color('#75827a', self))
        p.drawText(QRectF(10, 141, 128, 22), Qt.AlignmentFlag.AlignCenter,
                   p.fontMetrics().elidedText(self.person['code'], Qt.TextElideMode.ElideRight, 126))
        relation = relationship_text(self.person)
        p.drawText(QRectF(10, 170, 128, 22), Qt.AlignmentFlag.AlignCenter,
                   p.fontMetrics().elidedText(relation, Qt.TextElideMode.ElideRight, 126))
        if self.person['starred']:
            p.setPen(color('#315c4d', self)); p.drawText(QRectF(119, 8, 22, 22), Qt.AlignmentFlag.AlignCenter, '★')
        if self.person['pinned']:
            p.drawText(QRectF(8, 8, 28, 22), Qt.AlignmentFlag.AlignCenter, '↑')


class PersonEditor(QDialog):
    def __init__(self, repository, person=None, parent=None):
        super().__init__(parent)
        self.repository = repository
        self.person = dict(person) if person else None
        self.setWindowTitle('编辑人物' if person else '新增人物')
        self.resize(540, 580)
        self.setMinimumWidth(480)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setVerticalSpacing(14)
        self.fields = {}
        for key, title in [('name', '姓名'), ('code', '代号'), ('birth_date', '出生年月日'), ('met_date', '相遇时间')]:
            field = QLineEdit(person[key] if person else '')
            field.setMaxLength(100 if key in ('name', 'code') else 32)
            if key.endswith('date'): field.setPlaceholderText('可留空，或 2000 / 2000-05 / 2000-05-12')
            self.fields[key] = field; form.addRow(title, field)
        how = QTextEdit(); how.setAcceptRichText(False)
        how.setMaximumHeight(100)
        how.setPlainText(person['met_how'] if person else '')
        self.fields['met_how'] = how; form.addRow('相遇方式', how)
        self.relationships = TagPicker(self, owner_label='人物')
        self.relationships.set_catalog(repository.relationship_catalog())
        self.relationships.set_values((person or {}).get('relationships', []), (person or {}).get('temporary_relationships', []))
        form.addRow('关系', self.relationships)
        hint = QLabel('普通标签可复用 · 临时标签仅此人物 · 点击 × 移除')
        hint.setObjectName('muted'); hint.setWordWrap(True)
        form.addRow('', hint)
        layout.addLayout(form)
        self.error = QLabel(); self.error.setWordWrap(True); self.error.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.error)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.save); buttons.rejected.connect(self.reject); layout.addWidget(buttons)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText('保存人物')
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText('取消')
        name_theme = theme_name(parent) if parent else None
        dark = name_theme in ('dark', 'wine') if name_theme else self.palette().color(QPalette.ColorRole.Window).lightness() < 128
        apply_theme(self, dark, name_theme)

    def save(self):
        values = {k: (v.toPlainText() if isinstance(v, QTextEdit) else v.text()).strip() for k, v in self.fields.items()}
        values['relationships'] = sorted(self.relationships.normal_names)
        values['temporary_relationships'] = sorted(self.relationships.temporary_names)
        try:
            if self.person:
                self.person.update(values); self.repository.save(self.person)
            else:
                self.person = self.repository.create(**values)
        except Exception as error:
            self.error.setText('保存失败，填写内容已保留：' + str(error)); return
        self.accept()


class SelectedPeopleScroll(QScrollArea):
    def wheelEvent(self, event):
        delta = event.pixelDelta().x() or event.pixelDelta().y()
        if not delta:
            delta = (event.angleDelta().x() or event.angleDelta().y()) / 120 * 90
        bar = self.horizontalScrollBar()
        bar.setValue(bar.value() - round(delta))
        event.accept()


class PeopleDialog(QDialog):
    def __init__(self, database, parent=None, selected=None, attachments=None):
        super().__init__(parent)
        self.repository = PeopleRepository(database)
        self.attachments = attachments
        self.picker = selected is not None
        self.selected = list(dict.fromkeys(selected or []))
        self.cards = {}
        self.current_person = None
        self.setWindowTitle('选择人物标签' if self.picker else '人物档案')
        self.resize(790, 700)
        self.setMinimumSize(580, 520)
        outer = QVBoxLayout(self)
        self.stack = QStackedWidget(); outer.addWidget(self.stack, 1)
        self.list_page = QWidget(); listing = QVBoxLayout(self.list_page)
        top = QHBoxLayout(); top.addStretch()
        self.search = QLineEdit(); self.search.setPlaceholderText('搜索姓名或代号…'); self.search.setMaximumWidth(400)
        top.addWidget(self.search, 1); top.addStretch(); listing.addLayout(top)
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True)
        self.card_body = QWidget(); self.grid = QGridLayout(self.card_body)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.scroll.setWidget(self.card_body); listing.addWidget(self.scroll, 1)
        self.empty = QLabel('暂无人物，点击“新增人物”创建档案。'); self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        listing.addWidget(self.empty)
        add = QPushButton('＋ 新增人物'); add.clicked.connect(self.add_person); listing.addWidget(add)
        self.stack.addWidget(self.list_page)
        self.detail = QWidget(); self.detail_layout = QVBoxLayout(self.detail); self.stack.addWidget(self.detail)
        self.selected_scroll = SelectedPeopleScroll(); self.selected_scroll.setWidgetResizable(False); self.selected_scroll.setFixedHeight(112)
        self.selected_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.chips = QWidget(); self.chip_grid = QGridLayout(self.chips)
        self.chip_grid.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        self.selected_scroll.setWidget(self.chips)
        if self.picker:
            outer.addWidget(QLabel('已选人物（点击 × 取消）'))
            outer.addWidget(self.selected_scroll)
            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
            buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject)
        else:
            self.selected_scroll.hide()
            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close); buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)
        self.search.textChanged.connect(self.refresh)
        self.refresh()

    @staticmethod
    def clear_layout(layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().hide()
                item.widget().deleteLater()
            if item.layout(): PeopleDialog.clear_layout(item.layout())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'grid'): self.refresh()

    def refresh(self, *_):
        people = self.repository.list(self.search.text())
        existing = {p['id']: p for p in self.repository.list()}
        self.selected = [key for key in self.selected if key in existing]
        self.clear_layout(self.grid); self.cards = {}
        cols = max(1, (self.width()-70)//160)
        for i, person in enumerate(people):
            card = PersonCard(person, self.picker and person['id'] in self.selected)
            card.setCheckable(self.picker)
            card.clicked.connect(lambda checked=False, key=person['id']: self.activate(key))
            self.grid.addWidget(card, i//cols, i%cols); self.cards[person['id']] = card
        self.empty.setVisible(not people)
        self.empty.setText('没有匹配的人物。' if self.search.text() else '暂无人物，点击“新增人物”创建档案。')
        self.clear_layout(self.chip_grid)
        for i, key in enumerate(self.selected):
            chip = QWidget(); chip.setObjectName('personChip')
            chip.setStyleSheet(themed_css('QWidget#personChip { background: #fffefa; border: 1px solid #d4ddd1; border-radius: 5px; }', theme_name(self) in ('dark', 'wine'), theme_name(self)))
            row = QHBoxLayout(chip); row.setContentsMargins(5, 0, 5, 0)
            name = QLabel(existing[key]['name']); name.setTextFormat(Qt.TextFormat.PlainText); row.addWidget(name)
            remove = QPushButton('×'); remove.setFixedSize(28, 28); remove.setAccessibleName('取消选择 ' + existing[key]['name'])
            remove.clicked.connect(lambda checked=False, k=key: self.toggle(k)); row.addWidget(remove)
            self.chip_grid.addWidget(chip, i%2, i//2)
        self.chip_grid.activate()
        self.chips.adjustSize()

    def activate(self, key):
        if self.picker: self.toggle(key)
        else: self.show_person(key)

    def toggle(self, key):
        if key in self.selected: self.selected.remove(key)
        else: self.selected.append(key)
        self.refresh()

    def add_person(self):
        editor = PersonEditor(self.repository, parent=self)
        if editor.exec() == QDialog.DialogCode.Accepted: self.refresh()
        editor.deleteLater()

    def show_person(self, key):
        person = self.repository.get(key); self.current_person = key
        self.clear_layout(self.detail_layout)
        back = QPushButton('← 返回人物列表'); back.clicked.connect(self.back); self.detail_layout.addWidget(back)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); body = QWidget(); layout = QVBoxLayout(body)
        avatar_row = QHBoxLayout(); avatar_row.addStretch(); avatar_row.addWidget(Avatar()); avatar_row.addStretch()
        star = QLabel('★' if person['starred'] else ''); star.setFixedWidth(24)
        star.setAccessibleName('已星标' if person['starred'] else '未星标')
        avatar_row.addWidget(star, 0, Qt.AlignmentFlag.AlignTop); layout.addLayout(avatar_row)
        form = QFormLayout()
        for name, title in [('name', '姓名'), ('code', '代号'), ('birth_date', '出生年月日'), ('met_date', '相遇时间'), ('met_how', '相遇方式')]:
            value = QLabel(person[name] or '未详'); value.setTextFormat(Qt.TextFormat.PlainText); value.setWordWrap(True)
            value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse); form.addRow(title, value)
        relation = QLabel(relationship_text(person)); relation.setTextFormat(Qt.TextFormat.PlainText); relation.setWordWrap(True)
        form.addRow('关系', relation)
        layout.addLayout(form); layout.addWidget(QLabel('相关事件'))
        events = QListWidget(); events.setMinimumHeight(180)
        for article in self.repository.articles(key):
            item = QListWidgetItem(article.diary_date + ' · ' + article.title)
            item.setData(Qt.ItemDataRole.UserRole, article.id); events.addItem(item)
        events.setToolTip('双击打开只读文章')
        events.itemDoubleClicked.connect(lambda item: self.open_event(item.data(Qt.ItemDataRole.UserRole)))
        layout.addWidget(events, 1)
        if not events.count(): layout.addWidget(QLabel('暂无带此人物标签的文章。'))
        scroll.setWidget(body); self.detail_layout.addWidget(scroll, 1)
        buttons = QHBoxLayout()
        for text, fn in [('编辑', self.edit_person), ('删除', self.delete_person),
                         ('取消置顶' if person['pinned'] else '置顶', lambda: self.set_flag('pinned')),
                         ('取消星标' if person['starred'] else '星标', lambda: self.set_flag('starred'))]:
            button = QPushButton(text); button.clicked.connect(fn); buttons.addWidget(button)
        self.detail_layout.addLayout(buttons); self.stack.setCurrentWidget(self.detail)

    def back(self):
        self.refresh(); self.stack.setCurrentWidget(self.list_page)

    def edit_person(self):
        editor = PersonEditor(self.repository, self.repository.get(self.current_person), self)
        if editor.exec() == QDialog.DialogCode.Accepted:
            self.show_person(self.current_person); self.refresh()
        editor.deleteLater()

    def delete_person(self):
        if QMessageBox.question(self, '删除人物', '删除此人物档案并解除文章人物标签？文章正文和代号文字会保留。',
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes: return
        try:
            self.repository.delete(self.current_person); self.back()
        except Exception as error: QMessageBox.warning(self, '删除失败', str(error))

    def set_flag(self, flag):
        try:
            person = self.repository.get(self.current_person); person[flag] = 1-person[flag]
            self.repository.save(person); self.show_person(person['id']); self.refresh()
        except Exception as error: QMessageBox.warning(self, '保存失败', str(error))

    def open_event(self, key):
        if self.attachments is None: return
        from northdiary.storage.repository import ArticleRepository
        from northdiary.ui.memory_dialog import MemoryDialog
        dialog = MemoryDialog(ArticleRepository(self.repository.database), self.attachments, self, article_id=key)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose); dialog.exec()
