# 第三方组件与源码

NorthDiary 原创部分使用 **AGPL-3.0-or-later**，见 LICENSE / COPYRIGHT。
第三方组件的原始版权与许可证不因本项目的授权而改变。

| 组件 | 本包版本 | 许可证/声明位置 | 对应源码入口 |
| --- | --- | --- | --- |
| EbookLib | 0.20 | AGPLv3，licenses/EbookLib | https://pypi.org/project/EbookLib/0.20/#files |
| PySide6 / Shiboken6 | 6.9.2 | 选择 LGPLv3，licenses/PySide6*、shiboken6 | https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.9.2-src/pyside-setup-everywhere-src-6.9.2.zip |
| Qt | 6.9.2 | 随 PySide6 分发；相关模块选择 LGPLv3，保留模块自身第三方声明 | https://download.qt.io/archive/qt/6.9/6.9.2/single/qt-everywhere-src-6.9.2.zip |
| lxml | 6.1.1 | BSD 等，licenses/lxml（含 libxml2/libxslt 声明） | https://pypi.org/project/lxml/6.1.1/#files |
| six | 1.17.0 | MIT，licenses/six | https://pypi.org/project/six/1.17.0/#files |
| CPython | 3.13.9 | PSF 及第三方声明，licenses/LICENSE_PYTHON.txt | https://www.python.org/ftp/python/3.13.9/Python-3.13.9.tar.xz |
| OpenSSL | 3.0.18 | Apache-2.0，见 OpenSSL 项目 LICENSE.txt | https://github.com/openssl/openssl/releases/tag/openssl-3.0.18 |
| libffi | 3.4.4 | MIT，见其源码 LICENSE | https://github.com/libffi/libffi/releases/tag/v3.4.4 |
| SQLite | 3.51.0 | 公有领域；官方源码入口 | https://sqlite.org/2025/sqlite-src-3510000.zip |
| libmpdec | 4.0.0 | BSD，见 CPython 源码 Modules/_decimal/libmpdec/LICENSE.txt | https://www.python.org/ftp/python/3.13.9/Python-3.13.9.tar.xz |
| PyInstaller bootloader | 6.22.3 | GPLv2-or-later 加 bootloader 例外 | https://github.com/pyinstaller/pyinstaller/tree/v6.22.3 |

## 源码与修改

项目源码 ZIP 随安装包提供，包含正常构建所需的项目源码、图片、脚本和说明。
上游依赖未由 NorthDiary 修改。依赖源代码由上表相应版本的上游入口获取，
不将只含 Python 文件的 NorthDiary ZIP 描述为包含所有第三方库源代码。
公开发布时应将本安装包与对应源码包放在同一发布页，清楚列出这些下载入口；
不要将旧仓库分支描述为本安装包的对应源码。

允许按 LGPL 修改、替换 PySide6/Qt 并运行修改版，为此调试的逆向工程不受本项目限制。
可在源码中更换依赖重新构建，或替换安装目录 _internal 中匹配 ABI 的动态库；
更换 Python/Qt 大版本应完整重建。没有应用层库哈希校验或签名锁定。
本清单提供工程核对信息，不等同于所有上游依赖授权条件已经逐项完成法律审查。
