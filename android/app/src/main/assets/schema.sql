-- Desktop schema v7, derived from northdiary/storage/database.py.
CREATE TABLE articles (
 id TEXT PRIMARY KEY, title TEXT NOT NULL, diary_date TEXT NOT NULL,
 body_html TEXT NOT NULL DEFAULT '', body_text TEXT NOT NULL DEFAULT '',
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL, deleted_at TEXT
, pinned INTEGER NOT NULL DEFAULT 0, sort_order INTEGER NOT NULL DEFAULT 0);
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
CREATE TABLE article_temporary_tags (
                        article_id TEXT NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
                        name TEXT NOT NULL, PRIMARY KEY(article_id, name)
                    );
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
CREATE TABLE outside_articles (
                        article_id TEXT PRIMARY KEY REFERENCES articles(id) ON DELETE CASCADE
                    );
CREATE TABLE draft_articles (
                        article_id TEXT PRIMARY KEY REFERENCES articles(id) ON DELETE CASCADE
                    );
CREATE INDEX articles_date ON articles(diary_date DESC);
CREATE INDEX people_articles ON article_people(person_id, article_id);