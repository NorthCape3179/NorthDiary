import unittest
from PySide6.QtCore import Qt
import test_ui

class SidebarDateTests(unittest.TestCase):
    setUp=test_ui.WindowTests.setUp
    tearDown=test_ui.WindowTests.tearDown

    def test_default_uses_diary_dates_and_outside_is_after_dated_articles(self):
        w=self.window;self.assertEqual(w.sort_key,'diary_desc')
        keys=[]
        for title,date in [('老文章','2014-12-25'),('新文章','2025-07-22'),('年月未知','2020-未知-未知'),('已知月份','2020-02-未知')]:
            w.new_article(); w.confirm_article(w.current_id);w.title.setText(title);w.date.setText(date);w.save();keys.append(w.current_id)
        w.set_space(True);w.new_article(); w.confirm_article(w.current_id);w.title.setText('无日期');w.save();outside=w.current_id
        w.refresh_list()
        self.assertEqual(w.article_list.ids(),[keys[1],keys[3],keys[2],keys[0],outside])
        self.assertIn('时间线之外',w.article_list.item(4).text())
        w.pin_article(keys[0]);w.refresh_list();self.assertEqual(w.article_list.ids()[0],keys[0])
        self.assertEqual(w.ui_settings.value('article_sort'),'diary_desc')
