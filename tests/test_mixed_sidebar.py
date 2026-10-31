import unittest
from PySide6.QtCore import Qt
import test_ui
from northdiary.ui.timeline_overview import group_articles

class MixedSidebarTests(unittest.TestCase):
    setUp=test_ui.WindowTests.setUp
    tearDown=test_ui.WindowTests.tearDown

    def test_sidebar_shows_both_spaces_and_selection_switches_editor(self):
        w=self.window;w.new_article(); w.confirm_article(w.current_id);w.title.setText('时间线内文章');w.save();inside=w.current_id
        w.set_space(True);w.new_article(); w.confirm_article(w.current_id);w.title.setText('无日期文章');w.save();outside=w.current_id
        w.refresh_list()
        self.assertEqual(set(w.article_list.ids()),{inside,outside})
        texts={w.article_list.item(i).data(Qt.ItemDataRole.UserRole):w.article_list.item(i).text() for i in range(w.article_list.count())}
        self.assertIn('\n时间线之外  ·',texts[outside])
        self.assertNotIn('时间线之外',texts[inside])
        w.article_list.setCurrentRow(w.article_list.ids().index(inside))
        self.assertFalse(w.outside);self.assertFalse(w.timeline.isHidden())
        self.assertEqual([a.id for a in w.repository.list()],[inside])
        w.article_list.setCurrentRow(w.article_list.ids().index(outside))
        self.assertTrue(w.outside);self.assertTrue(w.timeline.isHidden());self.assertEqual(w.current_id,outside)
        self.assertEqual(set(w.article_list.ids()),{inside,outside})

    def test_date_browsing_does_not_include_outside_article(self):
        w=self.window;w.new_article(); w.confirm_article(w.current_id);inside=w.current_id;day=w.date.date();w.save()
        w.set_space(True);w.new_article(); w.confirm_article(w.current_id);outside=w.current_id;w.save();w.set_space(False)
        w.browse_day(day)
        self.assertEqual(w.article_list.ids(),[inside]);self.assertNotIn(outside,w.article_list.ids())
