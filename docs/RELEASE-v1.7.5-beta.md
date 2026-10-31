# NorthDiary v1.7.5-beta

发布日期：2026-11-01。本次为源码预发布版本，不提供新版 EXE 或安装包。稳定安装版仍为 v1.7.0。

## 更新总结（相较 v1.7.0）

- 新增「时间线之外」空间，单独整理不属于具体时间节点的文章，并支持切换、筛选与导入导出。
- 新建文章进入「待确认」区域，支持继续编辑、勾选确认及拖入文章列表确认；待确认内容在重启后保留，默认不加入导出列表。
- 文章侧栏默认按事件日期排序，增加日期正序／倒序切换，并将时间线内容与非时间线内容分区呈现。
- 分类和标签支持多选筛选、交集／并集，以及定义的新建、改名与删除。
- 数据文件夹增加切换位置与复制数据功能；复制时使用数据库快照并检查数据完整性。
- 编辑工具栏新增「居中」按钮，可居中当前段落或选中多段，再次点击恢复左对齐；居中时清除首行缩进。
- 优化日期选择器、文章右键菜单、已选人物排序、附件区域和编辑器末尾显示。
- NorthDiary 专用 EPUB 格式升级至 v4，保存「时间线之外」状态，并继续接受旧版 v1–v3 格式。

## 使用与兼容性

本次只发布源码，可下载 GitHub 提供的 Source code ZIP，安装 requirements.txt 中的依赖后运行 main.py；Windows 可使用 start.cmd。
数据库结构升级至 schema v7，包含时间线之外及待确认记录表。升级前自动保存快照；升级后的同一数据库不能用旧程序直接打开，请在更新前额外导出备份。
不包含个人日记、照片、数据库、附件、备份或登录凭据。保留原项目许可证和第三方声明。

## 验证与已知问题

完整项目检查：

```text
Ran 189 tests in 1022.462s

FAILED (failures=3, skipped=2)
test_connect_and_repo_ready_network_work_is_off_ui_thread (test_github_ui.GitHubWindowTests.test_connect_and_repo_ready_network_work_is_off_ui_thread)
test_zip_traversal_duplicate_entries_and_limits (test_importing.ImportTests.test_zip_traversal_duplicate_entries_and_limits)
test_header_rapid_reverse_and_theme_change_while_collapsed (test_memory_ui.MemoryUITests.test_header_rapid_reverse_and_theme_change_while_collapsed)
```

版本号及详情页单独复检：4 项通过。源码编译及待上传文件检查通过。已知失败包括 GitHub 连接界面测试和 EPUB 反斜线路径拒绝测试；完整失败信息以检查结果为准，本次并非全绿发布。
