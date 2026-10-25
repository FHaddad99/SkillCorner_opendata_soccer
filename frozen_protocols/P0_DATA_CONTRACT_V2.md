# P0 — SkillCorner data contract and hypothesis feasibility
Date: 2026-10-24 | Status: DOCUMENTATION REVIEW PARTIAL; LOCAL FILE ACCESS PENDING
Governing framework: SCIENTIFIC_PROTOCOL_V2_FROZEN.md. This supplement does not amend the frozen hypotheses.

## A. Source-of-truth hierarchy
1. Actual, user-authorized local competition files and their metadata; 2. SkillCorner's official schema/specifications and code/tutorials; 3. independently verified field behavior in a *bounded* representative development sample; 4. outside literature as modelling inspiration only. No additional match observations or video.

Public repositories examined: https://github.com/SkillCorner/opendata and https://github.com/FHaddad99/SkillCorner_opendata_soccer (master branches, accessed 2026-10-24). Both GitHub directory listings currently contain 20 match IDs, even though the official README says 10. Thus 20 *directories* are confirmed online, but completeness and validity of 20 local four-file bundles have not been established. The local macOS path is not mounted in this execution environment.

## B. Confirmed public-file contracts
| Source | Grain and primary linkage | Documented relevant fields | Constraints and status |
|---|---|---|---|
| `data/matches.json` | Match index | `id` | Inspect full content before deriving match eligibility. |
| `{id}_match.json` | Match + roster metadata | match/team/player IDs, pitch size, `home_team_side`, home/away scores, substitutions/start/end times | Final match score is NOT time-varying game state; do not use it as the current score. Direction must be verified per period. |
| `{id}_tracking_extrapolated.jsonl` | Match, period, frame (10 fps), with nested player rows | `frame`, `timestamp`, `period`, `player_data`: player ID, x/y, `is_detected`; `ball_data` x/y/z, is_detected; `possession` player_id/group; camera projection | Metres, origin pitch center; some player IDs erroneous (~97% accurate per vendor), speed/acceleration require smoothing. Observed and extrapolated are different uncertainty classes. |
| `{id}_dynamic_events.csv` | Event rows; `event_id` unique **within match** | Documented player_possession EPV, pressure, reception difficulty, time-to-impact, space constraint, passing-option ease; event timing and taxonomies require specifications inspection | EPV/pressure only populated on `player_possession` rows. Event x/y require conversion; not automatically tracking metre coordinates. 1–5 ordinal constraint bands should not be assumed interval-scaled. |
| `{id}_phases_of_play.csv` | Start/end frame intervals | Concurrent possession and out-of-possession phase categories | Only ball-in-play; phase labels and category mapping require exact CSV/spec. Join by same match, period and interval, not event ID. |
| `data/aggregates/*csv` | Player season aggregate | physical, off-ball run, passing features | Season-level aggregates include other games. **Do not** join these as if generated solely from the competition match sample or treat as match-level ground truth. May use descriptively only after competition-rule interpretation. |
| `data/bodypose/*` | Match, period, 25-fps frame, player, joint | 29 `joints` with XYZ and `p90_mae_cm`; 2 match IDs 1925299 and 1996435 | Pose only for detected players, joints null in many frames; ~1/3 player-frames populated per README, 25 Hz vs tracking 10 Hz, separate modelling pipelines may misalign XY, z relative to centroid. Download/checksum recipe exists; do not assume two complete local pose files already downloaded. |

Official docs: https://github.com/SkillCorner/opendata/blob/master/README.md ; https://github.com/SkillCorner/opendata/blob/master/data/bodypose/README.md ; https://github.com/SkillCorner/opendata/blob/master/notebooks/tutorials/README.md
Official linked Dynamic Events specification: https://26560301.fs1.hubspotusercontent-eu1.net/hubfs/26560301/Guides/Dynamic%20Events/20250216%20-%20Dynamic%20Events%20CSV%20Specifications.pdf
Official linked Phases specification: https://26560301.fs1.hubspotusercontent-eu1.net/hubfs/26560301/Guides/Phases%20of%20Play/20250216%20-%20Phases%20of%20Play%20CSV%20Specifications.pdf
The two linked PDFs were NOT retrievable from the web interface during this run. Consequently, do NOT describe event taxonomies or phase categories as verified against the formal PDFs.

## C. One canonical analysis canvas (without a giant merged table)
1. `match_context` (match_id, team/player lookup, pitch size, team attack direction **per period**, game time; score only if actual time-stamped goal events available).
2. `tracking_frame` (match_id, period, frame, timestamp, ball, possession, coverage flags).
3. `player_frame` (match_id, period, frame, player_id, team_id, x/y, detected flag, smoothed velocity + reliability flag).
4. `event` (match_id, event_id, original columns, timestamp/frame keys once verified, source event category, EPV/pressure field presence).
5. `phase_interval` (match_id, period, start_frame, end_frame, attacking and defending phase label; exact names to inspect).
6. `pose_joint` (match_id, period, pose frame, player_id, joint, XYZ, p90 uncertainty), plus derived player pose features.
7. `decision_snapshot` (match_id, possession/episode ID, time t, carrier and surrounding player positions, pressure, passing/carrying opportunity descriptors, quality flags).
8. `outcome` (episode/time horizon/terminal type, EPV metric provenance; no future data in decision features).

Key joins: match IDs are mandatory across every source; tracking to player metadata on (match_id,player_id), not player_id globally. Dynamic events ↔ tracking by **official documented frame/time alignment** plus (match_id, period); never raw x/y equality. Phases ↔ tracking by same match/period and inclusive interval after confirming boundary convention. Pose ↔ tracking by match/period/time: pose-frame ≈ 2.5× tracking-frame; use exact common timestamps first, then bounded interpolation only as documented. Do not join pose/tracking by identical integer frame. Event↔pose must pass through the time-aligned tracking context.

## D. Hypothesis-to-measure mapping and judgement
| Hypothesis | Native components | Must engineer | Primary foreseeable threat | Provisional feasibility |
|---|---|---|---|---|
| H1 coordination | 20-match tracking, player possession pressure, option-ease, phases, EPV | Pre-outcome onset, on-ball closing, coordinated off-ball closing, feasible outlets, settled/repress segmentation; terminal outcomes | Circularity if `passing_option_ease_end` defines both coordination and success; missing frame coverage and selection | Feasible as **associational/predictive** study pending event/phase semantics |
| H2 pose uplift | 2 full-match pose *if accessible*, joint confidence, tracking/event labels | Pose orientation and readiness features with matched-sample ablation | Only two matches; pose missing-not-at-random; degrees of freedom for testing | Exploratory; leave-one-match-out uplift, no sweeping significance |
| H3 carrying | carrier/player tracking, event action data, EPV | Carry detection if not coded, reachable endpoint and opponent intercept model, future player state with uncertainty; mutually exclusive pass/carry choices | Pass-only model has different choice space, fairness of comparison; vendor EPV may not be independent | Conditionally feasible; requires action category and candidate option verification |

## E. Three exact unresolved *gate* questions (no speculative audit expansion)
**Q1—Local integrity:** Does local `data/matches` have 20 complete, parseable groups of four files and can two full pose archives be read? Directory listings alone do not prove this. Use `p0_inventory.py` one time; record exceptions.
**Q2—Event and phase meanings:** Can action type, possession/onset frame, pressure/pass opportunity timing, turnover, 1v1 state, restart/outcome, and settled/repress phases be identified directly from documented columns? Get headers and a few representative rows, inspect the two official PDF specifications when accessible, and read the SkillCorner joining tutorial. If exact fields are absent, adjust operational definitions explicitly.
**Q3—Value provenance:** Does `possession_epv_*` depend on events after t, and are `passing_option_ease_start` / `overall_pressure_start` independently usable as features versus targets? Treat provenance as uncertain until documented; avoid using vendor metrics on both sides of a test where algebraic circularity arises.

## F. Stopping rule
P0 closes when: (1) exact file inventory and bounded parseability check is obtained; (2) required field headers, documented units, action/phase categories and join keys entered into this contract; (3) each hypothesis labelled feasible, conditional, or unsupported. If one field lacks vendor definition after targeted lookup, record an assumption and test it once with a tiny data-derived plot/sample in P1. No exhaustive scan or repeated audits. No modelling before temporal semantics are resolved. This gate currently remains OPEN for Q1–Q3.

## G. Important choices
- Do not treat a loss of actual-action EPV as equivalent to lost *available options*; distinguish them explicitly.
- Don't condition on post-onset defensive suppression when estimating any association of coordination with suppression; measure coordination using early/pre-outcome spatial behaviour and horizon-defined outcomes.
- A final score is not a minute-by-minute score.
- No precision or empirical success claims until observed experimental results.
