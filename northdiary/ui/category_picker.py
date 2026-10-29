from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QInputDialog
from northdiary.ui.controls import ComboBox


class CategoryPicker(QWidget):
    changed = Signal()

    def __init__(self):
        super().__init__()
        self.value = ''
        self.catalog = []
        self.combo = ComboBox()
        self.combo.setMinimumContentsLength(6)
        self.combo.setSizeAdjustPolicy(ComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo.activated.connect(self.choose)
        self.add_button = QPushButton('＋')
        self.add_button.setFixedSize(32, 32)
        self.add_button.setStyleSheet('QPushButton { padding: 0; font-size: 20px; }')
        self.add_button.setToolTip('新建分类（每篇文章只能选择一个分类）')
        self.add_button.clicked.connect(self.create)
        row = QHBoxLayout(self); row.setContentsMargins(0,0,0,0)
        row.addWidget(self.combo, 1); row.addWidget(self.add_button)
        self.refresh()

    def text(self):
        return self.value

    def setText(self, text):
        names = [name.strip() for name in text.replace('，', ',').split(',') if name.strip()]
        value = names[-1] if names else ''
        changed = value != self.value
        self.value = value
        self.refresh()
        if changed: self.changed.emit()

    def set_catalog(self, names):
        self.catalog = list(names); self.refresh()

    def refresh(self):
        self.combo.blockSignals(True)
        self.combo.clear(); self.combo.addItem('未分类', '')
        for name in sorted(set(self.catalog + ([self.value] if self.value else []))):
            self.combo.addItem(name, name)
        self.combo.setCurrentIndex(max(0, self.combo.findData(self.value)))
        self.combo.blockSignals(False)

    def choose(self, index):
        self.setText(self.combo.itemData(index) or '')

    def create(self):
        name, ok = QInputDialog.getText(self, '新建分类', '分类名称')
        if ok and name.strip(): self.setText(name.strip())
