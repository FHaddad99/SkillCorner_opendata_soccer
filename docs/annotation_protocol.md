# PressLens annotation protocol 2.0

This is the historical detailed-form protocol. That tab/form has been removed from the current UI at the owner's request; the saved schemas and original records remain intact and available in review-history downloads. The current workflow is the [simple press-event marking pass](press_event_marking.md), excluding counter-attacks and fast breaks for this pass.

Software version: 0.2.0. This protocol implements the refinements identified while reviewing the first human annotation. It defines PressLens review fields; it is not a universally agreed football taxonomy, detector or validated measurement scale. The frozen charter remains unchanged.

## Two independent questions

| Question | Choices | Operational meaning |
|---|---|---|
| Press-like response | Present, absent, uncertain, not assessed | Judge whether observed movement is consistent with an active press-like approach/response. Presence alone does not establish directional funneling, intention or effectiveness. |
| Directional funnel | Candidate, no funnel apparent, uncertain, unassessable, not assessed | Assess whether pressure/support geometry appears to restrict alternatives toward a surviving direction or route. Keep observed negatives, unresolved interpretations, unavailable evidence and unreviewed cases distinct. |

“No funnel apparent” is a pressure-without-funneling judgement. It requires press presence, a reviewer assessment that relevant route/support visibility is adequate, and a written route/support rationale. Missing receivers or uncertain geometry are not silently converted into negative examples. A funnel candidate also requires press presence, a rationale and an assessed level of visibility. The application checks these declared combinations; it cannot establish that the reviewer judged them correctly.

`funnel_observability` is separate from uncertainty: adequate, limited, essential geometry unavailable, or not assessed. An unassessable funnel requires limited/unavailable geometry. Competing interpretations with visible geometry can instead be uncertain. These are operational reviewer choices; no numerical visibility threshold is claimed.

Defaults are not assessed. The application does not automatically relabel existing examples or derive funnel status from subsequent outcomes.

## Uncertainty and defending roles

Press, funnel, candidate cue and primary-role judgements each have their own uncertainty: low, medium, high or not assessed. These are ordinal human judgements, not calibrated probabilities. Do not copy one confidence judgement across claims with different evidence.

Nominate a primary presser and, optionally, the attacking player they approach. These are manual nominations kept separate from the raw tracking/event carrier fields.

Each supporting defender can have a function, optional opposing target, route/role description and uncertainty:

- Approach carrier.
- Cover a named receiving target (target required).
- Cover a described route (description required).
- Other observed support function (description required).
- Not assessed.

Role players must belong to the nominated defending team; named targets must belong to the opposing team. Distinct defenders fill primary/support slots. Assigning a player does not prove that they performed the nominated function.

The form displays nominated actors' detection/extrapolation states at the current frame. Saves also include `actor_visibility` over the observed interval for nominated defenders, attacking player and receiver targets. Absent players and invalid XY remain separate from extrapolation. These counts describe provider flags; they do not independently verify identities, receiver locations or route accessibility.

## Stage bookmarks and observation boundaries

- **Context start** may precede the observed interval and stays in the same period.
- **Observation start/end** delimit the particular response being judged; they do not have to equal a provider possession interval.
- Optional stage bookmarks identify nominated cue, press-response onset, reception and attacking-action end. Each must be a real source frame within the context/observation window and the same period.
- Evidence frames can include prior context. Clicking an earlier stage's “Set cursor” extends context start without changing the observed interval. Evidence chips can be removed individually.
- Cue after onset is flagged as not a preceding-cue claim. An onset paired with a no-press judgement is flagged for review. A single evidence frame warns that movement needs temporal review. These are review warnings, not detector outputs or forced footballing sequences.

For the first annotation, provider comparison anchors are pass at 29, Warland reception at 42 and release at 60. The analyst must choose their own onset and boundaries. These anchors were not automatically written into the human annotation. The existing backward-pass cue can be used explicitly; kickoff context can be documented in the rationale. A received backward pass does not establish a trigger that caused an earlier approach.

## One direction convention

All directions now use the attacking team's reference:

- Forward/backward: toward/away from the attacking team's target goal.
- Left/right: lateral sides while facing the attacking direction, not the carrier's inferred body orientation or screen left/right.
- With attack along native +x, attacking-left is +y; with attack along −x, attacking-left is −y.

The viewer retains native XY positions. The form shows the coordinate reference for the **annotated period**, even if the cursor moves to another half. Saves include attacking team and native axis signs. No body-facing estimate is produced.

## Replay disclosure and separate follow-up passes

Record whether later raw replay has been viewed: yes, no, or unknown, plus a reviewed-through frame when known. Include exposure in earlier sessions, not just the current form.

The client also records its maximum actually displayed frame for each match/period in browser-tab session storage and submits it on save. Frames prefetched for playback are not automatically counted as displayed. The server validates native frame/period references and retains a maximum for the active review session. This is browser-reported exposure evidence, not independent measurement of what a person watched.

`future_replay_exposed` is true if any submitted same-period maximum exceeds the observation end, the reviewer answers yes, or a prior revision recorded exposure. It is unknown when the disclosure/history is unknown, including previously unmeasured legacy exposure. It is false only when the available disclosure says no and neither displayed-frame evidence nor prior history contradicts that. Previously recorded exposure cannot be erased by selecting no in a subsequent revision.

Provider outcome-panel exposure remains a separate provenance flag. A false provider-panel flag is not evidence that no subsequent raw action was watched. No flag establishes strict blinding or untouched evaluation status.

Use **Outcome & quality** after saving an observation:

- Save data-quality notes independently, with reviewed-through disclosure. This does not require opening provider outcomes. Describe a suspicious reconstruction or competing sources as unresolved until verified; do not repair the data by assertion.
- Reveal provider outcomes explicitly and save a separate outcome judgement. This does not update the observation's press/funnel values.
- Follow-up saves append revisions and retain the original observation. Interval boundaries become fixed after an outcome/data-quality follow-up; a different interval needs a new annotation.

Observation-window notes remain available, but later passing sequences or suspected future tracking errors belong in the separate follow-up. The software does not infer hindsight from free text.

## Existing annotations and schema versions

The real annotation JSONL is never rewritten during an upgrade. Schema 1 records remain readable. The UI shows original flat label, global uncertainty, mixed-direction values and notes; new independent assessments/uncertainties/directions initially remain unassessed/unknown. Existing player nominations and frame intervals can be reviewed without inventing new tactical judgements.

The reviewer can explicitly copy original notes into a quality-review draft. Copying does not save or reinterpret them automatically. Saving an observation under the new protocol appends schema 2 with explicit new choices and links the preceding revision. Original schema 1 text remains in history. A quality/outcome follow-up on an unchanged schema 1 observation retains schema 1, with `review_protocol_version=2.0` recording the current review workflow.

New schema 2 observations contain `press_assessment`, `funnel_assessment`, `funnel_observability`, per-claim uncertainty, `supporting_roles`, `stages`, `direction_reference`, and a separate `funnel_rationale`. `replay_review`, `quality_review`, `actor_visibility` and existing provenance are retained separately. Exports can contain records of multiple schema versions.

All 20 matches remain exposed development data. These refinements do not establish independent validation, sufficient sample size, inter-reviewer agreement or release/redistribution permission.
