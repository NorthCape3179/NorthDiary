import unittest
from unittest.mock import patch
import test_ui
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QMenu, QMessageBox
from northdiary.ui.overview_dialog import OverviewDialog


class OverviewDeleteTests(unittest.TestCase):
    setUp = test_ui.WindowTests.setUp
    tearDown = test_ui.WindowTests.tearDown

    def dialog(self):
        d = OverviewDialog(self.window.repository, [('标题', 'title')], 'title', self.window)
        d.deleteRequested.connect(self.window.trash_article)
        d.show()
        test_ui.APP.processEvents()
        self.addCleanup(d.close)
        return d

    def test_right_click_deletes_clicked_row_and_keeps_other_article(self):
        w = self.window
        w.new_article(); w.title.setText('A'); w.save()
        first = w.current_id
        w.new_article(); w.title.setText('B'); w.editor.setPlainText('保留正文'); w.save()
        second = w.current_id
        d = self.dialog()
        point = d.table.visualItemRect(d.table.item(0, 2)).center()
        with patch('northdiary.ui.overview_dialog.QMenu') as menu_type, patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes):
            menu = menu_type.return_value
            def choose_delete(*args):
                self.assertEqual(menu.addAction.call_args.args[0], '删除')
                menu.addAction.call_args.args[1]()
            menu.exec.side_effect = choose_delete
            d.show_article_menu(point)
        self.assertIsNotNone(w.repository.get(first).deleted_at)
        self.assertIsNone(w.repository.get(second).deleted_at)
        self.assertEqual(w.repository.get(second).body_text, '保留正文')
        self.assertEqual(d.table.rowCount(), 1)
        self.assertEqual(d.table.item(0, 0).text(), 'B')
        self.assertEqual(w.current_id, second)
        self.assertEqual(w.article_list.count(), 1)

    def test_cancel_save_failure_and_blank_area_keep_article(self):
        w = self.window
        w.new_article(); w.title.setText('A'); w.save()
        key = w.current_id
        d = self.dialog()
        with patch.object(QMenu, 'exec') as execute:
            d.show_article_menu(QPoint(-1, -1))
            execute.assert_not_called()
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.No):
            d.delete_article(key)
        self.assertIsNone(w.repository.get(key).deleted_at)
        with patch.object(w, 'save', return_value=False), patch.object(QMessageBox, 'question') as confirm:
            d.delete_article(key)
            confirm.assert_not_called()
        self.assertEqual(d.table.rowCount(), 1)
        self.assertIsNone(w.repository.get(key).deleted_at)

    def test_delete_current_article_clears_editor_and_is_restorable(self):
        w = self.window
        w.new_article(); w.title.setText('A'); w.editor.setPlainText('待保存正文')
        key = w.current_id
        d = self.dialog()
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes):
            d.delete_article(key)
        self.assertIsNone(w.current_id)
        self.assertEqual(d.table.rowCount(), 0)
        self.assertEqual(w.repository.get(key).body_text, '待保存正文')
        w.repository.set_deleted(key, False)
        d.refresh()
        self.assertEqual(d.table.rowCount(), 1)
