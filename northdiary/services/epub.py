"""Small EPUB 3 adapter; stored Qt HTML never goes directly into the book."""
import os
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import tempfile
from urllib.parse import unquote, urlsplit
from uuid import uuid4

from ebooklib import epub
from lxml import etree, html

from northdiary.models import ExportSelection
from northdiary.services.exporting import validate_selection
from northdiary.services.native_format import (
    FORMAT, FORMAT_VERSION, MAX_MANIFEST, MAX_MEMBER, MAX_TOTAL,
    article_record, image_type, validate_record,
)


STYLE = b'''body { line-height: 1.6; margin: 1em; }
p { margin: 0 0 0.8em; white-space: pre-wrap; } h1 { font-size: 1.6em; }
img { max-width: 100%; height: auto; } pre { white-space: pre-wrap; }
table { border-collapse: collapse; } td, th { padding: 0.3em; }
.date { color: #666; font-size: 0.9em; }'''
ALLOWED = set('p div span br hr h1 h2 h3 h4 h5 h6 strong b em i u s sub sup '
              'blockquote pre code ul ol li dl dt dd table caption thead tbody '
              'tfoot tr th td a img'.split())
DROP = set('head script style iframe object embed svg math form input button '
           'textarea select audio video link meta base'.split())
INVALID_XML = re.compile('[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]')


def _text(element, value):
    """Append mixed content without losing tails when an unknown tag is unwrapped."""
    if not value:
        return
    if len(element):
        element[-1].tail = (element[-1].tail or '') + value
    else:
        element.text = (element.text or '') + value


def clean_body(source: str, resolve_image, resolve_image_link=None, preserve_photo_links=False) -> etree._Element:
    """Rebuild a whitelist tree, strip Qt CSS, preserve basic inline emphasis."""
    source = INVALID_XML.sub('', source)
    document = html.document_fromstring(source or '<p></p>')
    body = etree.Element('body')
    ids = set()

    def copy(node, parent):
        if not isinstance(node.tag, str):
            return
        tag = node.tag.lower()
        if tag in DROP:
            return
        href = node.get('href', '').strip() if tag == 'a' else ''
        if href.startswith('ndiary-image:'):
            if resolve_image_link is None:
                raise ValueError('无法解析正文图片入口')
            reference, caption = resolve_image_link(href.removeprefix('ndiary-image:'))
            if preserve_photo_links:
                anchor = etree.SubElement(parent, 'a', href='ndiary-image:' + reference)
                anchor.text = '▧ ' + caption + ' ↗'
                return
            image = etree.SubElement(parent, 'img')
            image.set('src', resolve_image(reference))
            image.set('alt', caption)
            return
        target = etree.SubElement(parent, tag) if tag in ALLOWED else parent
        if tag in ALLOWED:
            identifier = node.get('id') or (node.get('name') if tag == 'a' else None)
            if identifier and identifier not in ids:
                target.set('id', identifier)
                ids.add(identifier)
        if tag == 'img':
            target.set('src', resolve_image(node.get('src', '')))
            target.set('alt', node.get('alt', ''))
        if tag == 'a':
            href = node.get('href', '').strip()
            scheme = urlsplit(href).scheme.lower()
            if scheme in ('https', 'http', 'mailto') or href.startswith('#'):
                target.set('href', href)
            elif href:
                raise ValueError('不支持导出本地附件链接，请仅使用正文图片或网页链接')
        if tag in ('td', 'th'):
            for key in ('rowspan', 'colspan'):
                if re.fullmatch(r'[1-9][0-9]{0,2}', node.get(key, '')):
                    target.set(key, node.get(key))
        # QTextEdit writes bold/italic as span CSS, not necessarily semantic tags.
        styles = dict(part.split(':', 1) for part in node.get('style', '').lower().split(';') if ':' in part)
        styles = {key.strip(): value.strip() for key, value in styles.items()}
        weight = styles.get('font-weight', '')
        for enabled, semantic in (
            (weight == 'bold' or (weight.isdigit() and int(weight) >= 600), 'strong'),
            (styles.get('font-style') == 'italic', 'em'),
            ('underline' in styles.get('text-decoration', ''), 'u'),
        ):
            if enabled and tag not in ('img', 'br', 'hr'):
                target = etree.SubElement(target, semantic)
        _text(target, node.text)
        for child in node:
            copy(child, target)
            _text(target, child.tail)

    original = document.find('body')
    if original is not None:
        _text(body, original.text)
        for node in original:
            copy(node, body)
            _text(body, node.tail)
    for anchor in body.iter('a'):
        href = anchor.get('href', '')
        if href.startswith('#') and unquote(href[1:]) not in ids:
            del anchor.attrib['href']
    if body.text:
        paragraph = etree.Element('p')
        paragraph.text, body.text = body.text, None
        body.insert(0, paragraph)
    return body


class EpubExporter:
    def __init__(self, repository, attachments):
        self.repository = repository
        self.attachments = attachments

    def export(self, selection: ExportSelection, destination: Path) -> Path:
        articles = validate_selection(self.repository, selection)
        if not selection.title.strip():
            raise ValueError('请填写书名')
        destination = Path(destination)
        if destination.suffix.lower() != '.epub':
            raise ValueError('导出文件必须使用 .epub 扩展名')
        book = epub.EpubBook()
        book.set_identifier('urn:uuid:' + str(uuid4()))
        book.set_title(selection.title.strip())
        book.set_language('zh-CN')
        if selection.author.strip():
            book.add_author(selection.author.strip())
        css = epub.EpubItem(uid='style', file_name='style.css', media_type='text/css', content=STYLE)
        book.add_item(css)
        resources = {}
        resource_info = {}
        records = []
        chapters = []
        root = self.attachments.database.root.resolve()

        for index, article in enumerate(articles, 1):
            attachments = self.attachments.list(article.id)
            owned = {row['relative_path'] for row in attachments}
            by_id = {row['id']: row for row in attachments}
            used = set()

            def resolve_image_link(identifier):
                row = by_id.get(identifier)
                if row is None:
                    raise ValueError('正文图片入口不存在或不属于当前文章：' + identifier)
                return row['relative_path'], row['caption'] or Path(row['name']).stem

            def resolve_image(reference):
                url = urlsplit(reference)
                path = unquote(url.path)
                parts = PurePosixPath(path).parts
                if (url.scheme or url.netloc or url.query or url.fragment or '\\' in path
                        or not parts or parts[0] != 'attachments' or '..' in parts
                        or path not in owned):
                    raise ValueError('图片必须是当前文章的托管附件：' + reference)
                source_path = (root / path).resolve(strict=True)
                if not source_path.is_relative_to(root / 'attachments') or not source_path.is_file():
                    raise ValueError('图片路径超出托管附件目录：' + reference)
                if path not in resources:
                    if source_path.stat().st_size > MAX_MEMBER:
                        raise ValueError('单张图片过大，请使用小于 32 MiB 的图片')
                    content = source_path.read_bytes()
                    # Only portable EPUB core image types; never trust file extensions.
                    media, suffix = image_type(content)
                    name = f'images/image-{len(resources) + 1}{suffix}'
                    book.add_item(epub.EpubItem(uid=f'image-{len(resources) + 1}',
                                              file_name=name, media_type=media, content=content))
                    resources[path] = name
                    resource_info[path] = {'media_type': media, 'sha256': hashlib.sha256(content).hexdigest()}
                used.add(path)
                return resources[path]

            try:
                body = clean_body(article.body_html, resolve_image, resolve_image_link)
            except (ValueError, OSError) as error:
                raise ValueError(f'文章「{article.title}」无法导出：{error}') from error
            assets = [dict(id=row['id'], relative_path=row['relative_path'],
                           archive_path='EPUB/' + resources[row['relative_path']],
                           name=row['name'], caption=row['caption'],
                           **resource_info[row['relative_path']])
                      for row in attachments if row['relative_path'] in used]
            record = article_record(self.repository, article, assets)
            validate_record(record)
            records.append(record)
            heading = etree.Element('h1')
            heading.text = INVALID_XML.sub('', article.title)
            body.insert(0, heading)
            date = etree.Element('p', {'class': 'date'})
            date.text = INVALID_XML.sub('', article.diary_date)
            body.insert(1, date)
            chapter = epub.EpubHtml(uid=f'chapter-{index}', title=heading.text,
                                    file_name=f'chapter-{index}.xhtml', lang='zh-CN')
            chapter.content = etree.tostring(body, encoding='unicode', method='xml')
            chapter.add_item(css)
            book.add_item(chapter)
            chapters.append(chapter)

        manifest = json.dumps({'format': FORMAT, 'version': FORMAT_VERSION,
                               'articles': records}, ensure_ascii=False).encode('utf-8')
        if (len(manifest) > MAX_MANIFEST or len(records) > 1000
                or sum(len(record['assets']) for record in records) > 5000):
            raise ValueError('本次导出数据过多，请分批选择文章')
        book.add_item(epub.EpubItem(uid='northdiary-data', file_name='northdiary/manifest.json',
                                   media_type='application/json', content=manifest))
        book.toc = chapters
        book.spine = ['nav', *chapters]
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav(title='目录'))
        sizes = [len(item.get_content()) for item in book.get_items()]
        if len(sizes) > 4990 or max(sizes) > MAX_MEMBER or sum(sizes) > MAX_TOTAL - 1024 * 1024:
            raise ValueError('本次导出文件过大，请分批选择文章或压缩图片')
        # A failed write must neither truncate an existing book nor leave a partial one.
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=destination.parent, suffix='.epub', delete=False) as handle:
                temporary = Path(handle.name)
            if not epub.write_epub(str(temporary), book, {'raise_exceptions': True}):
                raise OSError('EPUB 写入失败')
            os.replace(temporary, destination)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return destination
