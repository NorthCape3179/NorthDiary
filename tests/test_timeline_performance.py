import unittest
from unittest.mock import patch
import test_ui
from PySide6.QtCore import QDate
from PySide6.QtTest import QTest


class TimelinePerformanceTests(unittest.TestCase):
    setUp=test_ui.WindowTests.setUp
    tearDown=test_ui.WindowTests.tearDown

    def seed(self):
        w=self.window; ids=[]
        for day in (1,2):
            article=w.repository.create()
            w.repository.save(article.id,f'第{day}天',f'2025-01-{day:02d}','<p>内容</p>','内容',[],[])
            ids.append(article.id)
        w.browse_day(QDate(2025,1,1))
        return ids

    def test_switch_loads_destination_once_without_loading_blank(self):
        ids=self.seed();w=self.window
        with patch.object(w,'load_article',wraps=w.load_article) as load:
            w.browse_day(QDate(2025,1,2))
            self.assertEqual(load.call_args_list,[unittest.mock.call(ids[1])])
            w.browse_day(QDate(2025,1,2))
            self.assertEqual(load.call_count,1)
        self.assertEqual(w.editor.toPlainText(),'内容')
        self.assertTrue(w.updatesEnabled())

    def test_fast_preview_coalesces_to_latest_but_release_is_immediate(self):
        self.seed();w=self.window
        with patch.object(w,'browse_day',wraps=w.browse_day) as browse:
            for day in range(2,25): w.preview_timeline_day(QDate(2025,1,day))
            browse.assert_not_called()
            for _ in range(40):
                if browse.call_count: break
                QTest.qWait(50)
            self.assertEqual(browse.call_count,1)
            self.assertEqual(w.browse_date,'2025-01-24')
            w.preview_timeline_day(QDate(2025,1,25))
            w.commit_timeline_day(QDate(2025,1,26))
            self.assertEqual(w.browse_date,'2025-01-26')
            QTest.qWait(130)
            self.assertEqual(browse.call_count,2)

    def test_empty_dates_do_not_rebuild_editor_or_mark_dirty(self):
        self.seed();w=self.window
        w.browse_day(QDate(2025,1,3))
        with patch.object(w,'load_article',wraps=w.load_article) as load:
            w.browse_day(QDate(2025,1,4))
            w.browse_day(QDate(2025,4,5))
            load.assert_not_called()
        self.assertEqual(w.date.date(),QDate(2025,4,5))
        self.assertFalse(w.dirty)
        self.assertIn('春天',w.paper.name)

    def test_failed_save_preserves_unsaved_article_and_repaint_state(self):
        ids=self.seed();w=self.window
        w.editor.setPlainText('未保存修改')
        with patch.object(w.repository,'save',side_effect=OSError('test')),patch.object(w,'fail'):
            w.commit_timeline_day(QDate(2025,1,2))
        self.assertEqual(w.current_id,ids[0])
        self.assertEqual(w.browse_date,'2025-01-01')
        self.assertEqual(w.editor.toPlainText(),'未保存修改')
        self.assertTrue(w.dirty)
        self.assertTrue(w.updatesEnabled())
