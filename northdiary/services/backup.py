import json
from contextlib import closing
import sqlite3
import tempfile
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED


class BackupService:
    """Snapshot foundation. Restore UI and package migrations are future work."""
    def __init__(self, database):
        self.database = database

    def create(self, destination: Path):
        destination = destination.resolve()
        if destination.exists():
            raise FileExistsError('为保护已有备份，请使用新的文件名。')
        with tempfile.TemporaryDirectory() as temp:
            snapshot = Path(temp) / 'northdiary.sqlite3'
            with closing(sqlite3.connect(snapshot)) as target:
                self.database.connection.backup(target)
            archive = Path(temp) / 'backup.ndiary'
            with ZipFile(archive, 'w', ZIP_DEFLATED) as bundle:
                bundle.writestr('manifest.json', json.dumps({'format': 'NorthDiary', 'version': 1}, ensure_ascii=False))
                bundle.write(snapshot, 'northdiary.sqlite3')
                for source in (self.database.root / 'attachments').iterdir():
                    if source.is_file():
                        bundle.write(source, 'attachments/' + source.name)
            # Exclusive creation prevents accidental replacement of another backup.
            import shutil
            try:
                with destination.open('xb') as output, archive.open('rb') as source:
                    shutil.copyfileobj(source, output)
            except FileExistsError:
                raise
            except Exception:
                destination.unlink(missing_ok=True)
                raise
        return destination
