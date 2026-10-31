import unittest, sqlite3
from unittest.mock import patch, Mock
from PySide6.QtCore import Qt, QDate, QMimeData
from PySide6.QtWidgets import QMessageBox
import test_ui
from northdiary.storage.database import Database
from northdiary.ui.main_window import MainWindow
from northdiary.ui.draft_list import DRAFT_MIME
from northdiary.ui.date_picker import DateDialog

class DraftFlowTests(unittest.TestCase):
    setUp=test_ui.WindowTests.setUp
    tearDown=test_ui.WindowTests.tearDown

    def test_new_keeps_category_and_stays_pending_until_checkmark(self):
        w=self.window;w.new_article();w.categories.setText('小学');w.title.setText('第一篇');w.save();first=w.current_id
        self.assertEqual(w.article_list.ids(),[]);self.assertEqual(w.draft_list.ids(),[first])
        w.selected_categories={'小学'};w.selected_tags={'生活'};w.refresh_filter_buttons()
        w.new_article();second=w.current_id
        self.assertEqual(w.selected_categories,{'小学'});self.assertEqual(w.selected_tags,{'生活'})
        w.selected_tags=None
        self.assertEqual(w.categories.text(),'小学')
        self.assertEqual(w.repository.labels(second,'categories'),['小学'])
        self.assertEqual(w.article_list.ids(),[]);self.assertEqual(w.draft_list.ids(),[first,second])
        w.title.setText('第二篇');w.editor.setPlainText('待确认也要保存');w.save()
        row=w.draft_list.itemWidget(w.draft_list.item(1));test_ui.APP.processEvents()
        self.assertGreaterEqual(row.label.height(),row.label.fontMetrics().lineSpacing()*2)
        row.confirm.click()
        self.assertEqual(w.article_list.ids(),[second]);self.assertEqual(w.draft_list.ids(),[first])
        self.assertEqual(w.repository.get(second).body_text,'待确认也要保存')
        self.assertEqual(w.repository.labels(second,'categories'),['小学'])

    def test_pending_survives_restart_and_export_list_excludes_it(self):
        w=self.window;w.new_article();key=w.current_id;w.editor.setPlainText('关闭后保留');w.save();w.close()
        again=Database(w.database.root)
        try:
            reopened=MainWindow(again)
            self.assertEqual(reopened.draft_list.ids(),[key]);self.assertEqual(reopened.article_list.ids(),[])
            self.assertEqual(reopened.repository.list(),[])
            self.assertEqual(reopened.repository.get(key).body_text,'关闭后保留')
            reopened.close()
        finally:again.close()

    def test_failed_save_does_not_confirm_or_discard_edit(self):
        w=self.window;w.new_article();key=w.current_id;w.editor.setPlainText('不能丢失')
        with patch.object(w.repository,'save',side_effect=OSError('disk')),patch.object(w,'fail'):
            self.assertFalse(w.confirm_article(key))
        self.assertTrue(w.repository.is_draft(key));self.assertEqual(w.article_list.ids(),[])
        self.assertEqual(w.editor.toPlainText(),'不能丢失')

    def test_drop_from_pending_into_upper_list_confirms(self):
        w=self.window;w.new_article();key=w.current_id
        payload=QMimeData();payload.setData(DRAFT_MIME,key.encode('ascii'))
        event=Mock();event.source.return_value=w.draft_list;event.mimeData.return_value=payload
        w.article_list.dragEnterEvent(event);event.acceptProposedAction.assert_called_once()
        event.reset_mock();w.article_list.dropEvent(event)
        self.assertFalse(w.repository.is_draft(key));self.assertEqual(w.article_list.ids(),[key]);self.assertEqual(w.draft_list.ids(),[])
        event.acceptProposedAction.assert_called_once()

    def test_trash_restore_preserves_pending_state(self):
        w=self.window;w.new_article();key=w.current_id;w.save()
        w.repository.set_deleted(key)
        self.assertEqual([a.id for a in w.repository.list(trash=True)],[key])
        w.repository.set_deleted(key,False);w.refresh_list()
        self.assertEqual(w.draft_list.ids(),[key]);self.assertEqual(w.article_list.ids(),[])

    def test_pending_creation_rolls_back_if_category_reference_fails(self):
        repo=self.window.repository;db=repo.db;before=db.execute('select count(*) from articles').fetchone()[0]
        db.execute("CREATE TRIGGER reject_new_category BEFORE INSERT ON article_categories BEGIN SELECT RAISE(ABORT,'test'); END")
        with self.assertRaises(sqlite3.IntegrityError):repo.create(draft=True,categories=['新分类'])
        self.assertEqual(db.execute('select count(*) from articles').fetchone()[0],before)
        self.assertEqual(db.execute('select count(*) from draft_articles').fetchone()[0],0)
        self.assertNotIn('新分类',repo.categories())

    def test_v6_migration_keeps_existing_articles_confirmed(self):
        root=self.root/'v6';old=Database(root);from northdiary.storage.repository import ArticleRepository
        key=ArticleRepository(old).create().id
        old.connection.executescript('DROP TABLE draft_articles; PRAGMA user_version=6;');old.close()
        again=Database(root)
        try:
            repo=ArticleRepository(again);self.assertEqual([a.id for a in repo.list()],[key]);self.assertFalse(repo.is_draft(key))
            self.assertTrue(list((root/'backups').glob('before-v7-*.sqlite3')))
        finally:again.close()

    def test_year_month_triangles_and_partial_date_boundaries(self):
        dialog=DateDialog(QDate(2024,2,29),allow_partial=True)
        dialog.choose_unknown('month');dialog.year_previous.click()
        self.assertEqual(dialog.shown,QDate(2023,2,1));self.assertEqual(dialog.input.text(),'2023-02-未知')
        dialog.year_following.click();self.assertEqual(dialog.shown.year(),2024)
        dialog.year.setValue(2000);dialog.month.setCurrentIndex(0);dialog.month_previous.click()
        self.assertEqual(dialog.shown,QDate(1999,12,1))
        dialog.year.setValue(1753);dialog.month.setCurrentIndex(0)
        self.assertFalse(dialog.year_previous.isEnabled());self.assertFalse(dialog.month_previous.isEnabled())
        self.assertTrue(dialog.year_following.autoRepeat());dialog.reject()
