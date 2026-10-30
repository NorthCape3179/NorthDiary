import unittest
from unittest.mock import patch

import test_ui
from PySide6.QtCore import Qt, QPoint, QPointF, QTimer, QEvent
from PySide6.QtGui import QImage, QWheelEvent
from PySide6.QtTest import QTest, QSignalSpy
from PySide6.QtWidgets import QApplication, QPushButton

from northdiary.ui.main_window import MainWindow
from northdiary.ui.memory_dialog import MemoryDialog, plain_memory_text
from northdiary.ui.timeline_overview import TimelineOverview, TimelineCanvas, group_articles


class MemoryUITests(unittest.TestCase):
    setUp = test_ui.WindowTests.setUp
    tearDown = test_ui.WindowTests.tearDown

    def article(self, title='回忆', date='2026-07-15', body='<p>正文</p>'):
        key = self.window.repository.create().id
        self.window.repository.save(key, title, date, body, '正文', [], [])
        return key

    def photo(self, key):
        path = self.root / 'photo.png'
        image = QImage(30, 20, QImage.Format.Format_RGB32)
        image.fill(0xff557744)
        image.save(str(path))
        self.window.attachments.add(key, path)
        return self.window.attachments.list(key)[0]

    def timeline(self):
        dialog = TimelineOverview(self.window.repository, self.window.attachments, self.window)
        dialog.resize(800, 560)
        dialog.show()
        test_ui.APP.processEvents()
        self.addCleanup(dialog.close)
        return dialog

    def memory(self, **kwargs):
        dialog = MemoryDialog(self.window.repository, self.window.attachments, self.window, **kwargs)
        dialog.show()
        test_ui.APP.processEvents()
        self.addCleanup(dialog.close)
        return dialog

    def wheel(self, canvas, x, y, delta=-120):
        event = QWheelEvent(QPointF(x, y), QPointF(canvas.viewport().mapToGlobal(QPoint(x, y))),
                            QPoint(), QPoint(0, delta), Qt.MouseButton.NoButton,
                            Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase, False)
        QApplication.sendEvent(canvas.viewport(), event)
        test_ui.APP.processEvents()

    def test_group_order_partial_dates_and_trash_without_fabricated_dates(self):
        for value in ('2026-未知-未知', '2025-12-31', '2026-07-未知', '2026-07-15', '2026-01-01'):
            self.article(date=value)
        trashed = self.article('已删除', '2024-01-01')
        self.window.repository.set_deleted(trashed)
        groups = group_articles(self.window.repository.list())
        self.assertEqual([group.value for group in groups if group.kind == 'day'],
                         ['2025-12-31', '2026-01-01', '2026-07-15'])
        year = next(group for group in groups if group.value == '2026-未知-未知')
        month = next(group for group in groups if group.value == '2026-07-未知')
        self.assertEqual((year.label, year.kind, len(year.articles)), ('2026年', 'year', 1))
        self.assertEqual((month.label, month.kind, len(month.articles)), ('07月', 'month', 1))
        self.assertEqual([group.value for group in groups if group.kind == 'month'],
                         ['2025-12-未知', '2026-01-未知', '2026-07-未知'])

    def test_two_rows_extend_into_columns_and_card_activation_after_horizontal_scroll(self):
        keys = [self.article(f'同日事件 {i}') for i in range(10)]
        dialog = self.timeline()
        canvas = dialog.canvas
        index = canvas.selected_index
        self.assertEqual(canvas.card_rect(index, 0).x(), canvas.card_rect(index, 1).x())
        self.assertEqual(canvas.card_rect(index, 0).y(), canvas.card_rect(index, 2).y())
        self.assertGreater(canvas.card_rect(index, 2).x(), canvas.card_rect(index, 0).x())
        canvas.horizontal_offsets[index] = canvas.STEP
        canvas.articleActivated.disconnect(dialog.open_article)
        spy = QSignalSpy(canvas.articleActivated)
        rect = canvas.card_rect(index, 2)
        QTest.mouseClick(canvas.viewport(), Qt.MouseButton.LeftButton, pos=rect.center().toPoint())
        self.assertEqual(spy.count(), 1)
        self.assertEqual(spy.at(0)[0], canvas.groups[index].articles[2].id)

    def test_wheel_over_event_strip_is_horizontal_else_vertical_with_center_selection(self):
        for i in range(10):
            self.article(f'同日事件{i}', '2025-12-31')
        self.article('新年', '2026-01-01')
        dialog = self.timeline()
        canvas = dialog.canvas
        first = canvas.selected_index
        last = next(index for index, group in enumerate(canvas.groups) if group.value == '2026-01-01')
        center = round(canvas.center_y(first))
        before = canvas.verticalScrollBar().value()
        self.wheel(canvas, 300, center)
        self.assertGreater(canvas.horizontal_offsets[first], 0)
        self.assertEqual(canvas.verticalScrollBar().value(), before)
        self.wheel(canvas, 30, center)
        self.assertGreater(canvas.verticalScrollBar().value(), before)
        self.assertEqual(canvas.selected_index, first + 1)
        self.assertEqual(dialog.year.text(), '2026')
        canvas.center_on(last)
        self.assertAlmostEqual(canvas.center_y(last), canvas.viewport().height() / 2)

    def test_keyboard_navigation_year_stays_in_header_and_end_date_centered(self):
        self.article('一', '2024-01-01')
        self.article('二', '2025-01-01')
        self.article('三', '2026-01-01')
        dialog = self.timeline()
        before = dialog.year.pos()
        self.assertGreaterEqual(dialog.year.font().pixelSize(), 24)
        QTest.keyClick(dialog.canvas, Qt.Key.Key_End)
        last = len(dialog.canvas.groups) - 1
        self.assertEqual(dialog.canvas.selected_index, last)
        self.assertEqual(dialog.year.text(), '2026')
        self.assertEqual(dialog.year.pos(), before)
        self.assertAlmostEqual(dialog.canvas.center_y(last), dialog.canvas.viewport().height() / 2)
        QTest.keyClick(dialog.canvas, Qt.Key.Key_Home)
        self.assertEqual(dialog.year.text(), '2024')

    def test_horizontally_scroll_date_offsets_are_independent_and_resize_clamps(self):
        for date in ('2025-12-31', '2026-01-01'):
            for i in range(10): self.article(f'{date}事件{i}', date)
        dialog = self.timeline()
        canvas = dialog.canvas
        first_index = canvas.selected_index
        last = len(canvas.groups) - 1
        self.wheel(canvas, 300, round(canvas.center_y(first_index)))
        first = canvas.horizontal_offsets[first_index]
        canvas.center_on(last)
        self.wheel(canvas, 300, round(canvas.center_y(last)))
        self.assertEqual(canvas.horizontal_offsets[first_index], first)
        self.assertGreater(canvas.horizontal_offsets[last], 0)
        canvas.horizontal_offsets[last] = canvas.max_offset(last)
        dialog.resize(1800, 560)
        test_ui.APP.processEvents()
        self.assertLessEqual(canvas.horizontal_offsets[last], canvas.max_offset(last))
        self.assertEqual(canvas.selected_index, last)

    def test_year_month_nodes_contain_partial_articles_and_empty_periods_are_absent(self):
        annual = self.article('只记得年份', '2023-未知-未知')
        monthly = self.article('只记得月份', '2026-07-未知')
        self.article('知道日期', '2026-07-15')
        dialog = self.timeline()
        groups = dialog.canvas.groups
        self.assertEqual([group.year for group in groups if group.kind == 'year'], ['2023', '2026'])
        self.assertEqual([group.value for group in groups if group.kind == 'month'], ['2026-07-未知'])
        self.assertEqual(groups[0].articles[0].id, annual)
        month = next(group for group in groups if group.kind == 'month')
        self.assertEqual(month.articles[0].id, monthly)
        self.assertEqual(len(groups), 4)
        self.assertEqual(dialog.canvas.selected_index, 0)
        self.assertGreater(dialog.canvas.events_x(0), dialog.canvas.EVENTS)

    def test_empty_separator_keyboard_enter_does_not_open_or_crash(self):
        self.article()
        dialog = self.timeline()
        dialog.canvas.center_on(0)
        spy = QSignalSpy(dialog.canvas.articleActivated)
        QTest.keyClick(dialog.canvas, Qt.Key.Key_Return)
        self.assertEqual(spy.count(), 0)

    def test_empty_timeline_and_empty_random_memory(self):
        timeline, memory = self.timeline(), self.memory()
        self.assertEqual(timeline.canvas.selected_index, -1)
        self.assertEqual(timeline.year.text(), '时间线')
        self.wheel(timeline.canvas, 200, 200)
        self.assertIsNone(memory.current_id)
        self.assertFalse(memory.next_button.isEnabled())
        self.assertEqual(self.window.repository.list(), [])

    def test_random_excludes_trash_and_avoids_immediate_repetition(self):
        first, second, trash = self.article('一'), self.article('二'), self.article('删除')
        self.window.repository.set_deleted(trash)
        dialog = self.memory(chooser=lambda articles: articles[0])
        seen = [dialog.current_id]
        for _ in range(5):
            dialog.next_memory()
            seen.append(dialog.current_id)
        self.assertTrue(set(seen).issubset({first, second}))
        self.assertTrue(all(a != b for a, b in zip(seen, seen[1:])))

    def test_single_memory_plain_text_photo_board_and_no_database_or_recent_changes(self):
        key = self.article('标题 <b>原样</b>', '2026-未知-未知')
        photo = self.photo(key)
        body = f'<p>前文<b>粗体</b><a href="ndiary-image:{photo["id"]}">▧ 图片入口 ↗</a>后文</p>'
        self.window.repository.save(key, '标题 <b>原样</b>', '2026-未知-未知', body, '前文粗体后文', ['生活'], ['回忆'])
        before = self.window.repository.get(key)
        recent = self.window.ui_settings.value('recent_articles', [])
        dialog = self.memory()
        self.assertEqual(dialog.current_id, key)
        self.assertTrue(dialog.editor.isReadOnly())
        self.assertEqual(dialog.editor.toPlainText(), '前文粗体后文')
        self.assertEqual(dialog.title.text(), '标题 <b>原样</b>')
        self.assertGreaterEqual(dialog.title.font().pixelSize(), 24)
        self.assertEqual(dialog.image_list.count(), 1)
        self.assertFalse(dialog.image_list.isWrapping())
        self.assertFalse(dialog.next_button.isEnabled())
        self.assertEqual(dialog.paper.name, 'unknown-month.png')
        dialog.close()
        self.assertEqual(self.window.repository.get(key), before)
        self.assertEqual(self.window.ui_settings.value('recent_articles', []), recent)

    def test_memory_background_matches_date_and_theme(self):
        key = self.article(date='2026-07-未知')
        self.window.set_theme(True, 'wine')
        dialog = self.memory(article_id=key)
        self.assertEqual(dialog.date.text(), '2026-07-未知')
        self.assertEqual(dialog.paper.name, '夏天黑夜.png')
        self.assertTrue(dialog.next_button.isHidden())

    def test_memory_missing_picture_keeps_article_and_viewer_uses_selected_photo(self):
        key = self.article()
        photo = self.photo(key)
        (self.database.root / photo['relative_path']).unlink()
        dialog = self.memory(article_id=key)
        self.assertIn('图片缺失', dialog.image_list.item(0).text())
        self.assertEqual(dialog.editor.toPlainText(), '正文')
        with patch('northdiary.ui.memory_dialog.ImageViewer') as viewer:
            dialog.open_image(dialog.image_list.item(0))
            self.assertEqual(viewer.call_args.args[1], 0)
            viewer.return_value.exec.assert_called_once()

    def test_plain_memory_text_keeps_adjacent_text_and_removes_legacy_images_and_scripts(self):
        self.assertEqual(plain_memory_text('<p>A<img src="attachments/x.png">B</p><script>bad()</script><p>C</p>'), 'AB\nC')

    def test_header_animation_collapse_expand_retains_five_controls_and_right_anchor(self):
        tools = self.window.header_tools
        right = tools.geometry().right()
        self.assertEqual(tools.tools_layout.count(), 5)
        QTest.mouseClick(tools.arrow, Qt.MouseButton.LeftButton)
        QTest.qWait(230)
        self.assertTrue(tools.collapsed)
        self.assertTrue(tools.clip.isHidden())
        self.assertEqual(tools.arrow.arrowType(), Qt.ArrowType.LeftArrow)
        self.assertEqual(tools.geometry().right(), right)
        QTest.mouseClick(tools.arrow, Qt.MouseButton.LeftButton)
        QTest.qWait(230)
        self.assertFalse(tools.collapsed)
        self.assertFalse(tools.clip.isHidden())
        self.assertTrue(self.window.theme_combo.isEnabled())
        self.assertEqual(tools.arrow.arrowType(), Qt.ArrowType.RightArrow)
        self.assertEqual(tools.geometry().right(), right)

    def test_header_rapid_reverse_and_theme_change_while_collapsed(self):
        tools = self.window.header_tools
        tools.set_collapsed(True)
        QTest.qWait(30)
        tools.set_collapsed(False)
        QTest.qWait(30)
        tools.set_collapsed(True)
        QTest.qWait(230)
        self.window.set_theme(True, 'wine')
        tools.set_collapsed(False)
        QTest.qWait(230)
        self.assertFalse(tools.collapsed)
        self.assertGreater(tools.clip.width(), 0)
        self.assertTrue(self.window.theme_combo.isEnabled())
        self.assertEqual(self.window.theme_combo.currentData(), 'wine')

    def test_header_state_reopens_and_ctrl_s_works_when_save_button_hidden(self):
        self.window.header_tools.set_collapsed(True, animate=False)
        self.window.new_article()
        key = self.window.current_id
        self.window.editor.setPlainText('隐藏保存按钮仍可保存')
        QTest.keyClick(self.window, Qt.Key.Key_S, Qt.KeyboardModifier.ControlModifier)
        test_ui.APP.processEvents()
        self.assertFalse(self.window.dirty)
        self.assertEqual(self.window.repository.get(key).body_text, '隐藏保存按钮仍可保存')
        other = MainWindow(self.database)
        try:
            self.assertTrue(other.header_tools.collapsed)
            self.assertTrue(other.header_tools.clip.isHidden())
        finally:
            other.close()

    def test_sidebar_timeline_is_above_overview_and_save_failure_blocks_reading_dialogs(self):
        sidebar = self.window.article_list.parentWidget()
        buttons = {button.text(): button for button in sidebar.findChildren(QPushButton)}
        layout = sidebar.layout()
        self.assertEqual(layout.indexOf(buttons['时间线总览']) + 1, layout.indexOf(buttons['文章总览']))
        self.assertNotIn('随机回忆', buttons)
        tools = self.window.header_tools.tools_layout
        names = [tools.itemAt(i).widget().text() if isinstance(tools.itemAt(i).widget(), QPushButton) else '' for i in range(tools.count())]
        self.assertEqual(names.index('随机回忆'), names.index('数据文件夹') + 1)
        self.assertEqual(tools.itemAt(names.index('随机回忆')).widget(), self.window.random_memory_button)
        self.window.new_article()
        self.window.editor.setPlainText('未保存的正文')
        with patch.object(self.window.repository, 'save', side_effect=OSError('不可写')), \
             patch.object(self.window, 'fail'), \
             patch('northdiary.ui.memory_dialog.MemoryDialog') as memory, \
             patch('northdiary.ui.timeline_overview.TimelineOverview') as timeline:
            self.window.open_random_memory()
            self.window.open_timeline_overview()
            memory.assert_not_called()
            timeline.assert_not_called()
        self.assertTrue(self.window.dirty)
        self.assertEqual(self.window.editor.toPlainText(), '未保存的正文')

    def test_opening_and_closing_real_dialogs_saves_first_without_leaving_hidden_windows(self):
        self.window.new_article()
        key = self.window.current_id
        self.window.editor.setPlainText('打开前应保存')
        for opened, dialog_type in ((self.window.open_random_memory, MemoryDialog),
                                    (self.window.open_timeline_overview, TimelineOverview)):
            QTimer.singleShot(30, lambda: QApplication.activeModalWidget().accept())
            opened()
            QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            self.assertEqual(self.window.findChildren(dialog_type), [])
        self.assertEqual(self.window.repository.get(key).body_text, '打开前应保存')
        self.assertEqual(self.window.current_id, key)
