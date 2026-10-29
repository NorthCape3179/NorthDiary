import mimetypes
import shutil
from pathlib import Path
from uuid import uuid4


class AttachmentService:
    def __init__(self, database):
        self.database = database

    def add(self, article_id: str, source: Path):
        source = source.resolve(strict=True)
        if not source.is_file():
            raise ValueError('请选择文件')
        attachment_id = str(uuid4())
        relative = Path('attachments') / (attachment_id + source.suffix.lower())
        destination = self.database.root / relative
        try:
            shutil.copy2(source, destination)
            with self.database.connection:
                self.database.connection.execute('''INSERT INTO attachments
                    (id,article_id,name,relative_path,mime_type) VALUES (?,?,?,?,?)''',
                    (attachment_id, article_id, source.name, relative.as_posix(),
                     mimetypes.guess_type(source.name)[0] or 'application/octet-stream'))
        except Exception:
            destination.unlink(missing_ok=True)
            raise
        return relative.as_posix()

    def list(self, article_id):
        return self.database.connection.execute(
            'SELECT * FROM attachments WHERE article_id=? ORDER BY position,rowid', (article_id,)).fetchall()
