import unittest
import test_ui
from PySide6.QtCore import QDate
from northdiary.ui.date_picker import DateDialog


class CalendarMarksTests(unittest.TestCase):
    setUp = test_ui.WindowTests.setUp
    tearDown = test_ui.WindowTests.tearDown

    def test_marks_exact_month_year_and_excludes_trash(self):
        w=self.window
        for date in ('2026-07-15', '2026-08-未知', '2025-未知-未知', '2026-07-16'):
            w.new_article();w.date.setText(date);w.save()
        w.repository.set_deleted(w.current_id)
        for dark in (False, True):
            w.set_theme(dark)
            d=DateDialog(QDate(2026,7,15), w)
            for date, expected in ((QDate(2026,7,15), True), (QDate(2026,7,16), False),
                                   (QDate(2026,8,20), True), (QDate(2025,3,1), True)):
                d.choose(date)
                button=next(b for b in d.days if b.property('date') == date)
                self.assertEqual(button.property('hasArticles'), expected)
            d.close()
