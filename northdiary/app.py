import argparse
import sys
from pathlib import Path

from northdiary.bootstrap import configure_runtime
configure_runtime()

from PySide6.QtCore import QLockFile, QStandardPaths, Qt
from PySide6.QtGui import QIcon
from northdiary.ui.data_location import resolve_data_root
from PySide6.QtWidgets import QApplication, QMessageBox

from northdiary import __version__
from northdiary.storage.database import Database
from northdiary.ui.main_window import MainWindow
from northdiary.services.tls import configure_tls


def main():
    parser = argparse.ArgumentParser(description='NorthDiary desktop journal')
    parser.add_argument('--data-dir', type=Path, help='Independent diary data directory')
    parser.add_argument('--verify-installation',type=Path,help=argparse.SUPPRESS)
    args = parser.parse_args()
    if sys.platform == 'win32':
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('NorthCape.NorthDiary')
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    app = QApplication(sys.argv[:1])
    configure_tls()
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
    while True:
        window.show()
        try:
            result = app.exec()
        finally:
            database.close()
            lock.unlock()
        target = getattr(window, 'requested_data_root', None)
        if target is None:
            return result
        window.deleteLater()
        try:
            lock = QLockFile(str(target / 'northdiary.lock'))
            lock.setStaleLockTime(0)
            if not lock.tryLock(100):
                raise RuntimeError('目标数据目录已被另一个窗口打开。')
            database = Database(target)
            window = MainWindow(database)
        except Exception as error:
            QMessageBox.critical(None, '无法打开日记数据', str(error))
            lock.unlock()
            return 1
