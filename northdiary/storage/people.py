"""Stable person identities, independent of names and aliases in article text."""
from datetime import date
import re
from uuid import UUID, uuid4


FIELDS = ('id', 'name', 'code', 'birth_date', 'met_date', 'met_how', 'pinned', 'starred')


def validate_person(person):
    if (not isinstance(person, dict) or not set(FIELDS) <= set(person)
            or set(person) - set(FIELDS) - {'relationships', 'temporary_relationships'}):
        raise ValueError('人物资料字段无效')
    validate_relationships(person.get('relationships', []))
    validate_relationships(person.get('temporary_relationships', []))
    if not isinstance(person['id'], str) or str(UUID(person['id'])) != person['id']:
        raise ValueError('人物编号无效')
    for key, limit in (('name', 100), ('code', 100), ('birth_date', 32), ('met_date', 32), ('met_how', 10000)):
        value = person[key]
        if not isinstance(value, str) or len(value) > limit or '\x00' in value:
            raise ValueError('人物资料过长或无效')
    if not person['name'].strip() or not person['code'].strip():
        raise ValueError('姓名和代号不能为空')
    if any(person[k] != person[k].strip() for k in ('name', 'code')):
        raise ValueError('姓名和代号首尾不能有空格')
    for key in ('birth_date', 'met_date'):
        value = person[key]
        if not value:
            continue
        match = re.fullmatch(r'(\d{4})(?:-(\d{2}|未知)(?:-(\d{2}|未知))?)?', value)
        if not match:
            raise ValueError('日期请填写 YYYY、YYYY-MM 或 YYYY-MM-DD，也可留空或使用未知月/日')
        year, month, day = match.groups()
        if month == '未知' and day not in (None, '未知'):
            raise ValueError('月份未知时不能填写具体日子')
        date(int(year), int(month) if month not in (None, '未知') else 1,
             int(day) if day not in (None, '未知') else 1)
    if any(type(person[k]) is not int or person[k] not in (0, 1) for k in ('pinned', 'starred')):
        raise ValueError('人物状态无效')


def validate_relationships(names):
    if (not isinstance(names, list) or len(names) > 100
            or any(not isinstance(n, str) or not n.strip() or n != n.strip()
                   or len(n) > 100 or '\x00' in n for n in names)):
        raise ValueError('关系标签不能为空，每项最多 100 字，每类最多 100 项')
    if len(set(names)) != len(names):
        raise ValueError('关系标签不能重复')


class PeopleRepository:
    def __init__(self, database):
        self.database = database
        self.db = database.connection

    def list(self, query=''):
        query = query.strip()
        return [self.with_relationships(dict(r)) for r in self.db.execute('''SELECT * FROM people
            WHERE instr(lower(name),lower(?))>0 OR instr(lower(code),lower(?))>0
            ORDER BY pinned DESC, name COLLATE NOCASE, id''', (query, query))]

    def get(self, key):
        row = self.db.execute('SELECT * FROM people WHERE id=?', (key,)).fetchone()
        if row is None:
            raise KeyError('人物不存在')
        return self.with_relationships(dict(row))

    def save(self, person):
        validate_person(person)
        with self.db:
            self.db.execute('''INSERT INTO people VALUES (?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET name=excluded.name, code=excluded.code,
                birth_date=excluded.birth_date, met_date=excluded.met_date,
                met_how=excluded.met_how, pinned=excluded.pinned, starred=excluded.starred''',
                tuple(person[k] for k in FIELDS))
            if 'relationships' in person or 'temporary_relationships' in person:
                self.write_relationships(person['id'], person.get('relationships', []), person.get('temporary_relationships', []))
        return person['id']

    def create(self, name, code, **values):
        person = dict(id=str(uuid4()), name=name.strip(), code=code.strip(),
                      birth_date='', met_date='', met_how='', pinned=0, starred=0)
        person.update(values)
        self.save(person)
        return person

    def relationship_catalog(self):
        return [r[0] for r in self.db.execute('SELECT name FROM relationship_tags ORDER BY name')]

    def with_relationships(self, person):
        for key, table in [('relationships', 'person_relationship_tags'),
                           ('temporary_relationships', 'person_temporary_relationship_tags')]:
            names = [r[0] for r in self.db.execute(
                f'SELECT name FROM {table} WHERE person_id=? ORDER BY name', (person['id'],))]
            if names:
                person[key] = names
        return person

    def write_relationships(self, key, normal, temporary):
        # Called inside the caller's transaction, including EPUB import.
        validate_relationships(normal); validate_relationships(temporary)
        self.db.execute('DELETE FROM person_relationship_tags WHERE person_id=?', (key,))
        self.db.execute('DELETE FROM person_temporary_relationship_tags WHERE person_id=?', (key,))
        for name in normal:
            self.db.execute('INSERT OR IGNORE INTO relationship_tags VALUES (?)', (name,))
            self.db.execute('INSERT INTO person_relationship_tags VALUES (?,?)', (key, name))
        for name in temporary:
            self.db.execute('INSERT INTO person_temporary_relationship_tags VALUES (?,?)', (key, name))

    def delete(self, key):
        with self.db:
            self.db.execute('DELETE FROM people WHERE id=?', (key,))

    def for_article(self, article_id):
        return [self.with_relationships(dict(r)) for r in self.db.execute('''SELECT p.* FROM people p
            JOIN article_people ap ON ap.person_id=p.id WHERE ap.article_id=?
            ORDER BY p.pinned DESC, p.name, p.id''', (article_id,))]

    def articles(self, key):
        from northdiary.models import Article
        return [Article(**dict(r)) for r in self.db.execute('''SELECT a.* FROM articles a
            JOIN article_people ap ON ap.article_id=a.id
            WHERE ap.person_id=? AND a.deleted_at IS NULL ORDER BY a.diary_date DESC, a.id''', (key,))]
