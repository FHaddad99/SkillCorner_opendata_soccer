'use strict';
const candidateReview={cases:[],reviews:[],visible:[],current:null,busy:false,generation:0,drafts:{}};
try{candidateReview.drafts=JSON.parse(sessionStorage.getItem('presslens-candidate-drafts')||'{}');}catch{}
function candidateStatus(text,error=false){$('candidate-status').textContent=text;$('candidate-status').classList.toggle('error',error);}
function candidateAction(fn){return async()=>{try{await fn();}catch(error){candidateStatus(error.message,true);}};}
function candidateKey(c){return state.match.id+':'+$('marker-reviewer').value.trim()+':'+c.candidate_id;}
function candidatePrior(c){return candidateReview.reviews.find(r=>r.candidate_id===c.candidate_id);}
function candidateDecision(){return document.querySelector('input[name="candidate-decision"]:checked')?.value||'unreviewed';}
function candidateRemember(){const c=candidateReview.current;if(!c||candidateReview.busy)return;
  candidateReview.drafts[candidateKey(c)]={start_frame:valueInt('candidate-start'),end_frame:valueInt('candidate-end'),decision:candidateDecision(),scope_reason:$('candidate-scope').value};
  try{sessionStorage.setItem('presslens-candidate-drafts',JSON.stringify(candidateReview.drafts));}catch{}
  $('candidate-scope-field').hidden=candidateDecision()!=='out_of_scope';
}
function candidateButtons(){const c=candidateReview.current,busy=candidateReview.busy,i=candidateReview.visible.indexOf(c);
  for(const id of ['candidate-save','candidate-save-next','candidate-go','candidate-start','candidate-end','candidate-decisions','candidate-scope'])$(id).disabled=busy||!c;
  $('candidate-prev').disabled=busy||i<=0;$('candidate-next').disabled=busy||i<0||i>=candidateReview.visible.length-1;
  for(const id of ['candidate-pool','candidate-filter','candidate-reload','candidate-select'])$(id).disabled=busy;
}
function candidateDisplay(c){candidateReview.current=c||null;
  const old=c?candidatePrior(c):null,d=c?(candidateReview.drafts[candidateKey(c)]||old||{}):{};
  $('candidate-start').value=c?(d.start_frame??old?.case.start_frame??c.start_frame):'';
  $('candidate-end').value=c?(d.end_frame??old?.case.end_frame??c.end_frame):'';
  document.querySelectorAll('input[name="candidate-decision"]').forEach(el=>el.checked=el.value===(d.decision||'unreviewed'));
  $('candidate-scope').value=d.scope_reason||'counter_attack';$('candidate-scope-field').hidden=d.decision!=='out_of_scope';
  $('candidate-source').textContent=c?'P'+c.period+' · source frames '+c.start_frame+'–'+c.end_frame+' · '+friendly(c.source_kind)+(c.source_team_id?' · '+teamName(c.source_team_id):'')+(old?' · saved revision '+old.revision:' · unreviewed'): 'No episodes in this selection.';
  $('candidate-flags').textContent=c?(c.flags||[]).join(' · '):'';
  $('candidate-members').replaceChildren();
  for(const e of c?.engagements||[]){const line=document.createElement('p');line.textContent=e.event_id+' · '+friendly(e.subtype)+' · '+e.start_frame+'–'+e.end_frame+' · '+playerName(e.player_id)+' → '+playerName(e.carrier_id);$('candidate-members').append(line);}
  if(c&&!c.engagements)$('candidate-members').textContent=c.source_kind==='human_marked_press'?'Saved human pressure example; its original scope remains in the source record.':'Audit window outside the primary candidate intervals; pressure is not prelabelled.';
  if(c)$('candidate-select').value=c.candidate_id;
  candidateButtons();
}
function candidateFilter(preferred,keepSaved=false){const filter=$('candidate-filter').value;
  candidateReview.visible=candidateReview.cases.filter(c=>{const decision=candidatePrior(c)?.decision||'unreviewed';
    return filter==='all'||filter==='unreviewed'&&decision==='unreviewed'||filter==='reviewed'&&['yes','no','uncertain','unassessable'].includes(decision)||filter==='deferred'&&['not_pressure','out_of_scope'].includes(decision);});
  // Ordinary Save keeps the reviewed episode selected even when its new decision
  // no longer matches the filter. Never pair a new episode with the old replay.
  const pinned=keepSaved&&candidateReview.cases.find(c=>c.candidate_id===preferred&&!candidateReview.visible.includes(c));
  if(pinned)candidateReview.visible=candidateReview.cases.filter(c=>c===pinned||candidateReview.visible.includes(c));
  $('candidate-select').replaceChildren();
  for(const c of candidateReview.visible){const r=candidatePrior(c);$('candidate-select').append(option(c.candidate_id,'P'+c.period+' · '+c.start_frame+'–'+c.end_frame+' · '+friendly(r?.decision||'unreviewed')));}
  const reviewed=candidateReview.cases.filter(c=>candidatePrior(c)?.decision&&candidatePrior(c).decision!=='unreviewed').length;
  $('candidate-count').textContent=candidateReview.visible.length+' shown / '+candidateReview.cases.length+' proposals · '+reviewed+' decisions saved'+(pinned?' · just-saved episode kept selected':'');
  candidateDisplay(candidateReview.visible.find(c=>c.candidate_id===preferred)||candidateReview.visible[0]);
}
async function candidateLoad(){if(!state.match||candidateReview.busy)return;const generation=++candidateReview.generation;
  const mid=state.match.id,reviewer=$('marker-reviewer').value.trim();candidateReview.current=null;candidateButtons();
  candidateStatus('Loading proposals…');
  const result=await api('/api/candidates?'+new URLSearchParams({match:mid,pool:$('candidate-pool').value,reviewer}));
  if(generation!==candidateReview.generation||state.match.id!==mid||$('marker-reviewer').value.trim()!==reviewer)return;
  candidateReview.cases=result.cases;candidateReview.reviews=result.reviews;candidateFilter();
  const missed=result.manual_comparison.filter(m=>!m.overlapping_candidates.length);
  $('candidate-comparison').textContent=result.manual_comparison.length+' saved human examples across reviewers; '+missed.length+' have no overlap with the primary candidate pool.'+(missed.length?' Frames: '+missed.slice(0,8).map(m=>m.start_frame+'–'+m.end_frame).join(', ')+'. Use the saved-examples pool to inspect them.':'')+' Overlap alone does not measure recall.';
  candidateStatus('Queue ready. Choose Replay with context to navigate. Loading, editing and saving do not move playback.'+(result.source_diagnostics.invalid_or_unavailable_bound_engagements?' Omitted source engagements: '+result.source_diagnostics.omitted_engagements.map(e=>e.event_id+' (frames '+e.frame_start+'–'+e.frame_end+'): '+e.reason).join('; '):''));
}
async function candidateGo(){const c=candidateReview.current;if(!c)return;
  const limits=state.match.periods[c.period],start=valueInt('candidate-start');
  if(!Number.isInteger(start)||start<limits.start||start>limits.end)throw new Error('Enter a start frame in the original half.');
  pause();await seek(Math.max(limits.start,start-c.candidate_policy.context_frames));
  candidateStatus('Showing build-up to the episode. Press Play to continue through the full half.');
}
async function candidateMove(delta){candidateRemember();const index=candidateReview.visible.indexOf(candidateReview.current),c=candidateReview.visible[index+delta];if(!c)return;candidateDisplay(c);await candidateGo();}
async function candidateSave(next=false){if(candidateReview.busy||!candidateReview.current)return;
  if(marker.draft)throw new Error('Finish or cancel the manual pressure draft before saving a funnel review.');
  const reviewer=$('marker-reviewer').value.trim();if(!reviewer)throw new Error('Enter your reviewer name.');
  candidateRemember();const c=candidateReview.current,mid=state.match.id,generation=candidateReview.generation,following=candidateReview.visible[candidateReview.visible.indexOf(c)+1];
  const d=candidateReview.drafts[candidateKey(c)];candidateReview.busy=true;candidateButtons();
  try{const row=await api('/api/candidate-reviews',{match_id:mid,reviewer,pool:$('candidate-pool').value,candidate_id:c.candidate_id,
      ...d,base_revision:candidatePrior(c)?.revision||0,replay_review:{future_replay_viewed:'unknown',viewer_session_max_frame:state.viewedMax[mid+':'+c.period]??null}});
    delete candidateReview.drafts[mid+':'+reviewer+':'+c.candidate_id];try{sessionStorage.setItem('presslens-candidate-drafts',JSON.stringify(candidateReview.drafts));}catch{}
    if(state.match.id!==mid||generation!==candidateReview.generation||$('marker-reviewer').value.trim()!==reviewer)return;
    candidateReview.reviews=candidateReview.reviews.filter(r=>r.candidate_id!==c.candidate_id);candidateReview.reviews.push(row);
    candidateFilter(next&&following?following.candidate_id:c.candidate_id,!next||!following);
    candidateStatus('Saved '+friendly(row.decision)+' · revision '+row.revision+'. Playback unchanged.');
    if(next&&following&&candidateReview.visible.includes(following))await candidateGo();
  }finally{candidateReview.busy=false;candidateButtons();if(state.match?.id!==mid||$('marker-reviewer').value.trim()!==reviewer)await candidateLoad();}
}
$('candidate-reload').addEventListener('click',candidateAction(candidateLoad));
for(const id of ['candidate-pool','marker-reviewer'])$(id).addEventListener('change',candidateAction(candidateLoad));
$('candidate-filter').addEventListener('change',()=>{candidateRemember();candidateFilter(candidateReview.current?.candidate_id);});
$('candidate-select').addEventListener('change',candidateAction(async()=>{candidateRemember();candidateDisplay(candidateReview.visible.find(c=>c.candidate_id===$('candidate-select').value));await candidateGo();}));
$('candidate-go').addEventListener('click',candidateAction(candidateGo));
$('candidate-prev').addEventListener('click',candidateAction(()=>candidateMove(-1)));
$('candidate-next').addEventListener('click',candidateAction(()=>candidateMove(1)));
$('candidate-save').addEventListener('click',candidateAction(()=>candidateSave()));
$('candidate-save-next').addEventListener('click',candidateAction(()=>candidateSave(true)));
for(const id of ['candidate-start','candidate-end','candidate-scope'])$(id).addEventListener('input',candidateRemember);
document.querySelectorAll('input[name="candidate-decision"]').forEach(el=>el.addEventListener('change',candidateRemember));
document.addEventListener('presslens:matchloaded',candidateAction(candidateLoad));
candidateButtons();if(state.match)candidateLoad().catch(error=>candidateStatus(error.message,true));
