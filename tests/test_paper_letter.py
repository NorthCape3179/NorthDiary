import unittest
from zipfile import ZipFile
from unittest.mock import patch

import test_ui
from PySide6.QtCore import Qt, QDate, QSize
from PySide6.QtGui import QFont, QTextCursor, QTextCharFormat, QIcon, QPixmap
from PySide6.QtWidgets import QListWidgetItem, QDialog

from northdiary.ui.main_window import MainWindow
from northdiary.ui.theme import apply_theme, color
from northdiary.ui.letter_theme import stationery_rules, paper_fibers
from northdiary.ui.image_board import photo_size


class PaperLetterTests(unittest.TestCase):
    setUp = test_ui.WindowTests.setUp
    tearDown = test_ui.WindowTests.tearDown

    def enable_letter(self):
        self.window.theme_actions['letter'].trigger()
        test_ui.APP.processEvents()
        return self.window

    def test_menu_restart_and_radio_roundtrip(self):
        w = self.enable_letter()
        self.assertEqual(w.property('colorTheme'), 'letter')
        self.assertFalse(w.property('darkTheme'))
        self.assertTrue(w.letter_footer.isVisible())
        self.assertTrue(w.theme_combo.findData('letter') >= 0)
        self.assertFalse(w.radio_station.isVisible())
        self.assertFalse(w.timeline.radio_dial.isVisible())
        other = MainWindow(self.database)
        try:
            self.assertEqual(other.property('colorTheme'), 'letter')
        finally:
            other.close()
        w.set_theme(True, 'radio')
        self.assertTrue(w.timeline.radio_dial.isVisible())
        self.assertFalse(w.letter_footer.isVisible())
        w.set_theme(False)
        self.assertEqual(w.property('colorTheme'), 'letter')

    def test_document_format_default_font_and_saved_html_are_unchanged(self):
        w = self.window
        w.new_article()
        w.editor.setPlainText('保持原来的字体和局部格式。')
        cursor = w.editor.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        fmt = QTextCharFormat()
        fmt.setFontWeight(QFont.Weight.Bold)
        fmt.setFontItalic(True)
        fmt.setFontUnderline(True)
        cursor.mergeCharFormat(fmt)
        html, font = w.editor.toHtml(), QFont(w.editor.document().defaultFont())
        w.save()
        saved = w.repository.get(w.current_id).body_html
        for theme in ('letter', 'radio', 'light', 'letter'):
            w.set_theme(theme == 'radio', theme)
            self.assertEqual(w.editor.toHtml(), html)
            self.assertEqual(w.editor.document().defaultFont(), font)
        w.editor.grab()
        self.assertEqual(w.repository.get(w.current_id).body_html, saved)
        self.assertNotIn('TO MYSELF', html)
        self.assertNotIn('收好今天', html)

    def test_rules_follow_mixed_font_baselines_and_scroll_without_document_edits(self):
        w = self.enable_letter()
        w.new_article()
        w.editor.setPlainText('\n'.join('第%d行 日记内容' % i for i in range(100)))
        cursor = w.editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
        fmt = QTextCharFormat()
        fmt.setFontPointSize(28)
        cursor.mergeCharFormat(fmt)
        w.editor.moveCursor(QTextCursor.MoveOperation.Start)
        test_ui.APP.processEvents()
        before = w.editor.toHtml()
        rules = stationery_rules(w.editor)
        self.assertTrue(rules)
        layout = w.editor.document().begin().layout()
        block_rect = w.editor.document().documentLayout().blockBoundingRect(w.editor.document().begin())
        expected = block_rect.top()+layout.lineAt(0).ascent()+3
        self.assertAlmostEqual(rules[0], expected, places=1)
        w.editor.verticalScrollBar().setValue(113)
        test_ui.APP.processEvents()
        scrolled = stationery_rules(w.editor)
        self.assertNotEqual(rules, scrolled)
        self.assertTrue(all(0 <= y <= w.editor.viewport().height() for y in scrolled))
        self.assertEqual(w.editor.toHtml(), before)

    def test_photo_aspect_and_card_size_are_preserved(self):
        w = self.enable_letter()
        board = w.image_list
        for width, height in ((160, 80), (60, 150), (80, 80)):
            pixmap = QPixmap(width, height)
            pixmap.fill(Qt.GlobalColor.blue)
            item = QListWidgetItem(QIcon(pixmap), '照片')
            item.setData(Qt.ItemDataRole.UserRole, str(width))
            board.addItem(item)
            size = photo_size(item)
            self.assertLessEqual(max(size.width(), size.height()), 80)
            self.assertAlmostEqual(size.width()/size.height(), width/height, delta=.02)
        board.show()
        self.assertFalse(board.grab().isNull())

    def test_epub_exports_content_without_ui_paper_or_postmark(self):
        from northdiary.models import ExportSelection
        from northdiary.services.epub import EpubExporter
        w = self.enable_letter()
        w.new_article()
        w.confirm_article(w.current_id)
        w.title.setText('信笺导出验证')
        w.editor.setPlainText('只有日记正文进入电子书。')
        w.save()
        destination = self.root / 'letter.epub'
        EpubExporter(w.repository, w.attachments).export(
            ExportSelection((w.current_id,), '验证文集', '作者'), destination)
        with ZipFile(destination) as archive:
            content = '\n'.join(archive.read(name).decode('utf-8') for name in archive.namelist()
                                if name.endswith(('.xhtml', '.html')))
        self.assertIn('只有日记正文进入电子书', content)
        for decoration in ('TO MYSELF', '收好今天', 'paper_fibers', '信笺页角装饰'):
            self.assertNotIn(decoration, content)

    def test_palette_dialog_and_background_preference_remain_independent(self):
        w = self.enable_letter()
        self.assertEqual(color('#fffefa', w).name(), '#fff5dd')
        dialog = QDialog(w)
        apply_theme(dialog, False, 'letter')
        self.assertEqual(color('#273b37', dialog).name(), '#424a3d')
        dialog.close()
        w.set_background(False)
        w.set_theme(True, 'radio')
        w.set_theme(False, 'letter')
        w.set_theme(False, 'light')
        self.assertFalse(w.paper.enabled)
        self.assertFalse(w.ui_settings.value('season_background', True, type=bool))
        self.assertIs(paper_fibers(), paper_fibers())

    def test_small_window_keeps_editor_usable_with_lyrics(self):
        w = self.enable_letter()
        w.lyrics_board.show()
        w.resize(1000, 640)
        test_ui.APP.processEvents()
        self.assertGreaterEqual(w.editor.viewport().height(), 40)
        self.assertTrue(w.paper.rect().contains(w.letter_footer.geometry()))
        self.assertTrue(w.paper.rect().contains(w.lyrics_board.geometry()))


if __name__ == '__main__':
    unittest.main()
