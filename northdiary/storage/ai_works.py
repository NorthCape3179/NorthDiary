"""Independent works with append-only content versions and durable source references."""
import json
from uuid import uuid4

from northdiary.storage.repository import now


CATEGORIES = ('点评', '分析报告', '故事', '旁注', '创作草稿')


class AIWorkRepository:
    def __init__(self, database):
        self.database = database
        self.db = database.connection

    def list(self, query='', category=None):
        sql = '''SELECT w.*,v.number,v.model,v.generated_at FROM ai_works w
            JOIN ai_work_versions v ON v.work_id=w.id AND v.number=
            (SELECT MAX(number) FROM ai_work_versions WHERE work_id=w.id) WHERE 1=1'''
        args = []
        if query.strip():
            sql += ' AND (instr(lower(w.title),lower(?))>0 OR instr(lower(v.body_text),lower(?))>0)'
            args.extend([query.strip()] * 2)
        if category:
            sql += ' AND w.category=?'
            args.append(category)
        sql += ' ORDER BY w.updated_at DESC,w.id'
        return [dict(row) for row in self.db.execute(sql, args)]

    def get(self, work_id, number=None):
        sql = 'SELECT * FROM ai_work_versions WHERE work_id=?'
        args = [work_id]
        if number is not None:
            sql += ' AND number=?'
            args.append(number)
        row = self.db.execute(sql + ' ORDER BY number DESC LIMIT 1', args).fetchone()
        if row is None:
            raise KeyError('作品或版本已不存在')
        result = dict(row)
        result['sources'] = json.loads(result['sources_json'])
        return result

    def versions(self, work_id):
        return [dict(row) for row in self.db.execute('''SELECT number,note,created_at,model
            FROM ai_work_versions WHERE work_id=? ORDER BY number DESC''', (work_id,))]

    def find_by_turn(self, turn_id):
        if not turn_id:
            return None
        row = self.db.execute('''SELECT v.work_id FROM ai_work_versions v JOIN ai_works w ON w.id=v.work_id
            WHERE v.origin_turn_id=? ORDER BY w.updated_at DESC,v.number DESC LIMIT 1''', (turn_id,)).fetchone()
        return row['work_id'] if row else None

    def source_references(self, ids):
        references = []
        for key in dict.fromkeys(ids):
            row = self.db.execute('SELECT id,title,diary_date FROM articles WHERE id=?', (key,)).fetchone()
            references.append(dict(row) if row else {'id': key, 'title': '原文已不存在', 'diary_date': ''})
        return references

    def save(self, data, work_id=None, note='保存作品'):
        title = data['title'].strip()
        if not title or not data['body_text'].strip():
            raise ValueError('请填写作品标题和正文')
        if data['category'] not in CATEGORIES:
            raise ValueError('请选择作品分类')
        stamp, version_id = now(), str(uuid4())
        with self.db:
            if work_id:
                if self.db.execute('SELECT 1 FROM ai_works WHERE id=?', (work_id,)).fetchone() is None:
                    raise ValueError('目标作品已删除，请另存为新作品')
                number = self.db.execute('SELECT MAX(number)+1 FROM ai_work_versions WHERE work_id=?', (work_id,)).fetchone()[0]
                self.db.execute('UPDATE ai_works SET title=?,category=?,updated_at=? WHERE id=?',
                                (title, data['category'], stamp, work_id))
            else:
                work_id, number = str(uuid4()), 1
                self.db.execute('INSERT INTO ai_works VALUES (?,?,?,?,?)', (work_id, title, data['category'], stamp, stamp))
            self.db.execute('''INSERT INTO ai_work_versions
                (id,work_id,number,title,category,body_html,body_text,model,generated_at,created_at,
                 origin_turn_id,conversation_id,sources_json,note) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (version_id, work_id, number, title, data['category'], data['body_html'], data['body_text'],
                 data.get('model', ''), data.get('generated_at', ''), stamp, data.get('origin_turn_id'),
                 data.get('conversation_id'), json.dumps(data.get('sources', []), ensure_ascii=False), note))
        return work_id, number

    def delete(self, work_id):
        with self.db:
            self.db.execute('DELETE FROM ai_works WHERE id=?', (work_id,))

    def copy_to_article(self, data, title, outside=True):
        """Create a new ordinary article atomically, only after a user's explicit action."""
        stamp, key = now(), str(uuid4())
        with self.db:
            position = self.db.execute('SELECT COALESCE(MAX(sort_order),0)+1 FROM articles').fetchone()[0]
            self.db.execute('''INSERT INTO articles
                (id,title,diary_date,body_html,body_text,created_at,updated_at,sort_order)
                VALUES (?,?,?,?,?,?,?,?)''',
                (key, title.strip() or data['title'], stamp[:10], data['body_html'], data['body_text'], stamp, stamp, position))
            if outside:
                self.db.execute('INSERT INTO outside_articles VALUES (?)', (key,))
            for table, relation, column, name in [('categories', 'article_categories', 'category_id', 'AI作品'),
                                                   ('tags', 'article_tags', 'tag_id', 'AI生成')]:
                self.db.execute(f'INSERT OR IGNORE INTO {table}(id,name) VALUES (?,?)', (str(uuid4()), name))
                label_id = self.db.execute(f'SELECT id FROM {table} WHERE name=?', (name,)).fetchone()[0]
                self.db.execute(f'INSERT INTO {relation}(article_id,{column}) VALUES (?,?)', (key, label_id))
        return key
