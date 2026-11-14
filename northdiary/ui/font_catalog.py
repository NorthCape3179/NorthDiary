"""Fonts with verified commercial-use permission, including audited local files."""
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path

from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication


@dataclass(frozen=True)
class ApprovedFont:
    key: str
    label: str
    family: str
    license_url: str
    license_name: str = 'SIL OFL 1.1'
    bundled: bool = True
    note: str = ''


APPROVED = (
    ApprovedFont('noto-sans-sc', 'Noto 黑体', 'Noto Sans SC',
                 'https://github.com/google/fonts/blob/main/ofl/notosanssc/OFL.txt'),
    ApprovedFont('noto-serif-sc', 'Noto 宋体', 'Noto Serif SC',
                 'https://github.com/google/fonts/blob/main/ofl/notoserifsc/OFL.txt'),
    ApprovedFont('lxgw-wenkai', '霞鹜文楷', 'LXGW WenKai',
                 'https://github.com/lxgw/LxgwWenKai/blob/main/OFL.txt'),
    ApprovedFont('fusion-pixel', '融合像素', 'Fusion Pixel 12px Prop zh-Hans',
                 'https://github.com/TakWolf/fusion-pixel-font/blob/2026.10.25/LICENSE-OFL'),
)


def load_installed_fonts(manifest):
    """Use only reviewed file hashes; a matching family name alone is insufficient."""
    if not manifest.is_file():
        return ()
    roots = {
        'windows': Path(os.environ.get('WINDIR', 'C:/Windows')).resolve(),
        'programdata': Path(os.environ.get('PROGRAMDATA', 'C:/ProgramData')).resolve(),
    }
    loaded = []
    for record in json.loads(manifest.read_text(encoding='utf-8'))['fonts']:
        matched = False
        for source in record['files']:
            root = roots.get(source['base'])
            if root is None:
                continue
            path = (root/source['path']).resolve()
            if not path.is_relative_to(root) or not path.is_file():
                continue
            try:
                if hashlib.sha256(path.read_bytes()).hexdigest() != source['sha256']:
                    continue
                identifier = QFontDatabase.addApplicationFont(str(path))
                matched |= record['family'] in QFontDatabase.applicationFontFamilies(identifier)
            except OSError:
                continue
        if matched:
            loaded.append(ApprovedFont(record['key'], record['label'], record['family'],
                                       record['license_url'], record['license_name'], False,
                                       record['note']))
    return tuple(loaded)


def load_approved_fonts():
    app = QApplication.instance()
    if not hasattr(app, '_northdiary_approved_fonts'):
        root = Path(__file__).resolve().parent.parent/'assets/lyrics-fonts'
        loaded = []
        for font in APPROVED:
            path = root/font.key/'font.ttf'
            if path.is_file():
                identifier = QFontDatabase.addApplicationFont(str(path))
                if font.family in QFontDatabase.applicationFontFamilies(identifier):
                    loaded.append(font)
        loaded.extend(load_installed_fonts(root.parent/'font-licenses/installed-fonts-20261106.json'))
        if not loaded:
            raise RuntimeError('免费商用字体文件缺失，请恢复 northdiary/assets/lyrics-fonts。')
        app._northdiary_approved_fonts = tuple(loaded)
    return app._northdiary_approved_fonts
