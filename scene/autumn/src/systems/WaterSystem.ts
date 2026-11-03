import { Container, Graphics, Rectangle, Sprite, Texture } from 'pixi.js';
import type { SceneConfig } from '../config/types';
import { WindField } from './WindField';
export interface Ripple {active:boolean;x:number;y:number;age:number}
export class WaterSystem {
  readonly rings:Ripple[];private graphic=new Graphics();private strips:Sprite[]=[];private subtextures:Texture[]=[];
  private time=0;intensity:number;
  constructor(private config:SceneConfig,private wind:WindField,reflection:Texture,reflectionLayer:Container,rippleLayer:Container){
    this.intensity=config.water.intensity;
    this.rings=Array.from({length:config.water.maxRipples},()=>({active:false,x:0,y:0,age:0}));
    rippleLayer.addChild(this.graphic);
    // Pixel-row displacement fallback: no whole-scene filter or smooth sampling.
    const scaleX=reflection.width/480,scaleY=reflection.height/270;
    for(let y=146;y<270;y+=2){
      const t=new Texture({source:reflection.source,frame:new Rectangle(0,y*scaleY,480*scaleX,2*scaleY)});this.subtextures.push(t);
      const s=new Sprite(t);s.y=y;s.width=480;s.height=2;s.alpha=.85;this.strips.push(s);reflectionLayer.addChild(s);
    }
  }
  add(x:number,y:number){const r=this.rings.find(r=>!r.active)??this.rings.reduce((a,b)=>a.age>b.age?a:b);Object.assign(r,{active:true,x,y,age:0});}
  clear(){for(const r of this.rings)r.active=false;this.graphic.clear();}
  update(dt:number){
    this.time+=dt;const t=this.time;
    const strength = Math.min(2, this.intensity / .45);
    const breeze = this.wind.sample(t) * .25;
    for (const strip of this.strips) {
      const depth = (strip.y - 146) / 124;
      const swell = Math.sin(t * .85 - depth * 12);
      const shimmer = Math.sin(t * 1.35 + depth * 27);
      const amplitude = .06 + 2.1 * depth * depth;
      strip.x = strength * amplitude * (swell + .22 * shimmer + breeze);
    }
    this.graphic.clear();
    for(const r of this.rings){
      if(!r.active)continue;r.age+=dt;
      const f=r.age/this.config.water.rippleLifetimeSec;
      if(f>=1){r.active=false;continue;}
      // Two slightly staggered, perspective-flattened impact rings. Water mask
      // and the higher shore layer keep the effect off rocks and reeds.
      for(let wave=0;wave<2;wave++){
        const progress=(r.age-wave*.20)/this.config.water.rippleLifetimeSec;
        if(progress<0||progress>=1)continue;
        const radius=.8+Math.sqrt(progress)*this.config.water.rippleMaxRadius;
        const alpha=Math.pow(1-progress,1.25)*(wave?.40:.68)*Math.min(1,this.intensity*1.65);
        for(let i=0;i<48;i++){
          if(i%12===0||i%12===1)continue;
          const a=i/48*Math.PI*2,x=Math.round(r.x+Math.cos(a)*radius),y=Math.round(r.y+Math.sin(a)*radius*.28);
          this.graphic.rect(x,y,.8,.65).fill({color:0xd5dfcc,alpha});
        }
      }
    }
    // Sparse short glints move slowly with the same field.
    for(let i=0;i<22;i++){
      const phase = t * .55 + i * 2.4;
      const y = 180 + (i * 17) % 82;
      const depth = (y - 146) / 124;
      const perspective = .12 + .88 * depth * depth;
      const alpha = Math.min(.28, (.04 + .13 * Math.pow((1 + Math.sin(phase)) / 2, 2)) * strength * perspective);
      const x = (i * 73) % 480 + Math.sin(phase * .5) * 4 * perspective;
      this.graphic.rect(x, y, (3 + (i % 4) * 3) * (.35 + .65 * depth), .65).fill({color:0xc5d7ce,alpha});
    }
  }
  destroy(){for(const t of this.subtextures)t.destroy(false);}
}
