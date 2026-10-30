"""A virtual, vertically scrolling date timeline with per-date two-row strips."""
from dataclasses import dataclass
import math

from PySide6.QtCore import Qt, QRectF, QPointF, Signal, QEvent
from PySide6.QtGui import QPainter, QPen, QFont, QPalette, QPolygonF
from PySide6.QtWidgets import QAbstractScrollArea, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QToolTip, QWidget

from northdiary.ui.date_picker import parse_partial
from northdiary.ui.theme import color, apply_theme, theme_name
from northdiary.ui.memory_dialog import MemoryDialog


@dataclass(frozen=True)
class DateGroup:
    value: str
    year: str
    label: str
    articles: tuple
    order: tuple
    kind: str = 'day'


def group_articles(articles):
    grouped = {}
    for article in articles:
        if not article.deleted_at:
            grouped.setdefault(article.diary_date, []).append(article)
    years, unknown = {}, []
    for value, rows in grouped.items():
        date, precision = parse_partial(value)
        if not date.isValid():
            unknown.extend(rows)
            continue
        year = years.setdefault(date.year(), {'articles': [], 'months': {}})
        if precision == 'year':
            year['articles'].extend(rows)
            continue
        month = year['months'].setdefault(date.month(), {'articles': [], 'days': []})
        if precision == 'month':
            month['articles'].extend(rows)
        else:
            month['days'].append(DateGroup(value, str(date.year()), f'{date.month():02d}月\n{date.day():02d}日',
                                           tuple(rows), (date.year(), date.month(), date.day(), value)))
    groups = []
    for year, year_data in sorted(years.items()):
        groups.append(DateGroup(f'{year:04d}-未知-未知', str(year), f'{year}年', tuple(year_data['articles']),
                                (year, 0, 0), 'year'))
        for month, month_data in sorted(year_data['months'].items()):
            groups.append(DateGroup(f'{year:04d}-{month:02d}-未知', str(year), f'{month:02d}月', tuple(month_data['articles']),
                                    (year, month, 0), 'month'))
            groups.extend(sorted(month_data['days'], key=lambda group: group.order))
    if unknown:
        groups.append(DateGroup('日期未详', '日期未详', '日期未详', tuple(unknown), (10000, 0, 0), 'unknown'))
    return groups


class TimelineCanvas(QAbstractScrollArea):
    selectedChanged = Signal(object)
    articleActivated = Signal(str)
    ROW = 112
    AXIS = 86
    EVENTS = 118
    CARD = 192
    STEP = 202

    def __init__(self, groups, parent=None):
        super().__init__(parent)
        self.groups = groups
        self.selected_index = 0 if groups else -1
        self.horizontal_offsets = {}
        self.pressed_id = None
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName('时间线总览：右半区上下滚动；左半区溢出事件小幅横移；回车打开回忆')
        self.setFrameShape(QAbstractScrollArea.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.viewport().setMouseTracking(True)
        self.verticalScrollBar().setSingleStep(48)
        self.verticalScrollBar().valueChanged.connect(self.update_selected)
        self.sync_scrollbar()

    def sync_scrollbar(self):
        self.verticalScrollBar().setRange(0, max(0, (len(self.groups) - 1) * self.ROW))
        self.verticalScrollBar().setPageStep(max(self.ROW, self.viewport().height() - self.ROW))
        for index in list(self.horizontal_offsets):
            self.horizontal_offsets[index] = min(self.horizontal_offsets[index], self.max_offset(index))

    def center_y(self, index):
        return self.viewport().height() / 2 + index * self.ROW - self.verticalScrollBar().value()

    def center_on(self, index):
        if self.groups:
            self.verticalScrollBar().setValue(max(0, min(index, len(self.groups) - 1)) * self.ROW)

    def update_selected(self, *_):
        index = min(len(self.groups) - 1, int(self.verticalScrollBar().value() / self.ROW + .5)) if self.groups else -1
        if index != self.selected_index:
            self.selected_index = index
            self.selectedChanged.emit(self.groups[index] if index >= 0 else None)
        self.viewport().update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.sync_scrollbar()
        self.update_selected()

    def scrollContentsBy(self, dx, dy):
        self.viewport().update()

    def max_offset(self, index):
        columns = math.ceil(len(self.groups[index].articles) / 2)
        available = max(1, self.viewport().width() - self.events_x(index) - 12)
        content_width = (columns - 1) * self.STEP + self.CARD if columns else 0
        return max(0, content_width - available)

    def events_x(self, index):
        return self.EVENTS if self.groups[index].kind == 'day' else 232

    def row_at(self, point):
        index = int(math.floor((point.y() - self.viewport().height() / 2 + self.verticalScrollBar().value()) / self.ROW + .5))
        if 0 <= index < len(self.groups) and abs(point.y() - self.center_y(index)) <= 44:
            return index
        return None

    def card_rect(self, index, position):
        active = index == self.selected_index
        height = 34 if active else 28
        center = self.center_y(index)
        y = center - height / 2 if len(self.groups[index].articles) == 1 else center - 36 + position % 2 * 40
        x = self.events_x(index) + position // 2 * self.STEP - self.horizontal_offsets.get(index, 0)
        return QRectF(x, y, self.CARD, height)

    def hit_article(self, point):
        index = self.row_at(point)
        if index is None or point.x() < self.events_x(index):
            return None
        offset = self.horizontal_offsets.get(index, 0)
        column = int((point.x() - self.events_x(index) + offset) // self.STEP)
        for position in (column * 2, column * 2 + 1):
            if 0 <= position < len(self.groups[index].articles) and self.card_rect(index, position).contains(point):
                return self.groups[index].articles[position]
        return None

    def wheelEvent(self, event):
        point = event.position()
        index = self.row_at(point)
        pixels, angles = event.pixelDelta(), event.angleDelta()
        dialog_point = self.viewport().mapTo(self.window(), point.toPoint())
        if (dialog_point.x() < self.window().width() / 2 and index is not None
                and point.x() >= self.events_x(index) and self.max_offset(index) > 0):
            delta = pixels.x() or pixels.y() or (angles.x() or angles.y()) / 120 * 24
            delta = max(-36, min(36, delta))
            offset = self.horizontal_offsets.get(index, 0) - delta
            self.horizontal_offsets[index] = max(0, min(self.max_offset(index), offset))
            self.viewport().update()
        else:
            self.scroll_vertical(event)
        event.accept()

    def scroll_vertical(self, event):
        pixels, angles = event.pixelDelta(), event.angleDelta()
        delta = pixels.y() or pixels.x() or (angles.y() or angles.x()) / 120 * 96
        self.verticalScrollBar().setValue(round(self.verticalScrollBar().value() - delta))
        event.accept()

    def keyPressEvent(self, event):
        key = event.key()
        if key in (Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_Home, Qt.Key.Key_End,
                   Qt.Key.Key_PageUp, Qt.Key.Key_PageDown):
            index = self.selected_index
            if key == Qt.Key.Key_Up: index -= 1
            elif key == Qt.Key.Key_Down: index += 1
            elif key == Qt.Key.Key_Home: index = 0
            elif key == Qt.Key.Key_End: index = len(self.groups) - 1
            elif key == Qt.Key.Key_PageUp: index -= max(1, self.viewport().height() // self.ROW)
            else: index += max(1, self.viewport().height() // self.ROW)
            self.center_on(index)
            event.accept()
        elif self.selected_index >= 0 and key in (Qt.Key.Key_Left, Qt.Key.Key_Right):
            index = self.selected_index
            delta = 48 if key == Qt.Key.Key_Right else -48
            self.horizontal_offsets[index] = max(0, min(self.max_offset(index), self.horizontal_offsets.get(index, 0) + delta))
            self.viewport().update()
        elif self.selected_index >= 0 and key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self.groups[self.selected_index].articles:
                self.articleActivated.emit(self.groups[self.selected_index].articles[0].id)
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        article = self.hit_article(event.position()) if event.button() == Qt.MouseButton.LeftButton else None
        self.pressed_id = article.id if article else None
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        article = self.hit_article(event.position()) if event.button() == Qt.MouseButton.LeftButton else None
        if article and article.id == self.pressed_id:
            self.pressed_id = None
            self.articleActivated.emit(article.id)
            event.accept()
            return
        self.pressed_id = None
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        article = self.hit_article(event.position())
        self.viewport().setCursor(Qt.CursorShape.PointingHandCursor if article else Qt.CursorShape.ArrowCursor)
        if article:
            QToolTip.showText(event.globalPosition().toPoint(), article.title, self.viewport())
        else:
            QToolTip.hideText()
        super().mouseMoveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.viewport().rect(), self.palette().color(QPalette.ColorRole.Base))
        if not self.groups:
            painter.setPen(color('#75827a', self))
            painter.drawText(self.viewport().rect(), Qt.AlignmentFlag.AlignCenter, '还没有文章，时间线会从第一段回忆开始。')
            return
        painter.setPen(QPen(color('#c5d2c5', self), 2))
        end = self.center_y(len(self.groups) - 1) + 82
        painter.drawLine(QPointF(self.AXIS, self.center_y(0)), QPointF(self.AXIS, end))
        painter.drawPolyline(QPolygonF([QPointF(self.AXIS - 6, end - 8), QPointF(self.AXIS, end),
                                        QPointF(self.AXIS + 6, end - 8)]))
        first = max(0, int((self.verticalScrollBar().value() - self.viewport().height() / 2 - 70) // self.ROW))
        last = min(len(self.groups), first + self.viewport().height() // self.ROW + 4)
        for index in range(first, last):
            group, center = self.groups[index], self.center_y(index)
            active = index == self.selected_index
            if active:
                fill = color('#82ad8b', self)
                fill.setAlpha(30)
                painter.setBrush(fill)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(QRectF(4, center - 47, self.viewport().width() - 12, 94), 12, 12)
            painter.setBrush(color('#82ad8b', self))
            painter.setPen(QPen(self.palette().color(QPalette.ColorRole.Base), 2))
            if group.kind == 'day':
                radius = 6 if active else 4
                painter.drawEllipse(QPointF(self.AXIS, center), radius, radius)
            else:
                painter.setBrush(self.palette().color(QPalette.ColorRole.Base))
                painter.setPen(QPen(color('#82ad8b', self), 2))
                side = 14 if group.kind == 'year' else 10
                painter.drawRect(QRectF(self.AXIS - side / 2, center - side / 2, side, side))
            font = QFont(self.font())
            font.setPixelSize(16 if active else 13)
            font.setWeight(QFont.Weight.DemiBold if active else QFont.Weight.Normal)
            painter.setFont(font)
            painter.setPen(self.palette().color(QPalette.ColorRole.Text))
            if group.kind == 'day':
                painter.drawText(QRectF(8, center - 29, self.AXIS - 20, 58),
                                 Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, group.label)
            else:
                font.setPixelSize((22 if active else 20) if group.kind == 'year' else (19 if active else 17))
                font.setWeight(QFont.Weight.DemiBold)
                painter.setFont(font)
                painter.drawText(QRectF(self.AXIS + 18, center - 20, 118, 40), Qt.AlignmentFlag.AlignVCenter, group.label)
                if group.articles and group.kind in ('year', 'month'):
                    font.setPixelSize(11)
                    font.setWeight(QFont.Weight.Normal)
                    painter.setFont(font)
                    painter.setPen(color('#75827a', self))
                    painter.drawText(QRectF(self.AXIS + 20, center + 14, 118, 20), Qt.AlignmentFlag.AlignVCenter,
                                     '月份未详' if group.kind == 'year' else '日期未详')
            painter.save()
            left = self.events_x(index)
            painter.setClipRect(QRectF(left, center - 44, max(0, self.viewport().width() - left - 12), 88))
            font.setPixelSize(14 if active else 12)
            font.setWeight(QFont.Weight.DemiBold if active else QFont.Weight.Normal)
            painter.setFont(font)
            offset = self.horizontal_offsets.get(index, 0)
            start = max(0, int(offset // self.STEP) * 2)
            count = (math.ceil(max(1, self.viewport().width() - left) / self.STEP) + 1) * 2
            for position in range(start, min(len(group.articles), start + count)):
                rect = self.card_rect(index, position)
                fill = self.palette().color(QPalette.ColorRole.Window)
                fill.setAlpha(160 if active else 95)
                painter.setBrush(fill)
                painter.setPen(QPen(color('#d4ddd1', self), .8))
                painter.drawRoundedRect(rect, 7, 7)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(color('#82ad8b', self))
                painter.drawEllipse(QPointF(rect.left() + 11, rect.center().y()), 2.5, 2.5)
                painter.setPen(self.palette().color(QPalette.ColorRole.Text))
                title = painter.fontMetrics().elidedText(group.articles[position].title,
                                                        Qt.TextElideMode.ElideRight, self.CARD - 34)
                painter.drawText(rect.adjusted(22, 0, -12, 0), Qt.AlignmentFlag.AlignVCenter, title)
            painter.restore()


class TimelineOverview(QDialog):
    def __init__(self, repository, attachments, parent=None):
        super().__init__(parent)
        self.repository, self.attachments = repository, attachments
        self.setWindowTitle('时间线总览')
        self.resize(1030, 680)
        self.setMinimumSize(620, 420)
        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        self.year = QLabel()
        self.year.setTextFormat(Qt.TextFormat.PlainText)
        font = QFont(self.font())
        font.setPixelSize(24)
        font.setWeight(QFont.Weight.DemiBold)
        self.year.setFont(font)
        self.year.setStyleSheet('QLabel { font-size: 24px; font-weight: 600; background: transparent; }')
        row.addWidget(self.year)
        row.addStretch()
        layout.addLayout(row)
        groups = group_articles(repository.list(sort='created_asc', pinned_first=False))
        self.canvas = TimelineCanvas(groups, self)
        self.canvas.selectedChanged.connect(self.update_year)
        self.canvas.articleActivated.connect(self.open_article)
        layout.addWidget(self.canvas, 1)
        self.update_year(groups[0] if groups else None)
        first_article = next((index for index, group in enumerate(groups) if group.articles), 0)
        self.canvas.center_on(first_article)
        footer = QHBoxLayout()
        footer.addStretch()
        close = QPushButton('关闭')
        close.clicked.connect(self.accept)
        footer.addWidget(close)
        layout.addLayout(footer)
        dark = parent.palette().color(QPalette.ColorRole.Window).lightness() < 128 if parent else False
        apply_theme(self, dark, theme_name(parent) if parent else None)
        self.installEventFilter(self)
        for widget in self.findChildren(QWidget):
            widget.installEventFilter(self)

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.Wheel:
            point = self.mapFromGlobal(event.globalPosition().toPoint())
            if point.x() >= self.width() / 2:
                self.canvas.scroll_vertical(event)
                return True
        return super().eventFilter(watched, event)

    def update_year(self, group):
        self.year.setText(group.year if group else '时间线')

    def open_article(self, article_id):
        dialog = MemoryDialog(self.repository, self.attachments, self, article_id=article_id)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dialog.exec()
