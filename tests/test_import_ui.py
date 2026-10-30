import unittest
from pathlib import Path
from unittest.mock import patch

import test_ui
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QMessageBox

from northdiary.models import ExportSelection
from northdiary.services.attachments import AttachmentService
from northdiary.services.epub import EpubExporter
from northdiary.storage.database import Database
from northdiary.storage.repository import ArticleRepository


class ImportWindowTests(unittest.TestCase):
    setUp = test_ui.WindowTests.setUp
    tearDown = test_ui.WindowTests.tearDown

    def book(self):
        database = Database(self.root / 'external')
        try:
            repo = ArticleRepository(database)
            attachments = AttachmentService(database)
            key = repo.create().id
            image = QImage(20, 20, QImage.Format.Format_RGB32)
            image.fill(0xff467954)
            path = self.root / 'photo.png'
            image.save(str(path))
            attachments.add(key, path)
            photo = attachments.list(key)[0]
            repo.save(key, '手机上的回忆', '2026-07-未知',
                      f'<p>海边 <b>粗体</b><a href="ndiary-image:{photo["id"]}">照片</a></p>',
                      '海边 粗体 照片', ['旅行'], ['夏天'], ['随手记'])
            destination = self.root / 'import.epub'
            EpubExporter(repo, attachments).export(ExportSelection((key,), '文集'), destination)
            return destination
        finally:
            database.close()

    def test_import_real_book_saves_current_edit_and_loads_photo_references(self):
        path = self.book()
        self.window.new_article()
        existing = self.window.current_id
        self.window.title.setText('本机未保存标题')
        self.window.editor.setPlainText('本机未保存正文')
        with patch('northdiary.ui.main_window.QFileDialog.getOpenFileName', return_value=(str(path), '')), \
             patch('northdiary.ui.main_window.QMessageBox.question', return_value=QMessageBox.StandardButton.Yes), \
             patch('northdiary.ui.main_window.QMessageBox.information') as success, \
             patch.object(self.window, 'fail') as fail:
            self.window.import_epub()
            success.assert_called_once()
            fail.assert_not_called()
        self.assertEqual(self.window.repository.get(existing).body_text, '本机未保存正文')
        self.assertEqual(self.window.current_id, existing)
        incoming = next(article for article in self.window.repository.list() if article.title == '手机上的回忆')
        self.window.load_article(incoming.id)
        self.assertEqual(self.window.date.text(), '2026-07-未知')
        self.assertEqual(self.window.image_list.count(), 1)
        photo = self.window.attachments.list(incoming.id)[0]
        self.assertTrue(self.window.editor.image_links(photo['id']))
        self.assertTrue((self.database.root / photo['relative_path']).is_file())
        self.assertEqual(self.window.repository.temporary_tags(incoming.id), ['随手记'])

    def test_file_cancel_and_confirmation_cancel_do_not_import(self):
        with patch('northdiary.ui.main_window.QFileDialog.getOpenFileName', return_value=('', '')), \
             patch('northdiary.ui.main_window.EpubImporter') as importer:
            self.window.import_epub()
            importer.assert_not_called()
        path = self.book()
        with patch('northdiary.ui.main_window.QFileDialog.getOpenFileName', return_value=(str(path), '')), \
             patch('northdiary.ui.main_window.QMessageBox.question', return_value=QMessageBox.StandardButton.No), \
             patch('northdiary.ui.main_window.QMessageBox.information') as success:
            self.window.import_epub()
            success.assert_not_called()
        self.assertEqual(self.window.repository.list(), [])

    def test_save_failure_stops_before_file_dialog(self):
        self.window.new_article()
        self.window.editor.setPlainText('保留正在编辑的内容')
        with patch.object(self.window.repository, 'save', side_effect=OSError('保存失败')), \
             patch.object(self.window, 'fail'), \
             patch('northdiary.ui.main_window.QFileDialog.getOpenFileName') as dialog:
            self.window.import_epub()
            dialog.assert_not_called()
        self.assertTrue(self.window.dirty)
        self.assertEqual(self.window.editor.toPlainText(), '保留正在编辑的内容')

    def test_corrupt_book_reports_failure_without_success(self):
        path = self.root / 'broken.epub'
        path.write_bytes(b'bad')
        with patch('northdiary.ui.main_window.QFileDialog.getOpenFileName', return_value=(str(path), '')), \
             patch.object(self.window, 'fail') as fail, \
             patch('northdiary.ui.main_window.QMessageBox.information') as success:
            self.window.import_epub()
            fail.assert_called_once()
            success.assert_not_called()
        self.assertEqual(self.window.repository.list(), [])

    def test_repeated_import_skips_without_confirmation_and_preserves_count(self):
        path = self.book()
        with patch('northdiary.ui.main_window.QFileDialog.getOpenFileName', return_value=(str(path), '')), \
             patch('northdiary.ui.main_window.QMessageBox.question', return_value=QMessageBox.StandardButton.Yes) as question, \
             patch('northdiary.ui.main_window.QMessageBox.information') as success:
            self.window.import_epub()
            self.assertEqual(len(self.window.repository.list()), 1)
            question.reset_mock()
            self.window.import_epub()
            question.assert_not_called()
            self.assertIn('跳过 1 篇', success.call_args.args[2])
        self.assertEqual(len(self.window.repository.list()), 1)
