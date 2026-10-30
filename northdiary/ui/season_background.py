from datetime import datetime, timezone, timedelta
from pathlib import Path
from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QImage, QPainter, QLinearGradient, QColor, QPalette
from PySide6.QtWidgets import QWidget


def background_name(moment, dark=False):
    season = ('冬天' if moment.month in (12, 1, 2) else '春天' if moment.month <= 5
              else '夏天' if moment.month <= 8 else '秋天')
    return season + ('黑夜' if dark else '白天') + '.png'


class SeasonPaper(QWidget):
    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.enabled = True
        self.name = ''
        self.month_unknown = False
        self.article_date = None
        self.source = QImage()
        self.cached = QImage()
        self.cache_key = None
        self.timer = QTimer(self)
        self.timer.setInterval(60000)
        self.timer.timeout.connect(self.refresh_background)
        self.timer.start()
        self.refresh_background()

    def refresh_background(self, force=False):
        moment = self.article_date or datetime.now(timezone(timedelta(hours=8)))
        dark = self.palette().color(QPalette.ColorRole.Window).lightness() < 128
        name = 'unknown-month.png' if self.month_unknown else background_name(moment, dark=dark)
        if name != self.name:
            self.name = name
            path = Path(__file__).resolve().parents[1] / 'resources' / 'backgrounds' / name
            self.source = QImage(str(path))
            force = True
        if force:
            self.cache_key = None
            self.update()

    def set_article_date(self, date):
        self.article_date = date.toPython() if date.isValid() else None
        self.refresh_background()

    def set_enabled(self, enabled):
        self.enabled = bool(enabled)
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.enabled or self.source.isNull():
            return
        dark = self.palette().color(QPalette.ColorRole.Window).lightness() < 128
        ratio = self.devicePixelRatioF()
        width, height = max(1, self.width()-2), max(1, round(self.height()*.52)-1)
        key = (width, height, ratio, self.name, dark)
        if self.cache_key != key:
            pw, ph = max(1, round(width*ratio)), max(1, round(height*ratio))
            image = self.source.scaled(pw, ph, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            layer = QImage(pw, ph, QImage.Format.Format_ARGB32_Premultiplied)
            layer.fill(Qt.GlobalColor.transparent)
            painter = QPainter(layer)
            painter.drawImage((pw-image.width())//2, (ph-image.height())//2, image)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
            fade = QLinearGradient(0, 0, 0, ph)
            maximum = 100 if dark else 105
            fade.setColorAt(0, QColor(255, 255, 255, 0))
            fade.setColorAt(.3, QColor(255, 255, 255, round(maximum*.22)))
            fade.setColorAt(1, QColor(255, 255, 255, maximum))
            painter.fillRect(layer.rect(), fade)
            painter.end()
            layer.setDevicePixelRatio(ratio)
            self.cached = layer
            self.cache_key = key
        painter = QPainter(self)
        painter.setClipRect(QRectF(1, self.height()-height-1, width, height))
        painter.drawImage(1, self.height()-height-1, self.cached)

