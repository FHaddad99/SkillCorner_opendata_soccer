"""Render the Phase 0 findings from audited counts, without rereading match data."""
import json
from collections import Counter

from audit_phase0 import ROOT, OUT


def main():
    d = json.loads((OUT / 'data_audit.json').read_text())
    t = d['totals']
    c, b, r = t['counts'], t['boundaries'], t['start_frame_route_visibility']
    def ratio(n, den):
        return f'{n:,}/{den:,} ({n / den:.2%})' if den else 'undefined (zero denominator)'
    def save(name, text):
        (OUT / name).write_text(text.strip() + '\n', encoding='utf-8')
    rows = []
    for m in d['matches']:
        bb = m['boundaries']
        rows.append(f"| {m['match_id']} | {m['counts']['active_period_frames']:,} | {m['events']['rows']:,} | {m['phases']['rows']:,} | {len(m['events']['fields'])} | {bb.get('carrier_and_ball_detected', 0):,}/{bb['possession_starts']:,} |")
    temporal = Counter()
    for m in d['matches']:
        for key, value in m['event_clock_offsets_by_type_and_edge_seconds'].items():
            temporal[key + ':total'] += sum(value.values())
            temporal[key + ':nonzero'] += sum(n for offset, n in value.items() if float(offset) != 0)
    time_table = '\n'.join(f"| {key.removesuffix(':total')} | {value:,} | {temporal.get(key.removesuffix(':total') + ':nonzero', 0):,} |" for key, value in sorted(temporal.items()) if key.endswith(':total'))
    missing_context = [m['match_id'] for m in d['matches'] if 'passing_option_ease_start' not in m['events']['fields']]
    context = Counter()
    for m in d['matches']:
        for kind, summary in m['events']['by_event_type'].items():
            for key, count in summary['nonnull'].items():
                if key in ('passing_option_ease_start', 'passing_option_ease_end', 'overall_pressure_start', 'overall_pressure_end'):
                    context[kind + ':' + key] += count
    provider_rows = '\n'.join(f'| {key} | {value:,} |' for key, value in sorted(context.items()))
    pose_rows = '\n'.join(f"| {p['path']} | {p['hash_matches_provider_manifest']} | {p['bounded_alignment']['counts'].get('entries_with_joints', 0):,}/{p['bounded_alignment']['counts']['player_entries']:,} | {p['bounded_alignment']['counts']['shared_tick_detection_disagreement']}/{p['bounded_alignment']['counts']['shared_tick_player_pairs']} | {p['bounded_alignment']['xy_delta_m_quantiles']} |" for p in d['poses'])
    event_rows = sum(m['events']['rows'] for m in d['matches'])
    phase_rows = sum(m['phases']['rows'] for m in d['matches'])
    save('data_audit.md', f'''# PressLens Phase 0: data capability and eligibility audit

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

On this machine Python was not on PATH. The execution used `C:/Users/PC/.local/bin/python3.14.exe` (version {d['python']}). No package installation was needed. The audit scripts use only the standard library. Full application dependencies and a clean installation were not validated.

All {c['lines']:,} tracking JSONL lines were parsed, together with {event_rows:,} event rows and {phase_rows:,} phase rows. Pose scope is explicitly bounded below. Per-file hashes are in `eligibility_manifest.json`; script hashes, Git revision, per-match counts, missingness and context breakdowns are in `data_audit.json`. Metadata/player detection is provider-derived evidence, not independently verified ground truth.

## 2. Actual local capabilities

There are 20 match IDs in the index and 20 complete four-file groups: tracking, metadata, Dynamic Events and Phases of Play. There are zero local tracking-only matches, three aggregate CSVs, two full pose archives and one compressed pose excerpt. The root README still describes 10 matches. The [current competition overview](https://pysport.org/analytics-cup/editions/analytics-cup2) advertises 20 tracking games, events for 10 games, and two pose games. Treat the broader local event coverage as a provenance discrepancy to reconcile, not proof of misconduct or automatic eligibility.

| Match | Period-labelled frames | Event rows | Phase rows | Event columns | Starts: carrier + ball detected |
|---|---:|---:|---:|---:|---:|
{chr(10).join(rows)}

## 3. Coordinates, identities and time

All listed XY player IDs resolved against metadata `players[].id`; unresolved observations: {c.get('unknown_player_ids', 0):,}. Do not substitute `team_player_id` or `trackable_object`. Pitch dimensions and actual coordinate ranges are retained per match. Positions outside the nominal rectangle occurred {c['player_positions_outside_pitch']:,} times; this alone is not proof of bad data because players can leave the pitch.

There were {c['active_period_frames']:,} frames with period 1 or 2, and {c['null_or_other_period']:,} other/null-period frames. Period-labelled is **not** synonymous with ball-in-play. There were {c.get('malformed_lines', 0)} malformed JSONL lines, {c.get('frame_gaps', 0)} frame discontinuities, {c.get('nonincreasing_frame', 0)} nonincreasing frame steps, and {c.get('duplicate_player_entries', 0)} duplicate IDs within XY frames. Within-period timestamp increments were 0.1 seconds for all {c['within_period_timestamp_pairs']:,} comparable pairs. Frame-clock offsets differ by period and match; never derive match time simply as frame/10.

All {b['event_endpoints_found']:,} event endpoints found their frame number, and none had a period mismatch. However {sum(v for k, v in t['event_tracking_time_offsets_seconds'].items() if float(k) != 0):,} endpoint time strings disagreed with the tracking clock, with offsets from {min(map(float, t['event_tracking_time_offsets_seconds']))} to {max(map(float, t['event_tracking_time_offsets_seconds']))} seconds. All nonzero differences occur at `on_ball_engagement` starts; possession, passing-option and off-ball-run boundaries agree. A follow-up check explains the structural difference: `time_start` agrees with the clock at `frame_physical_start` for all {d['totals']['event_semantics_diagnostics']['physical_start_time_agrees']:,} engagements. Do not pair this time field blindly with `frame_start` or apply a global clock shift. The provider's tactical meaning of these two starts still requires documentation review; this is not evidence of bad clock synchronization.

| Event type and boundary | Comparable endpoints | Nonzero clock differences |
|---|---:|---:|
{time_table}

Provider attacking direction agrees with metadata `home_team_side` and its away-team opposite in all {d['totals']['event_semantics_diagnostics']['direction_groups_agree_metadata']}/{d['totals']['event_semantics_diagnostics']['direction_period_team_groups']} period/team groups; no goalkeeper-side guess is used. A canonical event/XY coordinate transformation was **not validated**. The root README warns that event coordinates require adjustment. Mixing them directly remains unsafe.

## 4. Visibility and the ball carrier

Across period-labelled frames, tracking carrier unknown: {ratio(t['carrier_frames'].get('unknown_carrier', 0), c['active_period_frames'])}. Known-carrier coordinates were directly detected in {t['carrier_frames'].get('detected', 0):,} frames, extrapolated in {t['carrier_frames'].get('extrapolated', 0):,}, and absent/invalid in {t['carrier_frames'].get('absent_or_invalid', 0):,}. Missing carrier does **not** mean no possession or no pressure.

Player coordinate entries were directly detected in {ratio(t['player_observations']['detected'], sum(t['player_observations'].values()))}; the rest were extrapolated. This denominator counts present player entries, not all expected active slots. Ball detected: {ratio(t['ball_frames']['detected'], c['active_period_frames'])}; ball absent/invalid: {ratio(t['ball_frames']['absent_or_invalid'], c['active_period_frames'])}.

At {b['possession_starts']:,} provider possession starts, event carrier and ball were both detected in {ratio(b['carrier_and_ball_detected'], b['possession_starts'])}. Tracking carrier was unknown at {r['tracking_carrier_unknown_starts']:,} starts; known tracking carrier disagreed with the event player at {r['known_tracking_carrier_disagrees_starts']:,}. Matching frame numbers therefore does not establish matching possession identity.

Phase team disagreed with event team at {b['phase_team_disagree']:,}/{b['phase_present']:,} starts with half-open phase membership; {b['no_half_open_phase']:,} starts had no phase. These are diagnostic joins under `[start,end)`, not adjudicated provider errors. Audit inclusive endpoints and overlapping phase conventions before assigning tactical context.

Local opponents within 10m of a known tracking carrier were detected in {ratio(t['local_geometry']['opponents_within_10m_detected'], sum(t['local_geometry'].values()))}. This is conditional on a known finite carrier and listed finite opponents; it cannot certify unseen defenders are absent.

At finite-carrier possession starts, {r['teammate_routes']:,} carrier-to-listed-teammate routes were inspected. Both endpoints detected: {ratio(r['carrier_receiver_both_detected_routes'], r['teammate_routes'])}. Routes containing an extrapolated opponent in a 2m corridor: {r['routes_with_extrapolated_corridor_opponent']:,}. Corridors exclude their endpoints and use a diagnostic width, not a fitted interception model. Empty known corridors are **not** certified open lanes. Expected active slots from half-open metadata intervals: {r['expected_active_player_slots']:,}; absent/invalid among those slots: {r['expected_active_slots_absent_or_invalid']:,}. Substitution boundary semantics remain provisional.

## 5. Provider fields and potential receivers

Event schemas differ: four matches lack the newer context fields ({', '.join(missing_context)}); sixteen contain them. Do not turn absent columns into zero pressure. Per-field null counts and per-event-type nonnull counts are machine-readable in `data_audit.json`.

| Provider field and event type | Nonnull rows |
|---|---:|
{provider_rows}

`passing_option` includes player/linked-possession identifiers and interval/peak fields where populated; exact counts are recorded per match. Events describe supplied opportunities, not every frame's complete hypothetical option set. `targeted`, `received`, end scores, EPV deltas and later outcomes are retrospective/provider estimates; they must not silently enter onset predictors. Full provider PDF definitions could not be accessed through browsing and are listed as unresolved references.

## 6. Velocities and usable sequence counts

Raw finite-difference speeds were calculated only across consecutive 0.1s samples within the same period with the same directly detected player. {c['raw_speed_above_12_mps']:,} pairs exceeded the diagnostic 12m/s warning. That threshold flags review; it is not a validated exclusion rule. Per-match quantiles are recorded. Robust smoothing, substitutions/gap segmentation and kinematic validity still need testing before velocity-dependent detection.

There are {r['pass_reception_starts']:,} provider `pass_reception` starts; {r['pass_reception_carrier_ball_detected']:,} have directly detected carrier and ball. These are **point observations**, not independent, quality-approved press/reception sequences. The number of complete press episodes surviving temporal, local-geometry and annotation filters is **undetermined**. No tactical positives, accuracy or effectiveness results are claimed.

## 7. Pose and aggregate resources

Both pose archive SHA256 values match the local provider manifest. For each, only the first 250 nonempty-player frames were inspected, with exact shared 25Hz/10Hz ticks used for identity/XY checks. Full ZIP CRC/JSON validity and full-match joint coverage were not tested. The manifest points to mutable `main`, so pin an immutable release before publication. The [provider pose dataset card](https://huggingface.co/datasets/SkillCorner/opendata-bodypose) labels its licence MIT; this does not by itself settle all Cup publication conditions.

| Archive | Hash matches | Sample entries with joints | Detection disagreements at shared ticks | Shared-tick XY delta quantiles (m) |
|---|---|---:|---:|---|
{pose_rows}

The local compressed excerpt was fully parsed: {d['pose_sample_counts']['frames']:,} frames and {d['pose_sample_counts']['joint_observations']:,} joint observations. Joint coordinates include `xyz` and `p90_mae_cm` in the bounded archive samples; these do not validate body orientation. Pose files can contain XY entries with no joints; count joints separately from player entries and detections. Exact shared ticks avoid rounding half-frame matches. Pose remains optional.

**Pose quality flag:** the sampled shared-tick XY differences reach 21.74m and 7.57m respectively. These comparisons include extrapolated XY entries; they do not isolate detected-only joint accuracy. The bounded sample cannot establish full-match alignment or justify treating pose XY as interchangeable with the 10Hz stream.

Aggregate CSV schemas/missingness are inventoried. Player-season aggregates cannot supply frame-level press onset or local geometry. They are deferred as contextual resources, not forced into the detector. Tutorials, documentation, reusable loaders, pose/orientation helpers and visualization tools are enumerated in `data_audit.json`; enumeration is not code correctness or licence validation of every dependency.

## 8. Conflicts, legal checks and exit decision

See `feasibility_decisions.md`, `reference_register.md` and `decision_log.md`. The submission requirements exclude competition datasets from the public submission repository; existing raw files are already tracked here. This audit did not remove them or rewrite history, and nothing was committed, pushed or published. Existing P1/P2 outputs have inspected all 20 matches; absent a documented partition, their tactical examples must be treated as exploratory. Aggregate quality inspection alone does not consume a holdout, but previous tactical feature work may have done so.

Additional submission-readiness flags: the existing MIT file is named `LICENSE`, while the portal requests `LICENSE.md`; the upstream-style README contains approximately 1,662 whitespace-delimited words, exceeding the 1,000-word submission limit under that simple counting method; many application dependencies are unpinned. These require a submission-specific packaging pass, not changes to the football findings.

The next technical product is a replay/annotation viewer with unknown states and visible quality flags. Resolve source release/rights, event joins and an honest development/evaluation split before presenting it as a compliant validated product. Unresolved findings are part of this Phase 0 result.
''')
    save('feasibility_decisions.md', '''# Phase 0 feasibility decisions

Date: 26 October 2026. Scope: first framework step only. These are provisional engineering decisions; no frozen charter changes.

| Component | Decision | Evidence and condition |
|---|---|---|
| Local tracking replay and annotation | ADAPT | All 20 local match groups parsed. Distinguish null periods, missing ball/carrier and extrapolated players. Source-release identity is pending before analytical release. |
| Carrier assignment | ADAPT | Sparse tracking carrier plus boundary disagreement prevents simple forward filling. Preserve event and tracking identities separately and abstain on unresolved conflicts. |
| Events and phases | ADAPT | Frames resolve; engagement time_start maps to frame_physical_start, explaining apparent offsets. Phase-team disagreements and tactical onset semantics need review. |
| Attacking direction | SUPPORTED AS PROVIDER CONTEXT | All 80 period/team groups agree with metadata. Event/XY coordinate transformation remains unvalidated. |
| Pass/carry accessibility | DEFER | Start-frame corridor visibility measured; continuous route quality, event-to-XY transforms and models remain unvalidated. No pass-probability claim. |
| Pressure context comparisons | ADAPT | Newer context fields exist only in 16 matches. Preserve separate denominators and boundary timing; they are vendor outputs. |
| Cue/press/funnel classifiers | DEFER | No independently reviewed labels or complete sequence-quality policy. Point-quality counts cannot prove sufficient training/evaluation sample. |
| Velocities/closing speed | DEFER | Regular 10Hz timestamps; raw speed warnings require robust smoothing and segmentation review. |
| Pose orientation | DEFER, optional | Two archive hashes match; bounded identity/XY/joint inspection only. Whole-match alignment and orientation uncertainty remain open. |
| Season physical/OBR/passing aggregates | CONTEXT ONLY | Inventoried; player-season summaries cannot resolve individual frame geometry or onset. |
| External model weights/data/video | EXCLUDE | No new observational sources were ingested. Literature/software review does not grant data permission. |
| Public raw-data release | STOP | Existing tracked datasets conflict with submission exclusion; prepare a separate code-only submission repository. Do not erase this working repository automatically. |
| Derived replay/video publication | UNRESOLVED | Verify licence/EULA for specific assets and release. No public sequence exported. |
| Held-out tactical validation | UNRESOLVED | Legacy P1/P2 outputs cover all matches. Reconstruct prior exposure before declaring any untouched test set. |

The Phase 0 audit execution is complete; its full exit gate remains open. A pending legal/quality check is not a negative finding about the football or an authorization to invent missing labels.

Suggested living-framework v0.3 edits: correct charter link to v1.2; record 20 local event-rich matches and the four older schemas; require event-specific time semantics, sparse-carrier handling and phase-team conflict flags; describe bounded pose verification; record legacy all-match exploratory exposure. Keep proposed detector thresholds provisional. The supplied protocols were preserved for owner review.
''')
    save('reference_register.md', '''# Phase 0 reference and resource register

Review date: 26 October 2026. References informed documentation and eligibility review only; no external empirical football data or fitted models were imported.

| Provider / exact resource | Source and verification | Use / limitation / licence |
|---|---|---|
| PySport / Overview — Analytics Cup 2.0 | https://pysport.org/analytics-cup/editions/analytics-cup2 ; indexed page content inspected; direct open returned a JavaScript shell | Current edition, eligible event/prior-Cup sources, advertised resource counts. Website terms; no content redistributed verbatim. An indexed view is not a pinned rules release. |
| PySport / Analytics Cup 2.0 call for proposals | https://pretalx.pysport.org/analytics-cup-2/cfp ; indexed submission text inspected | Public code repository excluding datasets, LICENSE.md, README and video requirements. Website publication terms. |
| SkillCorner / Analytics Cup 2027 | https://skillcorner.com/analytics-cup-2027 ; live page read | Distinguishes first edition from current second edition. Marketing/organizer page, not detailed EULA. |
| SkillCorner / opendata | https://github.com/SkillCorner/opendata ; repository description and local README inspected | Origin/resource discovery; README match-count statement is stale relative to local inventory. MIT software licence; exact local release identity remains unverified. |
| SkillCorner / opendata LICENSE | https://github.com/SkillCorner/opendata/blob/master/LICENSE ; source inspected | MIT software attribution retained. Do not silently equate software permission with all competition-data redistribution rights. |
| SkillCorner / opendata-bodypose | https://huggingface.co/datasets/SkillCorner/opendata-bodypose ; dataset card inspected | Provider-hosted two-match pose resource, labelled MIT. Local archive hashes matched local MANIFEST; upstream immutable revision not pinned. |
| SkillCorner / Dynamic Events CSV Specifications, URL dated 20250216 | https://26560301.fs1.hubspotusercontent-eu1.net/hubfs/26560301/Guides/Dynamic%20Events/20250216%20-%20Dynamic%20Events%20CSV%20Specifications.pdf ; UNRESOLVED: browser could not access | No equation, event-latency explanation or completeness claim attributed to this unread PDF. Obtain current accessible provider definition. |
| SkillCorner / Phases of Play CSV Specifications, URL dated 20250216 | https://26560301.fs1.hubspotusercontent-eu1.net/hubfs/26560301/Guides/Phases%20of%20Play/20250216%20-%20Phases%20of%20Play%20CSV%20Specifications.pdf ; UNRESOLVED: browser could not access | Inclusive/exclusive interval convention not established from this source. Half-open membership is explicitly our diagnostic convention. |
| PySport / Competition Rules — Analytics Cup (first edition) | https://pysport.org/analytics-cup/rules ; inspected then excluded as current governing source | Its 2025/2026 schedule belongs to the previous edition; do not apply it to this project. |

The source index advertises 18 December 2026 as the submission date; the submission portal displays 19 December 2026 00:01 UTC (18 December 19:01 Toronto). This is consistent with an evening local cutoff, but exact deadline/timezone should be reconfirmed before submission. No deadline is encoded in analytics.

The current overview's permission to use event/prior-Cup data is not an exact-file manifest. XY/event/aggregate release identity and derived-asset redistribution remain unresolved. No papers, borrowed spatial model or fitted artifact were adopted in this increment; literature appraisal remains a requirement when selecting those methods.

Local resource discovery: `data_audit.json.resource_inventory` enumerates notebooks, tutorials, loaders, visualization code and docs; match CSV fields and null counts are under each match. Files are classified as provider knowledge/software resources, not independently validated tools. Examples may require unpinned packages or private API credentials; those are not requirements of this audit. Historical P1/P2 outputs were inspected only to assess prior exposure and conflicting claims, not accepted as validated evidence.
''')
    save('decision_log.md', '''# Phase 0 decision log

- 2026-10-26: Executed only Phase 0 at the user's request. Used supplied charter v1.2 despite stale v1.1 reference. Preserved protocols and historical outputs; proposed edits are documented rather than silently applied.
- Built an exact local path/hash inventory. Unknown paths are quarantined; audit inspection does not enable analytical ingestion or public redistribution. Release evidence remains pending.
- Parsed all XY tracking and event/phase rows. Measured quality with separate frame, observation, event-boundary and route denominators. No thresholds were selected against tactical outcomes.
- Added route checks at possession starts (2m corridor half-width), local opponent counts (10m) and a raw-speed warning (12m/s). These are diagnostic parameters, not validated detector parameters. Pose inspection is bounded to the first 250 nonempty frames of each archive plus the complete small excerpt.
- Recorded timing/carrier/phase conflicts, mixed event schemas, previous all-match exploratory outputs, tracked raw datasets and unpinned dependencies. No claims of independent validation, calibrated probabilities, causal effects or tactical intention.
- Exit: ADAPT, with unresolved provenance/publication and methodological gates. No viewer, detector, release, raw-data deletion, Git commit or push was performed.
''')
    dictionary = {
        'version': 'phase0-1.0',
        'evidence_type': 'provider tracking/event records; independently observed ground truth not available',
        'tracking': {'frame': 'integer release-specific tick, nominal 10 Hz', 'timestamp': 'nullable HH:MM:SS.f tracking match clock',
                     'period': 'nullable integer; audit separates 1/2 from other/null', 'possession.player_id': 'nullable metadata players[].id; sparse and not forward filled',
                     'possession.group': 'nullable team group string; not an observed change-of-possession guarantee',
                     'player_data[].x/y': 'nullable pitch-centred metres per provider README; finite checked',
                     'player_data[].is_detected': 'provider detection/extrapolation flag, not independent identity accuracy',
                     'ball_data': 'nullable XYZ and detection state; XY finite checked',
                     'image_corners_projection': 'provider camera-footprint estimate; no visibility guarantee inferred'},
        'events': {'semantics': 'provider-generated estimates/labels; event-specific timing unresolved',
                   'schemas_by_match': {m['match_id']: m['events']['fields'] for m in d['matches']},
                   'missingness': 'data_audit.json matches[].events.null_or_empty and by_event_type',
                   'frame_start/end': 'integer tracking references; every endpoint matched; time strings can differ',
                   'start_type': 'categorical; pass_reception is the measured reception category',
                   'attacking_side': 'provider direction by period/team; canonical geometry not validated',
                   'x/y': 'event scale/convention requires verified transformation before combining with tracking'},
        'pose': {'frame': '25 Hz; only integer shared ticks joined, no rounding', 'joints': 'nullable joint dictionary',
                 'xyz': 'joint XYZ values; pitch-centred per provider; global Z accuracy limited',
                 'p90_mae_cm': 'provider predicted joint error in centimetres, not independently calibrated here'},
        'audit_metrics': {'frame_quality': 'counts of period-labelled frames, includes ball-out-of-play',
                          'entry_quality': 'detected/extrapolated among present player entries; absent players excluded from denominator',
                          'route_quality': 'possession-start listed-teammate endpoints and finite opponent corridor positions only',
                          'raw_velocity': 'consecutive detected same-player 0.1s finite difference, m/s; unsmoothed',
                          'eligible_episode_count': 'undetermined; point-quality counts are not complete sequences'}
    }
    save('variable_dictionary.json', json.dumps(dictionary, indent=2))
    print('Rendered data_audit.md, feasibility_decisions.md, reference_register.md, decision_log.md and variable_dictionary.json')


if __name__ == '__main__':
    main()
