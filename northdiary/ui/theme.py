STYLE = '''
QMainWindow, QWidget { background: #f6f5f1; color: #273b37; font-family: "Microsoft YaHei UI"; font-size: 13px; }
QWidget#sidebar { background: #e9ede7; border-radius: 12px; }
QWidget#paper { background: #fffefa; border: 1px solid #e3e5dd; border-radius: 12px; }
QWidget#properties { background: #f0f1eb; border-radius: 12px; }
QWidget#photoPanel { background: transparent; }
QWidget#articleTools { background: transparent; }
QFrame#toolDivider { background: #e3e5dd; border: none; }
QToolButton { background: transparent; border: 1px solid transparent; border-radius: 6px; padding: 0; }
QToolButton:hover { background: #e0e8db; border-color: #c5d2c5; }
QToolButton:pressed { background: #d3e2d2; border-color: transparent; }
QToolButton:checked { background: #d3e2d2; border-color: transparent; }
QToolButton:focus { border-color: transparent; }
QToolButton:enabled:hover { border-color: #c5d2c5; }
QToolButton#articleTool { background: transparent; border: 1px solid transparent; border-radius: 6px; padding: 0; }
QToolButton#articleTool:hover { background: #e0e8db; border-color: #c5d2c5; }
QToolButton#articleTool:pressed, QToolButton#articleTool:checked { background: #d3e2d2; border-color: transparent; }
QToolButton#articleTool:enabled:hover { border-color: #7d9b89; }
QLabel#brand { font-size: 28px; font-weight: 700; color: #244d42; }
QLabel { background: transparent; }
QLabel#muted { color: #75827a; font-size: 12px; }
QLabel#section { font-size: 14px; font-weight: 600; }
QLineEdit, QDateEdit, QComboBox { background: #fffefa; border: 1px solid #dce2d8; border-radius: 6px; padding: 8px; }
QLineEdit:focus, QTextEdit:focus { border-color: #7d9b89; }
QComboBox { padding-right: 24px; selection-background-color: #dbe7d8; selection-color: #273b37; }
QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: top right; width: 24px; border: none; background: transparent; }
QComboBox QAbstractItemView { background: #fffefa; color: #273b37; selection-background-color: #dbe7d8; selection-color: #273b37; border: 1px solid #d6dfd1; outline: none; }
QMenu { background: #fffefa; color: #273b37; border: 1px solid #d6dfd1; padding: 5px; }
QMenu::item { background: transparent; padding: 8px 16px; border-radius: 5px; }
QMenu::item:selected { background: #dbe7d8; }
QTableWidget { background: #fffefa; alternate-background-color: #f0f3ec; gridline-color: #e4e9df; selection-background-color: #dbe7d8; selection-color: #273b37; }
QHeaderView::section { background: #e9eee5; color: #526959; border: none; padding: 8px; }
QLineEdit#title { font-size: 25px; font-weight: 600; border: none; padding: 4px 2px; }
QTextEdit { background: #fffefa; border: none; padding: 10px 2px; font-size: 16px; selection-background-color: #cfe0d2; }
QPushButton { background: #fffefa; border: 1px solid #d4ddd1; border-bottom-color: #c5d2c5; border-radius: 8px; padding: 8px 12px; }
QPushButton:hover { background: #f1f3ed; border-color: #7d9b89; }
QPushButton:pressed, QPushButton:checked { background: #d3e2d2; border-color: #d4ddd1; }
QPushButton:focus { border: 1px solid #d4ddd1; padding: 8px 12px; }
QPushButton:enabled:hover { border-color: #7d9b89; }
QPushButton#primary { background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #416f5d,stop:1 #315c4d); color: white; border: 1px solid transparent; font-weight: 600; }
QPushButton#primary:hover { background: #416f5d; border-color: #7d9b89; }
QPushButton#primary:pressed { background: #315c4d; border-color: transparent; }
QPushButton#primary:focus { border: 1px solid transparent; padding: 8px 12px; }
QPushButton#primary:enabled:hover { border-color: #7d9b89; }
QPushButton[buttonTone="accent"] { background: #e9eee7; border: 1px solid #d4ddd1; color: #244d42; }
QToolButton#articleTool[buttonTone="accent"] { background: #e9eee7; border: 1px solid transparent; color: #244d42; }
QPushButton[buttonTone="accent"]:hover, QToolButton#articleTool[buttonTone="accent"]:hover { background: #dbe7d8; border-color: #7d9b89; }
QPushButton[buttonTone="accent"]:pressed, QPushButton[buttonTone="accent"]:checked { background: #d3e2d2; border-color: #d4ddd1; }
QToolButton#articleTool[buttonTone="accent"]:pressed { background: #d3e2d2; border-color: transparent; }
QPushButton[buttonTone="accent"]:enabled:hover, QToolButton#articleTool[buttonTone="accent"]:enabled:hover { border-color: __button_outline__; }
QPushButton[buttonTone="danger"] { color: #9a5348; border-color: #d4ddd1; background: transparent; }
QPushButton[buttonTone="danger"]:hover { color: #9a5348; border-color: #9a5348; background: #fffefa; }
QPushButton[buttonTone="danger"]:pressed { background: #eee4d3; border-color: #9a5348; }
QPushButton:disabled, QPushButton#primary:disabled, QPushButton[buttonTone="accent"]:disabled, QPushButton[buttonTone="danger"]:disabled { color: #a0aaa0; background: #eeeee9; border: 1px solid #dce2d8; }
QToolButton:disabled, QToolButton#articleTool[buttonTone="accent"]:disabled { color: #a0aaa0; background: transparent; border-color: transparent; }
QListWidget { background: transparent; border: none; outline: none; }
QListWidget::item { border-radius: 7px; padding: 12px 8px; margin: 2px 0; }
ArticleList::item { padding: 0; margin: 2px 0; }
QListWidget::item:selected, ArticleList::item:selected:hover { background: #d5e1d0; color: #234735; }
QListWidget::item:hover { background: #e0e8db; }
QSplitter::handle { background: transparent; width: 9px; }
QStatusBar { color: #708075; background: #f6f5f1; }
QMenuBar, QMenu { background: #f6f5f1; }
QToolTip { background: #fffefa; color: #273b37; border: 1px solid #d4ddd1; }
QScrollBar:vertical { background: transparent; width: 8px; margin: 0; border: none; }
QScrollBar::handle:vertical { background: #c5d2c5; border-radius: 4px; min-height: 28px; }
QScrollBar::handle:vertical:hover { background: #7d9b89; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; border: none; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QToolButton#articleTool::menu-indicator, QToolButton#formatTool::menu-indicator { image: none; width: 0; }
QToolButton#articleTool:focus, QToolButton#formatTool:focus { border: 1px solid transparent; }
QDialog { background: #f6f5f1; border: 1px solid #d4ddd1; }
QWidget#windowTitleBar { background: #f6f5f1; border: none; border-bottom: 1px solid #e3e5dd; }
QLabel#windowCaption { color: #75827a; font-size: 12px; background: transparent; }
QToolButton#captionButton, QToolButton#captionClose { background: transparent; border: none; border-radius: 5px; padding: 0; }
QToolButton#captionButton:hover { background: #e0e8db; }
QToolButton#captionClose:hover { background: #c64848; }
QWidget#formatToolbar { background: transparent; }
QToolButton#formatTool { background: transparent; border: 1px solid transparent; border-radius: 6px; padding: 0; }
QToolButton#formatTool:hover { background: #e0e8db; border-color: #c5d2c5; }
QToolButton#formatTool:pressed, QToolButton#formatTool:checked { background: #d3e2d2; color: #244d42; border-color: transparent; }
QToolButton#formatTool:enabled:hover { border-color: #7d9b89; }
QToolButton#formatTool:disabled, QToolButton#articleTool:disabled { color: #a0aaa0; background: transparent; border-color: transparent; }
QWidget#formatToolbar QComboBox { padding: 4px 20px 4px 6px; }
QDoubleSpinBox, QSpinBox { background: #fffefa; border: 1px solid #dce2d8; border-radius: 6px; padding: 5px; }
QDialog QDialogButtonBox { background: transparent; }
QLabel#typographyPreview { background: #fffefa; border: 1px solid #e3e5dd; border-radius: 8px; }
'''

# One mapping is shared by stylesheets, painted controls and popup palettes.
DARK = {
 '#f6f5f1':'#191a1c', '#273b37':'#e3e4e6', '#e9ede7':'#222326',
 '#fffefa':'#27292c', '#e3e5dd':'#35383c', '#f0f1eb':'#242528',
 '#244d42':'#d7d9dc', '#75827a':'#a1a4aa', '#dce2d8':'#41444a',
 '#7d9b89':'#84b393', '#dbe7d8':'#304c3e', '#d6dfd1':'#41444a',
 '#e9eee5':'#2b2d31', '#526959':'#b5b8be', '#f0f3ec':'#26282c',
 '#e4e9df':'#393c42', '#cfe0d2':'#3a5747', '#d4ddd1':'#41444a',
 '#e0e9dd':'#303d35', '#d3e2d2':'#3a5747', '#315c4d':'#315b49',
 '#416f5d':'#416f59', '#a0aaa0':'#73777c', '#eeeee9':'#25272a',
 '#d5e1d0':'#304c3e', '#234735':'#e0e9e3', '#e0e8db':'#303236',
 '#708075':'#a6a9af', '#eee4d3':'#4b4334', '#dfe9dc':'#33483a',
 '#708273':'#afb6b1', '#e9eee7':'#2a2c30', '#f1f3ed':'#26282b',
 '#c5d2c5':'#45484d', '#a1b3a4':'#858990', '#788b7c':'#a1a5ad',
 '#d1e1d3':'#526f5a', '#82ad8b':'#9cd9aa', '#9a5348':'#eda99d',
}


CREAM = {'#f6f5f1': '#f4ecdc', '#273b37': '#514539', '#e9ede7': '#ece0ca', '#fffefa': '#fffaf0', '#e3e5dd': '#dfd1b9', '#f0f1eb': '#f0e5d2', '#244d42': '#75573e', '#75827a': '#96836d', '#dce2d8': '#ddcfb7', '#7d9b89': '#af8c60', '#dbe7d8': '#e8d8bd', '#d6dfd1': '#d9c9af', '#e9eee5': '#ecdfc8', '#526959': '#846d53', '#f0f3ec': '#f7efdf', '#e4e9df': '#e4d7c0', '#cfe0d2': '#e5d3b4', '#d4ddd1': '#d9c9af', '#e0e9dd': '#eadbc3', '#d3e2d2': '#e2cfaa', '#315c4d': '#87684c', '#416f5d': '#987958', '#a0aaa0': '#b1a28e', '#eeeee9': '#eee5d6', '#d5e1d0': '#e8d8bd', '#234735': '#55412d', '#e0e8db': '#f0e4cf', '#708075': '#96836d', '#eee4d3': '#efdfc5', '#dfe9dc': '#eadbc3', '#708273': '#9a8064', '#e9eee7': '#ecdfcb', '#f1f3ed': '#f5eddd', '#c5d2c5': '#d3c0a3', '#a1b3a4': '#b39c7e', '#788b7c': '#9c8161', '#d1e1d3': '#e2ccaa', '#82ad8b': '#b99b72', '#9a5348': '#a05b49', '#527c61': '#ac855e'}
WINE = {'#f6f5f1': '#191a1c', '#273b37': '#e3e4e6', '#e9ede7': '#222326', '#fffefa': '#202124', '#e3e5dd': '#3b3d42', '#f0f1eb': '#242528', '#244d42': '#e0d7d9', '#75827a': '#a1a4aa', '#dce2d8': '#41444a', '#7d9b89': '#b95f6e', '#dbe7d8': '#482b31', '#d6dfd1': '#41444a', '#e9eee5': '#2b2d31', '#526959': '#b5b8be', '#f0f3ec': '#26282c', '#e4e9df': '#393c42', '#cfe0d2': '#542e38', '#d4ddd1': '#41444a', '#e0e9dd': '#3f2c31', '#d3e2d2': '#542e38', '#315c4d': '#702c36', '#416f5d': '#8e3947', '#a0aaa0': '#73777c', '#eeeee9': '#25272a', '#d5e1d0': '#482b31', '#234735': '#e0e9e3', '#e0e8db': '#342b2e', '#708075': '#a6a9af', '#eee4d3': '#4b4334', '#dfe9dc': '#482b31', '#708273': '#afb6b1', '#e9eee7': '#2a2c30', '#f1f3ed': '#26282b', '#c5d2c5': '#45484d', '#a1b3a4': '#858990', '#788b7c': '#a1a5ad', '#d1e1d3': '#70404a', '#82ad8b': '#cb7a87', '#9a5348': '#eda99d', '#527c61': '#b95f6e'}
BURGUNDY = {'#f6f5f1': '#f4ecdc', '#273b37': '#514539', '#e9ede7': '#ece0ca', '#fffefa': '#fffaf0', '#e3e5dd': '#dfd1b9', '#f0f1eb': '#f0e5d2', '#244d42': '#84374c', '#75827a': '#96836d', '#dce2d8': '#ddcfb7', '#7d9b89': '#a45b71', '#dbe7d8': '#ead3d4', '#d6dfd1': '#d9c9af', '#e9eee5': '#ecdfc8', '#526959': '#846d53', '#f0f3ec': '#f7efdf', '#e4e9df': '#e4d7c0', '#cfe0d2': '#e5d3b4', '#d4ddd1': '#d9c9af', '#e0e9dd': '#eadbc3', '#d3e2d2': '#e3c4ca', '#315c4d': '#84374c', '#416f5d': '#a14c63', '#a0aaa0': '#b1a28e', '#eeeee9': '#eee5d6', '#d5e1d0': '#ead3d4', '#234735': '#55412d', '#e0e8db': '#f0e4cf', '#708075': '#96836d', '#eee4d3': '#efdfc5', '#dfe9dc': '#ead3d4', '#708273': '#9a8064', '#e9eee7': '#ecdfcb', '#f1f3ed': '#f5eddd', '#c5d2c5': '#d3c0a3', '#a1b3a4': '#b39c7e', '#788b7c': '#9c8161', '#d1e1d3': '#e2ccaa', '#82ad8b': '#bb7c8e', '#9a5348': '#a05b49', '#527c61': '#a45b71'}
CITRUS = {'#f6f5f1': '#f4ecdc', '#273b37': '#514539', '#e9ede7': '#ece0ca', '#fffefa': '#fffaf0', '#e3e5dd': '#dfd1b9', '#f0f1eb': '#f0e5d2', '#244d42': '#597845', '#75827a': '#96836d', '#dce2d8': '#ddcfb7', '#7d9b89': '#c78747', '#dbe7d8': '#f0dbbb', '#d6dfd1': '#d9c9af', '#e9eee5': '#ecdfc8', '#526959': '#846d53', '#f0f3ec': '#f7efdf', '#e4e9df': '#e4d7c0', '#cfe0d2': '#e5d3b4', '#d4ddd1': '#d9c9af', '#e0e9dd': '#ebd8b8', '#d3e2d2': '#eacda4', '#315c4d': '#597845', '#416f5d': '#6c8b53', '#a0aaa0': '#b1a28e', '#eeeee9': '#eee5d6', '#d5e1d0': '#f0dbbb', '#234735': '#55412d', '#e0e8db': '#f0e4cf', '#708075': '#96836d', '#eee4d3': '#efdfc5', '#dfe9dc': '#dce5c9', '#708273': '#9a8064', '#e9eee7': '#ecdfcb', '#f1f3ed': '#f5eddd', '#c5d2c5': '#d3c0a3', '#a1b3a4': '#b39c7e', '#788b7c': '#9c8161', '#d1e1d3': '#e2ccaa', '#82ad8b': '#d79a58', '#9a5348': '#a05b49', '#527c61': '#c78747'}
BLUE = {'#f6f5f1': '#f2f6fb', '#273b37': '#243a53', '#e9ede7': '#e7effa', '#fffefa': '#ffffff', '#e3e5dd': '#d2dfef', '#f0f1eb': '#edf3fb', '#244d42': '#306cc2', '#75827a': '#7d8fa7', '#dce2d8': '#d2dfef', '#7d9b89': '#6998d4', '#dbe7d8': '#d1e2fa', '#d6dfd1': '#d2dfef', '#e9eee5': '#d2dfef', '#526959': '#6683a7', '#f0f3ec': '#d2dfef', '#e4e9df': '#d2dfef', '#cfe0d2': '#d2dfef', '#d4ddd1': '#d2dfef', '#e0e9dd': '#d2dfef', '#d3e2d2': '#c6dcf7', '#315c4d': '#306cc2', '#416f5d': '#437fd4', '#a0aaa0': '#9fabbc', '#eeeee9': '#e9eef5', '#d5e1d0': '#d1e2fa', '#234735': '#214b80', '#e0e8db': '#d2dfef', '#708075': '#7d8fa7', '#eee4d3': '#d2dfef', '#dfe9dc': '#d2dfef', '#708273': '#6683a7', '#e9eee7': '#d2dfef', '#f1f3ed': '#eaf1fa', '#c5d2c5': '#d2dfef', '#a1b3a4': '#d2dfef', '#788b7c': '#6683a7', '#d1e1d3': '#d2dfef', '#82ad8b': '#81a9df', '#9a5348': '#a24e57', '#527c61': '#d2dfef'}
GRAY = {'#f6f5f1': '#ededee', '#273b37': '#35373b', '#e9ede7': '#e1e2e5', '#fffefa': '#fafafa', '#e3e5dd': '#d5d6d9', '#f0f1eb': '#e6e7e9', '#244d42': '#53575e', '#75827a': '#81858b', '#dce2d8': '#d5d6d9', '#7d9b89': '#949aa4', '#dbe7d8': '#d0d3d8', '#d6dfd1': '#d5d6d9', '#e9eee5': '#d5d6d9', '#526959': '#737880', '#f0f3ec': '#d5d6d9', '#e4e9df': '#d5d6d9', '#cfe0d2': '#d5d6d9', '#d4ddd1': '#d5d6d9', '#e0e9dd': '#d5d6d9', '#d3e2d2': '#c5c9d0', '#315c4d': '#626770', '#416f5d': '#777d87', '#a0aaa0': '#a0a3a8', '#eeeee9': '#e5e6e8', '#d5e1d0': '#d0d3d8', '#234735': '#35373b', '#e0e8db': '#d5d6d9', '#708075': '#81858b', '#eee4d3': '#d5d6d9', '#dfe9dc': '#d5d6d9', '#708273': '#737880', '#e9eee7': '#d5d6d9', '#f1f3ed': '#e5e6e9', '#c5d2c5': '#d5d6d9', '#a1b3a4': '#d5d6d9', '#788b7c': '#737880', '#d1e1d3': '#d5d6d9', '#82ad8b': '#9da3ad', '#9a5348': '#a24e57', '#527c61': '#d5d6d9'}

from northdiary.ui.radio_theme import RADIO_COLORS, RADIO_STYLE
from northdiary.ui.letter_theme import LETTER_COLORS, LETTER_STYLE

RADIO = {**DARK, **RADIO_COLORS}


def theme_name(widget):
    while widget is not None:
        name = widget.property('colorTheme')
        if name:
            return name
        widget = widget.parentWidget()
    return None

def theme_mapping(dark, name=None):
    return {'cream': CREAM, 'wine': WINE, 'burgundy': BURGUNDY, 'citrus': CITRUS, 'blue': BLUE, 'gray': GRAY, 'radio': RADIO, 'letter': LETTER_COLORS}.get(name, DARK if dark else {})


def themed_css(css, dark, name=None):
    import re
    mapping = theme_mapping(dark, name)
    result = re.sub(r'#[0-9a-fA-F]{6}', lambda m: mapping.get(m[0].lower(), m[0]), css)
    outline = '#7d9b89' if dark else '#315c4d'
    result = result.replace('__button_outline__', mapping.get(outline, outline))
    return result.replace('__calendar_empty__', '#ffffff' if dark else mapping.get('#a0aaa0', '#a0aaa0'))


def set_dialog_button_tones(root):
    from PySide6.QtWidgets import QDialogButtonBox, QMessageBox
    boxes = root.findChildren(QDialogButtonBox)
    for box in boxes:
        for button in box.buttons():
            role = box.buttonRole(button)
            if button.property('buttonTone') is None:
                if role in (QDialogButtonBox.ButtonRole.AcceptRole, QDialogButtonBox.ButtonRole.YesRole, QDialogButtonBox.ButtonRole.ApplyRole):
                    button.setProperty('buttonTone', 'accent')
                elif role == QDialogButtonBox.ButtonRole.DestructiveRole:
                    button.setProperty('buttonTone', 'danger')
    if isinstance(root, QMessageBox):
        for button in root.buttons():
            role = root.buttonRole(button)
            if button.property('buttonTone') is None:
                if role in (QMessageBox.ButtonRole.AcceptRole, QMessageBox.ButtonRole.YesRole, QMessageBox.ButtonRole.ApplyRole):
                    button.setProperty('buttonTone', 'accent')
                elif role == QMessageBox.ButtonRole.DestructiveRole:
                    button.setProperty('buttonTone', 'danger')


def color(value, widget):
    from PySide6.QtGui import QColor, QPalette
    name = theme_name(widget)
    # Transparent controls may report a black Window palette even in light mode.
    # The explicit ancestor theme takes precedence for every painted control.
    dark = name in ('dark', 'wine', 'radio') if name else widget.palette().color(QPalette.ColorRole.Window).lightness() < 128
    return QColor(theme_mapping(dark, name).get(value, value))


def style_local(widget, dark):
    css = widget.styleSheet()
    cached = widget.property('themeSourceStyle')
    rendered = widget.property('themeRenderedStyle')
    if css != rendered:
        cached = css
        widget.setProperty('themeSourceStyle', cached)
    if cached:
        result = themed_css(cached, dark, theme_name(widget))
        widget.setProperty('themeRenderedStyle', result)
        if css != result:
            widget.setStyleSheet(result)


def apply_theme(root, dark, name=None):
    from PySide6.QtGui import QPalette, QColor
    from PySide6.QtWidgets import QWidget
    root.setProperty('darkTheme', dark)
    root.setProperty('colorTheme', name or ('dark' if dark else 'light'))
    set_dialog_button_tones(root)
    palette = QPalette(root.palette())
    for group in (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive, QPalette.ColorGroup.Disabled):
        for role, value in ((QPalette.ColorRole.Window, '#f6f5f1'), (QPalette.ColorRole.Base, '#fffefa'),
                            (QPalette.ColorRole.Text, '#273b37'), (QPalette.ColorRole.WindowText, '#273b37'),
                            (QPalette.ColorRole.Button, '#fffefa'), (QPalette.ColorRole.ButtonText, '#273b37'),
                            (QPalette.ColorRole.Highlight, '#dbe7d8'), (QPalette.ColorRole.HighlightedText, '#273b37')):
            palette.setColor(group, role, QColor(theme_mapping(dark, name).get(value, value)))
    root.setPalette(palette)
    root.setStyleSheet(themed_css(STYLE, dark, name) + {'radio': RADIO_STYLE, 'letter': LETTER_STYLE}.get(name, ''))
    for child in root.findChildren(QWidget):
        style_local(child, dark)
        QWidget.update(child)
