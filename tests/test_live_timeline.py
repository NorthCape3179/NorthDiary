import unittest
import test_ui
from PySide6.QtCore import QDate, QPoint, Qt
from PySide6.QtTest import QTest


class LiveTimelineTests(unittest.TestCase):
    setUp = test_ui.WindowTests.setUp
    tearDown = test_ui.WindowTests.tearDown

    def test_drag_previews_before_release_without_resetting_drag(self):
        w = self.window
        w.new_article(); w.date.setDate(QDate(2025,1,2))
        w.title.setText('第二天的文章'); w.save(); key = w.current_id
        w.new_article(); w.date.setDate(QDate(2025,1,1))
        w.editor.setPlainText('拖动前尚未保存'); first = w.current_id
        t = w.timeline
        QTest.mousePress(t, Qt.MouseButton.LeftButton, pos=QPoint(30,35))
        QTest.mouseMove(t, QPoint(64,35))
        for _ in range(40):
            if w.browse_date == t.selected.toString('yyyy-MM-dd'): break
            QTest.qWait(50)
        self.assertTrue(t.pressed)
        self.assertEqual(w.current_id, key)
        self.assertEqual(w.browse_date, '2025-01-02')
        self.assertEqual(w.repository.get(first).body_text, '拖动前尚未保存')
        self.assertEqual(t.origin, QDate(2025,1,1))
        QTest.mouseMove(t, QPoint(98,35))
        for _ in range(40):
            if w.browse_date == t.selected.toString('yyyy-MM-dd'): break
            QTest.qWait(50)
        self.assertEqual(w.browse_date, '2025-01-03')
        self.assertEqual(w.article_list.count(), 0)
        self.assertIsNone(w.current_id)
        self.assertEqual(t.spacing, t.REST_SPACING)
        QTest.mouseMove(t, QPoint(144,35))
        for _ in range(40):
            if w.browse_date == t.selected.toString('yyyy-MM-dd'): break
            QTest.qWait(50)
        self.assertEqual(w.browse_date, '2025-01-05')
        self.assertEqual(t.spacing, t.DRAG_SPACING)
        QTest.mouseRelease(t, Qt.MouseButton.LeftButton, pos=QPoint(144,35))
        self.assertEqual(w.repository.get(key).diary_date, '2025-01-02')
