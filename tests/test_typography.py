import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
from unittest.mock import patch

import test_ui
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QTextCursor, QTextDocument
from PySide6.QtTest import QTest
from lxml import html

from northdiary.models import ExportSelection
from northdiary.services.attachments import AttachmentService
from northdiary.services.epub import EpubExporter, clean_body
from northdiary.services.importing import EpubImporter
from northdiary.storage.database import Database
from northdiary.storage.repository import ArticleRepository
from northdiary.ui.editor import ArticleEditor
from northdiary.ui.editor_toolbar import DefaultTypographyDialog


def char_format(editor, start, end):
    cursor = QTextCursor(editor.document())
    cursor.setPosition(start)
    cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
    return cursor.charFormat()


class TypographyTests(unittest.TestCase):
    setUp = test_ui.WindowTests.setUp
    tearDown = test_ui.WindowTests.tearDown

    def new_entry(self):
        self.window.new_article()
        self.window.confirm_article(self.window.current_id)
        return self.window.editor

    def test_selection_format_save_reopen_reading_and_undo(self):
        editor = self.new_entry()
        editor.setPlainText('第一段文字\n第二段文字')
        cursor = editor.textCursor()
        cursor.setPosition(1)
        cursor.setPosition(4, QTextCursor.MoveMode.KeepAnchor)
        editor.setTextCursor(cursor)
        bar = self.window.format_toolbar
        bar.change_family(QFont('SimSun'))
        bar.change_size(22.5)
        bar.bold.click()
        bar.italic.click()
        bar.underline.click()
        fmt = char_format(editor, 1, 2)
        self.assertEqual(fmt.fontFamilies(), ['SimSun'])
        self.assertEqual(fmt.fontPointSize(), 22.5)
        self.assertEqual(fmt.fontWeight(), QFont.Weight.Bold)
        self.assertTrue(fmt.fontItalic() and fmt.fontUnderline())
        self.assertFalse(char_format(editor, 0, 1).fontItalic())
        editor.undo()
        self.assertFalse(char_format(editor, 1, 2).fontUnderline())
        editor.redo()
        bar.set_alignment(Qt.AlignmentFlag.AlignRight)
        key = self.window.current_id
        self.assertTrue(self.window.save())
        self.window.load_article(key)
        for reading in (True, False):
            self.window.preview.setChecked(reading)
            self.window.toggle_preview()
            fmt = char_format(editor, 1, 2)
            self.assertEqual(fmt.fontPointSize(), 22.5)
            self.assertTrue(fmt.fontItalic() and fmt.fontUnderline())
            self.assertTrue(editor.document().begin().blockFormat().alignment() & Qt.AlignmentFlag.AlignRight)
            self.assertEqual(bar.family.isEnabled(), not reading)

    def test_no_selection_changes_only_future_input_and_shortcuts(self):
        editor = self.new_entry()
        editor.setPlainText('original')
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        editor.setTextCursor(cursor)
        editor.setFocus()
        QTest.keyClick(editor, Qt.Key.Key_B, Qt.KeyboardModifier.ControlModifier)
        editor.insertPlainText('new')
        self.assertLess(char_format(editor, 0, 1).fontWeight(), QFont.Weight.Bold)
        self.assertEqual(char_format(editor, 8, 9).fontWeight(), QFont.Weight.Bold)

    def test_all_selected_paragraphs_align_without_touching_other_paragraph(self):
        editor = self.new_entry()
        editor.setPlainText('one\ntwo\nthree')
        cursor = editor.textCursor()
        cursor.setPosition(0)
        cursor.setPosition(7, QTextCursor.MoveMode.KeepAnchor)
        editor.setTextCursor(cursor)
        for flag in (Qt.AlignmentFlag.AlignHCenter, Qt.AlignmentFlag.AlignRight,
                     Qt.AlignmentFlag.AlignJustify, Qt.AlignmentFlag.AlignLeft):
            self.window.format_toolbar.set_alignment(flag)
            self.assertEqual(editor.document().begin().blockFormat().alignment(), flag)
            self.assertEqual(editor.document().begin().next().blockFormat().alignment(), flag)
            self.assertEqual(editor.document().lastBlock().blockFormat().alignment(), Qt.AlignmentFlag.AlignLeft)

    def test_defaults_seed_new_entries_preserve_existing_and_survive_switch(self):
        editor = self.new_entry()
        editor.setHtml('<p><span style="font-family:SimSun;font-size:23pt">已有文字</span></p>')
        key = self.window.current_id
        self.window.save()
        font = QFont('Arial', 18)
        self.window.default_body_font = font
        editor = self.new_entry()
        editor.insertPlainText('new entry')
        self.assertIn('font-size:18pt', editor.toHtml())
        self.assertIn("font-family:'Arial'", editor.toHtml())
        self.window.save()
        self.window.load_article(key)
        self.assertEqual(char_format(editor, 0, 1).fontPointSize(), 23)
        self.assertEqual(char_format(editor, 0, 1).fontFamilies(), ['SimSun'])

    def test_defaults_dialog_cancel_and_preview_do_not_edit_document(self):
        editor = self.new_entry()
        editor.setPlainText('keep')
        before = editor.toHtml()
        dialog = DefaultTypographyDialog(QFont('Arial', 12), self.window)
        dialog.size.setValue(26)
        dialog.reject()
        self.assertEqual(editor.toHtml(), before)
        self.assertEqual(self.window.default_body_font.pointSizeF(), 12)

    def test_default_preference_is_persisted_without_reformatting_current_entry(self):
        editor = self.new_entry()
        editor.setPlainText('unchanged')
        before = editor.toHtml()
        with patch('northdiary.ui.main_window.DefaultTypographyDialog') as dialog_type:
            dialog_type.return_value.exec.return_value = 1
            dialog_type.return_value.DialogCode.Accepted = 1
            dialog_type.return_value.chosen_font.return_value = QFont('SimSun', 19)
            self.window.configure_default_typography()
        self.assertEqual(self.window.ui_settings.value('editor/default_family'), 'SimSun')
        self.assertEqual(self.window.ui_settings.value('editor/default_size', type=float), 19)
        self.assertEqual(editor.toHtml(), before)

    def test_theme_and_reading_changes_do_not_replace_document_default_font(self):
        self.window.default_body_font = QFont('SimSun', 19)
        editor = self.new_entry()
        editor.insertPlainText('custom default')
        for name in ('dark', 'cream', 'light'):
            self.window.set_theme(name == 'dark', name)
            self.assertEqual(editor.document().defaultFont().family(), 'SimSun')
            self.assertEqual(editor.document().defaultFont().pointSizeF(), 19)
            self.assertIn('font-size:19pt', editor.toHtml())
        self.window.preview.setChecked(True)
        self.window.toggle_preview()
        self.assertIn('font-size:19pt', editor.toHtml())


class TypographyEpubTests(unittest.TestCase):
    def test_actual_qt_export_import_preserves_default_local_styles_and_alignment(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        source, target = Database(root/'source'), Database(root/'target')
        self.addCleanup(source.close)
        self.addCleanup(target.close)
        editor = ArticleEditor()
        editor.load_body('', QFont('Arial', 17))
        editor.setHtml('''<body style="font-family:'Arial';font-size:17pt">
            <p align="center" style="text-indent:24px">base <span style="font-family:'SimSun';font-size:25pt;font-weight:700;font-style:italic;text-decoration:underline">styled</span></p>
            <p align="justify">justified</p><p align="right">right</p></body>''')
        repo = ArticleRepository(source)
        entry = repo.create()
        repo.save(entry.id, '排版测试', '2026-11-06', editor.toHtml(), editor.toPlainText(), [], [])
        path = root/'typography.epub'
        EpubExporter(repo, AttachmentService(source)).export(ExportSelection((entry.id,), '排版测试'), path)
        with ZipFile(path) as archive:
            chapter = archive.read('EPUB/chapter-1.xhtml').decode()
            parsed = html.fromstring(chapter.encode())
            default_div = parsed.xpath('//div')[0]
            self.assertIn('font-size: 17pt', default_div.get('style'))
            self.assertIn('font-family: \'Arial\'', default_div.get('style'))
            self.assertIn('text-align: center', chapter)
            self.assertIn('text-indent: 24px', chapter)
            self.assertIn('font-size: 25pt', chapter)
            self.assertTrue(parsed.xpath('//strong//em//u'))
        target_repo = ArticleRepository(target)
        result = EpubImporter(target_repo, AttachmentService(target)).import_file(path)
        imported = target_repo.get(result.article_ids[0])
        after = ArticleEditor()
        after.load_body(imported.body_html, QFont('Courier New', 9))
        text = after.toPlainText()
        position = text.index('styled')
        local = char_format(after, position, position+1)
        self.assertEqual(local.fontPointSize(), 25)
        self.assertEqual(local.fontFamilies(), ['SimSun'])
        self.assertTrue(local.fontItalic() and local.fontUnderline())
        self.assertEqual(local.fontWeight(), QFont.Weight.Bold)
        base = char_format(after, 0, 1)
        self.assertEqual(base.fontPointSize(), 17)
        self.assertEqual(base.fontFamilies(), ['Arial'])
        first = after.document().begin()
        self.assertTrue(first.blockFormat().alignment() & Qt.AlignmentFlag.AlignHCenter)
        self.assertEqual(first.blockFormat().textIndent(), 24)
        self.assertEqual(first.next().blockFormat().alignment(), Qt.AlignmentFlag.AlignJustify)
        self.assertTrue(first.next().next().blockFormat().alignment() & Qt.AlignmentFlag.AlignRight)

    def test_css_whitelist_blocks_resources_but_keeps_typography_and_case(self):
        source = '''<p align="right" style="background:url(https://example.invalid/x);font-family:'MiXeD 中文'; font-size:24pt;position:fixed;text-indent:32px;-qt-user-state:1">ok<span style="font-family:url(x);font-size:expression(x);color:red">safe</span></p>'''
        body = clean_body(source, lambda _: self.fail('Unexpected resource'))
        from lxml import etree
        value = etree.tostring(body, encoding='unicode')
        for blocked in ('url(', 'expression', 'position', '-qt-', 'color:'):
            self.assertNotIn(blocked, value)
        self.assertIn('MiXeD 中文', value)
        self.assertIn('text-align: right', value)
