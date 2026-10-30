# v1.1 EPUB 验证记录

日期：2026-10-30。Linux / Python 3.12 / PySide6 6.9.2 / QT_QPA_PLATFORM=offscreen。

- 开发基线为昨晚完整桌面版 ec7fd83，而非 main 上的初始框架。
- 14 项 EPUB 专项测试全部通过：包结构、元数据、XML、双目录、章节顺序、Qt 样式清理、图片入口、旧式内嵌图片、模糊日期、跨文章资源拒绝、临时文件清理和导出前保存。
- 原有 48 项测试中，46 项通过；2 项涉及背景图片的测试在当前本地环境失败，原因是连接器未提供 PNG 二进制文件内容，本地缺少原图。未用伪造图片替代。
- 完整 62 项测试通过测试启动脚本显式跳过上述两项后，结果为 60 项通过、2 项跳过。未修改这两项原始测试；资源可用的完整 checkout 仍应运行正常的全量验证命令。
- 远端整合树以 v1.0 原始树为基础，九张背景图按原始 blob SHA 保留，不上传空文件或替代图片。
- compileall 语法检查通过。尚未完成 Windows 实机、EPUBCheck 和实际阅读器验收。

正常完整源码验证：`QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests -v`。
