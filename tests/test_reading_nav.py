import unittest
import test_ui
from PySide6.QtCore import QDate


class ReadingNavTests(unittest.TestCase):
    setUp = test_ui.WindowTests.setUp
    tearDown = test_ui.WindowTests.tearDown

    def test_layout_and_navigation(self):
        w = self.window
        keys = []
        for date in ('2026-01-31', '2026-02-28', '2026-未知-未知'):
            w.new_article(); w.date.setText(date); w.save(); keys.append(w.current_id)
        w.load_article(keys[0])
        w.preview.setChecked(True); w.toggle_preview()
        self.assertEqual(w.image_list.parentWidget(), w.paper)
        self.assertFalse(w.image_list.isWrapping())
        self.assertTrue(w.reading_nav.isVisible())
        w.shift_reading_date(1, True)
        self.assertEqual(w.reading_date.date(), QDate(2026, 2, 28))
        self.assertEqual(w.reading_articles.count(), 2)
        self.assertEqual(w.current_id, keys[2])
        self.assertTrue(w.preview.isChecked())
        w.open_reading_article(keys[0])
        w.step_reading_article(1)
        self.assertEqual(w.current_id, keys[1])
        w.shift_reading_date(1)
        self.assertEqual(w.reading_date.date(), QDate(2026, 3, 1))
        self.assertEqual(w.reading_articles.count(), 1)
        w.preview.setChecked(False); w.toggle_preview()
        self.assertEqual(w.image_list.parentWidget(), w.photo_panel)
        self.assertTrue(w.image_list.isWrapping())
        self.assertFalse(w.reading_nav.isVisible())
