import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog

from northdiary.storage.database import Database
from northdiary.storage.repository import ArticleRepository
from northdiary.ui.ai_sources import ArticleSelectionDialog, ArticleSources, RequestPreviewDialog
from northdiary.ui.main_window import MainWindow


APP = QApplication.instance() or QApplication([])
APP.setStyle('Fusion')


class StudioTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.temp.name) / 'data')
        self.repo = ArticleRepository(self.db)
        self.first = self.article('原文一', '只允许发送这一段', '生活', '晴天')
        self.repo.outside = True
        self.second = self.article('时间线外的文章', '另一篇私人内容', '随笔', '晴天')
        self.trash = self.article('回收站', '不可发送')
        self.repo.set_deleted(self.trash.id)
        self.draft = self.repo.create(draft=True)
        self.window = MainWindow(self.db)
        self.window.show()
        APP.processEvents()
        self.studio = self.window.ai_studio

    def article(self, title, body, category='', tag=''):
        article = self.repo.create()
        self.repo.save(article.id, title, '2026-10-01', '<p>' + body + '</p>', body,
                       [category] if category else [], [tag] if tag else [])
        return self.repo.get(article.id)

    def tearDown(self):
        self.window.dirty = False
        self.window.close()
        APP.processEvents()
        self.db.close()
        self.temp.cleanup()

    def test_metadata_listing_and_only_selected_bodies_resolved(self):
        sources = ArticleSources(self.db)
        statements = []
        self.db.connection.set_trace_callback(statements.append)
        rows = sources.list()
        self.assertEqual({a.id for a in rows}, {self.first.id, self.second.id})
        self.assertTrue(all(a.text == '' for a in rows))
        self.assertTrue(all('body_text' not in sql.lower() for sql in statements))
        statements.clear()
        resolved = sources.resolve([self.first.id, self.first.id, self.trash.id, self.draft.id])
        self.assertEqual([a.id for a in resolved], [self.first.id])
        self.assertEqual(resolved[0].text, '只允许发送这一段')
        self.assertFalse(any(self.second.id in sql for sql in statements))
        self.db.connection.set_trace_callback(None)

    def test_selection_across_filters_cancel_and_clear(self):
        dialog = ArticleSelectionDialog(self.db, parent=self.studio)
        try:
            item = next(dialog.list.item(i) for i in range(dialog.list.count())
                        if dialog.list.item(i).data(Qt.ItemDataRole.UserRole) == self.first.id)
            item.setCheckState(Qt.CheckState.Checked)
            dialog.space.setCurrentIndex(2)
            self.assertEqual(dialog.list.count(), 1)
            dialog.list.item(0).setCheckState(Qt.CheckState.Checked)
            dialog.search.setText('没有匹配')
            self.assertEqual(dialog.list.count(), 0)
            self.assertEqual(set(dialog.selected), {self.first.id, self.second.id})
            dialog.search.clear()
            dialog.confirm_selection()
            self.assertEqual(set(dialog.article_ids), {self.first.id, self.second.id})
            self.assertEqual(self.studio.article_ids, ())
            dialog.clear_selection()
            self.assertFalse(dialog.selected)
        finally:
            dialog.close()
            dialog.deleteLater()

    def test_full_workspace_switch_preserves_diary_and_guards_save_failure(self):
        self.window.load_article(self.first.id)
        self.window.editor.setPlainText('尚未保存的原文')
        with patch.object(self.window.repository, 'save', side_effect=OSError('无法保存')), patch.object(self.window, 'fail'):
            self.assertFalse(self.window.set_studio(True))
            self.assertIs(self.window.workspace_stack.currentWidget(), self.window.splitter)
            self.assertTrue(self.window.dirty)
        self.assertTrue(self.window.set_studio(True))
        self.assertEqual(self.repo.get(self.first.id).body_text, '尚未保存的原文')
        self.assertIs(self.window.workspace_stack.currentWidget(), self.studio)
        self.assertTrue(all(not action.isEnabled() for action in self.window.diary_actions))
        self.studio.navigate('writing')
        self.studio.tools['writing']['prompt'].setPlainText('保留细节')
        self.window.set_studio(False)
        self.assertEqual(self.window.current_id, self.first.id)
        self.window.set_studio(True)
        self.assertEqual(self.studio.current_page, 'writing')
        self.assertEqual(self.studio.tools['writing']['prompt'].toPlainText(), '保留细节')

    def test_preview_refreshes_selected_content_excludes_trash_and_has_instruction(self):
        self.studio.set_articles([self.first.id, self.second.id])
        self.repo.set_deleted(self.second.id)
        self.repo.save(self.first.id, '更新标题', '2026-10-02', '<p>更新正文</p>', '更新正文', [], [])
        self.studio.navigate('analysis')
        self.studio.tools['analysis']['prompt'].setPlainText('仅整理时间顺序')
        captured = {}

        def preview_exec(dialog):
            captured['ids'] = [a.id for a in dialog.articles]
            dialog.list.setCurrentRow(1)
            captured['body'] = dialog.body.toPlainText()
            dialog.list.setCurrentRow(0)
            captured['instruction'] = dialog.body.toPlainText()
            return QDialog.DialogCode.Accepted

        with patch.object(RequestPreviewDialog, 'exec', preview_exec):
            self.studio.preview_request()
        self.assertEqual(captured['ids'], [self.first.id])
        self.assertIn('更新正文', captured['body'])
        self.assertIn('仅整理时间顺序', captured['instruction'])
        self.assertIn('事实、推测和未知信息', captured['instruction'])
        self.assertEqual(self.studio.article_ids, (self.first.id,))

    def test_open_original_restores_correct_diary_space_and_keeps_ai_tables(self):
        self.window.set_studio(True)
        self.studio.set_articles([self.second.id])
        self.studio.open_source()
        self.assertIs(self.window.workspace_stack.currentWidget(), self.window.splitter)
        self.assertTrue(self.window.outside)
        self.assertEqual(self.window.current_id, self.second.id)
        tables = [r[0] for r in self.db.connection.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        self.assertEqual({name for name in tables if name.startswith('ai_')}, {'ai_conversations', 'ai_turns', 'ai_works', 'ai_work_versions'})
        self.assertTrue(self.studio.api_key.isEnabled())
        self.assertEqual(self.studio.api_key.text(), '')


if __name__ == '__main__':
    unittest.main()
