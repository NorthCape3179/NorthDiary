import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QImage, QColor, QFont, QTextDocument
from PySide6.QtWidgets import QApplication, QMessageBox
from northdiary.storage.database import Database
from northdiary.storage.people import PeopleRepository
from northdiary.storage.repository import ArticleRepository
from northdiary.services.person_media import make_photo, read_profile_image, decode_image, circular_avatar
from northdiary.services.attachments import AttachmentService
from northdiary.services.backup import BackupService
from northdiary.services.epub import EpubExporter
from northdiary.services.importing import EpubImporter
from northdiary.services.native_format import MANIFEST_PATH
from northdiary.models import ExportSelection
from northdiary.ui.people_dialog import PeopleDialog, PersonEditor, PersonPhotoViewer
from northdiary.ui.main_window import MainWindow
from northdiary.ui.memory_dialog import MemoryDialog

APP = QApplication.instance() or QApplication([])


class PersonMediaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        self.db = Database(self.root/'data'); self.people = PeopleRepository(self.db)
        self.repo = ArticleRepository(self.db); self.article = self.repo.create()
        self.person = self.people.create('测试人物', '@TEST')
        self.path = self.root/'photo.png'
        image = QImage(180, 120, QImage.Format.Format_RGB32); image.fill(QColor('#cc5500'))
        image.save(str(self.path)); self.windows = []

    def tearDown(self):
        for window in reversed(self.windows):
            if isinstance(window, MainWindow): window.dirty = False
            window.close(); window.deleteLater()
        APP.processEvents(); self.db.close(); self.temp.cleanup()

    def with_media(self):
        person = self.people.get(self.person['id'])
        person.update(avatar=read_profile_image(self.path, avatar=True), photos=[make_photo(self.path)])
        self.people.save(person)
        return self.people.get(person['id'])

    def window(self):
        win = MainWindow(self.db); self.windows.append(win); win.load_article(self.article.id)
        return win

    def test_media_persists_after_reopen_and_is_in_backup(self):
        person = self.with_media()
        self.db.close(); self.db = Database(self.root/'data'); self.people = PeopleRepository(self.db)
        self.assertEqual(self.people.get(person['id']), person)
        backup = BackupService(self.db).create(self.root/'backup.ndiary')
        with ZipFile(backup) as bundle: bundle.extract('northdiary.sqlite3', self.root/'snapshot')
        with closing(sqlite3.connect(self.root/'snapshot'/'northdiary.sqlite3')) as conn:
            self.assertEqual(conn.execute('SELECT avatar FROM person_media').fetchone()[0], person['avatar'])
        self.people.delete(person['id'])
        self.assertEqual(self.db.connection.execute('SELECT count(*) FROM person_media').fetchone()[0], 0)

    def test_v9_migration_snapshot_once_preserves_articles_and_people(self):
        self.db.connection.commit()
        legacy = self.root/'legacy'; legacy.mkdir()
        with closing(sqlite3.connect(legacy/'northdiary.sqlite3')) as conn:
            self.db.connection.backup(conn); conn.executescript('DROP TABLE person_media; PRAGMA user_version=9;')
        migrated = Database(legacy)
        self.assertEqual(PeopleRepository(migrated).get(self.person['id']), self.person)
        self.assertEqual(ArticleRepository(migrated).get(self.article.id).id, self.article.id)
        migrated.close(); migrated = Database(legacy); migrated.close()
        snapshots = list((legacy/'backups').glob('before-v10-*'))
        self.assertEqual(len(snapshots), 1)
        with closing(sqlite3.connect(snapshots[0])) as conn:
            self.assertEqual(conn.execute('PRAGMA user_version').fetchone()[0], 9)

    def test_avatar_cancel_invalid_save_and_restore_default(self):
        person = self.with_media()
        editor = PersonEditor(self.people, person); self.windows.append(editor)
        editor.clear_avatar(); editor.reject()
        self.assertEqual(self.people.get(person['id'])['avatar'], person['avatar'])
        editor = PersonEditor(self.people, person); self.windows.append(editor)
        editor.clear_avatar(); editor.fields['code'].setText(''); editor.save()
        self.assertTrue(editor.error.text())
        self.assertEqual(self.people.get(person['id'])['avatar'], person['avatar'])
        editor.fields['code'].setText('@TEST'); editor.save()
        self.assertNotIn('avatar', self.people.get(person['id']))
        self.assertEqual(self.people.get(person['id'])['photos'], person['photos'])

    def test_photo_batch_failure_is_atomic_set_avatar_view_remove(self):
        dialog = PeopleDialog(self.db); self.windows.append(dialog); dialog.show_person(self.person['id'])
        with patch('northdiary.ui.people_dialog.QFileDialog.getOpenFileNames', return_value=([str(self.path), str(self.root/'missing.png')], '')), patch.object(QMessageBox, 'warning'):
            dialog.add_photos()
        self.assertNotIn('photos', self.people.get(self.person['id']))
        with patch('northdiary.ui.people_dialog.QFileDialog.getOpenFileNames', return_value=([str(self.path)], '')):
            dialog.add_photos()
        self.assertEqual(dialog.photo_board.count(), 1)
        dialog.photo_board.setCurrentRow(0); dialog.photo_as_avatar()
        person = self.people.get(self.person['id']); self.assertTrue(person['avatar'])
        viewer = PersonPhotoViewer(person['photos'], 0, None); self.windows.append(viewer)
        self.assertEqual(len(viewer.scene.items()), 1)
        dialog.photo_board.setCurrentRow(0)
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes): dialog.remove_photo()
        person = self.people.get(self.person['id'])
        self.assertNotIn('photos', person); self.assertTrue(person['avatar']); self.assertTrue(self.path.exists())

    def test_avatar_reference_snapshot_size_undo_readonly_and_memory(self):
        person = self.with_media(); win = self.window()
        win.editor.setPlainText('前后'); cursor = win.editor.textCursor(); cursor.setPosition(1); win.editor.setTextCursor(cursor)
        win.person_reference_mode.setCurrentIndex(1); win.insert_person_reference(person['id'])
        html = win.editor.toHtml(); self.assertIn('width="24" height="24"', html)
        self.assertEqual(win.editor.toPlainText(), '前\ufffc后')
        rows = win.attachments.list(self.article.id); self.assertEqual(len(rows), 1)
        self.assertEqual(win.editor.image_links(rows[0]['id']), [(1, 2)])
        path = self.db.root/rows[0]['relative_path']; before = path.read_bytes()
        image = QImage(str(path)); self.assertEqual(image.pixelColor(0, 0).alpha(), 0)
        person['avatar'] = ''; self.people.save(person)
        self.assertEqual(path.read_bytes(), before)
        win.editor.undo(); self.assertEqual(win.editor.toPlainText(), '前后')
        win.editor.redo(); self.assertTrue(win.save())
        memory = MemoryDialog(self.repo, AttachmentService(self.db), article_id=self.article.id); self.windows.append(memory)
        self.assertIn('<img', memory.editor.toHtml()); self.assertEqual(memory.editor.toPlainText(), '前\ufffc后')
        self.assertTrue(win.editor.locate_image(rows[0]['id']))
        win.editor.setReadOnly(True); old = win.editor.toHtml(); win.insert_person_reference(person['id'])
        self.assertEqual(win.editor.toHtml(), old)

    def test_epub_roundtrip_keeps_profile_images_and_24px_reference(self):
        person = self.with_media(); win = self.window()
        win.person_reference_mode.setCurrentIndex(1); win.insert_person_reference(person['id'])
        win.person_ids = [person['id']]; win.mark_dirty(); self.assertTrue(win.save())
        output = self.root/'person.epub'
        EpubExporter(self.repo, win.attachments).export(ExportSelection((self.article.id,), '人物'), output)
        with ZipFile(output) as book:
            manifest = json.loads(book.read(MANIFEST_PATH))
            self.assertEqual(manifest['articles'][0]['people'][0], person)
            self.assertIn(b'width="24"', book.read('EPUB/chapter-1.xhtml'))
        db = Database(self.root/'imported')
        try:
            importer = EpubImporter(ArticleRepository(db), AttachmentService(db)); result = importer.import_file(output)
            self.assertEqual(result.imported, 1); self.assertEqual(PeopleRepository(db).get(person['id']), person)
            imported = ArticleRepository(db).list()[0]
            self.assertIn('width="24" height="24"', imported.body_html)
            self.assertEqual(importer.import_file(output).skipped, 1)
        finally: db.close()

    def test_avatar_references_are_hidden_from_board_but_square_photos_remain(self):
        person = self.with_media(); win = self.window()
        win.person_reference_mode.setCurrentIndex(1)
        win.insert_person_reference(person['id'])
        avatar = win.attachments.list(self.article.id)[0]
        self.assertEqual(win.image_list.count(), 0)
        self.assertTrue((self.db.root/avatar['relative_path']).is_file())
        square = self.root/'square.png'
        image = QImage(96, 96, QImage.Format.Format_RGB32); image.fill(QColor('#cc5500'))
        image.save(str(square))
        photo = win.attachments.add(self.article.id, square)
        win.update_properties()
        self.assertEqual(win.image_list.count(), 1)
        self.assertEqual(win.photo_attachments()[0]['relative_path'], photo)
        self.assertTrue(win.save())
        win.load_article(self.article.id)
        self.assertEqual(win.image_list.count(), 1)
        self.assertIn(avatar['relative_path'], win.editor.person_avatar_paths())
        # The saved inline marker also works when an import renames the file.
        with self.db.connection:
            self.db.connection.execute('UPDATE attachments SET name=? WHERE id=?', ('renamed.png', avatar['id']))
        win.update_properties()
        self.assertEqual(win.image_list.count(), 1)
        with patch('northdiary.ui.main_window.ImageViewer.exec', return_value=0) as opened:
            win.open_image(avatar['id'])
        opened.assert_called_once()
        # Generated avatar attachments stay hidden after their inline reference is removed.
        with self.db.connection:
            self.db.connection.execute('UPDATE attachments SET name=? WHERE id=?', (avatar['name'], avatar['id']))
        win.editor.remove_image_links(avatar['id']);win.update_properties()
        self.assertEqual(win.image_list.count(), 1)
        self.assertTrue((self.db.root/avatar['relative_path']).is_file())

    def test_bad_media_does_not_overwrite_existing_profile(self):
        person = self.with_media()
        for change in ({'avatar': 'invalid'}, {'photos': [{'id': 'bad', 'name': 'x', 'data': 'bad'}]}, {'photos': None}):
            with self.subTest(change=change), self.assertRaises(ValueError): self.people.save(dict(person, **change))
        self.assertEqual(self.people.get(person['id']), person)


if __name__ == '__main__': unittest.main()
