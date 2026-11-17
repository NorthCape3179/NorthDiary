import unittest
import test_ui
from PySide6.QtCore import Qt, QPoint, QPointF
from PySide6.QtGui import QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QListWidgetItem
from northdiary.ui.article_list import ArticleList
from northdiary.ui.theme import apply_theme


class ArticleSmoothScrollTests(unittest.TestCase):
    def setUp(self):
        self.listing = ArticleList()
        self.listing.resize(300, 280)
        apply_theme(self.listing, False, 'light')
        for i in range(40):
            item = QListWidgetItem(f'文章 {i}\n2026-11-17 · 100 字符')
            item.setData(Qt.ItemDataRole.UserRole, str(i))
            item.setData(Qt.ItemDataRole.UserRole+1, False)
            self.listing.addItem(item)
        self.listing.show();test_ui.APP.processEvents()
        self.listing.setCurrentRow(0)
        self.listing.verticalScrollBar().setValue(0)

    def tearDown(self):
        self.listing.close();self.listing.deleteLater();test_ui.APP.processEvents()

    def wheel(self, angle=-120, pixels=0):
        viewport = self.listing.viewport()
        point=QPoint(40,40)
        event=QWheelEvent(QPointF(point),QPointF(viewport.mapToGlobal(point)),
                          QPoint(0,pixels),QPoint(0,angle),Qt.MouseButton.NoButton,
                          Qt.KeyboardModifier.NoModifier,Qt.ScrollPhase.ScrollUpdate,False)
        test_ui.APP.sendEvent(viewport,event)

    def test_one_notch_animates_a_short_distance_without_changing_selection(self):
        bar=self.listing.verticalScrollBar();before=self.listing.ids()
        self.wheel()
        self.assertEqual(bar.value(),0)
        QTest.qWait(55)
        self.assertGreater(bar.value(),0)
        self.assertLess(bar.value(),42)
        QTest.qWait(350)
        self.assertEqual(bar.value(),42)
        self.assertFalse(self.listing.wheel_timer.isActive())
        self.assertEqual(self.listing.currentRow(),0)
        self.assertEqual(self.listing.ids(),before)

    def test_fast_wheel_is_bounded_and_reverse_does_not_finish_old_queue(self):
        for _ in range(40):self.wheel()
        self.assertLessEqual(self.listing.wheel_target,126)
        QTest.qWait(65)
        before=self.listing.verticalScrollBar().value()
        self.assertGreater(before,0)
        self.assertLess(before,60)
        self.wheel(120)
        QTest.qWait(100)
        self.assertLess(self.listing.verticalScrollBar().value(),before)

    def test_manual_scrollbar_and_clear_cancel_pending_animation(self):
        self.wheel();QTest.qWait(30)
        bar=self.listing.verticalScrollBar();bar.setValue(500)
        QTest.qWait(250)
        self.assertEqual(bar.value(),500)
        self.assertFalse(self.listing.wheel_timer.isActive())
        self.wheel();self.listing.clear();QTest.qWait(100)
        self.assertFalse(self.listing.wheel_timer.isActive())
        self.assertEqual(bar.value(),0)

    def test_pixel_wheel_boundaries_and_keyboard_navigation(self):
        self.wheel(angle=0,pixels=-15);QTest.qWait(350)
        self.assertEqual(self.listing.verticalScrollBar().value(),12)
        self.wheel(1200);QTest.qWait(350)
        self.assertEqual(self.listing.verticalScrollBar().value(),0)
        bar=self.listing.verticalScrollBar();bar.setValue(bar.maximum())
        self.wheel();QTest.qWait(80)
        self.assertEqual(bar.value(),bar.maximum())
        self.assertFalse(self.listing.wheel_timer.isActive())
        self.listing.setCurrentRow(0)
        self.wheel();QTest.keyClick(self.listing,Qt.Key.Key_Down);QTest.qWait(100)
        self.assertEqual(self.listing.currentRow(),1)
        self.assertFalse(self.listing.wheel_timer.isActive())

    def test_clicking_an_article_stops_motion_before_selection(self):
        self.wheel();QTest.qWait(40)
        point=self.listing.visualItemRect(self.listing.item(1)).center()
        QTest.mouseClick(self.listing.viewport(),Qt.MouseButton.LeftButton,pos=point)
        self.assertEqual(self.listing.currentRow(),1)
        value=self.listing.verticalScrollBar().value()
        QTest.qWait(250)
        self.assertEqual(self.listing.verticalScrollBar().value(),value)
        self.assertFalse(self.listing.wheel_timer.isActive())

    def test_high_resolution_angle_deltas_accumulate(self):
        for _ in range(3):self.wheel(angle=-1)
        QTest.qWait(350)
        self.assertEqual(self.listing.verticalScrollBar().value(),1)
