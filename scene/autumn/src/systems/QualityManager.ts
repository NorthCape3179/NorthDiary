import type { Quality } from '../config/types';
export class QualityManager {
  paused=false;hidden=false;
  constructor(public quality:Quality='light'){}
  get running(){return !this.paused&&!this.hidden&&this.quality!=='static';}
  get fps(){return this.quality==='full'?60:30;}
  get density(){return this.quality==='full'?1:0.6;}
}
