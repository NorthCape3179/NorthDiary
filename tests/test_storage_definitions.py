from contextlib import closing
import tempfile, unittest, sqlite3
from pathlib import Path
from northdiary.storage.database import Database
from northdiary.storage.repository import ArticleRepository
from northdiary.services.label_definitions import delete_definition
from northdiary.services.storage_location import copy_data

class StorageAndDefinitionsTests(unittest.TestCase):
    def test_definition_delete_preserves_article_and_child(self):
        with tempfile.TemporaryDirectory() as temp:
            database=Database(Path(temp)); repo=ArticleRepository(database); article=repo.create(); db=database.connection
            repo.save(article.id,'测试','2020-未知-未知','<p>正文</p>','正文',['父分类'],['标签'])
            parent=db.execute('select id from categories').fetchone()[0]
            with db:
                db.execute('insert into categories values(?,?,?)',('child','子分类',parent))
                db.execute('insert into relationship_tags values(?)',('朋友',))
            for kind,name in [('categories','父分类'),('tags','标签'),('relationships','朋友')]:delete_definition(db,kind,name)
            self.assertEqual(repo.get(article.id).body_text,'正文')
            self.assertIsNone(db.execute('select parent_id from categories where id=?',('child',)).fetchone()[0])
            self.assertEqual(db.execute('select count(*) from article_tags').fetchone()[0],0)
            self.assertFalse(db.execute('pragma foreign_key_check').fetchall());database.close()

    def test_live_snapshot_copies_attachments_and_rejects_overlap(self):
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'source'; target=Path(temp)/'target';database=Database(source)
            article=ArticleRepository(database).create();(source/'attachments'/'image.jpg').write_bytes(b'photo')
            (source/'northdiary.lock').write_text('lock')
            copy_data(database,target)
            with closing(sqlite3.connect(target/'northdiary.sqlite3')) as db:
                self.assertEqual(db.execute('select id from articles').fetchone()[0],article.id)
            self.assertEqual((target/'attachments'/'image.jpg').read_bytes(),b'photo')
            self.assertFalse((target/'northdiary.lock').exists())
            for bad in (source,source/'nested',target):
                with self.assertRaises(ValueError):copy_data(database,bad)
            self.assertTrue((source/'northdiary.sqlite3').exists());database.close()
