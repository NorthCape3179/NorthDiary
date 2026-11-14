"""Selection formatting and explicitly separate defaults for new diary entries."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QTextCharFormat, QActionGroup, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QDoubleSpinBox, QToolButton,
    QMenu, QDialog, QLabel, QDialogButtonBox, QFormLayout,
)
from northdiary.ui.font_picker import FontPicker


def font_fields(font, parent=None, preferences=None):
    family = FontPicker(font, preferences, parent)
    family.setMinimumWidth(100)
    family.setMaximumWidth(168)
    family.setMaxVisibleItems(12)
    family.setAccessibleName('正文字体')
    family.setToolTip('默认字体：原版 Windows 微软雅黑 UI；“更多字体”可搜索和勾选已核实免费商用的字体')
    size = QDoubleSpinBox(parent)
    size.setRange(6, 96)
    size.setDecimals(1)
    size.setSingleStep(1)
    size.setKeyboardTracking(False)
    size.setSuffix(' pt')
    size.setFixedWidth(82)
    size.setValue(font.pointSizeF() if font.pointSizeF() > 0 else 12)
    size.setAccessibleName('正文字号（磅）')
    size.setToolTip('字号单位为磅（pt），应用于选中文字或随后输入的文字')
    return family, size


class DefaultTypographyDialog(QDialog):
    def __init__(self, font, parent):
        super().__init__(parent)
        self.setWindowTitle('默认排版')
        self.setMinimumWidth(440)
        layout = QVBoxLayout(self)
        hint = QLabel('用于新文章；已有文章和局部格式保持原样。')
        hint.setObjectName('muted')
        layout.addWidget(hint)
        self.family, self.size = font_fields(font, self, getattr(parent, 'font_preferences', None))
        form = QFormLayout()
        form.addRow('默认字体', self.family)
        form.addRow('默认字号', self.size)
        layout.addLayout(form)
        self.preview = QLabel('把值得记住的日常，慢慢写下来。\nNorthDiary · 0123456789')
        self.preview.setWordWrap(True)
        self.preview.setMinimumHeight(100)
        self.preview.setObjectName('typographyPreview')
        layout.addWidget(self.preview)
        self.family.currentFontChanged.connect(self.update_preview)
        self.size.valueChanged.connect(self.update_preview)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText('保存默认')
        buttons.button(QDialogButtonBox.StandardButton.Ok).setObjectName('primary')
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText('取消')
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.update_preview()

    def chosen_font(self):
        font = QFont(self.family.currentFont().family())
        font.setPointSizeF(self.size.value())
        return font

    def update_preview(self, *_):
        font = self.chosen_font()
        # A local rule overrides the application's universal UI font selector.
        family = font.family().replace('"', '')
        self.preview.setStyleSheet(f'font-family: "{family}"; font-size: {font.pointSizeF()}pt; padding: 14px;')


class EditorToolbar(QWidget):
    def __init__(self, editor, defaults_callback, parent=None, preferences=None):
        super().__init__(parent)
        self.editor = editor
        self.setObjectName('formatToolbar')
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)
        self.family, self.size = font_fields(editor.document().defaultFont(), self, preferences)
        row.addWidget(self.family, 1)
        row.addWidget(self.size)
        self.family.currentFontChanged.connect(self.change_family)
        self.size.valueChanged.connect(self.change_size)
        self.bold = self.tool('B', '加粗  Ctrl+B', lambda: self.emphasis('bold'))
        self.italic = self.tool('I', '斜体  Ctrl+I', lambda: self.emphasis('italic'))
        self.underline = self.tool('U', '下划线  Ctrl+U', lambda: self.emphasis('underline'))
        for button, css in ((self.bold, 'font-weight:700;'), (self.italic, 'font-style:italic;'),
                            (self.underline, 'text-decoration:underline;')):
            button.setCheckable(True)
            button.setStyleSheet(css)
            row.addWidget(button)
        self.alignment = self.tool('对齐', '当前或选中的段落对齐')
        self.alignment.setFixedWidth(66)
        self.alignment.setCheckable(True)
        self.alignment.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.align_menu = QMenu(self.alignment)
        self.align_group = QActionGroup(self)
        self.align_actions = {}
        for title, flag in [('左对齐', Qt.AlignmentFlag.AlignLeft), ('居中', Qt.AlignmentFlag.AlignHCenter),
                            ('右对齐', Qt.AlignmentFlag.AlignRight), ('两端对齐', Qt.AlignmentFlag.AlignJustify)]:
            action = self.align_menu.addAction(title)
            action.setCheckable(True)
            self.align_group.addAction(action)
            action.triggered.connect(lambda checked=False, value=flag: self.set_alignment(value))
            self.align_actions[flag] = action
        self.alignment.setMenu(self.align_menu)
        row.addWidget(self.alignment)
        row.addStretch()
        self.defaults = self.tool('Aa', '默认排版：设置新文章的字体与字号', defaults_callback)
        row.addWidget(self.defaults)
        for key, attribute in [('Ctrl+B', 'bold'), ('Ctrl+I', 'italic'), ('Ctrl+U', 'underline')]:
            shortcut = QShortcut(QKeySequence(key), editor)
            shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            shortcut.activated.connect(lambda value=attribute: self.emphasis(value))
        editor.currentCharFormatChanged.connect(self.sync_format)
        editor.cursorPositionChanged.connect(self.sync_alignment)
        self.sync_format(editor.currentCharFormat())
        self.sync_alignment()

    def tool(self, text, tip, callback=None):
        button = QToolButton(self)
        button.setObjectName('formatTool')
        button.setText(text)
        button.setToolTip(tip)
        button.setAccessibleName(tip)
        button.setFixedSize(30, 30)
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        if callback:
            button.clicked.connect(callback)
        return button

    def apply_format(self, fmt):
        if self.editor.isReadOnly():
            return
        # QTextEdit merges only the selection (or the subsequent input format),
        # never implicitly expands an empty selection to the current word.
        self.editor.mergeCurrentCharFormat(fmt)
        self.editor.setFocus()

    def change_family(self, font):
        fmt = QTextCharFormat()
        fmt.setFontFamilies([font.family()])
        self.apply_format(fmt)

    def change_size(self, size):
        fmt = QTextCharFormat()
        fmt.setFontPointSize(size)
        self.apply_format(fmt)

    def emphasis(self, kind):
        current = self.editor.currentCharFormat()
        fmt = QTextCharFormat()
        if kind == 'bold':
            fmt.setFontWeight(QFont.Weight.Normal if current.fontWeight() >= QFont.Weight.Bold else QFont.Weight.Bold)
        elif kind == 'italic':
            fmt.setFontItalic(not current.fontItalic())
        else:
            fmt.setFontUnderline(not current.fontUnderline())
        self.apply_format(fmt)

    def set_alignment(self, alignment):
        if self.editor.isReadOnly():
            return
        from PySide6.QtGui import QTextBlockFormat
        fmt = QTextBlockFormat()
        fmt.setAlignment(alignment)
        self.editor.textCursor().mergeBlockFormat(fmt)
        self.sync_alignment()
        self.editor.setFocus()

    def sync_alignment(self):
        alignment = self.editor.alignment()
        for flag, action in self.align_actions.items():
            action.setChecked(bool(alignment & flag))
        self.alignment.setChecked(bool(alignment & Qt.AlignmentFlag.AlignHCenter))

    def sync_format(self, fmt):
        font = fmt.font().resolve(self.editor.document().defaultFont())
        self.family.blockSignals(True)
        self.size.blockSignals(True)
        self.family.setCurrentFont(font)
        self.size.setValue(font.pointSizeF() if font.pointSizeF() > 0 else font.pixelSize()*72/96)
        self.family.blockSignals(False)
        self.size.blockSignals(False)
        self.bold.setChecked(fmt.fontWeight() >= QFont.Weight.Bold)
        self.italic.setChecked(fmt.fontItalic())
        self.underline.setChecked(fmt.fontUnderline())

    def set_editable(self, editable):
        for widget in (self.family, self.size, self.bold, self.italic, self.underline, self.alignment):
            widget.setEnabled(editable)
