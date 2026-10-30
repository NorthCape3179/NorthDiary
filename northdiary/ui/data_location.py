"""First-run storage selection; never migrates or copies diary data implicitly."""
from pathlib import Path
import sqlite3

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QFileDialog, QMessageBox


def validate_location(path, existing=False):
    root = Path(path).expanduser().resolve()
    database = root / 'northdiary.sqlite3'
    if existing and not database.is_file():
        raise ValueError('请选择包含 northdiary.sqlite3 的那一层数据文件夹。')
    if database.exists():
        connection = sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)
        try:
            tables = {r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not {'articles','attachments'} <= tables:
                raise ValueError('这个数据库不是可识别的 NorthDiary 日记数据库。')
        finally:
            connection.close()
    elif root.exists() and any(root.iterdir()):
        raise ValueError('新数据位置请选择空文件夹，以免与其他文件混用。')
    return root


class DataLocationDialog(QDialog):
    def __init__(self, default_root, parent=None):
        super().__init__(parent)
        self.default_root = Path(default_root)
        self.selected = None
        self.setWindowTitle('NorthDiary · 选择日记数据位置')
        self.resize(580, 360)
        layout=QVBoxLayout(self);layout.setSpacing(14)
        title=QLabel('给记忆选择一个存放位置');title.setStyleSheet('font-size:22px;font-weight:600;')
        layout.addWidget(title)
        description=QLabel('程序安装位置和日记数据位置彼此独立。\n更新或卸载程序会保留日记数据。\n已有日记请选择原数据文件夹，无需导入或重新创建。')
        description.setWordWrap(True);layout.addWidget(description)
        label=QLabel('默认位置：\n'+str(default_root));label.setWordWrap(True);layout.addWidget(label)
        for text,action in [('使用默认位置',lambda:self.choose(self.default_root)),
                            ('选择已有日记数据文件夹',lambda:self.browse(True)),
                            ('选择新的空数据文件夹',lambda:self.browse(False))]:
            button=QPushButton(text);button.clicked.connect(action);layout.addWidget(button)
        cancel=QPushButton('暂不启动');cancel.clicked.connect(self.reject);layout.addWidget(cancel)

    def browse(self, existing):
        path=QFileDialog.getExistingDirectory(self,'选择已有日记数据文件夹' if existing else '选择新的空数据文件夹')
        if path:self.choose(path,existing)

    def choose(self,path,existing=False):
        try:self.selected=validate_location(path,existing)
        except Exception as error:
            QMessageBox.warning(self,'无法使用这个位置',str(error));return
        self.accept()


def resolve_data_root(default_root, settings_path=None, dialog_type=DataLocationDialog):
    default_root=Path(default_root)
    settings_path=Path(settings_path) if settings_path else default_root.parent/'launcher.ini'
    settings=QSettings(str(settings_path),QSettings.Format.IniFormat)
    previous=settings.value('data_dir','')
    if previous:
        try:
            return validate_location(previous, existing=True)
        except Exception:
            QMessageBox.warning(None,'找不到原日记数据','原来选择的数据位置不可用。请确认移动硬盘或文件夹位置，再重新选择。\n原文件不会被移动或删除。')
    elif (default_root/'northdiary.sqlite3').is_file():
        return validate_location(default_root,existing=True)
    dialog=dialog_type(default_root)
    if dialog.exec()!=QDialog.DialogCode.Accepted:return None
    root=dialog.selected
    settings_path.parent.mkdir(parents=True,exist_ok=True)
    settings.setValue('data_dir',str(root));settings.sync()
    if settings.status()!=QSettings.Status.NoError:
        raise OSError('无法保存数据位置设置，请选择可写的用户目录。')
    return root
