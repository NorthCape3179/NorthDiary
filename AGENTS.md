# NorthDiary 协作规则

- 中文沟通；先检查现有代码和状态，控制每轮范围，不生成大而全的单体。
- 原生 Windows 桌面，Python/PySide6/SQLite；不得擅自改成网页应用。
- 用户数据独立于源码；不得提交数据库、附件、备份、凭据或虚拟环境。
- 保存失败必须保留编辑内容；分类是多对多引用，不能复制文章。
- 数据库变更必须写迁移，不得删除现有数据库。
- 避免不必要依赖和重构；优先已有组件。
- 验证命令：python -m unittest discover -s tests -v。
- 云端 Qt 使用 QT_QPA_PLATFORM=offscreen，不能把无头测试通过等同于 Windows 体验验收。
- 尚未实现的功能在 UI 和文档中明确标示，不声称完成。
