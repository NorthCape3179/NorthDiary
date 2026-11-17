from PySide6.QtWidgets import QMessageBox


def choose_image_compression(parent):
    box = QMessageBox(parent)
    box.setWindowTitle('导入图片')
    box.setText('选择图片保存方式')
    box.setInformativeText('保留原图：按原文件保存。\n自动压缩：大图最长边缩至 2560 像素以内，保留透明背景。\n若压缩后文件更大，或图片为动图，则保留原图。\n两种方式都不会修改电脑上的原文件。')
    original = box.addButton('保留原图', QMessageBox.ButtonRole.AcceptRole)
    compressed = box.addButton('自动压缩', QMessageBox.ButtonRole.AcceptRole)
    cancel = box.addButton(QMessageBox.StandardButton.Cancel)
    cancel.setText('取消')
    box.setDefaultButton(original)
    box.setEscapeButton(cancel)
    box.exec()
    clicked = box.clickedButton()
    return False if clicked is original else True if clicked is compressed else None
