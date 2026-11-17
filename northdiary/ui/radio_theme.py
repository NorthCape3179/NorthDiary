"""Native, resolution-independent objects for the Midnight Radio theme."""
import math

from PySide6.QtCore import Qt, Signal, QTimer, QRectF, QPointF
from PySide6.QtGui import QColor, QPainter, QPen, QLinearGradient, QRadialGradient, QFont, QPainterPath
from PySide6.QtWidgets import QDial, QWidget


# Keys are the original light palette, as used by the other native themes.
RADIO_COLORS = {
    '#f6f5f1': '#101b28', '#273b37': '#dce8ec', '#e9ede7': '#142130',
    '#fffefa': '#182637', '#e3e5dd': '#304553', '#f0f1eb': '#142130',
    '#244d42': '#a9dddd', '#75827a': '#9ab1be', '#dce2d8': '#3a505e',
    '#7d9b89': '#81c8cc', '#dbe7d8': '#294653', '#d6dfd1': '#3a505e',
    '#e9eee5': '#213343', '#526959': '#b4cbd4', '#f0f3ec': '#1b2c3d',
    '#e4e9df': '#304553', '#cfe0d2': '#365664', '#d4ddd1': '#3a505e',
    '#e0e9dd': '#294653', '#d3e2d2': '#365664', '#315c4d': '#81c8cc',
    '#416f5d': '#9edbdc', '#a0aaa0': '#708893', '#eeeee9': '#1a2733',
    '#d5e1d0': '#294653', '#234735': '#e2f0f1', '#e0e8db': '#233b49',
    '#708075': '#9ab1be', '#eee4d3': '#493c36', '#dfe9dc': '#294653',
    '#708273': '#9ab1be', '#e9eee7': '#203745', '#f1f3ed': '#1b2c3d',
    '#c5d2c5': '#405966', '#a1b3a4': '#71919e', '#788b7c': '#9ab1be',
    '#d1e1d3': '#49737d', '#82ad8b': '#ace1df', '#9a5348': '#e9a99b',
    '#527c61': '#81c8cc',
}

RADIO_STYLE = '''
QWidget#sidebar, QWidget#properties { border: 1px solid #304553; border-radius: 14px; }
QWidget#paper { background: #182637; border: 1px solid #3a505e; border-radius: 14px; }
QLabel#brand { color: #bce2e4; font-family: "Microsoft YaHei UI"; }
QLabel#section { color: #b4cbd4; }
QLineEdit, QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox { background: #152330; border-color: #3a505e; border-radius: 7px; }
QLineEdit#title { background: transparent; color: #dce8ec; border: none; }
QPushButton { background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #213443,stop:1 #192b39); border: 1px solid #3a505e; border-radius: 8px; }
QPushButton:hover { background: #294653; border-color: #81c8cc; }
QPushButton#primary { background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #98d6d7,stop:1 #76babe); color: #102b32; border: 1px solid transparent; }
QPushButton#primary:hover { background: #a9dddd; border-color: #dce8ec; }
QPushButton#primary:pressed { background: #76babe; color: #102b32; }
QPushButton[buttonTone="accent"] { background: #233b49; color: #bce2e4; border-color: #3a505e; }
QPushButton[buttonTone="accent"]:hover { background: #294653; border-color: #81c8cc; }
QPushButton[buttonTone="danger"] { background: transparent; color: #e9a99b; border-color: #3a505e; }
QPushButton[buttonTone="danger"]:hover { border-color: #e9a99b; background: #322f33; }
QListWidget::item:selected, ArticleList::item:selected:hover { background: #294653; color: #e2f0f1; }
QStatusBar { background: #101b28; color: #9ab1be; }
'''


def draw_waveform(painter, rect, phase=0.0, active=False, tint='#81c8cc'):
    """Decorative signal motif, not an audio spectrum or measured level."""
    painter.save()
    painter.setClipRect(rect)
    pen = QPen(QColor(tint), 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)
    count = max(1, int(rect.width() / 5))
    for i in range(count):
        # Static when idle; only moves while real playback is progressing.
        envelope = .25 + .75 * abs(math.sin(i * .67 + (phase if active else 0)))
        height = (rect.height() - 3) * envelope * (1 if active else .48)
        x = rect.left() + i * 5 + 2
        painter.drawLine(QPointF(x, rect.center().y() - height / 2),
                         QPointF(x, rect.center().y() + height / 2))
    painter.restore()


class RadioDial(QDial):
    """An endless tuning knob. One 12-degree detent means one calendar day."""
    dayStepped = Signal(int)
    tuningFinished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRange(0, 359)
        self.setWrapping(True)
        self.setSingleStep(12)
        self.setPageStep(84)
        self.setFixedSize(52, 52)
        self.setAccessibleName('日期调谐旋钮')
        self.setToolTip('旋转浏览日期；方向键或滚轮每格一天，Page Up / Down 每格一周')
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setStyleSheet('background: transparent; border: none;')
        self.previous_value = self.value()
        self.remainder = 0
        self.last_angle = None
        self.idle = QTimer(self)
        self.idle.setSingleShot(True)
        self.idle.setInterval(220)
        self.idle.timeout.connect(self.tuningFinished)
        self.valueChanged.connect(self.turn)

    def turn(self, value):
        delta = (value - self.previous_value + 180) % 360 - 180
        self.previous_value = value
        self.remainder += delta
        days = math.trunc(self.remainder / 12)
        if days:
            self.remainder -= days * 12
            self.dayStepped.emit(days)
        self.update()

    def angle_at(self, point):
        return math.degrees(math.atan2(point.x() - self.width() / 2,
                                       self.height() / 2 - point.y()))

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return event.ignore()
        self.idle.stop()
        self.last_angle = self.angle_at(event.position())
        self.setSliderDown(True)
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        self.setCursor(Qt.CursorShape.ClosedHandCursor)
        event.accept()

    def mouseMoveEvent(self, event):
        if self.last_angle is None:
            return event.ignore()
        angle = self.angle_at(event.position())
        delta = (angle - self.last_angle + 180) % 360 - 180
        if abs(delta) >= 1:
            self.setValue((self.value() + round(delta)) % 360)
            self.last_angle = angle
        event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton or self.last_angle is None:
            return event.ignore()
        self.last_angle = None
        self.setSliderDown(False)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.tuningFinished.emit()
        event.accept()

    def keyPressEvent(self, event):
        steps = {Qt.Key.Key_Right: 1, Qt.Key.Key_Up: 1,
                 Qt.Key.Key_Left: -1, Qt.Key.Key_Down: -1,
                 Qt.Key.Key_PageUp: 7, Qt.Key.Key_PageDown: -7}
        if event.key() not in steps:
            return super().keyPressEvent(event)
        self.setValue((self.value() + steps[event.key()] * 12) % 360)
        self.idle.start()
        event.accept()

    def wheelEvent(self, event):
        amount = event.angleDelta().y()
        if not amount:
            return event.ignore()
        self.setValue((self.value() + (12 if amount > 0 else -12)) % 360)
        self.idle.start()
        event.accept()

    def hideEvent(self, event):
        self.idle.stop()
        self.last_angle = None
        self.setSliderDown(False)
        super().hideEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        center = QPointF(26, 26)
        p.setPen(QPen(QColor('#63808b'), .8))
        for angle in range(0, 360, 30):
            theta = math.radians(angle)
            p.drawLine(center + QPointF(math.sin(theta)*23, -math.cos(theta)*23),
                       center + QPointF(math.sin(theta)*25, -math.cos(theta)*25))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 65))
        p.drawEllipse(QRectF(7, 9, 39, 39))
        metal = QRadialGradient(QPointF(18, 13), 39)
        metal.setColorAt(0, QColor('#536d7b'))
        metal.setColorAt(.65, QColor('#2c424f'))
        metal.setColorAt(1, QColor('#192c38'))
        p.setBrush(metal)
        p.setPen(QPen(QColor('#6b8792'), .9))
        p.drawEllipse(QRectF(6, 6, 40, 40))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor('#243946'), 2))
        p.drawEllipse(QRectF(10, 10, 32, 32))
        p.translate(center)
        p.rotate(self.value())
        p.setPen(QPen(QColor('#b9e7e3'), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(0, -15), QPointF(0, -8))
        p.resetTransform()
        if self.hasFocus():
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor('#a9dddd'), 1, Qt.PenStyle.DotLine))
            p.drawEllipse(QRectF(1, 1, 50, 50))


def paint_tuner(widget, painter):
    """The existing continuous time axis, housed in a native radio console."""
    width, height = widget.width(), widget.height()
    frame = QRectF(.5, .5, width - 1, height - 1)
    metal = QLinearGradient(0, 0, 0, height)
    metal.setColorAt(0, QColor('#263b4b'))
    metal.setColorAt(1, QColor('#192c39'))
    painter.setBrush(metal)
    painter.setPen(QPen(QColor('#405967'), 1))
    painter.drawRoundedRect(frame, 9, 9)
    screen = QRectF(7, 6, max(30, width - 70), height - 12)
    painter.setBrush(QColor('#0b1922'))
    painter.setPen(QPen(QColor('#344d59'), 1))
    painter.drawRoundedRect(screen, 3, 3)
    painter.save()
    painter.setClipRect(screen.adjusted(2, 1, -2, -1))
    mid = screen.center().x()
    font = QFont(widget.font())
    font.setPixelSize(11)
    painter.setFont(font)
    painter.setPen(QColor('#b0dddd'))
    painter.drawText(screen.adjusted(6, 0, -6, -23), Qt.AlignmentFlag.AlignCenter,
                     widget.selected.toString('yyyy / MM / dd'))
    half = screen.width() / 2 / widget.spacing
    y = screen.top() + 24
    for day in range(math.floor(widget.view_center-half), math.ceil(widget.view_center+half)+1):
        x = mid + (day-widget.view_center)*widget.spacing
        date = widget.origin.addDays(day)
        painter.setPen(QPen(QColor('#587783'), .8))
        for minor in range(4):
            mx = x + minor * widget.spacing / 4
            painter.drawLine(QPointF(mx, y-5), QPointF(mx, y-(0 if minor == 0 else 2)))
        painter.setPen(QColor('#91aeba'))
        painter.drawText(QRectF(x-18, y+1, 36, 13), Qt.AlignmentFlag.AlignCenter,
                         date.toString('M/d') if date.day() == 1 else str(date.day()))
    pointer = mid + (widget.position_days-widget.view_center)*widget.spacing
    painter.setPen(QPen(QColor('#a9dddd'), 1.2))
    painter.drawLine(QPointF(pointer, y-9), QPointF(pointer, screen.bottom()-2))
    painter.restore()


def paint_radio_paper(widget, painter):
    """Quiet speaker cloth and signal details live outside the editable text."""
    rect = QRectF(widget.rect()).adjusted(2, 2, -2, -2)
    painter.save()
    clip = QPainterPath()
    clip.addRoundedRect(rect, 12, 12)
    painter.setClipPath(clip)
    gradient = QLinearGradient(0, 0, widget.width(), widget.height())
    gradient.setColorAt(0, QColor('#1d3043'))
    gradient.setColorAt(1, QColor('#162534'))
    painter.fillRect(rect, gradient)
    # Bottom only: no texture behind the main reading area.
    tint = QColor('#81c8cc')
    tint.setAlpha(13)
    painter.setPen(QPen(tint, .7))
    for y in range(max(18, widget.height()-130), widget.height()-12, 7):
        for x in range(18, widget.width()-14, 9):
            painter.drawPoint(x, y)
    for x in (12, widget.width()-12):
        for y in (12, widget.height()-12):
            painter.setBrush(QColor('#152634'))
            painter.setPen(QPen(QColor('#4a6270'), .8))
            painter.drawEllipse(QPointF(x, y), 2, 2)
            painter.drawLine(QPointF(x-1, y), QPointF(x+1, y))
    painter.restore()


def paint_radio_lyrics(canvas, painter):
    """Keep real track timing, manual plain-text scroll and translation support."""
    from bisect import bisect_right
    b = canvas.board
    width, height = canvas.width(), canvas.height()
    track = b.track
    playing = bool(track and track.get('playing'))
    known = bool(track and track.get('position_known', True))
    font = QFont('Microsoft YaHei UI')
    font.setPixelSize(11)
    painter.setFont(font)
    painter.setPen(QColor('#91aeba'))
    painter.drawText(QRectF(11, 0, max(1, width-22), 18),
                     Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, 'PRIVATE FM / 私人电台')
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor('#a9dddd' if playing else '#627e8b'))
    painter.drawEllipse(QPointF(width-14, 9), 2.5, 2.5)
    painter.setPen(QColor('#b4cbd4'))
    caption = painter.fontMetrics().elidedText(b.caption, Qt.TextElideMode.ElideRight, max(1, width-24))
    painter.drawText(QRectF(11, 19, max(1, width-22), 17), Qt.AlignmentFlag.AlignLeft, caption)
    painter.setPen(QPen(QColor('#29404e'), .7))
    painter.drawLine(QPointF(11, 38), QPointF(width-11, 38))
    clock = '未连接'
    if known:
        seconds = max(0, int(b.position()))
        clock = f'{seconds // 60:02}:{seconds % 60:02}' + (' · 播放中' if playing else ' · 暂停')
    elif track:
        clock = '等待进度' if playing else '已暂停'
    draw_waveform(painter, QRectF(12, height-20, max(10, min(96, width-160)), 17),
                  phase=b.position() * 2 if known else 0, active=playing and known)
    painter.setFont(font)
    painter.setPen(QColor('#91aeba'))
    painter.drawText(QRectF(max(12, width-150), height-21, min(138, width-24), 18),
                     Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, clock)
    lines = b.lines
    entries = [row[1] for row in lines] if lines else b.plain
    index = bisect_right(b.stamps, b.position() + b.offset.value()/1000)-1 if lines else b.plain_index
    translated = ''
    if lines and not known:
        current = '已匹配歌词 · ' + (track.get('progress_detail') or '等待网易云提供准确播放进度') if track else '等待网易云提供准确播放进度'
    elif entries:
        current = (entries[index] or '♪') if 0 <= index < len(entries) else '♪'
        if lines and 0 <= index < len(lines):
            translated = b.translations.get(lines[index][0], '')
    else:
        current = b.message
    body = QRectF(12, 44, max(1, width-24), max(1, height-72))
    painter.save()
    painter.setClipRect(body)
    flags = Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap
    lyric_font = QFont(b.family())
    size = b.font_size.value() if entries and not (lines and not known) else 17
    for pixels in range(size, 15, -1):
        lyric_font.setPixelSize(pixels)
        painter.setFont(lyric_font)
        current_height = painter.boundingRect(QRectF(0, 0, body.width(), 1000), flags, current).height()+2
        translation_font = QFont(b.family())
        translation_font.setPixelSize(max(14, pixels-5))
        painter.setFont(translation_font)
        translation_height = painter.boundingRect(QRectF(0, 0, body.width(), 1000), flags, translated).height()+2 if translated else 0
        total = current_height + (4+translation_height if translated else 0)
        if total <= body.height():
            break
    # Very long metadata or lyrics get an honest elision rather than overlapping chrome.
    if total > body.height():
        painter.setFont(lyric_font)
        current = painter.fontMetrics().elidedText(current.replace('\n', ' '), Qt.TextElideMode.ElideRight, round(body.width()))
        current_height = painter.fontMetrics().height()+2
        painter.setFont(translation_font)
        translated = painter.fontMetrics().elidedText(translated.replace('\n', ' '), Qt.TextElideMode.ElideRight, round(body.width()))
        translation_height = painter.fontMetrics().height()+2 if translated else 0
        total = current_height + (4+translation_height if translated else 0)
    top = body.center().y()-total/2
    painter.setFont(lyric_font)
    painter.setPen(QColor('#c4e9e6'))
    painter.drawText(QRectF(body.left(), top, body.width(), current_height), flags, current)
    if translated:
        painter.setFont(translation_font)
        painter.setPen(QColor('#a3bdc7'))
        painter.drawText(QRectF(body.left(), top+current_height+4, body.width(), translation_height), flags, translated)
    painter.restore()


class RadioStation(QWidget):
    """Static receiver detail: visible only with the Radio theme."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(76)
        self.setMinimumWidth(0)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAccessibleName('私人电台装饰')
        self.setStyleSheet('background: transparent;')

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor('#0b1722'), 2))
        for y in range(5, 33, 5):
            p.drawLine(0, y, self.width(), y)
        font = QFont('Consolas')
        font.setPixelSize(11)
        p.setFont(font)
        p.setPen(QColor('#91aeba'))
        p.drawText(QRectF(0, 39, self.width(), 17), Qt.AlignmentFlag.AlignLeft, 'N / D   PRIVATE FM')
        draw_waveform(p, QRectF(0, 60, max(10, self.width()), 13), tint='#587a89')
