import { Container, Sprite } from 'pixi.js';
import { AssetManager } from '../engine/AssetManager';
import type { SceneConfig } from '../config/types';
import { WindField } from './WindField';
interface Twig {node:Container;phase:number;leaves:{sprite:Sprite;texture:number;ready:number}[]}
export class BranchSystem {
  private twigs:Twig[]=[];private canopies:{node:Container;phase:number}[]=[];private time=0;
  constructor(parent:Container,assets:AssetManager,config:SceneConfig,private wind:WindField){
    for(const [bi,b] of config.branches.entries()){
      const root=new Container();root.position.set(b.x,b.y);root.scale.x=b.mirror?-1:1;parent.addChild(root);
      if(config.assets.canopy){
        const canopy=new Sprite(assets.get(config.assets.canopy));canopy.width=b.width??174;canopy.height=b.height??75;
        if(bi===1&&!b.width){canopy.width=151;canopy.height=65;}
        root.addChild(canopy);this.canopies.push({node:root,phase:bi*1.7});
        // Separate small leaves can detach; the painted canopy stays a single editable asset.
        for(let i=0;i<6;i++){
          const node=new Container();node.position.set((43+i*19)*canopy.width/174,(25+i*4)*canopy.height/75);root.addChild(node);
          const idx=(i+bi*3)%10,s=new Sprite(assets.get(config.assets.leaves[idx]));s.anchor.set(.5,.2);s.scale.set(.65);node.addChild(s);
          this.twigs.push({node,phase:i*.8+bi,leaves:[{sprite:s,texture:idx,ready:0}]});
        }
        continue;
      }
      root.addChild(new Sprite(assets.get(config.assets.branch)));
      for(let i=0;i<5;i++){
        const node=new Container();node.position.set(17+i*22,6+i*5);root.addChild(node);
        const twig=new Sprite(assets.get(config.assets.twig));node.addChild(twig);
        const crown=new Sprite(assets.get(config.assets.clusters[(i+bi*2)%5]));crown.position.set(13,8);crown.scale.set(.9);node.addChild(crown);
        const leaves:Twig['leaves']=[];
        for(let j=0;j<2;j++){
          const idx=(i*2+j+bi*3)%10,s=new Sprite(assets.get(config.assets.leaves[idx]));s.anchor.set(.5,.2);s.position.set(22+j*17,24+j*3);s.scale.set(.6);node.addChild(s);leaves.push({sprite:s,texture:idx,ready:0});
        }
        this.twigs.push({node,phase:i*.8+bi,leaves});
      }
    }
  }
  update(t:number){this.time=t;
    for(const c of this.canopies)c.node.rotation=Math.sin(t*.37+c.phase)*.003+this.wind.sample(t)*.002;
    for(const twig of this.twigs){
    const w=this.wind.sample(t,twig.node.x,twig.node.y);twig.node.rotation=w*.025+Math.sin(t*.8+twig.phase)*.012;
    for(const l of twig.leaves){l.sprite.visible=t>=l.ready;l.sprite.rotation=Math.sin(t*1.3+twig.phase)*.08+w*.03;}
  }}
  detach(){
    const slots=this.twigs.flatMap(t=>t.leaves).filter(l=>l.ready<=this.time);
    if(!slots.length)return undefined;
    const l=slots[Math.floor(Math.random()*slots.length)],p=l.sprite.getGlobalPosition();l.ready=this.time+12+Math.random()*15;l.sprite.visible=false;
    return {x:p.x,y:p.y,texture:l.texture};
  }
}
