import { qualities, type Quality } from '../config/types';
export interface Playback {title:string;artist:string;durationMs:number;positionMs:number;playing:boolean;positionKnown?:boolean;status?:string;font?:string;fontSize?:number;lines:{timeMs:number;text:string;translation?:string}[]}
export type BridgeMessage={type:'pauseScene'|'resumeScene'|'disconnect'}|{type:'setQuality';value:Quality}|{type:'setTheme';value:'autumn_day'}|{type:'setPlayback';value:Playback};
export function parseMessage(input:unknown):BridgeMessage|null{
  if(!input||typeof input!=='object'||Array.isArray(input))return null;
  const m=input as Record<string,unknown>;
  if(Object.keys(m).some(k=>k!=='type'&&k!=='value'))return null;
  if(['pauseScene','resumeScene','disconnect'].includes(m.type as string))return Object.keys(m).length===1?m as BridgeMessage:null;
  if(m.type==='setQuality'&&qualities.includes(m.value as Quality))return m as BridgeMessage;
  if(m.type==='setTheme'&&m.value==='autumn_day')return m as BridgeMessage;
  if(m.type==='setPlayback'){
    const p=m.value as Playback;
    if(!p||typeof p!=='object'||typeof p.title!=='string'||p.title.length>200||typeof p.artist!=='string'||p.artist.length>200||typeof p.playing!=='boolean'||!Number.isFinite(p.durationMs)||!Number.isFinite(p.positionMs)||p.durationMs<0||p.durationMs>86400000||p.positionMs<0||p.positionMs>p.durationMs||!Array.isArray(p.lines)||p.lines.length>500)return null;
    if(p.positionKnown!==undefined&&typeof p.positionKnown!=='boolean')return null;
    if(p.status!==undefined&&(typeof p.status!=='string'||p.status.length>500))return null;
    if(p.font!==undefined&&!['fusion-pixel','noto-sans-sc','noto-serif-sc','lxgw-wenkai'].includes(p.font))return null;
    if(p.fontSize!==undefined&&(!Number.isFinite(p.fontSize)||p.fontSize<16||p.fontSize>32))return null;
    let last=-1;for(const l of p.lines){if(!l||typeof l.text!=='string'||l.text.length>500||!Number.isFinite(l.timeMs)||l.timeMs<0||l.timeMs<last||l.timeMs>p.durationMs||(l.translation!==undefined&&(typeof l.translation!=='string'||l.translation.length>500)))return null;last=l.timeMs;}
    return structuredClone(m) as BridgeMessage;
  }return null;
}
export class SceneBridge {
  private listeners=new Set<(event:unknown)=>void>();
  constructor(private handler:(m:BridgeMessage)=>void){}
  receive=(input:unknown)=>{const message=parseMessage(input);if(!message)return {ok:false,error:'Invalid scene message'};this.handler(message);return {ok:true};};
  subscribe=(callback:(event:unknown)=>void)=>{this.listeners.add(callback);return ()=>this.listeners.delete(callback);};
  emit(event:unknown){for(const f of this.listeners){try{f(event);}catch{/* Host observers cannot break the renderer. */}}}
  destroy(){this.listeners.clear();}
}
