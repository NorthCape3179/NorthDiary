import unittest
import test_ui
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from northdiary.ui.main_window import MainWindow


class SplitThemeTests(unittest.TestCase):
    setUp = test_ui.WindowTests.setUp
    tearDown = test_ui.WindowTests.tearDown

    def test_independent_theme_choices_and_restart(self):
        w=self.window
        for key in ('burgundy','wine','citrus','dark','cream','wine','burgundy'):
            w.set_theme(key in ('dark','wine'))
            w.theme_combo.setCurrentIndex(w.theme_combo.findData(key))
            self.assertEqual(w.property('colorTheme'),key)
        QTest.mouseClick(w.theme_mode_button,Qt.MouseButton.LeftButton)
        self.assertEqual(w.property('colorTheme'),'wine')
        self.assertEqual(w.theme_combo.count(),2)
        QTest.mouseClick(w.theme_mode_button,Qt.MouseButton.LeftButton)
        self.assertEqual(w.property('colorTheme'),'burgundy')
        self.assertEqual(w.theme_combo.count(),6)
        other=MainWindow(self.database)
        try:
            self.assertEqual(other.property('colorTheme'),'burgundy')
            self.assertEqual(other.theme_combo.currentData(),'burgundy')
            self.assertEqual(other.header_tools.tools_layout.count(),5)
        finally:other.close()
