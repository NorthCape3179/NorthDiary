# 开源复用记录

本版复用 PySide6/Qt 的 QTextEdit、QSplitter、日期选择器、对话框、图片解码和平台数据路径，以及 Python 标准库 SQLite/ZIP。没有从其他应用复制源码、图标或主题。

评估过：

- https://github.com/miloisme/MyDiary ：PySide6/SQLite 日记，README 标示 Apache-2.0，侧重加密与 Android/Drive 同步，数据与本项目图文附件架构有差异，未作为底仓。
- https://github.com/Ovid/pyqt6-rich-text-editor ：MIT 富文本示例，适合独立 HTML 编辑；本项目需要事务保存、多分类与托管附件，未直接复制示例源码。

文档参考：https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QTextEdit.html

PySide6 为第三方依赖，不纳入本项目原创代码声明。正式分发 EXE 前应收录对应版本的 Qt/PySide6 许可和第三方声明，并复核打包方式。本轮没有生成发布包。
