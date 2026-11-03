export type Quality = 'static' | 'light' | 'full';
export type Point = [number, number];
export interface SceneConfig {
  id: string; version: number; logicalSize: {width:number;height:number}; assetRoot:string; artStatus:string;
  render: {targetFps:number;quality:Quality};
  layers: {id:string;z:number;asset?:string;dynamic?:boolean}[];
  assets: {branch:string;twig:string;canopy?:string;nearCanopy?:string;waterLeafAtlas?:string;clusters:string[];leaves:string[];reedStem:string;reedHead:string;waterMask:string;foregroundMask:string};
  wind: {baseX:number;gustPeriodSec:number;gustStrength:number};
  water: {polygon:Point[];flowX:number;flowY:number;rippleLifetimeSec:number;rippleMaxRadius:number;maxRipples:number;intensity:number};
  leaves: {count:number;maxPool:number;fallSpeedMin:number;fallSpeedMax:number;floatingLifetimeSec:number;surfaceCount?:number};
  branches: {x:number;y:number;mirror:boolean;width?:number;height?:number}[];
  nearCanopies?:{x:number;y:number;width:number;height:number;mirror:boolean;rotation?:number;asset?:string}[];
  reeds: {x:number;y:number;height:number}[];
  lyricsSafeArea: {x:number;y:number;width:number;height:number};
}
export const qualities:Quality[]=['static','light','full'];
export function validateConfig(v:unknown): asserts v is SceneConfig {
  const c=v as SceneConfig;
  const fail=(s:string):never=>{throw new Error('场景配置无效：'+s);};
  if(!c||typeof c!=='object'||c.version!==1)fail('version 必须为 1');
  if(c.logicalSize?.width!==480||c.logicalSize?.height!==270)fail('测试版逻辑画布必须是 480×270');
  const number=(n:unknown,min:number,max:number,name:string)=>{if(typeof n!=='number'||!Number.isFinite(n)||n<min||n>max)fail(name);};
  const path=(s:unknown)=>{if(typeof s!=='string'||!s.length||s.includes('..')||s.startsWith('/')||s.includes(':'))fail('资源必须使用工程内相对路径');};
  path(c.assetRoot);
  if(!c.render||!qualities.includes(c.render.quality))fail('quality');
  number(c.render.targetFps,1,60,'targetFps');
  if(!Array.isArray(c.layers))fail('layers');
  const ids=new Set<string>();for(const l of c.layers){if(typeof l.id!=='string'||ids.has(l.id))fail('图层 ID 重复或缺失');ids.add(l.id);number(l.z,-100,1000,'z');if(l.asset)path(l.asset);}
  for(const id of ['sky','far_mountains','near_mountains','forest','lake','reflection','ripples','floating_leaves','falling_leaves_back','shore','reeds','branches','falling_leaves_front'])if(!ids.has(id))fail('缺少图层 '+id);
  if(!c.assets||!Array.isArray(c.assets.leaves)||c.assets.leaves.length<6||!Array.isArray(c.assets.clusters)||c.assets.clusters.length<1)fail('资源清单');
  for(const s of [c.assets.branch,c.assets.twig,c.assets.reedStem,c.assets.reedHead,c.assets.waterMask,c.assets.foregroundMask,...c.assets.clusters,...c.assets.leaves])path(s);
  if(c.assets.canopy)path(c.assets.canopy);
  if(c.assets.nearCanopy)path(c.assets.nearCanopy);
  if(c.assets.waterLeafAtlas)path(c.assets.waterLeafAtlas);
  if(!c.wind||!c.water||!c.leaves)fail('动效参数缺失');
  number(c.wind.baseX,-2,2,'wind.baseX');number(c.wind.gustStrength,0,2,'gustStrength');number(c.wind.gustPeriodSec,1,120,'gustPeriodSec');
  number(c.leaves.count,0,40,'leaves.count');number(c.leaves.maxPool,80,128,'maxPool');number(c.leaves.fallSpeedMin,1,30,'fallSpeedMin');number(c.leaves.fallSpeedMax,c.leaves.fallSpeedMin,40,'fallSpeedMax');number(c.leaves.floatingLifetimeSec,1,120,'floatingLifetimeSec');
  if(c.leaves.surfaceCount!==undefined)number(c.leaves.surfaceCount,0,40,'leaves.surfaceCount');
  number(c.water.intensity,0,2,'water.intensity');number(c.water.maxRipples,1,64,'maxRipples');number(c.water.rippleLifetimeSec,.1,10,'rippleLifetimeSec');number(c.water.rippleMaxRadius,1,40,'rippleMaxRadius');number(c.water.flowX,-5,5,'flowX');number(c.water.flowY,-5,5,'flowY');
  if(!Array.isArray(c.water.polygon)||c.water.polygon.length<3)fail('water.polygon');
  for(const pt of c.water.polygon){if(!Array.isArray(pt)||pt.length!==2)fail('水域顶点');number(pt[0],0,480,'water.x');number(pt[1],0,270,'water.y');}
  if(!Array.isArray(c.branches)||!Array.isArray(c.reeds))fail('植物布局');
  for(const p of [...c.branches,...c.reeds]){number(p.x,-100,580,'plant.x');number(p.y,-100,370,'plant.y');}
  for(const b of c.branches){if(typeof b.mirror!=='boolean')fail('branch.mirror');if(b.width!==undefined)number(b.width,20,300,'branch.width');if(b.height!==undefined)number(b.height,10,160,'branch.height');}
  if(c.nearCanopies!==undefined){
    if(!Array.isArray(c.nearCanopies)||c.nearCanopies.length>8)fail('nearCanopies');
    for(const p of c.nearCanopies){number(p.x,-100,580,'nearCanopy.x');number(p.y,-100,100,'nearCanopy.y');number(p.width,20,300,'nearCanopy.width');number(p.height,10,160,'nearCanopy.height');if(typeof p.mirror!=='boolean')fail('nearCanopy.mirror');if(p.rotation!==undefined)number(p.rotation,-Math.PI,Math.PI,'nearCanopy.rotation');if(p.asset)path(p.asset);}
    if(c.nearCanopies.length&&(!c.assets.nearCanopy||!ids.has('near_canopy')))fail('nearCanopy layer/asset');
  }
  if(c.leaves.surfaceCount)for(const id of ['surface_leaves_far','surface_leaves_near'])if(!ids.has(id))fail('缺少图层 '+id);
  for(const r of c.reeds)number(r.height,8,70,'reed.height');
  if(!c.lyricsSafeArea)fail('lyricsSafeArea');
  for(const k of ['x','y','width','height'] as const)number(c.lyricsSafeArea[k],0,480,'lyrics.'+k);
}
