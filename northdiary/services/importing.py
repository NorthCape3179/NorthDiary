"""Import only the versioned NorthDiary data embedded in our own EPUBs."""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from uuid import UUID, uuid4, uuid5, NAMESPACE_URL
from urllib.parse import unquote, urlsplit
from zipfile import ZipFile, BadZipFile

from lxml import etree

from northdiary.services.epub import clean_body
from northdiary.services.native_format import (
    FORMAT, FORMAT_VERSION, MANIFEST_PATH, MAX_MANIFEST,
    article_record, fingerprint, image_type, validate_record, MAX_MEMBER, MAX_TOTAL,
)


@dataclass(frozen=True)
class PreparedArticle:
    record: dict
    target_id: str
    body_html: str
    body_text: str
    assets: tuple


@dataclass(frozen=True)
class ImportPreview:
    articles: tuple
    new_count: int
    conflict_count: int
    skipped_count: int


@dataclass(frozen=True)
class ImportResult:
    imported: int
    skipped: int
    conflicts: int
    article_ids: tuple


def _require(condition, message='NorthDiary 导入数据无效'):
    if not condition:
        raise ValueError(message)


def _string(value, limit=10000):
    _require(isinstance(value, str) and len(value) <= limit and '\x00' not in value)
    return value


def _uuid(value):
    _string(value, 36)
    _require(str(UUID(value)) == value, '文章或图片编号无效')


def _json_object(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, '导入清单含重复字段')
        result[key] = value
    return result


def _reference_path(reference):
    url = urlsplit(reference)
    path = unquote(url.path)
    _require(not (url.scheme or url.netloc or url.query or url.fragment)
             and '\\' not in path and '..' not in PurePosixPath(path).parts,
             '正文图片路径无效')
    return path


class EpubImporter:
    def __init__(self, repository, attachments):
        self.repository = repository
        self.attachments = attachments
        self.database = repository.database
        self.db = self.database.connection

    def prepare(self, source: Path) -> ImportPreview:
        """Read, validate and sanitize the entire book without changing local data."""
        source = Path(source)
        _require(source.suffix.lower() == '.epub', '请选择 NorthDiary 导出的 .epub 文件')
        try:
            with ZipFile(source) as archive:
                members = archive.infolist()
                _require(len(members) <= 5000 and sum(i.file_size for i in members) <= MAX_TOTAL,
                         '导入文件过大，请分批导出文章')
                names = [i.filename for i in members]
                _require(len(set(names)) == len(names), 'EPUB 含重复文件名')
                for info in members:
                    name = info.filename.rstrip('/')
                    path = PurePosixPath(name)
                    _require(name and not path.is_absolute() and '..' not in path.parts
                             and '\\' not in name and ':' not in name and str(path) == name,
                             'EPUB 含不安全路径')
                    _require(info.file_size <= MAX_MEMBER and not info.flag_bits & 1,
                             'EPUB 文件过大或已加密')
                    _require((info.external_attr >> 16) & 0o170000 != 0o120000,
                             'EPUB 不允许符号链接')
                _require('mimetype' in names and archive.read('mimetype') == b'application/epub+zip',
                         '不是有效的 EPUB 文件')
                _require(MANIFEST_PATH in names,
                         '仅支持新版 NorthDiary 导出的 EPUB；旧版文件请重新导出')
                _require(archive.getinfo(MANIFEST_PATH).file_size <= MAX_MANIFEST, 'NorthDiary 清单过大')
                manifest = json.loads(archive.read(MANIFEST_PATH), object_pairs_hook=_json_object)
                _require(isinstance(manifest, dict) and manifest.get('format') == FORMAT,
                         '不是 NorthDiary 专用导出格式')
                _require(type(manifest.get('version')) is int and manifest['version'] in (1, 2, FORMAT_VERSION),
                         '此导出格式版本暂不支持，请更新软件')
                records = manifest.get('articles')
                _require(isinstance(records, list) and 0 < len(records) <= 1000, '文章清单无效')
                _require(sum(len(r.get('assets', [])) for r in records if isinstance(r, dict)) <= 5000,
                         '图片引用过多，请分批导出文章')
                prepared, ids, image_cache = [], set(), {}
                people_seen, codes_seen = {}, {}
                for record in records:
                    if manifest['version'] >= 2:
                        _require(isinstance(record, dict) and 'people' in record, '人物数据清单缺失')
                    validate_record(record)
                    for person in record.get('people', []):
                        old = people_seen.setdefault(person['id'], person)
                        _require(old == person, '同一人物的资料不一致')
                        owner = codes_seen.setdefault(person['code'], person['id'])
                        _require(owner == person['id'], '不同人物不能使用同一代号')
                    article = self._prepare_article(archive, record, image_cache)
                    _require(record['id'] not in ids, '同一本书不能重复包含同一篇文章')
                    ids.add(record['id'])
                    prepared.append(article)
        except (BadZipFile, KeyError, TypeError, UnicodeError, json.JSONDecodeError, RecursionError) as error:
            raise ValueError('EPUB 损坏或缺少有效的 NorthDiary 数据') from error
        counts = {'new': 0, 'conflict': 0, 'skip': 0}
        for article in prepared:
            counts[self._status(article)] += 1
        return ImportPreview(tuple(prepared), counts['new'], counts['conflict'], counts['skip'])

    def _prepare_article(self, archive, record, image_cache):
        validate_record(record)
        by_path, by_id, staged = {}, {}, []
        for asset in record['assets']:
            _require(isinstance(asset, dict))
            _uuid(asset['id'])
            original = _string(asset['relative_path'], 200)
            _require(re.fullmatch(r'attachments/[A-Za-z0-9_-]+\.[A-Za-z0-9]+', original) is not None,
                     '图片原始路径无效')
            path = _string(asset['archive_path'], 200)
            _require(re.fullmatch(r'EPUB/images/image-[1-9][0-9]*\.(png|jpg|gif)', path) is not None,
                     '书内图片路径无效')
            if path not in image_cache:
                content = archive.read(path)
                media, suffix = image_type(content)
                image_cache[path] = content, media, suffix, hashlib.sha256(content).hexdigest()
            content, media, suffix, digest = image_cache[path]
            _require(asset['media_type'] == media and asset['sha256'] == digest,
                     '图片校验失败，文件可能已损坏')
            _string(asset['name'], 1000)
            _string(asset['caption'], 10000)
            _require(original not in by_path and asset['id'] not in by_id, '图片记录重复')
            key = str(uuid4())
            item = dict(id=key, relative_path='attachments/' + key + suffix,
                        name=asset['name'], caption=asset['caption'], media_type=media, content=content)
            by_path[original] = item
            by_id[asset['id']] = item
            staged.append(item)

        used = set()

        def resolve_image(reference):
            reference = _reference_path(reference)
            _require(reference in by_path, '正文图片缺少对应资源')
            item = by_path[reference]
            used.add(item['id'])
            return item['relative_path']

        def resolve_link(identifier):
            _require(identifier in by_id, '正文图片入口缺少对应资源')
            item = by_id[identifier]
            used.add(item['id'])
            return item['id'], item['caption'] or Path(item['name']).stem

        body = clean_body(record['body_html'], resolve_image, resolve_link, preserve_photo_links=True)
        _require(used == {item['id'] for item in staged}, '图片清单与正文引用不一致')
        target = str(uuid5(NAMESPACE_URL, 'northdiary-import:' + record['id'] + ':' + fingerprint(record)))
        return PreparedArticle(record, target, etree.tostring(body, encoding='unicode', method='xml'),
                               etree.tostring(body, encoding='unicode', method='text'), tuple(staged))

    def _current_record(self, article):
        rows = self.attachments.list(article.id)
        by_path = {row['relative_path']: row for row in rows}
        by_id = {row['id']: row for row in rows}
        used = set()

        def resolve(reference):
            reference = _reference_path(reference)
            _require(reference in by_path)
            used.add(reference)
            return reference

        def link(identifier):
            row = by_id[identifier]
            return row['relative_path'], row['caption'] or Path(row['name']).stem

        clean_body(article.body_html, resolve, link)
        assets = []
        for path in used:
            row = by_path[path]
            source = (self.database.root / path).resolve(strict=True)
            _require(source.is_relative_to(self.database.root / 'attachments'))
            content = source.read_bytes()
            media, _ = image_type(content)
            assets.append(dict(id=row['id'], relative_path=path, name=row['name'], caption=row['caption'],
                               media_type=media, sha256=hashlib.sha256(content).hexdigest()))
        return article_record(self.repository, article, assets)

    def _status(self, article):
        # A deterministic import ID makes repeated imports idempotent, even if
        # the imported local copy was edited or moved to the recycle bin later.
        if self.db.execute('SELECT 1 FROM articles WHERE id=?', (article.target_id,)).fetchone():
            return 'skip'
        try:
            current = self.repository.get(article.record['id'])
        except KeyError:
            return 'new'
        if not current.deleted_at:
            try:
                if fingerprint(self._current_record(current)) == fingerprint(article.record):
                    return 'skip'
            except (ValueError, KeyError, OSError):
                pass
        return 'conflict'

    def apply(self, preview: ImportPreview) -> ImportResult:
        """Commit all articles in one transaction; remove new files on failure."""
        root = self.database.root / 'attachments'
        _require(not root.is_symlink() and root.resolve() == root, '附件目录不能是符号链接')
        _require(not self.db.in_transaction, '请先保存当前修改后再导入')
        created, keys = [], []
        skipped = conflicts = 0
        try:
            with self.db:
                self.db.execute('BEGIN IMMEDIATE')
                position = self.db.execute('SELECT COALESCE(MAX(sort_order),0) FROM articles').fetchone()[0]
                for article in preview.articles:
                    status = self._status(article)
                    if status == 'skip':
                        skipped += 1
                        continue
                    record = article.record
                    conflicts += status == 'conflict'
                    position += 1
                    title = record['title'] + ('（导入副本）' if status == 'conflict' else '')
                    self.db.execute('''INSERT INTO articles
                        (id,title,diary_date,body_html,body_text,created_at,updated_at,deleted_at,pinned,sort_order)
                        VALUES (?,?,?,?,?,?,?,NULL,?,?)''',
                        (article.target_id, title, record['diary_date'], article.body_html, article.body_text,
                         record['created_at'], record['updated_at'], record['pinned'], position))
                    for kind in ('categories', 'tags'):
                        column = 'category_id' if kind == 'categories' else 'tag_id'
                        for name in record[kind]:
                            self.db.execute(f'INSERT OR IGNORE INTO {kind}(id,name) VALUES (?,?)',
                                            (str(uuid4()), name))
                            key = self.db.execute(f'SELECT id FROM {kind} WHERE name=?', (name,)).fetchone()[0]
                            self.db.execute(f'INSERT INTO article_{kind}(article_id,{column}) VALUES (?,?)',
                                            (article.target_id, key))
                    for person in record.get('people', []):
                        person_id = self._import_person(person)
                        self.db.execute('INSERT INTO article_people VALUES (?,?)', (article.target_id, person_id))
                    for name in record['temporary_tags']:
                        self.db.execute('INSERT INTO article_temporary_tags VALUES (?,?)', (article.target_id, name))
                    for index, asset in enumerate(article.assets):
                        destination = self.database.root / asset['relative_path']
                        with destination.open('xb') as handle:
                            created.append(destination)
                            handle.write(asset['content'])
                        self.db.execute('''INSERT INTO attachments
                            (id,article_id,name,relative_path,mime_type,caption,position) VALUES (?,?,?,?,?,?,?)''',
                            (asset['id'], article.target_id, asset['name'], asset['relative_path'],
                             asset['media_type'], asset['caption'], index))
                    keys.append(article.target_id)
        except BaseException:
            for path in created:
                path.unlink(missing_ok=True)
            raise
        return ImportResult(len(keys), skipped, conflicts, tuple(keys))

    def _import_person(self, person):
        # Never overwrite an existing profile. Conflicting revisions have stable
        # copy IDs so later packages reuse them, including locally edited copies.
        from northdiary.storage.people import FIELDS, PeopleRepository
        current = self.db.execute('SELECT * FROM people WHERE id=?', (person['id'],)).fetchone()
        people_repository = PeopleRepository(self.database)
        if current is not None and people_repository.get(person['id']) == person:
            return person['id']
        code_owner = self.db.execute('SELECT id FROM people WHERE code=?', (person['code'],)).fetchone()
        value = dict(person)
        if current is not None or code_owner is not None:
            digest = hashlib.sha256(json.dumps(person, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
            value['id'] = str(uuid5(NAMESPACE_URL, 'northdiary-person:' + person['id'] + ':' + digest))
            if self.db.execute('SELECT 1 FROM people WHERE id=?', (value['id'],)).fetchone():
                return value['id']
        if code_owner is not None:
            base = person['code'][:50]
            suffix = value['id'].replace('-', '')
            value['code'] = base + '（导入-' + suffix + '）'
            count = 0
            while self.db.execute('SELECT 1 FROM people WHERE code=?', (value['code'],)).fetchone():
                count += 1
                value['code'] = base + '（导入-' + suffix + '-' + str(count) + '）'
        self.db.execute('INSERT INTO people VALUES (?,?,?,?,?,?,?,?)', tuple(value[k] for k in FIELDS))
        people_repository.write_relationships(value['id'], value.get('relationships', []), value.get('temporary_relationships', []))
        return value['id']

    def import_file(self, source: Path) -> ImportResult:
        return self.apply(self.prepare(source))
