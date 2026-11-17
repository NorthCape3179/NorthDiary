import unittest
from unittest.mock import patch

import test_ui
from PySide6.QtCore import Qt


class PolishTests(unittest.TestCase):
    setUp = test_ui.WindowTests.setUp
    tearDown = test_ui.WindowTests.tearDown

    def entry(self):
        self.window.new_article()
        self.window.confirm_article(self.window.current_id)
        return self.window.editor

    def test_save_status_failure_retains_content_and_retry_recovers(self):
        editor = self.entry()
        editor.setPlainText('保留我的内容')
        self.assertEqual(self.window.save_state.text(), '待保存')
        with patch.object(self.window.repository, 'save', side_effect=OSError('test')):
            self.assertFalse(self.window.save())
        self.assertEqual(self.window.save_state.text(), '保存失败')
        self.assertTrue(self.window.dirty)
        self.assertEqual(editor.toPlainText(), '保留我的内容')
        self.assertTrue(self.window.save())
        self.assertEqual(self.window.save_state.text(), '已保存')

    def test_theme_menu_preserves_document_and_only_tints_image_references(self):
        editor = self.entry()
        editor.insert_image_link('sample', '图片')
        before = editor.toHtml()
        self.window.theme_actions['dark'].trigger()
        self.assertEqual(self.window.property('colorTheme'), 'dark')
        self.assertEqual(editor.toHtml(), before)
        selections = editor.extraSelections()
        self.assertGreaterEqual(selections[0].format.foreground().color().lightness(), 128)
        self.window.theme_actions['cream'].trigger()
        self.assertEqual(editor.toHtml(), before)
        self.assertEqual(self.window.ui_settings.value('theme_name'), 'cream')

    def test_tools_share_row_hide_in_reading_and_photo_heading_stays_compact(self):
        self.entry()
        bar = self.window.format_toolbar
        self.assertIs(self.window.image_button.parentWidget(), bar)
        self.assertIs(self.window.indent_button.parentWidget(), bar)
        self.assertLessEqual(self.window.photo_title.height(), 24)
        self.assertEqual(self.window.photo_layout.spacing(), 2)
        for button in (self.window.theme_button, self.window.settings_button,
                       self.window.image_button, bar.alignment):
            self.assertFalse(button.icon().isNull())
            self.assertTrue(button.toolTip())
            self.assertEqual(button.text(), '')
        self.window.preview.setChecked(True)
        self.window.toggle_preview()
        self.assertTrue(bar.isHidden())
        self.window.preview.setChecked(False)
        self.window.toggle_preview()
        self.assertFalse(bar.isHidden())

    def test_unknown_date_display_does_not_modify_stored_date_or_id(self):
        self.entry()
        self.window.title.setText('长标题' * 30)
        self.assertTrue(self.window.save())
        self.window.repository.save(self.window.current_id, self.window.title.text(), '未知-未知-未知', '', '', [], [])
        article = self.window.repository.get(self.window.current_id)
        self.assertIn('日期未设置', self.window.item_text(article))
        self.assertEqual(article.diary_date, '未知-未知-未知')
        self.window.refresh_list()
        self.assertEqual(self.window.article_list.horizontalScrollBarPolicy(), Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.assertIn(article.title, self.window.article_list.currentItem().toolTip())
