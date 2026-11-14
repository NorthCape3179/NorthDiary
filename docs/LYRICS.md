# 阅读模式歌词

右上角歌词图标在阅读模式底部的原照片板位置切换歌词；从编辑模式点击会先保存并进入阅读模式。再次点击恢复图片，原附件不改动。离开阅读模式 / AI 工作室切换时停止观察与联网，重新进入可继续；默认不开启，不持久化开启状态。

仅观察网易云（CloudMusic / NetEase）的 Windows SMTC 会话，读取歌曲名、歌手、专辑、时长、播放状态、播放速度和时间线。后台工作线程每约 0.8 秒更新，面板每 0.1 秒按系统时间线插值；支持暂停和跳转，不控制播放器。系统未暴露 SMTC 时提示等待，不抓取网易云账户或本地缓存。

LRCLIB 仅接收上述歌曲元数据，不接触日记或附件；无需账号或 API Key。按签名 `/api/get` 匹配，404 后 `/api/search` 仅接受归一化标题/歌手相同且时长相差不超过 2 秒的结果，不任取第一个搜索结果。10 秒请求超时，换歌和关闭会取消旧请求；最多缓存 48 个结果，仅在内存中。失败可手动重试；无同步歌词时支持滚轮浏览纯文本；纯音乐单独提示。

LRC 支持多时间戳、毫秒、offset 和同时间双语行；显示前一行 / 当前行 / 后一行，按行同步，不是逐字卡拉 OK。全局提前量可调 ±10000 ms（正数提前），字体 / 字号 / 提前量保存在本机 ui.ini。

内置完整未修改字体：Noto Sans SC、Noto Serif SC（思源对应的 Noto 系列）、LXGW WenKai、Fusion Pixel 12px 简体。均随附原始 OFL 许可证（融合像素保留发布包所附的全部许可证），不安装到系统，只在歌词中加载。资源来源与 SHA256 位于 `northdiary/assets/lyrics-fonts/SOURCES.json`。约 73 MB 字体资源，首次使用所选字体时加载。

参考资料（独立实现，没有复制这些项目源码）：

- Windows SMTC: https://learn.microsoft.com/en-us/uwp/api/windows.media.control.globalsystemmediatransportcontrolssessionmanager
- PyWinRT（MIT，安装包保留许可证）: https://github.com/pywinrt/pywinrt
- LRCLIB 开源服务与 API: https://github.com/tranxuanthang/lrclib · https://lrclib.net/docs
- Noto Sans SC: https://github.com/google/fonts/tree/main/ofl/notosanssc
- Noto Serif SC: https://github.com/google/fonts/tree/main/ofl/notoserifsc
- LXGW WenKai: https://github.com/lxgw/LxgwWenKai
- Fusion Pixel: https://github.com/TakWolf/fusion-pixel-font

验证：临时数据库原生窗口启动、阅读模式歌词入口、四字体加载和布局预览；正常 Windows 用户上下文 SMTC 接口可访问，当前会话数量 0，未进行真实网易云曲目的端到端同步验收。未跑全量测试，实际播放由用户验收。EXE 尚未重打包。
