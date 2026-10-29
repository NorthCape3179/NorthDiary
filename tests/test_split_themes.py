import unittest
import test_ui
from northdiary.ui.main_window import MainWindow


class SplitThemeTests(unittest.TestCase):
    setUp = test_ui.WindowTests.setUp
    tearDown = test_ui.WindowTests.tearDown

    def test_independent_theme_choices_and_restart(self):
        w=self.window
        for key in ('burgundy', 'wine', 'citrus', 'dark', 'cream', 'wine', 'burgundy'):
            combo=w.dark_theme_combo if key in ('dark','wine') else w.light_theme_combo
            other=w.light_theme_combo if combo is w.dark_theme_combo else w.dark_theme_combo
            combo.setCurrentIndex(combo.findData(key))
            self.assertEqual(w.property('colorTheme'), key)
            self.assertEqual(other.currentIndex(), 0)
        w.set_theme(True)
        self.assertEqual(w.property('colorTheme'), 'wine')
        w.set_theme(False)
        self.assertEqual(w.property('colorTheme'), 'burgundy')
        other=MainWindow(self.database)
        try:
            self.assertEqual(other.property('colorTheme'), 'burgundy')
            self.assertEqual(other.light_theme_combo.currentData(), 'burgundy')
            self.assertEqual(other.dark_theme_combo.currentIndex(), 0)
        finally: other.close()
