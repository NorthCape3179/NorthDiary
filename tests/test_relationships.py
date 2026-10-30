import sqlite3
import unittest
from contextlib import closing
from unittest.mock import patch
import test_people
from northdiary.storage.database import Database
from northdiary.storage.people import PeopleRepository
from northdiary.ui.people_dialog import PersonEditor, relationship_text


class RelationshipTests(test_people.PeopleTests):
    # Run only our new tests; the inherited suite is run separately.
    def test_relationship_scopes_restart_and_removal(self):
        p = dict(self.person, relationships=['同学'], temporary_relationships=['旅行认识'])
        self.people.save(p)
        other = self.people.create('另一个人', '@OTHER')
        self.assertEqual(self.people.relationship_catalog(), ['同学'])
        self.assertNotIn('temporary_relationships', self.people.get(other['id']))
        again = Database(self.db.root)
        try:
            self.assertEqual(PeopleRepository(again).get(p['id']), p)
        finally:
            again.close()
        self.people.save(dict(p, relationships=[], temporary_relationships=[]))
        self.assertNotIn('relationships', self.people.get(p['id']))
        self.assertEqual(self.people.relationship_catalog(), ['同学'])
        self.people.delete(p['id'])
        self.assertEqual(self.db.connection.execute('SELECT count(*) FROM person_relationship_tags').fetchone()[0], 0)

    def test_editor_cancel_and_save(self):
        editor = PersonEditor(self.people, self.person)
        self.windows.append(editor)
        editor.relationships.add_tag('朋友')
        editor.relationships.add_tag('只此人物', True)
        editor.reject()
        self.assertEqual(self.people.relationship_catalog(), [])
        self.assertNotIn('relationships', self.people.get(self.person['id']))
        editor = PersonEditor(self.people, self.person)
        self.windows.append(editor)
        editor.relationships.add_tag('朋友')
        editor.relationships.add_tag('只此人物', True)
        editor.save()
        self.assertIn('朋友', relationship_text(self.people.get(self.person['id'])))
        new = PersonEditor(self.people)
        self.windows.append(new)
        self.assertEqual(new.relationships.catalog, ['朋友'])
        self.assertEqual(new.relationships.temporary_names, [])

    def test_invalid_relations_and_sql_failure_roll_back_person(self):
        with self.assertRaises(ValueError):
            self.people.save(dict(self.person, name='不应保存', relationships=[' ']))
        self.db.connection.execute("CREATE TRIGGER reject_relation BEFORE INSERT ON person_relationship_tags BEGIN SELECT RAISE(ABORT, 'test'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.people.save(dict(self.person, name='不应保存', relationships=['不应留下']))
        self.assertEqual(self.people.get(self.person['id']), self.person)
        self.assertEqual(self.people.relationship_catalog(), [])

    def test_v4_migration_backup_preserves_people(self):
        root = self.root / 'v4'; root.mkdir()
        with closing(sqlite3.connect(root / 'northdiary.sqlite3')) as conn:
            self.db.connection.backup(conn)
            conn.executescript('DROP TABLE person_relationship_tags; DROP TABLE person_temporary_relationship_tags; DROP TABLE relationship_tags; PRAGMA user_version=4;')
        migrated = Database(root)
        self.assertEqual(PeopleRepository(migrated).get(self.person['id']), self.person)
        migrated.close()
        snapshots = list((root / 'backups').glob('before-v5-*.sqlite3'))
        self.assertEqual(len(snapshots), 1)
        with closing(sqlite3.connect(snapshots[0])) as conn:
            self.assertEqual(conn.execute('PRAGMA user_version').fetchone()[0], 4)
        migrated = Database(root); migrated.close()
        self.assertEqual(len(list((root / 'backups').glob('before-v5-*'))), 1)

    def test_epub_relationship_roundtrip_and_conflict_preserves_local(self):
        from northdiary.storage.repository import ArticleRepository
        from northdiary.services.importing import EpubImporter
        from northdiary.services.attachments import AttachmentService
        p = dict(self.person, relationships=['同学'], temporary_relationships=['某次旅伴'])
        self.people.save(p); self.link()
        book = self.export()
        target = Database(self.root / 'target')
        try:
            importer = EpubImporter(ArticleRepository(target), AttachmentService(target))
            result = importer.import_file(book)
            people = PeopleRepository(target)
            self.assertEqual(people.get(p['id']), p)
            self.assertEqual(people.relationship_catalog(), ['同学'])
            self.assertEqual(importer.import_file(book).imported, 0)
            people.save(dict(p, relationships=['本机关系']))
            self.assertEqual(people.get(p['id'])['relationships'], ['本机关系'])
        finally:
            target.close()
        conflict = Database(self.root / 'conflict')
        try:
            local = PeopleRepository(conflict)
            local.save(dict(p, relationships=['本机关系']))
            result = EpubImporter(ArticleRepository(conflict), AttachmentService(conflict)).import_file(book)
            imported = local.for_article(result.article_ids[0])[0]
            self.assertNotEqual(imported['id'], p['id'])
            self.assertEqual(imported['relationships'], ['同学'])
            self.assertEqual(imported['temporary_relationships'], ['某次旅伴'])
            self.assertEqual(local.get(p['id'])['relationships'], ['本机关系'])
        finally:
            conflict.close()

    def test_legacy_v2_package_remains_importable(self):
        import json
        from zipfile import ZipFile
        from northdiary.services.native_format import MANIFEST_PATH
        from northdiary.storage.repository import ArticleRepository
        from northdiary.services.importing import EpubImporter
        from northdiary.services.attachments import AttachmentService
        self.link()
        book = self.export()
        with ZipFile(book) as archive:
            files = {info.filename: archive.read(info) for info in archive.infolist()}
        manifest = json.loads(files[MANIFEST_PATH]); manifest['version'] = 2
        files[MANIFEST_PATH] = json.dumps(manifest).encode()
        with ZipFile(book, 'w') as archive:
            for name, data in files.items(): archive.writestr(name, data)
        target = Database(self.root / 'legacy-v2')
        try:
            result = EpubImporter(ArticleRepository(target), AttachmentService(target)).import_file(book)
            self.assertEqual(result.imported, 1)
            self.assertEqual(PeopleRepository(target).get(self.person['id']), self.person)
        finally:
            target.close()


# Avoid collecting inherited tests twice through this subclass.
for name in list(test_people.PeopleTests.__dict__):
    if name.startswith('test_') and name not in RelationshipTests.__dict__:
        setattr(RelationshipTests, name, None)
