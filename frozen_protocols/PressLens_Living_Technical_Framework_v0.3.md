# PressLens — Living Technical Framework

**Document type:** Iterative product, methodology and engineering plan  
**Version:** 0.3 (audited data and local replay/annotation foundation)  
**Established:** 26 October 2026  
**Status:** ACTIVE / LIVING — provisional methodology, intentionally revised through implementation and evaluation  
**Governing charter:** `PressLens_Frozen_Project_Charter_v1.2_FROZEN.md`

> **Guiding rule:** Observe → annotate → operationalize → implement → test → review → revise. This document records our *current best implementation ideas*, not immutable commitments. Codex should treat the formally frozen charter as the governing constraint and this document as a versioned engineering backlog. The analyst may expand, replace, or remove proposed metrics as real observations warrant, but changes and evaluation boundaries must remain traceable. Do not silently change research claims or remove evidence of past design choices.

## Implementation state after Phase 0 and the first Phase 1 increment

Phase 0 and independent carrier/context verification are recorded in `reports/data_audit.md` and `reports/carrier_context_verification/verification.md`. The raw carrier-ID field is 82.52% null over period-labelled frames and 67.82% null over phase-covered frames; 453/8,093 known-carrier possession starts disagree with event players; all 288 original phase-team disagreements lie strictly inside phases. These are source differences, not adjudicated error rates. Sixteen matches have the newer event context schema; four lack it.

The local replay/annotation viewer is implemented: run `start_presslens.cmd` on this Windows machine or `python scripts/run_presslens.py`. See `docs/presslens_phase1.md` for usage, interval conventions, disclosure and storage. It reads native tracking frames, displays detection versus extrapolation, keeps carrier/event/phase labels distinct, and stores human judgements with append-only revisions and input/configuration/implementation hashes. Provider context is optional; outcome review is separate.

All 20 matches are explicitly development with legacy exploratory exposure; no untouched holdout is claimed. Browser QA used temporary software-test annotations only. Actual analyst labels, reference agreement and tactical validity remain unmeasured. The Phase 1 software foundation is ready; the human review exit gate remains open. Phase 0 source-release/redistribution findings are unresolved. No detector, learned model, pose extension, public hosting or raw-data publication is included in this increment.

## 1. Product concept: current working interpretation

**Working name:** PressLens.  
**Current prototype format:** reusable Python analytics core plus a browser-based interactive historical match replay.  
**Primary experience:** select a permitted match and sequence, watch players and ball move frame by frame, and see candidate pressure/trigger/funnel overlays and time-synchronized explanatory metrics.

**Football sequence we currently want to illustrate (provisional interpretation):**

`observable opportunity/cue → defensive approach → restriction of particular routes → secondary cover → attacking response → observed outcome`

This is a conceptual sequence, **not** a compulsory ordering that all football situations must follow. It may branch, repeat, overlap, or be indeterminate. Manual tactical observations will inform the operational definitions before fully automatic labels are trusted.

**Current research priorities:** (1) candidate funneling and directional option suppression; (2) observable potential press cues and subsequent localized/coordinated responses; (3) explanatory spatial contributions of secondary defenders. Priority and exact metrics can change as evidence develops.

### Initial user stories

- As an **analyst**, I want to find candidate pressing sequences and replay them without watching a separate match video.
- As a **coach**, I want to understand which directional options appeared open or constrained and where supporting defenders were positioned.
- As a **developer**, I want to use the analytical functions independently of the UI, with documented inputs and outputs.
- As a **reviewer**, I want to trace every visual label to source data or a documented estimate, reproduce an example, and inspect failure cases.

## 2. Discovery gates before committing to specific algorithms

**Implementation Phase 0 must be a data-capabilities audit**, not immediate construction of a sophisticated funnel score.

### Provisional data expectations — VERIFY LOCALLY

The original SkillCorner open-data documentation describes 10 Hz, pitch-centred XY broadcast tracking, including ball and possession records, player identities and detection/extrapolation flags; match metadata; and, for the original match collection, Dynamic Events and Phases of Play. Current Cup material has advertised additional tracking matches. **Do not presume the total match count, exact schema, frame continuity or event coverage until audited.** Pose data are limited and do not form a dependency of the first prototype.

Audit outputs (files to implement):

- `reports/data_audit.md`: human-readable dataset capability map and quality limitations.
- `reports/data_audit.json`: machine-readable match/file capabilities, variable dictionary, null/missingness, coordinate/period checks, coverage by team and phase, observed/extrapolated shares, timestamp issues.
- `reports/eligibility_manifest.json`: sources explicitly allowlisted as permitted Cup data; no unknown match/video sources.
- `reports/feasibility_decisions.md`: which candidate detectors/metrics can or cannot be supported and why.

**Required questions for the audit:**

1. What matches and files are actually present? Which tracking matches also have events and phases?
2. Which fields reliably identify the ball carrier, pass initiation/reception, attacking direction by period and possession change?
3. What is the temporal alignment between event timestamps and tracking frames?
4. How often are the ball carrier, nearby defenders and receivers *directly observed* versus extrapolated or absent?
5. Can player velocities be derived reliably after segmentation and robust smoothing?
6. How many eligible candidate press/reception sequences remain after quality filters? Do not assume sufficient sample size.
7. Can an actual output sequence be shared in the public repo or pitch video under the dataset rules?

**Additional checks introduced in v0.2:**

- Inspect how provider `passing_option` events identify possible receiving targets and **when** each event is recorded. Do **not** assume these form a complete continuous catalogue of all hypothetical passing options.
- Verify `passing_option_ease_start`/`passing_option_ease_end` and analogous provider pressure/context measures: the public schema documents them at player-possession boundaries, not necessarily at every tracking frame. Confirm actual fields from local CSV headers/values before using them.
- Reconcile the event-rich, tracking-only, and two pose-covered match subsets. Maintain capability flags per match; do not let missing optional events/pose silently change denominators.
- Inspect native position/pose coordinate conventions, player identity alignment and the `is_detected` state on the actual zipped pose samples, if available.
- Measure the quality of **local route-relevant geometry**, not only whole-pitch completeness: who is visible around the ball carrier, each receiver corridor, and the secondary pressers at the intended observation time.
- Confirm any spatial library or fitted artifact can run lawfully and reproducibly using permitted competition data and permitted software. External literature may inform code, but non-permitted match data and trained football weights must not enter the computation.

**Go / adapt / stop:**

- **Go:** enough quality-supported sequence data and usable event alignment for the proposed detection.
- **Adapt:** tracking supports visual examination but certain event labels or route estimates are unreliable; implement reduced-feature mode and expose abstentions.
- **Stop that feature:** its essential observable inputs or validation references are absent. Do not fabricate supporting fields or imply empirical validity.

## 3. Version 0.2 candidate feature set — subject to change

These are **prioritized experiments**, not the final or maximum feature set.

| Area | Candidate v0.1 feature | Data dependency | Principal caveat |
|---|---|---|---|
| **Annotation-ready replay foundation** | Full-match XY replay, players, ball, possession, frame cursor, phase/event timeline, analyst bookmarks | Tracking + available metadata/events | Missing/out-of-camera objects; avoid importing external match footage |
| Pressure | Candidate presser, distance, relative closing speed, continuity | XY tracking + carrier | Approach alone ≠ deliberate pressing |
| Trigger exploration | Backward-pass reception, wide reception, and candidate coordinated movement on a temporal window | Reliable pass/reception alignment; local tracking | A cue plus response does not prove coaching intent |
| Passing options | Audited provider potential receivers + frame-wise candidate receiver/ground-pass accessibility | Dynamic Events when present + tracking | Provider event timing/coverage uncertain; model proxy not calibrated probability |
| Carrying space | Short-horizon directionally reachable/clear space | Tracking | Not observed dribble-success probability |
| Funneling | Analyst-reviewed positive/negative/uncertain candidate sequences, then measured time-varying directional asymmetry and supporting roles | Tracking + reviewed annotations + spatial estimates | A reviewed 2D sequence is not proof of tactical intention |
| Supporting defenders | Plausible route-covering role; optional model-estimated marginal positional contributions | Tracking + spatial model | Counterfactual attribution not causal player credit |
| Responses | Next pass direction, carry, turnover, dead ball, unknown | Reliable event/possession context | Must be defined separately from detection |
| Expert annotation | Bookmark intervals, label cue/press/funnel, roles, direction, uncertainty, notes and source provenance | Replay viewer + eligible tracking | Separate exploratory labels from held-out evaluation labels |
| Pose extension | Orientation, turning and facing cues where measurable | Two permitted pose matches | Detected players only; alignment error; not required for core |
| Quality | Observed/extrapolated share in relevant regions, tracking gaps, abstention reason | Tracking | Avoid misleading complete-pitch claims |

**Open design principle:** Additional metrics (for example approach-angle descriptors, spatial-control variants, coverage change, press delay, receiver separation, option-value proxies or pose-derived indicators) may be added when feasible. Metric removal is also acceptable where validity is inadequate.

## 4. Observation-led tactical interpretation and detection pipeline

### 4.0 Expert-guided annotation before fully automatic funnel classification

**Proposed first operational artifact:** a complete 2D match replay/annotation environment built only from competition-permitted tracking and events. The analyst can examine full matches (or stratified candidate windows), mark examples and counterexamples, and revisit them with synchronized spatial measurements. This is not an invitation to use prohibited broadcast video.

**Initial annotation schema (mutable):**

| Field | Proposed content |
|---|---|
| Episode identity | Match, defending team, period, start/end frame, possession and source provenance |
| Context | Phase, attacking direction, ball-carrier identity, coverage/visibility summary |
| Tactical candidate labels | `press_candidate`, `funnel_candidate`, `non_funnel_pressure`, `no_press`, `uncertain` |
| Functional description | Primary presser, possible secondary defenders, blocked/surviving direction, temporal boundaries |
| Candidate cue | Observable cue category, time, visual evidence, cue absent/unknown option |
| Analyst judgement | Label rationale, evidence frame(s), reviewer, timestamp, annotation version and uncertainty |
| Outcome (separate pass) | Next attacking action and later resolution; cannot enter the onset detector as a predictive feature |

**Annotation principles:**

1. Review **positive, negative, ambiguous, and indeterminate** sequences; include pressure episodes without funneling, wide play without directed pressure, and backwards passes without a coordinated response.
2. Create an **observation-only annotation pass** that focuses on geometry and movement before showing optional future outcome overlays, wherever practicable. Keep the later outcome review separate to mitigate hindsight bias.
3. Annotate the observed *pattern consistent with* a funnel, not a verified coach instruction or an incontrovertibly 'true' funnel.
4. Maintain **development and evaluation partitions** from the outset. Prefer splitting by complete match to prevent near-duplicate tracking-frame leakage; do not use held-out matches to choose definitions or thresholds. If no credible held-out sample remains, report evaluation as exploratory.
5. Where feasible, ask a second football-informed annotator to review a concealed subset and report label agreement/disagreement; otherwise state explicitly that reference annotations are single-reviewer judgements.
6. Record each annotation revision and the reasons for changed labels. When methodological revision requires examining a held-out case, it ceases to be independent validation data for that revised model.

**No invented annotation count or pass/fail thresholds:** Determine workload, annotation sampling and class balance after the actual data audit; revise the plan with evidence. The eventual labelled corpus is derived solely from permitted tracking reconstructions and eligible metadata, not external videos or scout labels.

### 4.1 Canonical data representation

Define an internal schema independent of SkillCorner's raw release shape. Tentative tables/objects:

- `Match`: match identity, pitch dimensions, participant IDs, period directions, input capabilities.
- `Frame`: match/period/frame/time, ball state, possession team/carrier, frame quality.
- `PlayerFrame`: player/team/XY, detected vs extrapolated state, smoothed kinematics if valid.
- `Event`: event category, start/end frames or timestamps, linked players, observed/provider labels, alignment uncertainty.
- `Sequence`: start/end, stage markers, candidate classifications, observability, subsequent outcomes.
- `MetricSample`: name, time, value/unit, method/version, sources, quality and uncertainty.

Keep `unknown` as an explicit value. Period transitions, substitutions, tracking gaps and implausible coordinate jumps break continuity where appropriate. Don't interpolate across unknown players to create apparently observed tactical geometry.

### 4.2 Candidate press detection — informed by reviewed examples

**Initial concept, not a fixed definition:** Identify continuous intervals where one or more defenders exhibit geometry and movement consistent with pressuring a reliably known ball carrier. Use manually annotated positive and negative sequences to examine which observable features discriminate genuine pressing from ordinary marking, recovery running or simple proximity.

Possible signals: distance/relative closing speed, primary presser approach vector and approach angle, pressure persistence, position relative to option routes, nearby defender movement, plus provider engagement/pressing-chain labels as **supporting comparisons** where available. A proximity-only baseline is mandatory for evaluating added value. Use continuity and hysteresis to avoid identity switches when defenders cross.

Don't optimize thresholds against the final outcomes or use held-out validation matches during initial feature selection. Abstain when essential actors or frame intervals are not observable.

### 4.3 Potential pressing cues and response patterns — open research module

**Purpose:** Explore measurable patterns associated with press onset and coordinated defending; do not assume a complete causal trigger taxonomy.

- **Initial observable cue candidates:** backward pass, backwards-facing/wide reception *only if verifiable*, wide ball location, changes in ball speed or receiver control *only if robustly reconstructable*. The initial reliable core remains backward-pass and wide-reception flags.
- **Response signatures to investigate:** localized increases in defender closing velocity, directional approach changes, synchronized support movements, spatial compacting around candidate outlets, emerging asymmetry in passing/carry space. Time-window definitions remain configurable and require empirical review.
- **Necessary negative controls:** the *same* cue types **without** subsequent collective pressure, and comparable pressing responses **without** the nominated cue. This guards against defining a 'trigger' by selecting only examples where a press followed.
- **Timing:** candidate cue time must be established separately from, and precede or coincide with, identified defensive response onset. Save window boundaries, observed movement and alternative contextual explanations.
- **What can be claimed initially:** `cue observed`, `subsequent press-like response detected`, `response pattern associated with cue`. Do not output `intentional trigger confirmed` or a causal explanation.
- **Pose as optional investigation:** two permitted pose matches may help with orientation/turning estimates and tests of **incremental value** versus XY-only detection. They cannot be mandatory for running all-match/10Hz detection or used to assert reliable body-orientation labels without measuring quality and alignment.

**Potential originality path:** A transparent, benchmarked cue→coordinated-response detector may become a major contribution independently of the funneling module. Its novelty must still be compared with provider/event methods and published research.

### 4.4 Continuous passing/carrying accessibility and value — model comparison

**The modelling question:** From each analysis frame, estimate which *feasible directions or candidate receiver routes* remain relatively accessible, not the objectively knowable result of a pass that was never taken.

Three distinct evidence channels:

1. **Provider potential-receiver events** (`passing_option` where supplied): inspect actual recording criteria, times, participating players and false/missing event cases. These may represent detected target opportunities, but **must not be assumed to constitute the complete time-continuous option set**.
2. **Provider possession-boundary context** (e.g., `passing_option_ease_start/end`, `overall_pressure_start/end`, `time_to_impact_start/end` when verified): treat as vendor model outputs attached to documented observation points, not frame-level ground truth or independent labels for our own scores.
3. **Independent frame-wise model outputs**: implement a transparent pass-interception/accessibility baseline and compare with an appropriately licensed, physically grounded option/space model (e.g., `accessible-space`) if it can be run with eligible inputs and legal dependencies. Pitch-control surfaces, pass success feasibility and spatial/EPV value **answer different questions**; represent them as distinct layers and do not silently treat pitch control as pass probability.

Options to evaluate in development:

- Receiver-directed ground-pass corridors and possible interception by opposing defenders.
- Access to *unnamed locations* or pass endpoints, if the model supports it, without treating off-camera receivers as known.
- Directionally binned short-horizon carrying clearance, identified as a geometric proxy rather than a dribble-success probability.
- Option value/EPV **only** when the model's data requirements are legal, reproducible and distinct from feasibility; never multiply unvalidated scores and call the result a calibrated probability.
- Continuous changes: per-route/sector delta from a clearly defined **earlier baseline** and frame-to-frame evolution, with defender and carrier motion taken into account.

**Performance strategy:** Start with modest temporal sampling or selected sequence precomputation; test interpolation and caching with no false frame precision. Label every output with `observed/provider/modelled/analyst`, tracking coverage and applicable uncertainty.

### 4.5 Candidate funnel detection and defensive-role explanations

**Derive from reviewed examples** rather than defining a funnel from only a single asymmetry threshold. Candidate components to measure are (i) an active press-like approach, (ii) restriction or reduction of one set of attacking directions relative to context/baseline, (iii) a comparatively surviving route, and (iv) secondary-defender movement/position that is plausibly able to restrict that surviving outlet or lead the carrier toward a controlled area. These components may arise at different times.

Potential evolving labels (not fixed): `toward_touchline`, `toward_center`, `toward_backward`, `directional_press_without_verified_funnel`, `incomplete_support`, `unclassified`, `indeterminate`.

**Competing explanations to test:** touchline geometry, ball location, natural team shape, attacker/receiver movements, possession tempo, extrapolated players and the pass/ball trajectory. A model should not assign funneling merely because a wide player has fewer directions available.

**Role and credit extension:** Begin with descriptions such as `primary_pressure`, `possible_lane_screen`, `secondary_outlet_coverage`, `unknown`. Later, compare baseline option accessibility with a *model-defined alternative* (e.g. omit one defender's influence or relocate them under controlled assumptions) to estimate marginal positional contribution. Explicitly state that these counterfactual changes are **conditional model contrasts**, not observed effects of removing the defender, private intent, or causal credit for the outcome. Team interactions mean effects need not be additive.

**Abstention:** If route-relevant player positions or supporting movement are inadequately observed, output `indeterminate` with a reason. Show the analyst the actual available geometry, never invent supporting players or a fully known attacking landscape.

### 4.6 Subsequent outcomes — independent labelling

Classify the next reliably observed action/sequence resolution *after* the detector's observation window:

- `backward_pass`, `lateral_pass`, `forward_pass`;
- `progressive_carry`, `nonprogressive_carry`, where reconstructable;
- `possession_loss`, `out_of_play`, `other`, `unknown`.

Optional: `long_ball`, `switch_escape`, `touchline_containment`, `press_broken`, **only with credible explicit definitions and enough observed evidence**.

Do **not** default to binary “funnel succeeded” versus “failed.” A backward pass, touchline carry or turnover has a different tactical meaning depending on context. If a coaching-oriented normative rule is later created, label it as a selected evaluation rubric rather than objective truth.

## 5. Metrics registry and how to expand it safely

Every public metric should have a registered schema:

```yaml
metric_id: "candidate_primary_presser_closing_speed"
version: "0.1.0"
display_name: "Presser closing speed"
category: "pressing"
source_type: "computed_from_tracking"  # observed | provider_model | model | heuristic | human_label | outcome
unit: "m/s"
input_requirements: ["carrier_xy", "defender_xy", "continuous_timestamps"]
observation_time: "frame_time"
lookahead_used: false
quality_policy: "unknown_if_track_gap_or_invalid_velocity"
validation_status: "prototype_only"
method_reference: "docs/metrics/closing_speed.md"
```

**Addition/update protocol:** propose metric → state tactical purpose and existing alternative → check required data → implement and unit-test → compare to baseline/reviewed examples → document quality limits → expose in UI when meaning is defensible → increment metric or method version. Changing a definition requires an output-version change or explicit migration note; never silently reinterpret historical exports.

### Initial dynamic metric groups

- **Pressure:** nearest/primary presser distance, closing speed, approaching direction, candidate time-to-arrival *if physically defensible*.
- **Opportunity:** estimated receiver route accessibility, available direction counts/sums, separate carrying-clearance proxies.
- **Directionality:** inside/outside, forward/backward access comparison and within-sequence change.
- **Coordination:** geometry of secondary cover of surviving routes, rather than mere number of nearby defenders.
- **Sequence:** time since cue/onset, observed next action, outcome and quality flags.
- **Trigger/response:** relative timing of cue and press onset, number of defensively responsive actors (defined by motion, not arbitrary proximity), temporal coordination descriptors.
- **Defensive roles and model attribution (experimental):** measured coverage effects and alternative-config positional differences, clearly labelled conditional estimates.
- **Pose (only on supported matches):** exploratory orientation/turning descriptors with joint uncertainty and alignment quality.
- **Model comparisons:** proximity-only baseline, spatial accessibility baseline, and any advanced alternative method, with the same quality filters and evaluation partition.

No uncalibrated `turnover_risk_%`, `forced_direction_confidence_%`, `press_success_probability`, or similar probability-sounding figures.

## 6. Replay and annotation UI — tentative v0.2 concept

**Preferred layout (changeable):**

1. **Full-match review and annotation:** playback of permitted tracking (no broadcast video), frame stepping, bookmarks, temporal intervals, on-pitch markups and editable candidate/negative/uncertain tactical tags. Analyst decisions are stored with user, annotation version, and justification.
2. **Match/sequence filter:** match, defending team, event phase, cue type, candidate funnel type, quality, outcome (when known).
3. **Central 2D pitch replay:** players and ball, arrows or trails for observed movement, primary presser highlight, secondary cover, accessible/suppressed pass corridors, directional sectors.
4. **Metrics rail:** 5–8 prioritized frame-synchronized indicators, with units, confidence/quality labels, toggles and plain-language interpretations.
5. **Timeline:** cue marker, pressure onset, route restriction, secondary cover, next action, possession resolution; play/pause/frame step/speed/scrub.
6. **Details/export:** why sequence was flagged, which conditions fired, exclusions/unknowns, JSON/CSV/Parquet export, static graphic, optional tracking-derived animation where lawful.

**Visual semantics:** analyst-annotation markers must remain distinguishable from provider/algorithm labels; solid movement path = observed/known; dashed/transparent trajectory = hypothetical or modelled; shaded sector = an estimate of opportunity, **not measured tactical intention**; gray/hatching or warning = uncertain/incomplete. Include readable legends and a color-blind-considerate alternative.

**“Live”:** calculations update *as the user replays historical frames*. Metric computation can be preprocessed/cached for smooth playback; actual broadcast/live-match integrations are out of scope for this Cup build.

## 7. Suggested architecture — not frozen

Preferred starting stack: Python 3.11+, `numpy`, `pandas` or `polars`, `scipy`, `plotly`/Matplotlib, `pytest`, and a lightweight open-source interface such as Streamlit. Choose between alternatives based on tested responsiveness, licensing and reproducibility.

Possible repository layout:

```text
presslens/
  pyproject.toml
  LICENSE.md
  README.md                       # <=1000 words; <=2 figures/tables combined
  src/presslens/
    io/                           # eligibility + schema adapters
    tracking/                     # normalization, temporal quality, kinematics
    detection/                    # candidate presses, cues, funnel states
    annotations/                  # review schema, audit trail and split assignment
    models/                       # accessible space, pass/carry proxies
    metrics/                      # registry + provenance
    outcomes/                     # subsequent actions, integrity checks
    visualization/                # pitch frames, overlays, replay payloads
    validation/                   # held-out comparisons + sensitivities
    baselines/                    # proximity/press-event/spatial reference methods
    cli.py
  app/                            # exploratory UI
  config/                         # tested defaults + source allowlist
  tests/                          # synthetic fixtures, no match data
  docs/
    prior_art.md
    annotation_protocol.md
    metrics/
    methodology.md
    development_log.md
    validation.md
  reports/                         # generated outputs (no restricted raw data)
  .gitignore
```

Candidate command interface, to be adapted during implementation:

```bash
python -m presslens audit --data-root /path/to/permitted/skillcorner
python -m presslens annotate --match-id MATCH_ID  # or equivalent in-app workflow
python -m presslens analyze --match-id MATCH_ID --config config/prototype.yaml
python -m presslens export --match-id MATCH_ID --format json
streamlit run app/main.py
pytest -q
```

These are **proposed API contracts**, not claims that the code already exists.

## 8. Validation, evidence boundaries and added-value evaluation — evolving plan

### Component-level validation plan

1. **Data integrity** — audit coordinates, ball/carrier identity, team direction, time alignment, missingness and pose/tracking alignment where relevant. Record eligibility and quality denominators, not just successful renderings.
2. **Human reference labels** — develop an explicit annotation guide; label candidate positive, negative, borderline and unknown examples from permitted XY replay. Preserve annotation authorship and rationale. Optional second-reviewer agreement analysis measures annotation consistency, not tactical intent.
3. **Design versus evaluation split** — group by match/possession episode, not random adjacent frames; use exploratory labels to design rules, and untouched sequences/matches for the reported test. Do not repeatedly retune to held-out errors while presenting the same set as independently validated. Track exploratory and confirmatory status.
4. **Press identification** — compare geometry-based press onset and presser selection to human annotations, a proximity-only baseline, and vendor events where provided. Vendor labels are not independent ground truth.
5. **Funnel classification** — evaluate against unseen expert candidate labels, including ambiguous and no-funnel episodes. Examine both false positives and false negatives, touchline-geometry confounds and uncertainty/abstention policy.
6. **Option models** — check physical consistency, local tracking sensitivity, agreement with observed next actions **without using them as in-frame labels of unchosen-route success**, plus comparisons to alternate licensed spatial models. Explicitly test extrapolation and perturbations.
7. **Trigger-response analysis** — compare cue-positive/response-positive episodes against cue-positive/no-response and response-positive/no-cue negatives. Report temporal lead–lag statistics descriptively; do not assert that an association reveals tactical instruction or causality.
8. **Defensive-role/model contribution** — check that role descriptions track reviewed movement and that marginal accessibility estimates behave sensibly; compare multiple defenders jointly and label all counterfactuals as model-only.
9. **Outcome integrity** — independently define subsequent actions with no future information in onset or funnel detection; inspect event-to-frame alignment and classification coverage.
10. **Coach/analyst usefulness** — compare a PressLens review against a basic tracking replay plus pressure label on matched candidate and negative episodes. Capture which additional tactical questions can be answered and how clearly, rather than presupposing added value.
11. **Reproducibility/visual honesty** — verify source restrictions, license metadata, cache reproducibility, algorithm/config provenance, clean environment and distinct observed/provider/model/annotation visual legends.

**Metrics for evaluation (choose based on the verified sample):** labelled confusion matrices; per-class precision/recall where meaningful; annotated time-onset deviation; agreement/uncertainty and abstention rates; quality-stratified error analysis; timing/alignment audits. Publish denominators and do not invent p-values, confidence bands, detector performance or generalization results.

**Evaluation contamination policy:** New methods developed after inspecting held-out mistakes must be treated as exploratory on those same examples. If possible, create a new untouched test partition for later final claims. Within the small Cup sample, clearly report when this is impossible.

### Change/feedback template

```text
Change ID / date:
Football concept / example prompting change:
Data scope and permissible source check:
Existing approach / relevant prior art:
Current observed failure or limitation:
Proposed metric/model/annotation change:
Design examples used (match IDs; no held-out leakage):
Expected benefit (hypothesis, not empirical result):
Tests, evaluation split and manual review:
Measured outcome / output files / commands (only after running):
New limitations, regression risks, status: accept / refine / revert / defer:
Affected metric/config/schema versions and UI provenance:
```

## 9. Iterative build plan — current priorities, not a fixed waterfall

| Phase | Goal | Exit evidence (only after execution) | Notes |
|---|---|---|---|
| **0 — Data audit** | Prove input eligibility, schemas, event/pose availability and local tracking quality | Inventory, provenance, quality and time-alignment reports | No assumptions about actual positive case count |
| **1 — Replay + annotation** | Build complete tracking-only match viewer and expert candidate/non-candidate annotation | Verified replay, reviewer labels and explicit development/evaluation partition | First major user-facing artifact; manual observations direct methodology |
| **2 — Spatial foundation** | Benchmark pass accessibility, carrying clearance, pressure and quality indicators on annotated episodes | Metric definitions, computed examples, baseline comparisons, sensitivity and unknown states | Keep pass feasibility vs value distinct |
| **3 — Press/trigger response prototype** | Identify pressure onset, potential cues and coordinated movement signatures | Reviewed positives and negatives, timing audit, baseline comparison | Trigger contribution may stand independently |
| **4 — Funneling + defender roles** | Relate dynamic direction suppression to primary and secondary positions and movements | Unseen-case comparison, role audit, ambiguous examples | Attribution only model-conditional unless justified otherwise |
| **5 — Insightful product** | Integrate replay-synchronized indicators, explanations, filtering, annotations, exports | Usability demo and added-value comparison | Avoid generic dashboard bloat |
| **6 — Evaluation + submission** | Report honest validity/limits, clean reproducibility, disclosure and licensed release | Test evidence, documented constraints, reproducible demo, compliant GitHub/video | Pin **release snapshot**, not the future method |

The review/annotation interface must be usable before we ask the analyst to identify an entire match manually. Subsequent phases can overlap and loop. Each stage should deliver testable value; no requirement to finish all optional metrics before showing a working prototype.

**Earliest viable end-to-end demonstration:** an independently auditable tracking-only segment with: aligned frame/phase, editable expert tactical annotation, candidate presser/response, one defensible time-varying spatial metric, on-pitch evidence-quality indicator, and the later attacking action displayed distinctly. Automatic funnel classification comes only after component-level review supports it.

## 10. Versioning, decision log and collaboration with Codex

### Document version rules

- `v0.1`: archived initial engineering proposal.
- `v0.2`: preserved observation-led proposal before the executed audit and viewer.
- `v0.3`: records executed audit findings and the local replay/annotation foundation; human review remains pending.
- `v0.3`, `v0.4`, ...: meaningful revisions after audits/prototypes; append a change-log entry.
- `v1.0`: a tested competition release of the *living technical framework*, not a declaration that future improvements are forbidden.

### Method and output versioning

All derived outputs should include: `metric_version`, `detector_version`, `config_hash`, `code_commit`, `input_manifest`, `timestamp/period`, `quality_flags`, and `result_provenance`. Recompute or clearly label comparisons across different versions.

### Codex working contract

1. Read **the frozen charter first**, then **the latest living framework**, then historical specs only as reference.
2. Start Phase 0 by inspecting the real permitted files. **Never guess columns, invent events, or fetch extra football datasets.** Then build annotation-ready tracking replay before claiming an automatic tactical detector.
3. Implement in small testable increments; surface alternatives when observed data invalidate the current approach.
4. For each increment report actual files changed, commands executed, passed/failed tests, detected uncertainty and suggested framework edits.
5. Treat newly discovered footballing requirements as **proposals to update the living framework**, not as violations of an old feature list.
6. Do not change frozen principles, loosen data restrictions, invent performance results, or silently expand sources. Do not treat manual funnel labels as proof of intent or developer-set rule outputs as evaluation ground truth.
7. Update the decision log, metric registry and documentation together with each material algorithm/threshold/output change.
8. Before submission, pin a **release configuration** that exactly reproduces the pitch and reported figures; retain a record of exploratory development.
9. Register every data-dependent parameter choice, borrowed algorithm and prior-art comparison; seek explicit project-owner direction when implementation choices materially change the tactical story, rather than presenting them as frozen requirements.
10. Protect evaluation partitions: a prompt that tells Codex to inspect the held-out cases to optimize detection is a methodology change requiring disclosure and usually a new evaluation set.

## 11. Prior art, data legality and optional research extensions

**Existing capabilities to benchmark, not rebrand:** SkillCorner pressure measures, press engagements/pressing chains, `passing_option` events and passing-option ease, tracking playback, simple pitch-control visuals; the published open-source bait/escape/pressing-trap project (`Danielbala-code/football-press-bait-escape-analysis`); research on pressure visual analytics, counterpressing detection and option accessibility. **Verification of specific implementation overlap remains an ongoing engineering task.** Keep references and licence notes in `docs/prior_art.md`.

**Candidate optional experiments:**

- **Pose incremental-value study** restricted to the two eligible 25Hz pose matches; compare XY-only vs XY+pose explanations with detection/alignment and missing-player exclusions. Do not import any external clips.
- **Defensive marginal-accessibility contribution** based on controlled model variants, labelled as a sensitivity calculation, not causal defensive credit.
- **Cue response typology** based on lead-lag defender motion (single presser, localized coordinated response, incomplete response, unsupported response) and explicit negative examples.
- **Option-value layer** distinct from geometric feasibility and calibrated completion probabilities, only if legally and computationally justified.

**Reference evidence files (historical, not governing):** `PressLens_PreFreeze_Prior_Art_Review_2026-10-26.md` and `PressLens_Value_Feasibility_Audit_v0.1.md`. These are assessments, not proof that any implementation has passed the proposed feasibility tests.

## 12. Current open decisions (deliberately unresolved)

- Which exact tracking/event files cover the current permitted match inventory?
- What is the safest frame-alignment method for passes and possession changes?
- What coverage threshold should force a funnel label to be `indeterminate`?
- What simple accessible-route model is reliable enough for the first prototype, and is a more advanced model worth its complexity?
- Which sectors best represent real footballing funneling: inside/outside, central/wide, directional angles, or a combination?
- How should supporting coverage be represented without claiming individual causal credit?
- Which outcome labels can be reconstructed consistently?
- Is a Streamlit pitch animation sufficiently responsive, or is a different open-source front end necessary?
- What constitutes a useful validated demonstration for a coach, beyond visual plausibility?

These are development questions to *resolve through building*; none requires a full research-paper protocol in advance.

## 13. Change log

| Version | Date | Change | Evidence / trigger |
|---|---|---|---|
| **0.1** | 2026-10-26 | Separated stable charter from living implementation. Established exploratory metrics, audit-first detection pipeline, dynamic replay and validation gates. | Project-owner decision to let implementation shape methodology. |
| **0.2** | 2026-10-26 | Aligned with approved charter; elevated full-match manual review and annotation, partition discipline, continuous option feasibility vs value, support-role analyses and cue→coordinated response; added optional pose and conditional defensive credit; revised development order. | Project-owner proposals to overcome limitations 1–8, prior-art assessment and direct data-capability audit. No new detector validated. |
| **0.3** | 2026-10-26 | Recorded Phase 0 findings and independent verification; corrected governing charter to v1.2; implemented hash-gated local replay, explicit exposed-development partition and versioned human annotation workflow. | Ten software tests, 20 match loads / 80 period-boundary records, browser flow on verified conflict cases. No human tactical labels or detector validation. |

---

**Next intended action:** Use the Phase 1 viewer to collect actual positive, negative and uncertain observations, with roles, cue evidence and rationale. Review label consistency and source conflicts before operationalizing automatic metrics. Resolve source-release and redistribution questions before publication; establish a defensible evaluation protocol rather than declaring previously exposed matches untouched.
