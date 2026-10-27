# PressLens Phase 0: data capability and eligibility audit

Reviewed 26 October 2026. Decision: **ADAPT**. Local replay inputs exist; the Phase 0 exit gate is **not fully passed** because source-release identity, redistribution rights, event semantics and some quality checks remain unresolved. This is a completed audit run with explicit unresolved findings, not validation of a detector.

**Carrier/context follow-up:** [Independent verification](carrier_context_verification/verification.md) reproduced the original 82.52%, 453 and 288 figures. It qualifies carrier nullness as 67.82% on provider-phase-covered frames, supplies the 8,093 known-carrier denominator, and establishes that all 288 phase disagreements are strictly inside phase intervals rather than at boundaries. Consult that follow-up before interpreting these as error rates.

## 1. Scope and reproducibility

The user requested the first framework step. The supplied v1.2 charter governs this audit; the v0.2 living framework still points to v1.1. Both source documents and all previous outputs were preserved. No match video, external observational dataset, trained football weights, tactical detector or viewer was introduced.

Run from the repository root with Python 3.11+ and Git:

```powershell
python scripts/audit_phase0.py
python scripts/audit_phase0_details.py
python scripts/audit_event_semantics.py
python scripts/report_phase0.py
python -m unittest discover -s tests -v
```

On this machine Python was not on PATH. The execution used `C:/Users/PC/.local/bin/python3.14.exe` (version 3.14.5). No package installation was needed. The audit scripts use only the standard library. Full application dependencies and a clean installation were not validated.

All 1,244,814 tracking JSONL lines were parsed, together with 94,517 event rows and 8,874 phase rows. Pose scope is explicitly bounded below. Per-file hashes are in `eligibility_manifest.json`; script hashes, Git revision, per-match counts, missingness and context breakdowns are in `data_audit.json`. Metadata/player detection is provider-derived evidence, not independently verified ground truth.

## 2. Actual local capabilities

There are 20 match IDs in the index and 20 complete four-file groups: tracking, metadata, Dynamic Events and Phases of Play. There are zero local tracking-only matches, three aggregate CSVs, two full pose archives and one compressed pose excerpt. The root README still describes 10 matches. The [current competition overview](https://pysport.org/analytics-cup/editions/analytics-cup2) advertises 20 tracking games, events for 10 games, and two pose games. Treat the broader local event coverage as a provenance discrepancy to reconcile, not proof of misconduct or automatic eligibility.

| Match | Period-labelled frames | Event rows | Phase rows | Event columns | Starts: carrier + ball detected |
|---|---:|---:|---:|---:|---:|
| 1874553 | 60,282 | 4,915 | 423 | 322 | 933/959 |
| 1886347 | 59,042 | 5,079 | 454 | 294 | 963/999 |
| 1899585 | 60,511 | 4,713 | 460 | 294 | 886/929 |
| 1925299 | 61,282 | 5,220 | 492 | 294 | 997/1,062 |
| 1927964 | 59,051 | 5,656 | 426 | 322 | 1,098/1,140 |
| 1953632 | 59,231 | 4,776 | 418 | 322 | 934/979 |
| 1959846 | 58,532 | 4,669 | 468 | 322 | 920/946 |
| 1986691 | 59,071 | 4,434 | 420 | 322 | 883/915 |
| 1996435 | 57,602 | 5,171 | 442 | 322 | 967/1,005 |
| 1996436 | 60,261 | 3,923 | 383 | 322 | 768/786 |
| 2006229 | 59,251 | 4,949 | 445 | 322 | 949/979 |
| 2006363 | 59,072 | 4,979 | 439 | 322 | 942/976 |
| 2007448 | 58,062 | 4,310 | 417 | 322 | 830/863 |
| 2007721 | 57,542 | 4,831 | 430 | 322 | 930/959 |
| 2010085 | 58,972 | 4,633 | 423 | 322 | 910/935 |
| 2011166 | 59,292 | 4,034 | 441 | 322 | 724/757 |
| 2013725 | 56,792 | 4,706 | 481 | 322 | 866/922 |
| 2015213 | 59,902 | 4,613 | 490 | 322 | 836/883 |
| 2016236 | 60,042 | 4,718 | 485 | 322 | 897/959 |
| 2017461 | 58,452 | 4,188 | 437 | 294 | 797/839 |

## 3. Coordinates, identities and time

All listed XY player IDs resolved against metadata `players[].id`; unresolved observations: 0. Do not substitute `team_player_id` or `trackable_object`. Pitch dimensions and actual coordinate ranges are retained per match. Positions outside the nominal rectangle occurred 139,500 times; this alone is not proof of bad data because players can leave the pitch.

There were 1,182,244 frames with period 1 or 2, and 62,570 other/null-period frames. Period-labelled is **not** synonymous with ball-in-play. There were 0 malformed JSONL lines, 0 frame discontinuities, 0 nonincreasing frame steps, and 0 duplicate IDs within XY frames. Within-period timestamp increments were 0.1 seconds for all 1,182,204 comparable pairs. Frame-clock offsets differ by period and match; never derive match time simply as frame/10.

All 189,034 event endpoints found their frame number, and none had a period mismatch. However 6,307 endpoint time strings disagreed with the tracking clock, with offsets from -4.0 to 0.0 seconds. All nonzero differences occur at `on_ball_engagement` starts; possession, passing-option and off-ball-run boundaries agree. A follow-up check explains the structural difference: `time_start` agrees with the clock at `frame_physical_start` for all 17,400 engagements. Do not pair this time field blindly with `frame_start` or apply a global clock shift. The provider's tactical meaning of these two starts still requires documentation review; this is not evidence of bad clock synchronization.

| Event type and boundary | Comparable endpoints | Nonzero clock differences |
|---|---:|---:|
| off_ball_run:end | 9,894 | 0 |
| off_ball_run:start | 9,894 | 0 |
| on_ball_engagement:end | 17,400 | 0 |
| on_ball_engagement:start | 17,400 | 6,307 |
| passing_option:end | 48,431 | 0 |
| passing_option:start | 48,431 | 0 |
| player_possession:end | 18,792 | 0 |
| player_possession:start | 18,792 | 0 |

Provider attacking direction agrees with metadata `home_team_side` and its away-team opposite in all 80/80 period/team groups; no goalkeeper-side guess is used. A canonical event/XY coordinate transformation was **not validated**. The root README warns that event coordinates require adjustment. Mixing them directly remains unsafe.

## 4. Visibility and the ball carrier

Across period-labelled frames, tracking carrier unknown: 975,572/1,182,244 (82.52%). Known-carrier coordinates were directly detected in 206,656 frames, extrapolated in 8, and absent/invalid in 8. Missing carrier does **not** mean no possession or no pressure.

Player coordinate entries were directly detected in 10,978,707/19,334,986 (56.78%); the rest were extrapolated. This denominator counts present player entries, not all expected active slots. Ball detected: 704,845/1,182,244 (59.62%); ball absent/invalid: 303,381/1,182,244 (25.66%).

At 18,792 provider possession starts, event carrier and ball were both detected in 18,030/18,792 (95.95%). Tracking carrier was unknown at 10,699 starts; known tracking carrier disagreed with the event player at 453. Matching frame numbers therefore does not establish matching possession identity.

Phase team disagreed with event team at 288/18,762 starts with half-open phase membership; 30 starts had no phase. These are diagnostic joins under `[start,end)`, not adjudicated provider errors. Audit inclusive endpoints and overlapping phase conventions before assigning tactical context.

Local opponents within 10m of a known tracking carrier were detected in 263,060/268,070 (98.13%). This is conditional on a known finite carrier and listed finite opponents; it cannot certify unseen defenders are absent.

At finite-carrier possession starts, 187,570 carrier-to-listed-teammate routes were inspected. Both endpoints detected: 117,394/187,570 (62.59%). Routes containing an extrapolated opponent in a 2m corridor: 11,895. Corridors exclude their endpoints and use a diagnostic width, not a fitted interception model. Empty known corridors are **not** certified open lanes. Expected active slots from half-open metadata intervals: 412,654; absent/invalid among those slots: 0. Substitution boundary semantics remain provisional.

## 5. Provider fields and potential receivers

Event schemas differ: four matches lack the newer context fields (1886347, 1899585, 1925299, 2017461); sixteen contain them. Do not turn absent columns into zero pressure. Per-field null counts and per-event-type nonnull counts are machine-readable in `data_audit.json`.

| Provider field and event type | Nonnull rows |
|---|---:|
| player_possession:overall_pressure_end | 13,298 |
| player_possession:overall_pressure_start | 13,251 |
| player_possession:passing_option_ease_end | 13,298 |
| player_possession:passing_option_ease_start | 13,251 |

`passing_option` includes player/linked-possession identifiers and interval/peak fields where populated; exact counts are recorded per match. Events describe supplied opportunities, not every frame's complete hypothetical option set. `targeted`, `received`, end scores, EPV deltas and later outcomes are retrospective/provider estimates; they must not silently enter onset predictors. Full provider PDF definitions could not be accessed through browsing and are listed as unresolved references.

## 6. Velocities and usable sequence counts

Raw finite-difference speeds were calculated only across consecutive 0.1s samples within the same period with the same directly detected player. 280 pairs exceeded the diagnostic 12m/s warning. That threshold flags review; it is not a validated exclusion rule. Per-match quantiles are recorded. Robust smoothing, substitutions/gap segmentation and kinematic validity still need testing before velocity-dependent detection.

There are 12,782 provider `pass_reception` starts; 12,537 have directly detected carrier and ball. These are **point observations**, not independent, quality-approved press/reception sequences. The number of complete press episodes surviving temporal, local-geometry and annotation filters is **undetermined**. No tactical positives, accuracy or effectiveness results are claimed.

## 7. Pose and aggregate resources

Both pose archive SHA256 values match the local provider manifest. For each, only the first 250 nonempty-player frames were inspected, with exact shared 25Hz/10Hz ticks used for identity/XY checks. Full ZIP CRC/JSON validity and full-match joint coverage were not tested. The manifest points to mutable `main`, so pin an immutable release before publication. The [provider pose dataset card](https://huggingface.co/datasets/SkillCorner/opendata-bodypose) labels its licence MIT; this does not by itself settle all Cup publication conditions.

| Archive | Hash matches | Sample entries with joints | Detection disagreements at shared ticks | Shared-tick XY delta quantiles (m) |
|---|---|---:|---:|---|
| pose_data/1925299.jsonl.zip | True | 4,234/8,000 | 48/1100 | {'0': 0.0, '0.5': 0.24166091947189128, '0.95': 1.0101980003939868, '0.99': 20.834586628968665, '1': 21.740009199630066} |
| pose_data/1996435.jsonl.zip | True | 2,000/7,500 | 1/1100 | {'0': 0.009999999999999787, '0.5': 0.17492855684535819, '0.95': 0.6989277502002589, '0.99': 5.5712924891805855, '1': 7.570951063109575} |

The local compressed excerpt was fully parsed: 309 frames and 143,637 joint observations. Joint coordinates include `xyz` and `p90_mae_cm` in the bounded archive samples; these do not validate body orientation. Pose files can contain XY entries with no joints; count joints separately from player entries and detections. Exact shared ticks avoid rounding half-frame matches. Pose remains optional.

**Pose quality flag:** the sampled shared-tick XY differences reach 21.74m and 7.57m respectively. These comparisons include extrapolated XY entries; they do not isolate detected-only joint accuracy. The bounded sample cannot establish full-match alignment or justify treating pose XY as interchangeable with the 10Hz stream.

Aggregate CSV schemas/missingness are inventoried. Player-season aggregates cannot supply frame-level press onset or local geometry. They are deferred as contextual resources, not forced into the detector. Tutorials, documentation, reusable loaders, pose/orientation helpers and visualization tools are enumerated in `data_audit.json`; enumeration is not code correctness or licence validation of every dependency.

## 8. Conflicts, legal checks and exit decision

See `feasibility_decisions.md`, `reference_register.md` and `decision_log.md`. The submission requirements exclude competition datasets from the public submission repository; existing raw files are already tracked here. This audit did not remove them or rewrite history, and nothing was committed, pushed or published. Existing P1/P2 outputs have inspected all 20 matches; absent a documented partition, their tactical examples must be treated as exploratory. Aggregate quality inspection alone does not consume a holdout, but previous tactical feature work may have done so.

Additional submission-readiness flags: the existing MIT file is named `LICENSE`, while the portal requests `LICENSE.md`; the upstream-style README contains approximately 1,662 whitespace-delimited words, exceeding the 1,000-word submission limit under that simple counting method; many application dependencies are unpinned. These require a submission-specific packaging pass, not changes to the football findings.

The next technical product is a replay/annotation viewer with unknown states and visible quality flags. Resolve source release/rights, event joins and an honest development/evaluation split before presenting it as a compliant validated product. Unresolved findings are part of this Phase 0 result.
