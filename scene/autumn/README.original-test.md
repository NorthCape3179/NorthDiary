# NorthDiary-AutumnScene · 0.1.0 测试版

完全独立的 PixiJS v8 + TypeScript + Vite + WebGL 工程。不需要 NorthDiary、Python、Qt、数据库、账号或 API key。没有读取或修改旧版 NorthDiary。

## 安装与运行

安装 Node.js 22.12+（也支持 24）。在本目录打开终端：

```sh
npm ci
npm run dev
```

打开终端显示的本地网址。首次安装需要网络，启动后的场景资源全部来自本工程，不请求远程 CDN。

```sh
npm test
npm run build
npm run preview
```

`npm ci` 使用随包提供的 package-lock.json；也可首次使用 `npm install`。`npm run build` 先检查 TypeScript，再生成 `dist/`。压缩包已包含构建产物；部署时只需把整个 dist 目录交给静态 HTTP 服务器。不要双击 HTML 使用 file://，浏览器模块与配置 fetch 需要 HTTP。开发端口以终端输出为准，停止使用 Ctrl+C。

Windows 快速运行预构建版本（仅在已安装 Python 时可选）：进入 dist 后执行 `python -m http.server 8080`，浏览器访问 http://localhost:8080。Python 只是可选的静态文件服务器，应用本身没有 Python 依赖。

## 本版已实现

- 480×270 逻辑画布、16:9 等比例缩放、最近邻采样、全屏与退出全屏。
- 13 个可单独开关的图层：天空、两层山、枫林、湖面、倒影、波纹、漂叶、两层空中落叶、湖岸石头、芦苇、树枝。
- 平滑统一风场，末端枝条分段摆动、枝上叶片脱离、芦苇分段弯曲且根部固定。
- 固定 1/60 秒模拟步，飘落→触水→漂浮→淡出→回收；固定 96 实体池；岸边遮挡、水域多边形与单次触水波纹。
- 像素行倒影位移、像素椭圆波纹、水面微光。采用可维护的像素渲染路径，尚无自定义水面 shader。
- 默认轻动态 30 FPS 目标、完整动态 60 FPS 目标、静态模式、暂停、隐藏页面暂停、减少动态效果偏好。
- 可折叠调试面板：风速/方向、落叶数量、波纹强度、品质、图层、遮罩、落水演示、4× 模拟时间、参数导出。
- 独立 DOM 歌词占位层，通信白名单与消息校验；没有接入真实音乐播放器或 Qt。

## 操作

右下工具栏「场景调试」打开面板；空格暂停/继续（输入控件聚焦时除外）。「演示落水」会在湖心生成一片即将触水的叶子；配合 4× 时间查看完整生命周期。轻动态的落叶滑块控制空中密度，完整动态使用 1.6 倍密度；加上漂浮叶，总可见数通常不超过密度的两倍。静态模式清除活动粒子并停止 ticker。

「歌词占位」使用本工程原创短句，与歌曲无关。「全屏」保留暂停、调试和退出按钮。

## 目录与美术替换

- `src/engine`：场景、资产、图层及生命周期。
- `src/systems`：统一风场、叶子状态机与渲染、水面、枝条、芦苇、品质。
- `src/bridge`：未来宿主通信入口及校验。
- `src/ui`：歌词 DOM。
- `public/config/autumn_day.scene.json`：图层顺序、素材路径、布局、水域多边形、动画参数。
- `public/assets/autumn_day`：独立 SVG 像素测试资源，可替换为透明 PNG。
- `scripts/generate-assets.mjs`：确定性测试资源生成器。`npm run assets` 会重新生成素材并覆盖默认配置；替换过素材后不要直接运行。
- `tests/scene.test.ts`：10 项自动测试。
- `dist`：已构建的静态页面。

**目前是程序化测试美术，未完成正式精修美术验收。** 顶部枝叶、石头、芦苇、10 种叶片与底景均为独立透明素材，不是完整背景图上随机撒叶。全景图层保持 480×270；局部素材需保留现有尺寸与 pivot，或同时修改对应系统的布局。替换为 PNG 后更新 JSON 文件名；水岸改变时同时更新 `water.polygon`、water_mask、foreground_mask 和湖岸纹理。运行时权威裁剪使用 polygon，遮挡由 shore 图层完成；两个 SVG mask 是可视化/制作参考。

若替换后缺资源，页面明确显示文件名，不会假装已加载。当前版本仅包含 autumn_day 场景；新季节可以复用系统，但还需要对应配置和资源。

## 预留通信契约（不含 Qt 实现）

初始化成功后可在宿主页使用：

```js
window.NorthDiaryScene.receive({type: 'pauseScene'});
window.NorthDiaryScene.receive({type: 'resumeScene'});
window.NorthDiaryScene.receive({type: 'setQuality', value: 'light'});
window.NorthDiaryScene.receive({type: 'setTheme', value: 'autumn_day'});
window.NorthDiaryScene.receive({type: 'setPlayback', value: {
  title: '测试曲目', artist: '', durationMs: 60000, positionMs: 12000,
  playing: true, lines: [{timeMs: 0, text: '测试文本'}]
}});
window.NorthDiaryScene.receive({type: 'disconnect'});
const unsubscribe = window.NorthDiaryScene.subscribe(event => console.log(event));
const state = window.NorthDiaryScene.getState();
unsubscribe();
// 页面彻底卸载前：await window.NorthDiaryScene.destroy();
```

返回 `{ok:true}` 或 `{ok:false,error:...}`。不接受任意脚本，不监听跨域 postMessage。歌词以 textContent 显示；时间戳必须升序，最多 500 行，每行最多 500 字。宿主负责持续发送 positionMs，当前层不推算播放器时间。disconnect 清空歌词；setPlayback 可处理空歌词及暂停状态。setTheme 目前只接受 autumn_day。未来由独立适配器连接 Qt WebChannel，不需要改动动画系统。

## 验证记录与限制

- TypeScript 检查和 Vite 生产构建通过。
- 10 项测试通过：配置校验、素材存在性、风场连续性、水域、单次落水/完整生命周期、陆地落点、30 分钟模拟、对象池上限、品质状态、桥接校验。
- 30 分钟是加速执行的纯逻辑模拟：峰值 24 片，536 次触水，652 次回收，对象池始终 96 个对象。**这不等同于浏览器连续运行 30 分钟或 GPU/内存性能验收。**
- 云端浏览器已实际打开场景，检查构图、图层、调试面板、风速方向、密度、品质切换、水域遮罩与落水事件。预览环境当时显示约 1 FPS，尚不能确定是环境节流还是设备渲染限制；没有声称达到 30/60 FPS。
- 手机和平板布局已写入响应式样式；尚未进行多台实机、多个分辨率与全屏全面验收。
- 正式美术、定制 shader、长时间实机性能测试、Qt 与播放器对接留待后续。本阶段没有依赖旧版 NorthDiary。

## 依赖与资料

锁定的实际版本见 package-lock.json。PixiJS 初始化采用 v8 异步 Application.init，纹理 nearest，Vite 使用相对 base 路径，方便之后挂载到子路径。

官方资料：https://pixijs.com/8.x/guides/components/application
