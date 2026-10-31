from contextlib import closing
from pathlib import Path
from PySide6.QtCore import QSettings, QStandardPaths, QLockFile, QUrl
from PySide6.QtGui import QDesktopServices, QCursor
from PySide6.QtWidgets import QMenu, QFileDialog, QMessageBox
from northdiary.ui.data_location import validate_location
from northdiary.services.storage_location import copy_data


def manage_location(window):
    popup = QMenu(window)
    popup.addAction('打开当前数据文件夹', lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(window.database.root))))
    popup.addAction('切换到已有数据文件夹…', lambda: change_location(window, False))
    popup.addAction('迁移当前数据到新文件夹…', lambda: change_location(window, True))
    popup.exec(QCursor.pos())


def change_location(window, migrate):
    if not window.save(True): return
    path = QFileDialog.getExistingDirectory(window, '选择空文件夹以迁移当前数据' if migrate else '选择已有数据文件夹')
    if not path: return
    try:
        target = validate_location(path, existing=not migrate)
        if target == window.database.root.resolve():
            QMessageBox.information(window, '数据位置', '这就是当前使用的数据文件夹。')
            return
        if migrate and any(target.iterdir()):
            raise ValueError('迁移目标必须是空文件夹。')
        lock = QLockFile(str(target / 'northdiary.lock'))
        lock.setStaleLockTime(0)
        if not lock.tryLock(100):
            raise ValueError('目标日记正在另一个窗口中使用。')
        lock.unlock()
        if not migrate:
            import sqlite3
            from northdiary.storage.database import SCHEMA_VERSION
            with closing(sqlite3.connect((target / 'northdiary.sqlite3').as_uri() + '?mode=ro', uri=True)) as db:
                if db.execute('PRAGMA user_version').fetchone()[0] > SCHEMA_VERSION:
                    raise ValueError('目标数据来自更新版本，请先更新软件。')
                if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise ValueError('目标数据库校验未通过。')
        if QMessageBox.question(window, '迁移数据' if migrate else '切换数据',
                ('将复制全部日记和附件，保留原文件夹。' if migrate else '将打开所选文件夹里的日记，当前日记保留在原处。') + '\n完成后会重新打开主窗口，是否继续？') != QMessageBox.StandardButton.Yes:
            return
        if migrate:
            copy_data(window.database, target)
        default = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation))
        settings = QSettings(str(default.parent / 'launcher.ini'), QSettings.Format.IniFormat)
        previous = settings.value('data_dir', '')
        settings.setValue('data_dir', str(target)); settings.sync()
        if settings.status() != QSettings.Status.NoError:
            raise OSError('无法保存数据位置设置，当前窗口保持原位置。')
        window.requested_data_root = target
        if not window.close():
            window.requested_data_root = None
            settings.setValue("data_dir", previous); settings.sync()
    except Exception as error:
        QMessageBox.warning(window, '无法更改数据位置', str(error))
