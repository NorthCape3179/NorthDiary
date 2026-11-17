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

    def add_image(self, article_id, source, compress=False):
        from tempfile import TemporaryDirectory
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QImageReader
        source = Path(source).resolve(strict=True)
        reader = QImageReader(str(source))
        reader.setAutoTransform(True)
        if not reader.canRead():
            raise ValueError('无法读取这张图片')
        # Animated images must retain their frames and timing.
        if not compress or reader.supportsAnimation():
            return self.add(article_id, source)
        size = reader.size()
        if max(size.width(), size.height()) > 2560:
            size.scale(2560, 2560, Qt.AspectRatioMode.KeepAspectRatio)
            reader.setScaledSize(size)
        image = reader.read()
        if image.isNull():
            raise ValueError('无法读取这张图片')
        if max(image.width(), image.height()) > 2560:
            image = image.scaled(2560, 2560, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        suffix, fmt = ('.png', 'PNG') if image.hasAlphaChannel() else ('.jpg', 'JPEG')
        with TemporaryDirectory(prefix='northdiary-image-') as folder:
            prepared = Path(folder)/(source.stem + suffix)
            if not image.save(str(prepared), fmt, 85):
                raise OSError('图片压缩失败，请重试或选择保留原图')
            # Avoid making a small, already optimized image larger.
            return self.add(article_id, prepared if prepared.stat().st_size < source.stat().st_size else source)
