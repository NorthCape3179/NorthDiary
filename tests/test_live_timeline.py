import unittest
import test_ui
from PySide6.QtCore import QDate, QPoint, Qt
from PySide6.QtTest import QTest


class LiveTimelineTests(unittest.TestCase):
    setUp = test_ui.WindowTests.setUp
    tearDown = test_ui.WindowTests.tearDown

    def test_zoom_keeps_animating_when_pointer_stops_and_reverses_smoothly(self):
        t = self.window.timeline
        t.setDate(QDate(2025, 1, 1))
        QTest.mousePress(t, Qt.MouseButton.LeftButton, pos=QPoint(30, 35))
        QTest.mouseMove(t, QPoint(230, 35))
        selected = QDate(t.selected)
        QTest.qWait(70)
        first = t.spacing
        self.assertGreater(first, t.DRAG_SPACING)
        self.assertLess(first, t.REST_SPACING)
        QTest.qWait(90)
        self.assertLess(t.spacing, first)
        self.assertEqual(t.selected, selected)
        pointer = (t.position_days-t.view_center)*t.spacing
        self.assertAlmostEqual(pointer, t.drag_pointer)
        QTest.mouseMove(t, QPoint(90, 35))
        before = t.spacing
        QTest.qWait(70)
        self.assertGreater(t.spacing, before)
        self.assertLess(t.spacing, t.REST_SPACING)
        QTest.mouseRelease(t, Qt.MouseButton.LeftButton, pos=QPoint(90, 35))
        QTest.qWait(260)
        self.assertEqual(t.spacing, t.REST_SPACING)

    def test_threshold_crossing_does_not_skip_a_day_or_snap_zoom(self):
        t = self.window.timeline;t.setDate(QDate(2025, 1, 1))
        QTest.mousePress(t, Qt.MouseButton.LeftButton, pos=QPoint(30, 35))
        QTest.mouseMove(t, QPoint(132, 35))
        self.assertEqual(t.selected, QDate(2025, 1, 4))
        QTest.mouseMove(t, QPoint(133, 35))
        self.assertEqual(t.selected, QDate(2025, 1, 4))
        self.assertGreater(t.zoom_target, t.REST_SPACING-.01)
        QTest.mouseRelease(t, Qt.MouseButton.LeftButton, pos=QPoint(133, 35))

    def test_return_animation_survives_slow_article_commit(self):
        t = self.window.timeline;t.setDate(QDate(2025, 1, 1))
        t.dateSelected.connect(lambda _: QTest.qWait(240))
        QTest.mousePress(t, Qt.MouseButton.LeftButton, pos=QPoint(30, 35))
        QTest.mouseMove(t, QPoint(230, 35));QTest.qWait(100)
        self.assertLess(t.spacing, t.REST_SPACING)
        QTest.mouseRelease(t, Qt.MouseButton.LeftButton, pos=QPoint(230, 35))
        self.assertLess(t.spacing, t.REST_SPACING)
        self.assertEqual(t.animation.state(), t.animation.State.Running)
        QTest.qWait(260)
        self.assertEqual(t.spacing, t.REST_SPACING)

    def test_drag_previews_before_release_without_resetting_drag(self):
        w = self.window
        w.new_article(); w.confirm_article(w.current_id); w.date.setDate(QDate(2025,1,2))
        w.title.setText('第二天的文章'); w.save(); key = w.current_id
        w.new_article(); w.confirm_article(w.current_id); w.date.setDate(QDate(2025,1,1))
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
        self.assertEqual(w.browse_date, '2025-01-04')
        self.assertGreater(t.spacing, t.DRAG_SPACING)
        self.assertLess(t.spacing, t.REST_SPACING)
        QTest.mouseRelease(t, Qt.MouseButton.LeftButton, pos=QPoint(144,35))
        self.assertEqual(w.repository.get(key).diary_date, '2025-01-02')
