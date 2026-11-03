import { Sprite } from 'pixi.js';
import type { SceneConfig } from '../config/types';
import { AssetManager } from '../engine/AssetManager';
import { LayerManager } from '../engine/LayerManager';
import { inPolygon } from './LeafSimulation';
import { WindField } from './WindField';

interface RestingLeaf {sprite:Sprite;near:boolean;x:number;y:number;phase:number;angle:number;age:number;life:number;scale:number}

/** Already-resting leaves keep both water depths populated from the first frame. */
export class SurfaceLeafSystem {
  private leaves:RestingLeaf[]=[];private time=0;
  get count(){return this.leaves.length;}
  constructor(private layers:LayerManager,private assets:AssetManager,private c:SceneConfig,private wind:WindField){
    const count=Math.round(c.leaves.surfaceCount??0);
    for(let i=0;i<count;i++){
      const sprite=new Sprite(assets.leaf(c,i));sprite.anchor.set(.5);
      const leaf:RestingLeaf={sprite,near:i>=Math.round(count*.38),x:0,y:0,phase:0,angle:0,age:0,life:0,scale:1};
      layers.get(leaf.near?'surface_leaves_near':'surface_leaves_far').addChild(sprite);
      this.reset(leaf,true);this.leaves.push(leaf);
    }
    this.update(0);
  }
  private reset(l:RestingLeaf,initial=false){
    const r=Math.random;l.phase=r()*Math.PI*2;l.angle=(r()-.5)*1.3;
    l.life=55+r()*30;l.age=initial?8+r()*25:0;
    // Bias the nearest leaves toward the two shorelines; leave the lyric center quiet.
    let x=240,y=260;
    for(let tries=0;tries<60;tries++){
      if(l.near){y=238+r()*29;x=r()<.58?105+r()*120:300+r()*125;}
      else{y=166+r()*27;x=35+r()*410;}
      if(inPolygon(x,y,this.c.water.polygon))break;
    }
    l.x=x;l.y=y;l.scale=l.near?.62+r()*.34:.29+r()*.17;
    l.sprite.texture=this.assets.leaf(this.c,Math.floor(r()*this.c.assets.leaves.length));
  }
  update(dt:number){
    this.time+=dt;
    for(const l of this.leaves){
      l.age+=dt;const w=this.wind.sample(this.time,l.x,l.y);
      l.x+=(.11+w*.13)*dt;l.y+=Math.sin(this.time*.2+l.phase)*.025*dt;
      if(l.age>=l.life||!inPolygon(l.x,l.y,this.c.water.polygon))this.reset(l);
      l.sprite.position.set(l.x,l.y+Math.sin(this.time*.6+l.phase)*.16);
      l.sprite.rotation=l.angle*.22+Math.sin(this.time*.35+l.phase)*.025;
      l.sprite.setSize(12*l.scale, 4.8*l.scale);
      l.sprite.alpha=Math.min(1,l.age/2,Math.max(0,(l.life-l.age)/5))*(l.near?.98:.78);
    }
  }
}
