import unittest
import test_memory_ui
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication


class TimelineScrollTests(test_memory_ui.MemoryUITests):
    def prepare(self, count=10):
        for i in range(count): self.article(f'事件 {i}', '2025-01-01')
        self.article('次日', '2025-01-02')
        dialog=self.timeline()
        return dialog, dialog.canvas, dialog.canvas.selected_index

    def test_right_half_over_cards_scrolls_vertical_only(self):
        dialog, canvas, index=self.prepare()
        before=canvas.verticalScrollBar().value()
        self.wheel(canvas, canvas.viewport().width()-40, round(canvas.center_y(index)))
        self.assertGreater(canvas.verticalScrollBar().value(), before)
        self.assertEqual(canvas.horizontal_offsets.get(index,0),0)

    def test_fitting_row_scrolls_vertical_even_in_left_event_area(self):
        dialog, canvas, index=self.prepare(2)
        self.assertEqual(canvas.max_offset(index),0)
        before=canvas.verticalScrollBar().value()
        self.wheel(canvas,300,round(canvas.center_y(index)))
        self.assertGreater(canvas.verticalScrollBar().value(), before)
        self.assertEqual(canvas.horizontal_offsets.get(index,0),0)

    def test_horizontal_wheel_small_step_cap_and_resize_disables_it(self):
        dialog, canvas, index=self.prepare()
        before=canvas.verticalScrollBar().value()
        self.wheel(canvas,300,round(canvas.center_y(index)))
        self.assertEqual(canvas.horizontal_offsets[index],24)
        self.wheel(canvas,300,round(canvas.center_y(index)),delta=-1200)
        self.assertEqual(canvas.horizontal_offsets[index],60)
        self.assertEqual(canvas.verticalScrollBar().value(),before)
        dialog.resize(1800,560);QApplication.processEvents()
        self.assertEqual(canvas.max_offset(index),0)
        self.assertEqual(canvas.horizontal_offsets[index],0)
        self.wheel(canvas,300,round(canvas.center_y(index)))
        self.assertGreater(canvas.verticalScrollBar().value(),before)

    def test_right_half_header_and_footer_also_scroll_vertical(self):
        dialog, canvas, index=self.prepare()
        for target,point in [(dialog,QPoint(dialog.width()-30,20)),
                             (dialog.findChildren(test_memory_ui.QPushButton)[-1],QPoint(10,10))]:
            canvas.center_on(index)
            before=canvas.verticalScrollBar().value()
            event=QWheelEvent(QPointF(point),QPointF(target.mapToGlobal(point)),QPoint(),QPoint(0,-120),
                              Qt.MouseButton.NoButton,Qt.KeyboardModifier.NoModifier,Qt.ScrollPhase.NoScrollPhase,False)
            QApplication.sendEvent(target,event);QApplication.processEvents()
            self.assertGreater(canvas.verticalScrollBar().value(),before)


for name in test_memory_ui.MemoryUITests.__dict__:
    if name.startswith('test_') and name not in TimelineScrollTests.__dict__:
        setattr(TimelineScrollTests,name,None)
