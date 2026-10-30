# 开源与第三方复用

项目原创部分：AGPL-3.0-or-later，见根目录 LICENSE / COPYRIGHT。

当前主要依赖包括 PySide6/Qt、EbookLib、lxml、Python 标准库。版本、原始声明、源码入口与替换说明统一维护于根目录 THIRD_PARTY_NOTICES.md。没有将第三方依赖声明为本项目原创。

打包说明见 packaging/BUILD.md。发布时保留与安装包对应的源码，不包含用户数据库、照片、备份和凭据。
