import unittest
from unittest.mock import patch
from zipfile import ZipFile
from PySide6.QtCore import Qt
import test_ui
from northdiary.ui.export_dialog import ExportDialog


class EpubWindowTests(unittest.TestCase):
    setUp = test_ui.WindowTests.setUp
    tearDown = test_ui.WindowTests.tearDown

    def test_epub_export_saves_pending_qt_html_and_selection_order(self):
            self.window.new_article()
            first = self.window.current_id
            self.window.title.setText('第一篇')
            self.window.editor.setHtml('<p><b>真实 Qt 粗体</b> &amp; 中文</p>')
            self.window.new_article()
            second = self.window.current_id
            self.window.title.setText('第二篇最新标题')
            self.window.editor.setPlainText('尚未自动保存的正文')
            dialog = ExportDialog([self.window.repository.get(first), self.window.repository.get(second)])
            dialog.chapters.setCurrentRow(1)
            dialog.move_chapter(-1)
            self.assertEqual(dialog.selection().article_ids, (second, first))
            destination = self.root / 'book.epub'
            with patch('northdiary.ui.main_window.ExportDialog', return_value=dialog), \
                 patch.object(dialog, 'exec', return_value=dialog.DialogCode.Accepted), \
                 patch('northdiary.ui.main_window.QFileDialog.getSaveFileName', return_value=(str(destination), '')), \
                 patch('northdiary.ui.main_window.QMessageBox.information'):
                self.window.export_epub()
            with ZipFile(destination) as archive:
                first_chapter = archive.read('EPUB/chapter-1.xhtml').decode()
                self.assertIn('第二篇最新标题', first_chapter)
                self.assertIn('尚未自动保存的正文', first_chapter)
                self.assertIn('<strong>真实 Qt 粗体</strong>', archive.read('EPUB/chapter-2.xhtml').decode())
            self.assertFalse(self.window.dirty)

    def test_epub_dialog_checkboxes_validation_and_cancel(self):
            self.window.new_article()
            dialog = ExportDialog(self.window.repository.list())
            dialog.chapters.item(0).setCheckState(Qt.CheckState.Unchecked)
            self.assertEqual(dialog.selection().article_ids, ())
            dialog.accept()
            self.assertNotEqual(dialog.result(), dialog.DialogCode.Accepted)
            self.assertTrue(dialog.error.text())
            dialog.chapters.item(0).setCheckState(Qt.CheckState.Checked)
            dialog.title.clear()
            dialog.accept()
            self.assertNotEqual(dialog.result(), dialog.DialogCode.Accepted)
            with patch('northdiary.ui.main_window.ExportDialog', return_value=dialog), \
                 patch.object(dialog, 'exec', return_value=dialog.DialogCode.Rejected), \
                 patch('northdiary.ui.main_window.QFileDialog.getSaveFileName') as save_dialog:
                self.window.export_epub()
                save_dialog.assert_not_called()

    def test_epub_export_stops_on_save_failure_and_reports_export_failure(self):
            self.window.new_article()
            self.window.editor.setPlainText('必须保留')
            with patch.object(self.window.repository, 'save', side_effect=OSError('不可写')), \
                 patch.object(self.window, 'fail'), \
                 patch('northdiary.ui.main_window.ExportDialog') as dialog_factory:
                self.window.export_epub()
                dialog_factory.assert_not_called()
                self.assertTrue(self.window.dirty)
                self.assertEqual(self.window.editor.toPlainText(), '必须保留')
            dialog = ExportDialog(self.window.repository.list())
            with patch('northdiary.ui.main_window.ExportDialog', return_value=dialog), \
                 patch.object(dialog, 'exec', return_value=dialog.DialogCode.Accepted), \
                 patch('northdiary.ui.main_window.QFileDialog.getSaveFileName', return_value=(str(self.root / 'book.epub'), '')), \
                 patch('northdiary.ui.main_window.EpubExporter.export', side_effect=ValueError('图片缺失')), \
                 patch.object(self.window, 'fail') as fail, \
                 patch('northdiary.ui.main_window.QMessageBox.information') as success:
                self.window.export_epub()
                fail.assert_called_once()
                success.assert_not_called()
