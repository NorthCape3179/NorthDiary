import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QUrl, QDate, QPoint, Qt
from PySide6.QtGui import QCloseEvent, QImage, QTextDocument, QTextImageFormat
from PySide6.QtTest import QTest, QSignalSpy
from PySide6.QtWidgets import QApplication

from northdiary.storage.database import Database
from northdiary.ui.main_window import MainWindow

APP = QApplication.instance() or QApplication([])
APP.setStyle('Fusion')


class WindowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.database = Database(self.root / 'data')
        self.window = MainWindow(self.database)
        self.window.show()
        APP.processEvents()

    def tearDown(self):
        self.window.dirty = False
        self.window.close()
        self.database.close()
        self.temp.cleanup()

    def test_autosave_and_switch(self):
        self.window.new_article()
        first = self.window.current_id
        self.window.title.setText('第一篇')
        self.window.editor.setPlainText('这是一段日记')
        # Wait for the timer event within a bound; a fixed 1.1 s wait is flaky
        # when the full offscreen suite has pending layout/paint events.
        for _ in range(30):
            if not self.window.dirty:
                break
            QTest.qWait(100)
        self.assertFalse(self.window.dirty)
        self.assertEqual(self.window.repository.get(first).body_text, '这是一段日记')
        self.window.editor.insertPlainText('追加')
        self.window.new_article()
        self.assertIn('追加', self.window.repository.get(first).body_text)
        self.window.load_article(first)
        self.assertIn('这是一段日记', self.window.editor.toPlainText())

    def test_failure_prevents_switch_and_close(self):
        self.window.new_article()
        first = self.window.current_id
        self.window.editor.setPlainText('必须保留')
        with patch.object(self.window.repository, 'save', side_effect=OSError('磁盘不可写')), patch.object(self.window, 'fail'):
            self.window.new_article()
            self.assertEqual(self.window.current_id, first)
            self.assertTrue(self.window.dirty)
            event = QCloseEvent()
            self.window.closeEvent(event)
            self.assertFalse(event.isAccepted())
            self.assertEqual(self.window.editor.toPlainText(), '必须保留')
        self.assertTrue(self.window.save())

    def test_image_roundtrip_and_relative_resource(self):
        self.window.new_article()
        key = self.window.current_id
        original = self.root / 'original.png'
        image = QImage(32, 20, QImage.Format.Format_RGB32)
        image.fill(0xff467954)
        image.save(str(original))
        relative = self.window.attachments.add(key, original)
        fmt = QTextImageFormat()
        fmt.setName(relative)
        self.window.editor.textCursor().insertImage(fmt)
        self.window.save()
        original.unlink()
        self.window.load_article(key)
        self.assertIn(relative, self.window.editor.toHtml())
        resource = self.window.editor.document().resource(QTextDocument.ResourceType.ImageResource, QUrl(relative))
        self.assertIsNotNone(resource)
        self.assertFalse(resource.isNull())

    def test_category_filter_with_pending_save(self):
        self.window.new_article()
        key = self.window.current_id
        self.window.categories.setText('生活，旅行')
        self.window.save()
        self.window.title.setText('筛选前修改')
        self.window.category_filter.setCurrentIndex(self.window.category_filter.findData('旅行'))
        self.assertEqual(self.window.category, '旅行')
        self.assertEqual(self.window.article_list.count(), 1)
        self.assertEqual(self.window.repository.get(key).title, '筛选前修改')

    def test_tag_menu_reuse_temporary_and_left_filter(self):
        self.window.new_article()
        first = self.window.current_id
        picker = self.window.tags
        with patch('northdiary.ui.tag_picker.QInputDialog.getText', side_effect=[('常用', True), ('私有备注', True)]):
            picker.add_button.menu().actions()[0].trigger()
            picker.add_button.menu().actions()[1].trigger()
        self.window.save()
        self.assertGreater(self.window.tag_filter.findData('常用'), 0)
        self.assertEqual(self.window.tag_filter.findData('私有备注'), -1)
        self.window.new_article()
        second = self.window.current_id
        self.assertEqual(picker.temporary_names, [])
        self.assertEqual(picker.combo.findData('私有备注'), -1)
        picker.choose(picker.combo.findData('常用'))
        self.window.save()
        self.window.tag_filter.setCurrentIndex(self.window.tag_filter.findData('常用'))
        self.assertEqual(self.window.article_list.count(), 2)
        picker.remove_tag('常用', False)
        self.window.save()
        APP.processEvents()
        self.assertEqual(self.window.article_list.count(), 1)
        self.assertEqual(self.window.repository.labels(second, 'tags'), [])
        self.window.load_article(first)
        self.assertEqual(picker.temporary_names, ['私有备注'])
        self.assertEqual(picker.normal_names, ['常用'])

    def test_image_navigation_roundtrip_removal_and_viewer(self):
        self.window.new_article()
        article_id = self.window.current_id
        source = self.root / 'photo.png'
        image = QImage(40, 30, QImage.Format.Format_RGB32)
        image.fill(0xff467954)
        image.save(str(source))
        with patch('northdiary.ui.main_window.QFileDialog.getOpenFileName', return_value=(str(source), '')):
            self.window.insert_image()
        row = self.window.attachments.list(article_id)[0]
        self.assertNotIn('<img', self.window.editor.toHtml())
        self.assertIn('ndiary-image:' + row['id'], self.window.editor.toHtml())
        self.assertEqual(self.window.image_list.count(), 1)
        self.window.save()
        source.unlink()
        self.window.load_article(article_id)
        self.assertTrue(self.window.editor.locate_image(row['id']))
        with patch('northdiary.ui.main_window.ImageViewer.exec', return_value=0) as opened:
            self.window.open_image(row['id'])
            opened.assert_called_once()
        self.window.editor.remove_image_links(row['id'])
        self.assertFalse(self.window.editor.image_links(row['id']))
        self.assertTrue((self.database.root / row['relative_path']).exists())
        self.window.editor.undo()
        self.assertTrue(self.window.editor.image_links(row['id']))

    def test_timeline_browse_does_not_change_article_date(self):
        self.window.new_article()
        key = self.window.current_id
        self.window.date.setDate(QDate(2025, 3, 15))
        self.window.save()
        self.window.timeline.setDate(QDate(2025, 3, 16))
        self.window.browse_day(QDate(2025, 3, 16))
        self.assertEqual(self.window.article_list.count(), 0)
        self.assertEqual(self.window.repository.get(key).diary_date, '2025-03-15')
        self.window.new_article()
        self.window.save()
        self.assertEqual(self.window.repository.get(self.window.current_id).diary_date, '2025-03-16')
        self.window.clear_day()
        self.assertEqual(self.window.article_list.count(), 2)

    def test_pin_button_and_list_reorder(self):
        self.window.sort_combo.setCurrentIndex(self.window.sort_combo.findData('manual'))
        self.window.new_article()
        first = self.window.current_id
        self.window.new_article()
        second = self.window.current_id
        QTest.mouseClick(self.window.pin_button, Qt.MouseButton.LeftButton)
        self.assertTrue(self.window.pin_button.isChecked())
        self.assertEqual(self.window.article_list.item(0).data(Qt.ItemDataRole.UserRole), second)
        self.window.load_article(first)
        QTest.mouseClick(self.window.pin_button, Qt.MouseButton.LeftButton)
        self.window.reorder_articles([first, second])
        self.assertEqual([a.id for a in self.window.repository.list(sort='manual')], [first, second])
        self.window.load_article(second)
        self.assertTrue(self.window.pin_button.isChecked())
        QTest.mouseClick(self.window.pin_button, Qt.MouseButton.LeftButton)
        self.assertFalse(self.window.pin_button.isChecked())

    def test_article_slide_is_vertical_and_stays_in_group(self):
        self.window.sort_combo.setCurrentIndex(self.window.sort_combo.findData('manual'))
        from PySide6.QtWidgets import QAbstractItemView
        for _ in range(3):
            self.window.new_article()
        self.window.repository.set_pinned(self.window.current_id, True)
        self.window.refresh_list()
        APP.processEvents()
        listing = self.window.article_list
        before = listing.ids()
        self.assertEqual(listing.dragDropMode(), QAbstractItemView.DragDropMode.NoDragDrop)
        viewport = listing.viewport()
        start = listing.visualItemRect(listing.item(1)).center()
        QTest.mousePress(viewport, Qt.MouseButton.LeftButton, pos=start)
        QTest.mouseMove(viewport, QPoint(start.x()+80, start.y()))
        self.assertEqual(listing.ids(), before)
        end = listing.visualItemRect(listing.item(2)).center()
        QTest.mouseMove(viewport, QPoint(start.x()+80, end.y()))
        self.assertEqual(listing.ids(), before)
        self.assertTrue(listing.ghost.isVisible())
        QTest.mouseRelease(viewport, Qt.MouseButton.LeftButton, pos=end)
        self.assertFalse(listing.ghost.isVisible())
        self.assertEqual(listing.ids(), [before[0], before[2], before[1]])
        self.assertEqual([a.id for a in self.window.repository.list(sort='manual')], listing.ids())
        start = listing.visualItemRect(listing.item(1)).center()
        QTest.mousePress(viewport, Qt.MouseButton.LeftButton, pos=start)
        QTest.mouseMove(viewport, QPoint(start.x(), 1))
        QTest.mouseRelease(viewport, Qt.MouseButton.LeftButton, pos=QPoint(start.x(), 1))
        self.assertEqual(listing.ids()[0], before[0])

    def test_trash_dialog_preview_restore_and_delete_confirmation(self):
        from northdiary.ui.trash_dialog import TrashDialog
        from PySide6.QtWidgets import QMessageBox
        self.window.new_article()
        key = self.window.current_id
        self.window.editor.setPlainText('回收站预览正文')
        self.window.save()
        self.window.repository.set_deleted(key)
        dialog = TrashDialog(self.window.repository, self.window)
        dialog.show()
        APP.processEvents()
        self.assertEqual(dialog.table.rowCount(), 1)
        self.assertIn('回收站预览正文', dialog.preview.toPlainText())
        with patch('northdiary.ui.trash_dialog.QMessageBox.question', return_value=QMessageBox.StandardButton.No):
            dialog.purge(key)
        self.assertEqual(dialog.table.rowCount(), 1)
        dialog.restore(key)
        self.assertEqual(dialog.table.rowCount(), 0)
        self.assertIsNone(self.window.repository.get(key).deleted_at)
        self.window.repository.set_deleted(key)
        dialog.refresh()
        with patch('northdiary.ui.trash_dialog.QMessageBox.question', return_value=QMessageBox.StandardButton.Yes):
            dialog.purge(key)
        self.assertEqual(dialog.table.rowCount(), 0)
        dialog.close()

    def test_dropdown_light_palette_and_button_ripple(self):
        from northdiary.ui.controls import Ripple
        from PySide6.QtGui import QPalette
        self.window.category_filter.showPopup()
        APP.processEvents()
        self.assertEqual(self.window.category_filter.view().palette().color(QPalette.ColorRole.Base).name(), '#fffefa')
        self.window.category_filter.hidePopup()
        QTest.mousePress(self.window.trash_button, Qt.MouseButton.LeftButton)
        APP.processEvents()
        self.assertTrue(self.window.trash_button.findChildren(Ripple))
        # Release outside the button: don't open a modal trash dialog in this test.
        QTest.mouseRelease(self.window.trash_button, Qt.MouseButton.LeftButton, pos=QPoint(-10, -10))

    def test_popup_fits_resized_control_and_ripple_resizes(self):
        from northdiary.ui.controls import Ripple
        combo = self.window.category_filter
        for width in (170, 260):
            combo.setFixedWidth(width)
            combo.showPopup()
            APP.processEvents()
            self.assertEqual(combo.popup.width(), combo.width())
            rect = combo.view().visualRect(combo.model().index(0, 0))
            self.assertLessEqual(rect.right(), combo.view().viewport().width())
            self.assertEqual(rect.height(), 32)
            combo.hidePopup()
        button = self.window.trash_button
        QTest.mousePress(button, Qt.MouseButton.LeftButton)
        button.resize(button.width()+80, button.height())
        APP.processEvents()
        ripple = button.findChildren(Ripple)[0]
        self.assertEqual(ripple.geometry(), button.rect())
        QTest.mouseRelease(button, Qt.MouseButton.LeftButton, pos=QPoint(-10, -10))

    def test_dropdown_same_button_toggles_once(self):
        combo = self.window.category_filter
        for expected in (True, False, True, False):
            QTest.mouseClick(combo, Qt.MouseButton.LeftButton)
            APP.processEvents()
            self.assertEqual(combo.popup.isVisible(), expected)
        self.assertTrue(combo.popup.testAttribute(Qt.WidgetAttribute.WA_NoMouseReplay))

    def test_floating_menu_closes_on_second_click_escape_and_outside(self):
        combo = self.window.category_filter
        self.assertEqual(combo.popup.windowType(), Qt.WindowType.Tool)
        QTest.mouseClick(combo, Qt.MouseButton.LeftButton)
        self.assertTrue(combo.popup.isVisible())
        QTest.mouseClick(self.window.title, Qt.MouseButton.LeftButton)
        self.assertFalse(combo.popup.isVisible())
        QTest.mouseClick(combo, Qt.MouseButton.LeftButton)
        QTest.keyClick(combo.view(), Qt.Key.Key_Escape)
        self.assertFalse(combo.popup.isVisible())
        self.window.new_article()
        plus = self.window.tags.add_button
        QTest.mouseClick(plus, Qt.MouseButton.LeftButton)
        self.assertTrue(plus.panel.isVisible())
        QTest.mouseClick(plus, Qt.MouseButton.LeftButton)
        self.assertFalse(plus.panel.isVisible())

    def test_context_menu_and_recent_removal(self):
        from PySide6.QtWidgets import QMessageBox
        self.window.new_article()
        first = self.window.current_id
        self.window.new_article()
        second = self.window.current_id
        menu = self.window.make_article_menu(first)
        self.assertEqual([a.text() for a in menu.actions()], ['置顶', '删除'])
        menu.actions()[0].trigger()
        self.assertTrue(self.window.repository.get(first).pinned)
        self.assertEqual(self.window.current_id, second)
        self.window.article_mode.setCurrentIndex(self.window.article_mode.findData('recent'))
        menu = self.window.make_article_menu(first)
        self.assertEqual(menu.actions()[-1].text(), '移出最近打开')
        menu.actions()[-1].trigger()
        self.assertNotIn(first, self.window.recent_ids)
        self.assertIsNone(self.window.repository.get(first).deleted_at)
        with patch('northdiary.ui.main_window.QMessageBox.question', return_value=QMessageBox.StandardButton.Yes):
            self.window.make_article_menu(first).actions()[1].trigger()
        self.assertIsNotNone(self.window.repository.get(first).deleted_at)

    def test_photo_board_white_cards_hover_and_click(self):
        self.window.new_article()
        source = self.root / 'photo.png'
        image = QImage(80, 60, QImage.Format.Format_RGB32)
        image.fill(0xff72937e)
        image.save(str(source))
        with patch('northdiary.ui.main_window.QFileDialog.getOpenFileName', return_value=(str(source), '')):
            self.window.insert_image()
        board = self.window.image_list
        APP.processEvents()
        rect = board.visualItemRect(board.item(0))
        QTest.mouseMove(board.viewport(), rect.center())
        APP.processEvents()
        self.assertTrue(board.hover_card.isVisible())
        self.assertGreater(board.hover_card.width(), rect.width())
        with patch('northdiary.ui.main_window.ImageViewer.exec', return_value=0) as opened:
            QTest.mouseClick(board.viewport(), Qt.MouseButton.LeftButton, pos=rect.center())
            opened.assert_not_called()
            self.assertTrue(board.item(0).isSelected())
            QTest.mouseDClick(board.viewport(), Qt.MouseButton.LeftButton, pos=rect.center())
            opened.assert_called_once()

    def test_season_background_selection_and_toggle(self):
        from datetime import datetime
        from northdiary.ui.season_background import background_name
        for month, season in ((1, '冬天'), (4, '春天'), (7, '夏天'), (10, '秋天')):
            for hour in (0, 6, 12, 18, 23):
                for dark, phase in ((False, '白天'), (True, '黑夜')):
                    self.assertEqual(background_name(datetime(2026, month, 1, hour), dark=dark), season+phase+'.png')
        self.window.new_article()
        self.window.editor.setPlainText('背景开关不改正文')
        self.window.save()
        html = self.window.editor.toHtml()
        self.assertFalse(self.window.paper.source.isNull())
        self.window.set_theme(True)
        self.assertIn('黑夜', self.window.paper.name)
        self.window.set_theme(False)
        self.assertIn('白天', self.window.paper.name)
        self.window.set_background(False)
        self.assertFalse(self.window.paper.enabled)
        self.assertFalse(self.window.background_button.isChecked())
        self.assertEqual(self.window.editor.toHtml(), html)
        self.assertFalse(self.window.dirty)
        other = MainWindow(self.database)
        try:
            self.assertFalse(other.paper.enabled)
        finally:
            other.close()

    def test_background_tracks_article_date_and_theme(self):
        self.window.new_article()
        july = self.window.current_id
        self.window.date.setDate(QDate(2026, 7, 15))
        self.window.set_theme(False)
        self.assertEqual(self.window.paper.name, '夏天白天.png')
        self.window.save()
        self.window.new_article()
        self.window.date.setDate(QDate(2026, 11, 2))
        self.window.set_theme(True)
        self.assertEqual(self.window.paper.name, '秋天黑夜.png')
        self.window.save()
        self.window.load_article(july)
        self.assertEqual(self.window.paper.name, '夏天黑夜.png')
        self.window.date.setDate(QDate(2026, 1, 3))
        self.assertEqual(self.window.paper.name, '冬天黑夜.png')
        self.window.set_theme(False)
        self.assertEqual(self.window.paper.name, '冬天白天.png')

    def test_custom_date_input_and_calendar_validation(self):
        from northdiary.ui.date_picker import DateDialog, parse_date
        self.window.new_article()
        self.window.date.input.setText('20260715')
        self.assertTrue(self.window.date.commit())
        self.assertEqual(self.window.date.date(), QDate(2026, 7, 15))
        self.assertEqual(self.window.paper.name, '夏天白天.png')
        self.assertFalse(parse_date('2026-02-30').isValid())
        self.assertEqual(parse_date('2024/2/29'), QDate(2024, 2, 29))
        dialog = DateDialog(QDate(2026, 7, 15), self.window)
        dialog.input.setText('2026-02-30')
        dialog.accept_input()
        self.assertNotEqual(dialog.result(), dialog.DialogCode.Accepted)
        dialog.input.setText('2024-02-29')
        dialog.accept_input()
        self.assertEqual(dialog.selected, QDate(2024, 2, 29))
        dialog.close()

    def test_all_eight_theme_choices_and_background_phase(self):
        self.window.new_article()
        self.window.date.setDate(QDate(2026, 7, 15))
        for key in ('light','dark','cream','wine','burgundy','citrus','blue','gray'):
            self.window.set_theme(key in ('dark', 'wine'))
            combo = self.window.theme_combo
            combo.setCurrentIndex(combo.findData(key))
            self.assertEqual(self.window.property('colorTheme'), key)
            self.assertIn('黑夜' if key in ('dark','wine') else '白天', self.window.paper.name)

    def test_date_recent_modes_and_history_persist(self):
        self.window.new_article()
        first = self.window.current_id
        self.window.date.setDate(QDate(2020, 1, 2))
        self.window.save()
        self.window.new_article()
        second = self.window.current_id
        self.window.save()
        self.window.load_article(first)
        self.window.article_mode.setCurrentIndex(self.window.article_mode.findData('recent'))
        self.assertEqual(self.window.article_list.ids(), [first, second])
        self.assertFalse(self.window.article_list.sorting_allowed)
        self.window.load_article(second)
        APP.processEvents()
        self.assertEqual(self.window.article_list.ids(), [second, first])
        self.assertEqual(len(self.window.recent_ids), 2)
        self.window.browse_day(QDate(2020, 1, 2))
        self.assertEqual(self.window.article_mode.currentData(), 'date')
        self.assertEqual(self.window.article_list.ids(), [first])
        other = MainWindow(self.database)
        try:
            other.article_mode.setCurrentIndex(other.article_mode.findData('recent'))
            self.assertEqual(set(other.article_list.ids()), {first, second})
        finally:
            other.close()

    def test_date_scope_button_repeated_toggle_and_single_category(self):
        self.window.new_article()
        key=self.window.current_id
        self.window.date.setDate(QDate(2026,7,15))
        self.window.categories.setText('生活')
        self.window.save()
        self.window.categories.setText('读书')
        self.window.save()
        self.assertEqual(self.window.repository.labels(key,'categories'), ['读书'])
        self.assertGreater(self.window.categories.combo.findData('生活'),0)
        for _ in range(3):
            QTest.mouseClick(self.window.date_scope_button, Qt.MouseButton.LeftButton)
            self.assertEqual(self.window.article_mode.currentData(),'date')
            self.assertEqual(self.window.browse_date,'2026-07-15')
            self.assertEqual(self.window.date_scope_button.text(),'全部日期')
            QTest.mouseClick(self.window.date_scope_button, Qt.MouseButton.LeftButton)
            self.assertEqual(self.window.article_mode.currentData(),'all')
            self.assertEqual(self.window.date_scope_button.text(),'当前日期')

    def test_article_overview_search_sort_and_open(self):
        from northdiary.ui.overview_dialog import OverviewDialog
        for title in ('Z文章','A文章'):
            self.window.new_article();self.window.title.setText(title);self.window.save()
        options=[(self.window.sort_combo.itemText(i),self.window.sort_combo.itemData(i)) for i in range(self.window.sort_combo.count())]
        dialog=OverviewDialog(self.window.repository,options,self.window.sort_key,self.window)
        spy=QSignalSpy(dialog.sortingChanged)
        dialog.sort.setCurrentIndex(dialog.sort.findData('title'))
        self.assertEqual(spy.count(),1)
        self.assertEqual(dialog.table.item(0,0).text(),'A文章')
        dialog.search.setText('Z文章')
        self.assertEqual(dialog.table.rowCount(),1)
        dialog.open_selected()
        self.assertEqual(self.window.repository.get(dialog.article_id).title,'Z文章')
        self.assertFalse(self.window.sort_combo.isVisible())
        dialog.close()

    def test_fullscreen_restores_previous_window_mode(self):
        self.window.showNormal()
        self.window.toggle_fullscreen()
        self.assertTrue(self.window.isFullScreen())
        self.window.leave_fullscreen()
        self.assertFalse(self.window.isFullScreen())
        self.assertFalse(self.window.isMaximized())
        self.window.showMaximized()
        self.window.toggle_fullscreen()
        self.assertTrue(self.window.isFullScreen())
        self.window.leave_fullscreen()
        self.assertTrue(self.window.isMaximized())

    def test_theme_persistence_and_reading_actions(self):
        from PySide6.QtGui import QPalette
        self.assertFalse(self.window.place_link_button.isEnabled())
        self.window.new_article()
        self.window.editor.setPlainText('主题切换不改变正文')
        self.window.set_theme(True)
        self.assertLess(self.window.palette().color(QPalette.ColorRole.Window).lightness(), 128)
        self.window.category_filter.showPopup()
        APP.processEvents()
        self.assertLess(self.window.category_filter.view().palette().color(QPalette.ColorRole.Base).lightness(), 128)
        self.window.category_filter.hidePopup()
        self.window.preview.setChecked(True)
        self.window.toggle_preview()
        self.assertTrue(self.window.editor.isReadOnly())
        self.assertFalse(self.window.bold.isEnabled())
        self.assertFalse(self.window.dirty)
        other = MainWindow(self.database)
        try:
            self.assertTrue(other.property('darkTheme'))
            self.assertEqual(other.editor.toPlainText(), '主题切换不改变正文')
        finally:
            other.close()
        self.window.set_theme(False)
        self.assertGreater(self.window.palette().color(QPalette.ColorRole.Window).lightness(), 128)

    def test_global_sort_and_new_theme_preserve_original_choices(self):
        from PySide6.QtGui import QPalette
        self.assertEqual(self.window.article_mode.currentData(), 'all')
        self.assertEqual(self.window.sort_key, 'created_desc')
        self.window.new_article()
        first = self.window.current_id
        self.window.date.setDate(QDate(2020, 1, 1))
        self.window.title.setText('B')
        self.window.save()
        self.window.new_article()
        second = self.window.current_id
        self.window.date.setDate(QDate(2025, 7, 1))
        self.window.title.setText('A')
        self.window.save()
        self.window.refresh_list()
        self.assertEqual(self.window.article_list.ids(), [second, first])
        self.window.sort_combo.setCurrentIndex(self.window.sort_combo.findData('title'))
        self.assertEqual(self.window.article_list.ids(), [second, first])
        self.window.sort_combo.setCurrentIndex(self.window.sort_combo.findData('created_asc'))
        self.assertEqual(self.window.article_list.ids(), [first, second])
        self.window.set_theme(False)
        self.assertEqual(self.window.theme_combo.count(), 6)
        self.window.theme_combo.setCurrentIndex(self.window.theme_combo.findData('cream'))
        self.assertEqual(self.window.palette().color(QPalette.ColorRole.Window).name(), '#f4ecdc')
        self.assertEqual(self.window.paper.name, '夏天白天.png')
        self.window.set_theme(True)
        self.assertEqual(self.window.theme_combo.count(), 2)
        self.window.theme_combo.setCurrentIndex(self.window.theme_combo.findData('wine'))
        self.assertEqual(self.window.palette().color(QPalette.ColorRole.Window).name(), '#191a1c')
        self.assertEqual(self.window.paper.name, '夏天黑夜.png')
        other = MainWindow(self.database)
        try:
            self.assertEqual(other.sort_key, 'created_asc')
            self.assertEqual(other.property('colorTheme'), 'wine')
        finally:
            other.close()

    def test_timeline_zoom_smooth_pointer_and_commit_on_release(self):
        timeline = self.window.timeline
        timeline.setDate(QDate(2025, 1, 1))
        spy = QSignalSpy(timeline.dateSelected)
        QTest.mousePress(timeline, Qt.MouseButton.LeftButton, pos=QPoint(30, 35))
        self.assertEqual(timeline.spacing, timeline.REST_SPACING)
        QTest.mouseMove(timeline, QPoint(64, 35))
        self.assertEqual(timeline.selected, QDate(2025, 1, 2))
        self.assertEqual(timeline.spacing, timeline.REST_SPACING)
        QTest.mouseMove(timeline, QPoint(98, 35))
        self.assertEqual(timeline.selected, QDate(2025, 1, 3))
        self.assertEqual(timeline.spacing, timeline.REST_SPACING)
        QTest.mouseMove(timeline, QPoint(132, 35))
        self.assertEqual(timeline.selected, QDate(2025, 1, 4))
        self.assertEqual(timeline.spacing, timeline.REST_SPACING)
        QTest.mouseMove(timeline, QPoint(144, 35))
        self.assertEqual(timeline.spacing, timeline.DRAG_SPACING)
        self.assertEqual(timeline.selected, QDate(2025, 1, 5))
        self.assertEqual(spy.count(), 0)
        QTest.mouseRelease(timeline, Qt.MouseButton.LeftButton, pos=QPoint(144, 35))
        self.assertEqual(spy.count(), 1)
        self.assertEqual(self.window.browse_date, '2025-01-05')
        for _ in range(20):
            if timeline.spacing == timeline.REST_SPACING:
                break
            QTest.qWait(30)
        self.assertEqual(timeline.spacing, timeline.REST_SPACING)


if __name__ == '__main__':
    unittest.main()

