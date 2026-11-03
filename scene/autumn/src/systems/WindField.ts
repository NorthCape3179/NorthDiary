import type { SceneConfig } from '../config/types';
/** A continuous, shared world field. Spatial phase stays small for coherent motion. */
export class WindField {
  constructor(public config:SceneConfig['wind']){}
  sample(t:number,x=240,y=135){
    const phase=t*2*Math.PI/this.config.gustPeriodSec;
    return this.config.baseX+this.config.gustStrength*(.62*Math.sin(phase)+.26*Math.sin(phase*.43+1.7)+.12*Math.sin(phase*1.91+x*.002+y*.001));
  }
}
