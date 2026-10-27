# Simple press-event marking

Software v0.6.0; review scope press-scope-1.1. This is the first focused review pass: identify candidate pressure events and nominate participating defenders. **Pressure during counter-attacks and fast breaks, and represses, are excluded from this pass and deferred for possible later annotation.** Funneling, cues, outcomes and other analytical measures are left for later passes.

This is the reviewer's declared selection policy, not an automatic phase detector. Full-half replay still shows every situation. Deferred/unmarked situations are not negative press labels; the current sample cannot support claims about pressure during counters/fast breaks or all-match prevalence. Older records retain their original scope or an explicit unknown scope rather than being reclassified retrospectively.

## Use it

Restart the local server after this update, then refresh the browser:

```powershell
.\start_presslens.cmd
```

Open http://127.0.0.1:8765. Full-half replay, first/second-half selection, scrubbing, frame stepping, playback speed and keyboard controls remain available. The marker does not pause, jump, loop, shorten or advance the replay.

1. Enter your reviewer name once.
2. Watch the half. Click **Start pressure event** when the episode begins, or press **P** outside a text/select field.
3. Click the primary presser's position on the pitch. The first selected player receives a green **P** outline.
4. Click other defenders to nominate secondary/supporting pressers. They receive violet **S** outlines. Clicking a support player again, or its × chip, removes it. Opposing-team players cannot be added as supports. **Change primary** lets you replace the primary before ending the event.
5. Click the **same button** again, now labelled **End pressure event** (or press P). The current native frame becomes the end; the event saves automatically and you can continue watching the half.

Use the existing pause, slow-speed or frame controls whenever helpful for selection. The marker itself does not change playback. It records the native frames you actually selected; it does not infer onset or release from future outcomes.

If no primary was selected, the event can still save with its primary explicitly unassigned. No defender is guessed. Select roles while the event is open. A marker must end in the same period and at or after its start. If you change halves while marking, return to the original half to finish or cancel the unsaved marker; the viewer's half controls remain usable.

Unsaved markers and selections are retained in browser-tab session storage across reloads. Reload still opens the viewer normally; it does not automatically seek to the draft. **Cancel unsaved event** discards only the draft. A failed save retains the captured end for retry rather than extending the episode to the retry time.

Saved events appear below the marker with their frame interval and selected players. **Go to start** is an explicit navigation action; no save or selection triggers navigation. The Detailed Annotation tab and form have been removed. **Download review history** preserves access to previous detailed records, press-event revisions and shared intervals without reintroducing that interface.

The faster provider-candidate and funnel-review path is documented in [pressure_candidate_review.md](pressure_candidate_review.md). This manual marker remains available for missed episodes and source comparisons.

## Edit or delete a saved event

- **Edit** opens the saved bounds and player selections without moving or pausing replay. Change start/end frame numbers, or use their **Use cursor** buttons. Use **Go to start** or the usual replay controls when you want to revisit the interval, then replace the primary or toggle supporting players with pitch clicks. **Save changes** appends a revision. Cancel discards only the unsaved edit.
- While editing, you can add or remove supporting pressers and replace the primary from any displayed frame in the event's original half. You do not have to move replay back into the interval first. The actual click frame is retained; selections outside the interval are flagged as retrospective role nominations, not proof of in-event observation. Event bounds remain unchanged unless you edit them explicitly. New recordings still require clicks inside their marked interval.
- **Delete** removes the saved event/interval from the active list and combined press results. It does not delete tracking frames, turn the event into a negative label, or remove the audit history. **Undo delete** restores the most recently deleted event during the current page session.
- Edits, deletions and restores append revisions. A stable event ID follows bounds edits; the interval's sequence ID changes when its native bounds change. Other analytical judgements are not silently transferred onto the resized interval. Old marker records without event IDs are supported without rewriting their original lines.
- Finish or cancel an open recording/edit before editing or deleting another event. Stale edits from another tab and collisions with an already saved interval are rejected rather than overwriting data.

## What is saved

- `.presslens/pass_reviews.jsonl`: append-only press-event records. Schema `press-marker-1.0`, review protocol `3.2`; each marker is an analyst-nominated press-positive, not an automatic detector result. Delete/restore revisions retain that original judgement and have an explicit deleted state.
- `.presslens/review_sequences.jsonl`: shared native intervals with stable sequence IDs for later measures.
- `.presslens/annotations.jsonl`: the existing detailed annotation history, preserved separately.

Press records contain reviewer/time, match/period/start/end, primary and support IDs, the frames at which those players were clicked, interval and nominated-actor quality counts, source/implementation/configuration hashes, and replay exposure disclosure. Detector/extrapolation styles are retained: a P/S outline is your role nomination, not evidence that the position was directly detected or that the player caused an outcome.

New markers also record `review_scope` from the declared policy in `config/presslens_review.json`. The policy lists `counter_attack`, `fast_break` and `repress` as `deferred_unreviewed`, with reviewer judgement and no automatic phase filter. It does not independently verify that an individual event was selected correctly. Editing/deleting/restoring older events retains their original scope; old records without a recorded scope remain unknown. Drafts started before the scope update are not silently recategorized.

Future measures can reference the same sequence ID and original input release to combine results. The current UI deliberately asks for no funnel, cue, outcome, role-function or rationale form during this initial marking pass. A nominated support player is not automatically classified as covering a receiver or route.

Unmarked time is **unreviewed**, not a negative label. A collection of selected pressure events cannot establish overall prevalence, detection recall, tactical intention or effectiveness. All current matches remain exposed development data. Data release and redistribution findings from the initial audit remain open.

## Verification

33 software tests passed, including same-period bounds, defender-team consistency, clicked-player presence, retrospective support selection during edits, unknown primary handling, source-linked interval IDs, resized-event identity, legacy compatibility, stale-edit rejection, delete/restore and preservation of review scope. Browser QA verifies marker controls, editing/deletion/undo, full-half playback, removal of the detailed form, and preservation of old annotations in the download. No automated QA records are written to the real human annotation files.

Current browser evidence: `reports/press_marker_verification.json` and `reports/replay_current_verification.json`. The current optional browser commands are `python scripts/qa_press_marker.py` and `python scripts/qa_replay_current.py`; earlier detailed-form browser scripts describe historical UI versions.
