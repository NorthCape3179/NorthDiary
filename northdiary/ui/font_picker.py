"""A small font menu backed by a searchable, explicitly selected font library."""
from PySide6.QtCore import QObject, Qt, Signal, QSize
from PySide6.QtGui import QFont
from html import escape
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QVBoxLayout, QPushButton, QTextBrowser,
)

from northdiary.ui.controls import ComboBox, PopupDelegate
from northdiary.ui.font_catalog import load_approved_fonts
from northdiary.ui.theme import color


class FontMenuDelegate(PopupDelegate):
    def sizeHint(self, option, index):
        if index.data(Qt.ItemDataRole.AccessibleDescriptionRole) == 'separator':
            return QSize(100, 12)
        return super().sizeHint(option, index)

    def paint(self, painter, option, index):
        if index.data(Qt.ItemDataRole.AccessibleDescriptionRole) == 'separator':
            painter.save()
            painter.setPen(color('#dce2d8', option.widget))
            painter.drawLine(option.rect.left()+8, option.rect.center().y(),
                             option.rect.right()-8, option.rect.center().y())
            painter.restore()
            return
        super().paint(painter, option, index)


class FontPreferences(QObject):
    changed = Signal()
    KEY = 'editor/favorite_fonts'
    ORIGINAL_FAMILY = 'Microsoft YaHei UI'

    def __init__(self, settings=None, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.catalog = load_approved_fonts()
        self.families = tuple(font.family for font in self.catalog)
        self.labels = {font.family: font.label for font in self.catalog}
        if settings is not None and settings.contains(self.KEY):
            self.selected = set(value for value in settings.value(self.KEY, [], type=list)
                                if isinstance(value, str) and value in self.families)
        else:
            self.selected = {font.family for font in self.catalog if font.bundled}

    @property
    def default_family(self):
        # This menu entry always means NorthDiary's original Windows font,
        # independently of the user's default typography for new articles.
        return self.ORIGINAL_FAMILY

    def new_entry_font(self):
        saved = self.settings.value('editor/default_family', '') if self.settings is not None else ''
        family = saved if saved in self.families or saved == self.default_family else self.default_family
        font = QFont(family)
        size = self.settings.value('editor/default_size', 12, type=float) if self.settings is not None else 12
        font.setPointSizeF(max(6, min(96, size)))
        return font

    def selected_families(self):
        return [family for family in self.families if family in self.selected]

    def set_selected(self, families):
        selected = set(families).intersection(self.families)
        if self.settings is not None:
            self.settings.setValue(self.KEY, sorted(selected, key=str.casefold))
            self.settings.sync()
        if self.selected != selected:
            self.selected = selected
            self.changed.emit()


class FontLibraryDialog(QDialog):
    def __init__(self, preferences, parent=None):
        super().__init__(parent)
        self.preferences = preferences
        self.selected = set(preferences.selected)
        self.setWindowTitle('更多字体')
        self.resize(560, 440)
        self.setMinimumSize(440, 380)
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        self.search = QLineEdit()
        self.search.setPlaceholderText('搜索字体名称…')
        self.search.setClearButtonEnabled(True)
        self.search.setAccessibleName('搜索已核实免费商用的字体')
        layout.addWidget(self.search)
        self.font_list = QListWidget()
        self.font_list.setObjectName('fontLibrary')
        self.font_list.setAccessibleName('全部免费商用字体，勾选后显示在字体下拉框中')
        self.font_list.setUniformItemSizes(True)
        self.font_list.setStyleSheet('QListWidget#fontLibrary { background: #fffefa; border: 1px solid #dce2d8; border-radius: 8px; } QListWidget#fontLibrary::item { padding: 8px; margin: 0; }')
        catalog = {font.family: font for font in preferences.catalog}
        for family in preferences.families:
            item = QListWidgetItem(preferences.labels[family])
            item.setData(Qt.ItemDataRole.UserRole, family)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if family in self.selected else Qt.CheckState.Unchecked)
            item.setFont(QFont(family, 11))
            entry = catalog[family]
            item.setToolTip(family + ' · ' + entry.license_name + '，免费商用\n' + entry.note)
            self.font_list.addItem(item)
        layout.addWidget(self.font_list, 1)
        footer = QHBoxLayout()
        self.count = QLabel()
        self.count.setObjectName('muted')
        footer.addWidget(self.count, 1)
        self.license_button = QPushButton('字体许可')
        self.license_button.clicked.connect(self.show_licenses)
        footer.addWidget(self.license_button)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText('完成')
        buttons.button(QDialogButtonBox.StandardButton.Ok).setObjectName('primary')
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText('取消')
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        footer.addWidget(buttons)
        layout.addLayout(footer)
        self.search.textChanged.connect(self.filter_fonts)
        self.font_list.itemChanged.connect(self.update_selection)
        self.filter_fonts('')
        self.search.setFocus()

    def show_licenses(self):
        dialog = FontLicensesDialog(self.preferences.catalog, self)
        dialog.exec()
        dialog.deleteLater()

    def filter_fonts(self, text):
        query = text.strip().casefold()
        for index in range(self.font_list.count()):
            item = self.font_list.item(index)
            searchable = item.text() + ' ' + item.data(Qt.ItemDataRole.UserRole)
            item.setHidden(query not in searchable.casefold())
        self.update_count()

    def update_selection(self, item):
        family = item.data(Qt.ItemDataRole.UserRole)
        if item.checkState() == Qt.CheckState.Checked:
            self.selected.add(family)
        else:
            self.selected.discard(family)
        self.update_count()

    def update_count(self):
        visible = sum(not self.font_list.item(index).isHidden() for index in range(self.font_list.count()))
        selected = len(self.selected.intersection(self.preferences.families))
        self.count.setText(f'已选 {selected} 种 · 显示 {visible} / {self.font_list.count()}')

    def accept(self):
        self.preferences.set_selected(self.selected)
        super().accept()


class FontLicensesDialog(QDialog):
    def __init__(self, catalog, parent=None):
        super().__init__(parent)
        self.setWindowTitle('字体许可')
        self.resize(640, 560)
        layout = QVBoxLayout(self)
        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        paragraphs = ['<h3>已核实可免费商用的字体</h3>']
        if any(font.family == 'MiSans' for font in catalog):
            paragraphs.append('<p>本软件使用了 MiSans 字体。MiSans 字体版权归小米所有，依其字体知识产权许可协议使用。</p>')
        paragraphs.append('<p>新增字体仅从本机已安装文件加载；字体文件本身未随本次更新重新分发。</p>')
        for font in catalog:
            paragraphs.append(f'<p><b>{escape(font.label)}</b> · {escape(font.license_name)}<br>'
                              f'{escape(font.note)}<br><a href="{escape(font.license_url, quote=True)}">官方许可依据</a></p>')
        paragraphs.append('<p>免费商用不等于免除许可条件。分发、嵌入或修改字体文件时，应遵守对应许可证。</p>')
        self.browser.setHtml(''.join(paragraphs))
        layout.addWidget(self.browser)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.button(QDialogButtonBox.StandardButton.Close).setText('关闭')
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


class FontPicker(ComboBox):
    currentFontChanged = Signal(QFont)
    MORE = '__northdiary_more_fonts__'
    DEFAULT = '__northdiary_default_font__'

    def __init__(self, font, preferences=None, parent=None):
        super().__init__(parent)
        self.preferences = preferences if preferences is not None else FontPreferences(parent=self)
        self._font = QFont(font)
        self.popup_list.setItemDelegate(FontMenuDelegate(self.popup_list))
        self.preferences.changed.connect(self.rebuild)
        self.activated.connect(self.choose_font)
        self.rebuild()

    def currentFont(self):
        return QFont(self._font)

    def showPopup(self):
        super().showPopup()
        height = sum(self.popup_list.sizeHintForRow(index) for index in range(self.count())) + 10
        self.popup.resize(self.popup.width(), min(height, self.popup.height()))

    def setCurrentFont(self, font):
        changed = self._font.family() != font.family()
        self._font = QFont(font)
        self.rebuild()
        if changed:
            self.currentFontChanged.emit(self.currentFont())

    def rebuild(self):
        blocked = self.blockSignals(True)
        try:
            self.clear()
            self.addItem('默认字体', self.DEFAULT)
            for family in self.preferences.selected_families():
                self.addItem(self.preferences.labels[family], family)
            self.insertSeparator(self.count())
            self.addItem('更多字体…', self.MORE)
            self.setCurrentIndex(0 if self._font.family() == self.preferences.default_family else self.findData(self._font.family()))
            # An article may use an unselected font. Display it without adding it
            # back to the menu or changing any document formatting.
            self.setPlaceholderText(self.preferences.labels.get(self._font.family(), '原文字体'))
            self.setAccessibleDescription('当前字体：' + self._font.family())
        finally:
            self.blockSignals(blocked)

    def choose_font(self, index):
        family = self.itemData(index)
        if family == self.MORE:
            self.rebuild()
            dialog = FontLibraryDialog(self.preferences, self.window())
            dialog.exec()
            self.rebuild()
            dialog.deleteLater()
        elif family == self.DEFAULT:
            self.setCurrentFont(QFont(self.preferences.default_family))
        elif family in self.preferences.families:
            self.setCurrentFont(QFont(family))
        else:
            self.rebuild()
