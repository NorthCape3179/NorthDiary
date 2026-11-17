import unittest

import test_ui
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QMessageBox, QInputDialog


class WindowChromeTests(unittest.TestCase):
    setUp = test_ui.WindowTests.setUp
    tearDown = test_ui.WindowTests.tearDown

    def test_main_caption_maximize_restore_and_fullscreen(self):
        window = self.window
        self.assertTrue(window.windowFlags() & Qt.WindowType.FramelessWindowHint)
        chrome = window._northdiary_chrome
        chrome.bar.maximize.click()
        test_ui.APP.processEvents()
        self.assertTrue(window.isMaximized())
        chrome.bar.maximize.click()
        test_ui.APP.processEvents()
        self.assertFalse(window.isMaximized())
        chrome.bar.minimize.click()
        test_ui.APP.processEvents()
        self.assertTrue(window.isMinimized())
        window.showNormal()
        window.toggle_fullscreen()
        test_ui.APP.processEvents()
        self.assertFalse(chrome.bar.isVisible())
        window.leave_fullscreen()
        test_ui.APP.processEvents()
        self.assertTrue(chrome.bar.isVisible())

    def test_dialogs_and_builtin_prompts_share_chrome_and_close_rejects(self):
        for dialog in (QDialog(self.window), QMessageBox(self.window), QInputDialog(self.window)):
            if dialog.layout() is None:
                QVBoxLayout(dialog).addWidget(QLabel('content'))
            dialog.setWindowTitle('测试弹窗')
            dialog.show()
            test_ui.APP.processEvents()
            chrome = dialog._northdiary_chrome
            self.assertTrue(dialog.windowFlags() & Qt.WindowType.FramelessWindowHint)
            self.assertGreaterEqual(dialog.layout().contentsMargins().top(), 48)
            self.assertEqual(chrome.bar.title.text(), '测试弹窗')
            self.assertGreater(chrome.bar.close_button.width(), 0)
            chrome.bar.close_button.click()
            test_ui.APP.processEvents()
            self.assertFalse(dialog.isVisible())
            dialog.deleteLater()

    def test_dialog_margins_do_not_grow_on_repeated_show_and_theme_is_inherited(self):
        self.window.set_theme(True, 'wine')
        dialog = QDialog(self.window)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel('content'))
        dialog.show()
        test_ui.APP.processEvents()
        first = layout.contentsMargins().top()
        self.assertEqual(dialog.property('colorTheme'), 'wine')
        dialog.hide()
        dialog.show()
        test_ui.APP.processEvents()
        self.assertEqual(layout.contentsMargins().top(), first)
        dialog.close()

    def test_transparent_caption_uses_explicit_light_theme(self):
        from northdiary.ui.theme import color
        self.window.set_theme(False, 'light')
        button = self.window._northdiary_chrome.bar.close_button
        self.assertEqual(color('#273b37', button).name(), '#273b37')
        self.window.set_theme(True, 'dark')
        self.assertEqual(color('#273b37', button).name(), '#e3e4e6')

    def test_client_area_calculation_removes_frame_for_both_message_forms(self):
        import sys
        if sys.platform != 'win32':
            self.skipTest('Windows non-client messages')
        import ctypes
        from ctypes import wintypes
        chrome = self.window._northdiary_chrome
        chrome.manager.register(chrome)
        rect = wintypes.RECT(10, 20, 700, 500)
        msg = wintypes.MSG()
        msg.hWnd = int(self.window.winId())
        msg.message = 0x83
        msg.lParam = ctypes.addressof(rect)
        for value in (0, 1):
            msg.wParam = value
            self.assertEqual(chrome.manager.native_filter.nativeEventFilter(None, ctypes.addressof(msg)), (True, 0))
            self.assertEqual((rect.left, rect.top, rect.right, rect.bottom), (10, 20, 700, 500))
