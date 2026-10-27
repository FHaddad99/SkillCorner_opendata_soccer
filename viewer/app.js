'use strict';
const $ = id => document.getElementById(id);
const state = {session:null,match:null,row:null,frame:0,playing:false,timer:null,epoch:0,seekId:0,
  cache:new Map(),pending:new Map(),context:null,contextAt:0,hits:[],viewedMax:{}};
const friendly = value => String(value ?? 'unknown').replaceAll('_',' ');
function message(text,error=false){$('alert').textContent=text;$('alert').classList.toggle('error',error);}
function action(fn){return async event=>{try{await fn(event);}catch(error){if(error.message!=='Superseded'){pause();message(error.message,true);if($('marker-status')){$('marker-status').textContent=error.message;$('marker-status').classList.add('error');}}}};}
async function api(path,body){const response=await fetch(path,{method:body===undefined?'GET':'POST',
  headers:{'Content-Type':'application/json','X-Review-Session':state.session||''},body:body===undefined?undefined:JSON.stringify(body)});
  const result=await response.json();if(!response.ok)throw new Error(result.error||`Request failed (${response.status})`);return result;}
function option(value,label){const el=document.createElement('option');el.value=value;el.textContent=label;return el;}
function roster(id){return state.match?.players.find(p=>p.id===Number(id));}
function playerName(id){if(id===null||id===undefined)return 'unknown';const p=roster(id);return p?`${p.name} · #${p.number} (${p.id})`:`unresolved player ${id}`;}
function teamName(id){return [state.match?.home,state.match?.away].find(t=>t?.id===Number(id))?.short_name||`unknown team ${id}`;}
function pause(){state.playing=false;clearTimeout(state.timer);$('play').textContent='▶';$('play').setAttribute('aria-label','Play replay');}
async function getFrame(frame){const epoch=state.epoch,mid=state.match.id,start=Math.max(state.match.first_frame,Math.floor(frame/100)*100),key=`${mid}:${start}`;
  if(!state.cache.has(key)){if(!state.pending.has(key))state.pending.set(key,api(`/api/matches/${mid}/frames?start=${start}&count=100`));
    const response=await state.pending.get(key);if(epoch!==state.epoch)throw new Error('Superseded');state.pending.delete(key);state.cache.set(key,response.frames);
    if(state.cache.size>8)state.cache.delete(state.cache.keys().next().value);}
  return state.cache.get(key).find(row=>row.frame===frame)||{frame,missing:true};}
async function seek(frame){if(!state.match)return;const request=++state.seekId;
  frame=Math.max(state.match.first_frame,Math.min(state.match.last_frame,Math.round(frame)));
  const row=await getFrame(frame);if(request!==state.seekId)return;state.frame=frame;state.row=row;
  if([1,2].includes(row.period)){const key=`${state.match.id}:${row.period}`;state.viewedMax[key]=Math.max(state.viewedMax[key]??frame,frame);try{sessionStorage.setItem('presslens-viewed-v2',JSON.stringify(state.viewedMax));}catch{}}
  $('scrubber').value=frame;$('jump').value=frame;$('frame-label').textContent=`FRAME ${frame.toLocaleString()}`;
  $('clock').textContent=row.timestamp?row.timestamp.replace(/^00:/,''):'—';
  for(const p of [1,2])$('period'+p).classList.toggle('active',row.period===p);
  $('detected').textContent=row.quality?.detected??0;$('estimated').textContent=row.quality?.extrapolated??0;
  $('ball-state').textContent=Number.isFinite(row.ball?.x)&&Number.isFinite(row.ball?.y)?(row.ball.is_detected?'Detected':row.ball.is_detected===false?'Extrapolated':'Unknown'):'Unavailable';
  $('carrier').textContent=`Raw tracking carrier: ${playerName(row.possession?.player_id)}`;
  const flags=[];if(row.missing)flags.push('Source frame missing');if(![1,2].includes(row.period))flags.push('Outside labelled playing period');
  if(!row.players?.length)flags.push('Player positions unavailable');if(row.quality?.invalid_xy)flags.push(`${row.quality.invalid_xy} invalid player positions`);
  if(row.possession?.player_id==null)flags.push('Carrier ID unknown');$('raw-flags').textContent=flags.join(' · ');
  const direction=row.period?state.match.home_directions[row.period-1]:null;
  $('direction').textContent=direction?`${state.match.home.short_name} attacks ${friendly(direction)} · native coordinates`:'Native coordinates · unknown period';
  $('pitch-empty').hidden=!!row.players?.length;draw();
  if($('provider').checked&&(!state.playing||performance.now()-state.contextAt>300))await updateContext();
}
async function updateContext(){if(!state.row||!$('provider').checked)return;const mid=state.match.id,frame=state.frame,epoch=state.epoch;
  const data=await api(`/api/matches/${mid}/context?frame=${frame}`);if(epoch!==state.epoch||!$('provider').checked)return;
  state.context=data;state.contextAt=performance.now();$('context-frame').textContent=`· FRAME ${frame}`;
  const box=$('provider-context');box.replaceChildren();
  function line(text,flag=false){const p=document.createElement('div');p.className=flag?'flag':'context-row';p.textContent=text;box.append(p);}
  if(!data.event_candidates.length)line('No possession-event candidate at this frame.');
  for(const e of data.event_candidates)line(`Event ${e.id}: ${playerName(e.player_id)} · ${friendly(e.start_type)}${e.at_start?' · starts here':''}`);
  for(const p of data.phase)line(`Phase ${p.index}: ${teamName(p.team_id)} in possession · ${friendly(p.in_possession)} / ${friendly(p.out_of_possession)}`);
  data.flags.forEach(flag=>line(flag,true));draw();
}
async function tick(){if(!state.playing)return;const period=state.match.periods[state.row?.period];
  if(state.frame>=state.match.last_frame||(period&&state.frame>=period.end)){pause();message('End of this period. Select the next half to continue.');return;}
  const before=performance.now();await seek(state.frame+1);if(state.playing)state.timer=setTimeout(action(tick),Math.max(0,100/Number($('speed').value)-(performance.now()-before)));}
function togglePlay(){if(state.playing){pause();return;}if(!state.match)return;state.playing=true;$('play').textContent='Ⅱ';$('play').setAttribute('aria-label','Pause replay');tick().catch(error=>{pause();message(error.message,true);});}
function valueInt(id){return $(id).value.trim()===''?null:Number($(id).value);}
async function loadMatch(mid){pause();state.epoch++;state.seekId++;state.cache.clear();state.pending.clear();state.context=null;
  $('scrubber').disabled=true;$('match-status').textContent='Verifying hashes and indexing tracking…';message('Opening audited match files. First load builds a local frame index.');
  const epoch=state.epoch,match=await api(`/api/matches/${mid}`);if(epoch!==state.epoch)return;state.match=match;
  $('fixture-title').textContent=`${match.home.short_name} — ${match.away.short_name}`;$('date').textContent=match.date;
  $('home-label').textContent=match.home.short_name;$('away-label').textContent=match.away.short_name;
  $('match-status').textContent=`${match.date} · ${match.pitch[0]} × ${match.pitch[1]} m · native 10 Hz · development review`;
  $('scrubber').min=match.first_frame;$('scrubber').max=match.last_frame;$('scrubber').disabled=false;
  $('provider').checked=false;hideContext();renderTimeline();
  await seek(match.periods['1'].start);message('Local observation review · source release and redistribution checks remain pending. No automatic tactical labels.');document.dispatchEvent(new Event('presslens:matchloaded'));}
function hideContext(){state.context=null;$('context-frame').textContent='';$('provider-context').textContent='Hidden during observation review. Enable the optional layer to inspect provider event candidates and phase labels.';renderTimeline();draw();}
function renderTimeline(){const track=$('phase-track');track.replaceChildren();if(!state.match||!$('provider').checked)return;
  const span=state.match.last_frame-state.match.first_frame||1;for(const p of state.match.phase_timeline){const el=document.createElement('span');el.style.left=`${(p.start-state.match.first_frame)/span*100}%`;el.style.width=`${(p.end-p.start)/span*100}%`;el.style.background=p.team_id===state.match.home.id?'#79d8f2':'#fa9480';track.append(el);}}
function draw(){const canvas=$('pitch'),ctx=canvas.getContext('2d'),W=canvas.width,H=canvas.height,L=state.match?.pitch[0]||105,B=state.match?.pitch[1]||68;
  const scale=Math.min((W-120)/L,(H-100)/B),left=(W-L*scale)/2,top=(H-B*scale)/2;
  const point=(x,y)=>[left+(x+L/2)*scale,top+(B/2-y)*scale];
  ctx.clearRect(0,0,W,H);ctx.fillStyle='#142f34';ctx.fillRect(0,0,W,H);
  for(let band=0;band<10;band++){ctx.fillStyle=band%2?'#153238':'#17363b';ctx.fillRect(left+band*L*scale/10,top,L*scale/10,B*scale);}
  ctx.strokeStyle='#73938e';ctx.lineWidth=1.7;ctx.setLineDash([]);
  function rect(x,y,w,h){const p=point(x,y);ctx.strokeRect(p[0],p[1],w*scale,-h*scale);}
  function line(x,y,x2,y2){ctx.beginPath();ctx.moveTo(...point(x,y));ctx.lineTo(...point(x2,y2));ctx.stroke();}
  function circle(x,y,r){ctx.beginPath();ctx.arc(...point(x,y),r*scale,0,Math.PI*2);ctx.stroke();}
  rect(-L/2,-B/2,L,B);line(0,-B/2,0,B/2);circle(0,0,9.15);
  for(const side of [-1,1]){const x=side*L/2;rect(side===-1?x:x-16.5,-20.16,16.5,40.32);rect(side===-1?x:x-5.5,-9.16,5.5,18.32);rect(side===-1?x-2:x,-3.66,2,7.32);circle(side*(L/2-11),0,.15);
    ctx.beginPath();const center=point(side*(L/2-11),0);const angle=Math.acos(5.5/9.15);ctx.arc(...center,9.15*scale,side===-1?-angle:Math.PI-angle,side===-1?angle:Math.PI+angle);ctx.stroke();}
  circle(0,0,.15);ctx.font='12px Segoe UI';ctx.fillStyle='#8faeae';ctx.textAlign='left';ctx.fillText('SKILLCORNER TRACKING',left,H-18);ctx.textAlign='right';ctx.fillText('10 Hz · native coordinates',W-left,H-18);
  state.hits=[];const row=state.row;if(!row||row.missing)return;
  const playerRadius=12;for(const p of row.players||[]){const [id,x,y,detected]=p;if(!Number.isFinite(x)||!Number.isFinite(y)||(!detected&&!$('extrapolated').checked))continue;
    const player=roster(id),[px,py]=point(x,y),color=player?.team_id===state.match.home.id?'#79d8f2':player?.team_id===state.match.away.id?'#fa9480':'#b3bbcb';
    if(row.possession?.player_id===id){ctx.strokeStyle='#f1f5fa';ctx.lineWidth=1.5;ctx.setLineDash([]);ctx.beginPath();ctx.arc(px,py,playerRadius+5,0,Math.PI*2);ctx.stroke();}
    if($('provider').checked&&state.context?.frame===row.frame&&state.context.event_candidates.some(e=>e.player_id===id)){ctx.strokeStyle='#efc37d';ctx.lineWidth=2;ctx.setLineDash([4,3]);ctx.beginPath();ctx.arc(px,py,playerRadius+9,0,Math.PI*2);ctx.stroke();}
    ctx.beginPath();ctx.arc(px,py,playerRadius,0,Math.PI*2);ctx.lineWidth=2;ctx.strokeStyle=color;ctx.setLineDash(detected?[]:[3,2]);ctx.fillStyle=detected?color:'#142f34';ctx.fill();ctx.stroke();ctx.setLineDash([]);
    if($('numbers').checked){ctx.fillStyle=detected?'#12333c':color;ctx.font='bold 12px Segoe UI';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(player?.number??'?',px,py+.5);}
    const nominated=window.pressLensMarkerRoles?.();
    if(nominated&&(nominated.primary_presser_id===id||nominated.supporting_defender_ids.includes(id))){const primary=nominated.primary_presser_id===id;ctx.strokeStyle=primary?'#85e1bd':'#d0abff';ctx.lineWidth=2.5;ctx.setLineDash([]);ctx.beginPath();ctx.arc(px,py,playerRadius+12,0,Math.PI*2);ctx.stroke();ctx.fillStyle=ctx.strokeStyle;ctx.font='bold 12px Segoe UI';ctx.textAlign='left';ctx.fillText(primary?'P':'S',px+20,py-15);}
    state.hits.push({id,x:px,y:py});}
  if(Number.isFinite(row.ball?.x)&&Number.isFinite(row.ball?.y)){ctx.beginPath();ctx.arc(...point(row.ball.x,row.ball.y),5.5,0,Math.PI*2);ctx.fillStyle=row.ball.is_detected?'#ffffff':'#142f34';ctx.strokeStyle='#ffffff';ctx.lineWidth=2;ctx.setLineDash(row.ball.is_detected?[]:[2,2]);ctx.fill();ctx.stroke();ctx.setLineDash([]);}ctx.textBaseline='alphabetic';}
function hit(event){const rect=$('pitch').getBoundingClientRect(),x=(event.clientX-rect.left)/rect.width*$('pitch').width,y=(event.clientY-rect.top)/rect.height*$('pitch').height;return state.hits.find(p=>Math.hypot(p.x-x,p.y-y)<18);}
async function init(){const session=await api('/api/session');state.session=session.session;
  try{state.viewedMax=JSON.parse(sessionStorage.getItem('presslens-viewed-v2')||'{}');}catch{state.viewedMax={};}
  const result=await api('/api/matches');$('match').replaceChildren(...result.matches.map(m=>option(m.id,`${m.home} — ${m.away} · ${m.id}`)));
  $('match').addEventListener('change',action(()=>loadMatch($('match').value)));
  $('period1').addEventListener('click',action(async()=>{pause();await seek(state.match.periods['1'].start);}));$('period2').addEventListener('click',action(async()=>{pause();await seek(state.match.periods['2'].start);}));
  $('play').addEventListener('click',togglePlay);
  for(const [id,delta] of [['back10',-10],['back',-1],['next',1],['next10',10]])$(id).addEventListener('click',action(async()=>{pause();await seek(state.frame+delta);}));
  $('scrubber').addEventListener('input',action(async()=>{pause();await seek(Number($('scrubber').value));}));
  $('jump-form').addEventListener('submit',action(async e=>{e.preventDefault();pause();await seek(Number($('jump').value));}));
  $('provider').addEventListener('change',action(async()=>{renderTimeline();if($('provider').checked)await updateContext();else hideContext();}));
  for(const id of ['numbers','extrapolated'])$(id).addEventListener('change',draw);
  $('pitch').addEventListener('pointermove',event=>{const picked=hit(event);$('pitch').title=picked?playerName(picked.id):'';});
  $('pitch').addEventListener('click',event=>{const picked=hit(event);if(!picked)return;$('picked').textContent=playerName(picked.id);window.pressLensMarkerClick?.(picked.id);});
  document.addEventListener('keydown',action(async e=>{if(['INPUT','TEXTAREA','SELECT','BUTTON'].includes(e.target.tagName))return;
    if(e.code==='Space'){e.preventDefault();togglePlay();}if(['ArrowLeft','ArrowRight'].includes(e.key)){e.preventDefault();pause();await seek(state.frame+(e.key==='ArrowLeft'?-1:1)*(e.shiftKey?10:1));}}));
  $('export').addEventListener('click',action(async()=>{const data=await api('/api/export'),blob=new Blob([JSON.stringify(data,null,2)],{type:'application/json'}),link=document.createElement('a');link.href=URL.createObjectURL(blob);link.download='presslens-review-history.json';link.click();setTimeout(()=>URL.revokeObjectURL(link.href),1000);message('Downloaded press events and previous annotation history.');}));
  await loadMatch(result.matches[0].id);
}
init().catch(error=>message(error.message,true));
