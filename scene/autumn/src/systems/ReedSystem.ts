import { Container, Sprite } from 'pixi.js';
import type { SceneConfig } from '../config/types';
import { AssetManager } from '../engine/AssetManager';
import { WindField } from './WindField';
export class ReedSystem {
  private plants:{root:Container;upper:Container;phase:number;direction:number}[]=[];
  constructor(parent:Container,assets:AssetManager,c:SceneConfig,private wind:WindField){
    for(const [j,clump] of c.reeds.entries())for(let i=0;i<5;i++){
      const root=new Container();root.position.set(clump.x+(i-2)*3,clump.y+Math.abs(i-2));parent.addChild(root);
      root.scale.set((clump.height/48)*(1-Math.abs(i-2)*.08));
      const bottom=new Sprite(assets.get(c.assets.reedStem));bottom.position.set(-4,-24);root.addChild(bottom);
      const upper=new Container();upper.position.set(0,-23);root.addChild(upper);
      const stem=new Sprite(assets.get(c.assets.reedStem));stem.position.set(-4,-24);upper.addChild(stem);
      const head=new Sprite(assets.get(c.assets.reedHead));head.position.set(-4,-33);upper.addChild(head);
      const direction=(i-2)*.07;this.plants.push({root,upper,phase:j*.8+i*.37,direction});
    }
  }
  update(t:number){for(const p of this.plants){const w=this.wind.sample(t,p.root.x,p.root.y);p.root.rotation=p.direction+w*.025+Math.sin(t*.8+p.phase)*.008;p.upper.rotation=w*.035+Math.sin(t*.9+p.phase)*.022;}}
}
