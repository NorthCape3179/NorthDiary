import time
import unittest
from unittest.mock import patch

import test_ui
from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QTextCursor, QTextCharFormat, QFont, QImage
from PySide6.QtTest import QTest, QSignalSpy
from PySide6.QtWidgets import QDialog

from northdiary.ui.main_window import MainWindow
from northdiary.ui.theme import apply_theme, color


class MidnightRadioTests(unittest.TestCase):
    setUp = test_ui.WindowTests.setUp
    tearDown = test_ui.WindowTests.tearDown

    def enable_radio(self):
        self.window.theme_actions['radio'].trigger()
        test_ui.APP.processEvents()
        return self.window

    def test_theme_menu_restore_and_light_mode_roundtrip(self):
        w = self.enable_radio()
        self.assertEqual(w.property('colorTheme'), 'radio')
        self.assertTrue(w.property('darkTheme'))
        self.assertTrue(w.timeline.radio_dial.isVisible())
        self.assertTrue(w.radio_station.isVisible())
        self.assertEqual(w.timeline.height(), 56)
        self.assertEqual(color('#315c4d', w).name(), '#81c8cc')
        other = MainWindow(self.database)
        try:
            self.assertEqual(other.property('colorTheme'), 'radio')
        finally:
            other.close()
        w.set_theme(False)
        self.assertFalse(w.timeline.radio_dial.isVisible())
        self.assertFalse(w.radio_station.isVisible())
        self.assertEqual(w.timeline.height(), 40)
        w.set_theme(True)
        self.assertEqual(w.property('colorTheme'), 'radio')

    def test_theme_switch_preserves_document_font_and_local_formats(self):
        w = self.window
        w.new_article()
        w.editor.setPlainText('格式保留')
        cursor = w.editor.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        fmt = QTextCharFormat()
        fmt.setFontWeight(QFont.Weight.Bold)
        fmt.setFontItalic(True)
        fmt.setFontUnderline(True)
        cursor.mergeCharFormat(fmt)
        before, font = w.editor.toHtml(), QFont(w.editor.document().defaultFont())
        for theme in ('radio', 'light', 'radio', 'wine'):
            w.set_theme(theme in ('radio', 'wine'), theme)
            self.assertEqual(w.editor.toHtml(), before)
            self.assertEqual(w.editor.document().defaultFont(), font)
        self.assertEqual(w.editor.toPlainText(), '格式保留')

    def test_knob_wraps_across_year_and_keyboard_commits_once(self):
        w = self.enable_radio()
        w.timeline.setDate(QDate(2025, 12, 31))
        dial = w.timeline.radio_dial
        committed = QSignalSpy(w.timeline.dateSelected)
        dial.setValue(348)
        self.assertEqual(w.timeline.selected, QDate(2025, 12, 30))
        dial.setValue(0)
        self.assertEqual(w.timeline.selected, QDate(2025, 12, 31))
        QTest.keyClick(dial, Qt.Key.Key_Right)
        self.assertEqual(w.timeline.selected, QDate(2026, 1, 1))
        QTest.qWait(350)
        self.assertEqual(committed.count(), 1)
        self.assertEqual(w.browse_date, '2026-01-01')
        self.assertFalse(w.dirty)

    def test_knob_respects_date_limits(self):
        w = self.enable_radio()
        w.timeline.setDate(QDate(1753, 1, 1))
        w.timeline.tune_days(-1)
        self.assertEqual(w.timeline.selected, QDate(1753, 1, 1))
        w.timeline.setDate(QDate(9999, 12, 31))
        w.timeline.tune_days(1)
        self.assertEqual(w.timeline.selected, QDate(9999, 12, 31))

    def test_knob_failed_save_preserves_article_and_its_date(self):
        w = self.enable_radio()
        article = w.repository.create()
        w.repository.save(article.id, '保存保护', '2026-11-17', '<p>原文</p>', '原文', [], [])
        w.browse_day(QDate(2026, 11, 17))
        w.editor.setPlainText('未保存的文字')
        with patch.object(w.repository, 'save', side_effect=OSError('test')), patch.object(w, 'fail'):
            w.timeline.tune_days(1)
            w.timeline.finish_tuning()
        self.assertEqual(w.current_id, article.id)
        self.assertEqual(w.browse_date, '2026-11-17')
        self.assertEqual(w.timeline.selected, QDate(2026, 11, 17))
        self.assertEqual(w.editor.toPlainText(), '未保存的文字')
        self.assertTrue(w.dirty)

    def test_dialog_and_calendar_inherit_radio_palette(self):
        w = self.enable_radio()
        dialog = QDialog(w)
        apply_theme(dialog, True, 'radio')
        self.assertEqual(color('#fffefa', dialog).name(), '#182637')
        self.assertIn('#81c8cc', dialog.styleSheet())
        dialog.close()

    def test_lyrics_known_unknown_paused_and_translation_paint(self):
        w = self.enable_radio()
        b = w.lyrics_board
        b.show()
        b.caption = '原创演示 · 夜晚的信号'
        b.lines, b.stamps = [(0, '把今天的风，寄给明天的你。')], [0]
        b.translations = {0: 'A little memory for tomorrow.'}
        b.track = {'playing': True, 'position_known': True, 'position': 3,
                   'sampled': time.monotonic(), 'rate': 1, 'duration': 120}
        for known, playing in ((True, True), (True, False), (False, True)):
            b.track.update(position_known=known, playing=playing)
            test_ui.APP.processEvents()
            image = b.grab().toImage()
            self.assertFalse(image.isNull())
            self.assertEqual(b.lines[0][1], '把今天的风，寄给明天的你。')
        b.track = None
        b.lines, b.stamps, b.plain = [], [], []
        b.message = '未连接网易云音乐'
        self.assertFalse(b.grab().isNull())

    def test_minimum_window_keeps_dial_and_editor_in_bounds(self):
        w = self.enable_radio()
        w.resize(1000, 640)
        test_ui.APP.processEvents()
        dial = w.timeline.radio_dial
        self.assertTrue(w.timeline.rect().contains(dial.geometry()))
        self.assertGreaterEqual(w.editor.width(), 160)
        self.assertGreater(w.editor.height(), 40)


if __name__ == '__main__':
    unittest.main()
