import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from northdiary.storage.database import Database
from northdiary.storage.repository import ArticleRepository
from northdiary.services.attachments import AttachmentService
from northdiary.services.epub import EpubExporter
from northdiary.ui.export_dialog import ExportDialog


APP = QApplication.instance() or QApplication([])


class ExportSelectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.temp.name) / 'data')
        self.repo = ArticleRepository(self.db)
        self.articles = []
        for title, categories, tags, temporary in (
            ('第一篇', ['校园', '旅行'], ['回忆'], ['夏日']),
            ('第二篇', ['校园'], ['日常'], []),
            ('第三篇', ['旅行'], ['回忆'], ['回忆']),
        ):
            article = self.repo.create()
            self.repo.save(article.id, title, '2026-11-01', f'<p>{title}</p>', title,
                           categories, tags, temporary)
            self.articles.append(self.repo.get(article.id))
        self.dialog = ExportDialog(self.articles, repository=self.repo)
        self.dialog.show()
        APP.processEvents()

    def tearDown(self):
        self.dialog.close()
        self.db.close()
        self.temp.cleanup()

    def choose(self, button, name):
        next(a for a in button.menu().actions() if a.data() == name).trigger()

    def test_category_tag_and_temporary_tag_replace_selection(self):
        first, second, third = (a.id for a in self.articles)
        self.choose(self.dialog.category_button, '校园')
        self.assertEqual(self.dialog.selection().article_ids, (first, second))
        self.choose(self.dialog.tag_button, '回忆')
        self.assertEqual(self.dialog.selection().article_ids, (first, third))
        self.choose(self.dialog.tag_button, '夏日')
        self.assertEqual(self.dialog.selection().article_ids, (first,))
        self.assertEqual(self.dialog.selection_count.text(), '已选择 1 / 3 篇')
        self.dialog.chapters.item(1).setCheckState(Qt.CheckState.Checked)
        self.assertEqual(self.dialog.selection_count.text(), '已选择 2 / 3 篇')

    def test_clear_all_validation_and_select_all(self):
        QTest.mouseClick(self.dialog.clear_selection_button, Qt.MouseButton.LeftButton)
        self.assertEqual(self.dialog.selection().article_ids, ())
        self.dialog.accept()
        self.assertNotEqual(self.dialog.result(), self.dialog.DialogCode.Accepted)
        self.assertTrue(self.dialog.error.text())
        QTest.mouseClick(self.dialog.select_all_button, Qt.MouseButton.LeftButton)
        self.assertEqual(self.dialog.selection().article_ids, tuple(a.id for a in self.articles))
        self.assertEqual(self.dialog.selection_count.text(), '已选择 3 / 3 篇')

    def test_group_selection_preserves_reordered_epub_chapters(self):
        self.dialog.chapters.setCurrentRow(2)
        self.dialog.move_chapter(-1)
        self.dialog.move_chapter(-1)
        self.choose(self.dialog.tag_button, '回忆')
        self.assertEqual(self.dialog.selection().article_ids, (self.articles[2].id, self.articles[0].id))
        destination = Path(self.temp.name) / 'selected.epub'
        EpubExporter(self.repo, AttachmentService(self.db)).export(self.dialog.selection(), destination)
        with ZipFile(destination) as archive:
            self.assertIn('第三篇', archive.read('EPUB/chapter-1.xhtml').decode())
            self.assertIn('第一篇', archive.read('EPUB/chapter-2.xhtml').decode())
            self.assertNotIn('EPUB/chapter-3.xhtml', archive.namelist())

    def test_menus_only_include_available_articles_and_empty_dialog(self):
        excluded = self.repo.create(draft=True)
        self.repo.save(excluded.id, '待写', '2026-11-01', '', '', ['不应出现'], ['不应出现'])
        deleted = self.repo.create()
        self.repo.save(deleted.id, '已删除', '2026-11-01', '', '', ['不应出现'], ['不应出现'])
        self.repo.set_deleted(deleted.id)
        scoped = ExportDialog(self.repo.list(), repository=self.repo)
        try:
            self.assertNotIn('不应出现', [a.data() for a in scoped.category_button.menu().actions()])
            self.assertNotIn('不应出现', [a.data() for a in scoped.tag_button.menu().actions()])
            self.assertEqual(len(scoped.selection().article_ids), 3)
        finally:
            scoped.close()
        empty = ExportDialog([], repository=self.repo)
        try:
            self.assertFalse(empty.category_button.isEnabled())
            self.assertFalse(empty.tag_button.isEnabled())
            empty.clear_selection_button.click()
            self.assertEqual(empty.selection_count.text(), '已选择 0 / 0 篇')
        finally:
            empty.close()
