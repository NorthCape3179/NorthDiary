from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton, QMenu, QInputDialog, QListWidget, QListWidgetItem, QLabel
from northdiary.ui.controls import ComboBox as QComboBox, MenuButton


class TagPicker(QWidget):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(44)
        self.normal_names = []
        self.temporary_names = []
        self.catalog = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        row = QHBoxLayout()
        self.combo = QComboBox()
        self.combo.setFixedHeight(32)
        self.combo.setStyleSheet('QComboBox { padding: 4px 8px; border-radius: 8px; }')
        self.combo.setMinimumWidth(0)
        self.combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo.setMinimumContentsLength(8)
        self.combo.activated.connect(self.choose)
        row.addWidget(self.combo, 1)
        self.add_button = MenuButton('＋')
        self.add_button.setFixedSize(32, 32)
        self.add_button.setStyleSheet('QPushButton { padding: 0; font-size: 20px; background: #e0e9dd; border-radius: 8px; } QPushButton::menu-indicator { image: none; width: 0px; }')
        self.add_button.setToolTip('新建普通标签或临时标签')
        menu = QMenu(self.add_button)
        menu.setAttribute(Qt.WidgetAttribute.WA_NoMouseReplay)
        menu.addAction('普通标签（以后可选）', lambda: self.create(False))
        menu.addAction('临时标签（仅此文章）', lambda: self.create(True))
        self.add_button.setMenu(menu)
        row.addWidget(self.add_button)
        layout.addLayout(row)
        self.selected = QListWidget()
        self.selected.setStyleSheet('QListWidget { background: transparent; } QListWidget::item { padding: 0; margin: 0; background: transparent; }')
        self.selected.setViewMode(QListWidget.ViewMode.IconMode)
        self.selected.setMovement(QListWidget.Movement.Static)
        self.selected.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.selected.setWrapping(True)
        self.selected.setSpacing(3)
        self.selected.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.selected.setFixedHeight(76)
        layout.addWidget(self.selected)
        self.refresh()

    def set_values(self, normal, temporary):
        self.normal_names = list(normal)
        self.temporary_names = list(temporary)
        self.refresh()

    def set_catalog(self, names):
        self.catalog = list(names)
        self.refresh_combo()

    def refresh_combo(self):
        self.combo.clear()
        self.combo.addItem('选择已有标签…', None)
        for name in sorted(set(self.catalog + self.normal_names)):
            self.combo.addItem(name, name)

    def choose(self, index):
        name = self.combo.itemData(index)
        if name:
            self.add_tag(name, False)
        self.combo.setCurrentIndex(0)

    def create(self, temporary):
        title = '新建临时标签' if temporary else '新建普通标签'
        name, ok = QInputDialog.getText(self, title, '标签名称')
        if ok and name.strip():
            self.add_tag(name.strip(), temporary)

    def add_tag(self, name, temporary=False):
        name = name.strip()
        target = self.temporary_names if temporary else self.normal_names
        if not name or name in target:
            return
        target.append(name)
        self.refresh()
        self.changed.emit()

    def remove_tag(self, name, temporary):
        target = self.temporary_names if temporary else self.normal_names
        target.remove(name)
        self.refresh()
        self.changed.emit()

    def refresh(self):
        self.refresh_combo()
        self.selected.clear()
        self.selected.setVisible(bool(self.normal_names or self.temporary_names))
        for temporary, names in ((False, self.normal_names), (True, self.temporary_names)):
            for name in names:
                item = QListWidgetItem()
                widget = QWidget()
                widget.setObjectName('tagChip')
                color = '#eee4d3' if temporary else '#dfe9dc'
                widget.setStyleSheet(f'QWidget#tagChip {{ background: {color}; border-radius: 12px; }}')
                row = QHBoxLayout(widget)
                row.setContentsMargins(9, 2, 3, 2)
                row.setSpacing(3)
                text = QLabel(name + (' · 临时' if temporary else ''))
                text.setMaximumWidth(145)
                text.setToolTip(name)
                text.setTextFormat(Qt.TextFormat.PlainText)
                row.addWidget(text, 1)
                remove = QPushButton('×')
                remove.setToolTip('从当前文章移除标签')
                remove.setFixedSize(24, 24)
                remove.setStyleSheet('QPushButton { padding: 0; border: none; background: transparent; color: #708273; font-size: 16px; } QPushButton:hover { color: #273b37; }')
                remove.clicked.connect(lambda checked=False, n=name, t=temporary: self.remove_tag(n, t))
                row.addWidget(remove)
                item.setSizeHint(widget.sizeHint())
                self.selected.addItem(item)
                self.selected.setItemWidget(item, widget)
