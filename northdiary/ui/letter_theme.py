"""Paper, stationery rules and small ink drawings for Letters to Myself."""
from functools import lru_cache

from PySide6.QtCore import Qt, QRectF, QPointF, QPoint, QSize
from PySide6.QtGui import (QColor, QPainter, QPen, QBrush, QImage,
                          QLinearGradient, QPainterPath, QPolygonF, QFont, QFontMetricsF)
from PySide6.QtWidgets import QWidget, QSizePolicy


LETTER_COLORS = {
    '#f6f5f1': '#e9e0cc', '#273b37': '#424a3d', '#e9ede7': '#eee5d1',
    '#fffefa': '#fff5dd', '#e3e5dd': '#d7cbae', '#f0f1eb': '#eee5d1',
    '#244d42': '#4e6549', '#75827a': '#7c725d', '#dce2d8': '#d3c5a6',
    '#7d9b89': '#74866a', '#dbe7d8': '#e0e5d2', '#d6dfd1': '#d3c5a6',
    '#e9eee5': '#e7ddc5', '#526959': '#6e775e', '#f0f3ec': '#f7edd6',
    '#e4e9df': '#e3d6b9', '#cfe0d2': '#d9e0ca', '#d4ddd1': '#cfc1a3',
    '#e0e9dd': '#e4e7d6', '#d3e2d2': '#d7dfc8', '#315c4d': '#556c50',
    '#416f5d': '#687f60', '#a0aaa0': '#a3977e', '#eeeee9': '#eae2d0',
    '#d5e1d0': '#dee4ce', '#234735': '#40583b', '#e0e8db': '#e7e9d7',
    '#708075': '#7c725d', '#eee4d3': '#eddfc1', '#dfe9dc': '#e0e5d2',
    '#708273': '#81745c', '#e9eee7': '#eee3c9', '#f1f3ed': '#faf0d8',
    '#c5d2c5': '#cabb9b', '#a1b3a4': '#a29474', '#788b7c': '#80745a',
    '#d1e1d3': '#c6d3b8', '#82ad8b': '#89a179', '#9a5348': '#9d6152',
    '#527c61': '#74866a', '#7f807a': '#c4b493',
}

LETTER_STYLE = '''
QWidget#sidebar { background: #eee5d1; border: 1px solid #d7cbae; border-radius: 8px; }
QWidget#paper { background: #fff5dd; border: 1px solid #cfc1a3; border-radius: 5px; }
QWidget#properties { background: #eee5d1; border: 1px solid #d7cbae; border-radius: 8px; }
QLabel#brand { color: #4e6549; }
QLabel#section { color: #59644e; }
QLineEdit, QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox { background: #fbf1d9; border-color: #d3c5a6; border-radius: 5px; }
QLineEdit#title { background: transparent; border: none; color: #424a3d; }
QPushButton { background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #fff8e8,stop:1 #f6ebd1); border: 1px solid #cfc1a3; border-radius: 6px; }
QPushButton:hover { background: #e7e9d7; border-color: #74866a; }
QPushButton#primary { background: #556c50; color: #fff9e9; border: 1px solid transparent; }
QPushButton#primary:hover { background: #687f60; border-color: #8da17d; }
QPushButton#primary:pressed { background: #4e6549; color: #fff9e9; }
QPushButton[buttonTone="accent"] { background: #e6e8d5; border-color: #cfc1a3; color: #4e6549; }
QPushButton[buttonTone="accent"]:hover { background: #d9e0ca; border-color: #74866a; }
QPushButton[buttonTone="danger"] { background: transparent; border-color: #cfc1a3; color: #9d6152; }
QPushButton[buttonTone="danger"]:hover { background: #f4e5d0; border-color: #9d6152; }
QListWidget::item:selected, ArticleList::item:selected:hover { background: #dee4ce; color: #40583b; }
QStatusBar { background: #e9e0cc; color: #7c725d; }
'''


@lru_cache(maxsize=1)
def paper_fibers():
    """A tiny deterministic tile, generated once, with no external assets."""
    image = QImage(96, 96, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    p = QPainter(image)
    for i in range(190):
        x, y = (i*47+13) % 96, (i*31+i*i*3) % 96
        p.setPen(QPen(QColor(132, 104, 56, 9+i % 9), .5))
        p.drawLine(QPointF(x, y), QPointF(x+1+i % 3, y+.4))
    p.end()
    return image


def paint_letter_paper(widget, p):
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    bounds = QRectF(widget.rect()).adjusted(2, 2, -2, -2)
    clip = QPainterPath()
    clip.addRoundedRect(bounds, 4, 4)
    p.setClipPath(clip)
    warm = QLinearGradient(0, 0, widget.width(), widget.height())
    warm.setColorAt(0, QColor('#fff6df'))
    warm.setColorAt(1, QColor('#f9edce'))
    p.fillRect(bounds, warm)
    p.fillRect(bounds, QBrush(paper_fibers()))
    # Binding details stay in the page gutter, clear of text and controls.
    p.setPen(QPen(QColor('#d8c7a2'), .8, Qt.PenStyle.DashLine))
    p.drawLine(QPointF(14, 28), QPointF(14, widget.height()-28))
    for y in (30, widget.height()//2, widget.height()-30):
        p.setBrush(QColor('#e9e0cc'))
        p.setPen(QPen(QColor('#cbb994'), .6))
        p.drawEllipse(QPointF(13, y), 2.2, 2.2)
    # A folded paper corner is painted outside the document.
    size = 20
    corner = QPointF(widget.width()-2, widget.height()-2)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor('#ddccaa'))
    p.drawPolygon(QPolygonF([corner-QPointF(size, 0), corner-QPointF(0, size), corner]))
    p.setBrush(QColor('#e9e0cc'))
    p.drawPolygon(QPolygonF([corner-QPointF(size, 0), corner, corner-QPointF(0, size/2)]))
    p.restore()


def stationery_rules(editor):
    """Return viewport rules following visible laid-out baselines, not fixed rows."""
    document = editor.document()
    layout = document.documentLayout()
    scroll = editor.verticalScrollBar().value()
    bottom = editor.viewport().height()
    block = editor.cursorForPosition(QPoint(0, 0)).block()
    if block.previous().isValid():
        block = block.previous()
    rules = []
    last = -1
    while block.isValid():
        rect = layout.blockBoundingRect(block)
        if rect.top()-scroll > bottom:
            break
        text_layout = block.layout()
        for index in range(text_layout.lineCount()):
            line = text_layout.lineAt(index)
            baseline = rect.top()+line.y()+line.ascent()+3-scroll
            if 0 <= baseline <= bottom:
                rules.append(baseline)
            last = max(last, baseline)
        block = block.next()
    if not block.isValid():
        step = max(17, QFontMetricsF(document.defaultFont()).lineSpacing())
        y = max(last, 0)+step
        while y < bottom:
            rules.append(y)
            y += step
    return rules


def paint_stationery_rules(editor, p):
    p.save()
    p.setClipRect(editor.viewport().rect())
    p.setPen(QPen(QColor(157, 137, 92, 48), .7))
    for y in stationery_rules(editor):
        p.drawLine(QPointF(0, y), QPointF(editor.viewport().width(), y))
    p.restore()


def paint_letter_photos(board, p):
    p.fillRect(board.viewport().rect(), QColor('#e5d7b8'))
    p.fillRect(board.viewport().rect(), QBrush(paper_fibers()))
    p.setPen(QPen(QColor('#d1be98'), .7, Qt.PenStyle.DashLine))
    p.drawLine(9, 8, board.viewport().width()-9, 8)


def paint_photo_tape(p, card):
    p.save()
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(185, 158, 96, 115))
    p.drawPolygon(QPolygonF([QPointF(-15, card.top()-2), QPointF(14, card.top()-4),
                            QPointF(16, card.top()+4), QPointF(-13, card.top()+6)]))
    p.restore()


class LetterFooter(QWidget):
    """A dedicated page corner keeps the postmark and doodles off the diary text."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMaximumHeight(76)
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAccessibleName('信笺页角装饰')
        self.setStyleSheet('background: transparent;')

    def sizeHint(self):
        return QSize(0, 76)

    def minimumSizeHint(self):
        return QSize(0, 0)

    def paintEvent(self, event):
        if self.height() < 40:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor('#cbb994'), .7))
        p.drawLine(QPointF(1, 1), QPointF(self.width()-1, 1))
        # A sprig drawn with a few deliberately loose pen strokes.
        p.save()
        p.translate(24, self.height()*.67)
        scale = min(1.0, self.height()/76)
        p.scale(scale, scale)
        p.rotate(-13)
        p.setPen(QPen(QColor('#879070'), 1.1, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.setBrush(Qt.BrushStyle.NoBrush)
        stem = QPainterPath(QPointF(-7, 16))
        stem.cubicTo(2, 0, -1, -19, 7, -29)
        p.drawPath(stem)
        for y, direction in ((4, -1), (-7, 1), (-17, -1)):
            leaf = QPainterPath(QPointF(0, y))
            leaf.cubicTo(direction*18, y-14, direction*15, y+7, 0, y)
            p.drawPath(leaf)
        p.restore()
        if self.width() > 260 and self.height() >= 54:
            font = QFont('Microsoft YaHei UI')
            font.setPixelSize(12)
            p.setFont(font)
            p.setPen(QColor('#8d8063'))
            p.drawText(QRectF(58, 18, self.width()-156, 28), Qt.AlignmentFlag.AlignVCenter,
                       '收好今天，留给未来。')
        # The fixed wording never invents a date for partially dated entries.
        p.save()
        p.translate(self.width()-42, self.height()/2+2)
        p.scale(scale, scale)
        p.rotate(-12)
        p.setPen(QPen(QColor('#a18d66'), .7))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QRectF(-29, -29, 58, 58))
        p.setPen(QPen(QColor('#a18d66'), .6, Qt.PenStyle.DashLine))
        p.drawEllipse(QRectF(-32, -32, 64, 64))
        font = QFont('Georgia')
        font.setPixelSize(9)
        p.setFont(font)
        p.setPen(QColor('#93815e'))
        for text, y in (('NORTH DIARY', -20), ('TO MYSELF', -5), ('LETTERS', 10)):
            p.drawText(QRectF(-35, y, 70, 13), Qt.AlignmentFlag.AlignCenter, text)
        p.restore()
