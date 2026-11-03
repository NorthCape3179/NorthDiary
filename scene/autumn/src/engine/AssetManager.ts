import { Assets, Rectangle, Texture } from 'pixi.js';
import type { SceneConfig } from '../config/types';
export class AssetManager {
  private textures=new Map<string,Texture>();
  private waterLeaves: Texture[] = [];
  private urls:string[]=[];
  async load(c:SceneConfig){
    const files=new Set([...c.layers.flatMap(l=>l.asset?[l.asset]:[]),...(c.assets.canopy?[c.assets.canopy]:[]),...(c.assets.nearCanopy?[c.assets.nearCanopy]:[]),...(c.nearCanopies??[]).flatMap(p=>p.asset?[p.asset]:[]),...(c.assets.waterLeafAtlas?[c.assets.waterLeafAtlas]:[]),c.assets.branch,c.assets.twig,...c.assets.clusters,...c.assets.leaves,c.assets.reedStem,c.assets.reedHead,c.assets.waterMask,c.assets.foregroundMask]);
    await Promise.all([...files].map(async file=>{
      const url=import.meta.env.BASE_URL+c.assetRoot+file;
      try{const texture=await Assets.load<Texture>(url);texture.source.scaleMode='nearest';this.textures.set(file,texture);this.urls.push(url);}
      catch{throw new Error(`无法加载素材：${file}。请检查 public/${c.assetRoot} 下的文件和配置。`);}
    }));
    if (c.assets.waterLeafAtlas) {
      const atlas = this.get(c.assets.waterLeafAtlas);
      const width = Math.floor(atlas.width / 2);
      const height = Math.floor(atlas.height / 2);
      this.waterLeaves = [0, 1, 2, 3].map(index => new Texture({
        source: atlas.source,
        frame: new Rectangle((index % 2) * width, Math.floor(index / 2) * height, width, height),
      }));
    }
  }
  leaf(c: SceneConfig, index: number) {
    return this.waterLeaves[index % this.waterLeaves.length]
      ?? this.get(c.assets.leaves[index % c.assets.leaves.length]);
  }
  get(file:string){const t=this.textures.get(file);if(!t)throw new Error('素材未预加载：'+file);return t;}
  async destroy(){for(const leaf of this.waterLeaves)leaf.destroy(false);this.waterLeaves=[];await Assets.unload(this.urls);this.textures.clear();}
}
