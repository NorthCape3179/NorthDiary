# GitHub 手动文章上传与下载（更新至 v1.5）

本版提供客户端代码，不需要自建服务器、安装 git 命令行或把 SQLite 上传云端。真实账户授权与 Windows 平台加密存储仍需实机验收。

## 操作入口

右侧“GitHub 上传与下载”打开连接窗口：连接账号 → 选择或新建独立私有数据仓库 → 选择文章上传，或选择远端记录下载并预览导入。网络工作在后台线程执行，SQLite 与本地导入仍在主线程；窗口关闭前等待正在进行的请求结束。

v1.5 的文章包使用原生清单 v2，携带所选文章关联的人物资料，兼容下载旧 v1 包。人物冲突处理见 PEOPLE.md。

上传复用原生 EPUB，最多 20 MiB；先保存当前编辑，选择文章与章节顺序，然后生成临时文章包。每次上传生成新的时间戳+UUID 文件，绝不覆盖旧包或远端数据库。图片随正文打包；未引用的独立附件、设置、回收站内容与凭据不上传。

下载记录固定到列出时的提交版本，通过 Git blob SHA 校验后，复用完整 EPUB 预检与导入预览。重复内容跳过，不同内容保留副本，不替换本机数据库；取消导入不写文章。临时传输文件随后清理。

这是一版手动文章包传输：不会自动更新同一篇文章、合并两端编辑、传播删除、定时同步或同步设置；也不是完整备份恢复。远端旧包保留历史，可能增长仓库用量。内容可在 GitHub 查看，并非端到端加密。

## 登录方式一：浏览器设备授权

需要先登记一个自己的 GitHub OAuth App，首次设置一次：

1. 打开 https://github.com/settings/developers → OAuth Apps → New OAuth App。
2. Application name 填 NorthDiary；Homepage URL 可填本项目仓库地址。
3. Authorization callback URL 可填 `http://127.0.0.1`（设备流程不使用回调，程序没有启动本地网页服务器）。
4. 保存应用，在应用设置中启用 Device Flow。
5. 将公开的 **Client ID** 粘贴到 NorthDiary；不要填写 Client Secret。
6. 点“在浏览器中登录 GitHub”，在 GitHub 官方网页输入软件显示的短验证码，确认授权；软件按 GitHub interval 轮询，遇 slow_down 增加等待，过期/取消停止。

该流程请求 `repo` 范围，可访问账号授权范围内的私有仓库，并非只授权一个数据仓库。若希望限制到单个仓库，使用下面的细粒度令牌。NorthDiary 不包含任何共享 Client Secret、应用私钥或用户密码。关闭窗口/取消登录会停止等待，迟到的授权响应被丢弃。

## 登录方式二：仅授权数据仓库的令牌

1. 在 GitHub 网页创建一个私有空仓库，如 NorthDiary-Data；不要与源码仓库同名，不勾选 README 等初始化文件。
2. GitHub Settings → Developer settings → Personal access tokens → Fine-grained tokens。
3. Resource owner 选对应账号；Repository access 只选上述数据仓库，授予 Repository permissions → Contents: Read and write（Metadata 随 GitHub 要求保留）。
4. 在软件“专用令牌”页粘贴令牌并连接，填写 `账号/NorthDiary-Data`，点击“连接 / 初始化空仓库”。

此类仅授予既有仓库权限的令牌可能不能创建新仓库，因此建议先在 GitHub 网页建空仓库，再连接。组织仓库还可能需要组织批准；程序不会绕过 GitHub 授权策略。

## 仓库保护

初始化仅接受空的私有仓库，写入 `northdiary-data.json` 格式标识。已有其他文件且没有本软件标识的仓库会被拒绝；任何名为 NorthDiary 的源码仓库也被拒绝。已经初始化的数据仓库校验标识后复用。新建按钮使用当前账号创建私有仓库；初始化失败不会擅自删除可能已创建的仓库，可在网页检查后重试连接。

仓库结构：`northdiary-data.json` + `packs/<UTC时间戳>-<UUID>.epub`。不存 `northdiary.sqlite3`、令牌或 ui.ini。远端目录最多列出 999 份符合格式的包，超过时需另建数据仓库归档。上传失败不自动重复写入，超时后先刷新确认远端结果，以免重复上传。

## 凭据与网络

“记住登录”仅在 Windows 提供，通过当前 Windows 用户的 DPAPI 加密保存到数据目录 `github.credentials`，使用临时文件原子替换；不使用机器共享密钥，不做明文回退。无法安全保存时仅本次会话连接。此文件已加入 .gitignore，不进入 EPUB 或 `.ndiary` 备份。ui.ini 只存公开 Client ID 与仓库名称。

断开会清除本机凭据，不删除云端包或本地文章；不等于撤销 GitHub 端授权，后者可在 GitHub 的应用/令牌设置中操作。程序仅访问固定 GitHub HTTPS 主机，拒绝重定向转发令牌，不使用外部 download_url，错误提示不回显服务端响应体或凭据。请求超时 30 秒，不擅自重试写入。

## 参考

- https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps
- https://docs.github.com/en/rest/repos/contents
- https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata
- https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptunprotectdata
