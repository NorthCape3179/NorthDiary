import type { Point, SceneConfig } from '../config/types';
import { WindField } from './WindField';
export type LeafState='RECYCLED'|'FALLING'|'FLOATING'|'FADING';
export interface Leaf { id:number;state:LeafState;x:number;y:number;vx:number;vy:number;angle:number;spin:number;age:number;phase:number;landingY:number;scale:number;alpha:number;texture:number;front:boolean;wet:boolean }
export interface SpawnPoint {x:number;y:number;texture:number}
export function inPolygon(x:number,y:number,poly:Point[]){
  let inside=false;for(let i=0,j=poly.length-1;i<poly.length;j=i++){
    const a=poly[i],b=poly[j];if((a[1]>y)!==(b[1]>y)&&x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0])inside=!inside;
  }return inside;
}
export class LeafSimulation {
  readonly leaves:Leaf[];
  time=0;spawnClock=0;count:number;enabled=true;landings=0;recycled=0;
  constructor(public config:SceneConfig,public wind:WindField,private ripple:(x:number,y:number)=>void,private random:()=>number=Math.random,private source?:()=>SpawnPoint|undefined){
    this.count=config.leaves.count;
    this.leaves=Array.from({length:config.leaves.maxPool},(_,id)=>({id,state:'RECYCLED',x:0,y:0,vx:0,vy:0,angle:0,spin:0,age:0,phase:0,landingY:0,scale:1,alpha:1,texture:0,front:false,wet:false}));
  }
  get active(){return this.leaves.filter(l=>l.state!=='RECYCLED').length;}
  spawn(at?:SpawnPoint,landingY?:number){
    const leaf=this.leaves.find(l=>l.state==='RECYCLED');if(!leaf)return;
    const r=this.random,p=at??this.source?.()??{x:40+r()*400,y:-10,texture:Math.floor(r()*10)};
    Object.assign(leaf,{state:'FALLING',x:p.x,y:p.y,vx:0,vy:this.config.leaves.fallSpeedMin+r()*(this.config.leaves.fallSpeedMax-this.config.leaves.fallSpeedMin),angle:r()*6.28,spin:(r()-.5)*1.3,age:0,phase:r()*6.28,landingY:landingY??181+r()*78,scale:.4+r()*.26,alpha:1,texture:p.texture,front:r()>.45,wet:false});
    return leaf;
  }
  seed(){for(let i=0;i<Math.min(8,this.count);i++)this.spawn({x:70+this.random()*340,y:40+this.random()*120,texture:i%10});}
  recycle(l:Leaf){l.state='RECYCLED';this.recycled++;}
  clear(){for(const l of this.leaves)if(l.state!=='RECYCLED')this.recycle(l);}
  step(dt:number){
    this.time+=dt;
    if(this.enabled&&this.count>0){
      this.spawnClock-=dt;
      if(this.spawnClock<=0){
        const falling=this.leaves.reduce((n,l)=>n+Number(l.state==='FALLING'),0);
        if(falling<this.count&&this.active<Math.min(this.leaves.length,this.count*2))this.spawn();
        this.spawnClock=(.5+this.random()*1.4)*12/this.count;
      }
    }
    for(const l of this.leaves){
      if(l.state==='RECYCLED')continue;
      l.age+=dt;
      const w=this.wind.sample(this.time,l.x,l.y);
      if(l.state==='FALLING'){
        const previousY=l.y;
        l.vx+=(w*9+Math.sin(this.time*1.4+l.phase)*3-l.vx)*Math.min(1,dt*.8);
        l.x+=l.vx*dt;l.y+=(l.vy+Math.sin(this.time*1.8+l.phase)*2.4)*dt;l.angle+=(l.spin+w*.1)*dt;
        // Each leaf has a depth-projected landing plane; geometry still determines water/land.
        if(previousY<l.landingY&&l.y>=l.landingY){
          if(inPolygon(l.x,l.landingY,this.config.water.polygon)){
            l.y=l.landingY;l.state='FLOATING';l.wet=true;l.age=0;l.vy=0;l.vx=0;l.angle*=.15;this.landings++;this.ripple(l.x,l.y);
          }else {l.state='FADING';l.age=0;}
        }
        if(l.x< -20||l.x>500||l.y>285||l.age>100)this.recycle(l);
      }else if(l.state==='FLOATING'){
        l.x+=(this.config.water.flowX+w*.3+Math.sin(this.time*.5+l.phase)*.14)*dt;
        l.y+=(this.config.water.flowY+Math.sin(this.time*.7+l.phase)*.12)*dt;
        l.angle+=Math.sin(this.time*.35+l.phase)*.05*dt;
        if(l.age>=this.config.leaves.floatingLifetimeSec||!inPolygon(l.x,l.y,this.config.water.polygon)){l.state='FADING';l.age=0;}
      }else if(l.state==='FADING'){
        l.alpha=Math.max(0,1-l.age/4);
        if(l.age>=4)this.recycle(l);
      }
    }
  }
}
