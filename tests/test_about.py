import unittest
from unittest.mock import patch
import test_ui
from PySide6.QtCore import Qt, QTimer, QEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from northdiary import __version__
from northdiary.ui.about_dialog import AboutDialog, about_html
from northdiary.ui.theme import theme_mapping


class AboutTests(unittest.TestCase):
    setUp = test_ui.WindowTests.setUp
    tearDown = test_ui.WindowTests.tearDown

    def test_version_sections_author_and_accurate_capabilities(self):
        self.assertEqual(__version__, '1.7.0')
        dialog = AboutDialog(self.window)
        try:
            text = dialog.browser.toPlainText()
            self.assertIn('v1.7.0', self.window.windowTitle())
            self.assertIn('v1.7.0', dialog.windowTitle())
            for value in ['关于 NorthDiary','设计理念','当前版本','更新日志','未来计划','项目信息',
                          'PySide6 / Qt','NorthCape','539241974','ChatGPT','（其实是主力）',
                          '自助备份恢复','暂不支持自定义头像照片','不是自动双向同步']:
                self.assertIn(value,text)
            self.assertNotIn('PyQt',text)
            for version in ['v1.0','v1.1','v1.2','v1.3','v1.4','v1.5']:
                self.assertIn(version,text)
            html = about_html({})
            self.assertIn('font-size:11px',html)
            self.assertIn('<hr ',html)
            self.assertTrue(dialog.browser.openExternalLinks())
        finally: dialog.close()

    def test_info_button_is_rightmost_and_remains_visible_when_collapsed(self):
        w=self.window
        self.assertGreater(w.about_button.x(),w.header_tools.geometry().right())
        w.header_tools.set_collapsed(True,animate=False)
        test_ui.APP.processEvents()
        self.assertTrue(w.about_button.isVisible())
        with patch('northdiary.ui.main_window.AboutDialog') as dialog:
            QTest.mouseClick(w.about_button,Qt.MouseButton.LeftButton)
            dialog.assert_called_once_with(w)
            dialog.return_value.exec.assert_called_once()

    def test_real_about_closes_without_altering_article_or_leaving_hidden_dialog(self):
        w=self.window;w.new_article();w.editor.setPlainText('详情弹窗不替换正文');w.timer.stop()
        before=w.editor.toPlainText();key=w.current_id
        QTimer.singleShot(40,lambda: QApplication.activeModalWidget().accept())
        w.open_about()
        QApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
        self.assertEqual(w.findChildren(AboutDialog),[])
        self.assertEqual(w.current_id,key)
        self.assertEqual(w.editor.toPlainText(),before)
        self.assertTrue(w.dirty)

    def test_about_follows_all_theme_modes(self):
        from PySide6.QtGui import QPalette
        for name in ['light','cream','burgundy','citrus','blue','gray','dark','wine']:
            dark=name in ('dark','wine');self.window.set_theme(dark,name)
            dialog=AboutDialog(self.window)
            try:
                self.assertEqual(dialog.property('colorTheme'),name)
                self.assertEqual(dialog.palette().color(QPalette.ColorRole.Window).lightness()<128,dark)
                self.assertIn(theme_mapping(dark,name).get('#273b37','#273b37'),about_html(theme_mapping(dark,name)))
            finally:dialog.close()
