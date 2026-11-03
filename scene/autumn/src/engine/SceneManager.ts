import { Application, Graphics, Sprite } from 'pixi.js';
import { AssetManager } from './AssetManager';
import { LayerManager } from './LayerManager';
import { validateConfig, type SceneConfig, type Quality } from '../config/types';
import { WindField } from '../systems/WindField';
import { LeafSimulation } from '../systems/LeafSimulation';
import { LeafSystem } from '../systems/LeafSystem';
import { WaterSystem } from '../systems/WaterSystem';
import { BranchSystem } from '../systems/BranchSystem';
import { ReedSystem } from '../systems/ReedSystem';
import { QualityManager } from '../systems/QualityManager';
import { NearCanopySystem } from '../systems/NearCanopySystem';
import { SurfaceLeafSystem } from '../systems/SurfaceLeafSystem';
export class SceneManager {
  readonly app=new Application();readonly assets=new AssetManager();readonly quality=new QualityManager();
  config!:SceneConfig;layers!:LayerManager;wind!:WindField;simulation!:LeafSimulation;leaves!:LeafSystem;water!:WaterSystem;branches!:BranchSystem;reeds!:ReedSystem;
  nearCanopy?:NearCanopySystem;surfaceLeaves?:SurfaceLeafSystem;
  timeScale=1;
  private hostActive=true;
  private accumulator=0;private observer?:ResizeObserver;private debugGraphic=new Graphics();private visibility=()=>{this.quality.hidden=document.hidden||!this.hostActive;this.sync();};
  private contextLost=(e:Event)=>{e.preventDefault();this.quality.paused=true;this.sync();this.onNotice('WebGL 上下文丢失，恢复后可继续；若持续黑屏请刷新。');};
  private contextRestored=()=>{this.onNotice('WebGL 已恢复，点击「继续」恢复动画。');this.render();};
  onChange=()=>{};onNotice=(_text:string)=>{};
  async init(host:HTMLElement,frame:HTMLElement,viewport:HTMLElement){
    const response=await fetch(import.meta.env.BASE_URL+'config/autumn_day.scene.json');if(!response.ok)throw new Error('场景配置加载失败');
    const c:unknown=await response.json();validateConfig(c);this.config=c;
    await this.app.init({width:480,height:270,resolution:3,antialias:false,roundPixels:true,preference:'webgl',autoStart:false,background:0x294c50,powerPreference:'low-power'});
    this.app.canvas.setAttribute('aria-label','秋日像素湖畔：远山、枫林、落叶与微风');host.append(this.app.canvas);
    this.app.canvas.addEventListener('webglcontextlost',this.contextLost);this.app.canvas.addEventListener('webglcontextrestored',this.contextRestored);
    await this.assets.load(c);
    this.layers=new LayerManager(this.app.stage,c);
    for(const layer of c.layers)if(layer.asset&&layer.id!=='reflection'){
      const sprite=new Sprite(this.assets.get(layer.asset));sprite.width=480;sprite.height=270;
      this.layers.get(layer.id).addChild(sprite);
    }
    // Place the large resting leaves along the two near banks, as in the reference.
    const foregroundLeaves = [
      { x: 166, y: 252, texture: 0, size: 13, angle: -.07 },
      { x: 218, y: 256, texture: 1, size: 15, angle: .06 },
      { x: 202, y: 261, texture: 3, size: 7, angle: .13 },
      { x: 208, y: 269, texture: 2, size: 12, angle: -.06 },
      { x: 350, y: 267, texture: 2, size: 13, angle: .05 },
      { x: 379, y: 249, texture: 3, size: 8, angle: -.10 },
      { x: 393, y: 246, texture: 0, size: 12, angle: .08 },
    ];
    const foregroundWater = this.layers.layers.get('surface_leaves_near') ?? this.layers.get('floating_leaves');
    for (const placement of foregroundLeaves) {
      const leaf = new Sprite(this.assets.leaf(c, placement.texture));
      leaf.anchor.set(.5);
      leaf.position.set(placement.x, placement.y);
      leaf.setSize(placement.size, placement.size * .35);
      leaf.rotation = placement.angle;
      foregroundWater.addChild(leaf);
    }
    for(const id of ['reflection','ripples','floating_leaves','surface_leaves_far','surface_leaves_near']){
      if(!this.layers.layers.has(id))continue;
      const mask=new Graphics().poly(c.water.polygon.flat()).fill(0xffffff);this.app.stage.addChild(mask);this.layers.get(id).mask=mask;
    }
    this.wind=new WindField(c.wind);
    this.water=new WaterSystem(c,this.wind,this.assets.get(c.layers.find(l=>l.id==='reflection')!.asset!),this.layers.get('reflection'),this.layers.get('ripples'));
    this.branches=new BranchSystem(this.layers.get('branches'),this.assets,c,this.wind);
    if(c.assets.nearCanopy&&this.layers.layers.has('near_canopy'))this.nearCanopy=new NearCanopySystem(this.layers.get('near_canopy'),this.assets,c,this.wind);
    if(c.leaves.surfaceCount)this.surfaceLeaves=new SurfaceLeafSystem(this.layers,this.assets,c,this.wind);
    this.reeds=new ReedSystem(this.layers.get('reeds'),this.assets,c,this.wind);
    this.simulation=new LeafSimulation(c,this.wind,(x,y)=>this.water.add(x,y),Math.random,()=>this.branches.detach());
    this.leaves=new LeafSystem(this.simulation,this.layers,this.assets,c);
    this.simulation.seed();this.branches.update(0);this.reeds.update(0);this.leaves.render();this.water.update(0);
    this.debugGraphic.zIndex=90;this.app.stage.addChild(this.debugGraphic);
    const size=()=>{const width=Math.min(frame.clientWidth,frame.clientHeight*16/9);viewport.style.width=width+'px';viewport.style.height=width*9/16+'px';};
    this.observer=new ResizeObserver(size);this.observer.observe(frame);size();
    document.addEventListener('visibilitychange',this.visibility);
    this.quality.hidden=document.hidden;
    this.quality.quality=matchMedia('(prefers-reduced-motion: reduce)').matches?'static':c.render.quality;
    if(this.quality.quality==='static'){this.simulation.clear();this.leaves.render();this.water.clear();}
    this.app.ticker.add(ticker=>{
      if(!this.quality.running)return;
      this.accumulator+=Math.min(ticker.deltaMS/1000,.05)*this.timeScale;
      while(this.accumulator>=1/60){
        this.simulation.step(1/60);this.surfaceLeaves?.update(1/60);this.water.update(1/60);this.accumulator-=1/60;
      }
      this.branches.update(this.simulation.time);this.nearCanopy?.update(this.simulation.time);this.reeds.update(this.simulation.time);this.leaves.render();
    });
    this.sync();this.render();
  }
  render(){this.app.render();}
  sync(){
    this.app.ticker.maxFPS=this.quality.fps;this.accumulator=0;
    this.quality.running?this.app.start():this.app.stop();this.render();this.onChange();
  }
  setQuality(q:Quality){
    this.quality.quality=q;
    if(q==='static'){this.simulation.clear();this.water.clear();this.leaves.render();}
    this.simulation.count=Math.round(this.config.leaves.count*(q==='full'?1.6:1));this.sync();
  }
  togglePause(){this.setPaused(!this.quality.paused);}
  setHostActive(active:boolean){if(active===this.hostActive)return;this.hostActive=active;this.visibility();}
  setPaused(p:boolean){this.quality.paused=p;this.sync();}
  setParameter(name:'wind'|'count'|'water',value:number){
    if(!Number.isFinite(value))return;
    if(name==='wind')this.wind.config.baseX=Math.max(-1.5,Math.min(1.5,value));
    if(name==='count'){this.config.leaves.count=Math.max(0,Math.min(24,Math.round(value)));this.simulation.count=Math.round(this.config.leaves.count*(this.quality.quality==='full'?1.6:1));
      // Keep at most two generations after reducing the density slider.
      let remaining=this.simulation.count*2;for(const l of this.simulation.leaves)if(l.state!=='RECYCLED'&&--remaining<0)this.simulation.recycle(l);this.leaves.render();
    }
    if(name==='water'){this.water.intensity=Math.max(0,Math.min(1.5,value));this.config.water.intensity=this.water.intensity;this.water.update(0);}
    this.render();this.onChange();
  }
  showMasks(on:boolean){this.debugGraphic.clear();if(on){this.debugGraphic.poly(this.config.water.polygon.flat()).fill({color:0x5fe3ca,alpha:.25});const a=this.config.lyricsSafeArea;this.debugGraphic.rect(a.x,a.y,a.width,a.height).stroke({width:1,color:0xf5d68a});}this.render();}
  demoLanding(){
    if(this.quality.quality==='static')this.setQuality('light');this.setPaused(false);
    this.simulation.spawn({x:284,y:242,texture:2},244);this.onNotice(`叶片即将触水并产生波纹；漂浮 ${this.config.leaves.floatingLifetimeSec} 秒后逐渐淡出。`);
  }
  exportConfig(){const c=structuredClone(this.config);c.render.quality=this.quality.quality;return JSON.stringify(c,null,2);}
  async destroy(){document.removeEventListener('visibilitychange',this.visibility);this.observer?.disconnect();this.app.canvas.removeEventListener('webglcontextlost',this.contextLost);this.app.canvas.removeEventListener('webglcontextrestored',this.contextRestored);this.water?.destroy();this.app.destroy(true,{children:true});await this.assets.destroy();}
}
