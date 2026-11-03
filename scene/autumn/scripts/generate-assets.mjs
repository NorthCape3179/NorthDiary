/** Deterministic, editable vector pixel-art TEST assets. No remote art/CDN. */
import { mkdirSync, writeFileSync } from 'node:fs';
const root = new URL('../public/assets/autumn_day/', import.meta.url);
mkdirSync(root, { recursive: true });
let seed=31879;
const rand=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/4294967296;};
const pick=a=>a[Math.floor(rand()*a.length)];
const r=(x,y,w,h,c,o=1)=>`<rect x="${Math.round(x)}" y="${Math.round(y)}" width="${Math.round(w)}" height="${Math.round(h)}" fill="${c}" opacity="${o}"/>`;
const p=(points,c,o=1)=>`<polygon points="${points.map(a=>a.map(Math.round).join(',')).join(' ')}" fill="${c}" opacity="${o}"/>`;
const svg=(name,body,w=480,h=270)=>writeFileSync(new URL(name+'.svg',root),`<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" shape-rendering="crispEdges">${body}</svg>`);
let sky=r(0,0,480,270,'#a8bfc0')+r(0,64,480,70,'#b2c6c3')+r(0,108,480,60,'#c1cec3');
for(const [x,y,w] of [[60,32,54],[220,24,38],[328,45,65],[148,63,28]]){
 sky+=r(x,y,w,3,'#d2d9cb',.65)+r(x+8,y-3,w*.55,3,'#d2d9cb',.65)+r(x-7,y+3,w+22,2,'#c1cfca',.75);
}
svg('sky',sky);
const far=[[0,99],[22,84],[39,90],[66,67],[84,74],[109,52],[126,59],[143,77],[158,69],[188,89],[211,75],[242,91],[268,73],[294,80],[315,62],[331,68],[350,91],[371,79],[403,95],[428,78],[454,86],[480,68],[480,176],[0,176]];
svg('far_mountains',p(far,'#829b9b')+p([[66,67],[84,74],[109,52],[101,77],[86,85],[81,97],[49,120]],'#92a7a4')+p([[315,62],[331,68],[350,91],[336,90],[330,82],[319,91],[309,84]],'#91a7a4')+p([[0,119],[55,110],[89,116],[133,104],[165,119],[204,106],[239,119],[285,99],[317,118],[361,109],[406,118],[448,102],[480,111],[480,170],[0,170]],'#7c9694'));
svg('near_mountains',p([[0,115],[30,108],[63,119],[95,108],[122,120],[153,98],[170,108],[194,113],[218,128],[244,120],[265,128],[301,107],[326,119],[351,102],[380,111],[410,120],[439,105],[464,110],[480,103],[480,175],[0,175]],'#607f7d')+p([[0,136],[37,128],[67,137],[111,126],[149,135],[181,123],[219,140],[263,132],[303,137],[340,125],[380,139],[424,130],[456,137],[480,130],[480,178],[0,178]],'#4d7069'));
const palettes=[['#74513a','#a87439','#c69a4b','#d5b265'],['#6e4936','#986039','#b98943','#cfa455'],['#69443b','#934f38','#b2653c','#c38149'],['#523c35','#783f32','#9d4c36','#b36540'],['#4e5843','#747746','#a39a50','#c2b16b']];
function canopy(x,y,w,h,cs){
 let s=''; const outline=[[0,.4],[.12,.4],[.12,.2],[.27,.2],[.27,.06],[.53,.06],[.53,0],[.7,0],[.7,.16],[.85,.16],[.85,.36],[1,.36],[1,.78],[.87,.78],[.87,.92],[.64,.92],[.64,1],[.26,1],[.26,.87],[.07,.87],[.07,.65],[0,.65]];
 s+=p(outline.map(([a,b])=>[x+a*w,y+b*h]),cs[0]);
 s+=p(outline.map(([a,b])=>[x+1+a*(w-3),y+b*(h-4)]),cs[1]);
 // Connected broad light clusters, not independent noise dots.
 for(let k=0;k<6;k++){let a=x+3+rand()*(w*.6),b=y+2+rand()*(h*.46);s+=r(a,b,4+rand()*7,2+rand()*4,k<3?cs[2]:cs[3]);s+=r(a-2,b+2,5+rand()*5,2,cs[2]);}
 return s;
}
let forest='';
for(let row=0;row<3;row++){
 let x=-10;while(x<490){let w=14+rand()*18,h=18+rand()*22,y=125+row*9-h*.3;let cs=pick(palettes);forest+=r(x+w*.51,y+h-3,2,12,'#4e5342');forest+=canopy(x,y,w,h,cs);x+=w*.72;}
}
forest+=p([[0,163],[51,164],[84,162],[120,166],[172,164],[213,167],[268,165],[304,163],[361,166],[405,162],[446,164],[480,161],[480,174],[0,174]],'#4b5b47');
forest+=r(0,169,480,2,'#9c9564',.65)+r(0,172,480,1,'#c4b47e',.45);
svg('forest',forest);
let lake=r(0,166,480,104,'#3b696a')+r(0,175,480,18,'#527c77')+r(0,193,480,19,'#487572')+r(0,212,480,24,'#3f6d6d')+r(0,236,480,34,'#355f63');
for(let i=0;i<115;i++){let y=173+rand()*96,x=rand()*480;lake+=r(x,y,3+rand()*(y>210?19:10),1,pick(['#7c9b8b','#76968a','#264f58']),.14+rand()*.16);}
svg('lake',lake);
let reflection='';for(let i=0;i<90;i++){let x=rand()*480,y=174+rand()*25;reflection+=r(x,y,4+rand()*14,1+rand()*2,pick(['#b09758','#9e8245','#98734a','#374f44']),.25*(1-(y-174)/30));}
svg('reflection',reflection);
const left=[[0,210],[14,218],[21,231],[44,237],[60,245],[87,249],[106,260],[141,264],[155,270],[0,270]],right=[[480,213],[468,221],[461,236],[443,243],[429,245],[420,252],[402,257],[376,263],[361,270],[480,270]];
let shore=p(left,'#374d41')+p(right,'#374d41')+p([[0,230],[22,238],[41,242],[46,250],[80,258],[109,270],[0,270]],'#55583e')+p([[480,238],[453,246],[436,257],[404,270],[480,270]],'#55583e');
const rocks=[[27,239,28,13],[56,253,32,14],[8,222,18,13],[103,267,27,12],[438,246,27,13],[465,226,23,12],[412,263,30,13]];
for(const [x,y,w,h] of rocks){shore+=p([[x,y+h],[x-2,y+4],[x+5,y-3],[x+w*.55,y-5],[x+w,y+3],[x+w+2,y+h]],'#454e46');shore+=p([[x-2,y+4],[x+5,y-3],[x+w*.55,y-5],[x+w-1,y+3],[x+w*.6,y+7],[x+4,y+6]],'#8e8b6c');shore+=p([[x+4,y+6],[x+w*.6,y+7],[x+w-1,y+3],[x+w+2,y+h],[x+7,y+h]],'#696f59');shore+=r(x+6,y-2,8,2,'#aaa184');}
for(let i=0;i<40;i++){let side=rand()<.5,x=side?rand()*92:403+rand()*77,y=252+rand()*18;shore+=r(x,y,2+rand()*4,1,pick(['#9b8651','#bda260','#7b783f']));}
svg('shore',shore);
svg('foreground_mask',p(left,'white')+p(right,'white'));
const water=[[0,174],[480,174],[480,213],[468,221],[461,236],[443,243],[429,245],[420,252],[402,257],[376,263],[361,270],[155,270],[141,264],[106,260],[87,249],[60,245],[44,237],[21,231],[14,218],[0,210]];
svg('water_mask',p(water,'white'));
svg('branch',p([[0,5],[33,10],[58,19],[82,23],[101,35],[126,39],[128,42],[100,39],[80,28],[56,25],[29,15],[0,13]],'#514737')+p([[31,13],[47,3],[68,0],[70,2],[48,7],[38,16]],'#514737')+p([[73,25],[89,13],[113,8],[112,11],[92,17],[81,28]],'#514737')+p([[8,5],[33,11],[58,20],[80,24],[98,34],[57,23],[29,13],[0,8]],'#766143'),140,60);
svg('twig',p([[0,0],[16,6],[29,9],[44,19],[43,21],[28,12],[15,9],[0,2]],'#61503c')+p([[15,7],[24,0],[26,0],[19,9]],'#61503c'),50,30);
for(let i=0;i<5;i++)svg('cluster'+i,canopy(0,0,30,19,palettes[i])+canopy(20,10,23,17,palettes[(i+1)%5]),46,30);
for(let i=0;i<10;i++){
 const cs=palettes[i%5],flip=i%2; const shape=flip?[[5,0],[7,3],[10,2],[9,5],[12,6],[8,8],[6,10],[4,8],[1,7],[3,5],[2,2],[5,3]]:[[6,0],[7,3],[10,1],[9,4],[12,4],[10,7],[7,8],[6,10],[4,8],[1,8],[2,5],[0,3],[4,4]];
 svg('leaf'+i,p(shape,cs[2])+p([[6,3],[7,6],[5,9],[3,7]],cs[1])+r(5,8,1,4,'#675038'),12,12);
}
// Stem and head remain separate, each rooted at its own pivot.
svg('reed_stem',r(3,0,1,22,'#7f8958')+r(4,19,1,5,'#656f48')+p([[3,11],[0,6],[1,10],[3,15]],'#92915d')+p([[4,17],[7,11],[6,16],[4,20]],'#586e4b'),8,24);
svg('reed_head',r(2,0,3,9,'#a18b58')+r(3,0,2,7,'#b5a16b')+r(3,8,1,4,'#7e8050'),8,12);
const config={id:'autumn_day',version:1,logicalSize:{width:480,height:270},assetRoot:'assets/autumn_day/',artStatus:'程序化测试素材 · 可替换',render:{targetFps:30,quality:'light'},layers:[
 ['sky',0,'sky.svg'],['far_mountains',10,'far_mountains.svg'],['near_mountains',20,'near_mountains.svg'],['forest',30,'forest.svg'],['lake',35,'lake.svg'],['reflection',40,'reflection.svg'],['ripples',45],['floating_leaves',47],['falling_leaves_back',49],['shore',50,'shore.svg'],['reeds',60],['branches',70],['falling_leaves_front',80]
].map(([id,z,asset])=>({id,z,...asset?{asset}:{dynamic:true}})),assets:{branch:'branch.svg',twig:'twig.svg',clusters:Array.from({length:5},(_,i)=>`cluster${i}.svg`),leaves:Array.from({length:10},(_,i)=>`leaf${i}.svg`),reedStem:'reed_stem.svg',reedHead:'reed_head.svg',waterMask:'water_mask.svg',foregroundMask:'foreground_mask.svg'},water:{polygon:water,flowX:.6,flowY:.1,rippleLifetimeSec:2.4,rippleMaxRadius:12,maxRipples:24,intensity:.65},wind:{baseX:.35,gustPeriodSec:18,gustStrength:.65},leaves:{count:12,maxPool:96,fallSpeedMin:4,fallSpeedMax:12,floatingLifetimeSec:32},branches:[{x:-8,y:0,mirror:false},{x:490,y:-3,mirror:true}],reeds:[{x:17,y:239,height:40},{x:36,y:248,height:31},{x:66,y:260,height:35},{x:448,y:252,height:36},{x:473,y:239,height:44},{x:414,y:269,height:27}],lyricsSafeArea:{x:120,y:54,width:240,height:120}};
writeFileSync(new URL('../public/config/autumn_day.scene.json',import.meta.url),JSON.stringify(config,null,2));
console.log('Generated 29 independently replaceable SVG test assets and scene configuration.');
