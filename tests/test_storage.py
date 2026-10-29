import json
from contextlib import closing
import sqlite3
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from northdiary.models import ExportSelection
from northdiary.services.attachments import AttachmentService
from northdiary.services.backup import BackupService
from northdiary.services.exporting import validate_selection
from northdiary.storage.database import Database, SCHEMA
from northdiary.storage.repository import ArticleRepository


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.database = Database(self.root / 'data')
        self.repo = ArticleRepository(self.database)

    def tearDown(self):
        self.database.close()
        self.temp.cleanup()

    def save_article(self):
        article = self.repo.create()
        self.repo.save(article.id, '秋日 100%', '2026-10-29', '<p>中文日记</p>', '中文日记',
                       ['旅行', '生活', '旅行'], ['秋天'])
        return article.id

    def test_restart_and_multi_category_one_article(self):
        key = self.save_article()
        self.database.close()
        self.database = Database(self.root / 'data')
        self.repo = ArticleRepository(self.database)
        self.assertEqual(self.repo.get(key).body_html, '<p>中文日记</p>')
        self.assertEqual(len(self.repo.list()), 1)
        self.assertEqual(self.repo.list(category='生活')[0].id, self.repo.list(category='旅行')[0].id)
        self.assertEqual(len(self.repo.list('%')), 1)
        self.assertEqual(self.repo.list('_'), [])

    def test_temporary_tags_are_article_local_and_persist(self):
        first, second = self.save_article(), self.save_article()
        self.repo.save(first, '第一篇', '2026-10-29', '', '', [], ['普通'], ['仅此文'])
        self.assertNotIn('仅此文', self.repo.tags())
        self.assertEqual(self.repo.temporary_tags(second), [])
        self.assertEqual([a.id for a in self.repo.list(tag='普通')], [first])
        self.database.close()
        self.database = Database(self.root / 'data')
        self.repo = ArticleRepository(self.database)
        self.assertEqual(self.repo.temporary_tags(first), ['仅此文'])
        self.repo.save(first, '第一篇', '2026-10-29', '', '', [], [])
        self.assertEqual(self.repo.temporary_tags(first), ['仅此文'])
        self.assertIn('普通', self.repo.tags())

    def test_v1_migration_backs_up_and_preserves_tags(self):
        root = self.root / 'legacy'
        root.mkdir()
        with closing(sqlite3.connect(root / 'northdiary.sqlite3')) as connection:
            connection.executescript(SCHEMA)
            connection.execute("INSERT INTO tags VALUES ('old-id', '旧标签')")
            connection.commit()
        migrated = Database(root)
        try:
            self.assertEqual(ArticleRepository(migrated).tags(), ['旧标签'])
            self.assertEqual(migrated.connection.execute('PRAGMA user_version').fetchone()[0], 3)
        finally:
            migrated.close()
        snapshots = list((root / 'backups').glob('*.sqlite3'))
        self.assertEqual(len(snapshots), 1)
        with closing(sqlite3.connect(snapshots[0])) as snapshot:
            self.assertEqual(snapshot.execute('PRAGMA user_version').fetchone()[0], 1)
            self.assertEqual(snapshot.execute('SELECT name FROM tags').fetchone()[0], '旧标签')

    def test_failed_relation_save_rolls_back_content(self):
        key = self.save_article()
        self.database.connection.execute('''CREATE TRIGGER reject_tag BEFORE INSERT ON tags
            BEGIN SELECT RAISE(ABORT, 'simulated failure'); END''')
        with self.assertRaises(sqlite3.IntegrityError):
            self.repo.save(key, '不能被保存', '2026-01-01', 'bad', 'bad', ['新分类'], ['新标签'])
        self.assertEqual(self.repo.get(key).title, '秋日 100%')
        self.assertEqual(set(self.repo.labels(key, 'categories')), {'旅行', '生活'})

    def test_trash_restore_preserves_attachment(self):
        key = self.save_article()
        original = self.root / 'note.txt'
        original.write_text('原文件', encoding='utf-8')
        service = AttachmentService(self.database)
        relative = service.add(key, original)
        self.repo.set_deleted(key)
        self.assertEqual(self.repo.list(), [])
        self.assertEqual(self.repo.list(trash=True)[0].id, key)
        with self.assertRaises(ValueError):
            self.repo.save(key, '覆盖', '2026-01-01', '', '', [], [])
        self.repo.set_deleted(key, False)
        self.assertEqual(self.repo.list()[0].id, key)
        self.assertTrue((self.database.root / relative).exists())
        self.assertEqual(original.read_text(encoding='utf-8'), '原文件')

    def test_backup_reopens_at_another_path_with_attachments(self):
        key = self.save_article()
        source = self.root / 'image.bin'
        source.write_bytes(b'test-resource')
        relative = AttachmentService(self.database).add(key, source)
        output = self.root / 'copy.ndiary'
        BackupService(self.database).create(output)
        with ZipFile(output) as bundle:
            self.assertEqual(json.loads(bundle.read('manifest.json'))['version'], 1)
            # Test extraction of our own generated fixture, not an untrusted import API.
            bundle.extractall(self.root / 'restored')
        restored = Database(self.root / 'restored')
        try:
            self.assertEqual(ArticleRepository(restored).get(key).title, '秋日 100%')
            self.assertEqual((restored.root / relative).read_bytes(), b'test-resource')
            self.assertEqual(restored.connection.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
        finally:
            restored.close()
        with self.assertRaises(FileExistsError):
            BackupService(self.database).create(output)

    def test_future_database_version_is_not_modified(self):
        root = self.root / 'future'
        root.mkdir()
        with closing(sqlite3.connect(root / 'northdiary.sqlite3')) as conn:
            conn.execute('PRAGMA user_version=99')
        with self.assertRaises(RuntimeError):
            Database(root)
        with closing(sqlite3.connect(root / 'northdiary.sqlite3')) as conn:
            self.assertEqual(conn.execute('PRAGMA user_version').fetchone()[0], 99)

    def test_export_selection_keeps_order_and_rejects_trash(self):
        first, second = self.save_article(), self.save_article()
        selection = ExportSelection((second, first), '文集')
        self.assertEqual([a.id for a in validate_selection(self.repo, selection)], [second, first])
        self.repo.set_deleted(first)
        with self.assertRaises(ValueError):
            validate_selection(self.repo, selection)

    def test_all_sort_orders_pins_and_combined_filters(self):
        keys = [self.save_article() for _ in range(4)]
        for i, key in enumerate(keys):
            with self.database.connection:
                self.database.connection.execute('UPDATE articles SET title=?,diary_date=?,created_at=?,updated_at=?,pinned=? WHERE id=?',
                    (['B','A','D','C'][i], f'2026-0{i+1}-01', f'2026-01-0{i+1}T12:00:00+08:00',
                     f'2026-02-0{4-i}T12:00:00+08:00', int(i < 2), key))
        expectations = {'created_desc':[1,0,3,2], 'created_asc':[0,1,2,3],
                        'updated_desc':[0,1,2,3], 'updated_asc':[1,0,3,2], 'title':[1,0,3,2]}
        for order, expected in expectations.items():
            self.assertEqual([a.id for a in self.repo.list(sort=order)], [keys[i] for i in expected])
            self.assertEqual([a.id for a in self.repo.list(category='生活', tag='秋天', sort=order)], [keys[i] for i in expected])
        self.assertEqual([a.id for a in self.repo.list('A', category='旅行', tag='秋天', sort='title')], [keys[1]])
        with self.assertRaises(ValueError):
            self.repo.list(sort='title; DELETE FROM articles')

    def test_pins_reorder_filtered_slots_and_restart(self):
        first, second, third, fourth = [self.save_article() for _ in range(4)]
        self.assertEqual([a.id for a in self.repo.list(sort='manual')], [first, second, third, fourth])
        self.repo.reorder([third, first])
        self.assertEqual([a.id for a in self.repo.list(sort='manual')], [third, second, first, fourth])
        self.repo.set_pinned(second, True)
        self.repo.set_pinned(fourth, True)
        self.repo.reorder([fourth, second, third, first])
        with self.assertRaises(ValueError):
            self.repo.reorder([third, fourth])
        self.database.close()
        self.database = Database(self.root / 'data')
        self.repo = ArticleRepository(self.database)
        self.assertEqual([a.id for a in self.repo.list(sort='manual')], [fourth, second, third, first])
        self.repo.set_deleted(fourth)
        self.repo.set_deleted(fourth, False)
        self.assertEqual(self.repo.list(sort='manual')[0].id, fourth)
        self.repo.set_pinned(fourth, False)
        self.assertEqual(self.repo.list(sort='manual')[0].id, second)

    def test_permanent_delete_requires_trash_and_preserves_original(self):
        key = self.save_article()
        source = self.root / 'source.txt'
        source.write_text('原文件保留', encoding='utf-8')
        relative = AttachmentService(self.database).add(key, source)
        with self.assertRaises(ValueError):
            self.repo.permanently_delete(key)
        self.repo.set_deleted(key)
        self.assertEqual(self.repo.permanently_delete(key), [])
        with self.assertRaises(KeyError):
            self.repo.get(key)
        self.assertTrue(source.exists())
        self.assertFalse((self.database.root / relative).exists())
        self.assertEqual(self.database.connection.execute('SELECT COUNT(*) FROM article_tags WHERE article_id=?', (key,)).fetchone()[0], 0)
        self.assertEqual(self.database.connection.execute('PRAGMA foreign_key_check').fetchall(), [])

    def test_v2_migration_keeps_article_data_and_order(self):
        root = self.root / 'version2'
        root.mkdir()
        with closing(sqlite3.connect(root / 'northdiary.sqlite3')) as connection:
            connection.executescript(SCHEMA)
            connection.executescript('''CREATE TABLE article_temporary_tags (
                article_id TEXT NOT NULL REFERENCES articles(id), name TEXT NOT NULL,
                PRIMARY KEY(article_id,name)); PRAGMA user_version=2;''')
            connection.execute("INSERT INTO articles VALUES ('old','旧文章','2020-01-01','<p>保留</p>','保留','2020','2020',NULL)")
            connection.execute("INSERT INTO article_temporary_tags VALUES ('old','临时')")
            connection.commit()
        upgraded = Database(root)
        try:
            repo = ArticleRepository(upgraded)
            self.assertEqual(repo.get('old').body_text, '保留')
            self.assertEqual(repo.get('old').pinned, 0)
            self.assertEqual(repo.temporary_tags('old'), ['临时'])
            self.assertEqual(len(list((root / 'backups').glob('before-v3-*.sqlite3'))), 1)
        finally:
            upgraded.close()


if __name__ == '__main__':
    unittest.main()
