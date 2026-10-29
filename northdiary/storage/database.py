import sqlite3
from contextlib import closing
from uuid import uuid4
from pathlib import Path

SCHEMA_VERSION = 3
SCHEMA = '''
BEGIN IMMEDIATE;
CREATE TABLE articles (
 id TEXT PRIMARY KEY, title TEXT NOT NULL, diary_date TEXT NOT NULL,
 body_html TEXT NOT NULL DEFAULT '', body_text TEXT NOT NULL DEFAULT '',
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL, deleted_at TEXT
);
CREATE INDEX articles_date ON articles(diary_date DESC);
CREATE TABLE categories (
 id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE,
 parent_id TEXT REFERENCES categories(id) ON DELETE SET NULL
);
CREATE TABLE tags (id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE);
CREATE TABLE article_categories (
 article_id TEXT REFERENCES articles(id) ON DELETE CASCADE,
 category_id TEXT REFERENCES categories(id) ON DELETE CASCADE,
 PRIMARY KEY(article_id, category_id)
);
CREATE TABLE article_tags (
 article_id TEXT REFERENCES articles(id) ON DELETE CASCADE,
 tag_id TEXT REFERENCES tags(id) ON DELETE CASCADE,
 PRIMARY KEY(article_id, tag_id)
);
CREATE TABLE attachments (
 id TEXT PRIMARY KEY, article_id TEXT NOT NULL REFERENCES articles(id),
 name TEXT NOT NULL, relative_path TEXT NOT NULL UNIQUE,
 mime_type TEXT NOT NULL, caption TEXT NOT NULL DEFAULT '',
 position INTEGER NOT NULL DEFAULT 0
);
PRAGMA user_version=1;
COMMIT;
'''


class Database:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / 'attachments').mkdir(exist_ok=True)
        self.connection = sqlite3.connect(self.root / 'northdiary.sqlite3', timeout=5)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute('PRAGMA foreign_keys=ON')
        version = self.connection.execute('PRAGMA user_version').fetchone()[0]
        if version > SCHEMA_VERSION:
            self.connection.close()
            raise RuntimeError('数据来自更新版本的 NorthDiary，请使用新版程序打开。')
        if version == 0:
            self.connection.executescript(SCHEMA)
        if version < 2:
            try:
                if version == 1:
                    backups = self.root / 'backups'
                    backups.mkdir(exist_ok=True)
                    with closing(sqlite3.connect(backups / f'before-v2-{uuid4().hex}.sqlite3')) as snapshot:
                        self.connection.backup(snapshot)
                self.connection.executescript('''BEGIN IMMEDIATE;
                    CREATE TABLE article_temporary_tags (
                        article_id TEXT NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
                        name TEXT NOT NULL, PRIMARY KEY(article_id, name)
                    );
                    PRAGMA user_version=2;
                    COMMIT;''')
            except Exception:
                self.connection.rollback()
                self.connection.close()
                raise
        if version < 3:
            try:
                if version == 2:
                    backups = self.root / 'backups'
                    backups.mkdir(exist_ok=True)
                    with closing(sqlite3.connect(backups / f'before-v3-{uuid4().hex}.sqlite3')) as snapshot:
                        self.connection.backup(snapshot)
                self.connection.executescript('''BEGIN IMMEDIATE;
                    ALTER TABLE articles ADD COLUMN pinned INTEGER NOT NULL DEFAULT 0;
                    ALTER TABLE articles ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0;
                    WITH ranks AS (SELECT id, ROW_NUMBER() OVER (ORDER BY diary_date DESC, created_at DESC) AS position FROM articles)
                    UPDATE articles SET sort_order=(SELECT position FROM ranks WHERE ranks.id=articles.id);
                    PRAGMA user_version=3;
                    COMMIT;''')
            except Exception:
                self.connection.rollback()
                self.connection.close()
                raise
        self.connection.execute('PRAGMA journal_mode=WAL')
        self.connection.execute('PRAGMA synchronous=FULL')

    def close(self):
        self.connection.close()
