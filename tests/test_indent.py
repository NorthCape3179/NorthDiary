import unittest
import test_ui
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest


class IndentTests(unittest.TestCase):
    setUp = test_ui.WindowTests.setUp
    tearDown = test_ui.WindowTests.tearDown

    def test_whole_article_indent_roundtrip_and_undo(self):
        self.window.new_article()
        editor = self.window.editor
        editor.setHtml('<p><b>第一段</b>正文</p><p>第二段</p><p><a href="ndiary-image:demo">图片引用</a></p>')
        original = editor.toPlainText()
        QTest.mouseClick(self.window.indent_button, Qt.MouseButton.LeftButton)
        indent = editor.document().begin().blockFormat().textIndent()
        self.assertGreater(indent, 0)
        self.assertEqual(editor.toPlainText(), original)
        block = editor.document().begin()
        while block.isValid():
            self.assertEqual(block.blockFormat().textIndent(), indent)
            block = block.next()
        editor.undo()
        self.assertEqual(editor.document().begin().blockFormat().textIndent(), 0)
        self.window.editor_indent()
        self.window.editor_indent()
        self.assertEqual(editor.document().begin().blockFormat().textIndent(), indent)
        self.assertTrue(editor.image_links('demo'))
        key = self.window.current_id
        self.window.save()
        self.window.load_article(key)
        self.assertEqual(editor.document().begin().blockFormat().textIndent(), indent)
        self.assertIn('font-weight:700', editor.toHtml())
        self.window.preview.setChecked(True)
        self.window.toggle_preview()
        self.assertFalse(self.window.indent_button.isEnabled())
