from PySide6.QtCore import QObject, QEvent, Qt, QVariantAnimation, QPointF, QRectF, QPoint, QSize
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPalette
from PySide6.QtWidgets import QWidget, QPushButton, QAbstractButton, QComboBox, QApplication, QFrame, QListView, QVBoxLayout, QStyledItemDelegate
from northdiary.ui.theme import color, style_local, themed_css, theme_name
import math
from shiboken6 import isValid


class PopupDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):
        return QSize(100, 32)


class FloatingPanel(QFrame):
    """No native popup grab/replay: opener clicks always reach the opener once."""
    def __init__(self, anchor):
        super().__init__(anchor, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.anchor = anchor

    def showEvent(self, event):
        QApplication.instance().installEventFilter(self)
        super().showEvent(event)

    def hideEvent(self, event):
        QApplication.instance().removeEventFilter(self)
        super().hideEvent(event)

    def eventFilter(self, target, event):
        if not isValid(self) or not self.isVisible():
            return False
        if event.type() == QEvent.Type.MouseButtonPress:
            point = event.globalPosition().toPoint()
            in_panel = self.rect().contains(self.mapFromGlobal(point))
            in_anchor = self.anchor.rect().contains(self.anchor.mapFromGlobal(point))
            if not in_panel and not in_anchor:
                self.hide()
        elif event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Escape:
            self.hide()
            return True
        elif event.type() == QEvent.Type.ApplicationDeactivate:
            self.hide()
        return False


class MenuButton(QPushButton):
    def setMenu(self, menu):
        self._menu = menu
        self.panel = FloatingPanel(self)
        self.panel.setObjectName('comboPopup')
        self.panel_layout = QVBoxLayout(self.panel)
        self.panel_layout.setContentsMargins(5, 5, 5, 5)
        for action in menu.actions():
            button = QPushButton(action.text(), self.panel)
            button.clicked.connect(lambda checked=False, chosen=action: self.choose(chosen))
            self.panel_layout.addWidget(button)
        self.clicked.connect(self.toggle_menu)

    def menu(self):
        return self._menu

    def choose(self, action):
        self.panel.hide()
        action.trigger()

    def toggle_menu(self):
        if self.panel.isVisible():
            self.panel.hide()
            return
        dark = self.palette().color(QPalette.ColorRole.Window).lightness() < 128
        self.panel.setPalette(self.palette())
        self.panel.setStyleSheet(themed_css('QFrame#comboPopup { background: #fffefa; border: 1px solid #d6dfd1; border-radius: 7px; } QPushButton { background: transparent; color: #273b37; text-align: left; border: none; padding: 8px 12px; } QPushButton:hover { background: #dbe7d8; }', dark, theme_name(self)))
        self.panel.adjustSize()
        screen = self.screen().availableGeometry()
        point = self.mapToGlobal(QPoint(0, self.height()+3))
        self.panel.move(max(screen.left(), min(point.x(), screen.right()-self.panel.width()+1)),
                        max(screen.top(), min(point.y(), screen.bottom()-self.panel.height()+1)))
        self.panel.show()
        self.panel.raise_()
        self.panel.activateWindow()


class ComboBox(QComboBox):
    """A bounded popup in Qt logical coordinates, independent of native menu sizing."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.popup = FloatingPanel(self)
        self.popup.setObjectName('comboPopup')
        # Closing a Popup on its opener must not replay the same press and reopen it.
        self.popup.setAttribute(Qt.WidgetAttribute.WA_NoMouseReplay)
        self.popup_list = QListView(self.popup)
        self.popup_list.setItemDelegate(PopupDelegate(self.popup_list))
        self.popup_list.setMouseTracking(True)
        self.popup_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.popup_list.setFrameShape(QFrame.Shape.NoFrame)
        self.popup_list.setSpacing(0)
        layout = QVBoxLayout(self.popup)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(0)
        layout.addWidget(self.popup_list)
        self.popup_list.clicked.connect(self.choose_index)
        self.popup_list.activated.connect(self.choose_index)

    def view(self):
        return self.popup_list

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(color('#75827a', self))
        x, y = self.width()-14, self.height()/2
        painter.drawLine(QPointF(x-3, y-1), QPointF(x, y+2))
        painter.drawLine(QPointF(x, y+2), QPointF(x+3, y-1))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.popup.isVisible():
                self.hidePopup()
            else:
                self.showPopup()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_F4):
            self.hidePopup() if self.popup.isVisible() else self.showPopup()
            event.accept()
            return
        super().keyPressEvent(event)

    def choose_index(self, index):
        row = index.row()
        if row < 0:
            return
        self.hidePopup()
        self.setCurrentIndex(row)
        self.activated.emit(row)

    def showPopup(self):
        if not self.count():
            return
        dark = self.palette().color(QPalette.ColorRole.Window).lightness() < 128
        self.popup.setPalette(self.palette())
        self.popup_list.setPalette(self.palette())
        self.popup.setStyleSheet(themed_css('QFrame#comboPopup { background: #fffefa; border: 1px solid #d6dfd1; border-radius: 8px; } QListView { background: #fffefa; color: #273b37; border: none; outline: none; padding: 0; } QListView::item { padding: 0 8px; margin: 0; border: none; border-radius: 4px; } QListView::item:selected, QListView::item:hover { background: #dbe7d8; color: #273b37; }', dark, theme_name(self)))
        self.popup_list.setModel(self.model())
        self.popup_list.setCurrentIndex(self.model().index(self.currentIndex(), self.modelColumn()))
        below = self.mapToGlobal(QPoint(0, self.height()+3))
        screen = self.screen().availableGeometry()
        width = min(self.width(), screen.width())
        height = min(self.count(), 8)*32+10
        height = min(height, screen.height()-8)
        x = max(screen.left(), min(below.x(), screen.right()-width+1))
        y = below.y() if below.y()+height <= screen.bottom() else self.mapToGlobal(QPoint(0, 0)).y()-height-3
        y = max(screen.top(), min(y, screen.bottom()-height+1))
        self.popup.setGeometry(x, y, width, height)
        self.popup.show()
        self.popup.raise_()
        self.popup.activateWindow()
        self.popup_list.setFocus()
        self.popup_list.scrollTo(self.popup_list.currentIndex())

    def hidePopup(self):
        self.popup.hide()


class Ripple(QWidget):
    def __init__(self, button, position):
        super().__init__(button)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet('background: transparent; border: none;')
        self.setGeometry(button.rect())
        self.position = QPointF(position)
        self.progress = 0.0
        button.installEventFilter(self)
        self.animation = QVariantAnimation(self)
        self.animation.setDuration(520)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.valueChanged.connect(self.advance)
        self.animation.finished.connect(self.deleteLater)
        self.show()
        self.raise_()
        self.animation.start()

    def eventFilter(self, target, event):
        if event.type() == QEvent.Type.Resize:
            self.setGeometry(target.rect())
        return False

    def advance(self, value):
        self.progress = value
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(self.rect()), 7, 7)
        painter.setClipPath(clip)
        tint = color('#82ad8b', self)
        tint.setAlpha(round(100*(1-self.progress)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(tint)
        radius = max(math.hypot(x-self.position.x(), y-self.position.y()) for x in (0, self.width()) for y in (0, self.height()))
        painter.drawEllipse(self.position, radius*self.progress, radius*self.progress)


class ButtonFeedback(QObject):
    def __init__(self, parent):
        super().__init__(parent)
        self.root = parent
        QApplication.instance().installEventFilter(self)

    def eventFilter(self, target, event):
        if isValid(self.root) and isinstance(target, QWidget) and self.root.isAncestorOf(target):
            if event.type() == QEvent.Type.Show:
                style_local(target, bool(self.root.property('darkTheme')))
            elif event.type() == QEvent.Type.MouseButtonPress and isinstance(target, QAbstractButton) and target.isEnabled():
                Ripple(target, event.position())
        return False
