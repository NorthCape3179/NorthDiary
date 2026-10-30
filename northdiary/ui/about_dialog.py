"""Native, themed and selectable product information. No journal content is read."""
from html import escape

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QPen, QFont, QColor, QPalette
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QToolButton,
    QTextBrowser, QWidget,
)

from northdiary import __version__
from northdiary.ui.theme import apply_theme, theme_name, theme_mapping


class AboutButton(QToolButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(34, 34)
        self.setObjectName('articleTool')
        self.setAccessibleName('关于 NorthDiary')
        self.setToolTip('软件详情 · v' + __version__)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(self.palette().color(QPalette.ColorRole.ButtonText), 1.6))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QRectF(7, 7, 20, 20))
        font = QFont('Segoe UI', 12)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(QRectF(7, 6, 20, 21), Qt.AlignmentFlag.AlignCenter, 'i')


def about_html(mapping):
    def c(value): return mapping.get(value, value)
    version = escape(__version__)
    return f'''<!DOCTYPE html><html><head><meta charset="utf-8"/>
<style>
body {{font-family:"Microsoft YaHei UI";font-size:14px;color:{c('#273b37')};line-height:145%;}}
h2 {{font-size:21px;font-weight:600;color:{c('#244d42')};margin-top:28px;margin-bottom:12px;}}
h3 {{font-size:16px;font-weight:600;margin-top:16px;margin-bottom:7px;}}
p {{margin-top:7px;margin-bottom:11px;}}
li {{margin-bottom:7px;}}
a {{color:{c('#7d9b89')};text-decoration:none;}}
.muted {{color:{c('#75827a')};font-size:12px;}}
td {{padding:12px;vertical-align:top;}}
</style></head><body>
<a name="about"></a><h2>关于 NorthDiary</h2>
<p>NorthDiary 是一款面向个人的日记与记忆管理软件。</p>
<p>生活中的记忆往往是零散的。某一天发生的事情、一段偶然的对话、一张照片，或是一个曾经出现在生命中的人，都值得被认真保存。</p>
<p>NorthDiary 希望提供一个属于自己的空间，将这些片段收集起来，通过时间线、文章、人物档案等形式，让原本散落的记忆逐渐形成完整的记录。</p>
<p>它不只是一个用来写日记的工具，也是一份可以不断积累、整理和回顾的个人档案。</p>

<a name="ideas"></a><h2>设计理念</h2>
<table width="100%" cellspacing="8"><tr>
<td width="50%" bgcolor="{c('#f0f1eb')}"><h3>关于时间</h3><p>以时间为线索，整理过去发生的事情。无论是明确的日期，还是无法确定具体时间的回忆，都可以在这里找到自己的位置。</p></td>
<td width="50%" bgcolor="{c('#f0f1eb')}"><h3>关于记录</h3><p>文字、图片与附件共同构成记忆。每一篇文章都可以独立存在，也可以成为更大故事的一部分。</p></td>
</tr><tr>
<td bgcolor="{c('#f0f1eb')}"><h3>关于人物</h3><p>人物档案让记忆中的人物拥有独立的位置。记录姓名、代号、关系、相遇经过，以及与他们有关的故事。</p></td>
<td bgcolor="{c('#f0f1eb')}"><h3>关于保存</h3><p>记录不应该只停留在某一个软件里。NorthDiary 希望让积累的内容能够被整理、导出，并以更长久的形式保存下来。</p></td>
</tr></table>

<a name="features"></a><h2>当前版本 <span style="font-size:14px;font-weight:400;">v{version}</span></h2>
<p>当前版本围绕个人档案体系、图文整理与记录体验进行扩展。</p>
<h3>日记与文章管理</h3><ul>
<li>创建、编辑和自动保存文章，支持基础加粗、斜体与段落缩进。</li>
<li>分类、普通标签与临时标签、标题和正文搜索、置顶、排序及最近打开。</li>
<li>文章总览支持分类排列、分类筛选与搜索，双击打开，右键移入回收站；回收站可恢复。</li>
</ul>
<h3>时间与回忆</h3><ul>
<li>完整日期，以及仅记得年份或月份的模糊日期。</li>
<li>主界面时间轴拖动浏览；时间线总览按时间串联往事，同一节点的文章两行排列。</li>
<li>紧凑时间线提供更多可见节点；右半区纵向滚动，左半区仅在事件超宽时小幅横移。</li>
<li>随机回忆、只读阅读、照片板与图片查看；背景随文章季节及深浅主题变化。</li>
</ul>
<h3>人物与关系</h3><ul>
<li>人物档案支持姓名、代号、出生日期、相遇时间和相遇方式，以及搜索、置顶与星标。</li>
<li>普通与临时关系标签用不同颜色区分；普通关系可复用，临时关系仅当前人物使用。</li>
<li>文章可关联多个人物，人物详情显示相关文章；修改姓名或代号不破坏已有编号关联。</li>
<li>人物代号快捷插入正文；插入代号文字不会自动添加人物标签。</li>
</ul><p class="muted">人物当前使用默认剪影头像，暂不支持自定义头像照片。</p>
<h3>图文、导出与数据</h3><ul>
<li>正文图片入口、图注、照片板与附件托管；图片复制到本地后不依赖原文件位置。</li>
<li>EPUB 电子书导出支持文章选择、章节排序、目录与正文引用图片。</li>
<li>NorthDiary 专用 EPUB 导入可恢复文章、分类标签、模糊日期及关联人物和关系；重复跳过，冲突保留副本。</li>
<li>独立私有 GitHub 数据仓库的文章包手动上传、下载与导入预览，每包最多 20 MiB。</li>
<li>本地 SQLite 数据存储、完整 .ndiary 备份导出，以及数据库升级前快照。</li>
</ul>
<h3>界面与展示</h3><ul>
<li>三栏原生桌面窗口、八套配色、深浅模式一键切换，并分别记住上次配色。</li>
<li>右上角功能区支持折叠；随机回忆位于数据文件夹之后，软件详情入口始终位于顶栏最右侧。</li>
<li>独立展示模式提供虚构文章、人物与标签，不与个人数据混用。</li>
</ul>

<a name="changes"></a><h2>更新日志</h2>
<p class="muted">历史版本：<a href="#v15">v1.5</a> · <a href="#v14">v1.4</a> · <a href="#v13">v1.3</a> · <a href="#v12">v1.2</a> · <a href="#v11">v1.1</a> · <a href="#v10">v1.0</a></p>
<h3>v{version} · 本轮功能汇总</h3><ul>
<li>新增分区排版的软件详情页，统一程序及详情页版本显示。</li>
<li>扩展人物档案、人物标签、代号插入与人物关系管理。</li>
<li>优化深色关系标签和弹窗；去掉临时标签文字后缀，以颜色区分。</li>
<li>文章总览增加右键删除、分类排序和分类筛选。</li>
<li>缩小时间线总览节点与卡片，优化横纵滚动规则。</li>
<li>主界面时间轴合并拖动预览，松手立即定位，减少先清空再加载造成的闪烁。</li>
<li>主题区合并为深浅切换按钮和配色选择框；随机回忆移入可折叠顶栏。</li>
<li>完善 EPUB 人物与关系交换，补充独立展示入口和虚构样例。</li>
</ul>
<a name="v15"></a><h3>v1.5 · 人物走进记忆</h3><ul>
<li>新增人物档案：搜索、卡片列表、详情、新增、编辑、删除、置顶与星标。</li>
<li>记录姓名、代号、出生日期、相遇时间和相遇方式，提供默认剪影头像。</li>
<li>文章人物标签支持多选；已选人物两行横向排列，可逐个移除。</li>
<li>新增两列人物代号快捷插入区，在正文光标处插入文字；插入代号不自动建立人物关联。</li>
<li>相关文章按人物编号关联，修改姓名和代号仍保留联系；删除人物保留文章正文。</li>
<li>专用 EPUB 与 GitHub 文章包携带关联人物资料，人物冲突时保留本机档案并导入副本。</li>
<li>数据库从 schema v3 升至 v4，升级前自动保存数据库快照。</li>
</ul>
<a name="v14"></a><h3>v1.4 · 时间线与随机回忆</h3><ul>
<li>新增时间线总览，日期圆点、年份和月份方块串联文章；没有内容的年月不显示。</li>
<li>只有年份或月份的文章归入对应节点，同一节点的事件两行横向排列。</li>
<li>居中节点稍放大并显示半透明背景，左上角年份随当前节点变化；点击文章打开只读回忆。</li>
<li>新增随机回忆，提供带季节背景的正文阅读与毛毡照片板，可换一篇。</li>
<li>右上角功能区支持动画收起、展开和状态记忆，收起后仍可用 Ctrl+S 保存。</li>
</ul>
<a name="v13"></a><h3>v1.3 · GitHub 手动文章包传输</h3><ul>
<li>新增独立私有数据仓库连接，支持浏览器设备授权和专用令牌。</li>
<li>选择文章上传新 EPUB 包，浏览远端记录，下载后预览并确认导入。</li>
<li>每包最多 20 MiB；重复内容跳过，冲突保留副本，不直接覆盖整个本地数据库。</li>
<li>网络请求在后台执行，Windows 可选加密记住登录。</li>
<li>提供手动交换流程，不是自动双向同步，也没有删除传播。</li>
</ul>
<a name="v12"></a><h3>v1.2 · NorthDiary 专用 EPUB 导入</h3><ul>
<li>新版导出包加入专用数据清单，可恢复文章、模糊日期、分类标签、正文引用图片和图注。</li>
<li>导入前预览数量；重复内容跳过，冲突保留副本，不自动覆盖本机文章。</li>
<li>图片复制到本地，删除导入使用的 EPUB 后仍可继续查看。</li>
<li>仅支持 NorthDiary 自己的专用 EPUB；早期 v1.1 文件需由新版重新导出后才能完整还原。</li>
</ul>
<a name="v11"></a><h3>v1.1 · 把记录整理成电子书</h3><ul>
<li>新增 EPUB 电子书导出：选择文章、调整章节顺序、填写书名和作者。</li>
<li>按所选章节顺序生成目录，打包正文引用图片与图注。</li>
<li>导出前保存当前编辑；图片缺失或导出失败时提示错误，保护已有目标文件。</li>
<li>保留完整桌面版已有的主题、季节背景、日期时间轴与照片板。</li>
</ul>
<a name="v10"></a><h3>v1.0 · 第一份完整桌面日记</h3><ul>
<li>建立 Python、PySide6 与 SQLite 原生桌面工作区，数据独立保存到本机。</li>
<li>完成日记创建、编辑、自动保存、正常切换和关闭前保存，以及保存失败时保留内容。</li>
<li>提供分类、普通/临时标签、搜索、置顶、排序、最近打开和文章总览。</li>
<li>支持完整日期与模糊日期、日期选择和主界面时间轴浏览。</li>
<li>提供正文图片入口、图注、图片查看、照片板、附件托管及只读阅读。</li>
<li>加入多套配色、深浅切换、季节背景、回收站与完整备份导出。</li>
</ul>
<p class="muted">以上按已保存的历史版本记录整理。v1.7.0 汇总其后的本机更新；历史功能的首次加入不代表当时已完成全部 Windows、账号授权或阅读器验收。</p>

<a name="future"></a><h2>未来计划</h2>
<p>NorthDiary 仍在持续开发中。</p>
<p>未来计划完善备份恢复、自动备份与升级体验，扩展排版与导出、人物档案及内容整理能力，并持续完善 Windows 安装、分发与升级体验。</p>
<p>我们希望它能够逐渐成为一个真正完整的个人记忆库，而不仅仅是一个日记编辑器。</p>
<p class="muted">以上为开发方向，不代表已经实现或承诺具体发布日期。</p>

<a name="project"></a><h2>项目信息</h2>
<table width="100%" cellspacing="0">
<tr><td>项目名称</td><td><b>NorthDiary</b></td></tr>
<tr><td>当前版本</td><td>v{version}</td></tr>
<tr><td>开发语言</td><td>Python</td></tr>
<tr><td>界面框架</td><td>PySide6 / Qt</td></tr>
<tr><td>数据库</td><td>SQLite</td></tr>
<tr><td>开源许可</td><td><a href="https://www.gnu.org/licenses/agpl-3.0.html">AGPL-3.0-or-later</a></td></tr>
<tr><td>项目仓库</td><td><a href="https://github.com/NorthCape3179/NorthDiary">GitHub / NorthCape3179 / NorthDiary</a></td></tr>
</table>
<h3>当前范围</h3>
<p class="muted">GitHub 传输为手动文章包交换，不是自动双向同步。EPUB 仅支持 NorthDiary 专用格式，不包含未在正文引用的独立附件。自助备份恢复、PDF 与自动备份尚未完成；真实账号、阅读器与 Windows 显示体验仍需持续验收。</p>
<hr style="color:{c('#d4ddd1')};"/>
<p class="muted">使用 PySide6 / Qt（LGPLv3）、EbookLib（AGPLv3）等开源组件。安装目录 _internal/licenses 提供许可证、第三方声明及本版本项目源码和构建说明。</p>
<p style="font-size:17px;font-weight:600;">作者 NorthCape</p>
<p>闲聊 Q 群 <b>539241974</b></p>
<p>辅助 ChatGPT <span style="font-size:11px;color:{c('#75827a')};">（其实是主力）</span></p>
<p class="muted">记录时间，留存记忆。</p>
</body></html>'''


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('关于 NorthDiary · v' + __version__)
        self.resize(780, 760)
        self.setMinimumSize(600, 480)
        name = theme_name(parent) if parent else 'light'
        dark = name in ('dark', 'wine')
        mapping = theme_mapping(dark, name)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 16)
        layout.setSpacing(12)
        hero = QWidget(); hero.setObjectName('aboutHero')
        hero.setStyleSheet('QWidget#aboutHero {background:#e9ede7;border:1px solid #d4ddd1;border-radius:12px;}')
        hero_layout = QVBoxLayout(hero); hero_layout.setContentsMargins(20, 16, 20, 16)
        heading = QHBoxLayout()
        title = QLabel('NorthDiary'); title.setStyleSheet('font-size:34px;font-weight:700;color:#244d42;background:transparent;')
        heading.addWidget(title); heading.addStretch()
        version = QLabel('v' + __version__); version.setStyleSheet('font-size:13px;color:#75827a;background:transparent;')
        heading.addWidget(version); hero_layout.addLayout(heading)
        subtitle = QLabel('A Personal Archive of Memories')
        subtitle.setStyleSheet('font-size:13px;font-style:italic;color:#75827a;background:transparent;')
        hero_layout.addWidget(subtitle)
        tagline = QLabel('记录时间，留存记忆。')
        tagline.setStyleSheet('font-size:18px;color:#273b37;background:transparent;')
        hero_layout.addWidget(tagline);layout.addWidget(hero)
        self.browser = QTextBrowser()
        self.browser.setAccessibleName('NorthDiary 软件详情')
        self.browser.setOpenExternalLinks(True)
        self.browser.setStyleSheet('QTextBrowser {background:#fffefa;border:1px solid #d4ddd1;border-radius:8px;padding:14px;}')
        self.browser.setHtml(about_html(mapping))
        nav = QHBoxLayout(); nav.setSpacing(4)
        for text, anchor in [('关于','about'),('理念','ideas'),('功能','features'),('更新','changes'),('计划','future'),('项目信息','project')]:
            button = QPushButton(text)
            button.setStyleSheet('QPushButton {padding:5px 9px;font-size:12px;}')
            button.clicked.connect(lambda checked=False, target=anchor: self.browser.scrollToAnchor(target))
            nav.addWidget(button)
        nav.addStretch();layout.addLayout(nav)
        layout.addWidget(self.browser, 1)
        footer = QHBoxLayout(); footer.addStretch()
        close = QPushButton('关闭');close.clicked.connect(self.accept);footer.addWidget(close)
        layout.addLayout(footer)
        apply_theme(self, dark, name)
