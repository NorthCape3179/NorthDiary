import unittest
from unittest.mock import patch
import test_ui
from PySide6.QtCore import QDate
from PySide6.QtWidgets import QDialog


class EmptyCalendarTests(unittest.TestCase):
    setUp = test_ui.WindowTests.setUp
    tearDown = test_ui.WindowTests.tearDown

    def test_pick_date_before_creation(self):
        w=self.window
        self.assertIsNone(w.current_id)
        self.assertTrue(w.date.isEnabled())
        def accept_date(dialog):
            dialog.selected=QDate(2001,7,15)
            return QDialog.DialogCode.Accepted
        with patch('northdiary.ui.date_picker.DateDialog.exec', accept_date):
            w.date.open_calendar()
        self.assertEqual(w.date.date(), QDate(2001,7,15))
        self.assertEqual(w.browse_date, '2001-07-15')
        self.assertEqual(w.repository.list(), [])
        w.new_article();w.title.setText('往事');w.save()
        self.assertEqual(w.repository.get(w.current_id).diary_date, '2001-07-15')
        w.load_article(None)
        self.assertTrue(w.date.isEnabled())
        w.date.setText('1999-未知-未知')
        w.new_article();w.save()
        self.assertEqual(w.repository.get(w.current_id).diary_date, '1999-未知-未知')
