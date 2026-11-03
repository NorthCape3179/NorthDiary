import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,existsSync} from 'node:fs';
import {validateConfig,type SceneConfig} from '../src/config/types';
import {WindField} from '../src/systems/WindField';
import {LeafSimulation,inPolygon} from '../src/systems/LeafSimulation';
import {QualityManager} from '../src/systems/QualityManager';
import {parseMessage} from '../src/bridge/SceneBridge';
const config=()=>JSON.parse(readFileSync(new URL('../public/config/autumn_day.scene.json',import.meta.url),'utf8')) as SceneConfig;
function rng(){let s=12345;return ()=>{s=(Math.imul(s,1664525)+1013904223)>>>0;return s/4294967296;};}
test('configuration validates; malformed numeric, resource and geometry values fail',()=>{
 validateConfig(config());
 for(const alter of [(c:SceneConfig)=>c.wind.baseX=NaN,(c:SceneConfig)=>c.water.polygon=[],(c:SceneConfig)=>c.layers.push(c.layers[0]),(c:SceneConfig)=>c.assets.branch='../secret',(c:SceneConfig)=>c.assets.leaves=[],(c:SceneConfig)=>c.leaves.maxPool=9999]){const c=config();alter(c);assert.throws(()=>validateConfig(c));}
});
test('all configured art assets are bundled and retain logical pixel sizes',()=>{
 const c=config();const all=[...c.layers.flatMap(l=>l.asset?[l.asset]:[]),...(c.assets.canopy?[c.assets.canopy]:[]),...(c.assets.nearCanopy?[c.assets.nearCanopy]:[]),c.assets.branch,c.assets.twig,c.assets.reedHead,c.assets.reedStem,c.assets.waterMask,c.assets.foregroundMask,...c.assets.leaves,...c.assets.clusters];
 for(const name of all){const file=new URL('../public/'+c.assetRoot+name,import.meta.url);assert.ok(existsSync(file),name);if(name.endsWith('.svg'))assert.match(readFileSync(file,'utf8'),/shape-rendering="crispEdges"/);else{const png=readFileSync(file);assert.equal(png.subarray(1,4).toString(),'PNG');assert.ok(png.readUInt32BE(16)>=480);if(name===c.assets.canopy||name===c.assets.nearCanopy||name==='shore-v2.png')assert.equal(png[25],6,'foreground PNG must retain alpha');}}
});
test('wind remains continuous including gusts and wind direction is coherent',()=>{
 const wind=new WindField(config().wind);for(let t=0;t<360;t+=.02){assert.ok(Math.abs(wind.sample(t+.001)-wind.sample(t))<.002);assert.ok(Math.abs(wind.sample(t,0,0)-wind.sample(t,480,270))<.15);}
});
test('water polygon excludes near banks and includes open water',()=>{
 const p=config().water.polygon;assert.equal(inPolygon(240,220,p),true);assert.equal(inPolygon(8,260,p),false);assert.equal(inPolygon(470,260,p),false);assert.equal(inPolygon(240,140,p),false);assert.equal(inPolygon(240,150,p),true);
});
test('one impact creates one ripple; floating leaf stops falling then fades and recycles',()=>{
 const c=config();c.leaves.floatingLifetimeSec=2;let impacts=0;const sim=new LeafSimulation(c,new WindField(c.wind),()=>impacts++,rng());sim.enabled=false;
 const leaf=sim.spawn({x:240,y:199,texture:0},200)!;
 for(let i=0;i<60;i++)sim.step(1/60);
 assert.equal(leaf.state,'FLOATING');assert.equal(leaf.vy,0);assert.equal(impacts,1);assert.ok(Math.abs(leaf.y-200)<1);
 for(let i=0;i<480;i++)sim.step(1/60);
 assert.equal(leaf.state,'RECYCLED');assert.equal(impacts,1);assert.equal(sim.recycled,1);
});
test('land contact does not generate water ripple or force floating state',()=>{
 const c=config();let impacts=0;const sim=new LeafSimulation(c,new WindField(c.wind),()=>impacts++,rng());sim.enabled=false;const l=sim.spawn({x:3,y:253,texture:0},254)!;
 for(let i=0;i<60;i++)sim.step(1/60);assert.equal(l.state,'FADING');assert.equal(l.wet,false);assert.equal(impacts,0);
});
test('fallen leaf makes one impact, remains on water, then fades before recycling',()=>{
 const c=config();let impacts=0;const sim=new LeafSimulation(c,new WindField(c.wind),()=>impacts++,rng());sim.enabled=false;
 const leaf=sim.spawn({x:240,y:199,texture:2},200)!;
 for(let i=0;i<60;i++)sim.step(1/60);
 assert.equal(impacts,1);assert.equal(leaf.state,'FLOATING');
 for(let i=0;i<40*60;i++)sim.step(1/60);
 assert.equal(leaf.state,'FLOATING');assert.equal(leaf.alpha,1);assert.equal(impacts,1);
 for(let i=0;i<6*60;i++)sim.step(1/60);
 assert.equal(leaf.state,'FADING');assert.ok(leaf.alpha>0&&leaf.alpha<1);
 for(let i=0;i<4*60;i++)sim.step(1/60);
 assert.equal(leaf.state,'RECYCLED');assert.equal(impacts,1);
});
test('30-minute fixed-step simulation preserves pool identity and bounded active count',()=>{
 const c=config();const sim=new LeafSimulation(c,new WindField(c.wind),()=>{},rng());const pool=sim.leaves.slice();let peak=0;
 for(let i=0;i<1800*60;i++){sim.step(1/60);peak=Math.max(peak,sim.active);}
 assert.ok(sim.landings>20);assert.ok(sim.recycled>100);assert.ok(peak<=c.leaves.count*2);assert.equal(sim.leaves.length,c.leaves.maxPool);assert.ok(sim.leaves.every((l,i)=>l===pool[i]));
 console.log(JSON.stringify({simulatedSeconds:1800,peak,landings:sim.landings,recycled:sim.recycled,poolSize:pool.length}));
});
test('zero leaves stops spawning; explicit pool overflow is bounded',()=>{
 const c=config();const sim=new LeafSimulation(c,new WindField(c.wind),()=>{},rng());sim.count=0;for(let i=0;i<600;i++)sim.step(1/60);assert.equal(sim.active,0);
 for(let i=0;i<1000;i++)sim.spawn();assert.equal(sim.active,c.leaves.maxPool);assert.equal(sim.spawn(),undefined);sim.clear();assert.equal(sim.active,0);
});
test('quality pause, hidden tab and static mode all stop running',()=>{
 const q=new QualityManager();assert.equal(q.running,true);q.paused=true;assert.equal(q.running,false);q.paused=false;q.hidden=true;assert.equal(q.running,false);q.hidden=false;q.quality='static';assert.equal(q.running,false);q.quality='full';assert.equal(q.running,true);assert.equal(q.fps,60);
});
test('bridge accepts only whitelisted bounded messages, including empty lyrics',()=>{
 assert.deepEqual(parseMessage({type:'pauseScene'}),{type:'pauseScene'});assert.equal(parseMessage({type:'eval',value:'alert(1)'}),null);assert.equal(parseMessage({type:'pauseScene',extra:1}),null);assert.equal(parseMessage({type:'setQuality',value:'ultra'}),null);
 const value={title:'测试',artist:'',durationMs:1000,positionMs:10,playing:false,lines:[]};assert.ok(parseMessage({type:'setPlayback',value}));assert.equal(parseMessage({type:'setPlayback',value:{...value,positionMs:Infinity}}),null);assert.equal(parseMessage({type:'setPlayback',value:{...value,lines:[{timeMs:100,text:'x'},{timeMs:50,text:'y'}]}}),null);assert.equal(parseMessage({type:'setPlayback',value:{...value,lines:Array(501).fill({timeMs:0,text:'x'})}}),null);
});
