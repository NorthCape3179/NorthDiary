import json
import tempfile
import unittest
import warnings
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

from test_epub import PNG
from northdiary.models import ExportSelection
from northdiary.services.attachments import AttachmentService
from northdiary.services.epub import EpubExporter
from northdiary.services.importing import EpubImporter
from northdiary.services.native_format import MANIFEST_PATH
from northdiary.storage.database import Database, SCHEMA_VERSION
from northdiary.storage.repository import ArticleRepository


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = Database(self.root / 'source')
        self.destination = Database(self.root / 'destination')
        self.repo = ArticleRepository(self.source)
        self.target = ArticleRepository(self.destination)
        self.attachments = AttachmentService(self.source)
        self.local_attachments = AttachmentService(self.destination)
        self.exporter = EpubExporter(self.repo, self.attachments)
        self.importer = EpubImporter(self.target, self.local_attachments)
        self.book = self.root / 'book.epub'

    def tearDown(self):
        self.source.close()
        self.destination.close()
        self.temp.cleanup()

    def article(self, title='回忆', picture=False, date='2026-未知-未知'):
        article = self.repo.create()
        body = '<p>中文 &amp; <b>粗体</b></p>'
        if picture:
            source = self.root / 'photo.png'
            source.write_bytes(PNG)
            self.attachments.add(article.id, source)
            row = self.attachments.list(article.id)[0]
            with self.source.connection:
                self.source.connection.execute('UPDATE attachments SET caption=? WHERE id=?', ('海边', row['id']))
            body += f'<p>前文<a href="ndiary-image:{row["id"]}">▧ 海边 ↗</a>后文</p>'
        self.repo.save(article.id, title, date, body, '中文 粗体', ['旅行'], ['海'], ['临时'])
        return article.id

    def export(self, keys):
        self.exporter.export(ExportSelection(tuple(keys), '我的回忆'), self.book)

    def mutate(self, change=None, extra=None):
        with ZipFile(self.book) as archive:
            files = {item.filename: archive.read(item) for item in archive.infolist()}
        if change:
            manifest = json.loads(files[MANIFEST_PATH])
            change(manifest)
            files[MANIFEST_PATH] = json.dumps(manifest).encode()
        if extra:
            files.update(extra)
        with ZipFile(self.book, 'w') as archive:
            for name, data in files.items():
                archive.writestr(name, data)

    def assert_empty(self):
        self.assertEqual(self.target.list(), [])
        self.assertEqual(list((self.destination.root / 'attachments').iterdir()), [])
        self.assertEqual(self.target.categories(), [])

    def test_full_roundtrip_independent_images_labels_partial_dates_and_reopen(self):
        first = self.article(picture=True)
        second = self.article('第二篇', date='2026-07-未知')
        self.repo.set_pinned(first, True)
        original = self.repo.get(first)
        self.export([second, first])
        preview = self.importer.prepare(self.book)
        self.assertEqual(preview.new_count, 2)
        self.assert_empty()  # Preview is read-only.
        for path in (self.source.root / 'attachments').iterdir():
            path.unlink()
        result = self.importer.apply(preview)
        self.book.unlink()
        self.assertEqual((result.imported, result.skipped), (2, 0))
        imported = self.target.get(result.article_ids[1])
        self.assertEqual((imported.title, imported.diary_date, imported.created_at, imported.updated_at, imported.pinned),
                         (original.title, original.diary_date, original.created_at, original.updated_at, 1))
        self.assertEqual(self.target.labels(imported.id, 'categories'), ['旅行'])
        self.assertEqual(self.target.labels(imported.id, 'tags'), ['海'])
        self.assertEqual(self.target.temporary_tags(imported.id), ['临时'])
        local = self.local_attachments.list(imported.id)[0]
        self.assertEqual((self.destination.root / local['relative_path']).read_bytes(), PNG)
        self.assertEqual(local['caption'], '海边')
        self.assertIn('ndiary-image:' + local['id'], imported.body_html)
        self.assertIn('粗体', imported.body_text)
        self.assertIn('前文', imported.body_text)
        self.assertIn('后文', imported.body_text)
        self.assertEqual(self.target.get(result.article_ids[0]).diary_date, '2026-07-未知')
        self.destination.close()
        self.destination = Database(self.root / 'destination')
        reopened = ArticleRepository(self.destination)
        self.assertEqual(reopened.get(imported.id), imported)
        self.assertEqual(self.destination.connection.execute('PRAGMA user_version').fetchone()[0], SCHEMA_VERSION)

    def test_repeat_import_and_locally_edited_or_trashed_copy_are_skipped(self):
        key = self.article(picture=True)
        self.export([key])
        first = self.importer.import_file(self.book)
        imported = first.article_ids[0]
        self.target.save(imported, '本地修改', '2026-10-30', '<p>保留</p>', '保留', [], [])
        self.assertEqual(self.importer.import_file(self.book).skipped, 1)
        self.assertEqual(self.target.get(imported).title, '本地修改')
        self.target.set_deleted(imported)
        self.assertEqual(self.importer.import_file(self.book).skipped, 1)
        self.assertIsNotNone(self.target.get(imported).deleted_at)
        self.assertEqual(len(self.local_attachments.list(imported)), 1)

    def test_own_unchanged_export_skips_and_changed_source_gets_conflict_copy(self):
        key = self.article(picture=True)
        self.export([key])
        importer = EpubImporter(self.repo, self.attachments)
        self.assertEqual(importer.prepare(self.book).skipped_count, 1)
        self.assertEqual(importer.import_file(self.book).imported, 0)
        self.repo.save(key, '本机新标题', '2026-10-30', '<p>本机新正文</p>', '本机新正文', [], [])
        before = self.repo.get(key)
        preview = importer.prepare(self.book)
        self.assertEqual(preview.conflict_count, 1)
        result = importer.apply(preview)
        self.assertEqual(result.conflicts, 1)
        self.assertEqual(self.repo.get(key), before)
        self.assertTrue(self.repo.get(result.article_ids[0]).title.endswith('（导入副本）'))
        self.assertEqual(importer.import_file(self.book).skipped, 1)

    def test_two_versions_keep_both_without_overwriting(self):
        key = self.article()
        self.export([key])
        first = self.importer.import_file(self.book).article_ids[0]
        self.repo.save(key, '新版文章', '2026-10-30', '<p>新版内容</p>', '新版内容', [], [])
        self.export([key])
        second = self.importer.import_file(self.book).article_ids[0]
        self.assertNotEqual(first, second)
        self.assertEqual(self.target.get(first).title, '回忆')
        self.assertEqual(self.target.get(second).title, '新版文章')

    def test_sql_failure_rolls_back_entire_batch_and_new_files(self):
        first = self.article('第一篇', picture=True)
        second = self.article('第二篇')
        self.export([first, second])
        with self.destination.connection:
            self.destination.connection.execute('''CREATE TRIGGER reject_second BEFORE INSERT ON articles
                WHEN NEW.title='第二篇' BEGIN SELECT RAISE(ABORT,'模拟写入失败'); END''')
        with self.assertRaisesRegex(Exception, '模拟写入失败'):
            self.importer.import_file(self.book)
        self.assert_empty()

    def test_file_collision_never_overwrites_or_deletes_existing_file(self):
        key = self.article(picture=True)
        self.export([key])
        preview = self.importer.prepare(self.book)
        path = self.destination.root / preview.articles[0].assets[0]['relative_path']
        path.write_bytes(b'existing')
        with self.assertRaises(FileExistsError):
            self.importer.apply(preview)
        self.assertEqual(path.read_bytes(), b'existing')
        self.assertEqual(self.target.list(), [])

    def test_tampered_last_record_rejects_before_any_write(self):
        first = self.article('一', picture=True)
        second = self.article('二', picture=True)
        self.export([first, second])
        self.mutate(lambda data: data['articles'][1]['assets'][0].update(sha256='0' * 64))
        with self.assertRaisesRegex(ValueError, '图片校验失败'):
            self.importer.import_file(self.book)
        self.assert_empty()

    def test_old_third_party_bad_version_and_damaged_books_are_rejected(self):
        key = self.article()
        for mode in ('old', 'format', 'version', 'broken'):
            with self.subTest(mode=mode):
                self.export([key])
                if mode == 'old':
                    with ZipFile(self.book) as archive:
                        files = {i.filename: archive.read(i) for i in archive.infolist() if i.filename != MANIFEST_PATH}
                    with ZipFile(self.book, 'w') as archive:
                        for name, data in files.items():
                            archive.writestr(name, data)
                elif mode == 'format':
                    self.mutate(lambda data: data.update(format='OtherApp'))
                elif mode == 'version':
                    self.mutate(lambda data: data.update(version=99))
                else:
                    self.book.write_bytes(b'not a zip')
                with self.assertRaises(ValueError):
                    self.importer.import_file(self.book)
                self.assert_empty()

    def test_zip_traversal_duplicate_entries_and_limits(self):
        key = self.article()
        for name in ('../escape', '/absolute', 'EPUB/../escape', 'EPUB\\escape'):
            self.export([key])
            self.mutate(extra={name: b'bad'})
            with self.assertRaisesRegex(ValueError, '不安全路径'):
                self.importer.import_file(self.book)
            self.assert_empty()
        self.export([key])
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            with ZipFile(self.book, 'a') as archive:
                archive.writestr('mimetype', b'application/epub+zip')
        with self.assertRaisesRegex(ValueError, '重复文件名'):
            self.importer.import_file(self.book)
        self.export([key])
        with patch('northdiary.services.importing.MAX_TOTAL', 10), self.assertRaisesRegex(ValueError, '过大'):
            self.importer.import_file(self.book)
        self.assert_empty()

    def test_invalid_dates_missing_images_and_hostile_html(self):
        key = self.article(picture=True)
        self.export([key])
        self.mutate(lambda data: data['articles'][0].update(diary_date='2026-02-30'))
        with self.assertRaises(ValueError):
            self.importer.import_file(self.book)
        self.assert_empty()
        self.export([key])
        self.mutate(lambda data: data['articles'][0].update(body_html='<img src="file:///etc/passwd">'))
        with self.assertRaises(ValueError):
            self.importer.import_file(self.book)
        self.assert_empty()
        self.export([key])
        self.mutate(lambda data: data['articles'][0].update(
            body_html=data['articles'][0]['body_html'] + '<script>bad()</script><p onclick="bad()">安全文字</p>'))
        result = self.importer.import_file(self.book)
        body = self.target.get(result.article_ids[0]).body_html
        self.assertNotIn('<script', body)
        self.assertNotIn('onclick', body)
        self.assertIn('安全文字', body)

    def test_preview_applies_without_rereading_changed_package(self):
        key = self.article(picture=True)
        self.export([key])
        preview = self.importer.prepare(self.book)
        self.book.write_bytes(b'replaced while confirmation was open')
        self.assertEqual(self.importer.apply(preview).imported, 1)

    def test_reexport_with_different_chapter_order_does_not_duplicate_content(self):
        first = self.article('一', picture=True)
        self.export([first])
        self.importer.import_file(self.book)
        second = self.article('二', picture=True)
        self.export([second, first])
        result = self.importer.import_file(self.book)
        self.assertEqual((result.imported, result.skipped), (1, 1))
        self.assertEqual(len(self.target.list()), 2)

    def test_legacy_inline_image_is_rewritten_to_local_managed_copy(self):
        key = self.article(picture=True)
        path = self.attachments.list(key)[0]['relative_path']
        self.repo.save(key, '内嵌图', '2026-10-30', f'<p>图<img src="{path}"></p>', '图', [], [])
        self.export([key])
        result = self.importer.import_file(self.book)
        imported = self.target.get(result.article_ids[0])
        local = self.local_attachments.list(imported.id)[0]
        self.assertIn(local['relative_path'], imported.body_html)
        self.assertNotIn(path, imported.body_html)
        self.assertEqual((self.destination.root / local['relative_path']).read_bytes(), PNG)

    def test_second_image_write_failure_cleans_first_image_and_database(self):
        first = self.article('一', picture=True)
        second = self.article('二', picture=True)
        self.export([first, second])
        preview = self.importer.prepare(self.book)
        original_open = Path.open
        writes = []

        def fail_second(path, mode='r', *args, **kwargs):
            if mode == 'xb':
                writes.append(path)
                if len(writes) == 2:
                    raise OSError('模拟附件磁盘已满')
            return original_open(path, mode, *args, **kwargs)

        with patch.object(Path, 'open', fail_second), self.assertRaisesRegex(OSError, '磁盘已满'):
            self.importer.apply(preview)
        self.assert_empty()

    def test_symlinked_attachment_directory_is_rejected(self):
        key = self.article(picture=True)
        self.export([key])
        directory = self.destination.root / 'attachments'
        directory.rmdir()
        try:
            directory.symlink_to(self.source.root / 'attachments', target_is_directory=True)
        except OSError:
            directory.mkdir()
            self.skipTest('当前系统不允许符号链接')
        with self.assertRaisesRegex(ValueError, '符号链接'):
            self.importer.import_file(self.book)
        self.assertEqual(self.target.list(), [])
        self.assertEqual(len(self.attachments.list(key)), 1)


if __name__ == '__main__':
    unittest.main()
