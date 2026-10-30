"""A right-anchored, animated clip for the header controls."""
from PySide6.QtCore import Qt, QSize, QEvent, Signal, QPropertyAnimation, QParallelAnimationGroup, QEasingCurve
from PySide6.QtWidgets import QWidget, QHBoxLayout, QToolButton, QSizePolicy, QGraphicsOpacityEffect, QComboBox


class ToolsClip(QWidget):
    def __init__(self, content, parent):
        super().__init__(parent)
        self.content = content
        content.setParent(self)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def sizeHint(self):
        size = self.content.sizeHint()
        return QSize(size.width() + 6, max(32, size.height()))

    def minimumSizeHint(self):
        return QSize(0, self.sizeHint().height())


class HeaderTools(QWidget):
    collapsedChanged = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.collapsed = False
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.tools = QWidget()
        self.tools_layout = QHBoxLayout(self.tools)
        self.tools_layout.setContentsMargins(0, 0, 0, 0)
        self.tools_layout.setSpacing(6)
        self.clip = ToolsClip(self.tools, self)
        self.arrow = QToolButton(self)
        self.arrow.setFixedSize(28, 32)
        self.arrow.setObjectName('articleTool')
        self.arrow.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.arrow.clicked.connect(lambda: self.set_collapsed(not self.collapsed))
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        row.addWidget(self.arrow)
        row.addWidget(self.clip)
        self.opacity = QGraphicsOpacityEffect(self.tools)
        self.opacity.setOpacity(1.0)
        self.tools.setGraphicsEffect(self.opacity)
        self.animation = QParallelAnimationGroup(self)
        self.width_animation = QPropertyAnimation(self.clip, b'maximumWidth', self.animation)
        self.fade_animation = QPropertyAnimation(self.opacity, b'opacity', self.animation)
        for animation in (self.width_animation, self.fade_animation):
            animation.setDuration(180)
            animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
            self.animation.addAnimation(animation)
        self.animation.finished.connect(self.finish_animation)
        self.tools.installEventFilter(self)
        self.sync_size()
        self.update_arrow()

    def add_widget(self, widget):
        self.tools_layout.addWidget(widget)
        self.sync_size()

    def eventFilter(self, watched, event):
        if watched is self.tools and event.type() in (QEvent.Type.LayoutRequest, QEvent.Type.StyleChange, QEvent.Type.FontChange):
            self.sync_size()
        return super().eventFilter(watched, event)

    def sync_size(self):
        size = self.tools.sizeHint()
        self.tools.setFixedSize(size)
        self.tools.move(6, 0)
        self.clip.setFixedHeight(max(32, size.height()))
        if self.animation.state() != QParallelAnimationGroup.State.Running:
            self.clip.setMaximumWidth(0 if self.collapsed else size.width() + 6)
        self.updateGeometry()

    def update_arrow(self):
        self.arrow.setArrowType(Qt.ArrowType.LeftArrow if self.collapsed else Qt.ArrowType.RightArrow)
        text = '展开右上角功能' if self.collapsed else '收起右上角功能'
        self.arrow.setToolTip(text)
        self.arrow.setAccessibleName(text)

    def set_collapsed(self, collapsed, animate=True):
        collapsed = bool(collapsed)
        self.animation.stop()
        self.collapsed = collapsed
        self.update_arrow()
        for combo in self.tools.findChildren(QComboBox):
            combo.hidePopup()
        self.tools.setEnabled(False)
        if collapsed:
            self.arrow.setFocus(Qt.FocusReason.OtherFocusReason)
        self.clip.show()
        target = 0 if collapsed else self.tools.sizeHint().width() + 6
        if animate:
            self.width_animation.setStartValue(self.clip.maximumWidth())
            self.width_animation.setEndValue(target)
            self.fade_animation.setStartValue(self.opacity.opacity())
            self.fade_animation.setEndValue(0.0 if collapsed else 1.0)
            self.animation.start()
        else:
            self.clip.setMaximumWidth(target)
            self.opacity.setOpacity(0.0 if collapsed else 1.0)
            self.finish_animation()
        self.collapsedChanged.emit(collapsed)

    def finish_animation(self):
        self.clip.setVisible(not self.collapsed)
        self.tools.setEnabled(not self.collapsed)
        self.sync_size()
