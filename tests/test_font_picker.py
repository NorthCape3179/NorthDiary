import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import test_ui
from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtTest import QSignalSpy

from northdiary.ui.font_catalog import APPROVED, load_approved_fonts
from northdiary.ui.font_picker import FontPreferences, FontPicker, FontLibraryDialog
from northdiary.ui.editor_toolbar import DefaultTypographyDialog


class FontLibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = str(Path(self.temp.name)/'ui.ini')
        self.settings = QSettings(self.path, QSettings.Format.IniFormat)
        self.preferences = FontPreferences(self.settings)

    def test_only_verified_bundled_fonts_and_pixel_are_available(self):
        manifest = Path(__file__).resolve().parent.parent/'northdiary/assets/font-licenses/installed-fonts-20261106.json'
        reviewed = {font['family'] for font in json.loads(manifest.read_text(encoding='utf-8'))['fonts']}
        bundled = {font.family for font in APPROVED}
        self.assertTrue(bundled.issubset(self.preferences.families))
        self.assertTrue(set(self.preferences.families).issubset(bundled | reviewed))
        self.assertNotIn('Arial', self.preferences.families)
        self.assertNotIn('Microsoft YaHei UI', self.preferences.families)
        self.assertIn('Fusion Pixel 12px Prop zh-Hans', self.preferences.selected_families())
        root = Path(__file__).resolve().parent.parent/'northdiary/assets/lyrics-fonts'
        sources = json.loads((root/'SOURCES.json').read_text(encoding='utf-8'))
        for item in sources:
            self.assertEqual(hashlib.sha256((root/item['name']/'font.ttf').read_bytes()).hexdigest(), item['sha256'])

    def test_search_retains_hidden_choices_and_cancel_discards_them(self):
        dialog = FontLibraryDialog(self.preferences)
        self.addCleanup(dialog.deleteLater)
        before = set(self.preferences.selected)
        first = dialog.font_list.item(0)
        first.setCheckState(Qt.CheckState.Unchecked)
        dialog.search.setText('像素')
        self.assertTrue(first.isHidden())
        visible = [dialog.font_list.item(i) for i in range(dialog.font_list.count()) if not dialog.font_list.item(i).isHidden()]
        self.assertEqual(len(visible), 1)
        self.assertEqual(visible[0].text(), '融合像素')
        dialog.search.setText('lxgw')
        self.assertEqual(sum(not dialog.font_list.item(i).isHidden() for i in range(dialog.font_list.count())), 1)
        dialog.search.clear()
        self.assertEqual(first.checkState(), Qt.CheckState.Unchecked)
        dialog.reject()
        self.assertEqual(self.preferences.selected, before)

    def test_individual_checks_save_persist_and_can_all_be_cleared(self):
        dialog = FontLibraryDialog(self.preferences)
        self.addCleanup(dialog.deleteLater)
        for index in range(dialog.font_list.count()):
            dialog.font_list.item(index).setCheckState(Qt.CheckState.Unchecked)
        dialog.accept()
        reloaded = FontPreferences(QSettings(self.path, QSettings.Format.IniFormat))
        self.assertEqual(reloaded.selected_families(), [])
        picker = FontPicker(QFont(reloaded.default_family), reloaded)
        self.addCleanup(picker.deleteLater)
        self.assertEqual(picker.itemData(0), FontPicker.DEFAULT)
        self.assertEqual(picker.itemData(picker.count()-1), FontPicker.MORE)
        self.assertEqual(picker.count(), 3)  # Default, separator, More.

    def test_default_and_separator_are_fixed_and_unverified_preferences_filtered(self):
        self.settings.setValue('editor/default_family', 'Unverified Font')
        self.preferences.set_selected(['Arial', self.preferences.families[-1]])
        picker = FontPicker(QFont(self.preferences.default_family), self.preferences)
        self.addCleanup(picker.deleteLater)
        self.assertEqual(self.preferences.default_family, 'Microsoft YaHei UI')
        self.assertEqual(self.preferences.new_entry_font().family(), 'Microsoft YaHei UI')
        self.assertEqual(picker.itemText(0), '默认字体')
        self.assertEqual(picker.itemText(picker.count()-1), '更多字体…')
        separator = picker.model().index(picker.count()-2, 0)
        self.assertEqual(separator.data(Qt.ItemDataRole.AccessibleDescriptionRole), 'separator')
        self.assertFalse(separator.flags() & Qt.ItemFlag.ItemIsEnabled)
        self.assertEqual(picker.findData('Arial'), -1)

    def test_original_default_is_independent_of_saved_new_entry_typography(self):
        self.assertEqual(self.preferences.new_entry_font().family(), 'Microsoft YaHei UI')
        self.assertEqual(self.preferences.new_entry_font().pointSizeF(), 12)
        self.settings.setValue('editor/default_family', 'LXGW WenKai')
        self.settings.setValue('editor/default_size', 18)
        self.assertEqual(self.preferences.new_entry_font().family(), 'LXGW WenKai')
        self.assertEqual(self.preferences.new_entry_font().pointSizeF(), 18)
        picker = FontPicker(QFont('LXGW WenKai'), self.preferences)
        self.addCleanup(picker.deleteLater)
        self.assertNotEqual(picker.currentIndex(), 0)
        picker.choose_font(0)
        self.assertEqual(picker.currentFont().family(), 'Microsoft YaHei UI')
        self.assertEqual(self.preferences.new_entry_font().family(), 'LXGW WenKai')
        self.settings.setValue('editor/default_family', 'Microsoft YaHei UI')
        self.assertEqual(self.preferences.new_entry_font().family(), 'Microsoft YaHei UI')


class FontPickerIntegrationTests(unittest.TestCase):
    setUp = test_ui.WindowTests.setUp
    tearDown = test_ui.WindowTests.tearDown

    def test_new_article_uses_original_font_and_survives_save_reading_and_theme(self):
        self.assertEqual(self.window.default_body_font.family(), 'Microsoft YaHei UI')
        self.assertEqual(self.window.default_body_font.pointSizeF(), 12)
        self.window.new_article()
        self.window.confirm_article(self.window.current_id)
        editor = self.window.editor
        editor.insertPlainText('最初的默认字体')
        self.assertEqual(editor.document().defaultFont().family(), 'Microsoft YaHei UI')
        self.assertIn("font-family:'Microsoft YaHei UI'", editor.toHtml())
        self.assertTrue(self.window.save())
        self.window.load_article(self.window.current_id)
        before = editor.toHtml()
        for name in ('dark', 'cream', 'light'):
            self.window.set_theme(name == 'dark', name)
            self.assertEqual(editor.toHtml(), before)
        self.window.preview.setChecked(True)
        self.window.toggle_preview()
        self.assertEqual(editor.toHtml(), before)

    def test_more_font_management_does_not_change_selection_or_document(self):
        self.window.new_article()
        self.window.confirm_article(self.window.current_id)
        editor = self.window.editor
        editor.setPlainText('选区保留，管理字体不改文章')
        cursor = editor.textCursor()
        cursor.setPosition(1)
        cursor.setPosition(5, QTextCursor.MoveMode.KeepAnchor)
        editor.setTextCursor(cursor)
        before = editor.toHtml()
        picker = self.window.format_toolbar.family
        current = picker.currentFont().family()
        spy = QSignalSpy(picker.currentFontChanged)
        with patch('northdiary.ui.font_picker.FontLibraryDialog') as dialog:
            dialog.return_value.exec.side_effect = lambda: self.window.font_preferences.set_selected([])
            picker.choose_index(picker.model().index(picker.count()-1, 0))
        self.assertEqual(spy.count(), 0)
        self.assertEqual(editor.toHtml(), before)
        self.assertEqual(editor.textCursor().selectionStart(), 1)
        self.assertEqual(editor.textCursor().selectionEnd(), 5)
        self.assertEqual(picker.currentFont().family(), current)

    def test_pixel_selection_is_local_and_default_option_uses_safe_default(self):
        self.window.new_article()
        self.window.confirm_article(self.window.current_id)
        editor = self.window.editor
        editor.setPlainText('局部正文')
        cursor = editor.textCursor()
        cursor.setPosition(0)
        cursor.setPosition(2, QTextCursor.MoveMode.KeepAnchor)
        editor.setTextCursor(cursor)
        picker = self.window.format_toolbar.family
        pixel = 'Fusion Pixel 12px Prop zh-Hans'
        picker.choose_index(picker.model().index(picker.findData(pixel), 0))
        self.assertEqual(editor.textCursor().charFormat().fontFamilies(), [pixel])
        other = QTextCursor(editor.document())
        other.setPosition(3)
        other.setPosition(4, QTextCursor.MoveMode.KeepAnchor)
        self.assertNotEqual(other.charFormat().fontFamilies(), [pixel])
        picker.choose_index(picker.model().index(0, 0))
        self.assertEqual(editor.textCursor().charFormat().fontFamilies(), [self.window.font_preferences.default_family])

    def test_default_dialog_and_toolbar_share_choices_without_rewriting_existing_font(self):
        picker = self.window.format_toolbar.family
        dialog = DefaultTypographyDialog(self.window.default_body_font, self.window)
        self.addCleanup(dialog.deleteLater)
        pixel = 'Fusion Pixel 12px Prop zh-Hans'
        self.window.font_preferences.set_selected([pixel])
        self.assertEqual(picker.findData(pixel), 1)
        self.assertEqual(dialog.family.findData(pixel), 1)
        picker.setCurrentFont(QFont('Arial'))
        self.assertEqual(picker.currentFont().family(), 'Arial')
        self.assertEqual(picker.findData('Arial'), -1)
