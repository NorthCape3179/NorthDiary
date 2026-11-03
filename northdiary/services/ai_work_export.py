"""Export only a chosen work version; never resolve its original diary bodies."""
import os
import tempfile
from pathlib import Path
from uuid import uuid4


def metadata(version):
    return (f"AI 作品 · {version['category']} · v{version['number']}\n"
            f"模型：{version['model'] or '未记录'}\n生成：{version['generated_at'] or '未记录'}")


def export_work(version, destination, kind):
    destination = Path(destination)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, suffix='.' + kind, delete=False) as handle:
            temporary = Path(handle.name)
        if kind == 'txt':
            temporary.write_text(version['title'] + '\n' + metadata(version) + '\n\n' + version['body_text'], encoding='utf-8-sig')
        elif kind == 'epub':
            from ebooklib import epub
            from lxml import etree
            from northdiary.services.epub import clean_body, INVALID_XML, STYLE
            def reject_image(_):
                raise ValueError('AI 作品导出暂不包含图片，请移除图片后重试，或导出 TXT。')
            body = clean_body(version['body_html'], reject_image)
            heading = etree.Element('h1')
            heading.text = INVALID_XML.sub('', version['title'])
            provenance = etree.Element('p', {'class': 'date'})
            provenance.text = INVALID_XML.sub('', metadata(version))
            body.insert(0, heading)
            body.insert(1, provenance)
            book = epub.EpubBook()
            book.set_identifier('urn:uuid:' + str(uuid4()))
            book.set_title(version['title'])
            book.set_language('zh-CN')
            css = epub.EpubItem(uid='style', file_name='style.css', media_type='text/css', content=STYLE)
            book.add_item(css)
            chapter = epub.EpubHtml(uid='work', title=version['title'], file_name='work.xhtml', lang='zh-CN')
            chapter.content = etree.tostring(body, encoding='unicode', method='xml')
            chapter.add_item(css)
            book.add_item(chapter)
            book.toc = (chapter,)
            book.spine = ['nav', chapter]
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav(title='目录'))
            if not epub.write_epub(str(temporary), book, {'raise_exceptions': True}):
                raise OSError('EPUB 写入失败')
        else:
            raise ValueError('不支持的导出格式')
        os.replace(temporary, destination)
        return destination
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
