"""Delete reusable definitions and references atomically."""
def delete_definition(db, kind, name):
    with db:
        if kind == 'categories':
            row = db.execute('SELECT id FROM categories WHERE name=?', (name,)).fetchone()
            if row:
                db.execute('UPDATE categories SET parent_id=NULL WHERE parent_id=?', (row[0],))
                db.execute('DELETE FROM article_categories WHERE category_id=?', (row[0],))
                db.execute('DELETE FROM categories WHERE id=?', (row[0],))
        elif kind == 'tags':
            db.execute('DELETE FROM article_tags WHERE tag_id IN (SELECT id FROM tags WHERE name=?)', (name,))
            db.execute('DELETE FROM tags WHERE name=?', (name,))
        elif kind == 'relationships':
            db.execute('DELETE FROM person_relationship_tags WHERE name=?', (name,))
            db.execute('DELETE FROM relationship_tags WHERE name=?', (name,))
        else:
            raise ValueError('未知定义类型')
