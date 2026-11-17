"""Portable, bounded image copies for person profiles (no external file paths)."""
import base64
import binascii
from pathlib import Path
from uuid import UUID, uuid4

from PySide6.QtCore import QByteArray, QBuffer, QIODevice, Qt, QRectF
from PySide6.QtGui import QImage, QImageReader, QPainter, QPainterPath

IMAGE_FILTER = '图片 (*.png *.jpg *.jpeg *.webp *.bmp *.gif)'
MAX_IMAGE_TEXT = 8 * 1024 * 1024


def decode_image(value):
    if not isinstance(value, str) or len(value) > MAX_IMAGE_TEXT:
        raise ValueError('人物图片过大或无效')
    try:
        raw = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error) as error:
        raise ValueError('人物图片数据无效') from error
    reader = QImageReader()
    buffer = QBuffer()
    buffer.setData(QByteArray(raw)); buffer.open(QIODevice.OpenModeFlag.ReadOnly)
    reader.setDevice(buffer)
    size = reader.size()
    if not size.isValid() or max(size.width(), size.height()) > 2000:
        raise ValueError('人物图片尺寸无效')
    image = reader.read()
    if image.isNull():
        raise ValueError('人物图片无法读取')
    return image


def encode_image(image, avatar=False):
    if image.isNull():
        raise ValueError('无法读取这张图片')
    if avatar:
        edge = min(image.width(), image.height())
        image = image.copy((image.width()-edge)//2, (image.height()-edge)//2, edge, edge)
    limit = 256 if avatar else 2000
    if max(image.width(), image.height()) > limit:
        image = image.scaled(limit, limit, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    if not avatar and image.hasAlphaChannel():
        canvas = QImage(image.size(), QImage.Format.Format_RGB32); canvas.fill(Qt.GlobalColor.white)
        painter = QPainter(canvas); painter.drawImage(0, 0, image); painter.end(); image = canvas
    data = QByteArray(); buffer = QBuffer(data); buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    if not image.save(buffer, 'PNG' if avatar else 'JPEG', 90):
        raise OSError('无法保存人物图片')
    value = base64.b64encode(bytes(data)).decode('ascii')
    if len(value) > MAX_IMAGE_TEXT:
        raise ValueError('图片过大，请先缩小图片')
    return value


def read_profile_image(path, avatar=False):
    path = Path(path)
    if path.stat().st_size > 32 * 1024 * 1024:
        raise ValueError('请选择小于 32 MiB 的图片')
    reader = QImageReader(str(path)); reader.setAutoTransform(True)
    size = reader.size()
    if size.isValid() and max(size.width(), size.height()) > 2000:
        size.scale(2000, 2000, Qt.AspectRatioMode.KeepAspectRatio); reader.setScaledSize(size)
    return encode_image(reader.read(), avatar)


def make_photo(path):
    return dict(id=str(uuid4()), name=Path(path).name[:255], data=read_profile_image(path))


def validate_media(person):
    if person.get('avatar'):
        image = decode_image(person['avatar'])
        if image.width() != image.height() or image.width() > 256:
            raise ValueError('头像应为不超过 256 像素的正方形')
    elif 'avatar' in person and person['avatar'] != '':
        raise ValueError('头像数据无效')
    photos = person.get('photos', [])
    if not isinstance(photos, list) or len(photos) > 100:
        raise ValueError('每个人物最多保存 100 张照片')
    ids = set()
    for photo in photos:
        if not isinstance(photo, dict) or set(photo) != {'id', 'name', 'data'}:
            raise ValueError('照片资料字段无效')
        if not isinstance(photo['id'], str) or str(UUID(photo['id'])) != photo['id'] or photo['id'] in ids:
            raise ValueError('照片编号无效或重复')
        ids.add(photo['id'])
        if not isinstance(photo['name'], str) or not photo['name'] or len(photo['name']) > 255 or '\x00' in photo['name']:
            raise ValueError('照片名称无效')
        decode_image(photo['data'])
    if sum(len(p['data']) for p in photos) > 32 * 1024 * 1024:
        raise ValueError('人物照片总量超过 32 MiB，请移除部分照片')


def circular_avatar(value, size=96):
    source = decode_image(value)
    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    clip = QPainterPath(); clip.addEllipse(QRectF(0, 0, size, size)); painter.setClipPath(clip)
    painter.drawImage(QRectF(0, 0, size, size), source); painter.end()
    return image
