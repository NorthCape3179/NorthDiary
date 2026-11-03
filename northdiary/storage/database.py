import sqlite3
from contextlib import closing
from uuid import uuid4
from pathlib import Path

SCHEMA_VERSION = 9
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
        if version < 4:
            try:
                if version == 3:
                    backups = self.root / 'backups'
                    backups.mkdir(exist_ok=True)
                    with closing(sqlite3.connect(backups / f'before-v4-{uuid4().hex}.sqlite3')) as snapshot:
                        self.connection.backup(snapshot)
                self.connection.executescript('''BEGIN IMMEDIATE;
                    CREATE TABLE people (
                        id TEXT PRIMARY KEY, name TEXT NOT NULL, code TEXT NOT NULL UNIQUE,
                        birth_date TEXT NOT NULL DEFAULT '', met_date TEXT NOT NULL DEFAULT '',
                        met_how TEXT NOT NULL DEFAULT '', pinned INTEGER NOT NULL DEFAULT 0,
                        starred INTEGER NOT NULL DEFAULT 0
                    );
                    CREATE TABLE article_people (
                        article_id TEXT NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
                        person_id TEXT NOT NULL REFERENCES people(id) ON DELETE CASCADE,
                        PRIMARY KEY(article_id, person_id)
                    );
                    CREATE INDEX people_articles ON article_people(person_id, article_id);
                    PRAGMA user_version=4;
                    COMMIT;''')
            except Exception:
                self.connection.rollback()
                self.connection.close()
                raise
        if version < 5:
            try:
                if version == 4:
                    backups = self.root / 'backups'
                    backups.mkdir(exist_ok=True)
                    with closing(sqlite3.connect(backups / f'before-v5-{uuid4().hex}.sqlite3')) as snapshot:
                        self.connection.backup(snapshot)
                self.connection.executescript('''BEGIN IMMEDIATE;
                    CREATE TABLE relationship_tags (
                        name TEXT PRIMARY KEY
                    );
                    CREATE TABLE person_relationship_tags (
                        person_id TEXT NOT NULL REFERENCES people(id) ON DELETE CASCADE,
                        name TEXT NOT NULL REFERENCES relationship_tags(name),
                        PRIMARY KEY(person_id, name)
                    );
                    CREATE TABLE person_temporary_relationship_tags (
                        person_id TEXT NOT NULL REFERENCES people(id) ON DELETE CASCADE,
                        name TEXT NOT NULL, PRIMARY KEY(person_id, name)
                    );
                    PRAGMA user_version=5;
                    COMMIT;''')
            except Exception:
                self.connection.rollback()
                self.connection.close()
                raise
        if version < 6:
            try:
                if version == 5:
                    backups = self.root / 'backups'
                    backups.mkdir(exist_ok=True)
                    with closing(sqlite3.connect(backups / f'before-v6-{uuid4().hex}.sqlite3')) as snapshot:
                        self.connection.backup(snapshot)
                self.connection.executescript('''BEGIN IMMEDIATE;
                    CREATE TABLE IF NOT EXISTS outside_articles (
                        article_id TEXT PRIMARY KEY REFERENCES articles(id) ON DELETE CASCADE
                    );
                    PRAGMA user_version=6;
                    COMMIT;''')
            except Exception:
                self.connection.rollback()
                self.connection.close()
                raise
        if version < 7:
            try:
                if version == 6:
                    backups = self.root / 'backups'
                    backups.mkdir(exist_ok=True)
                    with closing(sqlite3.connect(backups / f'before-v7-{uuid4().hex}.sqlite3')) as snapshot:
                        self.connection.backup(snapshot)
                self.connection.executescript('''BEGIN IMMEDIATE;
                    CREATE TABLE IF NOT EXISTS draft_articles (
                        article_id TEXT PRIMARY KEY REFERENCES articles(id) ON DELETE CASCADE
                    );
                    PRAGMA user_version=7;
                    COMMIT;''')
            except Exception:
                self.connection.rollback()
                self.connection.close()
                raise
        if version < 8:
            try:
                if version == 7:
                    backups = self.root / 'backups'
                    backups.mkdir(exist_ok=True)
                    with closing(sqlite3.connect(backups / f'before-v8-{uuid4().hex}.sqlite3')) as snapshot:
                        self.connection.backup(snapshot)
                self.connection.executescript('''BEGIN IMMEDIATE;
                    CREATE TABLE ai_conversations (
                        id TEXT PRIMARY KEY, mode TEXT NOT NULL, title TEXT NOT NULL,
                        article_ids TEXT NOT NULL, source_fingerprint TEXT NOT NULL DEFAULT '',
                        created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                    );
                    CREATE TABLE ai_turns (
                        id TEXT PRIMARY KEY,
                        conversation_id TEXT NOT NULL REFERENCES ai_conversations(id) ON DELETE CASCADE,
                        instruction TEXT NOT NULL, response TEXT NOT NULL DEFAULT '',
                        model TEXT NOT NULL, response_model TEXT NOT NULL DEFAULT '',
                        status TEXT NOT NULL CHECK(status IN ('running','complete','stopped','error','incomplete','interrupted')),
                        article_ids TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                        prompt_tokens INTEGER, completion_tokens INTEGER, cache_hit_tokens INTEGER,
                        cost_low_usd REAL, cost_high_usd REAL,
                        error_text TEXT NOT NULL DEFAULT '', finish_reason TEXT
                    );
                    CREATE INDEX ai_turns_conversation ON ai_turns(conversation_id,created_at);
                    PRAGMA user_version=8;
                    COMMIT;''')
            except Exception:
                self.connection.rollback()
                self.connection.close()
                raise
        if version < 9:
            try:
                if version == 8:
                    backups = self.root / 'backups'
                    backups.mkdir(exist_ok=True)
                    with closing(sqlite3.connect(backups / f'before-v9-{uuid4().hex}.sqlite3')) as snapshot:
                        self.connection.backup(snapshot)
                self.connection.executescript('''BEGIN IMMEDIATE;
                    CREATE TABLE ai_works (
                        id TEXT PRIMARY KEY, title TEXT NOT NULL, category TEXT NOT NULL,
                        created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                    );
                    CREATE TABLE ai_work_versions (
                        id TEXT PRIMARY KEY,
                        work_id TEXT NOT NULL REFERENCES ai_works(id) ON DELETE CASCADE,
                        number INTEGER NOT NULL, title TEXT NOT NULL, category TEXT NOT NULL,
                        body_html TEXT NOT NULL, body_text TEXT NOT NULL,
                        model TEXT NOT NULL DEFAULT '', generated_at TEXT NOT NULL DEFAULT '',
                        created_at TEXT NOT NULL, origin_turn_id TEXT, conversation_id TEXT,
                        sources_json TEXT NOT NULL DEFAULT '[]', note TEXT NOT NULL DEFAULT '',
                        UNIQUE(work_id,number)
                    );
                    CREATE INDEX ai_work_origin ON ai_work_versions(origin_turn_id);
                    PRAGMA user_version=9;
                    COMMIT;''')
            except Exception:
                self.connection.rollback()
                self.connection.close()
                raise
        self.connection.execute('PRAGMA journal_mode=WAL')
        self.connection.execute('PRAGMA synchronous=FULL')

    def close(self):
        self.connection.close()

