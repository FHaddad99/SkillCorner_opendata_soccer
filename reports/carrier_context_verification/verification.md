# Follow-up verification: carrier and phase context

## Result

All three original numerical counts were independently reproduced from the raw source files for all 20 matches. Their interpretation needs qualification: **82.52% is nullness of a field across period-labelled frames, not an error rate or the percentage of live football with an unknowable ball carrier.** The 453 and 288 values are cross-source disagreements, not adjudicated provider mistakes.

The 80 metadata/tracking/event/phase file hashes still match the original eligibility manifest. The new verifier does not import the old audit's counting or joining functions. It normalizes IDs to integers, enumerates every phase containing each possession start, and separately reproduces the original latest-start join. All matching tracking records had the expected period.

## 1. Raw tracking carrier nullness: confirmed, denominator qualified

`possession.player_id` is null on **975,572 / 1,182,244 = 82.5187%** of frames with period 1 or 2. There are another 62,570 rows outside those periods, excluded from that denominator.

The original period denominator includes 303,381 frames with no finite ball XY and no player entries. Every one of those frames has a null carrier. Excluding those frames gives 76.48%; restricting to provider phase coverage gives 67.82%. A frame without a named carrier does not by itself establish a tracking failure: the ball may be between players or control may be uncertain. This audit does not identify which explanation applies at each null frame.

Each subset below is a separate denominator, not a cumulative filter:

| Selection | Null raw carrier IDs | Selected frames | Null rate |
|---|---:|---:|---:|
| period_1_2 | 975,572 | 1,182,244 | 82.52% |
| ball_xy_finite | 672,199 | 878,863 | 76.49% |
| players_present | 672,199 | 878,863 | 76.49% |
| ball_detected_and_xy_finite | 498,395 | 704,845 | 70.71% |
| phase_covered_half_open | 427,089 | 629,755 | 67.82% |
| tracking_team_group_nonnull | 432,376 | 639,048 | 67.66% |
| possession_event_covered_half_open | 139,885 | 292,512 | 47.82% |

Phase-covered and event-covered masks are unions of same-period `[frame_start, frame_end)` intervals. Phase coverage is a provider-labelled proxy for in-play, not independently verified video truth. Zero-duration event rows do not add frames to the half-open event mask. Therefore the 47.82% event-covered value is not directly interchangeable with the all-period 82.52% value.

**Correct wording:** “The raw tracking carrier-ID field is sparse: 82.52% null over period-labelled frames, and 67.82% null over frames covered by provider phases.” We have not shown that 82.52% of the match is analytically unusable.

## 2. Known tracking carrier versus possession-event player: confirmed

At **18,792** provider `player_possession` starts:

| Tracking carrier state | Count | Share of all starts |
|---|---:|---:|
| Null | 10,699 | 56.93% |
| Known and agrees with event player | 7,640 | 40.66% |
| Known and disagrees with event player | 453 | 2.41% |

The known-carrier denominator is **8,093**: 453/8,093 = **5.60%** disagree. Relative to all possession starts, disagreements are **2.41%**. Of the 453, **367** name a tracking player on the opposite team and **86** name another player on the same team. Both players have directly detected XY coordinates in **416** cases. Coordinates being detected does not validate the possession label.

Adjacent-frame sensitivity: none of the 453 event players agrees with the tracking ID exactly one tick before or after the start. Agreement at +2 frames occurs once, at +5 twice, and at +10 twenty times. These are separate checks of the original mismatches, not a complete shifted-data performance comparison and not evidence to apply a global time shift. In **60** mismatches the event player appears as the tracking carrier later within the inclusive event interval; that does not retroactively resolve the start. **173** mismatches are zero-duration possession events, making ordinary duration-based filling especially unsafe.

### Concrete source example

Match **1874553**, period **1**, frame **8958**, tracking timestamp **00:14:54.80**, event **8_153**:

- Event player: **50966, B. Halloran**, team **1802**; event `start_type=pass_reception`, `end_type=shot`.
- Raw tracking carrier: **26766, B. Vriends**, team **866**.
- Both players are marked detected. Event-player distance to the ball is **0.941m**; tracking-player distance is **3.900m**.

This is a real identity disagreement in the files, not a string/integer join artifact. Being closer to the ball is insufficient to adjudicate possession. The source record is in `carrier_disagreements.csv`, along with every other mismatch and nearby tracking IDs.

## 3. Event team versus containing phase team: confirmed, not a boundary artifact

There are **18,762** starts with a half-open phase match and **30** without one. In **288/18,762 = 1.54%**, the event team differs from `team_in_possession_id` of the containing phase. Exhaustive membership finds no overlapping half-open phases at these starts and reproduces the original count.

Crucially, **all 288 starts lie strictly inside their containing phase**: none is at any same-period phase boundary. All remain disagreements under inclusive membership. Inclusive membership introduces three additional unmatched-team cases at previously uncovered starts, giving **291** cases in that separate population; it does not fix the original 288. Across all starts it also creates **2,719** multiple-phase matches, so it is not an unambiguous replacement join.

### Concrete source example

Match **1874553**, period **1**, frame **6732**, event **8_123**:

- Event team **866**, `start_type=pass_interception`, `end_type=pass`.
- Containing phase index **67**, interval **[6682, 6882)**, team in possession **1802**.
- Frame 6732 is **50 frames after the phase start** and **150 before its end**. The event's own `phase_index` is also **67**.

This confirms a difference between individual event attribution and the team-level phase label. It does not establish which field is wrong, or whether the provider intentionally permits brief opposition actions inside a broader phase. Provider semantic confirmation is still needed.

The 288 event starts are distributed as follows:

| Event start type | Count |
|---|---:|
| pass_interception | 103 |
| recovery | 72 |
| pass_reception | 42 |
| corner_interception | 23 |
| free_kick_interception | 21 |
| unknown | 13 |
| keep_possession | 7 |
| throw_in_interception | 7 |

Only **7** of these 288 cases also belong to the 453 raw-carrier disagreement cases. They are largely different issues. The raw `player_possession_phase_index` is recorded in the CSV for inspection only; its name is not treated as evidence that it is a foreign key into phase rows.

## 4. Per-match reproduction

| Match | Null carrier / period frames | Known-carrier disagreements | Half-open phase-team disagreements |
|---|---:|---:|---:|
| 1874553 | 48,691/60,282 | 29 | 9 |
| 1886347 | 48,555/59,042 | 22 | 18 |
| 1899585 | 51,553/60,511 | 21 | 20 |
| 1925299 | 49,179/61,282 | 26 | 10 |
| 1927964 | 44,353/59,051 | 15 | 9 |
| 1953632 | 47,726/59,231 | 19 | 9 |
| 1959846 | 48,553/58,532 | 20 | 6 |
| 1986691 | 48,920/59,071 | 16 | 21 |
| 1996435 | 46,787/57,602 | 28 | 23 |
| 1996436 | 51,718/60,261 | 21 | 20 |
| 2006229 | 48,482/59,251 | 18 | 10 |
| 2006363 | 48,113/59,072 | 25 | 14 |
| 2007448 | 48,507/58,062 | 21 | 10 |
| 2007721 | 45,493/57,542 | 28 | 11 |
| 2010085 | 47,613/58,972 | 27 | 8 |
| 2011166 | 51,517/59,292 | 26 | 10 |
| 2013725 | 47,303/56,792 | 23 | 13 |
| 2015213 | 51,080/59,902 | 22 | 9 |
| 2016236 | 50,533/60,042 | 19 | 25 |
| 2017461 | 50,896/58,452 | 27 | 33 |

## 5. Implications and limits

Preserve separate `tracking_carrier_id`, `event_player_id`, `event_team_id` and `phase_team_id` fields. Do not silently forward-fill the sparse field, choose the nearest player as truth, or overwrite a conflicting event team with the phase team. A conflicting phase label should remain a context-quality flag until its definition is established; it is not automatically grounds to discard the entire sequence.

An additional, distinct source issue was found: match **1953632**, event **8_948**, frame **56766**, names event player **973077**, absent from that match's metadata roster. The original zero-unresolved-ID result concerned XY tracking entries and does not establish that every event player resolves. This needs a separate event-roster check before canonical joins.

### Provider reference check

SkillCorner's [official phase/tracking tutorial](https://skillcorner.github.io/opendata/notebooks/tutorials/02_Working_with_Game_Intelligence_and_Dynamic_Events/Part7_Pitch_Maps_Tracking_by_Phase_Tutorial/) was inspected on 26 October 2026. Its Step 3 uses a left-closed interval index and filters nonnull `possession.group`. That supports the half-open join as a provider-example convention; it does not validate all possession labels or explain the 288 cases. The linked detailed phase specification PDF remained inaccessible through the browser tool. No unread definition is used to explain away a conflict.

### Reproduce and validate

```powershell
python scripts/verify_carrier_context.py
python scripts/report_carrier_context_verification.py
python -m unittest discover -s tests -v
```

Executed using `C:/Users/PC/.local/bin/python3.14.exe`. Four software tests passed, including new tests for ambiguous inclusive team-change boundaries and same-period coverage unions. Source-hash checks, original-count comparisons and denominator-balance assertions passed. These are source consistency and software checks, not independent football ground truth. The original Phase 0 JSON and all source data were preserved.
