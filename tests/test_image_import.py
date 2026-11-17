import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import test_ui
from PySide6.QtCore import Qt, QSize, QRectF
from PySide6.QtGui import QImage, QColor, QIcon, QPixmap, QPainter
from PySide6.QtWidgets import QListWidgetItem
from northdiary.ui.image_board import photo_size, paint_photo, photo_seed


class ImageImportTests(unittest.TestCase):
    setUp = test_ui.WindowTests.setUp
    tearDown = test_ui.WindowTests.tearDown

    def source(self, size=(3000, 1600), alpha=False):
        path = self.root / ('transparent.png' if alpha else 'original.bmp')
        image = QImage(*size, QImage.Format.Format_ARGB32 if alpha else QImage.Format.Format_RGB32)
        image.fill(QColor(20, 100, 180, 60 if alpha else 255))
        self.assertTrue(image.save(str(path)))
        return path

    def entry(self):
        self.window.new_article()
        self.window.confirm_article(self.window.current_id)
        return self.window.current_id

    def test_original_is_byte_identical_and_compression_keeps_source(self):
        key = self.entry()
        source = self.source()
        before = source.read_bytes()
        service = self.window.attachments
        original = service.add_image(key, source, False)
        self.assertEqual((self.window.database.root/original).read_bytes(), before)
        compressed = service.add_image(key, source, True)
        target = self.window.database.root/compressed
        image = QImage(str(target))
        self.assertEqual(image.width(), 2560)
        self.assertAlmostEqual(image.width()/image.height(), 3000/1600, places=2)
        self.assertLess(target.stat().st_size, len(before))
        self.assertEqual(source.read_bytes(), before)
        row = next(r for r in service.list(key) if r['relative_path'] == compressed)
        self.assertEqual(row['mime_type'], 'image/jpeg')

    def test_transparency_is_preserved(self):
        key = self.entry()
        source = self.source((3200, 1200), True)
        relative = self.window.attachments.add_image(key, source, True)
        image = QImage(str(self.window.database.root/relative))
        self.assertTrue(image.hasAlphaChannel())
        self.assertEqual(image.pixelColor(10, 10).alpha(), 60)
        self.assertEqual(Path(relative).suffix, '.png')

    def test_cancel_import_leaves_no_attachment_or_reference(self):
        self.entry()
        source = self.source((80, 60))
        before = self.window.editor.toHtml()
        with patch('northdiary.ui.main_window.QFileDialog.getOpenFileName', return_value=(str(source), '')), patch('northdiary.ui.main_window.choose_image_compression', return_value=None):
            self.window.insert_image()
        self.assertEqual(self.window.attachments.list(self.window.current_id), [])
        self.assertEqual(self.window.editor.toHtml(), before)

    def test_image_import_choices_apply_to_both_image_and_attachment_entry(self):
        key = self.entry()
        source = self.source()
        for callback, compress in ((self.window.insert_image, True), (self.window.add_attachment, False)):
            with patch('northdiary.ui.main_window.QFileDialog.getOpenFileName', return_value=(str(source), '')), patch('northdiary.ui.main_window.choose_image_compression', return_value=compress):
                callback()
        rows = self.window.attachments.list(key)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['mime_type'], 'image/jpeg')
        self.assertEqual((self.window.database.root/rows[1]['relative_path']).read_bytes(), source.read_bytes())

    def test_card_sizes_follow_photo_aspect_and_heading_stays_attached_after_reading(self):
        key = self.entry()
        for width, height in ((240, 80), (80, 240), (160, 160)):
            pixmap = QPixmap(width, height); pixmap.fill(Qt.GlobalColor.red)
            item = QListWidgetItem('photo');item.setData(Qt.ItemDataRole.UserRole, str(width))
            item.setIcon(QIcon(pixmap))
            size = photo_size(item)
            self.assertAlmostEqual(size.width()/size.height(), width/height, delta=.1)
            self.window.image_list.addItem(item)
            self.assertEqual(item.sizeHint(), size+QSize(34, 52))
        for reading in (True, False):
            self.window.preview.setChecked(reading);self.window.toggle_preview();test_ui.APP.processEvents()
        panel = self.window.photo_layout
        self.assertEqual(panel.indexOf(self.window.image_list), panel.indexOf(self.window.image_hint)+1)
        self.assertLessEqual(self.window.image_list.y()-self.window.photo_title.geometry().bottom()-1, 2)

    def test_panorama_keeps_both_edges_when_painted(self):
        pixmap = QPixmap(240, 80);pixmap.fill(Qt.GlobalColor.green)
        p = QPainter(pixmap)
        p.fillRect(0, 0, 40, 80, Qt.GlobalColor.red)
        p.fillRect(200, 0, 40, 80, Qt.GlobalColor.blue)
        p.end()
        item = QListWidgetItem('panorama');item.setIcon(QIcon(pixmap))
        for seed in range(100):
            item.setData(Qt.ItemDataRole.UserRole, str(seed))
            if photo_seed(item) % 9 == 4:
                break
        size = photo_size(item)+QSize(34, 52)
        output = QImage(size, QImage.Format.Format_RGB32);output.fill(Qt.GlobalColor.black)
        painter = QPainter(output)
        paint_photo(painter, QRectF(output.rect()), item, widget=self.window.image_list)
        painter.end()
        colors = [output.pixelColor(x, y).name() for y in range(output.height()) for x in range(output.width())]
        self.assertGreater(colors.count('#ff0000'), 100)
        self.assertGreater(colors.count('#0000ff'), 100)
