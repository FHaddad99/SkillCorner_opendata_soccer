'use strict';
const marker={active:true,draft:null,busy:false,replacePrimary:false,rows:[],drafts:{},generation:0,lastDeleted:null};
function markerStatus(text,error=false){$('marker-status').textContent=text;$('marker-status').classList.toggle('error',error);}
function markerAction(fn){return async event=>{try{await fn(event);}catch(error){markerStatus(error.message,true);}};}
function markerPersist(){if(state.match){if(marker.draft)marker.drafts[state.match.id]=marker.draft;else delete marker.drafts[state.match.id];}
  try{sessionStorage.setItem('presslens-marker-drafts',JSON.stringify(marker.drafts));}catch{}}
function markerRender(){const d=marker.draft;
  $('marker-toggle').textContent=marker.busy?'Saving…':d?(d.editing?'Save changes':d.end_frame!==null?'Retry save':'End pressure event · P'):'Start pressure event · P';
  $('marker-edit-bounds').hidden=!d?.editing;
  if(d?.editing)for(const [id,key] of [['marker-edit-start','start_frame'],['marker-edit-end','end_frame']])if(document.activeElement!==$(id))$(id).value=d[key]??'';
  $('marker-toggle').classList.toggle('recording',!!d);$('marker-toggle').disabled=marker.busy||!state.match;
  $('marker-reviewer').disabled=!!d;$('marker-cancel').hidden=!d;$('marker-cancel').disabled=marker.busy;
  $('marker-interval').textContent=d?(d.editing?'Editing frames '+d.start_frame+'–'+d.end_frame+' · period '+d.period:'Recording from frame '+d.start_frame+' · period '+d.period+(d.end_frame!==null?' · end captured at '+d.end_frame:'')):'Watch the half normally. Start a marker when pressure begins.';
  $('marker-primary').textContent=d?.primary_presser_id!=null?playerName(d.primary_presser_id):'Not assigned';
  $('marker-support').replaceChildren();
  for(const pid of d?.supporting_defender_ids||[]){const button=document.createElement('button');button.type='button';button.className='bookmark-chip';button.textContent=playerName(pid)+' ×';button.addEventListener('click',()=>{if(marker.busy)return;d.supporting_defender_ids=d.supporting_defender_ids.filter(p=>p!==pid);delete d.selection_frames[pid];markerPersist();markerRender();draw();});$('marker-support').append(button);}
  if(!d?.supporting_defender_ids.length)$('marker-support').textContent='None selected';
  $('marker-replace-primary').disabled=!d||marker.busy;
  $('marker-click-hint').textContent=marker.replacePrimary?'Click the new primary presser.':d?.editing?'Click same-team players to toggle support. You can select from any frame in this half; event bounds stay unchanged.':'First player click = primary presser. Further same-team clicks toggle supporting pressers.';
}
async function markerLoad(){if(!state.match)return;const generation=++marker.generation,mid=state.match.id;
  marker.draft=marker.drafts[mid]||null;marker.replacePrimary=false;
  if(marker.draft)$('marker-reviewer').value=marker.draft.reviewer;markerRender();
  const reviewer=$('marker-reviewer').value.trim();marker.rows=[];
  if(reviewer){const result=await api('/api/pass-reviews?'+new URLSearchParams({match:mid,pass:'press',reviewer}));if(generation!==marker.generation)return;marker.rows=result.reviews.filter(r=>r.press_event);}
  markerList();if(marker.draft)markerStatus('Unsaved event restored. Continue selecting players, then end it; replay remains under your control.');
}
function markerList(){const list=$('marker-events');list.replaceChildren();$('marker-count').textContent=marker.rows.length+' saved press events in this match';
  for(const row of [...marker.rows].sort((a,b)=>b.case.start_frame-a.case.start_frame)){const e=row.press_event,card=document.createElement('div');card.className='combined-case';
    const title=document.createElement('strong');title.textContent='P'+e.period+' · '+e.start_frame+'–'+e.end_frame;const roles=document.createElement('p');roles.textContent='Primary: '+playerName(e.primary_presser_id)+' · supporting: '+e.supporting_defender_ids.map(playerName).join(', ');
    const go=document.createElement('button');go.type='button';go.className='quiet';go.textContent='Go to start';go.addEventListener('click',markerAction(async()=>{pause();await seek(e.start_frame);}));
    const edit=document.createElement('button');edit.type='button';edit.className='quiet';edit.textContent='Edit';edit.addEventListener('click',markerAction(()=>markerEdit(row)));
    const remove=document.createElement('button');remove.type='button';remove.className='quiet';remove.textContent='Delete';remove.addEventListener('click',markerAction(()=>markerDelete(row)));
    card.append(title,roles,go,edit,remove);list.append(card);}
}
function markerEdit(row){if(marker.busy||marker.draft)throw new Error('Finish or cancel the current draft before editing a saved event.');
  marker.draft={...structuredClone(row.press_event),match_id:row.match_id,reviewer:row.reviewer,event_id:row.event_id,base_revision:row.revision,editing:true};
  $('marker-edit-start').value=marker.draft.start_frame;$('marker-edit-end').value=marker.draft.end_frame;
  marker.replacePrimary=false;markerPersist();markerRender();draw();markerStatus('Editing saved event. Adjust bounds or click players in the same half; save changes when ready. Replay is unchanged.');}
async function markerDelete(row){if(marker.busy||marker.draft)throw new Error('Finish or cancel the current draft before deleting a saved event.');
  const mid=state.match.id;marker.busy=true;markerRender();try{const result=await api('/api/press-event-state',{match_id:mid,event_id:row.event_id,reviewer:row.reviewer,base_revision:row.revision,deleted:true});
    marker.lastDeleted=result;$('marker-undo-delete').hidden=false;if(state.match.id===mid){marker.rows=marker.rows.filter(r=>r.event_id!==row.event_id);markerList();markerStatus('Saved event deleted from the list. Undo is available; replay and source frames are unchanged.');}
  }finally{marker.busy=false;markerRender();}}
async function markerToggle(){if(marker.busy||!state.match)return;
  if(!marker.draft){const reviewer=$('marker-reviewer').value.trim();if(!reviewer)throw new Error('Enter your name once before marking events.');
    if(![1,2].includes(state.row?.period)||state.row.missing)throw new Error('Start the event inside a labelled playing period.');
    marker.draft={match_id:state.match.id,reviewer,review_scope_version:state.match.review_scope?.version??null,period:state.row.period,start_frame:state.frame,end_frame:null,primary_presser_id:null,supporting_defender_ids:[],selection_frames:{}};
    marker.replacePrimary=false;markerPersist();markerRender();markerStatus('Pressure start marked. Click the primary presser, then supporting defenders. Playback continues.');draw();return;}
  const d=marker.draft;
  if(d.editing&&(!Number.isInteger(d.start_frame)||!Number.isInteger(d.end_frame)))throw new Error('Enter both start and end frame IDs before saving changes.');
  if(d.end_frame===null){if(state.row?.period!==d.period)throw new Error('End the event in its starting half, or cancel this marker.');if(state.frame<d.start_frame)throw new Error('The end must be at or after the marked start.');d.end_frame=state.frame;markerPersist();}
  marker.busy=true;markerRender();const mid=d.match_id;
  try{const row=await api('/api/press-events',{...d,replay_review:{future_replay_viewed:'unknown',viewer_session_max_frame:state.viewedMax[mid+':'+d.period]??null}});
    delete marker.drafts[mid];if(state.match.id===mid){marker.draft=null;marker.replacePrimary=false;marker.rows=marker.rows.filter(r=>!(r.event_id===row.event_id||r.sequence_id===row.sequence_id&&r.reviewer===row.reviewer));marker.rows.push(row);markerList();markerStatus('Saved frames '+d.start_frame+'–'+d.end_frame+(d.primary_presser_id===null?' · primary presser unassigned':'')+'. Continue watching the half.');}
    markerPersist();
  }finally{marker.busy=false;markerRender();draw();}}
function markerPick(pid){if(!marker.active)return false;if(!marker.draft){markerStatus('Start a pressure marker first, then click players.');return true;}
  if(marker.busy)return true;const d=marker.draft,p=roster(pid);
  if(!p)return true;if(state.row?.period!==d.period){markerStatus('Select players in the saved event’s half.',true);return true;}
  const outside=state.frame<d.start_frame||(d.end_frame!==null&&state.frame>d.end_frame);
  if(outside&&!d.editing){markerStatus('Select players while viewing the marked event in its starting half.',true);return true;}
  if(d.primary_presser_id===null||marker.replacePrimary){const previous=d.primary_presser_id,changedTeam=previous!==null&&roster(previous)?.team_id!==p.team_id;
    if(changedTeam){d.supporting_defender_ids=[];d.selection_frames={};}
    if(previous!==null)delete d.selection_frames[previous];d.supporting_defender_ids=d.supporting_defender_ids.filter(x=>x!==pid);
    d.primary_presser_id=pid;d.selection_frames[pid]=state.frame;marker.replacePrimary=false;
  }else if(pid===d.primary_presser_id){markerStatus('Primary already selected. Use “Change primary” to replace this player.');return true;}
  else{if(p.team_id!==roster(d.primary_presser_id).team_id){markerStatus('Choose supporting pressers from the primary presser’s team.',true);return true;}
    if(d.supporting_defender_ids.includes(pid)){d.supporting_defender_ids=d.supporting_defender_ids.filter(x=>x!==pid);delete d.selection_frames[pid];}
    else{d.supporting_defender_ids.push(pid);d.selection_frames[pid]=state.frame;}}
  markerPersist();markerRender();markerStatus(outside?'Player selection updated from review frame '+state.frame+', outside the event interval. Event bounds and playback are unchanged.':'Player selection updated. Playback is unchanged.');draw();return true;}
window.pressLensMarkerClick=markerPick;
window.pressLensMarkerRoles=()=>marker.active&&marker.draft?marker.draft:null;
function initMarker(){try{marker.drafts=JSON.parse(sessionStorage.getItem('presslens-marker-drafts')||'{}');$('marker-reviewer').value=sessionStorage.getItem('presslens-marker-reviewer')||sessionStorage.getItem('presslens-focused-reviewer')||'';}catch{marker.drafts={};}
  $('marker-reviewer').addEventListener('change',markerAction(async()=>{try{sessionStorage.setItem('presslens-marker-reviewer',$('marker-reviewer').value);}catch{}await markerLoad();}));
  $('marker-toggle').addEventListener('click',markerAction(markerToggle));
  for(const [id,key] of [['marker-edit-start','start_frame'],['marker-edit-end','end_frame']]){
    const update=()=>{if(!marker.draft?.editing)return;marker.draft[key]=valueInt(id);markerPersist();markerRender();};
    $(id).addEventListener('input',update);$(id+'-cursor').addEventListener('click',()=>{$(id).value=state.frame;update();});
  }
  $('marker-undo-delete').addEventListener('click',markerAction(async()=>{if(marker.busy||!marker.lastDeleted)return;const row=marker.lastDeleted;
    marker.busy=true;markerRender();try{const restored=await api('/api/press-event-state',{match_id:row.match_id,event_id:row.event_id,reviewer:row.reviewer,base_revision:row.revision,deleted:false});
      marker.lastDeleted=null;$('marker-undo-delete').hidden=true;if(state.match?.id===row.match_id){marker.rows.push(restored);markerList();}markerStatus('Deleted event restored. Replay unchanged.');
    }finally{marker.busy=false;markerRender();}}));
  $('marker-cancel').addEventListener('click',()=>{if(marker.busy)return;marker.draft=null;marker.replacePrimary=false;markerPersist();markerRender();draw();markerStatus('Unsaved marker cancelled. Replay unchanged.');});
  $('marker-replace-primary').addEventListener('click',()=>{marker.replacePrimary=true;markerRender();});
  document.addEventListener('presslens:matchloaded',markerAction(markerLoad));
  document.addEventListener('keydown',markerAction(async event=>{if(marker.active&&event.key.toLowerCase()==='p'&&!event.ctrlKey&&!event.metaKey&&!event.altKey&&!['INPUT','TEXTAREA','SELECT'].includes(event.target.tagName)){event.preventDefault();await markerToggle();}}));
  markerRender();if(state.match)markerLoad().catch(error=>markerStatus(error.message,true));}
initMarker();
