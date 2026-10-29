import argparse
import sys
from pathlib import Path

from PySide6.QtCore import QLockFile, QStandardPaths
from PySide6.QtWidgets import QApplication, QMessageBox

from northdiary.storage.database import Database
from northdiary.ui.main_window import MainWindow


def main():
    parser = argparse.ArgumentParser(description='NorthDiary desktop journal')
    parser.add_argument('--data-dir', type=Path, help='Independent diary data directory')
    args = parser.parse_args()
    app = QApplication(sys.argv[:1])
    app.setApplicationName('NorthDiary')
    app.setOrganizationName('NorthDiary')
    app.setStyle('Fusion')
    root = args.data_dir or Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation))
    try:
        root.mkdir(parents=True, exist_ok=True)
        lock = QLockFile(str(root / 'northdiary.lock'))
        lock.setStaleLockTime(0)
        if not lock.tryLock(100):
            QMessageBox.warning(None, 'NorthDiary', '这个日记数据目录已在另一个窗口打开。')
            return 1
        database = Database(root)
        window = MainWindow(database)
    except Exception as error:
        QMessageBox.critical(None, '无法启动 NorthDiary', str(error))
        return 1
    window.show()
    try:
        return app.exec()
    finally:
        database.close()
        lock.unlock()
