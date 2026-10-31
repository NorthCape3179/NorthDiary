from pathlib import Path
import unittest
from unittest.mock import patch
import test_ui
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QMessageBox
from northdiary.ui.storage_actions import change_location
from northdiary.storage.database import Database

class SwitchUITests(unittest.TestCase):
    setUp=test_ui.WindowTests.setUp
    tearDown=test_ui.WindowTests.tearDown

    def test_switch_saves_and_remembers_target(self):
        w=self.window;w.new_article(); w.confirm_article(w.current_id);w.editor.setPlainText('切换前保存')
        target=w.database.root.parent/'other-data';db=Database(target);db.close()
        ini=w.database.root.parent/'launcher.ini'
        with patch('northdiary.ui.storage_actions.QFileDialog.getExistingDirectory',return_value=str(target)), patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Yes), patch('northdiary.ui.storage_actions.QStandardPaths.writableLocation',return_value=str(w.database.root)), patch.object(w,'close',return_value=True):
            change_location(w,False)
        self.assertEqual(w.requested_data_root,target.resolve())
        self.assertEqual(w.repository.get(w.current_id).body_text,'切换前保存')
        self.assertEqual(QSettings(str(ini),QSettings.Format.IniFormat).value('data_dir'),str(target.resolve()))
