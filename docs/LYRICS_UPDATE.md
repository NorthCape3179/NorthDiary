# 歌词设置与真实进度修正

右上角音乐图标旁新增下拉箭头。菜单仅保留：歌词显示开关、字体切换、字号大小、刷新；歌词板移除全部控制按钮。原字号/字体/偏移设置仍保留，偏移控件本轮隐藏，不再占歌词区。

本机网易云 3.1.41.205529 的 SMTC 只提供歌曲和播放状态：连续四次读取 position=0、start=0、end=0、last_updated_time=1601 年。此时不能准确同步。现在明确检测缺失时间轴并显示等待准确进度，不把空时间轴当成零秒反复刷新，不用本地从零模拟冒充实际进度。

多个网易云会话并存时优先选正在播放且具有真实时间轴的会话；额外识别 InfLink 标识，修正正在播放但速率字段为0时的兼容处理。收到有效时间轴后按时间戳插值、切换歌词，暂停/拖动由新的系统进度校正。

用户选择优先准确获取进度，因此继续调查插件：InfLink-rs v3.4.0 官方 README 测试范围覆盖 3.1.20–3.1.41，提供每秒更新的实际播放进度，需要 BetterNCM 加载器。已准备官方 BetterNCM 1.3.4 x64 DLL 和 InfLink-rs v3.4.0 插件，存于工作区 `work/netease-lyrics-plugin` 并保存SHA256，尚待用户明确同意安装到网易云目录；NorthDiary 本身不静默安装外部插件。

安装仅新增 `C:/Program Files/NetEase/CloudMusic/msimg32.dll` 以及 `C:/betterncm/plugins/InfLink-rs.plugin`；禁止覆盖已有加载器/插件。用户自行重启网易云后生效。插件默认启用 SMTC、禁用 Discord RPC，参见作者 `packages/frontend/src/store.ts`。安装脚本与回退清单单独准备，不触碰账户、日记或音乐文件。

也查看了 now-playing-service 的 UI Automation 进度文本读取方案，但当前网易云默认播放栏未稳定暴露进度文本，不作为本轮准确同步的依赖。

资料：

- https://github.com/apoint123/inflink-rs/blob/main/README.md
- https://github.com/apoint123/inflink-rs/releases/tag/v3.4.0
- https://github.com/apoint123/inflink-rs/blob/main/packages/frontend/src/store.ts
- https://github.com/std-microblock/chromatic/releases/tag/1.3.4
- https://github.com/Widdit/now-playing-service/blob/master/external_programs/AudioService/GetMusicStatus/Helpers/NeteaseMusicHelper.cs

验证仅做临时库原生启动/菜单布局与只读系统进度诊断，不跑全量测试。安装插件后的真实进度验证待安装生效后进行。
