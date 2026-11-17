from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap, QPainter, QPainterPath, QPen, QColor


def ui_icon(kind, widget):
    """Compact line icons, using the same theme tint and logical grid."""
    from northdiary.ui.theme import color
    ratio = widget.devicePixelRatioF()
    pixmap = QPixmap(round(24 * ratio), round(24 * ratio))
    pixmap.setDevicePixelRatio(ratio)
    pixmap.fill(Qt.GlobalColor.transparent)
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(color('#526959', widget), 1.6, Qt.PenStyle.SolidLine,
                  Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.setBrush(Qt.BrushStyle.NoBrush)
    if kind == 'image':
        p.drawRoundedRect(3, 4, 18, 16, 2, 2)
        p.drawEllipse(14, 7, 3, 3)
        p.drawLine(4, 18, 9, 12); p.drawLine(9, 12, 14, 17); p.drawLine(14, 17, 18, 13)
    elif kind in ('align', 'indent'):
        for y, end in ((5, 20), (10, 16), (15, 20), (20, 16)):
            p.drawLine(9 if kind == 'indent' and y in (10, 15) else 4, y, end, y)
        if kind == 'indent':
            p.drawLine(3, 10, 6, 12); p.drawLine(6, 12, 3, 14)
    elif kind == 'save':
        p.drawRoundedRect(4, 3, 16, 18, 2, 2)
        p.drawRect(8, 3, 8, 6); p.drawRect(8, 14, 8, 7)
    elif kind == 'random':
        path = QPainterPath(); path.moveTo(3, 6); path.cubicTo(11, 6, 13, 18, 21, 18)
        p.drawPath(path)
        path = QPainterPath(); path.moveTo(3, 18); path.cubicTo(11, 18, 13, 6, 21, 6)
        p.drawPath(path)
        for y in (6, 18):
            p.drawLine(18, y-3, 21, y); p.drawLine(21, y, 18, y+3)
    elif kind == 'theme':
        p.drawEllipse(4, 4, 16, 16)
        p.setBrush(color('#526959', widget)); p.drawPie(4, 4, 16, 16, 90*16, 180*16)
    elif kind == 'settings':
        for x, y in ((6, 8), (12, 16), (18, 10)):
            p.drawLine(x, 3, x, y-3); p.drawLine(x, y+3, x, 21)
            p.drawRoundedRect(x-2, y-3, 4, 6, 1, 1)
    elif kind == 'lyrics':
        for y in (5, 10, 15): p.drawLine(3, y, 12, y)
        p.drawLine(18, 6, 18, 18); p.drawLine(18, 6, 22, 5)
        p.drawEllipse(14, 17, 4, 3)
    p.end()
    return QIcon(pixmap)


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


def date_sort_icon(ascending=False, dark=False, ratio=1.0, theme=None):
    """Triangle direction above a rectangular base, in logical pixels."""
    pixmap = QPixmap(round(24*ratio), round(24*ratio))
    pixmap.setDevicePixelRatio(ratio)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    tint = QColor('#cfb2bf' if theme == 'wine' else '#8d765b' if theme == 'cream' else '#b5bbc1' if dark else '#53645a')
    painter.setPen(QPen(tint, 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.setBrush(tint)
    triangle = QPainterPath()
    if ascending:
        triangle.moveTo(7, 10); triangle.lineTo(12, 4); triangle.lineTo(17, 10)
    else:
        triangle.moveTo(7, 4); triangle.lineTo(17, 4); triangle.lineTo(12, 10)
    triangle.closeSubpath(); painter.drawPath(triangle)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRect(5, 15, 14, 5)
    painter.end()
    return QIcon(pixmap)
