"""Explicit local installation diagnostics, using temporary synthetic data only."""
import json
import ssl
import tempfile
from pathlib import Path

from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QImage
from northdiary import __version__
from northdiary.storage.database import Database
from northdiary.storage.repository import ArticleRepository
from northdiary.storage.people import PeopleRepository
from northdiary.services.attachments import AttachmentService
from northdiary.services.epub import EpubExporter
from northdiary.services.importing import EpubImporter
from northdiary.models import ExportSelection
from northdiary.ui.main_window import MainWindow
from northdiary.ui.about_dialog import AboutDialog


def run_installation_check(output):
    output=Path(output).resolve();output.parent.mkdir(parents=True,exist_ok=True)
    result={'version':__version__,'openssl':ssl.OPENSSL_VERSION}
    with tempfile.TemporaryDirectory(dir=output.parent) as temp:
        root=Path(temp);db=Database(root/'source');target=None
        try:
            repo=ArticleRepository(db);people=PeopleRepository(db)
            person=people.create('展示人物','@TEST',relationships=['朋友'],temporary_relationships=['同行'])
            article=repo.create();images=AttachmentService(db)
            photo=root/'test.png';picture=QImage(40,30,QImage.Format.Format_RGB32);picture.fill(0xff819b88);picture.save(str(photo))
            images.add(article.id,photo);asset=images.list(article.id)[0]
            repo.save(article.id,'安装验证文章','2026-10-30',f'<p>安装验证</p><a href="ndiary-image:{asset["id"]}">图片</a>',
                      '安装验证',['测试分类'],['普通'],['临时'],people=[person['id']])
            book=root/'test.epub';EpubExporter(repo,images).export(ExportSelection((article.id,),'安装验证'),book)
            target=Database(root/'target');importer=EpubImporter(ArticleRepository(target),AttachmentService(target))
            imported=importer.import_file(book);assert imported.imported==1
            assert PeopleRepository(target).for_article(imported.article_ids[0])[0]['relationships']==['朋友']
            assert importer.import_file(book).imported==0
            result.update(sqlite=db.connection.execute('PRAGMA quick_check').fetchone()[0],epub_roundtrip=True,
                          attachments=len(AttachmentService(target).list(imported.article_ids[0])))
            window=MainWindow(db);window.set_theme(True,'dark');window.show();QCoreApplication.processEvents()
            assert not window.windowIcon().isNull()
            assert not window.paper.source.isNull()
            window.grab().save(str(output.with_suffix('.png')))
            about=AboutDialog(window);assert 'v1.7.0' in about.windowTitle();about.close()
            result.update(window_title=window.windowTitle(),icon=True,background=True,people=True)
            window.close();window.deleteLater();QCoreApplication.processEvents()
        finally:
            if target:target.close()
            db.close()
    result['success']=True
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return 0
