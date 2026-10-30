import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from PySide6.QtWidgets import QApplication,QDialog
from northdiary.storage.database import Database
from northdiary.ui.data_location import resolve_data_root,validate_location
APP=QApplication.instance() or QApplication([])


class DataLocationTests(unittest.TestCase):
    def test_existing_default_data_is_reused_without_wizard(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'data';db=Database(root);db.close()
            with patch('northdiary.ui.data_location.DataLocationDialog') as dialog:
                self.assertEqual(resolve_data_root(root,Path(temp)/'launcher.ini'),root.resolve())
                dialog.assert_not_called()

    def test_new_selection_is_remembered_and_reused(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);selected=root/'我的日记';settings=root/'launcher.ini'
            class Choice:
                def __init__(self,default):self.selected=selected
                def exec(self):return QDialog.DialogCode.Accepted
            self.assertEqual(resolve_data_root(root/'default',settings,Choice),selected)
            db=Database(selected);db.close()
            with patch('northdiary.ui.data_location.QMessageBox.warning') as warning:
                self.assertEqual(resolve_data_root(root/'default',settings),selected.resolve())
                warning.assert_not_called()

    def test_invalid_existing_or_nonempty_new_location_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'other.txt').write_text('keep',encoding='utf-8')
            with self.assertRaises(ValueError):validate_location(root,existing=True)
            with self.assertRaises(ValueError):validate_location(root)
            self.assertEqual((root/'other.txt').read_text(),'keep')

    def test_cancelling_first_launch_creates_no_database(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            class Cancel:
                def __init__(self,default):pass
                def exec(self):return QDialog.DialogCode.Rejected
            self.assertIsNone(resolve_data_root(root/'data',root/'launcher.ini',Cancel))
            self.assertEqual(list(root.iterdir()),[])
