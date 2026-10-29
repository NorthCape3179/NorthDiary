from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap, QPainter, QPainterPath, QPen, QColor


def pin_icon(pinned=False, dark=False, ratio=1.0, theme=None):
    """Draw in logical coordinates, rasterize at the current screen pixel ratio."""
    pixmap = QPixmap(round(24*ratio), round(24*ratio))
    pixmap.setDevicePixelRatio(ratio)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    color = QColor(('#a6cdb4' if dark else '#315c4d') if pinned else ('#b5bbc1' if dark else '#53645a'))
    if theme in ('cream', 'wine'):
        color = QColor(('#d59db5' if pinned else '#cfb2bf') if theme == 'wine' else ('#87684c' if pinned else '#8d765b'))
    painter.setPen(QPen(color, 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.setBrush(color if pinned else Qt.BrushStyle.NoBrush)
    path = QPainterPath()
    path.moveTo(7, 4)
    path.lineTo(17, 4)
    path.lineTo(17, 6)
    path.lineTo(15, 7)
    path.lineTo(15, 12)
    path.lineTo(18, 15)
    path.lineTo(6, 15)
    path.lineTo(9, 12)
    path.lineTo(9, 7)
    path.lineTo(7, 6)
    path.closeSubpath()
    painter.drawPath(path)
    painter.drawLine(12, 15, 12, 21)
    painter.end()
    return QIcon(pixmap)


def landscape_icon(dark=False, ratio=1.0, theme=None):
    pixmap = QPixmap(round(24*ratio), round(24*ratio))
    pixmap.setDevicePixelRatio(ratio)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    tint = '#cfb2bf' if theme == 'wine' else '#8d765b' if theme == 'cream' else '#b5bbc1' if dark else '#53645a'
    painter.setPen(QPen(QColor(tint), 1.5))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRoundedRect(3, 4, 18, 16, 2, 2)
    painter.drawEllipse(14, 7, 3, 3)
    path = QPainterPath()
    path.moveTo(4, 18); path.lineTo(9, 11); path.lineTo(13, 16); path.lineTo(16, 13); path.lineTo(20, 18)
    painter.drawPath(path)
    painter.end()
    return QIcon(pixmap)
