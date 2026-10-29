from PySide6.QtCore import Qt
from PySide6.QtGui import QImageReader, QPixmap, QKeySequence, QShortcut
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QGraphicsView, QGraphicsScene


def read_image(path, limit=2400):
    reader = QImageReader(str(path))
    reader.setAutoTransform(True)
    size = reader.size()
    if size.width() > limit or size.height() > limit:
        size.scale(limit, limit, Qt.AspectRatioMode.KeepAspectRatio)
        reader.setScaledSize(size)
    image = reader.read()
    if image.isNull():
        raise ValueError('图片缺失或无法读取，请检查附件文件。')
    return QPixmap.fromImage(image)


class ImageViewer(QDialog):
    def __init__(self, images, index, root, parent=None):
        super().__init__(parent)
        self.images, self.index, self.root = images, index, root
        self.setWindowTitle('图片查看')
        self.resize(960, 720)
        layout = QVBoxLayout(self)
        self.view = QGraphicsView()
        self.scene = QGraphicsScene(self)
        self.view.setScene(self.scene)
        self.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        layout.addWidget(self.view, 1)
        self.info = QLabel()
        self.info.setTextFormat(Qt.TextFormat.PlainText)
        self.info.setWordWrap(True)
        layout.addWidget(self.info)
        controls = QHBoxLayout()
        for title, action in [('上一张', lambda: self.change(-1)), ('缩小', lambda: self.view.scale(.8, .8)),
                              ('适应窗口', self.fit), ('放大', lambda: self.view.scale(1.25, 1.25)),
                              ('下一张', lambda: self.change(1)), ('关闭', self.accept)]:
            button = QPushButton(title)
            button.clicked.connect(action)
            controls.addWidget(button)
        layout.addLayout(controls)
        QShortcut(QKeySequence('Left'), self, activated=lambda: self.change(-1))
        QShortcut(QKeySequence('Right'), self, activated=lambda: self.change(1))
        self.load()

    def load(self):
        row = self.images[self.index]
        self.scene.clear()
        self.view.resetTransform()
        try:
            self.scene.addPixmap(read_image(self.root / row['relative_path']))
            self.info.setText(f"{self.index + 1} / {len(self.images)}  ·  {row['caption'] or row['name']}")
        except ValueError as error:
            self.info.setText(str(error))
        self.scene.setSceneRect(self.scene.itemsBoundingRect())
        self.fit()

    def fit(self):
        if self.scene.items():
            self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def showEvent(self, event):
        super().showEvent(event)
        self.fit()

    def change(self, step):
        self.index = (self.index + step) % len(self.images)
        self.load()
