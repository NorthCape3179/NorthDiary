# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import sys
ROOT = Path(SPECPATH).parent
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import copy_metadata

datas = [(str(ROOT / 'northdiary/resources'), 'northdiary/resources'), (str(ROOT / 'licenses'), 'licenses'), (str(ROOT / '使用说明.txt'), '.')]
datas += collect_data_files('ebooklib')
datas += copy_metadata('EbookLib')
datas += copy_metadata('lxml')


a = Analysis(
    [str(ROOT / 'main.py')],
    pathex=[str(ROOT)],
    binaries=[(str(p), '.') for p in (Path(sys.base_prefix) / 'Library/bin').glob('*.dll') if p.name in {'sqlite3.dll','ffi.dll','libmpdec-4.dll'}],
    datas=datas,
    hiddenimports=['lxml._elementpath'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'unittest', 'numpy', 'matplotlib', 'PIL'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='NorthDiary',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=str(ROOT / 'packaging/version_info.txt'),
    icon=[str(ROOT / 'northdiary/resources/northdiary.ico')],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='NorthDiary',
)
