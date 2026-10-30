# NorthDiary

Windows 本地图文日记与个人文集软件。Python / PySide6 / SQLite 原生桌面窗口，支持离线写作。

当前版本 **1.5.2**，数据库 **schema v5**，NorthDiary EPUB 原生清单 **v3**。`main` 保存最新完整源码；旧版本可通过 Git 提交记录查阅。

## 启动

安装 Python 3.11–3.13，解压后双击 `start.cmd`。首次联网建立 `.venv` 并安装依赖。PyCharm 可选择 `.venv\Scripts\python.exe` 运行 `main.py`。

个人数据通常位于 `%LOCALAPPDATA%\NorthDiary\NorthDiary`，实际路径见窗口底部。更新请沿用原数据目录，不要删除数据库和附件。自定义目录：

```powershell
.\.venv\Scripts\python.exe main.py --data-dir D:\NorthDiaryData
```

## 主要功能

- 三栏图文写作、约 0.9 秒自动保存、分类、普通/临时文章标签、搜索、置顶、排序与最近打开。保存失败保留编辑并阻止切换；强制结束仍可能丢失未保存修改。
- 文章总览支持右键删除，移入回收站后可恢复。
- 模糊日期、季节背景、八套配色、照片板、只读阅读、时间线总览与随机回忆。
- 主界面时间轴约 90 ms 合并拖动预览，松手立即切换，避免先清空再加载。
- 时间线总览右半区纵向滚动；左半事件区仅在超宽时小幅横移，完整显示后归零。
- 人物档案、置顶、星标、稳定编号关联、人物标签与代号插入。插入代号不自动打标签。
- 人物关系支持普通/临时标签，普通可复用、临时仅当前人物；卡片、详情与编辑器均显示，适配深色主题。
- EPUB 文章选择、章节排序、目录、正文引用图片与关联人物资料。仅导入 NorthDiary 专用 EPUB，重复跳过、冲突保留副本。
- 私有 GitHub 数据仓库手动上传/下载 EPUB 文章包，每包最多 20 MiB。不是自动双向同步，没有删除传播。
- `.ndiary` 完整备份导出；自助恢复界面尚未完成。

## 展示模式

先运行 `start.cmd` 完成依赖安装并关闭，再双击 `start-demo.cmd`。首次生成到源码目录 `demo-data/`，之后继续使用，不读取个人日记。包含 32 篇虚构文章、12 位人物、20 个文章标签、8 个关系标签、6 个分类和 16 个附件；配图使用软件自带季节素材。展示中的修改会保存，不自动重置。

也可使用新的空目录：

```powershell
.\.venv\Scripts\python.exe scripts\generate_demo.py D:\NorthDiaryDemo
.\.venv\Scripts\python.exe main.py --data-dir D:\NorthDiaryDemo
```

生成器拒绝覆盖非空目录。仓库不包含个人/展示数据库、用户附件、凭据或虚拟环境。

## 升级与交换

现有 v4 数据库首次升至 v5 前自动保存 `backups/before-v5-*.sqlite3`。旧程序不能打开升级后的数据库；回退需使用升级前快照的副本目录和对应附件。

EPUB 清单 v3 携带关联人物的普通/临时关系，兼容旧 v1/v2；旧程序不能读取新包。未在正文引用的独立附件不在 EPUB/GitHub 交换范围内。分享前检查包内人物出生、相遇和关系资料。

## 验证与限制

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

测试使用临时目录和 Qt offscreen，不修改真实日记，不等同于 Windows 实际显示验收。已知测试问题：Windows GitHub 模拟凭据存储缺少 `save()`；EPUB 反斜杠路径拒绝检查未通过。不能宣称全量测试通过。

真实账号授权、Windows 加密登录存储、实际阅读器和完整备份恢复仍待验收。PDF、完整排版、自动备份与自动同步尚未完成。

更多说明：[关系标签](docs/RELATIONSHIPS.md)、[GitHub](docs/GITHUB_TRANSFER.md)、[发布日志](docs/RELEASE_1_5_2.md)、[第三方说明](docs/OPEN_SOURCE.md)。
