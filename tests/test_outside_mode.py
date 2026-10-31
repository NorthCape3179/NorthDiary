import unittest
from unittest.mock import patch
from contextlib import closing
import sqlite3
from PySide6.QtCore import Qt, QPoint
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QMessageBox
import test_ui
from northdiary.ui.label_filter_dialog import LabelFilterDialog, filter_articles
from northdiary.ui.overview_dialog import OverviewDialog
from northdiary.storage.repository import ArticleRepository
from northdiary.storage.database import Database
from northdiary.services.epub import EpubExporter
from northdiary.services.importing import EpubImporter
from northdiary.services.attachments import AttachmentService
from northdiary.models import ExportSelection

class OutsideModeTests(unittest.TestCase):
    setUp = test_ui.WindowTests.setUp
    tearDown = test_ui.WindowTests.tearDown

    def test_independent_groups_create_move_restart_and_hidden_controls(self):
        w=self.window;w.new_article(); w.confirm_article(w.current_id);w.title.setText('时间线里');w.save();inside=w.current_id
        self.assertTrue(w.set_space(True));w.new_article(); w.confirm_article(w.current_id);w.title.setText('时间线外');w.save();outside=w.current_id
        self.assertEqual([a.id for a in w.repository.list()],[outside])
        self.assertTrue(w.timeline.isHidden());self.assertTrue(w.people_archive_button.isHidden());self.assertTrue(w.timeline_overview_button.isHidden())
        self.assertEqual(w.space_button.text(),'时间线之内')
        w.preview.setChecked(True);self.assertTrue(w.reading_nav.isHidden())
        w.set_space(False)
        self.assertEqual([a.id for a in w.repository.list()],[inside])
        self.assertFalse(w.timeline.isHidden())
        again=Database(w.database.root)
        try:
            repo=ArticleRepository(again);repo.outside=True
            self.assertEqual([a.id for a in repo.list()],[outside])
        finally:again.close()
        w.move_article_space(inside)
        self.assertEqual(w.repository.list(),[])
        w.set_space(True);self.assertEqual({a.id for a in w.repository.list()},{inside,outside})

    def test_checkbox_filter_union_and_intersection_and_no_selection(self):
        w=self.window
        ids=[]
        for title,cat,tag in [('A','小学','生活'),('B','初中','生活'),('C','初中','读书')]:
            w.new_article(); w.confirm_article(w.current_id);w.title.setText(title);w.categories.setText(cat);w.tags.add_tag(tag);w.save();ids.append(w.current_id)
        rows=w.repository.list()
        self.assertEqual({a.id for a in filter_articles(w.repository,rows,{'小学','初中'},{'生活'})},set(ids[:2]))
        self.assertEqual(filter_articles(w.repository,rows,set(),None),[])
        dialog=LabelFilterDialog(w,'categories',{'小学'})
        self.assertEqual(dialog.selection(),{'小学'})
        dialog.check_all(False);self.assertEqual(dialog.selection(),set());dialog.close()
        w.selected_categories={'小学'};w.selected_tags={'生活'};w.refresh_list()
        self.assertEqual(w.article_list.ids(),ids[:1])
        self.assertEqual(w.category_filter_button.width(),w.tag_filter_button.width())

    def test_right_click_dropdown_uses_definition_menu_without_selecting(self):
        w=self.window;w.new_article(); w.confirm_article(w.current_id);w.tags.add_tag('测试右键');w.save();combo=w.tags.combo
        combo.showPopup();test_ui.APP.processEvents()
        index=combo.model().index(combo.findData('测试右键'),0)
        point=combo.view().visualRect(index).center()
        with patch('northdiary.ui.definition_menu.menu') as menu:
            QTest.mouseClick(combo.view().viewport(),Qt.MouseButton.RightButton,pos=point)
            self.assertEqual(menu.call_count,1)
            self.assertEqual(menu.call_args.args[2],'测试右键')
        self.assertEqual(combo.currentIndex(),0)
        self.assertIn('测试右键',w.repository.tags())

    def test_overview_switch_is_local_and_lists_selected_group(self):
        w=self.window;w.new_article(); w.confirm_article(w.current_id);w.title.setText('内');w.save();inside=w.current_id
        w.set_space(True);w.new_article(); w.confirm_article(w.current_id);w.title.setText('外');w.save();outside=w.current_id;w.set_space(False)
        dialog=OverviewDialog(w.repository,[('标题','title')],'title',w)
        self.assertEqual(dialog.table.item(0,0).data(Qt.ItemDataRole.UserRole),inside)
        dialog.toggle_space()
        self.assertEqual(dialog.table.item(0,0).data(Qt.ItemDataRole.UserRole),outside)
        self.assertFalse(w.repository.outside)
        self.assertTrue(dialog.table.isColumnHidden(2));dialog.close()

    def test_outside_epub_roundtrip_and_repeated_import(self):
        w=self.window;w.set_space(True);w.new_article(); w.confirm_article(w.current_id);w.title.setText('外部文章');w.editor.setPlainText('正文');w.save();key=w.current_id
        book=self.root/'outside.epub'
        EpubExporter(w.repository,w.attachments).export(ExportSelection((key,),'文集'),book)
        target=Database(self.root/'roundtrip')
        try:
            repo=ArticleRepository(target);importer=EpubImporter(repo,AttachmentService(target))
            result=importer.apply(importer.prepare(book))
            self.assertEqual(result.imported,1);self.assertEqual(repo.list(),[])
            repo.outside=True;self.assertEqual(len(repo.list()),1)
            self.assertEqual(importer.prepare(book).skipped_count,1)
        finally:target.close()

    def test_export_popup_opens_above_button(self):
        button=self.window.export_button;button.toggle_menu();test_ui.APP.processEvents()
        self.assertTrue(button.panel.isVisible())
        self.assertLess(button.panel.geometry().bottom(),button.mapToGlobal(QPoint(0,0)).y())
        button.panel.hide()

    def test_v5_migration_keeps_existing_articles_inside_and_backs_up(self):
        path=self.root/'v5-data';old=Database(path);repo=ArticleRepository(old);key=repo.create().id
        with old.connection:
            old.connection.executescript('DROP TABLE outside_articles; PRAGMA user_version=5;')
        old.close()
        migrated=Database(path)
        try:
            repo=ArticleRepository(migrated)
            self.assertEqual([a.id for a in repo.list()],[key])
            self.assertFalse(repo.is_outside(key))
            self.assertEqual(migrated.connection.execute('PRAGMA user_version').fetchone()[0],7)
            snapshots=list((path/'backups').glob('before-v6-*.sqlite3'))
            self.assertTrue(snapshots)
        finally:migrated.close()
