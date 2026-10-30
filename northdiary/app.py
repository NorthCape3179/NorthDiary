import argparse
import sys
from pathlib import Path

from PySide6.QtCore import QLockFile, QStandardPaths
from PySide6.QtGui import QIcon
from northdiary.ui.data_location import resolve_data_root
from PySide6.QtWidgets import QApplication, QMessageBox

from northdiary import __version__
from northdiary.storage.database import Database
from northdiary.ui.main_window import MainWindow


def main():
    parser = argparse.ArgumentParser(description='NorthDiary desktop journal')
    parser.add_argument('--data-dir', type=Path, help='Independent diary data directory')
    parser.add_argument('--verify-installation',type=Path,help=argparse.SUPPRESS)
    args = parser.parse_args()
    if sys.platform == 'win32':
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('NorthCape.NorthDiary')
    app = QApplication(sys.argv[:1])
    app.setWindowIcon(QIcon(str(Path(__file__).parent / 'resources' / 'northdiary.ico')))
    app.setApplicationName('NorthDiary')
    app.setApplicationVersion(__version__)
    app.setOrganizationName('NorthDiary')
    app.setStyle('Fusion')
    if args.verify_installation:
        from northdiary.services.installation_check import run_installation_check
        return run_installation_check(args.verify_installation)
    default_root = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation))
    try:
        root = args.data_dir or resolve_data_root(default_root)
        if root is None:
            return 0
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

