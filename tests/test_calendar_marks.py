import unittest
import test_ui
from PySide6.QtCore import QDate
from PySide6.QtGui import QPalette
from northdiary.ui.date_picker import DateDialog
from northdiary.ui.theme import color, apply_theme


class CalendarMarksTests(unittest.TestCase):
    setUp = test_ui.WindowTests.setUp
    tearDown = test_ui.WindowTests.tearDown

    def test_visible_calendar_keeps_marked_text_color_after_chrome_and_theme(self):
        w=self.window
        w.new_article();w.confirm_article(w.current_id);w.date.setText('2026-07-15');w.save()
        for name in ('dark','wine','light','cream','burgundy','citrus','blue','gray'):
            with self.subTest(theme=name):
                dark=name in ('dark','wine');w.set_theme(dark,name)
                d=DateDialog(QDate(2026,7,20),w.date)
                d.show();test_ui.APP.processEvents()
                marked=next(b for b in d.days if b.property('date')==QDate(2026,7,15))
                empty=next(b for b in d.days if b.property('date')==QDate(2026,7,20))
                accent=color('#7d9b89' if dark else '#315c4d',w).name()
                self.assertEqual(marked.palette().color(QPalette.ColorRole.ButtonText).name(),accent)
                self.assertTrue(marked.font().bold())
                self.assertNotEqual(empty.palette().color(QPalette.ColorRole.ButtonText).name(),accent)
                apply_theme(d,dark,name);test_ui.APP.processEvents()
                d.move_month(1);d.move_month(-1);test_ui.APP.processEvents()
                self.assertEqual(marked.palette().color(QPalette.ColorRole.ButtonText).name(),accent)
                d.choose(QDate(2026,7,15));test_ui.APP.processEvents()
                self.assertEqual(marked.palette().color(QPalette.ColorRole.ButtonText).name(),accent)
                apply_theme(d,False,'blue');test_ui.APP.processEvents()
                self.assertEqual(marked.palette().color(QPalette.ColorRole.ButtonText).name(),'#306cc2')
                d.close();d.deleteLater();test_ui.APP.processEvents()

    def test_marks_only_exact_dates_and_excludes_unknown_and_trash(self):
        w=self.window
        for date in ('2026-07-15', '2026-08-未知', '2025-未知-未知', '2026-07-16'):
            w.new_article(); w.confirm_article(w.current_id);w.date.setText(date);w.save()
        w.repository.set_deleted(w.current_id)
        for dark in (False, True):
            w.set_theme(dark)
            d=DateDialog(QDate(2026,7,15), w)
            for date, expected in ((QDate(2026,7,15), True), (QDate(2026,7,16), False),
                                   (QDate(2026,8,20), False), (QDate(2025,3,1), False)):
                d.choose(date)
                button=next(b for b in d.days if b.property('date') == date)
                self.assertEqual(button.property('hasArticles'), expected)
            d.close()

    def test_unknown_year_does_not_mark_every_day_in_leap_year(self):
        w=self.window
        for date in ('2000-未知-未知','2000-03-未知','2000-06-15'):
            w.new_article();w.confirm_article(w.current_id);w.date.setText(date);w.save()
        d=DateDialog(QDate(2000,1,1),w)
        d.show();test_ui.APP.processEvents()
        seen=set()
        for month in range(1,13):
            d.choose(QDate(2000,month,1))
            for button in d.days:
                date=button.property('date')
                if date.year()!=2000:
                    continue
                seen.add(date.toString('yyyy-MM-dd'))
                self.assertEqual(button.property('hasArticles'),date==QDate(2000,6,15))
                self.assertEqual('有文章' in button.toolTip() and '暂无文章' not in button.toolTip(),date==QDate(2000,6,15))
        self.assertEqual(len(seen),366)
        d.close()
