from pathlib import Path

from PySide6.QtCore import QDate, QTimer, Qt, QUrl, QSize, QSettings
from PySide6.QtGui import QAction, QFont, QImageReader, QKeySequence, QIcon, QDesktopServices
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QLabel, QPushButton,
    QLineEdit, QDateEdit, QListWidget, QListWidgetItem, QComboBox, QFileDialog, QMessageBox, QInputDialog, QScrollArea, QFrame, QToolButton, QMenu,
)

from northdiary import __version__
from northdiary.services.attachments import AttachmentService
from northdiary.services.epub import EpubExporter
from northdiary.services.importing import EpubImporter
from northdiary.ui.export_dialog import ExportDialog
from northdiary.services.backup import BackupService
from northdiary.storage.repository import ArticleRepository
from northdiary.ui.editor import ArticleEditor
from northdiary.ui.theme import STYLE, apply_theme
from northdiary.ui.image_viewer import ImageViewer, read_image
from northdiary.ui.timeline import Timeline
from northdiary.ui.tag_picker import TagPicker
from northdiary.ui.article_list import ArticleList
from northdiary.ui.controls import ComboBox as QComboBox, ButtonFeedback, FloatingPanel
from northdiary.ui.trash_dialog import TrashDialog
from northdiary.ui.icons import pin_icon, landscape_icon
from northdiary.ui.season_background import SeasonPaper
from northdiary.ui.image_board import ImageBoard
from northdiary.ui.category_picker import CategoryPicker
from northdiary.ui.overview_dialog import OverviewDialog
from northdiary.ui.date_picker import DateInput, matches_day
from northdiary.ui.header_tools import HeaderTools


def label(text, name='muted'):
    widget = QLabel(text)
    widget.setObjectName(name)
    widget.setWordWrap(True)
    return widget


class MainWindow(QMainWindow):
    def __init__(self, database):
        super().__init__()
        self.database = database
        self.repository = ArticleRepository(database)
        self.attachments = AttachmentService(database)
        self.backups = BackupService(database)
        self.person_ids = []
        self.current_id = None
        self.loading = False
        self.dirty = False
        self.trash = False
        self.category = None
        self.tag = None
        self.browse_date = None
        self.list_mode = 'all'
        self.sort_key = 'created_desc'
        self.setWindowTitle(f'NorthDiary v{__version__} · 留下值得记住的日常')
        self.resize(1280, 820)
        self.setMinimumSize(1000, 640)
        self.setStyleSheet(STYLE)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(900)
        self.timer.timeout.connect(lambda: self.save(False))
        self.build_ui()
        self.button_feedback = ButtonFeedback(self)
        self.ui_settings = QSettings(str(database.root / 'ui.ini'), QSettings.Format.IniFormat)
        self.header_tools.set_collapsed(self.ui_settings.value('header_collapsed', False, type=bool), animate=False)
        self.header_tools.collapsedChanged.connect(self.remember_header_state)
        self.recent_ids = self.ui_settings.value('recent_articles', [], type=list)
        saved_sort = self.ui_settings.value('article_sort', 'created_desc')
        index = self.sort_combo.findData(saved_sort)
        self.sort_combo.blockSignals(True)
        self.sort_combo.setCurrentIndex(max(0, index))
        self.sort_combo.blockSignals(False)
        self.sort_key = self.sort_combo.currentData()
        self.set_theme(self.ui_settings.value('dark', False, type=bool), self.ui_settings.value('theme_name', ''))
        self.set_background(self.ui_settings.value('season_background', True, type=bool))
        self.refresh_categories()
        self.refresh_list()
        if self.article_list.count():
            self.article_list.setCurrentRow(0)
        else:
            self.load_article(None)

    def button(self, text, callback, primary=False):
        widget = QPushButton(text)
        if primary:
            widget.setObjectName('primary')
        widget.clicked.connect(callback)
        return widget

    def build_ui(self):
        frame = QWidget()
        outer = QVBoxLayout(frame)
        outer.setContentsMargins(20, 16, 20, 8)
        header = QHBoxLayout()
        header.addWidget(label('NorthDiary', 'brand'))
        header.addStretch()
        self.header_tools = HeaderTools()
        self.light_theme_combo = QComboBox()
        self.dark_theme_combo = QComboBox()
        for combo, title, choices in (
            (self.light_theme_combo, '浅色主题', [('鼠尾草绿白', 'light'), ('浅咖米白', 'cream'), ('酒红米白', 'burgundy'), ('橙绿米白', 'citrus'), ('蓝与纯白', 'blue'), ('灰与浅灰', 'gray')]),
            (self.dark_theme_combo, '深色主题', [('灰黑夜色', 'dark'), ('黑红夜色', 'wine')]),
        ):
            combo.addItem(title, None)
            for text, key in choices: combo.addItem(text, key)
            combo.setFixedWidth(124)
            combo.setAccessibleName(title)
            combo.setToolTip(title)
            combo.currentIndexChanged.connect(lambda _, c=combo: self.choose_theme(c))
            self.header_tools.add_widget(combo)
        self.header_tools.add_widget(self.button('数据文件夹', lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.database.root)))))
        self.header_tools.add_widget(self.button('保存  Ctrl+S', lambda: self.save(True)))
        header.addWidget(self.header_tools)
        outer.addLayout(header)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        outer.addWidget(self.splitter, 1)
        self.setCentralWidget(frame)

        sidebar = QWidget()
        sidebar.setObjectName('sidebar')
        left = QVBoxLayout(sidebar)
        left.setContentsMargins(16, 20, 16, 16)
        left.addWidget(label('我的文集', 'section'))
        left.addWidget(self.button('＋  新建文章', self.new_article, True))
        self.search = QLineEdit()
        self.search.setPlaceholderText('搜索标题与正文…')
        left.addWidget(self.search)
        self.category_filter = QComboBox()
        self.category_filter.addItem('所有分类', None)
        self.category_filter.currentIndexChanged.connect(self.change_category)
        left.addWidget(self.category_filter)
        self.tag_filter = QComboBox()
        self.tag_filter.addItem('所有标签', None)
        self.tag_filter.currentIndexChanged.connect(self.change_tag)
        left.addWidget(self.tag_filter)
        self.list_count = label('0 篇文章')
        mode_row = QHBoxLayout()
        mode_row.addWidget(self.list_count, 1)
        self.article_mode = QComboBox()
        self.article_mode.addItem('全部文章', 'all')
        self.article_mode.addItem('所选日期', 'date')
        self.article_mode.addItem('最近打开', 'recent')
        self.article_mode.setToolTip('跨日期查看全部文章，按所选日期浏览，或查看最近打开')
        self.article_mode.setFixedHeight(30)
        self.article_mode.setStyleSheet('QComboBox { padding: 3px 20px 3px 6px; font-size: 11px; }')
        self.article_mode.setMinimumContentsLength(6)
        self.article_mode.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.article_mode.currentIndexChanged.connect(self.change_article_mode)
        mode_row.addWidget(self.article_mode)
        left.addLayout(mode_row)
        self.sort_combo = QComboBox()
        for text, key in [('创建时间：最新优先', 'created_desc'), ('创建时间：最早优先', 'created_asc'),
                          ('修改时间：最新优先', 'updated_desc'), ('修改时间：最早优先', 'updated_asc'),
                          ('标题：升序', 'title'), ('手动排列', 'manual')]:
            self.sort_combo.addItem(text, key)
        self.sort_combo.setToolTip('置顶文章始终在前，各组内按此规则排序；标题按字符顺序排列')
        self.sort_combo.currentIndexChanged.connect(self.change_sort)
        self.sort_combo.setParent(sidebar)
        self.sort_combo.hide()
        self.article_list = ArticleList()
        self.article_list.orderRequested.connect(self.reorder_articles)
        self.article_list.currentItemChanged.connect(self.select_article)
        self.article_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.article_list.customContextMenuRequested.connect(self.show_article_menu)
        left.addWidget(self.article_list, 1)
        left.addWidget(self.button('时间线总览', self.open_timeline_overview))
        left.addWidget(self.button('文章总览', self.open_overview))
        left.addWidget(self.button('随机回忆', self.open_random_memory))
        left.addWidget(self.button('人物档案', self.open_people))
        self.trash_button = self.button('回收站', self.open_trash)
        left.addWidget(self.trash_button)
        self.search.textChanged.connect(self.filter_search)
        self.splitter.addWidget(sidebar)

        paper = SeasonPaper()
        self.paper = paper
        paper.setObjectName('paper')
        center = QVBoxLayout(paper)
        self.center_layout = center
        center.setContentsMargins(30, 12, 30, 20)
        tool_band = QWidget()
        band_layout = QVBoxLayout(tool_band)
        band_layout.setContentsMargins(0, 0, 0, 0)
        band_layout.setSpacing(0)
        for_top = QFrame()
        for_top.setObjectName('toolDivider')
        for_top.setFixedHeight(1)
        band_layout.addWidget(for_top)
        tool_strip = QWidget()
        tool_strip.setObjectName('articleTools')
        tool_strip.setFixedHeight(26)
        article_bar = QHBoxLayout(tool_strip)
        article_bar.setContentsMargins(0, 0, 0, 0)
        article_bar.setSpacing(4)
        self.pin_button = QToolButton()
        self.pin_button.setObjectName('articleTool')
        self.pin_button.setFixedSize(24, 24)
        self.pin_button.setIconSize(QSize(20, 20))
        self.pin_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.pin_button.clicked.connect(self.toggle_pin)
        self.pin_button.setCheckable(True)
        self.pin_button.setAccessibleName('置顶文章')
        article_bar.addWidget(self.pin_button)
        self.background_button = QToolButton()
        self.background_button.setObjectName('articleTool')
        self.background_button.setFixedSize(24, 24)
        self.background_button.setIconSize(QSize(20, 20))
        self.background_button.setCheckable(True)
        self.background_button.setAccessibleName('季节背景')
        self.background_button.clicked.connect(lambda checked: self.set_background(checked))
        article_bar.addWidget(self.background_button)
        article_bar.addStretch()
        band_layout.addWidget(tool_strip)
        divider = QFrame()
        divider.setObjectName('toolDivider')
        divider.setFixedHeight(1)
        band_layout.addWidget(divider)
        center.addWidget(tool_band)
        row = QHBoxLayout()
        row.addWidget(label('日期'))
        self.date = DateInput(QDate.currentDate())
        self.date.dateChanged.connect(self.update_date_background)
        self.date.dateChanged.connect(self.select_creation_date)
        self.update_date_background()
        row.addWidget(self.date)
        self.timeline = Timeline()
        self.date.dateChanged.connect(lambda date: self.timeline.setDate(date) if not self.loading or not self.browse_date else None)
        self.timeline_preview_timer = QTimer(self)
        self.timeline_preview_timer.setSingleShot(True)
        self.timeline_preview_timer.setInterval(90)
        self.timeline_preview_timer.timeout.connect(self.apply_timeline_preview)
        self.pending_timeline_date = None
        self.timeline.dateSelected.connect(self.commit_timeline_day)
        self.timeline.datePreviewed.connect(self.preview_timeline_day)
        row.addWidget(self.timeline, 1)
        self.date_scope_button = self.button('当前日期', self.toggle_date_scope)
        row.addWidget(self.date_scope_button)
        self.preview = self.button('阅读模式', self.toggle_preview)
        self.preview.setCheckable(True)
        row.addWidget(self.preview)
        center.addLayout(row)
        self.title = QLineEdit()
        self.title.setObjectName('title')
        self.title.setPlaceholderText('给今天一个标题')
        center.addWidget(self.title)
        toolbar = QHBoxLayout()
        self.bold = self.button('加粗', self.toggle_bold)
        self.italic = self.button('斜体', self.toggle_italic)
        self.indent_button = self.button('自动缩进', self.editor_indent)
        self.indent_button.setToolTip('将全文各段首行缩进两个汉字，重复点击不叠加')
        self.bold.setCheckable(True)
        self.italic.setCheckable(True)
        self.image_button = self.button('插入图片', self.insert_image)
        toolbar.addWidget(self.bold)
        toolbar.addWidget(self.italic)
        toolbar.addWidget(self.indent_button)
        toolbar.addWidget(self.image_button)
        toolbar.addStretch()
        center.addLayout(toolbar)
        self.editor = ArticleEditor()
        self.editor.setObjectName('articleEditor')
        self.editor.setStyleSheet('QTextEdit#articleEditor { background: transparent; }')
        self.editor.viewport().setAutoFillBackground(False)
        self.editor.viewport().setStyleSheet('background: transparent;')
        self.editor.imageActivated.connect(self.open_image)
        self.editor.setPlaceholderText('点击左侧「新建文章」，开始记录。')
        self.editor.document().setBaseUrl(QUrl.fromLocalFile(str(self.database.root) + '/'))
        self.editor.document().setDefaultFont(QFont('Microsoft YaHei UI', 12))
        center.addWidget(self.editor, 1)
        self.word_count = label('0 字符')
        center.addWidget(self.word_count)
        self.splitter.addWidget(paper)

        properties = QWidget()
        properties.setObjectName('properties')
        right = QVBoxLayout(properties)
        right.setContentsMargins(18, 22, 18, 18)
        right.addWidget(label('文章属性', 'section'))
        right.addWidget(label('分类'))
        self.categories = CategoryPicker()
        right.addWidget(self.categories)
        right.addWidget(label('标签'))
        self.tags = TagPicker()
        right.addWidget(self.tags)
        people_row = QHBoxLayout()
        self.people_button = self.button('人物标签', self.pick_people)
        people_row.addWidget(self.people_button, 1)
        self.people_expand = QToolButton()
        self.people_expand.setArrowType(Qt.ArrowType.RightArrow)
        self.people_expand.setCheckable(True)
        self.people_expand.setAccessibleName('展开人物代号快捷插入')
        self.people_expand.toggled.connect(self.toggle_people_shortcuts)
        people_row.addWidget(self.people_expand)
        right.addLayout(people_row)
        self.timestamps = label('尚未选择文章')
        self.timestamps.setTextFormat(Qt.TextFormat.PlainText)
        right.addWidget(self.timestamps)
        right.addSpacing(18)
        self.photo_panel = QWidget()
        self.photo_layout = QVBoxLayout(self.photo_panel)
        self.photo_layout.setContentsMargins(0, 0, 0, 0)
        self.photo_title = label('文章图片', 'section')
        self.photo_layout.addWidget(self.photo_title)
        right.addWidget(self.photo_panel)
        self.reading_nav = QWidget()
        nav = QVBoxLayout(self.reading_nav)
        nav.setContentsMargins(0, 0, 0, 0)
        nav.addWidget(label('文章浏览', 'section'))
        self.reading_date = DateInput(QDate.currentDate())
        nav.addWidget(self.reading_date)
        for previous_text, next_text, months in [('前一天', '后一天', False), ('上个月', '下个月', True)]:
            buttons = QHBoxLayout()
            buttons.addWidget(self.button(previous_text, lambda checked=False, m=months: self.shift_reading_date(-1, m)))
            buttons.addWidget(self.button(next_text, lambda checked=False, m=months: self.shift_reading_date(1, m)))
            nav.addLayout(buttons)
        pages = QHBoxLayout()
        self.previous_article = self.button('上一篇', lambda: self.step_reading_article(-1))
        self.next_article = self.button('下一篇', lambda: self.step_reading_article(1))
        pages.addWidget(self.previous_article); pages.addWidget(self.next_article)
        nav.addLayout(pages)
        self.reading_count = label('')
        nav.addWidget(self.reading_count)
        self.reading_articles = QListWidget()
        self.reading_articles.setMinimumHeight(140)
        self.reading_articles.setMaximumHeight(250)
        self.reading_articles.itemClicked.connect(lambda item: self.open_reading_article(item.data(Qt.ItemDataRole.UserRole)))
        nav.addWidget(self.reading_articles)
        self.reading_date.dateChanged.connect(self.reading_day_changed)
        right.addWidget(self.reading_nav)
        self.reading_nav.hide()
        self.image_hint = label('暂无图片')
        self.photo_layout.addWidget(self.image_hint)
        self.image_list = ImageBoard()
        self.image_list.setIconSize(QSize(96, 72))
        self.image_list.setMinimumHeight(260)
        self.image_list.setMaximumHeight(320)
        self.image_list.itemDoubleClicked.connect(lambda item: self.open_image(item.data(Qt.ItemDataRole.UserRole)))
        self.image_list.currentItemChanged.connect(lambda *_: self.update_image_actions())
        self.photo_layout.addWidget(self.image_list, 1)
        self.image_actions = QWidget()
        action_layout = QVBoxLayout(self.image_actions)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.addWidget(label('图片操作', 'section'))
        image_tools = QHBoxLayout()
        self.locate_button = self.button('跳到引用位置', self.locate_selected_image)
        self.caption_button = self.button('编辑图注', self.edit_image_caption)
        image_tools.addWidget(self.locate_button)
        image_tools.addWidget(self.caption_button)
        action_layout.addLayout(image_tools)
        self.place_link_button = self.button('在光标处插入图片引用', self.place_selected_link)
        action_layout.addWidget(self.place_link_button)
        self.remove_link_button = self.button('移除引用（保留图片）', self.remove_selected_link)
        action_layout.addWidget(self.remove_link_button)
        self.photo_layout.addWidget(self.image_actions)
        self.image_actions.hide()
        right.addWidget(label('附件', 'section'))
        self.attachment_list = QListWidget()
        self.attachment_list.setMaximumHeight(150)
        right.addWidget(self.attachment_list)
        self.attachment_button = self.button('＋  添加附件', self.add_attachment)
        right.addWidget(self.attachment_button)
        right.addWidget(label('文集工具', 'section'))
        right.addWidget(self.button('导出备份', self.backup))
        right.addWidget(self.button('导出 EPUB', self.export_epub))
        right.addWidget(self.button('导入 NorthDiary EPUB', self.import_epub))
        right.addWidget(self.button('GitHub 上传与下载', self.open_github))
        right.addWidget(label('备份恢复界面将在后续版本接入。'))
        self.delete_button = self.button('移入回收站', self.delete_or_restore)
        right.addWidget(self.delete_button)
        property_scroll = QScrollArea()
        property_scroll.setWidgetResizable(True)
        property_scroll.setFrameShape(QFrame.Shape.NoFrame)
        property_scroll.setWidget(properties)
        property_scroll.setMinimumWidth(240)
        self.splitter.addWidget(property_scroll)
        self.people_shortcuts = QScrollArea()
        self.people_shortcuts.setWidgetResizable(True)
        self.people_shortcuts.setMinimumWidth(230)
        self.people_shortcuts.setMaximumWidth(380)
        self.shortcut_body = QWidget()
        from PySide6.QtWidgets import QGridLayout
        self.shortcut_grid = QGridLayout(self.shortcut_body)
        self.shortcut_grid.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.people_shortcuts.setWidget(self.shortcut_body)
        self.splitter.addWidget(self.people_shortcuts)
        self.people_shortcuts.hide()
        self.splitter.setSizes([245, 690, 255, 0])
        self.statusBar().showMessage('数据目录：' + str(self.database.root))

        for signal in (self.title.textChanged, self.date.dateChanged,
                       self.editor.textChanged, self.categories.changed, self.tags.changed):
            signal.connect(self.mark_dirty)
        self.editor.currentCharFormatChanged.connect(self.sync_format_buttons)
        save_action = QAction('保存', self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(lambda: self.save(True))
        self.addAction(save_action)
        new_action = QAction('新建文章', self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self.new_article)
        self.addAction(new_action)
        fullscreen_action = QAction('切换全屏', self)
        fullscreen_action.setShortcut(QKeySequence('F11'))
        fullscreen_action.triggered.connect(self.toggle_fullscreen)
        self.addAction(fullscreen_action)
        exit_fullscreen = QAction('退出全屏', self)
        exit_fullscreen.setShortcut(QKeySequence('Escape'))
        exit_fullscreen.triggered.connect(self.leave_fullscreen)
        self.addAction(exit_fullscreen)

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.leave_fullscreen()
        else:
            self.was_maximized = self.isMaximized()
            self.showFullScreen()

    def leave_fullscreen(self):
        panels = [panel for panel in self.findChildren(FloatingPanel) if panel.isVisible()]
        if panels:
            for panel in panels:
                panel.hide()
            return
        if self.isFullScreen():
            if getattr(self, 'was_maximized', False):
                self.showMaximized()
            else:
                self.showNormal()

    def fail(self, error):
        QMessageBox.warning(self, '操作未完成', str(error))

    def choose_theme(self, combo):
        name = combo.currentData()
        if name:
            self.set_theme(name in ('dark', 'wine'), name)

    def set_theme(self, dark, name=None):
        if not name:
            name = self.ui_settings.value('last_dark_theme' if dark else 'last_light_theme', 'dark' if dark else 'light')
        if name not in ('light', 'dark', 'cream', 'wine', 'burgundy', 'citrus', 'blue', 'gray'):
            name = 'dark' if dark else 'light'
        dark = name in ('dark', 'wine')
        apply_theme(self, dark, name)
        for combo in (self.light_theme_combo, self.dark_theme_combo):
            combo.blockSignals(True)
            combo.setCurrentIndex(max(0, combo.findData(name)))
            combo.blockSignals(False)
        self.ui_settings.setValue('dark', dark)
        self.ui_settings.setValue('theme_name', name)
        self.ui_settings.setValue('last_dark_theme' if dark else 'last_light_theme', name)
        self.ui_settings.sync()
        self.update_pin()
        self.background_button.setIcon(landscape_icon(dark, self.devicePixelRatioF(), self.property('colorTheme')))
        self.paper.refresh_background(force=True)
        self.refresh_list()

    def set_background(self, enabled):
        self.paper.set_enabled(enabled)
        self.background_button.setChecked(enabled)
        self.background_button.setToolTip('隐藏季节背景' if enabled else '显示季节背景')
        self.ui_settings.setValue('season_background', enabled)
        self.ui_settings.sync()

    def sync_format_buttons(self, fmt):
        self.bold.setChecked(fmt.fontWeight() >= QFont.Weight.Bold)
        self.italic.setChecked(fmt.fontItalic())

    def update_image_actions(self):
        if not hasattr(self, 'place_link_button'):
            return
        key = self.selected_image_id()
        self.image_actions.setVisible(bool(key) and not self.preview.isChecked())
        has_images = self.image_list.count() > 0
        self.image_list.setVisible(has_images)
        self.image_hint.setVisible(not has_images)
        editable = bool(self.current_id) and not self.trash and not self.preview.isChecked()
        linked = bool(key and self.editor.image_links(key))
        self.locate_button.setEnabled(linked)
        self.caption_button.setEnabled(bool(key) and editable)
        self.place_link_button.setEnabled(bool(key) and editable)
        self.remove_link_button.setEnabled(linked and editable)

    def select_creation_date(self, date):
        if self.loading or self.current_id:
            return
        self.browse_date = date.toString('yyyy-MM-dd')
        self.article_mode.blockSignals(True)
        self.article_mode.setCurrentIndex(self.article_mode.findData('date'))
        self.article_mode.blockSignals(False)
        self.list_mode = 'date'
        self.refresh_list()

    def update_date_background(self, *_):
        self.paper.month_unknown = self.date.precision == 'year'
        self.paper.set_article_date(self.date.date())
        self.paper.update()

    def mark_dirty(self, *_):
        if self.loading or not self.current_id or self.trash:
            return
        self.dirty = True
        self.word_count.setText(f'{len(self.editor.toPlainText())} 字符')
        self.timer.start()
        self.update_image_actions()

    def save(self, notify=False):
        self.timer.stop()
        if not self.dirty or not self.current_id:
            return True
        try:
            split = lambda text: text.replace('，', ',').split(',')
            self.repository.save(self.current_id, self.title.text(), self.date.text(),
                                 self.editor.toHtml(), self.editor.toPlainText(),
                                 split(self.categories.text()), self.tags.normal_names, self.tags.temporary_names, self.person_ids)
        except Exception as error:
            self.statusBar().showMessage('保存失败 · 内容仍保留，请重试：' + str(error))
            if notify:
                self.fail(error)
            return False
        self.dirty = False
        if self.statusBar().currentMessage().startswith('保存失败'):
            self.statusBar().showMessage('数据目录：' + str(self.database.root))
        self.refresh_categories()
        QTimer.singleShot(0, self.refresh_list)
        # Avoid a list rebuild while typing, preserving selection and focus.
        for index in range(self.article_list.count()):
            item = self.article_list.item(index)
            if item.data(Qt.ItemDataRole.UserRole) == self.current_id:
                item.setText(self.item_text(self.repository.get(self.current_id)))
        self.update_properties()
        return True

    def item_text(self, article):
        return f'{article.title}\n{article.diary_date}  ·  {len(article.body_text)} 字符'

    def show_article_menu(self, point):
        item = self.article_list.itemAt(point)
        if item:
            menu = self.make_article_menu(item.data(Qt.ItemDataRole.UserRole))
            menu.exec(self.article_list.viewport().mapToGlobal(point))
            menu.deleteLater()

    def make_article_menu(self, article_id):
        article = self.repository.get(article_id)
        menu = QMenu(self)
        menu.addAction('取消置顶' if article.pinned else '置顶', lambda: self.pin_article(article_id))
        menu.addAction('删除', lambda: self.trash_article(article_id))
        if self.article_mode.currentData() == 'recent':
            menu.addSeparator()
            menu.addAction('移出最近打开', lambda: self.remove_recent(article_id))
        return menu

    def pin_article(self, article_id):
        if not self.save(True):
            return
        try:
            article = self.repository.get(article_id)
            self.repository.set_pinned(article_id, not article.pinned)
            self.update_pin()
            self.refresh_list()
        except Exception as error:
            self.fail(error)

    def remove_recent(self, article_id):
        if not self.save(True):
            return
        self.recent_ids = [key for key in self.recent_ids if key != article_id]
        self.ui_settings.setValue('recent_articles', self.recent_ids)
        self.ui_settings.sync()
        self.refresh_list()
        self.statusBar().showMessage('已移出最近打开，文章仍保留在日期列表中。', 5000)

    def trash_article(self, article_id):
        if not self.save(True):
            return
        if QMessageBox.question(self, '移入回收站', '文章和附件会保留，可在回收站恢复。继续？') != QMessageBox.StandardButton.Yes:
            return
        try:
            self.repository.set_deleted(article_id)
            if self.current_id == article_id:
                self.load_article(None)
            self.refresh_list()
        except Exception as error:
            self.fail(error)

    def toggle_pin(self):
        if not self.current_id or not self.save(True):
            self.update_pin()
            return
        try:
            article = self.repository.get(self.current_id)
            self.repository.set_pinned(article.id, not article.pinned)
            self.update_pin()
            self.refresh_list()
        except Exception as error:
            self.update_pin()
            self.fail(error)

    def update_pin(self):
        article = self.repository.get(self.current_id) if self.current_id else None
        pinned = bool(article and article.pinned)
        self.pin_button.setChecked(pinned)
        self.pin_button.setIcon(pin_icon(pinned, bool(self.property('darkTheme')), self.devicePixelRatioF(), self.property('colorTheme')))
        self.pin_button.setToolTip('取消置顶' if pinned else '置顶')
        self.pin_button.setEnabled(bool(article and not self.trash))
        self.article_list.sorting_allowed = not self.trash and self.article_mode.currentData() != 'recent' and self.sort_key == 'manual'

    def reorder_articles(self, article_ids):
        if self.save(True):
            try:
                self.repository.reorder(article_ids)
            except Exception as error:
                self.fail(error)
        self.refresh_list()

    def refresh_list(self):
        self.article_list.blockSignals(True)
        self.article_list.clear()
        rows = self.repository.list(self.search.text(), self.category, self.trash, tag=self.tag, sort=self.sort_key)
        recent = self.article_mode.currentData() == 'recent'
        if recent:
            positions = {key: i for i, key in enumerate(self.recent_ids)}
            rows = [article for article in rows if article.id in positions]
            pinned = [article for article in rows if article.pinned]
            normal = sorted((article for article in rows if not article.pinned), key=lambda article: positions[article.id])
            rows = pinned + normal
        elif self.article_mode.currentData() == 'date' and self.browse_date:
            rows = [article for article in rows if matches_day(article.diary_date, self.browse_date)]
        for article in rows:
            item = QListWidgetItem(self.item_text(article))
            item.setData(Qt.ItemDataRole.UserRole, article.id)
            item.setData(Qt.ItemDataRole.UserRole + 1, article.pinned)
            if article.pinned:
                item.setIcon(pin_icon(True, bool(self.property('darkTheme')), self.devicePixelRatioF(), self.property('colorTheme')))
            self.article_list.addItem(item)
            if article.id == self.current_id:
                self.article_list.setCurrentItem(item)
        self.article_list.blockSignals(False)
        date_label = self.browse_date if self.article_mode.currentData() == 'date' else '全部文章'
        self.list_count.setText(f'{"最近" if recent else date_label}\n{len(rows)} 篇文章')
        self.sort_combo.setEnabled(not recent)
        self.article_list.sorting_allowed = not recent and self.sort_key == 'manual'
        self.article_list.setToolTip('选择“手动排列”可上下拖动；最近打开模式按打开时间排序')
        self.date_scope_button.setText('全部日期' if self.article_mode.currentData() == 'date' else '当前日期')
        self.date_scope_button.setToolTip('切换到全部日期' if self.article_mode.currentData() == 'date' else '切换到当前文章日期')

    def toggle_date_scope(self):
        if self.article_mode.currentData() == 'date':
            self.clear_day()
        else:
            self.browse_day(self.date.date())

    def open_overview(self):
        if not self.save(True): return
        options=[(self.sort_combo.itemText(i),self.sort_combo.itemData(i)) for i in range(self.sort_combo.count())]
        dialog=OverviewDialog(self.repository,options,self.sort_key,self)
        dialog.deleteRequested.connect(self.trash_article)
        dialog.sortingChanged.connect(lambda key: self.sort_combo.setCurrentIndex(self.sort_combo.findData(key)))
        dialog.exec()
        if dialog.article_id:
            self.search.clear();self.category=None;self.tag=None
            self.clear_day();self.refresh_categories()
            self.load_article(dialog.article_id);self.refresh_list()

    def change_sort(self):
        selected = self.sort_combo.currentData()
        if not self.save(True):
            self.sort_combo.blockSignals(True)
            self.sort_combo.setCurrentIndex(self.sort_combo.findData(self.sort_key))
            self.sort_combo.blockSignals(False)
            return
        self.sort_key = selected
        self.ui_settings.setValue('article_sort', selected)
        self.ui_settings.sync()
        self.refresh_list()

    def change_article_mode(self):
        if not self.save(True):
            self.article_mode.blockSignals(True)
            self.article_mode.setCurrentIndex(self.article_mode.findData(self.list_mode))
            self.article_mode.blockSignals(False)
            return
        self.list_mode = self.article_mode.currentData()
        if self.list_mode == 'date' and not self.browse_date:
            self.browse_date = self.date.date().toString('yyyy-MM-dd')
        self.refresh_list()

    def preview_timeline_day(self, date):
        self.pending_timeline_date = QDate(date)
        # Throttle rather than debounce: a long drag still previews periodically.
        if not self.timeline_preview_timer.isActive():
            self.timeline_preview_timer.start()

    def apply_timeline_preview(self):
        date = self.pending_timeline_date
        self.pending_timeline_date = None
        if date is not None:
            self.browse_day(date)

    def commit_timeline_day(self, date):
        self.timeline_preview_timer.stop()
        self.pending_timeline_date = None
        self.browse_day(date)

    def browse_day(self, date):
        if not self.save(True):
            self.timeline.setDate(QDate.fromString(self.browse_date, 'yyyy-MM-dd') if self.browse_date else self.date.date())
            return
        self.browse_date = date.toString('yyyy-MM-dd')
        if not self.timeline.pressed:
            self.timeline.setDate(date)
        repaint = self.updatesEnabled()
        self.setUpdatesEnabled(False)
        try:
            self.article_mode.blockSignals(True)
            self.article_mode.setCurrentIndex(self.article_mode.findData('date'))
            self.list_mode = 'date'
            self.article_mode.blockSignals(False)
            # Choose the destination before changing the editor: no blank frame.
            self.refresh_list()
            item = self.article_list.item(0)
            target = item.data(Qt.ItemDataRole.UserRole) if item else None
            if target != self.current_id:
                self.load_article(target)
            elif target is None:
                # Consecutive empty dates need only date/background updates.
                previous_loading = self.loading
                self.loading = True
                try:
                    self.date.setDate(date)
                    self.update_date_background()
                finally:
                    self.loading = previous_loading
            self.article_list.blockSignals(True)
            try:
                self.article_list.setCurrentRow(0 if item else -1)
            finally:
                self.article_list.blockSignals(False)
            if item is None:
                self.statusBar().showMessage(self.browse_date + ' 没有文章，可新建记录。', 5000)
        finally:
            self.setUpdatesEnabled(repaint)

    def clear_day(self):
        if self.save(True):
            self.browse_date = None
            self.article_mode.blockSignals(True)
            self.article_mode.setCurrentIndex(0)
            self.list_mode = 'all'
            self.article_mode.blockSignals(False)
            self.refresh_list()

    def refresh_categories(self):
        self.categories.set_catalog(self.repository.categories())
        self.category_filter.blockSignals(True)
        self.category_filter.clear()
        self.category_filter.addItem('所有分类', None)
        for name in self.repository.categories():
            self.category_filter.addItem(name, name)
        index = self.category_filter.findData(self.category)
        self.category_filter.setCurrentIndex(max(0, index))
        self.category_filter.blockSignals(False)
        self.tag_filter.blockSignals(True)
        self.tag_filter.clear()
        self.tag_filter.addItem('所有标签', None)
        for name in self.repository.tags():
            self.tag_filter.addItem(name, name)
        self.tag_filter.setCurrentIndex(max(0, self.tag_filter.findData(self.tag)))
        self.tag_filter.blockSignals(False)
        self.tags.set_catalog(self.repository.tags())

    def change_tag(self):
        selected = self.tag_filter.currentData()
        if not self.save(True):
            self.refresh_categories()
            return
        self.tag = selected
        self.refresh_categories()
        self.refresh_list()

    def filter_search(self):
        if self.save(True):
            self.refresh_list()

    def change_category(self):
        selected = self.category_filter.currentData()
        if not self.save(True):
            self.refresh_categories()
            return
        self.category = selected
        self.refresh_categories()
        self.refresh_list()

    def open_trash(self):
        if not self.save(True):
            return
        TrashDialog(self.repository, self).exec()
        self.refresh_categories()
        self.refresh_list()

    def select_article(self, item, previous):
        if item is None:
            return
        if not self.save(True):
            self.article_list.blockSignals(True)
            self.article_list.setCurrentItem(previous)
            self.article_list.blockSignals(False)
            return
        self.load_article(item.data(Qt.ItemDataRole.UserRole))

    def load_article(self, article_id):
        reading = self.preview.isChecked() and not self.trash
        self.loading = True
        self.current_id = article_id
        self.update_pin()
        self.dirty = False
        article = self.repository.get(article_id) if article_id else None
        if article and not article.deleted_at:
            self.recent_ids = [article.id] + [key for key in self.recent_ids if key != article.id]
            self.recent_ids = self.recent_ids[:200]
            self.ui_settings.setValue('recent_articles', self.recent_ids)
            self.ui_settings.sync()
            if self.article_mode.currentData() == 'recent':
                QTimer.singleShot(0, self.refresh_list)
        self.title.setText(article.title if article else '')
        shown_date = article.diary_date if article else self.browse_date or QDate.currentDate().toString('yyyy-MM-dd')
        self.date.setText(shown_date)
        self.update_date_background()
        if article and not self.browse_date:
            self.timeline.setDate(self.date.date())
        self.editor.setHtml(article.body_html if article else '')
        self.categories.setText('，'.join(self.repository.labels(article_id, 'categories')) if article else '')
        self.tags.set_values(self.repository.labels(article_id, 'tags') if article else [],
                             self.repository.temporary_tags(article_id) if article else [])
        from northdiary.storage.people import PeopleRepository
        self.person_ids = [p['id'] for p in PeopleRepository(self.database).for_article(article_id)] if article else []
        self.refresh_people()
        self.word_count.setText(f'{len(self.editor.toPlainText())} 字符')
        self.preview.setChecked(self.trash or reading)
        self.toggle_preview()
        self.delete_button.setText('恢复文章' if self.trash else '移入回收站')
        self.delete_button.setEnabled(article is not None)
        self.update_properties()
        self.loading = False

    def update_properties(self):
        selected = self.selected_image_id() if hasattr(self, 'image_list') else None
        self.image_list.clear()
        self.attachment_list.clear()
        self.attachment_list.hide()
        if not self.current_id:
            self.timestamps.setText('尚未选择文章')
            self.update_image_actions()
            return
        article = self.repository.get(self.current_id)
        self.timestamps.setText('创建  ' + article.created_at[:19].replace('T', ' ') +
                                '\n修改  ' + article.updated_at[:19].replace('T', ' '))
        for attachment in self.attachments.list(self.current_id):
            if attachment['mime_type'].startswith('image/'):
                item = QListWidgetItem(attachment['caption'] or attachment['name'])
                item.setData(Qt.ItemDataRole.UserRole, attachment['id'])
                item.setToolTip(attachment['name'])
                try:
                    item.setIcon(QIcon(read_image(self.database.root / attachment['relative_path'], 160)))
                except ValueError:
                    item.setText('图片缺失 · ' + item.text())
                self.image_list.addItem(item)
                if attachment['id'] == selected:
                    self.image_list.setCurrentItem(item)
            else:
                self.attachment_list.addItem(attachment['name'])
        if self.attachment_list.count():
            row_height = max(28, self.attachment_list.sizeHintForRow(0))
            self.attachment_list.setFixedHeight(min(150, row_height * self.attachment_list.count() + 8))
            self.attachment_list.show()
        self.update_image_actions()

    def toggle_preview(self):
        if not self.loading and self.preview.isChecked() and not self.save(True):
            self.preview.setChecked(False)
        editable = bool(self.current_id) and not self.trash and not self.preview.isChecked()
        self.editor.setReadOnly(not editable)
        for widget in (self.title, self.date, self.categories, self.tags, self.bold,
                       self.italic, self.indent_button, self.image_button, self.attachment_button, self.people_button,
                       self.caption_button, self.remove_link_button, self.place_link_button):
            widget.setEnabled(editable)
        self.date.setEnabled(not self.trash and not self.preview.isChecked())
        self.preview.setEnabled(bool(self.current_id) and not self.trash)
        self.preview.setText('返回编辑' if self.preview.isChecked() else '阅读模式')
        self.set_reading_layout(self.preview.isChecked() and not self.trash)
        self.shortcut_body.setEnabled(editable)
        self.update_image_actions()

    def set_reading_layout(self, reading):
        target = self.center_layout if reading else self.photo_layout
        if self.image_list.parentWidget() != target.parentWidget():
            self.image_list.hover_card.hide()
            target.addWidget(self.image_list)
        self.image_list.set_horizontal(reading)
        self.image_list.setMinimumHeight(170 if reading else 260)
        self.image_list.setMaximumHeight(170 if reading else 320)
        self.photo_panel.setVisible(not reading)
        self.reading_nav.setVisible(reading)
        if reading:
            if not self.loading:
                self.reading_date.blockSignals(True)
                self.reading_date.setDate(self.date.date())
                self.reading_date.blockSignals(False)
            self.refresh_reading_nav()

    def reading_rows(self):
        return sorted(self.repository.list(self.search.text(), self.category, tag=self.tag),
                      key=lambda article: (article.diary_date.replace('未知', '00'), article.created_at, article.id))

    def refresh_reading_nav(self):
        rows = self.reading_rows()
        keys = [a.id for a in rows]
        index = keys.index(self.current_id) if self.current_id in keys else -1
        self.previous_article.setEnabled(index > 0)
        self.next_article.setEnabled(0 <= index < len(keys)-1)
        day = self.reading_date.date().toString('yyyy-MM-dd')
        matches = [a for a in rows if matches_day(a.diary_date, day)]
        self.reading_articles.clear()
        for article in matches:
            item = QListWidgetItem(self.item_text(article))
            item.setData(Qt.ItemDataRole.UserRole, article.id)
            self.reading_articles.addItem(item)
            if article.id == self.current_id: self.reading_articles.setCurrentItem(item)
        self.reading_count.setText(f'{day} · {len(matches)} 篇')

    def shift_reading_date(self, offset, months=False):
        date = self.reading_date.date()
        self.reading_date.setDate(date.addMonths(offset) if months else date.addDays(offset))

    def reading_day_changed(self, *_):
        if self.loading: return
        self.refresh_reading_nav()
        if self.reading_articles.count():
            self.open_reading_article(self.reading_articles.item(0).data(Qt.ItemDataRole.UserRole), False)

    def open_reading_article(self, key, sync_date=True):
        if not self.save(True): return
        self.load_article(key)
        if sync_date:
            self.reading_date.blockSignals(True)
            self.reading_date.setDate(self.date.date())
            self.reading_date.blockSignals(False)
        self.refresh_reading_nav()
        self.refresh_list()

    def step_reading_article(self, offset):
        keys = [a.id for a in self.reading_rows()]
        if self.current_id in keys:
            index = keys.index(self.current_id) + offset
            if 0 <= index < len(keys): self.open_reading_article(keys[index])

    def new_article(self):
        chosen_date = self.date.text() if not self.current_id else None
        if not self.save(True):
            return
        try:
            article = self.repository.create()
        except Exception as error:
            self.fail(error)
            return
        self.trash = False
        self.category = None
        self.tag = None
        self.search.blockSignals(True)
        self.search.clear()
        self.search.blockSignals(False)
        self.refresh_categories()
        self.load_article(article.id)
        if chosen_date:
            self.date.setText(chosen_date)
        elif self.browse_date:
            self.date.setDate(QDate.fromString(self.browse_date, 'yyyy-MM-dd'))
        self.refresh_list()
        self.title.setFocus()
        self.title.selectAll()

    def editor_indent(self):
        if not self.current_id or self.editor.isReadOnly():
            return
        self.editor.indent_paragraphs()
        self.editor.setFocus()

    def toggle_bold(self):
        self.editor.setFontWeight(QFont.Weight.Normal if self.editor.fontWeight() >= QFont.Weight.Bold else QFont.Weight.Bold)
        self.editor.setFocus()

    def toggle_italic(self):
        self.editor.setFontItalic(not self.editor.fontItalic())
        self.editor.setFocus()

    def insert_image(self):
        path, _ = QFileDialog.getOpenFileName(self, '插入图片', '', '图片 (*.png *.jpg *.jpeg *.webp *.bmp)')
        if not path:
            return
        try:
            reader = QImageReader(path)
            if not reader.canRead():
                raise ValueError('无法读取这张图片')
            relative = self.attachments.add(self.current_id, Path(path))
            attachment = next(row for row in self.attachments.list(self.current_id) if row['relative_path'] == relative)
            self.editor.insert_image_link(attachment['id'], Path(path).stem)
            self.update_properties()
        except Exception as error:
            self.fail(error)

    def add_attachment(self):
        path, _ = QFileDialog.getOpenFileName(self, '添加附件')
        if path:
            try:
                self.attachments.add(self.current_id, Path(path))
                self.update_properties()
            except Exception as error:
                self.fail(error)

    def selected_image_id(self):
        item = self.image_list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def open_image(self, attachment_id):
        if not self.current_id:
            return
        images = [row for row in self.attachments.list(self.current_id) if row['mime_type'].startswith('image/')]
        index = next((i for i, row in enumerate(images) if row['id'] == attachment_id), None)
        if index is None:
            self.fail('图片入口对应的附件不存在。')
            return
        for i in range(self.image_list.count()):
            item = self.image_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == attachment_id:
                self.image_list.setCurrentItem(item)
        ImageViewer(images, index, self.database.root, self).exec()

    def locate_selected_image(self):
        key = self.selected_image_id()
        if key and not self.editor.locate_image(key):
            self.statusBar().showMessage('这张图片尚未放置正文入口，或入口已移除。', 5000)

    def place_selected_link(self):
        key = self.selected_image_id()
        row = next((row for row in self.attachments.list(self.current_id) if row['id'] == key), None)
        if row:
            self.editor.insert_image_link(key, row['caption'] or Path(row['name']).stem)

    def remove_selected_link(self):
        key = self.selected_image_id()
        if key:
            self.editor.remove_image_links(key)

    def edit_image_caption(self):
        key = self.selected_image_id()
        row = next((row for row in self.attachments.list(self.current_id) if row['id'] == key), None)
        if row is None:
            return
        text, accepted = QInputDialog.getText(self, '图片说明', '说明（显示在图片栏和大图下方）', text=row['caption'])
        if accepted:
            try:
                with self.database.connection:
                    self.database.connection.execute('UPDATE attachments SET caption=? WHERE id=? AND article_id=?',
                                                     (text.strip(), key, self.current_id))
                self.update_properties()
            except Exception as error:
                self.fail(error)

    def delete_or_restore(self):
        if self.current_id:
            self.trash_article(self.current_id)

    def backup(self):
        if not self.save(True):
            return
        path, _ = QFileDialog.getSaveFileName(self, '导出备份（请选择新文件名）', 'NorthDiary.ndiary', 'NorthDiary 备份 (*.ndiary)')
        if path:
            try:
                self.backups.create(Path(path))
                QMessageBox.information(self, '备份已导出', '文章数据库与附件已打包。当前版本尚未提供恢复界面。')
            except Exception as error:
                self.fail(error)

    def export_epub(self):
        if not self.save(True):
            return
        dialog = ExportDialog(self.repository.list(), self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        path, _ = QFileDialog.getSaveFileName(self, '导出 EPUB', 'NorthDiary.epub', 'EPUB 电子书 (*.epub)')
        if not path:
            return
        try:
            EpubExporter(self.repository, self.attachments).export(dialog.selection(), Path(path))
            QMessageBox.information(self, 'EPUB 已导出', '已按所选顺序生成章节、目录和正文图片。')
        except Exception as error:
            self.fail(error)

    def import_epub(self):
        if not self.save(True):
            return
        path, _ = QFileDialog.getOpenFileName(self, '导入 NorthDiary EPUB', '', 'NorthDiary EPUB (*.epub)')
        if not path:
            return
        try:
            importer = EpubImporter(self.repository, self.attachments)
            preview = importer.prepare(Path(path))
            if preview.new_count + preview.conflict_count:
                message = (f'新增 {preview.new_count} 篇，冲突副本 {preview.conflict_count} 篇，'
                           f'跳过已存在内容 {preview.skipped_count} 篇。\n'
                           '现有文章不会被覆盖；正文图片会复制到本机。继续导入？')
                if QMessageBox.question(self, '确认导入', message,
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                        QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
                    return
            result = importer.apply(preview)
            self.refresh_categories()
            self.refresh_people()
            self.refresh_list()
            if result.article_ids and not self.current_id:
                self.load_article(result.article_ids[0])
                self.refresh_list()
            QMessageBox.information(self, '导入完成',
                                    f'已导入 {result.imported} 篇（含冲突副本 {result.conflicts} 篇），'
                                    f'跳过 {result.skipped} 篇。可在“文章总览”中查看。')
        except Exception as error:
            self.fail(error)

    def open_github(self):
        if not self.save(True):
            return
        from northdiary.ui.github_dialog import GitHubDialog
        GitHubDialog(self).exec()

    def refresh_people(self):
        from northdiary.storage.people import PeopleRepository
        people = PeopleRepository(self.database).list()
        keys = {p['id'] for p in people}
        self.person_ids = [key for key in self.person_ids if key in keys]
        self.people_button.setText(f'人物标签 · {len(self.person_ids)}')
        self.people_button.setToolTip('、'.join(p['name'] + '（' + p['code'] + '）' for p in people if p['id'] in self.person_ids) or '选择文章关联的人物')
        while self.shortcut_grid.count():
            item = self.shortcut_grid.takeAt(0)
            if item.widget():
                item.widget().hide()
                item.widget().deleteLater()
        for i, person in enumerate(people):
            button = QPushButton(person['name'] + '\n' + person['code'])
            button.setToolTip(person['name'] + '\n在光标处插入代号：' + person['code'])
            button.setMaximumWidth(155)
            button.setMinimumWidth(90)
            button.clicked.connect(lambda checked=False, code=person['code']: self.insert_person_code(code))
            self.shortcut_grid.addWidget(button, i//2, i%2)
        if not people:
            self.shortcut_grid.addWidget(label('暂无人物，请先在左侧人物档案中新建。'), 0, 0, 1, 2)

    def toggle_people_shortcuts(self, expanded):
        self.people_expand.setArrowType(Qt.ArrowType.LeftArrow if expanded else Qt.ArrowType.RightArrow)
        self.people_shortcuts.setVisible(expanded)
        if expanded:
            self.refresh_people()
            sizes = self.splitter.sizes()
            if sizes[-1] < 100:
                self.splitter.setSizes([max(160, sizes[0]), max(300, sizes[1]-230), max(220, sizes[2]), 230])

    def insert_person_code(self, code):
        if not self.current_id or self.editor.isReadOnly(): return
        self.editor.insertPlainText(code)
        self.editor.setFocus()

    def open_people(self):
        if not self.save(True): return
        from northdiary.ui.people_dialog import PeopleDialog
        dialog = PeopleDialog(self.database, self, attachments=self.attachments)
        dialog.exec()
        dialog.deleteLater()
        self.refresh_people()

    def pick_people(self):
        if not self.current_id or self.editor.isReadOnly() or not self.save(True): return
        from northdiary.ui.people_dialog import PeopleDialog
        dialog = PeopleDialog(self.database, self, selected=self.person_ids, attachments=self.attachments)
        if dialog.exec() == dialog.DialogCode.Accepted:
            self.person_ids = list(dialog.selected)
            self.mark_dirty()
            self.refresh_people()
            self.save(True)
        else:
            self.refresh_people()
        dialog.deleteLater()

    def remember_header_state(self, collapsed):
        self.ui_settings.setValue('header_collapsed', collapsed)
        self.ui_settings.sync()

    def open_timeline_overview(self):
        if not self.save(True):
            return
        from northdiary.ui.timeline_overview import TimelineOverview
        dialog = TimelineOverview(self.repository, self.attachments, self)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dialog.exec()

    def open_random_memory(self):
        if not self.save(True):
            return
        from northdiary.ui.memory_dialog import MemoryDialog
        dialog = MemoryDialog(self.repository, self.attachments, self)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dialog.exec()

    def closeEvent(self, event):
        if self.save(True):
            self.timeline_preview_timer.stop()
            self.pending_timeline_date = None
            event.accept()
        else:
            event.ignore()



