import re
from PySide6.QtCore import Qt, QDate, Signal, QSize
from PySide6.QtGui import QIcon, QPixmap, QPainter, QPen
from PySide6.QtWidgets import QWidget, QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QToolButton, QPushButton, QSpinBox, QAbstractSpinBox, QToolTip
from northdiary.ui.controls import ComboBox
from northdiary.ui.theme import color, themed_css, theme_name


def parse_date(text):
    cleaned = text.strip().replace('/', '-').replace('.', '-')
    if re.fullmatch(r'\d{8}', cleaned):
        cleaned = cleaned[:4]+'-'+cleaned[4:6]+'-'+cleaned[6:]
    match = re.fullmatch(r'(\d{4})-(\d{1,2})-(\d{1,2})', cleaned)
    if not match:
        return QDate()
    date = QDate(*map(int, match.groups()))
    return date if date.isValid() and 1753 <= date.year() <= 9999 else QDate()


def parse_partial(text):
    text = text.strip().replace('/', '-').replace('.', '-')
    match = re.fullmatch(r'(\d{4})-(未知|\d{1,2})-(未知|\d{1,2})', text)
    if match and '未知' in match.groups():
        year, month, day = match.groups()
        if month == '未知' and day != '未知':
            return QDate(), 'day'
        anchor = QDate(int(year), 1 if month == '未知' else int(month), 1)
        if anchor.isValid() and 1753 <= anchor.year() <= 9999:
            return anchor, 'year' if month == '未知' else 'month'
        return QDate(), 'day'
    return parse_date(text), 'day'


def date_text(date, precision='day'):
    if precision == 'year': return date.toString('yyyy') + '-未知-未知'
    if precision == 'month': return date.toString('yyyy-MM') + '-未知'
    return date.toString('yyyy-MM-dd')


def matches_day(stored, selected):
    date, precision = parse_partial(stored)
    if not date.isValid(): return False
    length = {'year': 4, 'month': 7, 'day': 10}[precision]
    return date.toString('yyyy-MM-dd')[:length] == selected[:length]


def calendar_icon(widget):
    ratio = widget.devicePixelRatioF()
    pixmap = QPixmap(round(16*ratio), round(16*ratio))
    pixmap.setDevicePixelRatio(ratio)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(color('#75827a', widget), 1.2))
    painter.drawRoundedRect(2, 3, 12, 11, 2, 2)
    painter.drawLine(2, 6, 14, 6)
    painter.drawLine(5, 1, 5, 4); painter.drawLine(11, 1, 11, 4)
    painter.drawPoint(6, 9); painter.drawPoint(10, 9)
    painter.end()
    return QIcon(pixmap)


class DateDialog(QDialog):
    def __init__(self, selected, parent=None, title='选择日期', precision='day', allow_partial=False):
        super().__init__(parent)
        self.selected = QDate(selected)
        self.precision = precision
        self.allow_partial = allow_partial
        self.article_dates = set()
        owner = parent
        while owner is not None:
            if hasattr(owner, 'repository'):
                self.article_dates = {article.diary_date for article in owner.repository.list()}
                break
            owner = owner.parentWidget()
        self.icon_key = None
        self.shown = QDate(selected.year(), selected.month(), 1)
        self.setWindowTitle(title)
        self.setFixedWidth(330)
        dark = theme_name(self) in ('dark', 'wine')
        self.setStyleSheet(themed_css('''
            QDialog { background: #fffefa; }
            QToolButton { border: none; border-radius: 7px; background: transparent; color: #273b37; }
            QToolButton:hover { background: #e0e8db; }
            QToolButton#calendarDay:checked { background: #315c4d; color: white; }
            QToolButton#calendarDay[outside="true"] { color: #a0aaa0; }
            QToolButton#calendarDay[today="true"] { border: 1px solid #7d9b89; }
            QSpinBox { background: transparent; border: none; color: #273b37; font-size: 14px; }
            QLineEdit { padding: 6px 8px; }
        ''', dark, theme_name(self)))
        accent = color('#7d9b89' if dark else '#315c4d', self).name()
        empty = '#ffffff' if dark else color('#a0aaa0', self).name()
        self.setStyleSheet(self.styleSheet() + f"""
            QToolButton#calendarDay {{ color: {empty}; }}
            QToolButton#calendarDay[outside="true"] {{ color: {empty}; }}
            QToolButton#calendarDay[hasArticles="true"] {{ color: {accent}; font-weight: 700; }}
            QToolButton#calendarDay:checked {{ background: transparent; border: 2px solid {accent}; }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)
        layout.addWidget(QLabel(title))
        self.input = QLineEdit(date_text(selected, self.precision))
        self.input.setPlaceholderText('输入日期，例如 2026-07-15')
        self.input.setToolTip('支持 2026-07-15、2026/7/15 或 20260715')
        self.input.returnPressed.connect(self.accept_input)
        layout.addWidget(self.input)
        row = QHBoxLayout()
        row.setSpacing(2)
        def triangle(title, count, years=False):
            button = QToolButton()
            button.setArrowType(Qt.ArrowType.LeftArrow if count < 0 else Qt.ArrowType.RightArrow)
            button.setFixedSize(22, 28)
            button.setAccessibleName(title); button.setToolTip(title + '（长按连续切换）')
            button.setAutoRepeat(True); button.setAutoRepeatDelay(300); button.setAutoRepeatInterval(90)
            button.clicked.connect(lambda: self.move_year(count) if years else self.move_month(count))
            return button
        self.year_previous = triangle('上一年', -1, True)
        self.year_following = triangle('下一年', 1, True)
        self.month_previous = triangle('上个月', -1)
        self.month_following = triangle('下个月', 1)
        self.year = QSpinBox(); self.year.setRange(1753, 9999); self.year.setSuffix(' 年')
        self.year.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons); self.year.setFixedWidth(82)
        self.year.setToolTip('可直接输入年份，也可用左右三角切换')
        self.month = ComboBox()
        for month in range(1, 13): self.month.addItem(f'{month} 月', month)
        if allow_partial: self.month.addItem('未知', None)
        self.month.setFixedWidth(68); self.month.setFixedHeight(28)
        self.month.setStyleSheet('QComboBox { padding: 2px 16px 2px 4px; }')
        row.addWidget(self.year_previous); row.addWidget(self.year); row.addWidget(self.year_following)
        row.addStretch()
        row.addWidget(self.month_previous); row.addWidget(self.month); row.addWidget(self.month_following)
        layout.addLayout(row)
        self.unknown_month = QPushButton('月份未知')
        self.unknown_day = QPushButton('日期未知')
        unknown_row = QHBoxLayout()
        for button, precision_key in ((self.unknown_month, 'year'), (self.unknown_day, 'month')):
            button.setCheckable(True)
            button.setAutoDefault(False)
            button.setVisible(allow_partial)
            button.clicked.connect(lambda checked=False, key=precision_key: self.choose_unknown(key))
            unknown_row.addWidget(button)
        if allow_partial: layout.addLayout(unknown_row)
        grid = QGridLayout(); grid.setSpacing(3)
        for column, name in enumerate('一二三四五六日'):
            label = QLabel(name); label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            grid.addWidget(label, 0, column)
        self.days = []
        for index in range(42):
            button = QToolButton(); button.setObjectName('calendarDay')
            button.setFixedSize(36, 30); button.setCheckable(True)
            button.clicked.connect(lambda checked=False, b=button: self.choose(b.property('date')))
            grid.addWidget(button, index//7+1, index%7)
            self.days.append(button)
        layout.addLayout(grid)
        self.error = QLabel(''); self.error.setWordWrap(True); self.error.hide()
        layout.addWidget(self.error)
        footer = QHBoxLayout()
        today = QPushButton('今天'); today.clicked.connect(lambda: self.choose(QDate.currentDate()))
        cancel = QPushButton('取消'); cancel.clicked.connect(self.reject)
        confirm = QPushButton('确定'); confirm.setObjectName('primary'); confirm.clicked.connect(self.accept_input)
        for button in (today, cancel, confirm): button.setAutoDefault(False)
        footer.addWidget(today); footer.addStretch(); footer.addWidget(cancel); footer.addWidget(confirm)
        layout.addLayout(footer)
        self.year.valueChanged.connect(self.change_page)
        self.month.currentIndexChanged.connect(self.change_page)
        self.render_days()

    def choose_unknown(self, precision):
        self.precision = precision
        self.selected = QDate(self.shown.year(), self.shown.month(), 1)
        self.input.setText(date_text(self.selected, precision))
        self.error.hide()
        self.render_days()

    def render_days(self):
        self.unknown_month.setChecked(self.precision == 'year')
        self.unknown_day.setChecked(self.precision in ('year', 'month'))
        self.year.blockSignals(True); self.month.blockSignals(True)
        self.year.setValue(self.shown.year())
        self.month.setCurrentIndex(self.month.findData(None) if self.allow_partial and self.precision == 'year' else self.month.findData(self.shown.month()))
        self.year.blockSignals(False); self.month.blockSignals(False)
        self.year_previous.setEnabled(self.shown.year() > 1753)
        self.year_following.setEnabled(self.shown.year() < 9999)
        self.month_previous.setEnabled(self.shown > QDate(1753, 1, 1))
        self.month_following.setEnabled(self.shown < QDate(9999, 12, 1))
        start = self.shown.addDays(1-self.shown.dayOfWeek())
        for index, button in enumerate(self.days):
            date = start.addDays(index)
            button.setText(str(date.day()))
            button.setProperty('date', date)
            text = date.toString('yyyy-MM-dd')
            has_articles = any(value in self.article_dates for value in
                               (text, text[:7] + '-未知', text[:4] + '-未知-未知'))
            button.setProperty('hasArticles', has_articles)
            button.setToolTip(text + (' · 有文章' if has_articles else ' · 暂无文章'))
            button.setProperty('outside', date.month() != self.shown.month())
            button.setProperty('today', date == QDate.currentDate())
            button.setChecked(self.precision == 'day' and date == self.selected)
            button.setEnabled(1753 <= date.year() <= 9999 and self.precision != 'year')
            button.style().unpolish(button); button.style().polish(button)

    def move_year(self, count):
        date = self.shown.addYears(count)
        if 1753 <= date.year() <= 9999:
            self.shown = date
            if self.precision != 'day': self.choose_unknown(self.precision)
            self.render_days()

    def move_month(self, count):
        date = self.shown.addMonths(count)
        if 1753 <= date.year() <= 9999:
            self.shown = date
            if self.allow_partial and self.precision == 'year': self.precision = 'month'
            if self.precision != 'day': self.choose_unknown(self.precision)
            self.render_days()

    def change_page(self):
        month = self.month.currentData()
        if month is None and self.allow_partial:
            self.shown = QDate(self.year.value(), self.shown.month(), 1)
            self.choose_unknown('year')
            return
        self.shown = QDate(self.year.value(), month, 1)
        if self.precision == 'year': self.precision = 'month'
        if self.precision != 'day': self.choose_unknown(self.precision)
        self.render_days()

    def choose(self, date):
        self.precision = 'day'
        self.selected = QDate(date)
        self.shown = QDate(date.year(), date.month(), 1)
        self.input.setText(date.toString('yyyy-MM-dd'))
        self.error.hide(); self.render_days()

    def accept_input(self):
        date, precision = parse_partial(self.input.text()) if self.allow_partial else (parse_date(self.input.text()), 'day')
        if not date.isValid():
            self.error.setText('日期无效，请输入正确日期，例如 2026-07-15。')
            self.error.show(); self.input.setFocus()
            return
        self.selected = date
        self.precision = precision
        self.accept()


class DateInput(QWidget):
    dateChanged = Signal(QDate)

    def __init__(self, selected, parent=None):
        super().__init__(parent)
        self.selected = QDate(selected)
        self.precision = 'day'
        self.setFixedSize(148, 26)
        row = QHBoxLayout(self); row.setContentsMargins(0, 0, 0, 0); row.setSpacing(2)
        self.input = QLineEdit(selected.toString('yyyy-MM-dd'))
        self.input.setStyleSheet('QLineEdit { padding: 3px 4px; font-size: 11px; }')
        self.input.setToolTip('可直接输入日期：2026-07-15 或 20260715，按 Enter 确认')
        self.input.editingFinished.connect(self.commit)
        self.calendar_button = QToolButton(); self.calendar_button.setObjectName('articleTool')
        self.calendar_button.setFixedSize(18, 22); self.calendar_button.setIconSize(QSize(13, 13))
        self.calendar_button.setToolTip('打开日历'); self.calendar_button.clicked.connect(self.open_calendar)
        row.addWidget(self.input, 1); row.addWidget(self.calendar_button)

    def date(self):
        return QDate(self.selected)

    def text(self):
        return date_text(self.selected, self.precision)

    def setText(self, text):
        date, precision = parse_partial(text)
        self.setDate(date, precision)

    def setDate(self, date, precision='day'):
        if not date.isValid(): return
        changed = date != self.selected or precision != self.precision
        self.selected = QDate(date)
        self.precision = precision
        self.input.setText(self.text())
        self.input.setProperty('invalid', False)
        if changed: self.dateChanged.emit(self.selected)

    def commit(self):
        date, precision = parse_partial(self.input.text())
        if date.isValid():
            self.setDate(date, precision)
            return True
        self.input.setToolTip('日期无效，请输入正确日期，例如 2026-07-15')
        QToolTip.showText(self.input.mapToGlobal(self.input.rect().bottomLeft()), self.input.toolTip(), self.input)
        return False

    def open_calendar(self):
        dialog = DateDialog(self.selected, self, '文章日期', self.precision, allow_partial=True)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.setDate(dialog.selected, dialog.precision)

    def paintEvent(self, event):
        key = (theme_name(self), self.devicePixelRatioF())
        if key != getattr(self, 'icon_key', None):
            self.icon_key = key
            self.calendar_button.setIcon(calendar_icon(self))
        super().paintEvent(event)
