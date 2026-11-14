# NorthDiary 字体授权核对与选择器更新

核对日期：2026-11-06，上海时间。

## 结论

软件正文与默认排版的字体候选列表只保留下列四款已核对的随包字体，不再枚举全部 Windows 系统字体。字体文件已随 NorthDiary 提供，本次不另行下载字体或安装系统字体。

这四款字体均采用 SIL Open Font License 1.1，允许免费用于个人和商业作品。分发字体本身时须保留版权与许可证，不得将字体文件本身单独售卖，修改字体还须遵守保留名称等条款。“免费商用”不等于无条件放弃著作权。

| 软件显示名 | 字体内部名称 | 官方许可证 |
| --- | --- | --- |
| Noto 黑体 | Noto Sans SC | [Google Fonts：OFL.txt](https://github.com/google/fonts/blob/main/ofl/notosanssc/OFL.txt) |
| Noto 宋体 | Noto Serif SC | [Google Fonts：OFL.txt](https://github.com/google/fonts/blob/main/ofl/notoserifsc/OFL.txt) |
| 霞鹜文楷 | LXGW WenKai | [作者仓库：OFL.txt](https://github.com/lxgw/LxgwWenKai/blob/main/OFL.txt) |
| 融合像素 | Fusion Pixel 12px Prop zh-Hans | [作者仓库 2026.10.25 版本：LICENSE-OFL](https://github.com/TakWolf/fusion-pixel-font/blob/2026.10.25/LICENSE-OFL) |

许可使用范围另见 [SIL 官方 OFL FAQ](https://openfontlicense.org/ofl-faq/)。融合像素还保留原有的上游字体许可文件，本次补齐该字体自己的官方 LICENSE-OFL.txt。

Windows 自带字体及第三方软件安装的其他字体，未逐一获得符合本次标准的明确许可证明，因此从软件候选列表移除；这不代表判定它们全部禁止商用。没有卸载或删除 Windows 中的字体，也没有批量改写旧文章。

## 文件身份核对

四个本地 TTF 文件的 SHA-256 与随包 `northdiary/assets/lyrics-fonts/SOURCES.json` 的来源记录一致；通过 Qt 注册后，内部字体名称也与上表一致。

| 文件键名 | SHA-256 |
| --- | --- |
| noto-sans-sc | a3041811a78c361b1de50f953c805e0244951c21c5bd412f7232ef0d899af0da |
| noto-serif-sc | 050080d9255a86808f2945bffac582b31ef32bc36411ce29563b4961670c66f9 |
| lxgw-wenkai | 2d73eea94ad808999d90c0000c239a84a33b09d4bc6ab6c5b8bbf1eda8a7fc8b |
| fusion-pixel | 58a0ac8784bfb0ed70b788a9cf815d00fcad9daa9e0517b8d1c244b4f912e3d6 |

## 界面行为

- 下拉框首项固定为“默认字体”，使用当前默认排版中的字体。未经核实的旧默认设置在新建文章时改用 Noto 黑体；已有文章保留原排版。
- 中间只显示在“更多字体”中勾选的字体，首次默认勾选四款，包含融合像素。
- 末尾在横线分隔后提供“更多字体…”。弹窗顶端可按中文显示名或英文内部名称搜索，列表可逐项勾选与取消。
- 搜索不会清除隐藏项目的勾选；点击“完成”保存当前日记库的常用列表，点击“取消”或 Esc 放弃本次修改。
- 正文与默认排版共用常用字体列表。只管理常用列表不会更改当前正文、选区或局部格式。
- 全部取消后，仍保留“默认字体”和横线后的“更多字体…”入口。

像素字体此前只在歌词模块按需加载；本次也为正文加载同一个已核实的融合像素文件。

## 验证与实现

相关 16 项检查通过，包括许可白名单、四个 TTF 文件身份、搜索和隐藏勾选、取消／保存、重读设置、空常用列表、默认项和分隔线、正文选区保留及局部像素字体。

使用独立临时数据，以 Qt offscreen 渲染字体下拉框、字体管理和搜索结果，并查看布局。该检查不替代用户对 Windows 字体观感的验收。

新增组件：`northdiary/ui/font_catalog.py`、`northdiary/ui/font_picker.py`。
开发副本：`C:\Users\NORTH\Documents\ChatGPT\NorthDiary\work\font-picker-20261106`。
实际安装目录仍为 `D:\NorthDiary-v1.5`。
