from datetime import datetime
from uuid import uuid4

from northdiary.models import Article
from northdiary.storage.database import Database


def now():
    return datetime.now().astimezone().isoformat(timespec='microseconds')


class ArticleRepository:
    def __init__(self, database: Database):
        self.database = database
        self.db = database.connection

    def create(self):
        stamp = now()
        position = self.db.execute('SELECT COALESCE(MAX(sort_order),0)+1 FROM articles').fetchone()[0]
        article = Article(str(uuid4()), '未命名文章', stamp[:10], '', '', stamp, stamp, sort_order=position)
        with self.db:
            self.db.execute('INSERT INTO articles VALUES (?,?,?,?,?,?,?,?,?,?)',
                            tuple(vars(article).values()))
        return article

    def get(self, article_id):
        row = self.db.execute('SELECT * FROM articles WHERE id=?', (article_id,)).fetchone()
        if row is None:
            raise KeyError('文章不存在')
        return Article(**dict(row))

    def list(self, query='', category=None, trash=False, tag=None, sort='created_desc', pinned_first=True):
        orders = {
            'created_desc': 'a.created_at DESC', 'created_asc': 'a.created_at ASC',
            'updated_desc': 'a.updated_at DESC', 'updated_asc': 'a.updated_at ASC',
            'title': 'a.title COLLATE NOCASE ASC', 'manual': 'a.sort_order ASC',
        }
        if sort not in orders:
            raise ValueError('未知排序方式')
        sql = 'SELECT a.* FROM articles a WHERE a.deleted_at IS ' + ('NOT NULL' if trash else 'NULL')
        args = []
        if query.strip():
            # Literal substring search, so percent and underscore are ordinary characters.
            sql += ' AND (instr(lower(a.title),lower(?))>0 OR instr(lower(a.body_text),lower(?))>0)'
            args += [query.strip(), query.strip()]
        if category:
            sql += ' AND EXISTS (SELECT 1 FROM article_categories ac JOIN categories c ON c.id=ac.category_id WHERE ac.article_id=a.id AND c.name=?)'
            args.append(category)
        if tag:
            sql += ' AND EXISTS (SELECT 1 FROM article_tags at JOIN tags t ON t.id=at.tag_id WHERE at.article_id=a.id AND t.name=?)'
            args.append(tag)
        sql += ' ORDER BY ' + ('a.pinned DESC,' if pinned_first else '') + orders[sort] + ',a.created_at DESC,a.id ASC'
        return [Article(**dict(row)) for row in self.db.execute(sql, args)]

    def save(self, article_id, title, diary_date, body_html, body_text, categories, tags, temporary_tags=None):
        # Content and organization commit together, never partially.
        with self.db:
            cursor = self.db.execute('''UPDATE articles SET title=?,diary_date=?,body_html=?,
                body_text=?,updated_at=? WHERE id=? AND deleted_at IS NULL''',
                (title.strip() or '未命名文章', diary_date, body_html, body_text, now(), article_id))
            if cursor.rowcount != 1:
                raise ValueError('文章已移入回收站或不存在，未覆盖内容。')
            for table, relation, column, names in (
                ('categories', 'article_categories', 'category_id', categories),
                ('tags', 'article_tags', 'tag_id', tags),
            ):
                self.db.execute(f'DELETE FROM {relation} WHERE article_id=?', (article_id,))
                for name in dict.fromkeys(n.strip() for n in names if n.strip()):
                    self.db.execute(f'INSERT OR IGNORE INTO {table}(id,name) VALUES (?,?)', (str(uuid4()), name))
                    entity_id = self.db.execute(f'SELECT id FROM {table} WHERE name=?', (name,)).fetchone()[0]
                    self.db.execute(f'INSERT INTO {relation}(article_id,{column}) VALUES (?,?)', (article_id, entity_id))
            if temporary_tags is not None:
                self.db.execute('DELETE FROM article_temporary_tags WHERE article_id=?', (article_id,))
                for name in dict.fromkeys(n.strip() for n in temporary_tags if n.strip()):
                    self.db.execute('INSERT INTO article_temporary_tags VALUES (?,?)', (article_id, name))

    def tags(self):
        return [r[0] for r in self.db.execute('SELECT name FROM tags ORDER BY name')]

    def temporary_tags(self, article_id):
        return [r[0] for r in self.db.execute('SELECT name FROM article_temporary_tags WHERE article_id=? ORDER BY name', (article_id,))]

    def labels(self, article_id, kind):
        if kind not in ('categories', 'tags'):
            raise ValueError(kind)
        column = 'category_id' if kind == 'categories' else 'tag_id'
        return [r[0] for r in self.db.execute(f'''SELECT t.name FROM {kind} t JOIN article_{kind} r
            ON r.{column}=t.id WHERE r.article_id=? ORDER BY t.name''', (article_id,))]

    def categories(self):
        return [r[0] for r in self.db.execute('SELECT name FROM categories ORDER BY name')]

    def set_deleted(self, article_id, deleted=True):
        with self.db:
            self.db.execute('UPDATE articles SET deleted_at=?,updated_at=? WHERE id=?',
                            (now() if deleted else None, now(), article_id))

    def set_pinned(self, article_id, pinned):
        with self.db:
            position = self.db.execute('SELECT COALESCE(MAX(sort_order),0)+1 FROM articles WHERE pinned=?', (int(pinned),)).fetchone()[0]
            cursor = self.db.execute('UPDATE articles SET pinned=?,sort_order=? WHERE id=? AND deleted_at IS NULL',
                                    (int(pinned), position, article_id))
            if cursor.rowcount != 1:
                raise ValueError('文章已不存在或在回收站中')

    def permanently_delete(self, article_id):
        """Only trashed articles; remove managed copies, never original source files."""
        with self.db:
            article = self.get(article_id)
            if not article.deleted_at:
                raise ValueError('只能永久删除回收站中的文章')
            paths = [row[0] for row in self.db.execute('SELECT relative_path FROM attachments WHERE article_id=?', (article_id,))]
            self.db.execute('DELETE FROM attachments WHERE article_id=?', (article_id,))
            self.db.execute('DELETE FROM articles WHERE id=?', (article_id,))
        failed = []
        root = (self.database.root / 'attachments').resolve()
        for relative in paths:
            path = (self.database.root / relative).resolve()
            if not path.is_relative_to(root) or path == root:
                failed.append(relative)
                continue
            try:
                path.unlink(missing_ok=True)
            except OSError:
                failed.append(relative)
        return failed

    def reorder(self, article_ids):
        if len(set(article_ids)) != len(article_ids):
            raise ValueError('排序中不能出现重复文章')
        with self.db:
            articles = [self.get(key) for key in article_ids]
            if any(article.deleted_at for article in articles):
                raise ValueError('请在正常文章列表中调整顺序')
            if [a.pinned for a in articles] != sorted([a.pinned for a in articles], reverse=True):
                raise ValueError('置顶文章请在置顶区内排序；可用图钉按钮改变置顶状态')
            # Permute only visible slots, preserving positions of filtered-out articles.
            for pinned in (0, 1):
                group = [a for a in articles if a.pinned == pinned]
                slots = sorted(a.sort_order for a in group)
                for article, position in zip(group, slots):
                    self.db.execute('UPDATE articles SET sort_order=? WHERE id=?', (position, article.id))
