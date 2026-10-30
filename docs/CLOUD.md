# 版本说明（2026-10-30，v1.5）

v1.5 独立分支增加人物档案、文章人物标签、代号快捷插入与 EPUB/GitHub 文章包的人物资料交换。schema v3→v4，迁移前自动快照，旧版不能打开升级后的数据库。未修改用户电脑本地工程；Windows 实机验收仍待进行。详见 PEOPLE.md。以下为历史说明。

# 版本说明（2026-10-30，v1.4）

v1.4 在独立分支增加时间线总览、年/月方块分隔与未详归类、随机回忆、右上角功能动画收起。保留 v1.3 的 GitHub 客户端；不改数据库结构。Windows 验收待进行，未修改用户电脑本地工程。

v1.3 增加 GitHub 连接、专用私有数据仓库初始化与手动文章包上传下载；自动同步未实现。OAuth Client ID 或专用令牌需要用户首次配置，详见 GITHUB_TRANSFER.md。未修改用户 Windows 本地工程。

v1.2 独立分支增加本软件原生 EPUB 导出再导入；旧 v1.1 EPUB 需重新导出。v1.0、v1.1 与 main 不改动。GitHub 账户登录、云端日记同步尚未实现。

v1.0 分支保留昨晚完整桌面版；v1.1 保留其全部源文件与九张背景素材，并增加 EPUB 导出。main 未改动。后续需求见 ROADMAP.md。

# 手机与云端开发交接

目标：Windows 电脑关机后，仍能从手机在 Codex Cloud 继续开发。GitHub 保存源码；Codex Cloud 执行任务。上传 GitHub 本身不会把本地会话转换成云端会话。

## 一次性连接

1. 将本工程上传 GitHub 私有仓库，不上传真实日记、附件、备份、虚拟环境、令牌。
2. 桌面或网页选择 Work in > Cloud > Select environment > Create environment。
3. 选择 NorthDiary 仓库，完成必要的 GitHub 授权。
4. 让环境安装 Python 依赖、运行下列测试，检查结果后 Publish。
5. 在手机 Codex 选择已发布环境，开始云端任务；继续同一云端任务可保留任务上下文。

官方文档：https://learn.chatgpt.com/docs/environments/cloud-environments

## 环境命令

```sh
python -m pip install -r requirements.txt
QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests -v
```

若 Linux 镜像缺少 Qt 运行库，安装系统的 libegl1、libopengl0 等实际报错所需依赖，再重跑测试。不要为这个纯桌面项目启动网页服务器。Windows GUI 体验与打包仍需在 Windows 验证。

## 可直接使用的云端任务说明

> 阅读 AGENTS.md、README.md 和 docs/ARCHITECTURE.md。NorthDiary 是 Python/PySide6/SQLite 原生 Windows 图文日记应用。先运行现有测试并总结状态，再按我指定的单一功能开发。不要改成网页，不要删库，不要上传真实日记。每个任务只做一个小闭环，更新测试与文档，给出变更和实际验证结果。优先复用已有代码和成熟依赖，减少无关重构。

## 当前交接状态

0.1 已包含主界面、存储闭环、基础分类标签、托管图片附件、回收站与备份导出。优先后续任务：安全的备份恢复流程，其次完整编辑工具栏与 EPUB。

本说明仅为配置准备；是否已上传仓库、发布环境、启动云端任务，以对应服务的实际结果为准。

