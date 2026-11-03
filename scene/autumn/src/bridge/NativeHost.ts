import type { Playback } from './SceneBridge';
export interface HostState {type:'hostState';active:boolean;lyricsEnabled:boolean;playback:Playback|null}
interface Host {ready:()=>void;setLyricsEnabled:(enabled:boolean)=>void;message:{connect:(callback:(value:string)=>void)=>void}}
declare global {interface Window {
  qt?:{webChannelTransport:unknown};
  QWebChannel?:new(transport:unknown,callback:(channel:{objects:{northDiaryHost:Host}})=>void)=>unknown;
}}
export const isNative=Boolean(window.qt?.webChannelTransport);
export let nativeHost:Host|undefined;
export function connectHost(receive:(state:HostState)=>void){
  if(!isNative)return;
  const fonts=document.createElement('style');
  fonts.textContent=['fusion-pixel','noto-sans-sc','noto-serif-sc','lxgw-wenkai'].map(key=>`@font-face{font-family:"${key}";src:url("${new URL(import.meta.env.BASE_URL+'fonts/'+key+'.ttf',location.href)}") format("truetype");font-display:swap;}`).join('\n');
  document.head.append(fonts);
  const script=document.createElement('script');script.src='qrc:///qtwebchannel/qwebchannel.js';
  script.onload=()=>{if(!window.QWebChannel)return;new window.QWebChannel(window.qt!.webChannelTransport,channel=>{
    nativeHost=channel.objects.northDiaryHost;
    nativeHost.message.connect(raw=>{try{const value=JSON.parse(raw) as HostState;if(value.type==='hostState')receive(value);}catch{/* Ignore malformed host messages. */}});
    nativeHost.ready();
  });};
  document.head.append(script);
}
