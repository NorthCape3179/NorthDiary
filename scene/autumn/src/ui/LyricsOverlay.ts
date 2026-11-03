import type { Playback } from '../bridge/SceneBridge';
export class LyricsOverlay {
  demo=false;private playback:Playback|null=null;private key='';
  constructor(private element:HTMLElement){}
  setPlayback(p:Playback){this.playback=p;this.demo=false;this.render();}
  clear(){this.playback=null;this.demo=false;this.render();}
  setDemo(value:boolean){this.demo=value;this.playback=null;this.render();}
  private render(){
    const p=this.playback,e=this.element;
    const seconds=Math.floor((p?.positionMs??0)/1000),clock=`${String(Math.floor(seconds/60)).padStart(2,'0')}:${String(seconds%60).padStart(2,'0')}${p&&!p.playing?' · 暂停':''}`;
    const clockNode=e.querySelector('.lyric-clock');if(clockNode)clockNode.textContent=clock;
    let idx=-1;if(p)for(let i=0;i<p.lines.length;i++){if(p.lines[i].timeMs<=p.positionMs)idx=i;else break;}
    const key=JSON.stringify([this.demo,p?.title,p?.artist,p?.playing,p?.positionKnown,p?.status,p?.font,p?.fontSize,idx,p?.lines.slice(Math.max(0,idx-1),idx+2)]);
    if(key===this.key)return;this.key=key;
    e.replaceChildren();e.hidden=!this.demo&&!p;if(e.hidden)return;
    const meta=document.createElement('div');meta.className='lyric-meta';e.append(meta);
    const tag=document.createElement('span');tag.className='lyrics-label';meta.append(tag);
    if(this.demo){
      tag.textContent='歌词显示层 · 原创占位文案';
      for(const [i,text] of ['风经过枝头','把一片秋天，轻轻放进水里','此刻，不必赶路'].entries()){const row=document.createElement('div');row.className=`lyric-row ${['previous','current','next'][i]}`;const p=document.createElement('p');p.textContent=text;row.append(p);e.append(row);}return;
    }
    if(!p)return;
    e.style.setProperty('--lyric-size',`${p.fontSize??27}px`);
    e.style.fontFamily=`"${p.font??'fusion-pixel'}", "Microsoft YaHei", sans-serif`;
    tag.textContent=[p.title,p.artist,p.playing?'':'已暂停'].filter(Boolean).join(' · ');
    tag.title=tag.textContent;
    const time=document.createElement('span');time.className='lyric-clock';time.textContent=p.positionKnown===false?'读取进度中':clock;meta.append(time);
    if(p.positionKnown===false||!p.lines.length||idx<0){
      const line=document.createElement('p');line.className='current status';
      line.textContent=p.positionKnown===false?(p.status||'等待准确播放进度'):p.lines.length?'♪':p.status||'暂无歌词';e.append(line);return;
    }
    const neighbor=(start:number,step:number)=>{while(start>=0&&start<p.lines.length){if(p.lines[start].text.trim())return start;start+=step;}return -1;};
    for(const [i,cls] of [[neighbor(idx-1,-1),'previous'],[idx,'current'],[neighbor(idx+1,1),'next']] as const){
      if(i<0)continue;const row=document.createElement('div');row.className=`lyric-row ${cls}`;
      const line=document.createElement('p');line.textContent=p.lines[i].text||'♪';row.append(line);
      if(p.lines[i].translation){const translated=document.createElement('p');translated.className='translation';translated.textContent=p.lines[i].translation!;row.append(translated);}
      e.append(row);
    }
  }
}
