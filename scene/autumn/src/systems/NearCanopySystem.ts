import { Container, Sprite } from 'pixi.js';
import type { SceneConfig } from '../config/types';
import { AssetManager } from '../engine/AssetManager';
import { WindField } from './WindField';

/** Close, dense framing foliage; independent of the thinner hanging branches. */
export class NearCanopySystem {
  private crowns:{node:Container;phase:number;rotation:number}[]=[];
  constructor(parent:Container,assets:AssetManager,c:SceneConfig,private wind:WindField){
    if(!c.assets.nearCanopy)return;
    for(const [i,p] of (c.nearCanopies??[]).entries()){
      const root=new Container();root.position.set(p.x,p.y);root.scale.x=p.mirror?-1:1;
      const leaves=new Sprite(assets.get(p.asset??c.assets.nearCanopy));leaves.width=p.width;leaves.height=p.height;
      leaves.tint=0xead8ce;root.addChild(leaves);parent.addChild(root);
      this.crowns.push({node:root,phase:i*2.1,rotation:p.rotation??0});
    }
    this.update(0);
  }
  update(t:number){for(const c of this.crowns)c.node.rotation=c.rotation+Math.sin(t*.32+c.phase)*.002+this.wind.sample(t)*.0015;}
}
