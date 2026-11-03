import { Container } from 'pixi.js';
import type { SceneConfig } from '../config/types';
export class LayerManager {
  readonly layers=new Map<string,Container>();
  constructor(stage:Container,config:SceneConfig){
    stage.sortableChildren=true;
    for(const item of [...config.layers].sort((a,b)=>a.z-b.z)){
      const c=new Container({label:item.id});c.zIndex=item.z;this.layers.set(item.id,c);stage.addChild(c);
    }
  }
  get(id:string){const c=this.layers.get(id);if(!c)throw new Error('缺少图层 '+id);return c;}
  visible(id:string,value:boolean){this.get(id).visible=value;}
}
