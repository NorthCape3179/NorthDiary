import { Sprite } from 'pixi.js';
import { AssetManager } from '../engine/AssetManager';
import { LayerManager } from '../engine/LayerManager';
import { LeafSimulation } from './LeafSimulation';
import type { SceneConfig } from '../config/types';
export class LeafSystem {
  readonly sprites:Sprite[];
  constructor(public simulation:LeafSimulation,private layers:LayerManager,private assets:AssetManager,private config:SceneConfig){
    this.sprites=simulation.leaves.map(()=>{const s=new Sprite(assets.get(config.assets.leaves[0]));s.anchor.set(.5);s.visible=false;layers.get('falling_leaves_front').addChild(s);return s;});
  }
  render(){for(const l of this.simulation.leaves){
    const s=this.sprites[l.id];s.visible=l.state!=='RECYCLED';if(!s.visible)continue;
    const parent=this.layers.get(l.wet?'floating_leaves':l.front?'falling_leaves_front':'falling_leaves_back');if(s.parent!==parent)parent.addChild(s);
    s.texture=this.assets.leaf(this.config,l.texture);s.position.set(Math.round(l.x),Math.round(l.y));s.rotation=l.wet?Math.sin(l.angle)*.15:l.angle;s.alpha=l.alpha;
    const flutter=l.wet?.42:Math.max(.3,Math.abs(Math.cos(this.simulation.time*1.9+l.phase)));
    s.setSize(12*l.scale,12*l.scale*flutter);
  }}
}
