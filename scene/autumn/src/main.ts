import './style.css';
import './polish.css';
import { SceneManager } from './engine/SceneManager';
import { SceneBridge } from './bridge/SceneBridge';
import { LyricsOverlay } from './ui/LyricsOverlay';
import type { Quality } from './config/types';
import { connectHost, nativeHost, isNative } from './bridge/NativeHost';
document.body.classList.add('embedded');
const icons={leaf:'<svg viewBox="0 0 24 24"><path d="m12 2 2 5 5-2-1 5 4 2-6 3-3 5-3-5-6-3 4-2-1-5 5 2Z"/><path d="m12 12-1 10"/></svg>',play:'▶',pause:'Ⅱ',expand:'⛶',tune:'<svg viewBox="0 0 24 24"><path d="M4 7h16M4 17h16"/><circle cx="9" cy="7" r="3"/><circle cx="15" cy="17" r="3"/></svg>'};
document.querySelector<HTMLDivElement>('#app')!.innerHTML=`
<div class="shell">
 <header class="topbar"><a class="brand" href="./" aria-label="NorthDiary 秋日湖畔">${icons.leaf}<span>NORTHDIARY<small>SCENE STUDIES / 001</small></span></a><div class="edition"><span class="dot"></span>独立场景实验 <span class="badge">SCENE 0.3</span></div></header>
 <main>
  <div class="intro"><div><p class="eyebrow">AUTUMN, IN A QUIETER TEMPO</p><h1>秋日湖畔<span>让时间慢下来。</span></h1></div><p class="intro-note">山色在远处，风落在水面。<br>留一会儿，看一片叶子的旅程。</p></div>
  <section class="scene-frame" id="frame" aria-label="动态场景">
   <div id="viewport"><div id="canvas-host"></div><div class="lyrics" id="lyrics" hidden></div><div class="scene-label"><span class="live-dot"></span><span id="scene-state">正在准备秋天</span></div><div class="scene-coordinate">AUTUMN LAKE / 01</div></div>
   <div class="fullscreen-controls"><button id="fs-pause">暂停 / 继续</button><button id="fs-debug">场景调试</button><button id="fs-exit">退出全屏 ↙</button></div>
   <div class="loading" id="loading"><div class="leaf-mark">${icons.leaf}</div><p>正在铺开一片秋天…</p></div>
  </section>
  <div class="toolbar"><div class="play-group"><button id="pause" class="round-button" aria-label="暂停动画">Ⅱ</button><div class="weather"><strong id="weather">微风 · 秋日午后</strong><span id="weather-note">风与水，各有自己的节奏</span></div></div>
   <div class="tools"><button class="tool-button" id="lyrics-toggle" aria-pressed="false"><span>♫</span><span>歌词占位</span></button><span class="separator"></span><button class="tool-button" id="fullscreen"><span>⛶</span><span>全屏</span></button><button class="tool-button debug-toggle" id="debug-toggle" aria-expanded="false" aria-controls="debug">${icons.tune}<span>场景调试</span></button></div>
  </div>
  <div class="under-scene"><p><span class="tiny-leaf">◇</span> 秋日湖畔 · 微风与落叶</p><p>480 × 270 <span> / </span> WEBGL <span> / </span> <span id="fps">— FPS</span></p></div>
 </main>
 <footer><span>给回忆留一处安静的地方。</span><span>NORTHDIARY–AUTUMNSCENE <b>独立测试版</b></span></footer>
</div>
<aside class="debug" id="debug" hidden aria-label="开发调试面板">
 <div class="debug-heading"><div><p class="eyebrow">SCENE LAB</p><h2>调一阵风</h2></div><button id="debug-close" class="icon-button" aria-label="关闭调试面板">×</button></div>
 <p class="panel-note">参数即时生效，让画面按照你的节奏呼吸。</p>
 <label class="slider-label" for="wind">风速与方向 <output id="wind-out">0.35</output></label><input id="wind" type="range" min="-1.5" max="1.5" step="0.05" value="0.35"><div class="range-hints"><span>← 向左</span><span>向右 →</span></div>
 <label class="slider-label" for="count">落叶数量 <output id="count-out">12</output></label><input id="count" type="range" min="0" max="24" step="1" value="12">
 <label class="slider-label" for="water">水面波纹 <output id="water-out">0.65</output></label><input id="water" type="range" min="0" max="1.5" step="0.05" value="0.65">
 <label class="field-label" for="quality">动态品质</label><select id="quality"><option value="static">静态 · 停止动画</option><option value="light" selected>轻动态 · 30 FPS</option><option value="full">完整动态 · 60 FPS</option></select>
 <div class="check-row"><label><input type="checkbox" id="masks">水域 / 歌词安全区</label></div><div class="check-row"><label><input type="checkbox" id="speed">4× 时间 · 生命周期测试</label></div>
 <div class="panel-actions"><button id="landing">演示落水</button><button id="reset">重置参数</button></div>
 <details class="layers"><summary>图层与遮挡 <span>9 层</span></summary><div id="layers"></div></details>
 <div class="stats"><div>当前风场 <strong id="stat-wind">—</strong></div><div>飘落 / 漂浮 <strong id="stat-leaves">—</strong></div><div>触水 / 已回收 <strong id="stat-life">—</strong></div><div>运行时间 <strong id="stat-time">—</strong></div></div>
 <button class="export-button" id="export">导出场景参数 JSON <span>↗</span></button><p class="panel-footnote">素材独立存放，可替换为 PNG。<br>未连接 NorthDiary 或音乐播放器。</p>
</aside><div id="toast" role="status"></div>`;
const $=<T extends HTMLElement=HTMLElement>(id:string)=>document.getElementById(id) as T;
const scene=new SceneManager(),lyrics=new LyricsOverlay($('lyrics'));
let toastTimer:ReturnType<typeof setTimeout>;
function toast(text:string){$('toast').textContent=text;$('toast').classList.add('visible');clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').classList.remove('visible'),5000);}
scene.onNotice=toast;
const bridge=new SceneBridge(message=>{
  if(message.type==='pauseScene')scene.setPaused(true);
  if(message.type==='resumeScene')scene.setPaused(false);
  if(message.type==='setQuality')scene.setQuality(message.value);
  if(message.type==='setPlayback'){lyrics.setPlayback(message.value);if(!isNative)$('lyrics-toggle').setAttribute('aria-pressed','false');}
  if(message.type==='disconnect'){lyrics.clear();$('lyrics-toggle').setAttribute('aria-pressed','false');}
  if(message.type==='setTheme')toast('当前场景：秋日湖畔');
});
declare global {interface Window {NorthDiaryScene:{receive:SceneBridge['receive'];subscribe:SceneBridge['subscribe'];getState:()=>unknown;destroy:()=>Promise<void>}}}
function state(){return {version:'0.3.0',quality:scene.quality.quality,running:scene.quality.running,time:scene.simulation?.time??0,active:scene.simulation?.active??0,landings:scene.simulation?.landings??0,recycled:scene.simulation?.recycled??0,poolCapacity:scene.simulation?.leaves.length??0,surfaceLeaves:scene.surfaceLeaves?.count??0,ripples:scene.water?.rings.filter(r=>r.active).length??0};}
function updateControls(){
  const running=scene.quality.running;
  $('pause').textContent=running?'Ⅱ':'▶';$('pause').setAttribute('aria-label',running?'暂停动画':'继续动画');
  $('scene-state').textContent=scene.quality.quality==='static'?'静静的秋天':running?'风正在经过':'此刻已暂停';
  $('frame').classList.toggle('paused',!running);$<HTMLSelectElement>('quality').value=scene.quality.quality;
  for(const name of ['wind','count','water'] as const){const value=name==='wind'?scene.wind.config.baseX:name==='count'?scene.config.leaves.count:scene.water.intensity;$<HTMLInputElement>(name).value=String(value);$(name+'-out').textContent=name==='count'?String(value):value.toFixed(2);}
  bridge.emit({type:'stateChanged',state:state()});
}
function toggleDebug(open:boolean){$('debug').hidden=!open;$('debug-toggle').setAttribute('aria-expanded',String(open));if(open)$('debug-close').focus();else $('debug-toggle').focus();}
async function start(){
 try{
  await scene.init($('canvas-host'),$('frame'),$('viewport'));$('loading').hidden=true;
  const defaults={wind:scene.config.wind.baseX,count:scene.config.leaves.count,water:scene.config.water.intensity};
  scene.onChange=updateControls;updateControls();
  $('pause').onclick=()=>{if(scene.quality.quality==='static'){scene.setQuality('light');scene.setPaused(false);}else scene.togglePause();};
  $('debug-toggle').onclick=()=>toggleDebug($('debug').hidden);$('debug-close').onclick=()=>toggleDebug(false);
  $('lyrics-toggle').onclick=()=>{if(isNative){nativeHost?.setLyricsEnabled($('lyrics-toggle').getAttribute('aria-pressed')!=='true');return;}lyrics.setDemo(!lyrics.demo);$('lyrics-toggle').setAttribute('aria-pressed',String(lyrics.demo));};
  $('fullscreen').onclick=async()=>{if(isNative){document.body.classList.toggle('focus-scene');return;}try{if(document.fullscreenElement)await document.exitFullscreen();else await $('frame').requestFullscreen();}catch{toast('当前浏览器不支持全屏，请使用横屏或浏览器全屏模式。');}};
  $('fs-exit').onclick=()=>{if(isNative)document.body.classList.remove('focus-scene');else void document.exitFullscreen();};$('fs-pause').onclick=()=>$('pause').click();$('fs-debug').onclick=()=>toggleDebug($('debug').hidden);
  document.addEventListener('fullscreenchange',()=>{(document.fullscreenElement?$('frame'):document.body).append($('debug'));});
  for(const name of ['wind','count','water'] as const)$<HTMLInputElement>(name).oninput=e=>scene.setParameter(name,Number((e.target as HTMLInputElement).value));
  $<HTMLSelectElement>('quality').onchange=e=>scene.setQuality((e.target as HTMLSelectElement).value as Quality);
  $<HTMLInputElement>('masks').onchange=e=>scene.showMasks((e.target as HTMLInputElement).checked);
  $<HTMLInputElement>('speed').onchange=e=>{scene.timeScale=(e.target as HTMLInputElement).checked?4:1;toast(scene.timeScale===4?'已开启 4× 模拟时间':'已恢复正常时间');};
  $('landing').onclick=()=>scene.demoLanding();
  $('reset').onclick=()=>{scene.setParameter('wind',defaults.wind);scene.setParameter('count',defaults.count);scene.setParameter('water',defaults.water);scene.setQuality('light');scene.setPaused(false);scene.timeScale=1;$<HTMLInputElement>('speed').checked=false;$<HTMLInputElement>('masks').checked=false;scene.showMasks(false);for(const [id,layer]of scene.layers.layers){layer.visible=true;const checkbox=document.querySelector<HTMLInputElement>(`[data-layer="${id}"]`);if(checkbox)checkbox.checked=true;}toast('已恢复默认场景参数');};
  $('export').onclick=()=>{const url=URL.createObjectURL(new Blob([scene.exportConfig()],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='autumn_day.scene.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
  const names:Record<string,string>={sky:'天空',far_mountains:'远山',near_mountains:'近山',forest:'对岸枫林',lake:'湖面底色',reflection:'水面倒影',ripples:'波纹与微光',floating_leaves:'水面漂叶',falling_leaves_back:'后景落叶',shore:'前景湖岸 / 石头',reeds:'芦苇',branches:'顶部枫枝',falling_leaves_front:'前景落叶'};
  names.sky='远景底图 · 天空、群山与枫林';
  names.near_canopy='近景密叶树冠';names.surface_leaves_far='远处水面漂叶';names.surface_leaves_near='近岸水面漂叶';
  for(const layer of scene.config.layers){if(!layer.asset&&!layer.dynamic)continue;const label=document.createElement('label');label.className='layer-row';const input=document.createElement('input');input.type='checkbox';input.checked=true;input.dataset.layer=layer.id;input.onchange=()=>{scene.layers.visible(layer.id,input.checked);scene.render();};label.append(input,document.createTextNode(names[layer.id]??layer.id));$('layers').append(label);}
  document.querySelector('.layers summary span')!.textContent=`${$('layers').children.length} 层`;
  window.addEventListener('keydown',e=>{if(e.key==='Escape'){document.body.classList.remove('focus-scene');if(!$('debug').hidden)toggleDebug(false);}if((e.target as HTMLElement).matches('input,select,textarea,button'))return;if(e.code==='Space'){e.preventDefault();$('pause').click();}});
  const stats=setInterval(()=>{
    $('fps').textContent=scene.quality.running?`${Math.round(scene.app.ticker.FPS)} FPS`:'已暂停';
    const wind=scene.wind.sample(scene.simulation.time);$('stat-wind').textContent=wind.toFixed(2);$('weather').textContent=`${wind<0?'西向':'东向'}${Math.abs(wind)>.85?'阵风':'微风'} · 秋日午后`;
    $('stat-leaves').textContent=`${scene.simulation.leaves.filter(l=>l.state==='FALLING').length} / ${scene.simulation.leaves.filter(l=>l.wet&&l.state!=='RECYCLED').length+(scene.surfaceLeaves?.count??0)}`;
    $('stat-life').textContent=`${scene.simulation.landings} / ${scene.simulation.recycled}`;$('stat-time').textContent=`${Math.floor(scene.simulation.time)} s`;
  },750);
  window.NorthDiaryScene={receive:bridge.receive,subscribe:bridge.subscribe,getState:state,destroy:async()=>{clearInterval(stats);clearTimeout(toastTimer);bridge.destroy();await scene.destroy();}};
  if(isNative){
    document.body.classList.add('native-scene');
    let wasActive = false;
    $('lyrics-toggle').lastElementChild!.textContent='同步歌词';
    $('fullscreen').lastElementChild!.textContent='铺满场景';
    $('fs-exit').textContent='退出铺满 ↙';
    $('debug-toggle').lastElementChild!.textContent='场景设置';
    $('fs-debug').textContent='场景设置';
    document.querySelector('.panel-footnote')!.textContent='已接入 NorthDiary 播放信息与双语歌词。参数仅控制当前场景。';
    connectHost(message=>{
      scene.setHostActive(message.active);
      if (message.active && !wasActive) document.body.classList.add('focus-scene');
      wasActive = message.active;
      $('lyrics-toggle').setAttribute('aria-pressed',String(message.lyricsEnabled));
      if(message.playback)bridge.receive({type:'setPlayback',value:message.playback});
      else lyrics.clear();
    });
  }
  bridge.emit({type:'ready',version:'0.3.0',capabilities:['pause','quality','lyrics','autumn_day']});
 }catch(error){
  $('loading').replaceChildren();const title=document.createElement('h2');title.textContent='场景暂时无法启动';const detail=document.createElement('p');detail.textContent=error instanceof Error?error.message:String(error);const hint=document.createElement('p');hint.textContent=isNative?'请检查显卡驱动或点击重新加载；也可以返回日记继续使用。':'请启用浏览器硬件加速，并通过 npm run dev 或静态服务器访问。';const retry=document.createElement('button');retry.textContent='重新加载';retry.onclick=()=>location.reload();$('loading').append(title,detail,hint,retry);console.error(error);
 }
}
void start();
