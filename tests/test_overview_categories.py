import unittest
from unittest.mock import patch
import test_ui
from PySide6.QtCore import Qt
from PySide6.QtTest import QSignalSpy
from PySide6.QtWidgets import QMessageBox
from northdiary.ui.overview_dialog import OverviewDialog


class OverviewCategoryTests(unittest.TestCase):
    setUp=test_ui.WindowTests.setUp
    tearDown=test_ui.WindowTests.tearDown

    def prepare(self):
        w=self.window
        for title,labels in [('读书一',['阅读']),('旅行一',['旅行']),('旅行二',['旅行']),('空分类',[])]:
            a=w.repository.create()
            w.repository.save(a.id,title,'2026-10-30','<p>文字</p>','文字',labels,[])
        d=OverviewDialog(w.repository,[('标题','title'),('创建','created_desc')],'title',w)
        d.deleteRequested.connect(w.trash_article)
        d.show();test_ui.APP.processEvents();self.addCleanup(d.close)
        return d

    def titles(self,d):return [d.table.item(i,0).text() for i in range(d.table.rowCount())]

    def test_category_selector_shown_only_in_category_mode_and_filters(self):
        d=self.prepare();self.assertFalse(d.category_combo.isVisible())
        spy=QSignalSpy(d.sortingChanged)
        d.sort.setCurrentIndex(d.sort.findData('category'))
        self.assertTrue(d.category_combo.isVisible())
        self.assertEqual(spy.count(),0)
        self.assertEqual(d.table.item(d.table.rowCount()-1,1).text(),'未分类')
        d.category_combo.setCurrentIndex(d.category_combo.findData('旅行'))
        self.assertEqual(self.titles(d),['旅行一','旅行二'])
        d.search.setText('二');self.assertEqual(self.titles(d),['旅行二'])
        d.search.clear();d.category_combo.setCurrentIndex(d.category_combo.findData(''))
        self.assertEqual(self.titles(d),['空分类'])
        d.sort.setCurrentIndex(d.sort.findData('created_desc'))
        self.assertFalse(d.category_combo.isVisible())
        self.assertEqual(d.table.rowCount(),4)
        self.assertEqual(spy.count(),1)

    def test_filtered_article_open_and_delete_use_correct_id(self):
        d=self.prepare();d.sort.setCurrentIndex(d.sort.findData('category'))
        d.category_combo.setCurrentIndex(d.category_combo.findData('阅读'))
        key=d.table.item(0,0).data(Qt.ItemDataRole.UserRole)
        d.open_selected();self.assertEqual(d.article_id,key)
        with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Yes):d.delete_article(key)
        self.assertIsNotNone(self.window.repository.get(key).deleted_at)
        self.assertEqual(d.table.rowCount(),0)
        self.assertEqual(len(self.window.repository.list()),3)
