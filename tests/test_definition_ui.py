import unittest
from unittest.mock import patch
import test_ui
from PySide6.QtWidgets import QMessageBox
from northdiary.ui.definition_menu import delete_from_widget

class DefinitionUITests(unittest.TestCase):
    setUp=test_ui.WindowTests.setUp
    tearDown=test_ui.WindowTests.tearDown

    def test_delete_definition_does_not_reappear_on_save(self):
        w=self.window;w.new_article(); w.confirm_article(w.current_id);w.categories.setText('删除分类');w.tags.add_tag('删除标签');w.editor.setPlainText('保留内容');w.save()
        key=w.current_id
        with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Yes):
            delete_from_widget(w.tags,'tags','删除标签')
            delete_from_widget(w.categories,'categories','删除分类')
        w.editor.setPlainText('保存之后的内容');self.assertTrue(w.save())
        self.assertNotIn('删除标签',w.repository.tags());self.assertNotIn('删除分类',w.repository.categories())
        self.assertEqual(w.repository.get(key).body_text,'保存之后的内容')
