# Windows x64 构建 v1.7.0

原安装包使用 Python 3.13.9（Conda）/ PySide6 6.9.2 / PyInstaller 6.22.3 / Inno Setup 7.1.1。
运行支持 Python 3.11–3.13；构建环境应优先使用上述已验证版本。新环境构建须重新验收。
以下命令在解压后的项目根目录 PowerShell 执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r packaging/requirements-build.txt
.\.venv\Scripts\python.exe main.py --data-dir .\scratch-data
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --distpath dist --workpath build packaging/NorthDiary.spec
```

如 PyInstaller 扫描用户 site-packages 时遇到权限错误，可先设置当前进程
`$env:PYTHONUSERBASE = Join-Path (Get-Location) "build-usersite"`，再重试构建。

如用 Conda Python，先将其 `Library/bin` 加入当前 PATH；spec 同时显式收集 SQLite/ffi/mpdec DLL。
官方 CPython 安装方式由 PyInstaller 自行解析相关依赖；不要硬编码他人的 D 盘路径。
本源码包保留界面 PNG 和 ICO，不能为缩小体积删掉这些构建资源。

安装 Inno Setup 7.1.1 后，使用其 ISCC.exe 编译 `packaging/NorthDiary.iss`，
例如 `& 'C:/path/to/Inno Setup 7/ISCC.exe' packaging/NorthDiary.iss`。
产物为 release/NorthDiary-Setup-v1.7.0.exe；不需要用户安装 Python。

发布前将本源码包复制至 dist/NorthDiary/_internal/licenses/NorthDiary-1.7.0-source.zip，
并保留该目录完整许可证。然后再编译 Inno 安装包；源 ZIP 不包含它自身。
项目原始构建采用本 spec 同样参数、原界面代码与资源。文件时间、宿主 Python 发行版
及工具链会影响二进制结果，不承诺逐字节可复现。

安装验证：运行 `dist/NorthDiary/NorthDiary.exe --verify-installation report.json`。
此隐藏诊断只创建临时合成数据，不读取真实日记；成功应生成 success=true 的 JSON。
还需测试安装、覆盖升级和卸载，并确认外部数据哈希保持一致。

本轮原源码回归：164 项，160 通过、2 已知失败、2 跳过；不是全绿。
已知失败：Windows GitHub UI 测试替身 save 方法、EPUB 反斜线路径拒绝测试。
未包含签名私钥；本安装包未数字签名。程序数据库无需随构建复制。
