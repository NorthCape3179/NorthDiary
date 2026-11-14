import { Container, Mesh, PlaneGeometry } from 'pixi.js';
import type { SceneConfig } from '../config/types';
import { AssetManager } from '../engine/AssetManager';
import { WindField } from './WindField';

/** Close, dense framing foliage; independent of the thinner hanging branches. */
export class NearCanopySystem {
  private crowns:{
    node:Container;phase:number;rotation:number;mesh:Mesh;
    rest:Float32Array;width:number;height:number;anchorX:number;
  }[]=[];
  constructor(parent:Container,assets:AssetManager,c:SceneConfig,private wind:WindField){
    if(!c.assets.nearCanopy)return;
    for(const [i,p] of (c.nearCanopies??[]).entries()){
      const root=new Container();
      const anchorX=p.x>240?p.width:0;
      root.scale.x=p.mirror?-1:1;
      root.pivot.set(anchorX,0);
      root.position.set(p.x+anchorX*root.scale.x,p.y);
      const leaves=new Mesh({
        texture:assets.get(p.asset??c.assets.nearCanopy),
        geometry:new PlaneGeometry({width:p.width,height:p.height,verticesX:13,verticesY:9}),
      });
      leaves.tint=0xead8ce;root.addChild(leaves);parent.addChild(root);
      this.crowns.push({node:root,phase:i*2.1,rotation:p.rotation??0,mesh:leaves,
        rest:leaves.geometry.positions.slice(),width:p.width,height:p.height,anchorX});
    }
    this.update(0);
  }
  update(t:number){
    for(const c of this.crowns){
      const breeze=this.wind.sample(t,c.node.x,c.node.y);
      c.node.rotation=c.rotation+Math.sin(t*.48+c.phase)*.006+breeze*.003;
      const positions=c.mesh.geometry.positions;
      for(let i=0;i<positions.length;i+=2){
        const x=c.rest[i],y=c.rest[i+1];
        const u=x/c.width,v=y/c.height;
        // Fixed branch roots, with more flexibility at the hanging leaf tips.
        const reach=Math.abs(x-c.anchorX)/c.width;
        const flexibility=Math.pow(.35*reach+.65*v,1.4);
        const flutter=Math.sin(t*2.1+u*12+v*5+c.phase)*.18;
        positions[i]=x+flexibility*(Math.sin(t*.83+u*5+v*2+c.phase)*.8+breeze*.6+flutter);
        positions[i+1]=y+flexibility*(Math.sin(t*.67+u*7+c.phase)*.85+Math.sin(t*1.7+v*9+c.phase)*.22);
      }
      c.mesh.geometry.getBuffer('aPosition').update();
    }
  }
}
