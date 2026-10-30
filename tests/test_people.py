import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from contextlib import closing
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QTextCursor, QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton, QDialog, QMessageBox
from northdiary.models import ExportSelection
from northdiary.services.attachments import AttachmentService
from northdiary.services.epub import EpubExporter
from northdiary.services.importing import EpubImporter
from northdiary.services.native_format import MANIFEST_PATH
from northdiary.storage.database import Database, SCHEMA_VERSION
from northdiary.storage.repository import ArticleRepository
from northdiary.storage.people import PeopleRepository
from northdiary.ui.main_window import MainWindow
from northdiary.ui.people_dialog import PeopleDialog, PersonEditor

APP = QApplication.instance() or QApplication([])


class PeopleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        self.db = Database(self.root/'data'); self.repo = ArticleRepository(self.db)
        self.people = PeopleRepository(self.db)
        self.article = self.repo.create()
        self.person = self.people.create('小明', '@M', birth_date='2000-02-29', met_date='2020-未知-未知', met_how='同学')
        self.windows = []

    def tearDown(self):
        for window in reversed(self.windows):
            if isinstance(window, MainWindow): window.dirty = False
            window.close(); window.deleteLater()
        APP.processEvents(); self.db.close(); self.temp.cleanup()

    def link(self, keys=None):
        self.repo.save(self.article.id, '相遇', '2026-10-30', '<p>hello</p>', 'hello', [], [], people=keys or [self.person['id']])

    def window(self):
        win = MainWindow(self.db); self.windows.append(win); win.show(); APP.processEvents(); return win

    def dialog(self, **kw):
        dialog = PeopleDialog(self.db, **kw); self.windows.append(dialog); dialog.show(); APP.processEvents(); return dialog

    def export(self, ids=None):
        path = self.root/'people.epub'
        EpubExporter(self.repo, AttachmentService(self.db)).export(ExportSelection(tuple(ids or [self.article.id]), '人物回忆'), path)
        return path

    def test_migration_v3_backup_and_restart(self):
        self.link(); root = self.root/'legacy'; root.mkdir()
        self.db.connection.commit()
        with closing(sqlite3.connect(root/'northdiary.sqlite3')) as conn:
            self.db.connection.backup(conn)
            conn.executescript('DROP TABLE person_relationship_tags; DROP TABLE person_temporary_relationship_tags; DROP TABLE relationship_tags; DROP TABLE article_people; DROP TABLE people; PRAGMA user_version=3;')
        migrated = Database(root)
        self.assertEqual(migrated.connection.execute('PRAGMA user_version').fetchone()[0], SCHEMA_VERSION)
        self.assertEqual(ArticleRepository(migrated).get(self.article.id).title, '相遇')
        self.assertEqual(PeopleRepository(migrated).list(), [])
        migrated.close()
        snapshots = list((root/'backups').glob('before-v4-*.sqlite3'))
        self.assertEqual(len(snapshots), 1)
        with closing(sqlite3.connect(snapshots[0])) as conn: self.assertEqual(conn.execute('PRAGMA user_version').fetchone()[0], 3)
        again = Database(root); again.close()
        self.assertEqual(len(list((root/'backups').glob('before-v4-*.sqlite3'))), 1)

    def test_stable_link_rename_search_pin_star_delete_preserves_article(self):
        self.link(); person = dict(self.person); person.update(name='新名字', code='@NEW', pinned=1, starred=1)
        self.people.save(person)
        self.assertEqual(self.people.articles(person['id'])[0].id, self.article.id)
        self.assertEqual(self.people.for_article(self.article.id)[0]['code'], '@NEW')
        self.assertEqual(self.people.list('new')[0]['name'], '新名字')
        self.repo.set_deleted(self.article.id); self.assertEqual(self.people.articles(person['id']), [])
        self.repo.set_deleted(self.article.id, False)
        self.people.delete(person['id'])
        self.assertEqual(self.repo.get(self.article.id).body_text, 'hello')
        self.assertEqual(self.people.for_article(self.article.id), [])

    def test_invalid_person_and_duplicate_code_do_not_overwrite(self):
        for values in ({'birth_date':'2001-02-29'}, {'met_date':'2020-未知-02'}, {'name':''}, {'code':''}):
            with self.subTest(values=values), self.assertRaises(ValueError): self.people.save(dict(self.person, **values))
        with self.assertRaises(sqlite3.IntegrityError): self.people.create('其他人', '@M')
        self.assertEqual(len(self.people.list()), 1)
        self.assertEqual(self.people.get(self.person['id']), self.person)

    def test_article_and_people_save_are_atomic(self):
        self.link()
        with self.assertRaises(sqlite3.IntegrityError):
            self.repo.save(self.article.id, '不应保存', '2026-10-30', '', '', [], [], people=['missing'])
        self.assertEqual(self.repo.get(self.article.id).title, '相遇')
        self.assertEqual(self.people.for_article(self.article.id)[0]['id'], self.person['id'])
        self.repo.save(self.article.id, '普通保存', '2026-10-30', '', '', [], [])
        self.assertEqual(len(self.people.for_article(self.article.id)), 1)

    def test_picker_theme_selection_search_chips_two_rows_and_cancel(self):
        for i in range(24): self.people.create('人物'+str(i), '@'+str(i))
        dialog = self.dialog(selected=[])
        keys = list(dialog.cards)
        for key in keys: dialog.toggle(key)
        self.assertEqual(len(dialog.selected), 25)
        self.assertTrue(dialog.cards[keys[0]].isChecked())
        self.assertEqual(dialog.chip_grid.getItemPosition(8)[:2], (0, 4))
        APP.processEvents()
        self.assertGreater(dialog.chips.width(), dialog.selected_scroll.viewport().width())
        dialog.search.setText('@M'); self.assertEqual(len(dialog.cards), 1)
        self.assertEqual(len(dialog.selected), 25)
        dialog.toggle(self.person['id']); self.assertFalse(dialog.cards[self.person['id']].isChecked())
        dialog.reject(); self.assertEqual(self.people.for_article(self.article.id), [])

    def test_editor_failed_save_keeps_fields(self):
        editor = PersonEditor(self.people, self.person); self.windows.append(editor)
        editor.fields['code'].setText('')
        editor.save(); self.assertEqual(editor.result(), QDialog.DialogCode.Rejected)
        self.assertTrue(editor.error.text()); self.assertEqual(editor.fields['name'].text(), '小明')
        editor.fields['code'].setText('@NEW'); editor.save()
        self.assertEqual(self.people.get(self.person['id'])['code'], '@NEW')

    def test_profile_detail_buttons_flags_related_events(self):
        self.link(); dialog = self.dialog(); dialog.activate(self.person['id'])
        self.assertEqual(dialog.stack.currentWidget(), dialog.detail)
        dialog.set_flag('starred'); self.assertEqual(self.people.get(self.person['id'])['starred'], 1)
        dialog.set_flag('pinned'); self.assertEqual(self.people.list()[0]['pinned'], 1)
        dialog.back(); self.assertTrue(dialog.cards[self.person['id']].person['starred'])
        dialog.show_person(self.person['id'])
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes): dialog.delete_person()
        self.assertEqual(self.people.list(), []); self.assertEqual(len(self.repo.list()), 1)

    def test_shortcuts_insert_at_cursor_without_label_or_html_and_readonly_blocks(self):
        win = self.window(); win.load_article(self.article.id)
        win.editor.setPlainText('前后'); cursor = win.editor.textCursor(); cursor.setPosition(1); win.editor.setTextCursor(cursor)
        win.people_expand.setChecked(True); APP.processEvents()
        self.assertTrue(win.people_shortcuts.isVisible())
        self.assertEqual(win.shortcut_grid.count(), 1)
        QTest.mouseClick(win.shortcut_grid.itemAtPosition(0, 0).widget(), Qt.MouseButton.LeftButton)
        self.assertEqual(win.editor.toPlainText(), '前@M后'); self.assertEqual(win.person_ids, [])
        self.assertTrue(win.save()); win.preview.setChecked(True); win.toggle_preview()
        win.insert_person_code('NO'); self.assertNotIn('NO', win.editor.toPlainText())
        self.assertFalse(win.shortcut_body.isEnabled()); self.assertFalse(win.people_button.isEnabled())

    def test_picker_accept_save_restart_and_failure_retains_pending_selection(self):
        win = self.window(); win.load_article(self.article.id)
        def pick(dialog):
            dialog.selected = [self.person['id']]; return QDialog.DialogCode.Accepted
        with patch.object(PeopleDialog, 'exec', pick): win.pick_people()
        self.assertEqual(self.people.for_article(self.article.id)[0]['id'], self.person['id'])
        win.load_article(self.article.id); self.assertEqual(win.person_ids, [self.person['id']])
        win.person_ids = []; win.mark_dirty()
        with patch.object(win.repository, 'save', side_effect=OSError('disk')), patch.object(win, 'fail'):
            self.assertFalse(win.save(True)); self.assertTrue(win.dirty); self.assertEqual(win.person_ids, [])
        self.assertTrue(win.save()); self.assertEqual(self.people.for_article(self.article.id), [])

    def test_epub_roundtrip_shared_people_unselected_excluded_repeat_skip(self):
        self.link(); second = self.repo.create()
        self.repo.save(second.id, '再次相遇', '2026-10-30', '', '', [], [], people=[self.person['id']])
        self.people.create('不应导出', '@SECRET')
        path = self.export([self.article.id, second.id])
        from northdiary.services.github_sync import validate_package
        validate_package(path.read_bytes())
        with ZipFile(path) as book:
            manifest = json.loads(book.read(MANIFEST_PATH)); self.assertEqual(manifest['version'], 3)
            self.assertEqual(len(manifest['articles'][0]['people']), 1)
        db = Database(self.root/'other')
        try:
            repo = ArticleRepository(db); importer = EpubImporter(repo, AttachmentService(db))
            result = importer.import_file(path); self.assertEqual(result.imported, 2)
            people = PeopleRepository(db); self.assertEqual(people.list(), [self.person])
            self.assertEqual(len(people.articles(self.person['id'])), 2)
            self.assertEqual(importer.import_file(path).skipped, 2)
        finally: db.close()

    def test_import_person_conflict_preserves_local_profile_and_reuses_copy(self):
        self.link(); second = self.repo.create()
        self.repo.save(second.id, '第二篇', '2026-10-30', '', '', [], [], people=[self.person['id']])
        path = self.export([self.article.id, second.id]); db = Database(self.root/'other')
        try:
            people = PeopleRepository(db); local = dict(self.person, name='本机人物'); people.save(local)
            importer = EpubImporter(ArticleRepository(db), AttachmentService(db)); importer.import_file(path)
            self.assertEqual(people.get(local['id']), local)
            self.assertEqual(len(people.list()), 2)
            copied = [p for p in people.list() if p['id'] != local['id']][0]
            self.assertNotEqual(copied['code'], local['code']); self.assertEqual(len(people.articles(copied['id'])), 2)
        finally: db.close()

    def test_import_failure_rolls_back_people_and_article_links(self):
        self.link(); path = self.export(); db = Database(self.root/'other')
        try:
            db.connection.executescript("CREATE TRIGGER reject_people BEFORE INSERT ON article_people BEGIN SELECT RAISE(ABORT, 'disk'); END;")
            importer = EpubImporter(ArticleRepository(db), AttachmentService(db))
            with self.assertRaises(sqlite3.IntegrityError): importer.import_file(path)
            self.assertEqual(ArticleRepository(db).list(), [])
            self.assertEqual(PeopleRepository(db).list(), [])
            self.assertEqual(db.connection.execute('SELECT COUNT(*) FROM article_people').fetchone()[0], 0)
        finally: db.close()

    def test_theme_and_quick_grid_two_columns_selection_saved_on_close(self):
        for i in range(5): self.people.create('人物'+str(i), '@'+str(i))
        win = self.window(); win.load_article(self.article.id)
        win.people_expand.setChecked(True); win.set_theme(True, 'wine'); APP.processEvents()
        self.assertEqual(win.shortcut_grid.getItemPosition(5)[:2], (2, 1))
        win.person_ids = [self.person['id']]; win.mark_dirty(); win.close()
        win = self.window(); win.load_article(self.article.id)
        self.assertEqual(win.person_ids, [self.person['id']])
        self.assertIn('小明', win.people_button.toolTip())

    def test_legacy_v1_import_and_inconsistent_people_rejected_without_writes(self):
        self.link(); path = self.export()
        with ZipFile(path) as book: files = {n:book.read(n) for n in book.namelist()}
        manifest = json.loads(files[MANIFEST_PATH]); manifest['version'] = 1
        for r in manifest['articles']: r.pop('people')
        files[MANIFEST_PATH] = json.dumps(manifest).encode()
        with ZipFile(path, 'w') as book:
            for n, data in files.items(): book.writestr(n, data)
        db = Database(self.root/'other')
        try:
            importer = EpubImporter(ArticleRepository(db), AttachmentService(db))
            self.assertEqual(importer.import_file(path).imported, 1)
            self.assertEqual(PeopleRepository(db).list(), [])
        finally: db.close()
        second = self.repo.create(); self.repo.save(second.id, '另文', '2026-10-30', '', '', [], [], people=[self.person['id']])
        path = self.export([self.article.id, second.id])
        with ZipFile(path) as book: files = {n:book.read(n) for n in book.namelist()}
        manifest = json.loads(files[MANIFEST_PATH]); manifest['articles'][1]['people'][0]['name'] = '伪造不同资料'
        files[MANIFEST_PATH] = json.dumps(manifest).encode()
        with ZipFile(path, 'w') as book:
            for n, data in files.items(): book.writestr(n, data)
        with self.assertRaises(ValueError): EpubImporter(self.repo, AttachmentService(self.db)).prepare(path)
        self.assertEqual(self.people.list(), [self.person])
