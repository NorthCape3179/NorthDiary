"""A translucent lyrics board occupying the reading-mode photo board slot."""
from bisect import bisect_right
from pathlib import Path
import time

from PySide6.QtCore import Qt, QTimer, QRectF, QPoint, QEvent
from PySide6.QtGui import QColor, QFont, QFontDatabase, QPainter, QPen, QPixmap, QIcon, QRadialGradient, QPalette
from PySide6.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QSpinBox, QPushButton, QCheckBox
from northdiary.services.lyrics import MediaObserver, LyricsLookup
from northdiary.ui.controls import ComboBox, FloatingPanel
from northdiary.ui.theme import color, themed_css, theme_name


def lyrics_icon(widget, checked=False):
    ratio = widget.devicePixelRatioF()
    pixmap = QPixmap(round(24 * ratio), round(24 * ratio))
    pixmap.setDevicePixelRatio(ratio)
    pixmap.fill(Qt.GlobalColor.transparent)
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    tint = color('#315c4d', widget)
    if checked:
        # Reverse foreground against the selected accent background.
        tint = QColor('#fffefa') if tint.lightnessF() < .6 else QColor('#191a1c')
    p.setPen(QPen(tint, 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    for y, width in ((6, 11), (11, 8), (16, 6)):
        p.drawLine(3, y, width, y)
    p.drawLine(18, 5, 18, 17)
    p.drawLine(18, 5, 22, 7)
    p.setBrush(tint)
    p.drawEllipse(QRectF(13, 16, 5, 4))
    p.end()
    return QIcon(pixmap)


class LyricsCanvas(QWidget):
    def __init__(self, board):
        super().__init__(board)
        self.board = board
        self.setMinimumHeight(115)
        self.setStyleSheet('background: transparent;')

    def wheelEvent(self, event):
        board = self.board
        if not board.lines and board.plain:
            board.plain_index = max(0, min(len(board.plain) - 1,
                board.plain_index + (-1 if event.angleDelta().y() > 0 else 1)))
            self.update()
            event.accept()
        else:
            event.ignore()

    def paintEvent(self, event):
        b = self.board
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        tint = color('#315c4d', self)
        white = QColor.fromRgbF(.9 + tint.redF() * .1, .9 + tint.greenF() * .1, .9 + tint.blueF() * .1)
        painter.setFont(QFont(self.font().family(), 8))
        painter.setPen(QColor(255, 255, 255, 165))
        known = b.track and b.track.get('position_known', True)
        if known:
            seconds = int(b.position())
            clock = f'{seconds // 60:02}:{seconds % 60:02}'
            if not b.track['playing']:
                clock += ' · 暂停'
        else:
            clock = '读取进度中'
        title_width = max(20, self.width() * .38 - 20)
        caption = painter.fontMetrics().elidedText(b.caption, Qt.TextElideMode.ElideRight, round(title_width))
        painter.drawText(QRectF(12, 0, title_width, 20), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, caption)
        painter.drawText(QRectF(self.width() - 120, self.height() - 23, 108, 21), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, clock)
        body = QRectF(18, 28, self.width() - 36, self.height() - 58)
        if b.lines and not known:
            painter.setFont(QFont(b.family(), 11))
            painter.setPen(white)
            painter.drawText(body, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                             '已匹配歌词 · ' + (b.track.get('progress_detail') or '等待网易云提供准确播放进度')
                             if b.track else '等待网易云提供准确播放进度')
            return
        lines = b.lines
        index = bisect_right(b.stamps, b.position() + b.offset.value() / 1000) - 1 if lines else b.plain_index
        entries = [row[1] for row in lines] if lines else b.plain
        if not entries:
            painter.setFont(QFont(b.family(), 11))
            painter.setPen(white)
            painter.drawText(body, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, b.message)
            return
        current = (entries[index] or '♪') if 0 <= index < len(entries) else '♪'
        def surrounding(i, step):
            while 0 <= i < len(entries):
                if entries[i].strip():
                    translated = b.translations.get(lines[i][0], '') if lines else ''
                    return entries[i], translated
                i += step
            return '', ''

        previous, previous_translation = surrounding(index - 1, -1)
        following, next_translation = surrounding(index + 1, 1)
        painter.setPen(QColor(white.red(), white.green(), white.blue(), 125))
        small = QFont(b.family())
        small.setPixelSize(max(12, b.font_size.value() - 11))
        painter.setFont(small)
        previous_rect = QRectF(self.width() * .40, 0, self.width() * .60 - 12, 22)
        next_rect = QRectF(12, self.height() - 23, self.width() - 145, 22)
        for content, rect, alignment in ((previous, previous_rect, Qt.AlignmentFlag.AlignRight),
                                         (following, next_rect, Qt.AlignmentFlag.AlignLeft)):
            elided = painter.fontMetrics().elidedText(content, Qt.TextElideMode.ElideRight, round(rect.width()))
            painter.drawText(rect, alignment | Qt.AlignmentFlag.AlignVCenter, elided)
        corner_translation = QFont(b.family())
        corner_translation.setPixelSize(max(11, b.font_size.value() - 12))
        painter.setFont(corner_translation)
        painter.setPen(QColor(white.red(), white.green(), white.blue(), 115))
        for content, rect, alignment in (
            (previous_translation, QRectF(previous_rect.left(), 21, previous_rect.width(), 18), Qt.AlignmentFlag.AlignRight),
            (next_translation, QRectF(next_rect.left(), self.height() - 43, next_rect.width(), 18), Qt.AlignmentFlag.AlignLeft),
        ):
            elided = painter.fontMetrics().elidedText(content, Qt.TextElideMode.ElideRight, round(rect.width()))
            painter.drawText(rect, alignment | Qt.AlignmentFlag.AlignVCenter, elided)

        translated = b.translations.get(lines[index][0], '') if lines and 0 <= index < len(lines) else ''
        middle = body

        # A soft pool of light behind the current phrase, fading to transparent.
        glow_rect = middle.adjusted(-8, -12, 8, 10)
        painter.save()
        painter.setClipRect(glow_rect)
        painter.translate(glow_rect.center())
        painter.scale(max(1, glow_rect.width() / 2), max(1, glow_rect.height() / 2))
        glow = QRadialGradient(0, 0, 1)
        highlight = QColor.fromRgbF(.75 + tint.redF() * .25, .75 + tint.greenF() * .25,
                                    .75 + tint.blueF() * .25, .13)
        glow.setColorAt(0, highlight)
        highlight.setAlpha(18)
        glow.setColorAt(.55, highlight)
        highlight.setAlpha(0)
        glow.setColorAt(1, highlight)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(glow)
        painter.drawEllipse(QRectF(-1, -1, 2, 2))
        painter.restore()

        font = QFont(b.family())
        font.setPixelSize(max(18, b.font_size.value()))
        font.setWeight(QFont.Weight.Medium)
        painter.setFont(font)
        painter.setPen(white)
        flags = Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap
        original_height = painter.boundingRect(QRectF(0, 0, middle.width(), 200), flags, current).height()
        original_height = min(original_height + 2, middle.height() * .54 if translated else middle.height())
        translation_height = 0
        if translated:
            small.setPixelSize(max(17, b.font_size.value() - 1))
            painter.setFont(small)
            translation_height = painter.boundingRect(QRectF(0, 0, middle.width(), 200), flags, translated).height() + 2
            translation_height = min(translation_height, middle.height() - original_height - 3)
        group_height = original_height + (3 + translation_height if translated else 0)
        top = middle.center().y() - group_height / 2
        painter.setFont(font)
        painter.drawText(QRectF(middle.left(), top, middle.width(), original_height), flags, current)
        if translated:
            painter.setFont(small)
            painter.setPen(QColor(white.red(), white.green(), white.blue(), 225))
            painter.drawText(QRectF(middle.left(), top + original_height + 3, middle.width(), translation_height), flags, translated)


class LyricsBoard(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(180)
        self.setStyleSheet('QWidget { background: transparent; }')
        self.track = None
        self.track_key = None
        self.lines, self.stamps, self.plain = [], [], []
        self.translations = {}
        self.lyric_source = ''
        self.plain_index = 0
        self.message = '在网易云音乐播放一首歌…'
        self.caption = '网易云音乐 · 歌词'
        self.observer = None
        self.enabled = False
        self.settings = None
        self.loaded_fonts = {}
        self.lookup = LyricsLookup(self)
        self.lookup.ready.connect(self.set_lyrics)
        self.lookup.message.connect(self.set_message)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 6)
        layout.setSpacing(3)
        self.font_choice = ComboBox(self)
        self.font_choice.setFixedWidth(132)
        for label, key in [('思源黑体', 'noto-sans-sc'), ('思源宋体', 'noto-serif-sc'),
                           ('霞鹜文楷', 'lxgw-wenkai'), ('融合像素', 'fusion-pixel')]:
            self.font_choice.addItem(label, key)
        self.font_choice.setCurrentIndex(self.font_choice.findData('fusion-pixel'))
        self.font_choice.setAccessibleName('歌词字体')
        self.font_choice.setToolTip('随软件提供的免费商用开源字体（OFL），仅应用于歌词')
        self.font_choice.hide()
        self.font_size = QSpinBox(self)
        self.font_size.setRange(16, 32)
        self.font_size.setValue(27)
        self.font_size.setSuffix(' px')
        self.font_size.setFixedWidth(65)
        self.font_size.setToolTip('歌词字号')
        self.font_size.setAccessibleName('歌词字号')
        self.font_size.hide()
        self.offset = QSpinBox(self)
        self.offset.setRange(-10000, 10000)
        self.offset.setSingleStep(100)
        self.offset.setSuffix(' ms')
        self.offset.setPrefix('提前 ')
        self.offset.setFixedWidth(115)
        self.offset.setToolTip('同步微调：正数使歌词提前，负数使歌词延后；对所有歌曲生效')
        self.offset.setAccessibleName('歌词同步偏移')
        self.offset.hide()
        self.canvas = LyricsCanvas(self)
        layout.addWidget(self.canvas, 1)
        self.font_choice.currentIndexChanged.connect(self.preferences_changed)
        self.font_size.valueChanged.connect(self.preferences_changed)
        self.offset.valueChanged.connect(self.preferences_changed)
        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.canvas.update)

    def bind_settings(self, settings):
        self.settings = settings
        if not settings.value('lyrics_pixel27_default_v1', False, type=bool):
            settings.setValue('lyrics_font', 'fusion-pixel')
            settings.setValue('lyrics_size', 27)
            settings.setValue('lyrics_pixel27_default_v1', True)
        for widget in (self.font_choice, self.font_size, self.offset):
            widget.blockSignals(True)
        self.font_choice.setCurrentIndex(max(0, self.font_choice.findData(settings.value('lyrics_font', 'fusion-pixel'))))
        self.font_size.setValue(settings.value('lyrics_size', 27, type=int))
        self.offset.setValue(settings.value('lyrics_offset', 0, type=int))
        for widget in (self.font_choice, self.font_size, self.offset):
            widget.blockSignals(False)

    def preferences_changed(self, *_):
        if self.settings:
            self.settings.setValue('lyrics_font', self.font_choice.currentData())
            self.settings.setValue('lyrics_size', self.font_size.value())
            self.settings.setValue('lyrics_offset', self.offset.value())
        self.canvas.update()

    def family(self):
        key = self.font_choice.currentData()
        if key not in self.loaded_fonts:
            path = Path(__file__).resolve().parent.parent / 'assets/lyrics-fonts' / key / 'font.ttf'
            font_id = QFontDatabase.addApplicationFont(str(path))
            families = QFontDatabase.applicationFontFamilies(font_id) if font_id >= 0 else []
            self.loaded_fonts[key] = families[0] if families else self.font().family()
        return self.loaded_fonts[key]

    def set_active(self, active):
        self.enabled = active
        if active:
            self.timer.start()
            if self.observer is None:
                self.observer = MediaObserver(self)
                self.observer.snapshot.connect(self.accept_snapshot)
                self.observer.unavailable.connect(self.observer_message)
                self.observer.finished.connect(self.observer_finished)
                self.observer.start()
        else:
            self.timer.stop()
            self.lookup.cancel()
            self.track_key = None
            if self.observer:
                self.observer.requestInterruption()

    def observer_finished(self):
        worker = self.observer
        self.observer = None
        interrupted = worker and worker.isInterruptionRequested()
        if worker:
            worker.deleteLater()
        if self.enabled:
            if interrupted:
                QTimer.singleShot(0, lambda: self.set_active(True) if self.enabled else None)
            else:
                # Missing dependencies / OS errors stay visible until user retries.
                self.timer.stop()

    def observer_message(self, message):
        if self.enabled:
            self.track = None
            self.track_key = None
            self.lookup.cancel()
            self.set_message(message)

    def accept_snapshot(self, track):
        if not self.enabled:
            return
        self.track = track
        if not track or not track['title']:
            self.track_key = None
            self.caption = '网易云音乐 · 歌词'
            self.lookup.cancel()
            self.set_message('未检测到网易云播放 · 请开启网易云的系统媒体控制（SMTC）')
            return
        self.caption = f"{track['title']} · {track['artist']}"
        key = (track['title'], track['artist'], track['album'], round(track['duration']))
        if key != self.track_key:
            self.track_key = key
            self.lookup.fetch(track)

    def position(self):
        if not self.track or not self.track.get('position_known', True):
            return 0
        p = self.track['position']
        if self.track['playing']:
            p += (time.monotonic() - self.track['sampled']) * self.track['rate']
        return min(p, self.track['duration']) if self.track['duration'] else p

    def set_message(self, message):
        self.lines, self.stamps, self.plain = [], [], []
        self.translations = {}
        self.lyric_source = ''
        self.message = message
        self.canvas.update()

    def set_lyrics(self, result):
        self.lines, self.plain = result['lines'], result['plain']
        self.translations = result.get('translations', {})
        self.lyric_source = result.get('source', 'LRCLIB')
        self.stamps = [row[0] for row in self.lines]
        self.plain_index = 0
        self.message = result['message']
        detail = ' · 含译文' if self.translations else ' · 歌词源未提供译文'
        status = '同步歌词' if self.lines else '纯文本歌词 · 无时间轴，无法自动换行'
        self.canvas.setToolTip(self.message or f'歌词来源：{self.lyric_source} · {status}' + detail)
        self.canvas.update()

    def retry_lookup(self):
        if self.observer is None and self.enabled:
            self.set_active(True)
        if self.track:
            self.lookup.fetch(self.track, True)

    def shutdown(self):
        self.set_active(False)
        if self.observer and not self.observer.wait(100):
            return False
        return True

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        tint = color('#315c4d', self)
        name = theme_name(self)
        dark = name in ('dark', 'wine') if name else self.palette().color(QPalette.ColorRole.Window).lightness() < 128
        backdrop = QColor(60, 61, 65, 155) if dark else QColor.fromRgbF(
            tint.redF() * .35, tint.greenF() * .35, tint.blueF() * .35, .70)
        painter.setBrush(backdrop)
        painter.setPen(QPen(QColor(255, 255, 255, 48), 1))
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(.5, .5, -.5, -.5), 8, 8)


class LyricsSettingsPopup(FloatingPanel):
    """Four compact settings beside the header music icon."""
    def __init__(self, anchor, owner):
        super().__init__(anchor)
        self.owner = owner
        self.setObjectName('lyricsSettings')
        self.setFixedWidth(278)
        self.show_lyrics = QCheckBox('歌词显示开关', self)
        self.show_lyrics.setChecked(owner.lyrics_button.isChecked())
        self.show_lyrics.clicked.connect(self.toggle_lyrics)
        owner.lyrics_button.toggled.connect(self.show_lyrics.setChecked)
        form = QFormLayout(self)
        form.setContentsMargins(14, 12, 14, 12)
        form.setVerticalSpacing(10)
        form.addRow(self.show_lyrics)
        board = owner.lyrics_board
        board.font_choice.setFixedWidth(148)
        board.font_size.setFixedWidth(148)
        form.addRow('字体切换', board.font_choice)
        form.addRow('字号大小', board.font_size)
        board.font_choice.show()
        board.font_size.show()
        board.font_choice.popup.installEventFilter(self)
        refresh = QPushButton('刷新', self)
        refresh.clicked.connect(self.refresh)
        form.addRow(refresh)

    def toggle_lyrics(self, checked):
        self.owner.lyrics_button.setChecked(checked)
        self.owner.toggle_lyrics(checked)

    def refresh(self):
        if self.owner.lyrics_button.isChecked():
            self.owner.lyrics_board.retry_lookup()
        else:
            self.owner.statusBar().showMessage('先开启歌词显示，再刷新。', 3000)
        self.hide()

    def eventFilter(self, target, event):
        if target is self.owner.lyrics_board.font_choice.popup:
            if event.type() == QEvent.Type.Show:
                self.setProperty('contextMenuOpen', True)
            elif event.type() == QEvent.Type.Hide:
                self.setProperty('contextMenuOpen', False)
        return super().eventFilter(target, event)

    def toggle(self):
        if self.isVisible():
            self.hide()
            return
        dark = bool(self.owner.property('darkTheme'))
        self.setPalette(self.owner.palette())
        self.setStyleSheet(themed_css('QFrame#lyricsSettings { background: #fffefa; border: 1px solid #d6dfd1; border-radius: 9px; } QWidget { color: #273b37; } QComboBox, QSpinBox { padding: 4px 8px; } QPushButton { padding: 5px 10px; }', dark, theme_name(self.owner)))
        self.show_lyrics.setChecked(self.owner.lyrics_button.isChecked())
        self.adjustSize()
        point = self.anchor.mapToGlobal(QPoint(self.anchor.width() - self.width(), self.anchor.height() + 6))
        bounds = self.anchor.screen().availableGeometry()
        self.move(max(bounds.left(), min(point.x(), bounds.right() - self.width() + 1)),
                  max(bounds.top(), min(point.y(), bounds.bottom() - self.height() + 1)))
        self.show()
        self.raise_()
