"""Versioned NorthDiary records carried inside an otherwise readable EPUB."""
import hashlib
import json
from datetime import date, datetime
import re
from uuid import UUID

FORMAT = 'NorthDiary-EPUB'
FORMAT_VERSION = 3
MANIFEST_PATH = 'EPUB/northdiary/manifest.json'
MAX_MANIFEST = 8 * 1024 * 1024
MAX_MEMBER = 32 * 1024 * 1024
MAX_TOTAL = 256 * 1024 * 1024


def validate_record(record):
    """The exporter and importer use the same record limits and date rules."""
    def require(condition):
        if not condition:
            raise ValueError('文章数据不符合 NorthDiary 交换格式')

    def string(value, limit=10000):
        require(isinstance(value, str) and len(value) <= limit and '\x00' not in value)
        return value

    require(isinstance(record, dict))
    value = string(record['id'], 36)
    require(str(UUID(value)) == value)
    require(bool(string(record['title']).strip()))
    match = re.fullmatch(r'(\d{4})-(\d{2}|未知)-(\d{2}|未知)', string(record['diary_date'], 32))
    require(match is not None)
    year, month, day = match.groups()
    require(1753 <= int(year) <= 9999 and (month != '未知' or day == '未知'))
    date(int(year), 1 if month == '未知' else int(month), 1 if day == '未知' else int(day))
    string(record['body_html'], 2 * 1024 * 1024)
    for key in ('created_at', 'updated_at'):
        datetime.fromisoformat(string(record[key], 64))
    require(type(record['pinned']) is int and record['pinned'] in (0, 1))
    for key in ('categories', 'tags', 'temporary_tags'):
        labels = record[key]
        require(isinstance(labels, list) and len(labels) <= 500)
        for label in labels:
            string(label, 1000)
            require(bool(label.strip()) and label == label.strip())
        require(len(set(labels)) == len(labels))
    people = record.get('people', [])
    require(isinstance(people, list) and len(people) <= 500)
    from northdiary.storage.people import validate_person
    for person in people:
        validate_person(person)
    require(len({p['id'] for p in people}) == len(people))
    require(len({p['code'] for p in people}) == len(people))
    require(isinstance(record['assets'], list) and len(record['assets']) <= 1000)
    for asset in record['assets']:
        require(isinstance(asset, dict))
        value = string(asset['id'], 36)
        require(str(UUID(value)) == value)
        string(asset['name'], 1000)
        string(asset['caption'], 10000)
        require(re.fullmatch(r'attachments/[A-Za-z0-9_-]+\.[A-Za-z0-9]+',
                             string(asset['relative_path'], 200)) is not None)
        require(re.fullmatch(r'EPUB/images/image-[1-9][0-9]*\.(png|jpg|gif)',
                             string(asset['archive_path'], 200)) is not None)
        require(asset['media_type'] in ('image/png', 'image/jpeg', 'image/gif'))
        require(re.fullmatch(r'[0-9a-f]{64}', string(asset['sha256'], 64)) is not None)


def image_type(content):
    if content.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'image/png', '.png'
    if content.startswith(b'\xff\xd8\xff'):
        return 'image/jpeg', '.jpg'
    if content.startswith((b'GIF87a', b'GIF89a')):
        return 'image/gif', '.gif'
    raise ValueError('EPUB 图片仅支持 PNG、JPEG、GIF')


def article_record(repository, article, assets):
    from northdiary.storage.people import PeopleRepository
    return {
        'id': article.id, 'title': article.title, 'diary_date': article.diary_date,
        'body_html': article.body_html, 'created_at': article.created_at,
        'updated_at': article.updated_at, 'pinned': int(article.pinned),
        'categories': repository.labels(article.id, 'categories'),
        'tags': repository.labels(article.id, 'tags'),
        'temporary_tags': repository.temporary_tags(article.id),
        'people': PeopleRepository(repository.database).for_article(article.id),
        'assets': sorted(assets, key=lambda item: item['relative_path']),
    }


def fingerprint(record):
    # Chapter order changes image filenames; identity must not depend on them.
    data = dict(record)
    if not data.get('people'):
        data.pop('people', None)
    else:
        data['people'] = sorted(data['people'], key=lambda p: p['id'])
    data['assets'] = [{k: v for k, v in asset.items() if k != 'archive_path'}
                      for asset in record['assets']]
    encoded = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()
