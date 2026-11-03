"""Native AI studio UI. Networking and conversation lifecycle live in its controller."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QPushButton, QScrollArea, QStackedWidget, QTextEdit, QVBoxLayout,
    QWidget, QCheckBox, QSpinBox,
)

from northdiary.ui.ai_sources import ArticleSelectionDialog, ArticleSources, RequestPreviewDialog
from northdiary.ui.ai_studio_widgets import ModeCard, Stationery
from northdiary.ui.controls import ComboBox
from northdiary.services.deepseek import DEFAULT_MODELS, DeepSeekClient
from northdiary.services.ai_tasks import STORY_FIELDS, STORY_STEPS, decode_story, encode_story, instruction_field
from northdiary.ui.chat_transcript import ChatTranscript


MODES = {
    'appreciation': ('文字赏析', '从文字里，读见更多',
                     '文学点评、情感点评、读者视角、逐段批注',
                     ('文学点评', '情感点评', '读者视角', '逐段批注')),
    'analysis': ('深度分析', '把散落的记录，连成线索',
                 '人物分析、事件整理、跨时间分析、文章关联',
                 ('人物分析', '事件整理', '跨时间分析', '文章关联')),
    'writing': ('故事创作', '让记录，生长出新的故事',
                '小说、轻小说、散文、多视角、长篇整合',
                ('小说', '轻小说', '散文', '多视角', '长篇整合')),
    'chat': ('自由对话', '围绕这些文字，聊一聊',
             '与已选择的文章展开一场对话', ('文章讨论',)),
}

STUDIO_STYLE = '''
QWidget#studioSidebar, QWidget#studioSources { background: #e9ede7; border-radius: 12px; }
QWidget#studioCanvas { background: #fffefa; border: 1px solid #e3e5dd; border-radius: 12px; }
QPushButton#studioNav { text-align: left; padding: 12px 15px; background: transparent; border: none; }
QPushButton#studioNav:hover { background: #e0e8db; }
QPushButton#studioNav:checked { background: #d3e2d2; color: #244d42; font-weight: 600; }
QPushButton#studioCard { background: #fffefa; border: 1px solid #dce2d8; border-radius: 12px; text-align: left; }
QPushButton#studioCard:hover { background: #f0f1eb; border-color: #7d9b89; }
QLabel#studioHeading { font-size: 27px; font-weight: 600; color: #244d42; }
QLabel#studioToolHeading { font-size: 23px; font-weight: 600; color: #244d42; }
QLabel#studioEyebrow { font-size: 11px; color: #75827a; letter-spacing: 2px; }
QFrame#studioRule { background: #e3e5dd; border: none; max-height: 1px; }
QTextEdit#studioPrompt { border: 1px solid #dce2d8; border-radius: 8px; padding: 10px; font-size: 14px; }
QTextEdit#studioResult { border: 1px solid #e3e5dd; border-radius: 8px; padding: 16px; font-size: 15px; }
QScrollArea { background: transparent; border: none; }
QScrollBar:vertical { background: transparent; width: 8px; margin: 0; }
QScrollBar::handle:vertical { background: #c5d2c5; min-height: 28px; border-radius: 4px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QScrollBar:horizontal { background: transparent; height: 8px; margin: 0; }
QScrollBar::handle:horizontal { background: #c5d2c5; min-width: 28px; border-radius: 4px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }
'''


def text(value, name=None):
    label = QLabel(value)
    label.setWordWrap(True)
    if name:
        label.setObjectName(name)
    return label


def button(title, callback=None, primary=False):
    widget = QPushButton(title)
    if primary:
        widget.setObjectName('primary')
    if callback:
        widget.clicked.connect(callback)
    return widget


def unavailable(widget, explanation='第二阶段接入 DeepSeek 后启用'):
    widget.setEnabled(False)
    widget.setToolTip(explanation)
    return widget


def combo(options):
    widget = ComboBox()
    widget.addItems(options)
    return widget


def scroll_page():
    body = QWidget()
    layout = QVBoxLayout(body)
    layout.setContentsMargins(30, 26, 30, 26)
    layout.setSpacing(16)
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setWidget(body)
    return scroll, layout


class AIStudio(QWidget):
    articleRequested = Signal(str)

    def __init__(self, database, parent=None, *, credential_store=None, client_factory=DeepSeekClient):
        super().__init__(parent)
        self.database = database
        self.sources = ArticleSources(database)
        self.article_ids = ()
        self.selected_articles = []
        self.current_page = 'home'
        self.setStyleSheet(STUDIO_STYLE)
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(12)
        sidebar = QWidget()
        sidebar.setObjectName('studioSidebar')
        sidebar.setFixedWidth(178)
        nav = QVBoxLayout(sidebar)
        nav.setContentsMargins(12, 24, 12, 16)
        nav.setSpacing(6)
        brand = text('AI 工作室', 'section')
        nav.addWidget(brand)
        nav.addWidget(text('NORTHDIARY', 'studioEyebrow'))
        nav.addSpacing(20)
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_buttons = {}
        for key, title in [('home', '工作室主页')] + [(k, v[0]) for k, v in MODES.items()]:
            self.add_navigation(nav, key, title)
        nav.addStretch()
        self.add_navigation(nav, 'library', 'AI 作品库')
        self.add_navigation(nav, 'settings', 'API 设置')
        nav.addSpacing(14)
        nav.addWidget(text('DeepSeek API', 'muted'))
        outer.addWidget(sidebar)
        canvas = QWidget()
        canvas.setObjectName('studioCanvas')
        canvas_layout = QVBoxLayout(canvas)
        canvas_layout.setContentsMargins(0, 0, 0, 0)
        self.pages = QStackedWidget()
        canvas_layout.addWidget(self.pages)
        outer.addWidget(canvas, 1)
        self.page_widgets = {}
        self.page_widgets['home'] = self.build_home()
        self.tools = {}
        for key, spec in MODES.items():
            self.page_widgets[key] = self.build_tool(key, spec)
        self.page_widgets['library'] = self.build_library()
        self.page_widgets['settings'] = self.build_settings()
        for page in self.page_widgets.values():
            self.pages.addWidget(page)
        self.source_panel = self.build_sources()
        outer.addWidget(self.source_panel)
        from northdiary.ui.ai_controller import StudioController
        self.runtime = StudioController(self, credential_store, client_factory)
        self.navigate('home')

    def add_navigation(self, layout, key, title):
        item = button(title, lambda checked=False, page=key: self.navigate(page))
        item.setObjectName('studioNav')
        item.setCheckable(True)
        self.nav_group.addButton(item)
        self.nav_buttons[key] = item
        layout.addWidget(item)

    def build_home(self):
        page, layout = scroll_page()
        layout.addWidget(text('YOUR WRITING SPACE', 'studioEyebrow'))
        layout.addWidget(text('与文字，慢慢对话', 'studioHeading'))
        layout.addWidget(text('从一篇记录出发，读懂情绪，梳理过往，或写一个新的故事。', 'muted'))
        grid = QGridLayout()
        grid.setSpacing(14)
        for index, (key, spec) in enumerate(MODES.items()):
            card = ModeCard(key, spec[0], spec[2])
            card.clicked.connect(lambda checked=False, mode=key: self.navigate(mode))
            grid.addWidget(card, index // 2, index % 2)
        layout.addLayout(grid)
        layout.addSpacing(4)
        row = QHBoxLayout()
        row.addWidget(text('从你选择的文章开始', 'section'), 1)
        row.addWidget(button('选择文章', self.choose_articles, True))
        layout.addLayout(row)
        layout.addWidget(text('由你决定本次使用哪些文字。原始日记与 AI 作品独立保存。', 'muted'))
        layout.addStretch()
        return page

    def build_tool(self, key, spec):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 18, 24, 18)
        layout.setSpacing(8)
        eyebrow = text('工作室 / ' + spec[0], 'studioEyebrow')
        layout.addWidget(eyebrow)
        layout.addWidget(text(spec[1], 'studioToolHeading'))
        notice = ('虚构创作会与真实记录明确区分。' if key == 'writing' else
                  '分析将区分原文事实、推测与未知信息。' if key == 'analysis' else
                  '围绕右侧已选文章交流。' if key == 'chat' else '用不同的目光，重新阅读你的文字。')
        layout.addWidget(text(notice, 'muted'))
        conversations = QHBoxLayout()
        conversation = ComboBox()
        conversation.setMinimumWidth(160)
        conversation.setAccessibleName(spec[0] + '对话历史')
        conversation.currentIndexChanged.connect(lambda _, mode=key: self.runtime.load_conversation(mode))
        conversations.addWidget(conversation, 1)
        new = button('新对话', lambda checked=False, mode=key: self.runtime.new_conversation(mode))
        delete = button('删除对话', lambda checked=False, mode=key: self.runtime.delete_conversation(mode))
        conversations.addWidget(new)
        conversations.addWidget(delete)
        layout.addLayout(conversations)
        parameters = QWidget()
        options = QHBoxLayout(parameters)
        options.setContentsMargins(0, 0, 0, 0)
        kind = combo(spec[3])
        tone = combo(('自然温和', '细腻抒情', '克制客观', '轻松日常'))
        perspective = combo(('原文视角', '第一人称', '第三人称', '多视角'))
        length = combo(('适中篇幅', '简短', '详细'))
        for label, widget in [('类型', kind), ('语气', tone), ('视角', perspective), ('篇幅', length)]:
            column = QVBoxLayout()
            column.setSpacing(5)
            column.addWidget(text(label, 'muted'))
            widget.setMinimumWidth(90)
            column.addWidget(widget)
            options.addLayout(column, 1)
        layout.addWidget(parameters)
        extras = {}
        if key == 'analysis':
            focus_row = QHBoxLayout()
            focus_row.addWidget(text('分析对象', 'muted'))
            focus = QLineEdit()
            focus.setPlaceholderText('可填写人物、事件或关注的问题；留空分析全部所选材料')
            focus_row.addWidget(focus, 1)
            layout.addLayout(focus_row)
            extras['focus'] = focus
        elif key == 'writing':
            story_row = QHBoxLayout()
            step = combo(STORY_STEPS)
            step.setAccessibleName('故事创作步骤')
            story_row.addWidget(step, 1)
            story_row.addWidget(text('第', 'muted'))
            chapter = QSpinBox()
            chapter.setRange(1, 999)
            chapter.setValue(1)
            chapter.setAccessibleName('当前章节序号')
            story_row.addWidget(chapter)
            story_row.addWidget(text('章', 'muted'))
            story_settings = button('故事设定', self.edit_story_settings)
            story_row.addWidget(story_settings)
            layout.addLayout(story_row)
            extras.update(step=step, chapter=chapter, story_settings=story_settings,
                          story_notes={field: '' for field in STORY_FIELDS})
        output = ChatTranscript()
        layout.addWidget(output, 1)
        actions = QHBoxLayout()
        actions.addWidget(text('对话记录' if key == 'chat' else '生成结果', 'muted'), 1)
        parameter_toggle = button('创作设置')
        parameter_toggle.setCheckable(True)
        parameter_toggle.setChecked(True)
        parameter_toggle.toggled.connect(parameters.setVisible)
        actions.addWidget(parameter_toggle)
        copy = button('复制', lambda checked=False, mode=key: self.runtime.copy_response(mode))
        actions.addWidget(copy)
        edit_work = button('编辑', lambda checked=False, mode=key: self.runtime.save_work(mode, True))
        edit_work.setToolTip('编辑最近有内容的回复并保存为作品，不修改对话历史')
        save_work = button('保存作品', lambda checked=False, mode=key: self.runtime.save_work(mode))
        save_work.setToolTip('将最近有内容的回复保存到独立作品库')
        actions.addWidget(edit_work)
        actions.addWidget(save_work)
        layout.addLayout(actions)
        status = text('每次发送前可核对文章和历史；同一对话延续上下文。', 'muted')
        layout.addWidget(status)
        prompt = QTextEdit()
        prompt.setObjectName('studioPrompt')
        prompt.setAcceptRichText(False)
        prompt.setFixedHeight(66)
        prompt.setPlaceholderText('想聊些什么？可以引用已选文章中的一段话…' if key == 'chat' else
                                  '补充你的要求，例如：重点关注情绪变化，保留原文中的细节…')
        layout.addWidget(prompt)
        footer = QHBoxLayout()
        footer.addWidget(button('查看本次范围', self.preview_request))
        footer.addStretch()
        regenerate = button('重新生成', lambda checked=False, mode=key: self.runtime.send(mode, True))
        stop = button('停止', lambda: self.runtime.client.stop())
        send = button('发送' if key == 'chat' else '生成', lambda checked=False, mode=key: self.runtime.send(mode), True)
        footer.addWidget(regenerate)
        footer.addWidget(stop)
        footer.addWidget(send)
        layout.addLayout(footer)
        self.tools[key] = {'kind': kind, 'tone': tone, 'perspective': perspective,
                           'length': length, 'prompt': prompt, 'output': output,
                           'conversation': conversation, 'new': new, 'delete': delete,
                           'parameters': parameters, 'parameter_toggle': parameter_toggle, 'eyebrow': eyebrow,
                           'copy': copy, 'edit_work': edit_work, 'save_work': save_work,
                           'status': status, 'regenerate': regenerate, 'stop': stop, 'send': send}
        self.tools[key].update(extras)
        return page

    def edit_story_settings(self):
        if self.runtime.client.busy or self.runtime.pending_result:
            return
        from northdiary.ui.story_settings import StorySettingsDialog
        suggestion = None
        turns = self.runtime.repo.turns(self.runtime.active['writing'])
        for turn in reversed(turns):
            if turn['status'] == 'complete' and turn['response']:
                state = decode_story(turn['instruction'])
                target = {'故事大纲': 'outline', '人物设定': 'characters', '连续性整理': 'continuity'}.get(state['step'] if state else '')
                if target:
                    suggestion = (target, turn['response'])
                break
        dialog = StorySettingsDialog(self.tools['writing']['story_notes'], self, suggestion)
        try:
            if dialog.exec() == dialog.DialogCode.Accepted:
                self.tools['writing']['story_notes'] = dialog.notes
                self.tools['writing']['status'].setText('故事设定已应用，将在下次发送时一并展示并保存。')
        finally:
            dialog.deleteLater()

    def reset_task_settings(self, mode):
        if mode == 'writing':
            self.tools[mode]['story_notes'] = {field: '' for field in STORY_FIELDS}
            self.tools[mode]['step'].setCurrentIndex(0)
            self.tools[mode]['chapter'].setValue(1)
        elif mode == 'analysis':
            self.tools[mode]['focus'].clear()

    def restore_task_settings(self, mode, instruction, completed=False):
        if mode == 'analysis':
            self.tools[mode]['focus'].setText(instruction_field(instruction, '分析对象'))
        elif mode == 'writing':
            state = decode_story(instruction)
            self.reset_task_settings(mode)
            if state:
                tool = self.tools[mode]
                tool['story_notes'] = {field: state[field] for field in STORY_FIELDS}
                tool['step'].setCurrentText(state['step'])
                next_chapter = state['chapter'] + (1 if completed and state['step'] in ('生成章节', '续写下一章') else 0)
                tool['chapter'].setValue(min(999, next_chapter))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not hasattr(self, 'tools'):
            return
        compact = self.height() < 690
        if getattr(self, '_compact', None) != compact:
            self._compact = compact
            for tool in self.tools.values():
                tool['eyebrow'].setVisible(not compact)
                tool['parameter_toggle'].setChecked(not compact)
                tool['parameters'].setVisible(not compact)

    def build_sources(self):
        panel = QWidget()
        panel.setObjectName('studioSources')
        panel.setFixedWidth(244)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 24, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(text('本次文章', 'section'))
        self.source_count = text('尚未选择文章', 'muted')
        layout.addWidget(self.source_count)
        self.source_list = QListWidget()
        self.source_list.setWordWrap(True)
        self.source_list.setAccessibleName('本次已选文章')
        self.source_list.currentRowChanged.connect(self.update_source_actions)
        self.source_list.itemDoubleClicked.connect(lambda item: self.open_source())
        layout.addWidget(self.source_list, 1)
        self.source_empty = text('选择一篇或多篇文章，\n作为本次交流与创作的起点。', 'muted')
        layout.addWidget(self.source_empty)
        self.open_source_button = button('打开原文', self.open_source)
        self.remove_source_button = button('移出本次范围', self.remove_source)
        layout.addWidget(self.open_source_button)
        layout.addWidget(self.remove_source_button)
        self.choose_source_button = button('选择文章', self.choose_articles, True)
        layout.addWidget(self.choose_source_button)
        self.preview_button = button('查看本次范围', self.preview_request)
        layout.addWidget(self.preview_button)
        rule = QFrame()
        rule.setObjectName('studioRule')
        rule.setFixedHeight(1)
        layout.addWidget(rule)
        layout.addWidget(text('仅使用你主动选择的文章', 'muted'))
        layout.addWidget(text('人物资料、附件不默认加入', 'muted'))
        self.update_source_actions()
        return panel

    def build_library(self):
        from northdiary.ui.ai_library import AIWorkLibrary
        self.library = AIWorkLibrary(self.database, self)
        self.library.articleRequested.connect(self.articleRequested.emit)
        self.library_search = self.library.search
        self.library_category = self.library.category_filter
        return self.library

    def update_library_empty(self):
        self.library.refresh()

    def build_settings(self):
        page, layout = scroll_page()
        layout.addWidget(text('CONNECTION', 'studioEyebrow'))
        layout.addWidget(text('API 设置', 'studioHeading'))
        layout.addWidget(text('DeepSeek', 'section'))
        layout.addWidget(text('填写开放平台 API Key 即可使用。测试连接不会发送日记内容。', 'muted'))
        layout.addSpacing(8)
        layout.addWidget(text('API Key', 'section'))
        key_row = QHBoxLayout()
        self.api_key = QLineEdit()
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key.setPlaceholderText('粘贴 API Key，应用后清空输入框')
        key_row.addWidget(self.api_key, 1)
        self.apply_key_button = button('应用密钥', lambda: self.runtime.apply_key())
        self.clear_key_button = button('清除密钥', lambda: self.runtime.clear_key())
        key_row.addWidget(self.apply_key_button)
        key_row.addWidget(self.clear_key_button)
        layout.addLayout(key_row)
        self.remember_key = QCheckBox('在本机安全记住密钥（Windows 当前用户加密）')
        self.remember_key.setChecked(True)
        layout.addWidget(self.remember_key)
        layout.addWidget(text('Windows 和 Android 分别保存密钥，不通过 GitHub 同步。', 'muted'))
        layout.addWidget(text('模型', 'section'))
        self.model = ComboBox()
        for name in DEFAULT_MODELS:
            self.model.addItem(name, name)
        layout.addWidget(self.model)
        options = QHBoxLayout()
        self.thinking = QCheckBox('深度思考')
        options.addWidget(self.thinking)
        options.addStretch()
        options.addWidget(text('最大输出 Token', 'muted'))
        self.max_tokens = QSpinBox()
        self.max_tokens.setRange(256, 65536)
        self.max_tokens.setSingleStep(1024)
        self.max_tokens.setValue(8192)
        self.max_tokens.setToolTip('限制本次回复及思考的输出预算，不是原文输入上限。默认8192，可调至65536；详细分析可选16384或32768。')
        options.addWidget(self.max_tokens)
        layout.addLayout(options)
        connection = QHBoxLayout()
        self.test_button = button('测试连接 / 刷新模型', lambda: self.runtime.test_connection())
        connection.addWidget(self.test_button)
        self.connection_status = text('尚未建立连接', 'muted')
        connection.addWidget(self.connection_status, 1)
        layout.addLayout(connection)
        layout.addSpacing(12)
        layout.addWidget(text('用量与费用', 'section'))
        self.usage_label = text('Token 用量：—     预估费用：—', 'muted')
        layout.addWidget(self.usage_label)
        layout.addWidget(text('按接口回报的 Token 记录用量。费用区间参考 2026-11-02 官方峰谷价格（美元），实际以账单为准。', 'muted'))
        layout.addStretch()
        layout.addWidget(text('文章授权', 'section'))
        layout.addWidget(text('仅主动选择文章；每次请求可查看使用范围。', 'muted'))
        layout.addWidget(text('同一对话可继续；新对话独立。历史保存在本地，不与 DeepSeek 网页聊天同步。', 'muted'))
        return page

    def navigate(self, key):
        if key not in self.page_widgets:
            return
        if self.current_page == 'library' and key != 'library' and not self.library.can_leave():
            self.nav_buttons['library'].setChecked(True)
            return
        self.current_page = key
        self.pages.setCurrentWidget(self.page_widgets[key])
        self.nav_buttons[key].setChecked(True)
        self.source_panel.setVisible(key not in ('settings', 'library'))
        if hasattr(self, 'runtime'):
            self.runtime.page_changed(key)
        if key == 'library':
            self.library.refresh()

    def choose_articles(self):
        if self.runtime.client.busy or self.runtime.pending_result:
            return
        dialog = ArticleSelectionDialog(self.database, self.article_ids, self)
        try:
            if dialog.exec() == dialog.DialogCode.Accepted:
                # The selector contains metadata only; don't fetch bodies here.
                self.set_articles(dialog.article_ids)
        finally:
            dialog.deleteLater()

    def set_articles(self, ids):
        previous = self.article_ids
        self.article_ids = tuple(dict.fromkeys(ids))
        # Query metadata only for selected IDs, keeping selection order.
        self.selected_articles = []
        for key in self.article_ids:
            row = self.database.connection.execute('''SELECT a.id,a.title,a.diary_date,
                EXISTS (SELECT 1 FROM outside_articles o WHERE o.article_id=a.id) AS outside
                FROM articles a WHERE a.id=? AND a.deleted_at IS NULL
                AND NOT EXISTS (SELECT 1 FROM draft_articles d WHERE d.article_id=a.id)''', (key,)).fetchone()
            if row:
                from northdiary.ui.ai_sources import SourceArticle
                self.selected_articles.append(SourceArticle(row['id'], row['title'], row['diary_date'], bool(row['outside'])))
        self.article_ids = tuple(a.id for a in self.selected_articles)
        self.source_list.clear()
        for article in self.selected_articles:
            self.source_list.addItem(article.title + '\n' + article.description)
        if self.selected_articles:
            self.source_list.setCurrentRow(0)
        self.source_count.setText(f'已选 {len(self.article_ids)} 篇文章' if self.article_ids else '尚未选择文章')
        self.source_empty.setVisible(not self.article_ids)
        self.update_source_actions()
        if previous != self.article_ids and hasattr(self, 'runtime'):
            self.runtime.scope_changed()

    def update_source_actions(self):
        selected = self.source_list.currentRow() >= 0
        self.open_source_button.setEnabled(selected)
        self.remove_source_button.setEnabled(selected)

    def open_source(self):
        index = self.source_list.currentRow()
        if 0 <= index < len(self.article_ids):
            self.articleRequested.emit(self.article_ids[index])

    def remove_source(self):
        index = self.source_list.currentRow()
        if 0 <= index < len(self.article_ids):
            self.set_articles(key for i, key in enumerate(self.article_ids) if i != index)

    def request_instruction(self, mode=None):
        mode = mode or self.current_page
        if mode not in self.tools:
            return '尚未选择功能。请进入文字赏析、深度分析、故事创作或自由对话补充指令。'
        tool = self.tools[mode]
        lines = [f'功能：{MODES[mode][0]}']
        lines.extend(f'{label}：{tool[key].currentText()}' for label, key in
                     [('类型', 'kind'), ('语气', 'tone'), ('视角', 'perspective'), ('篇幅', 'length')])
        if mode == 'analysis':
            lines.append('内容规范：区分事实、推测和未知信息。')
            lines.append('分析对象：' + tool['focus'].text().strip())
        elif mode == 'writing':
            lines.append('内容规范：允许虚构，但必须与真实记录明确区分。')
            lines.append('步骤：' + tool['step'].currentText())
            lines.append(f"当前章节：第{tool['chapter'].value()}章")
            lines.append(encode_story(tool['story_notes'], tool['step'].currentText(), tool['chapter'].value()))
        lines.append('\n自定义指令：\n' + (tool['prompt'].toPlainText().strip() or '未填写'))
        return '\n'.join(lines)

    def preview_request(self):
        self.runtime.preview()
