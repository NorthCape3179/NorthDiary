import unittest
import test_ui
from PySide6.QtCore import QDate
from northdiary.ui.date_picker import DateDialog, parse_partial, matches_day


class PartialDateTests(unittest.TestCase):
    setUp = test_ui.WindowTests.setUp
    tearDown = test_ui.WindowTests.tearDown
    # Reuse only the fixture, not the inherited test suite.
    def test_partial_persistence_and_timeline_filter(self):
        keys = []
        for value in ('2026-未知-未知', '2026-07-未知', '2026-07-15'):
            self.window.new_article()
            self.window.date.setText(value)
            self.window.save()
            keys.append(self.window.current_id)
        for day, expected in ((QDate(2026,7,15), keys), (QDate(2026,7,31), keys[:2]),
                              (QDate(2026,2,28), keys[:1]), (QDate(2027,1,1), [])):
            self.window.browse_day(day)
            self.assertEqual(set(self.window.article_list.ids()), set(expected))
            self.assertEqual(self.window.timeline.selected, day)
        self.window.load_article(keys[0])
        self.assertEqual(self.window.date.text(), '2026-未知-未知')
        self.assertTrue(self.window.paper.month_unknown)
        self.assertEqual(self.window.paper.name, 'unknown-month.png')
        self.assertFalse(self.window.paper.source.isNull())
        self.window.set_theme(True)
        self.assertEqual(self.window.paper.name, 'unknown-month.png')
        self.window.set_theme(False)
        self.window.editor.setPlainText('保留未知日期')
        self.window.save()
        self.assertEqual(self.window.repository.get(keys[0]).diary_date, '2026-未知-未知')
        self.window.date.setDate(QDate(2026,8,12))
        self.assertFalse(self.window.paper.month_unknown)

    def test_partial_calendar_controls(self):
        dialog = DateDialog(QDate(2026,7,15), allow_partial=True)
        dialog.unknown_month.click()
        self.assertEqual(dialog.input.text(), '2026-未知-未知')
        dialog.unknown_day.click()
        self.assertEqual(dialog.input.text(), '2026-07-未知')
        dialog.month.setCurrentIndex(1)
        self.assertEqual(dialog.input.text(), '2026-02-未知')
        dialog.accept_input()
        self.assertEqual(dialog.precision, 'month')
        dialog.choose(QDate(2024,2,29))
        self.assertEqual(dialog.precision, 'day')
        self.assertEqual(dialog.input.text(), '2024-02-29')
        for value in ('2026-未知-15', '2026-13-未知', '2026-02-30'):
            self.assertFalse(parse_partial(value)[0].isValid())
        self.assertTrue(matches_day('2024-02-未知', '2024-02-29'))
        dialog.close()




