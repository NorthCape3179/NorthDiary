# 架构与后续边界

## v1.5 人物档案

storage/people.py 管理 people；article_people 为多对多关联，文章 save 在同一事务提交人物标签。姓名/代号修改不改变人物编号，删除人物仅级联解除关联。ui/people_dialog.py 共用档案列表、详情及文章人物选择器，头像由 QPainter 绘制。MainWindow 提供右侧快捷区与正文纯文字插入。

数据库 schema v4，v3 升级前使用 SQLite 在线备份，迁移失败回滚并停止打开。旧版拒绝打开 v4 数据。原生 EPUB 清单 v2 在每篇记录内携带关联人物，校验整本资料一致性，导入同事务写入人物与文章关联；人物冲突生成稳定编号副本，不覆盖本机资料。新导入器与 GitHub 预检兼容 v1/v2，旧导入器拒绝新包。详见 PEOPLE.md。

## v1.4 浏览与收起交互

timeline_overview.py 按实际文章构建年、月、日节点，未知日期记录归入年/月节点，使用虚拟绘制和独立水平偏移支持两行事件条。memory_dialog.py 共用只读随机回忆与指定文章阅读，复用 SeasonPaper/ImageBoard/ImageViewer，不改文章和打开历史。header_tools.py 对四个原控件共同执行宽度/透明度动画，通过 ui.ini 记住收起状态。弹窗打开前仍遵守保存失败阻止离开的规则；schema v3 不变。详见 UI_V14.md。

## v1.3 GitHub 手动包传输

github_sync.py 使用标准库 HTTPS/JSON 实现设备授权与 Contents API；credentials.py 在 Windows 使用 DPAPI，拒绝明文回退；github_dialog.py 以 QThread 执行网络任务、主线程导出/导入和 SQLite 写入。私有仓库须校验数据标识；上传采用不可覆盖的唯一包名，下载固定提交并校验 Git blob SHA，再复用 EpubImporter。不改变数据库结构，不提供自动同步或删除传播。详见 GITHUB_TRANSFER.md。

## v1.2 原生 EPUB 导入

导出在正常 EPUB 内增加版本化 JSON 原生清单；native_format.py 共用记录校验、资源类型与内容指纹规则。importing.py 的 EpubImporter 分离无写入的 prepare 与单事务 apply，按固定导入 UUID 跳过同一内容版本，不覆盖已有文章，图片以新编号和路径复制。正文重新清理，照片入口重建为本地附件引用。保持 schema v3，不做数据库整体替换。完整格式及边界见 IMPORTING.md。

## 数据模型

- Article：UUID、标题、日记日期、正文 HTML、搜索用纯文本、创建/修改时间、软删除时间。
- Category/Tag：独立实体，通过关系表关联文章；Category 预留 parent_id。
- Attachment：复制后的文件、相对路径、媒体类型、说明、排序；原文件始终保留。
- ExportSelection：有序文章 ID 列表、书名、作者，分类与导出编排分离。

正文由 QTextEdit 生成 HTML。`services/epub.py` 的 EpubExporter 实现 Exporter 协议，使用现有 validate_selection 重新读取内容并保持 ExportSelection 的文章 ID 顺序；不改变分类、数据库结构或正文原件。

当前桌面正文的 ndiary-image: 图片入口会转换为书内图片，同时兼容旧的内嵌 img；未知月份和日期原样保留。

EPUB 适配器用 lxml 解析 HTML，再按允许的元素重建 XML 树，不直接打包 Qt HTML。清除 Qt CSS、脚本、事件属性和外部样式，将 Qt 的粗体/斜体/下划线转换为语义元素，添加统一 CSS、章节标题和日期。EbookLib 负责 EPUB 3 容器、元数据、manifest、spine、导航目录和兼容 NCX。`ui/export_dialog.py` 只负责勾选章节、上下移动与书名/作者；不承担排版。

图片引用必须属于该文章的附件记录，路径必须留在数据目录 attachments 内（含解析符号链接后校验）；按实际文件头识别 PNG/JPEG/GIF，重写为书内相对路径，并复用重复引用。仅打包被正文引用的图片；未引用附件不进入 EPUB。远程图片、越界路径、缺失资源、不支持格式和本地附件链接均报错；不联网获取资源。网页链接和有效的章内锚点保留。默认粘贴纯文本，避免正文引入未托管图片。

所有内容和资源处理成功后，在目标文件同目录写临时 EPUB，再用 os.replace 替换，失败清理临时文件并保留原目标。导出前界面要求当前编辑保存成功。自动测试覆盖 Qt 真实 HTML、包结构、XML 解析、manifest/spine/双目录与资源链接、数据不变及失败保护；不能代替 Windows 操作体验、EPUBCheck 和实际阅读器验收。

## 保存与生命周期

界面收集编辑快照，由仓储在事务中更新内容和分类标签；只有提交成功才清除 dirty。自动保存失败保留 dirty；手动保存、切换、关闭时显示原因并阻止内容被替换。附件先复制成功再提交元数据，失败清理新副本。移入回收站不删除正文或资源。

应用通过 QLockFile 阻止同一数据目录同时打开两个窗口。数据库 foreign_keys / WAL / FULL 开启。user_version=4；未来迁移必须先备份，逐版本执行，不得删库重建。新格式数据库由旧程序拒绝打开。

## 后续模块

1. 备份恢复：包结构、版本、路径、大小和资源引用校验；临时目录验证后再切换；恢复前备份现有数据。
2. 编辑器：列表、引用、标题层级、图片说明；先确定正文规范，再做统一预览与导出样式。
3. EPUB：最小导出已实现；后续做 EPUBCheck 与实际阅读器验收，再按需求扩展正文规范。PDF 尚未实现。
4. 分类/标签：树形导航和管理页；删除分类只删关联；增加标签筛选。
5. 发布：Windows 打包、安装、升级保留数据；按依赖许可保留相应声明。

## 当前限制

备份写入为单线程；大附件会短暂阻塞界面，后续转后台任务。暂无自动备份策略和历史版本。附件被正文移除后仍保留在托管目录，暂不自动清理，避免误删。搜索是小规模全文 substring 搜索，规模增长后迁移到 FTS。筛选不隐藏正在编辑的文章，避免编辑时页面跳走。

