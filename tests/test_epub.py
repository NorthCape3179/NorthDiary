import base64
import posixpath
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree as ET
from zipfile import ZipFile, ZIP_STORED

from ebooklib import epub

from northdiary.models import ExportSelection
from northdiary.services.attachments import AttachmentService
from northdiary.services.epub import EpubExporter
from northdiary.storage.database import Database
from northdiary.storage.repository import ArticleRepository


PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=')
X = {'x': 'http://www.w3.org/1999/xhtml', 'opf': 'http://www.idpf.org/2007/opf',
     'dc': 'http://purl.org/dc/elements/1.1/', 'ncx': 'http://www.daisy.org/z3986/2005/ncx/'}


class EpubTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.database = Database(self.root / 'data')
        self.repository = ArticleRepository(self.database)
        self.attachments = AttachmentService(self.database)
        self.exporter = EpubExporter(self.repository, self.attachments)
        self.destination = self.root / '书.epub'

    def tearDown(self):
        self.database.close()
        self.temp.cleanup()

    def article(self, title, body=''):
        article = self.repository.create()
        self.repository.save(article.id, title, '2026-10-30', body, '', [], [])
        return article.id

    def export(self, ids):
        return self.exporter.export(ExportSelection(tuple(ids), '文集 & <回忆>', '作者 & 我'), self.destination)

    def test_package_metadata_order_navigation_and_xml(self):
        first = self.article('第一篇 & <日记>', '<p>中文 &amp; &nbsp; &copy; <br>换行</p>')
        second = self.article('同名章节', '<p>第二篇</p>')
        third = self.article('同名章节')
        self.assertEqual(self.export([third, first, second]), self.destination)
        with ZipFile(self.destination) as archive:
            self.assertEqual(archive.namelist()[0], 'mimetype')
            self.assertEqual(archive.getinfo('mimetype').compress_type, ZIP_STORED)
            self.assertEqual(archive.read('mimetype'), b'application/epub+zip')
            container = ET.fromstring(archive.read('META-INF/container.xml'))
            package_name = container.find('.//{*}rootfile').attrib['full-path']
            prefix = posixpath.dirname(package_name)
            package = ET.fromstring(archive.read(package_name))
            self.assertEqual(package.find('.//dc:title', X).text, '文集 & <回忆>')
            self.assertEqual(package.find('.//dc:creator', X).text, '作者 & 我')
            self.assertEqual(package.find('.//dc:language', X).text, 'zh-CN')
            self.assertIsNotNone(package.find('.//dc:identifier', X).text)
            manifest = {item.attrib['id']: item.attrib for item in package.find('opf:manifest', X)}
            spine = [manifest[item.attrib['idref']]['href'] for item in package.find('opf:spine', X)]
            self.assertEqual(spine, ['nav.xhtml', 'chapter-1.xhtml', 'chapter-2.xhtml', 'chapter-3.xhtml'])
            for name in archive.namelist():
                if name.endswith(('.xml', '.opf', '.ncx', '.xhtml')):
                    document = ET.fromstring(archive.read(name))
                    for element in document.iter():
                        for attribute in ('src', 'href'):
                            reference = element.get(attribute)
                            if reference and not urlsplit(reference).scheme:
                                path = unquote(urlsplit(reference).path)
                                if path:
                                    target = posixpath.normpath(posixpath.join(posixpath.dirname(name), path))
                                    self.assertIn(target, archive.namelist())
            nav = ET.fromstring(archive.read(prefix + '/nav.xhtml'))
            self.assertEqual([a.text for a in nav.findall('.//x:nav/x:ol/x:li/x:a', X)],
                             ['同名章节', '第一篇 & <日记>', '同名章节'])
            ncx = ET.fromstring(archive.read(prefix + '/toc.ncx'))
            self.assertEqual([n.attrib['src'] for n in ncx.findall('.//ncx:content', X)], spine[1:])
            chapter = ET.fromstring(archive.read(prefix + '/chapter-2.xhtml'))
            self.assertEqual(chapter.find('.//x:h1', X).text, '第一篇 & <日记>')
            self.assertIn('中文 & \xa0 ©', ''.join(chapter.itertext()))
        # Independent read path also resolves all three chapters.
        book = epub.read_epub(str(self.destination))
        self.assertEqual(len(book.toc), 3)

    def test_qt_html_cleaning_and_managed_images(self):
        key = self.article('图文')
        source = self.root / 'original.png'
        source.write_bytes(PNG)
        image = self.attachments.add(key, source)
        source.unlink()
        body = f'''<!DOCTYPE HTML><html><head><meta name="qrichtext" content="1" />
        <style>p {{white-space: pre-wrap}}</style></head><body style="font-family:Arial">
        <p style="-qt-paragraph-type:empty"><br></p>
        <p onclick="bad()"><span style="font-weight:700;font-style:italic;color:red">粗斜体 &amp; 中文</span></p>
        <ul><li>项目</li></ul><table><tr><td colspan="2">格子</td></tr></table>
        <img src="{image}" width="9000" onerror="bad()"><img src="{image}">
        <a href="https://example.org/?a=1&amp;b=2">网页</a>
        <a name="target"></a><a href="#target">定位</a><a href="#missing">缺失定位</a>
        <script>坏脚本</script><iframe src="https://example.org">隐藏</iframe>
        <custom>保留文字<span>及尾部</span>结束</custom>\x01</body></html>'''
        self.repository.save(key, '图文', '2026-10-30', body, '', [], [])
        self.export([key])
        with ZipFile(self.destination) as archive:
            data = archive.read('EPUB/chapter-1.xhtml').decode()
            self.assertNotIn('-qt-', data)
            self.assertNotIn('onclick', data)
            self.assertNotIn('font-family', data)
            self.assertNotIn('坏脚本', data)
            self.assertNotIn('iframe', data)
            self.assertNotIn('width="9000"', data)
            chapter = ET.fromstring(data)
            self.assertEqual(chapter.find('.//x:strong/x:em', X).text, '粗斜体 & 中文')
            self.assertIn('保留文字及尾部结束', ''.join(chapter.itertext()))
            images = chapter.findall('.//x:img', X)
            self.assertEqual([n.attrib['src'] for n in images], ['images/image-1.png'] * 2)
            self.assertEqual(archive.read('EPUB/images/image-1.png'), PNG)
            self.assertEqual(len([n for n in archive.namelist() if '/images/' in n]), 1)
            self.assertIn(b'max-width: 100%', archive.read('EPUB/style.css'))

    def test_invalid_selection_never_creates_book(self):
        key = self.article('有效')
        for ids, exception in (([], ValueError), ([key, key], ValueError), (['missing'], KeyError)):
            with self.subTest(ids=ids), self.assertRaises(exception):
                self.export(ids)
        self.repository.set_deleted(key)
        with self.assertRaises(ValueError):
            self.export([key])
        self.assertFalse(self.destination.exists())

    def test_desktop_photo_links_and_partial_dates(self):
        key = self.article('回忆')
        source = self.root / 'photo.png'
        source.write_bytes(PNG)
        relative = self.attachments.add(key, source)
        row = self.attachments.list(key)[0]
        body = f'<p>海边<a href="ndiary-image:{row["id"]}"><span>▧ 照片 ↗</span></a>雨夜</p>'
        for date in ('2026-未知-未知', '2026-07-未知'):
            self.repository.save(key, '回忆', date, body, '', [], [])
            self.export([key])
            with ZipFile(self.destination) as archive:
                chapter = ET.fromstring(archive.read('EPUB/chapter-1.xhtml'))
                self.assertIn(date, ''.join(chapter.itertext()))
                self.assertNotIn('ndiary-image:', archive.read('EPUB/chapter-1.xhtml').decode())
                self.assertEqual(chapter.find('.//x:img', X).get('alt'), 'photo')
                self.assertEqual(archive.read('EPUB/images/image-1.png'), PNG)
        self.assertEqual(self.attachments.list(key)[0]['relative_path'], relative)

    def test_foreign_and_missing_photo_links_fail_without_overwrite(self):
        key = self.article('当前文章')
        other = self.article('其他文章')
        source = self.root / 'photo.png'
        source.write_bytes(PNG)
        self.attachments.add(other, source)
        foreign = self.attachments.list(other)[0]['id']
        self.destination.write_bytes(b'previous')
        for identifier in ('missing', foreign):
            self.repository.save(key, '当前文章', '2026-10-30',
                                 f'<a href="ndiary-image:{identifier}">照片</a>', '', [], [])
            with self.assertRaisesRegex(ValueError, '正文图片入口'):
                self.export([key])
            self.assertEqual(self.destination.read_bytes(), b'previous')

    def test_bad_references_leave_existing_book_untouched(self):
        key = self.article('图片')
        other = self.article('别人的图片')
        source = self.root / 'x.png'
        source.write_bytes(PNG)
        other_image = self.attachments.add(other, source)
        for reference in ('https://example.org/x.png', 'file:///etc/passwd',
                          'data:image/png;base64,abcd', '../x.png',
                          'attachments/../x.png', 'attachments/%2e%2e/x.png',
                          'attachments\\x.png', other_image, 'attachments/missing.png'):
            with self.subTest(reference=reference):
                self.repository.save(key, '图片', '2026-10-30', f'<img src="{reference}">', '', [], [])
                self.destination.write_bytes(b'existing book')
                with self.assertRaisesRegex(ValueError, '图片'):
                    self.export([key])
                self.assertEqual(self.destination.read_bytes(), b'existing book')

    def test_missing_and_unsupported_image(self):
        key = self.article('图片')
        source = self.root / 'x.webp'
        source.write_bytes(b'RIFFinvalid')
        image = self.attachments.add(key, source)
        self.repository.save(key, '图片', '2026-10-30', f'<img src="{image}">', '', [], [])
        with self.assertRaisesRegex(ValueError, '仅支持'):
            self.export([key])
        (self.database.root / image).unlink()
        with self.assertRaisesRegex(ValueError, '无法导出'):
            self.export([key])

    def test_write_failure_cleans_temp_and_preserves_destination(self):
        key = self.article('正常', '<p>正文</p>')
        self.destination.write_bytes(b'previous')

        def fail(path, *args):
            Path(path).write_bytes(b'partial')
            raise OSError('磁盘已满')

        with patch('northdiary.services.epub.epub.write_epub', side_effect=fail):
            with self.assertRaisesRegex(OSError, '磁盘已满'):
                self.export([key])
        self.assertEqual(self.destination.read_bytes(), b'previous')
        self.assertEqual(list(self.root.glob('*.epub')), [self.destination])
        with patch('northdiary.services.epub.os.replace', side_effect=OSError('不可替换')):
            with self.assertRaises(OSError):
                self.export([key])
        self.assertEqual(self.destination.read_bytes(), b'previous')
        self.assertEqual(list(self.root.glob('*.epub')), [self.destination])

    def test_fresh_content_and_no_source_mutation(self):
        key = self.article('旧标题')
        selection = ExportSelection((key,), '书')
        self.repository.save(key, '新标题', '2026-10-30', '<p>新正文</p>', '新正文', ['分类'], [])
        before = self.repository.get(key)
        self.exporter.export(selection, self.destination)
        with ZipFile(self.destination) as archive:
            self.assertIn('新标题', archive.read('EPUB/chapter-1.xhtml').decode())
        self.assertEqual(self.repository.get(key), before)
        self.assertEqual(self.repository.labels(key, 'categories'), ['分类'])

    def test_registered_symlink_cannot_escape_attachment_root(self):
        key = self.article('越界资源')
        source = self.root / 'outside.png'
        source.write_bytes(PNG)
        image = self.attachments.add(key, source)
        managed = self.database.root / image
        managed.unlink()
        try:
            managed.symlink_to(source)
        except OSError:
            self.skipTest('当前系统不允许创建符号链接')
        self.repository.save(key, '越界资源', '2026-10-30', f'<img src="{image}">', '', [], [])
        with self.assertRaisesRegex(ValueError, '超出'):
            self.export([key])
        self.assertFalse(self.destination.exists())

    def test_empty_title_wrong_extension_and_plain_text_body(self):
        key = self.article('标题', '开头文字 &amp; 特殊符号')
        with self.assertRaisesRegex(ValueError, '书名'):
            self.exporter.export(ExportSelection((key,), '  '), self.destination)
        with self.assertRaisesRegex(ValueError, '扩展名'):
            self.exporter.export(ExportSelection((key,), '书'), self.root / 'wrong.pdf')
        self.export([key])
        with ZipFile(self.destination) as archive:
            chapter = ET.fromstring(archive.read('EPUB/chapter-1.xhtml'))
            body = chapter.find('x:body', X)
            self.assertEqual(body[0].tag, '{%s}h1' % X['x'])
            self.assertIn('开头文字 & 特殊符号', ''.join(body.itertext()))


if __name__ == '__main__':
    unittest.main()
