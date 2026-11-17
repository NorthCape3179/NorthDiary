"""Shared desktop chrome; Windows keeps ownership of moving, snapping and sizing."""
import sys
import weakref

from PySide6.QtCore import QObject, QEvent, Qt, QPoint, QTimer, QAbstractNativeEventFilter
from PySide6.QtGui import QPainter, QPen, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QHBoxLayout, QToolButton, QMainWindow,
    QDialog, QFileDialog, QMenu,
)
from shiboken6 import isValid

from northdiary.ui.theme import color, apply_theme, theme_name


class CaptionButton(QToolButton):
    def __init__(self, action, window, parent):
        super().__init__(parent)
        self.action, self.host = action, window
        self.setObjectName('captionClose' if action == 'close' else 'captionButton')
        self.setFixedSize(44, 36)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        title = {'minimize': '最小化', 'maximize': '最大化 / 还原', 'close': '关闭'}[action]
        self.setAccessibleName(title)
        self.setToolTip(title)
        self.clicked.connect(self.activate)

    def activate(self):
        if self.action == 'close':
            self.host.close()  # Preserve QDialog rejection and MainWindow's save guard.
        elif self.action == 'minimize':
            self.host.showMinimized()
        else:
            self.host.showNormal() if self.host.isMaximized() else self.host.showMaximized()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        tint = color('#273b37', self)
        if self.action == 'close' and self.underMouse():
            from PySide6.QtGui import QColor
            tint = QColor('white')
        painter.setPen(QPen(tint, 1.2))
        x, y = self.width() // 2, self.height() // 2
        if self.action == 'close':
            painter.drawLine(x-5, y-5, x+5, y+5)
            painter.drawLine(x+5, y-5, x-5, y+5)
        elif self.action == 'minimize':
            painter.drawLine(x-5, y+3, x+5, y+3)
        elif self.host.isMaximized():
            painter.drawRect(x-3, y-5, 8, 8)
            painter.fillRect(x-5, y-3, 8, 8, color('#f6f5f1', self))
            painter.drawRect(x-5, y-3, 8, 8)
        else:
            painter.drawRect(x-5, y-5, 10, 10)


class TitleBar(QWidget):
    def __init__(self, window, dialog=False):
        super().__init__(window)
        self.host = window
        self.setObjectName('windowTitleBar')
        self.setFixedHeight(38 if not dialog else 44)
        row = QHBoxLayout(self)
        row.setContentsMargins(16, 0, 2, 0)
        row.setSpacing(0)
        self.title = QLabel(window.windowTitle(), self)
        self.title.setObjectName('windowCaption')
        self.title.setTextFormat(Qt.TextFormat.PlainText)
        self.title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.header = getattr(window, 'main_header', None) if not dialog else None
        if self.header is not None:
            # Move the existing brand and tools into the draggable caption row.
            # The OS window title remains available to the taskbar and Alt+Tab.
            self.title.hide()
            row.addWidget(self.header, 1)
            self.setFixedHeight(60)
            # Use the workspace's inset on both sides, so the brand and caption
            # buttons line up with the panel edges instead of the OS frame.
            workspace = window.centralWidget()
            margins = workspace.layout().contentsMargins()
            row.setContentsMargins(margins.left(), 8, margins.right(), 8)
            row.setSpacing(10)
            brand = self.header.findChild(QLabel, 'brand')
            if brand is not None:
                brand.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)
        else:
            row.addWidget(self.title, 1)
        self.minimize = CaptionButton('minimize', window, self)
        self.maximize = CaptionButton('maximize', window, self)
        self.close_button = CaptionButton('close', window, self)
        self.minimize.setVisible(not dialog)
        self.maximize.setVisible(not dialog or window.minimumSize() != window.maximumSize())
        row.addWidget(self.minimize)
        row.addWidget(self.maximize)
        row.addWidget(self.close_button)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.header is not None:
            margins = self.layout().contentsMargins()
            painter = QPainter(self)
            painter.setPen(QPen(color('#dce2d8', self), 1))
            painter.drawLine(margins.left(), self.height()-1,
                             self.width()-margins.right()-1, self.height()-1)
            painter.end()

    def draggable(self, position):
        child = self.childAt(position)
        return (child is None or child is self.title or child is self.header
                or child.objectName() == 'brand')

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.host.windowHandle():
            self.host.windowHandle().startSystemMove()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.maximize.isVisible():
            self.maximize.activate()
            event.accept()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.addAction('还原', self.host.showNormal).setEnabled(self.host.isMaximized())
        menu.addAction('最小化', self.host.showMinimized)
        menu.addAction('最大化', self.host.showMaximized).setEnabled(self.maximize.isVisible() and not self.host.isMaximized())
        menu.addSeparator()
        menu.addAction('关闭', self.host.close)
        menu.exec(event.globalPos())


class WindowChrome(QObject):
    def __init__(self, window, manager, dialog=False):
        super().__init__(window)
        self.window, self.manager = window, manager
        self.dialog = dialog
        self.content_margins = None
        window.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        window.setProperty('customChrome', True)
        self.bar = TitleBar(window, dialog)
        if isinstance(window, QMainWindow):
            window.setMenuWidget(self.bar)
        else:
            layout = window.layout()
            if layout:
                margins = layout.contentsMargins()
                self.content_margins = (max(18, margins.left()), margins.top()+48,
                                        max(18, margins.right()), max(16, margins.bottom()))
                layout.setContentsMargins(*self.content_margins)
                # Preserve the dialog's intended content area.
                window.resize(window.width(), window.height()+48)
        window.installEventFilter(self)
        self.system_menu_shortcut = QShortcut(QKeySequence('Alt+Space'), window)
        self.system_menu_shortcut.activated.connect(self.show_system_menu)
        self.refresh()

    def show_system_menu(self):
        if sys.platform == 'win32':
            import ctypes
            user = ctypes.windll.user32
            user.GetSystemMenu.restype = ctypes.c_void_p
            menu = user.GetSystemMenu(ctypes.c_void_p(int(self.window.winId())), False)
            ratio = self.window.devicePixelRatioF()
            # Native screen coordinates are obtained from the HWND (mixed DPI safe).
            from ctypes import wintypes
            point = wintypes.POINT(0, int(self.bar.height()*ratio))
            user.ClientToScreen(ctypes.c_void_p(int(self.window.winId())), ctypes.byref(point))
            command = user.TrackPopupMenu(ctypes.c_void_p(menu), 0x100 | 0x2, point.x, point.y,
                                         0, ctypes.c_void_p(int(self.window.winId())), None)
            if command:
                user.PostMessageW(ctypes.c_void_p(int(self.window.winId())), 0x112, command, 0)

    def refresh(self):
        if not isValid(self.window):
            return
        window = self.window
        self.bar.title.setText(window.windowTitle())
        self.bar.setVisible(not window.isFullScreen())
        if self.dialog:
            layout = window.layout()
            if layout:
                if self.content_margins is None:
                    margins = layout.contentsMargins()
                    self.content_margins = (max(18, margins.left()), margins.top()+48,
                                            max(18, margins.right()), max(16, margins.bottom()))
                if layout.contentsMargins().top() < self.content_margins[1]:
                    layout.setContentsMargins(*self.content_margins)
            self.bar.setGeometry(1, 1, max(0, window.width()-2), self.bar.height())
            self.bar.raise_()
        self.bar.maximize.update()
        if window.isVisible():
            self.manager.register(self)

    def eventFilter(self, target, event):
        if event.type() == QEvent.Type.Show:
            # QMessageBox/QInputDialog rebuild their own layout during showEvent.
            QTimer.singleShot(0, self.refresh)
        if event.type() in (QEvent.Type.Resize, QEvent.Type.WindowStateChange,
                            QEvent.Type.WindowTitleChange, QEvent.Type.Show, QEvent.Type.PaletteChange):
            self.refresh()
        return False


class NativeFrameFilter(QAbstractNativeEventFilter):
    def __init__(self, manager):
        super().__init__()
        self.manager = manager

    def nativeEventFilter(self, event_type, message):
        if sys.platform != 'win32':
            return False, 0
        import ctypes
        from ctypes import wintypes
        msg = wintypes.MSG.from_address(int(message))
        reference = self.manager.handles.get(int(msg.hWnd or 0))
        chrome = reference() if reference else None
        if chrome is None or not isValid(chrome) or not isValid(chrome.window):
            return False, 0
        window, user = chrome.window, ctypes.windll.user32
        if msg.message == 0x83:  # WM_NCCALCSIZE, with either RECT or NCCALCSIZE_PARAMS
            if (window.isMaximized() or user.IsZoomed(msg.hWnd)) and not window.isFullScreen():
                class MonitorInfo(ctypes.Structure):
                    _fields_ = [('size', wintypes.DWORD), ('monitor', wintypes.RECT),
                                ('work', wintypes.RECT), ('flags', wintypes.DWORD)]
                info = MonitorInfo()
                info.size = ctypes.sizeof(info)
                user.MonitorFromWindow.restype = ctypes.c_void_p
                monitor = user.MonitorFromWindow(msg.hWnd, 2)
                if user.GetMonitorInfoW(ctypes.c_void_p(monitor), ctypes.byref(info)):
                    rect = wintypes.RECT.from_address(msg.lParam)
                    rect.left, rect.top = info.work.left, info.work.top
                    rect.right, rect.bottom = info.work.right, info.work.bottom
            return True, 0
        if msg.message != 0x84 or window.isFullScreen():  # WM_NCHITTEST
            return False, 0
        rect = wintypes.RECT()
        user.GetWindowRect(msg.hWnd, ctypes.byref(rect))
        x = ctypes.c_short(msg.lParam & 0xffff).value
        y = ctypes.c_short((msg.lParam >> 16) & 0xffff).value
        border = max(5, round(6*window.devicePixelRatioF()))
        horizontal = window.minimumWidth() < window.maximumWidth()
        vertical = window.minimumHeight() < window.maximumHeight()
        if not window.isMaximized():
            left, right = horizontal and x < rect.left+border, horizontal and x >= rect.right-border
            top, bottom = vertical and y < rect.top+border, vertical and y >= rect.bottom-border
            hit = (13 if left else 14 if right else 12) if top else ((16 if left else 17 if right else 15) if bottom else (10 if left else 11 if right else 0))
            if hit:
                return True, hit
        # Convert native physical pixels into Qt logical client coordinates.
        point = wintypes.POINT(x, y)
        user.ScreenToClient(msg.hWnd, ctypes.byref(point))
        logical = QPoint(round(point.x/window.devicePixelRatioF()), round(point.y/window.devicePixelRatioF()))
        local = chrome.bar.mapFrom(window, logical)
        if chrome.bar.isVisible() and chrome.bar.rect().contains(local) and chrome.bar.draggable(local):
            return True, 2  # HTCAPTION: native dragging, double-click, snapping, system menu.
        return False, 0


class ChromeManager(QObject):
    def __init__(self, app):
        super().__init__(app)
        self.handles = {}
        self.native_filter = NativeFrameFilter(self)
        app.installEventFilter(self)
        app.installNativeEventFilter(self.native_filter)

    def register(self, chrome):
        window = chrome.window
        handle = int(window.winId())
        if handle not in self.handles:
            self.handles[handle] = weakref.ref(chrome)
            chrome.destroyed.connect(lambda *_: self.handles.pop(handle, None))
            if sys.platform == 'win32':
                import ctypes
                user = ctypes.windll.user32
                hwnd = ctypes.c_void_p(handle)
                get_style = user.GetWindowLongPtrW if ctypes.sizeof(ctypes.c_void_p) == 8 else user.GetWindowLongW
                set_style = user.SetWindowLongPtrW if ctypes.sizeof(ctypes.c_void_p) == 8 else user.SetWindowLongW
                get_style.restype = ctypes.c_ssize_t
                set_style.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_ssize_t]
                style = get_style(hwnd, -16) | 0xC00000 | 0x80000  # CAPTION, SYSMENU
                if window.minimumSize() != window.maximumSize():
                    style |= 0x40000 | 0x10000  # THICKFRAME, MAXIMIZEBOX
                if not chrome.dialog:
                    style |= 0x20000  # MINIMIZEBOX
                set_style(hwnd, -16, style)
                user.SetWindowPos(hwnd, None, 0, 0, 0, 0, 0x27)  # FRAMECHANGED, NOMOVE, NOSIZE, NOZORDER
                # NCCALCSIZE does not remove a frame extended by DWM. Extending
                # one pixel here leaves a system-colored strip over our title bar.
                margins = (ctypes.c_int*4)(0, 0, 0, 0)
                ctypes.windll.dwmapi.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(margins))
        if sys.platform == 'win32':
            self.update_frame_appearance(chrome)

    def update_frame_appearance(self, chrome):
        import ctypes
        window = chrome.window
        hwnd = ctypes.c_void_p(int(window.winId()))
        state = (hwnd.value, window.isMaximized() or window.isFullScreen(), theme_name(window))
        if getattr(chrome, '_native_frame_state', None) == state:
            return
        chrome._native_frame_state = state
        # Qt's frameless maximize can fill the work area without WS_MAXIMIZE;
        # explicitly square the corners instead of relying on DWM's detection.
        corners = ctypes.c_int(1 if state[1] else 2)
        border = ctypes.c_uint(0xfffffffe)  # DWMWA_COLOR_NONE
        dark = ctypes.c_int(theme_name(window) in ('dark', 'wine', 'radio'))
        dwm = ctypes.windll.dwmapi
        dwm.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(corners), 4)
        dwm.DwmSetWindowAttribute(hwnd, 34, ctypes.byref(border), 4)
        dwm.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(dark), 4)

    def eventFilter(self, target, event):
        if event.type() == QEvent.Type.Polish and isinstance(target, QDialog) and not isinstance(target, QFileDialog):
            if target.isWindow() and not hasattr(target, '_northdiary_chrome'):
                parent = target.parentWidget()
                if parent:
                    name = theme_name(parent)
                    apply_theme(target, bool(parent.property('darkTheme')) or name in ('dark', 'wine', 'radio'), name)
                else:
                    apply_theme(target, False)
                target._northdiary_chrome = WindowChrome(target, self, dialog=True)
        return False


def install_window_chrome():
    app = QApplication.instance()
    if not hasattr(app, '_northdiary_chrome_manager'):
        app._northdiary_chrome_manager = ChromeManager(app)
    return app._northdiary_chrome_manager


def style_main_window(window):
    window._northdiary_chrome = WindowChrome(window, install_window_chrome())
