from contextlib import closing
"""Copy a live SQLite snapshot and its managed files to an empty directory."""
from pathlib import Path
import shutil
import sqlite3


def copy_data(database, destination):
    source = database.root.resolve()
    target = Path(destination).resolve()
    if target == source or source in target.parents or target in source.parents:
        raise ValueError('请选择与当前数据文件夹互不包含的新位置。')
    if target.exists() and any(target.iterdir()):
        raise ValueError('迁移目标必须是空文件夹。')
    if any(item.is_symlink() for item in source.rglob('*')):
        raise ValueError('数据文件夹含链接，请先整理后再迁移。')
    target.mkdir(parents=True, exist_ok=True)
    created = []
    try:
        for entry in source.iterdir():
            if entry.name in ('northdiary.sqlite3', 'northdiary.sqlite3-wal', 'northdiary.sqlite3-shm', 'northdiary.lock'):
                continue
            if entry.is_symlink():
                raise ValueError('数据文件夹含链接，请先整理后再迁移。')
            dest = target / entry.name
            created.append(dest)
            if entry.is_dir(): shutil.copytree(entry, dest)
            else: shutil.copy2(entry, dest)
        snapshot = target / 'northdiary.sqlite3'
        created.append(snapshot)
        with closing(sqlite3.connect(snapshot)) as connection:
            database.connection.backup(connection)
            if connection.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise ValueError('迁移后的数据库校验未通过。')
    except Exception:
        # Remove only items created by this operation, never an existing tree.
        for item in reversed(created):
            if target not in item.resolve().parents:
                raise ValueError('清理路径超出迁移目标。')
            if item.is_dir(): shutil.rmtree(item)
            elif item.exists(): item.unlink()
        raise
    return target
