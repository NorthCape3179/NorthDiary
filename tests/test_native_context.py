import unittest
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QContextMenuEvent
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
import test_ui
from northdiary.ui.people_dialog import PersonEditor
from northdiary.storage.people import PeopleRepository

class NativeContextTests(unittest.TestCase):
    setUp=test_ui.WindowTests.setUp
    tearDown=test_ui.WindowTests.tearDown

    def check_context(self,picker,combo,name):
        combo.showPopup();test_ui.APP.processEvents()
        index=combo.model().index(combo.findData(name),0)
        pos=combo.view().visualRect(index).center()
        QTest.mouseClick(combo.view().viewport(),Qt.MouseButton.RightButton,pos=pos)
        test_ui.APP.processEvents()
        popup=picker._definition_menu
        self.assertIsNotNone(popup)
        self.assertTrue(popup.isVisible())
        self.assertTrue(combo.popup.isVisible(),'右键不能收起原来的列表')
        # Windows can send WM_CONTEXTMENU after the right-button release.
        event=QContextMenuEvent(QContextMenuEvent.Reason.Mouse,pos,combo.view().viewport().mapToGlobal(pos))
        QApplication.sendEvent(combo.view().viewport(),event)
        self.assertTrue(popup.isVisible())
        self.assertTrue(combo.popup.isVisible())
        QTest.keyClick(popup,Qt.Key.Key_Escape);test_ui.APP.processEvents()
        self.assertTrue(combo.popup.isVisible())
        self.assertFalse(combo.popup.property('contextMenuOpen'))
        combo.hidePopup()

    def test_article_tag_right_click_keeps_list_and_menu_visible(self):
        w=self.window;w.new_article(); w.confirm_article(w.current_id);w.tags.add_tag('测试标签');w.save()
        self.check_context(w.tags,w.tags.combo,'测试标签')
        self.assertIn('测试标签',w.repository.tags())

    def test_category_right_click_keeps_list_and_menu_visible(self):
        w=self.window;w.new_article(); w.confirm_article(w.current_id);w.categories.setText('测试分类');w.save()
        self.check_context(w.categories,w.categories.combo,'测试分类')
        self.assertEqual(w.categories.text(),'测试分类')

    def test_person_relationship_right_click_keeps_list_visible(self):
        w=self.window;editor=PersonEditor(PeopleRepository(w.database),parent=w)
        editor.relationships.add_tag('测试人物关系');editor.show();test_ui.APP.processEvents()
        try:self.check_context(editor.relationships,editor.relationships.combo,'测试人物关系')
        finally:editor.reject()
