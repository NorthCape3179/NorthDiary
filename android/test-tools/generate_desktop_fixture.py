"""Generate fictional interoperability fixtures with the actual desktop exporter."""
import base64
import hashlib
import json
import sys
import tempfile
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5
from zipfile import ZipFile

repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo_root))
from northdiary.models import ExportSelection
from northdiary.services.attachments import AttachmentService
from northdiary.services.epub import EpubExporter
from northdiary.services.native_format import fingerprint
from northdiary.storage.database import Database
from northdiary.storage.people import PeopleRepository
from northdiary.storage.repository import ArticleRepository


def generate(destination):
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        db = Database(root / 'data')
        try:
            repo, attachments, people = ArticleRepository(db), AttachmentService(db), PeopleRepository(db)
            value = people.create('测试同学', 'QA-CLASSMATE', birth_date='2005', met_date='2023-09',
                                  met_how='测试用虚构人物', pinned=1, starred=1,
                                  relationships=['同学'], temporary_relationships=['同行'])
            person = value['id'] if isinstance(value, dict) else value
            first = repo.create()
            image = root / '测试照片.png'
            image.write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a4uoAAAAASUVORK5CYII='))
            path = attachments.add(first.id, image)
            repo.save(first.id, '校园里的测试回忆', '2026-未知-未知',
                      f'<p style="text-align:center"><b>中文加粗</b>与<i>斜体</i></p><p><img src="{path}"/></p>',
                      '中文加粗与斜体', ['校园', '往事'], ['回忆'], ['临时标签'], [person])
            with db.connection:
                db.connection.execute('UPDATE articles SET pinned=1 WHERE id=?', (first.id,))
                db.connection.execute('UPDATE attachments SET caption=? WHERE article_id=?', ('测试照片说明', first.id))
            second = repo.create()
            repo.save(second.id, '时间线之外的测试信', '2025-10-未知', '<p>没有具体事件日期的测试正文。</p>',
                      '没有具体事件日期的测试正文。', ['书信'], ['回忆'], [], [person])
            with db.connection:
                db.connection.execute('INSERT INTO outside_articles VALUES (?)', (second.id,))
            book = root / 'desktop.epub'
            EpubExporter(repo, attachments).export(ExportSelection((first.id, second.id), '跨端导入测试文集', 'NorthDiary QA'), book)
            with ZipFile(book) as archive:
                manifest = json.loads(archive.read('EPUB/northdiary/manifest.json'))
            person_hash = hashlib.sha256(json.dumps(manifest['articles'][0]['people'][0], ensure_ascii=False, sort_keys=True).encode()).hexdigest()
            expected = {'articles': [{'id': record['id'], 'target': str(uuid5(NAMESPACE_URL, 'northdiary-import:' + record['id'] + ':' + fingerprint(record))),
                                      'fingerprint': fingerprint(record)} for record in manifest['articles']],
                        'person': person, 'person_copy': str(uuid5(NAMESPACE_URL, 'northdiary-person:' + person + ':' + person_hash))}
            (destination / 'desktop-v4.epub.base64').write_text(base64.b64encode(book.read_bytes()).decode() + '\n')
            (destination / 'desktop-v4.expected.json').write_text(json.dumps(expected, ensure_ascii=False, indent=2) + '\n')
            print('Generated desktop EPUB fixture:', book.stat().st_size, 'bytes')
        finally:
            db.close()


if __name__ == '__main__':
    generate(Path(sys.argv[1]) if len(sys.argv) > 1 else repo_root / 'android/app/src/androidTest/assets')
