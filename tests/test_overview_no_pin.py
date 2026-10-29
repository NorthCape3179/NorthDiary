import unittest
import test_ui
from northdiary.ui.overview_dialog import OverviewDialog


class OverviewPinTests(unittest.TestCase):
    setUp = test_ui.WindowTests.setUp
    tearDown = test_ui.WindowTests.tearDown

    def test_overview_ignores_pin_sidebar_keeps_it(self):
        w = self.window
        for title in ('A文章', 'Z文章'):
            w.new_article(); w.title.setText(title); w.save()
        w.repository.set_pinned(w.current_id, True)
        options=[('标题', 'title'), ('创建最早', 'created_asc')]
        dialog=OverviewDialog(w.repository, options, 'title', w)
        self.assertEqual(dialog.table.item(0,0).text(), 'A文章')
        self.assertEqual(dialog.table.item(1,0).text(), 'Z文章')
        self.assertNotIn('置顶', dialog.count_label.text())
        self.assertEqual(w.repository.list(sort='title')[0].title, 'Z文章')
        dialog.sort.setCurrentIndex(1)
        self.assertEqual(dialog.table.item(0,0).text(), 'A文章')
        dialog.close()
