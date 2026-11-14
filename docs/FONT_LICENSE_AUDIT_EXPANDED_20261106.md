# NorthDiary 已安装字体扩展核对（2026-11-06）

本轮先扫描安装目录与 Windows 字体注册表，读取字体文件的名称、版权和许可元数据，再对拟通过的字体核查官方资料。扫描范围为 438 个 TTF/OTF/TTC 等文件、470 个字体字面、266 个家族；不是只核对原先随软件提供的四款。

## 结果

确认额外 11 个家族可按各自许可证免费商用；与原先四款合计，软件本机字体库现为 15 款。系统中另有已安装的 Noto 黑体和 Noto 宋体，因与原四款同名，不重复添加。

家族分类：{'已确认免费商用': 13, '未确认': 145, '随产品授权使用': 77, '厂商授权条件': 31}。另有 192 个遗留位图字体文件未启用，以及 1 个无法按标准字体格式解析的文件（mstmc.ttf）；它们未被认定为可免费商用。

“未确认”表示没有取得明确依据，不表示确认禁止商用。“随产品授权使用”也不表示禁止商用：微软允许符合其产品许可的多种商业输出，但这不等于字体文件可以免费捆绑、重新分发或移植到任何设备。

## 新增候选字体及官方依据

| 字体 | 许可 | 适用字形／备注 | 官方依据 |
| --- | --- | --- | --- |
| MiSans（小米） | MiSans 免费商用许可 | 中文正文；本软件使用了 MiSans 字体。 | [来源](https://hyperos.mi.com/font/zh/faq/) / [许可](https://hyperos.mi.com/font-download/MiSans%E5%AD%97%E4%BD%93%E7%9F%A5%E8%AF%86%E4%BA%A7%E6%9D%83%E8%AE%B8%E5%8F%AF%E5%8D%8F%E8%AE%AE.pdf) |
| Lato | SIL OFL 1.1 | 拉丁文字 | [来源](https://github.com/google/fonts/blob/main/ofl/lato/OFL.txt) / [许可](https://github.com/google/fonts/blob/main/ofl/lato/OFL.txt) |
| Academico | SIL OFL 1.1 | 拉丁衬线文字；本地字体内嵌完整 OFL 许可 | [来源](https://download.steinberg.net/webcontent/products/dorico/Dorico_21_Detailed_Feature_List.pdf) / [许可](https://download.steinberg.net/webcontent/products/dorico/Dorico_21_Detailed_Feature_List.pdf) |
| Noto 日文黑体 | SIL OFL 1.1 | 日文字形 | [来源](https://github.com/google/fonts/blob/main/ofl/notosansjp/OFL.txt) / [许可](https://github.com/google/fonts/blob/main/ofl/notosansjp/OFL.txt) |
| Sans Serif Collection | SIL OFL 1.1 | 多语种字形；本地字体声明 Noto 项目版权和 OFL 许可 | [来源](https://github.com/notofonts/noto-docs/blob/main/docs/website/use.md) / [许可](https://github.com/notofonts/noto-docs/blob/main/docs/website/use.md) |
| Petaluma Script | SIL OFL 1.1 | 拉丁手写文字 | [来源](https://github.com/steinbergmedia/petaluma) / [许可](https://github.com/steinbergmedia/petaluma) |
| Bravura（乐谱） | SIL OFL 1.1 | 乐谱符号 | [来源](https://github.com/steinbergmedia/bravura/blob/master/LICENSE.txt) / [许可](https://github.com/steinbergmedia/bravura/blob/master/LICENSE.txt) |
| Bravura Text（乐谱） | SIL OFL 1.1 | 乐谱符号 | [来源](https://github.com/steinbergmedia/bravura/blob/master/LICENSE.txt) / [许可](https://github.com/steinbergmedia/bravura/blob/master/LICENSE.txt) |
| Petaluma（乐谱） | SIL OFL 1.1 | 乐谱符号 | [来源](https://github.com/steinbergmedia/petaluma) / [许可](https://github.com/steinbergmedia/petaluma) |
| Petaluma Text（乐谱） | SIL OFL 1.1 | 乐谱符号 | [来源](https://github.com/steinbergmedia/petaluma) / [许可](https://github.com/steinbergmedia/petaluma) |
| DejaVu Math（数学） | Bitstream Vera / AMS / 公有领域扩展 | 数学与拉丁字形 | [来源](https://github.com/dejavu-fonts/dejavu-fonts/blob/master/LICENSE) / [许可](https://github.com/dejavu-fonts/dejavu-fonts/blob/master/LICENSE) |

MiSans 的官方 FAQ 明确允许在任意平台和商业项目使用；其专有许可要求软件注明使用 MiSans，并限制修改及单独分发字体。本版在“更多字体 → 字体许可”中保留注明。MiSans 不是 OFL 字体。

DejaVu Math 使用 Bitstream Vera、AMS 相关条款及公有领域扩展，不标成 OFL。乐谱字体已在显示名中标明，主要用于音符字形，并非中文正文字体。

## 对软件的处理

- 原有默认字体、像素字体、常用列表、搜索和分隔线保留。新增字体在“更多字体”中选择，不自动改动已勾选的常用列表。
- 新增字体调用本机已有的已核验文件，不下载或重新分发字体文件。37 个本地文件的路径与 SHA-256 已记录；文件缺失或内容变化时不自动当作已通过。
- 不修改、卸载系统字体，不批量改变旧文章。没有将 Windows、Office、方正或华文字体统一说成禁止商用。
- 仅非商业许可没有自动加入；开源、不收费不自动满足软件嵌入或字体再分发条件。

## 完整家族核对清单

| 家族 | 结果 | 依据／未通过原因 |
| --- | --- | --- |
| Academico | 已确认免费商用 | SIL OFL 1.1；[来源](https://download.steinberg.net/webcontent/products/dorico/Dorico_21_Detailed_Feature_List.pdf) |
| Agency FB | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Algerian | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Arial | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Arial Rounded MT Bold | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Bahnschrift | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Baskerville Old Face | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Bauhaus 93 | 厂商授权条件 | 本地许可要求遵守厂商 EULA 或联系厂商；未证实符合免费商用条件 |
| Bell MT | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Berlin Sans FB | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Berlin Sans FB Demi | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Bernard MT Condensed | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Blackadder ITC | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Bodoni MT | 厂商授权条件 | 本地许可要求遵守厂商 EULA 或联系厂商；未证实符合免费商用条件 |
| Book Antiqua | 厂商授权条件 | 本地许可要求遵守厂商 EULA 或联系厂商；未证实符合免费商用条件 |
| Bookman Old Style | 厂商授权条件 | 本地许可要求遵守厂商 EULA 或联系厂商；未证实符合免费商用条件 |
| Bookshelf Symbol 7 | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Bradley Hand ITC | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Bravura | 已确认免费商用 | SIL OFL 1.1；[来源](https://github.com/steinbergmedia/bravura/blob/master/LICENSE.txt) |
| Bravura Text | 已确认免费商用 | SIL OFL 1.1；[来源](https://github.com/steinbergmedia/bravura/blob/master/LICENSE.txt) |
| Britannic Bold | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Broadway | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Brush Script MT | 厂商授权条件 | 本地许可要求遵守厂商 EULA 或联系厂商；未证实符合免费商用条件 |
| Calibri | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Californian FB | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Calisto MT | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Cambria | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Cambria Math | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Candara | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Castellar | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Centaur | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Century | 厂商授权条件 | 本地许可要求遵守厂商 EULA 或联系厂商；未证实符合免费商用条件 |
| Century Gothic | 厂商授权条件 | 本地许可要求遵守厂商 EULA 或联系厂商；未证实符合免费商用条件 |
| Century Schoolbook | 厂商授权条件 | 本地许可要求遵守厂商 EULA 或联系厂商；未证实符合免费商用条件 |
| Chiller | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Colonna MT | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Comic Sans MS | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Consolas | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Constantia | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Cooper Black | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Copperplate Gothic Bold | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Copperplate Gothic Light | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Corbel | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Courier New | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Curlz MT | 厂商授权条件 | 本地许可要求遵守厂商 EULA 或联系厂商；未证实符合免费商用条件 |
| DejaVu Math TeX Gyre | 已确认免费商用 | Bitstream Vera / AMS / 公有领域扩展；[来源](https://github.com/dejavu-fonts/dejavu-fonts/blob/master/LICENSE) |
| DengXian | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| DFGHSMaruGothic-W4 | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| DFHannotateW7-B5 | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| DFHannotateW7-GB | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| DFHSMaruGothic-W4 | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| DFKanTingLiu-B5 | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| DFKanTingLiuW9-GB | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| DFLiJinHeiW8-GB | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| DFLiKingHei-XB | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| DFPHannotateW7-B5 | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| DFPHannotateW7-GB | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| DFPHSMaruGothic-W4 | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| DFPKanTeiRyu-XB | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| DFPKanTingLiu-B5 | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| DFPKanTingLiuW9-GB | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| DFPLiJinHeiW8-GB | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| DFPLiKingHei-XB | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| DIN Next Devanagari Std | 厂商授权条件 | 本地许可要求遵守厂商 EULA 或联系厂商；未证实符合免费商用条件 |
| Dubai | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Ebrima | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Edwardian Script ITC | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Elephant | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Engravers MT | 厂商授权条件 | 本地许可要求遵守厂商 EULA 或联系厂商；未证实符合免费商用条件 |
| Eras Bold ITC | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Eras Demi ITC | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Eras Light ITC | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Eras Medium ITC | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| FangSong | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Felix Titling | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Footlight MT Light | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Forte | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| FOT-MatisseV Pro | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| FOT-ModeMinBLarge Std | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| FOT-Seurat ProN | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| FOT-UDMincho Pr6N | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Franklin Gothic Book | 厂商授权条件 | 本地许可要求遵守厂商 EULA 或联系厂商；未证实符合免费商用条件 |
| Franklin Gothic Demi | 厂商授权条件 | 本地许可要求遵守厂商 EULA 或联系厂商；未证实符合免费商用条件 |
| Franklin Gothic Demi Cond | 厂商授权条件 | 本地许可要求遵守厂商 EULA 或联系厂商；未证实符合免费商用条件 |
| Franklin Gothic Heavy | 厂商授权条件 | 本地许可要求遵守厂商 EULA 或联系厂商；未证实符合免费商用条件 |
| Franklin Gothic Medium | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Franklin Gothic Medium Cond | 厂商授权条件 | 本地许可要求遵守厂商 EULA 或联系厂商；未证实符合免费商用条件 |
| Freestyle Script | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| French Script MT | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| FZFW ZhuZi MinchoS | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| FZKaTong-M19 | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| FZLanTingHei-R-GBK | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| FZLanTingKanHei-R-GBK | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| FZLanTingYuan-DB-GBK | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| FZLanTingYuan-R-GBK | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| FZLiBian-S02 | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| FZShuTi | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| FZXiaoBiaoSong-B05 | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| FZYaoTi | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| FZYaSong-B-GBK | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| FZYaSong-EL-GBK | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| FZYaSong-L-GBK | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| FZYaSong-M-GBK | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| FZYingBiKaiShu-S15 | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| FZYouHei_GBK | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| FZZhunYuan-M02 | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Gabriola | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Gadugi | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Garamond | 厂商授权条件 | 本地许可要求遵守厂商 EULA 或联系厂商；未证实符合免费商用条件 |
| Georgia | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Gigi | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Gill Sans MT | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Gill Sans MT Condensed | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Gill Sans MT Ext Condensed Bold | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Gill Sans Ultra Bold | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Gill Sans Ultra Bold Condensed | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Gloucester MT Extra Condensed | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Goudy Old Style | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Goudy Stout | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Haettenschweiler | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Harlow Solid Italic | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Harrington | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Heiti SC | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| High Tower Text | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| HYZhongHei | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Impact | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Imprint MT Shadow | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Informal Roman | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Ink Free | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Javanese Text | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Jokerman | 厂商授权条件 | 本地许可要求遵守厂商 EULA 或联系厂商；未证实符合免费商用条件 |
| Juice ITC | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| KaiTi | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Kingsoft UE | 未确认 | 本地声明 OFL，但未定位到字体自身的官方公开来源，暂不纳入 |
| Kristen ITC | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Kunstler Script | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Lato | 已确认免费商用 | SIL OFL 1.1；[来源](https://github.com/google/fonts/blob/main/ofl/lato/OFL.txt) |
| Leelawadee | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Leelawadee UI | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| LiSu | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Lucida Bright | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Lucida Calligraphy | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Lucida Console | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Lucida Fax | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Lucida Handwriting | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Lucida Sans | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Lucida Sans Typewriter | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Lucida Sans Unicode | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Magneto | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Maiandra GD | 厂商授权条件 | 本地许可要求遵守厂商 EULA 或联系厂商；未证实符合免费商用条件 |
| Malgun Gothic | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Marlett | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Matura MT Script Capitals | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Microsoft Himalaya | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Microsoft JhengHei UI | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Microsoft New Tai Lue | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Microsoft PhagsPa | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Microsoft Sans Serif | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Microsoft Tai Le | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Microsoft Uighur | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Microsoft YaHei | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Microsoft YaHei UI | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Microsoft Yi Baiti | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| MingLiU-ExtB | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| MingLiU_HKSCS-ExtB | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| MingLiU_MSCS-ExtB | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| MiSans | 已确认免费商用 | MiSans 免费商用许可；[来源](https://hyperos.mi.com/font/zh/faq/) |
| Mistral | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Modern No. 20 | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Mongolian Baiti | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Monotype Corsiva | 厂商授权条件 | 本地许可要求遵守厂商 EULA 或联系厂商；未证实符合免费商用条件 |
| MS Gothic | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| MS Outlook | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| MS PGothic | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| MS Reference Sans Serif | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| MS Reference Specialty | 厂商授权条件 | 本地许可要求遵守厂商 EULA 或联系厂商；未证实符合免费商用条件 |
| MS UI Gothic | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| MT Extra | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| MV Boli | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Myanmar Text | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Niagara Engraved | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Niagara Solid | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Nirmala Text | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Nirmala UI | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Noto Sans JP | 已确认免费商用 | SIL OFL 1.1；[来源](https://github.com/google/fonts/blob/main/ofl/notosansjp/OFL.txt) |
| Noto Sans SC | 已确认免费商用 | SIL OFL 1.1；[来源](https://github.com/google/fonts/blob/main/ofl/notosanssc/OFL.txt) |
| Noto Serif SC | 已确认免费商用 | SIL OFL 1.1；[来源](https://github.com/google/fonts/blob/main/ofl/notoserifsc/OFL.txt) |
| NSimSun | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| OCR A Extended | 厂商授权条件 | 本地许可要求遵守厂商 EULA 或联系厂商；未证实符合免费商用条件 |
| Old English Text MT | 厂商授权条件 | 本地许可要求遵守厂商 EULA 或联系厂商；未证实符合免费商用条件 |
| Onyx | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Palace Script MT | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Palatino Linotype | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Papyrus | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Parchment | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Perpetua | 厂商授权条件 | 本地许可要求遵守厂商 EULA 或联系厂商；未证实符合免费商用条件 |
| Perpetua Titling MT | 厂商授权条件 | 本地许可要求遵守厂商 EULA 或联系厂商；未证实符合免费商用条件 |
| Petaluma | 已确认免费商用 | SIL OFL 1.1；[来源](https://github.com/steinbergmedia/petaluma) |
| Petaluma Script | 已确认免费商用 | SIL OFL 1.1；[来源](https://github.com/steinbergmedia/petaluma) |
| Petaluma Text | 已确认免费商用 | SIL OFL 1.1；[来源](https://github.com/steinbergmedia/petaluma) |
| Playbill | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| PMingLiU-ExtB | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Poor Richard | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Pristina | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Qihei Lenovo | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Rage Italic | 厂商授权条件 | 本地许可要求遵守厂商 EULA 或联系厂商；未证实符合免费商用条件 |
| Ravie | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Reishoreiryu | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Rockwell | 厂商授权条件 | 本地许可要求遵守厂商 EULA 或联系厂商；未证实符合免费商用条件 |
| Rockwell Condensed | 厂商授权条件 | 本地许可要求遵守厂商 EULA 或联系厂商；未证实符合免费商用条件 |
| Rockwell Extra Bold | 厂商授权条件 | 本地许可要求遵守厂商 EULA 或联系厂商；未证实符合免费商用条件 |
| Sans Serif Collection | 已确认免费商用 | SIL OFL 1.1；[来源](https://github.com/notofonts/noto-docs/blob/main/docs/website/use.md) |
| Script MT Bold | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Segoe Fluent Icons | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Segoe MDL2 Assets | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Segoe Print | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Segoe Script | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Segoe UI | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Segoe UI Emoji | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Segoe UI Historic | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Segoe UI Symbol | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Segoe UI Variable | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Showcard Gothic | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| SimHei | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| SimSun | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| SimSun-ExtB | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| SimSun-ExtG | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Sitka | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Snap ITC | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| STCaiyun | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Stencil | 厂商授权条件 | 本地许可要求遵守厂商 EULA 或联系厂商；未证实符合免费商用条件 |
| STFangsong | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| STHupo | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| STKaiti | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| STLiti | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| STSong | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| STXihei | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| STXingkai | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| STXinwei | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| STZhongsong | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Sylfaen | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Symbol | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Tahoma | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Tempus Sans ITC | 厂商授权条件 | 本地许可要求遵守厂商 EULA 或联系厂商；未证实符合免费商用条件 |
| Times New Roman | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Trebuchet MS | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Tw Cen MT | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Tw Cen MT Condensed | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Tw Cen MT Condensed Extra Bold | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Verdana | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Viner Hand ITC | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Vivaldi | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Vladimir Script | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Webdings | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Wide Latin | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Wingdings | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Wingdings 2 | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Wingdings 3 | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| YouYuan | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| Yu Gothic | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| Yu Gothic UI | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |
| yyb | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| ÇcÇeÇfÇ‹ÇÈÇ‡Ç∂ëÃW7 | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| ÇcÇeÇoÇ‹ÇÈÇ‡Ç∂ëÃW7 | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| ÇcÇeÇ‹ÇÈÇ‡Ç∂ëÃW7 | 未确认 | 未取得覆盖本字体的软件使用与免费商用的明确许可依据 |
| 微軟正黑體 | 随产品授权使用 | 许可依附 Windows/Office 等产品；不据此认定字体文件可自由再分发；[来源](https://learn.microsoft.com/en-us/typography/fonts/font-faq) |

详细路径见工作区 outputs/font-system-review-20261106.json；原始元数据见 outputs/font-system-inventory-20261106.json。

本说明记录可核实的许可条件，不将个人使用、商业输出、软件嵌入与字体文件再分发视为同一项权利。
