"""Reproduce the PressLens Phase 0 audit with Python 3.11+ standard library.

Run from the repository root: python scripts/audit_phase0.py
Reads local inputs only; never downloads, changes, or exports raw records.
Eligibility for inspection is distinct from approval for analysis/publication.
"""
import bisect
import csv
import gzip
import hashlib
import json
import math
import platform
import subprocess
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports'
RULES = 'https://pysport.org/analytics-cup/editions/analytics-cup2'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def clock(value):
    if not value:
        return None
    parts = list(map(float, value.split(':')))
    return sum(v * 60 ** i for i, v in enumerate(reversed(parts)))


def finite_xy(obj):
    return all(isinstance(obj.get(k), (int, float)) and math.isfinite(obj[k]) for k in ('x', 'y'))


def state(obj):
    if not obj or not finite_xy(obj):
        return 'absent_or_invalid'
    return {True: 'detected', False: 'extrapolated'}.get(obj.get('is_detected'), 'unknown_detection')


def quantiles(values):
    if not values:
        return None
    values = sorted(values)
    return {str(p): values[round((len(values) - 1) * p)] for p in (0, .5, .95, .99, 1)}


def csv_audit(path):
    if not path.exists():
        return {'present': False}, []
    with path.open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        rows = list(reader)
    filled = Counter(k for row in rows for k in fields if row[k] not in ('', None))
    types = Counter(row.get('event_type', '<not_event>') for row in rows)
    by_type = {}
    for kind in types:
        subset = [r for r in rows if r.get('event_type', '<not_event>') == kind]
        by_type[kind] = {'rows': len(subset), 'nonnull': dict(Counter(k for r in subset for k in fields if r[k] not in ('', None)))}
    return {'present': True, 'rows': len(rows), 'fields': fields,
            'null_or_empty': {k: len(rows) - filled[k] for k in fields},
            'event_types': dict(types), 'by_event_type': by_type}, rows


def audit_match(directory):
    ident = directory.name
    meta = json.loads((directory / f'{ident}_match.json').read_text(encoding='utf-8'))
    teams = {str(p['id']): str(p['team_id']) for p in meta['players']}
    ev, events = csv_audit(directory / f'{ident}_dynamic_events.csv')
    ph, phases = csv_audit(directory / f'{ident}_phases_of_play.csv')
    starts = defaultdict(list)
    endpoints = defaultdict(list)
    for row in events:
        for edge in ('start', 'end'):
            try:
                endpoints[int(row[f'frame_{edge}'])].append((row, edge))
            except (ValueError, TypeError):
                pass
        if row.get('event_type') == 'player_possession':
            starts[int(row['frame_start'])].append(row)
    phase_index = defaultdict(list)
    for row in phases:
        phase_index[int(row['period'])].append(row)
    for period in phase_index:
        phase_index[period].sort(key=lambda r: int(r['frame_start']))
    phase_starts = {p: [int(r['frame_start']) for r in rows] for p, rows in phase_index.items()}
    counts = Counter()
    carrier = Counter()
    players = Counter()
    ball = Counter()
    local = Counter()
    boundaries = Counter()
    by_context = defaultdict(Counter)
    offsets = Counter()
    timestamp_offsets = Counter()
    speeds = []
    previous = None
    prev_players = {}
    prev_possession = None
    ranges = {'x': [math.inf, -math.inf], 'y': [math.inf, -math.inf]}
    seen_endpoints = set()
    keys = Counter()
    tracking_path = directory / f'{ident}_tracking_extrapolated.jsonl'
    if not tracking_path.exists():
        return {'match_id': ident, 'error': 'missing tracking', 'events': ev, 'phases': ph}
    with tracking_path.open(encoding='utf-8') as handle:
        for line in handle:
            counts['lines'] += 1
            try:
                record = json.loads(line)
            except (ValueError, TypeError):
                counts['malformed_lines'] += 1
                previous, prev_players, prev_possession = None, {}, None
                continue
            keys.update(record.keys())
            frame, period = record.get('frame'), record.get('period')
            t = clock(record.get('timestamp'))
            if previous is not None:
                pf, pp, pt = previous
                if frame <= pf:
                    counts['nonincreasing_frame'] += 1
                elif frame != pf + 1:
                    counts['frame_gaps'] += 1
                if period == pp and t is not None and pt is not None:
                    counts['within_period_timestamp_pairs'] += 1
                    counts['timestamp_not_0.1s'] += abs(t - pt - .1) > 1e-5
            if period not in (1, 2):
                counts['null_or_other_period'] += 1
                previous, prev_players, prev_possession = (frame, period, t), {}, None
                continue
            counts['active_period_frames'] += 1
            counts[f'period_{period}_frames'] += 1
            if t is None:
                counts['active_timestamp_missing'] += 1
            else:
                timestamp_offsets[f'{period}:{round(frame - t * 10, 3)}'] += 1
            ps = record.get('player_data') or []
            lookup = {str(p['player_id']): p for p in ps}
            counts['duplicate_player_entries'] += len(ps) - len(lookup)
            counts['frames_fewer_than_22_entries'] += len(ps) < 22
            pos = record.get('possession') or {}
            cid = str(pos.get('player_id'))
            cp = lookup.get(cid)
            cs = state(cp)
            carrier[cs if pos.get('player_id') is not None else 'unknown_carrier'] += 1
            bs = state(record.get('ball_data'))
            ball[bs] += 1
            if prev_possession is not None and pos.get('group') is not None:
                counts['possession_group_changes'] += prev_possession != pos['group']
            prev_possession = pos.get('group')
            idx = bisect.bisect_right(phase_starts.get(period, []), frame) - 1
            phase = phase_index[period][idx] if idx >= 0 else None
            # Explicit diagnostic convention: half-open phase membership.
            if phase and not int(phase['frame_start']) <= frame < int(phase['frame_end']):
                phase = None
            context = f"{period}:{pos.get('group')}:{phase.get('team_out_of_possession_phase_type') if phase else 'no_phase'}"
            by_context[context]['frames'] += 1
            by_context[context]['carrier_' + (cs if pos.get('player_id') is not None else 'unknown')] += 1
            by_context[context]['ball_' + bs] += 1
            current = {}
            for p in ps:
                pid = str(p['player_id'])
                s = state(p)
                players[s] += 1
                by_context[context]['players_' + s] += 1
                counts['unknown_player_ids'] += pid not in teams
                if not finite_xy(p):
                    continue
                for k in ('x', 'y'):
                    ranges[k][0] = min(ranges[k][0], p[k])
                    ranges[k][1] = max(ranges[k][1], p[k])
                counts['player_positions_outside_pitch'] += abs(p['x']) > meta['pitch_length'] / 2 or abs(p['y']) > meta['pitch_width'] / 2
                if previous and previous[1] == period and frame == previous[0] + 1 and t is not None and previous[2] is not None and abs(t - previous[2] - .1) < 1e-5 and s == 'detected' and pid in prev_players:
                    old = prev_players[pid]
                    if state(old) == 'detected':
                        v = math.hypot(p['x'] - old['x'], p['y'] - old['y']) * 10
                        speeds.append(v)
                        counts['raw_speed_above_12_mps'] += v > 12
                current[pid] = p
                if cp and finite_xy(cp) and teams.get(cid) and teams.get(pid) and teams[pid] != teams[cid] and math.hypot(cp['x'] - p['x'], cp['y'] - p['y']) <= 10:
                    local['opponents_within_10m_' + s] += 1
            if frame in starts:
                for row in starts[frame]:
                    boundaries['possession_starts'] += 1
                    if str(period) != row['period']:
                        boundaries['period_mismatch'] += 1
                        continue
                    ec = lookup.get(row['player_id'])
                    boundaries['event_carrier_' + state(ec)] += 1
                    boundaries['ball_' + bs] += 1
                    boundaries['tracking_event_carrier_agree'] += cid == row['player_id']
                    boundaries['event_carrier_team_agree'] += teams.get(row['player_id']) == row['team_id']
                    if phase:
                        boundaries['phase_present'] += 1
                        boundaries['phase_team_disagree'] += row['team_id'] != phase['team_in_possession_id']
                    else:
                        boundaries['no_half_open_phase'] += 1
                    if state(ec) == 'detected' and bs == 'detected':
                        boundaries['carrier_and_ball_detected'] += 1
                    if row.get('start_type') == 'reception':
                        boundaries['reception_starts'] += 1
                        boundaries['reception_carrier_and_ball_detected'] += state(ec) == 'detected' and bs == 'detected'
            for row, edge in endpoints.get(frame, []):
                seen_endpoints.add(frame)
                boundaries['event_endpoints_found'] += 1
                if str(period) != row['period']:
                    boundaries['endpoint_period_mismatch'] += 1
                et = clock(row.get('time_' + edge))
                if et is not None and t is not None:
                    offsets[str(round(et - t, 3))] += 1
            previous, prev_players = (frame, period, t), current
    option_rows = [r for r in events if r['event_type'] == 'passing_option']
    option_timing = Counter()
    for row in option_rows:
        for col in ('player_id', 'player_in_possession_id', 'associated_player_possession_event_id', 'peak_passing_option_frame', 'passing_option_score'):
            option_timing[col + '_nonnull'] += bool(row.get(col))
        if row.get('peak_passing_option_frame'):
            option_timing['peak_inside_interval_inclusive'] += int(row['frame_start']) <= int(row['peak_passing_option_frame']) <= int(row['frame_end'])
    direction = defaultdict(set)
    for row in events:
        direction[f"{row['period']}:{row['team_id']}"].add(row['attacking_side'])
    missing_frames = set(endpoints) - seen_endpoints
    return {'match_id': ident, 'pitch_m': [meta['pitch_length'], meta['pitch_width']],
            'home_team_side_metadata': meta.get('home_team_side'), 'home_team_id': meta['home_team']['id'],
            'away_team_id': meta['away_team']['id'], 'counts': dict(counts),
            'tracking_fields_record_counts': dict(keys), 'player_observations': dict(players),
            'carrier_frames': dict(carrier), 'ball_frames': dict(ball),
            'local_geometry': dict(local), 'by_period_team_phase': dict(by_context),
            'position_ranges_m': ranges, 'raw_detected_speed_mps_quantiles': quantiles(speeds),
            'timestamp_frame_offsets_frames': dict(timestamp_offsets),
            'event_tracking_time_offsets_seconds': dict(offsets),
            'boundaries': dict(boundaries), 'missing_event_endpoint_frames': len(missing_frames),
            'missing_event_endpoint_rows': sum(len(endpoints[f]) for f in missing_frames),
            'provider_attacking_side_by_period_team': {k: sorted(v) for k, v in direction.items()},
            'passing_option_timing': dict(option_timing), 'events': ev, 'phases': ph}


def pose_audit(path, expected):
    digest = sha(path)
    result = {'path': path.relative_to(ROOT).as_posix(), 'sha256': digest,
              'expected_sha256': expected, 'hash_matches_provider_manifest': digest == expected,
              'scope': 'whole compressed-file hash; first 250 nonempty-player records only; not full JSON/CRC validation'}
    counts = Counter()
    schema = set()
    joint_schema = set()
    with zipfile.ZipFile(path) as archive:
        members = [n for n in archive.namelist() if n.endswith('.jsonl') and not n.startswith('__MACOSX/')]
        result['members'] = members
        with archive.open(members[0]) as handle:
            for line in handle:
                row = json.loads(line)
                if not row.get('player_data'):
                    continue
                counts['nonempty_frames_sampled'] += 1
                for player in row['player_data']:
                    schema.update(player)
                    counts['player_entries'] += 1
                    counts['detected'] += player.get('is_detected') is True
                    for key, value in player.items():
                        if isinstance(value, (dict, list)):
                            joint_schema.add(key)
                if counts['nonempty_frames_sampled'] == 250:
                    break
    result.update(counts=dict(counts), player_fields=sorted(schema), nested_fields=sorted(joint_schema))
    return result


def main():
    OUT.mkdir(exist_ok=True)
    index = json.loads((ROOT / 'data/matches.json').read_text(encoding='utf-8'))
    ids = {str(row['id']) for row in index}
    directories = sorted((ROOT / 'data/matches').iterdir())
    # Explicit local allowlist: index IDs, exact expected filenames, and provider pose manifest.
    allowed = {'data/matches.json', 'data/bodypose/MANIFEST.json',
               'data/bodypose/sample_1925299_phase406.jsonl.gz',
               'data/aggregates/aus1league_physicalaggregates_20242025.csv',
               'data/aggregates/aus1league_passingaggregates_20242025.csv',
               'data/aggregates/aus1league_obraggregates_20242025.csv'}
    for ident in ids:
        for suffix in ('match.json', 'tracking_extrapolated.jsonl', 'dynamic_events.csv', 'phases_of_play.csv'):
            allowed.add(f'data/matches/{ident}/{ident}_{suffix}')
    pose_manifest = json.loads((ROOT / 'data/bodypose/MANIFEST.json').read_text())
    allowed.update(f'pose_data/{ident}.jsonl.zip' for ident in pose_manifest['matches'])
    inputs = [p for base in ('data', 'pose_data') for p in (ROOT / base).rglob('*') if p.is_file() and p.suffix != '.md']
    unknown = [p.relative_to(ROOT).as_posix() for p in inputs if p.relative_to(ROOT).as_posix() not in allowed]
    manifest = {'generated_utc': datetime.now(timezone.utc).isoformat(), 'rules_url': RULES,
                'policy': 'Exact-path allowlist for local audit only. Unknown inputs quarantined. No analytical/publication permission inferred from a filename.',
                'analytical_ingestion_enabled': False, 'publication_enabled': False,
                'pending': 'Match local file hashes to a Cup release manifest or immutable provider release; verify redistribution terms.',
                'unknown_quarantined_inputs': unknown, 'files': []}
    for p in sorted(inputs):
        rel = p.relative_to(ROOT).as_posix()
        if rel in allowed:
            manifest['files'].append({'path': rel, 'bytes': p.stat().st_size, 'sha256': sha(p),
                                      'status': 'allowlisted_for_local_audit', 'provider': 'SkillCorner (local provenance; independent release identity pending)'})
    (OUT / 'eligibility_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    results = []
    for directory in directories:
        if not directory.is_dir() or directory.name not in ids:
            continue
        print('Auditing match ' + directory.name, flush=True)
        results.append(audit_match(directory))
    poses = []
    for ident in pose_manifest['matches']:
        path = ROOT / f'pose_data/{ident}.jsonl.zip'
        if path.exists():
            print('Checking pose ' + ident, flush=True)
            poses.append(pose_audit(path, pose_manifest['files'][f'raw/{ident}.jsonl.zip']['sha256']))
    aggregates = {p.name: csv_audit(p)[0] for p in sorted((ROOT / 'data/aggregates').glob('*.csv')) if p.relative_to(ROOT).as_posix() in allowed}
    totals = {}
    for key in ('counts', 'carrier_frames', 'ball_frames', 'player_observations', 'boundaries', 'local_geometry', 'event_tracking_time_offsets_seconds'):
        total = Counter()
        for row in results:
            total.update(row.get(key, {}))
        totals[key] = dict(total)
    tracked = subprocess.check_output(['git', 'ls-files', 'data', 'pose_data', 'outputs'], cwd=ROOT, text=True).splitlines()
    resource_files = [p.relative_to(ROOT).as_posix() for base in ('notebooks', 'src', 'docs', 'viz_tools') for p in (ROOT / base).rglob('*') if p.is_file()]
    data = {'audit_version': '1.0', 'generated_utc': datetime.now(timezone.utc).isoformat(),
            'python': platform.python_version(), 'script_sha256': sha(Path(__file__)),
            'git_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
            'status': 'ADAPT; eligibility and public redistribution unresolved',
            'scope': 'All local allowlisted XY frames and event/phase CSV rows. Pose bounded sample plus full compressed SHA256. No detector or outcome evaluation.',
            'diagnostic_parameters': {'local_opponent_radius_m': 10, 'raw_speed_warning_mps': 12,
                                      'phase_membership': '[frame_start, frame_end)', 'pose_nonempty_frames_per_match': 250,
                                      'note': 'Diagnostic choices only; no validated detector/quality thresholds.'},
            'matches': results, 'totals': totals, 'poses': poses, 'aggregates': aggregates,
            'tracked_data_and_output_files': tracked, 'resource_inventory': resource_files,
            'limitations': ['No independently verified release manifest for XY/events/aggregates.',
                            'No continuous receiver-corridor visibility audit; absent off-camera opponents cannot be inferred.',
                            'No robust smoothing validation or independent tactical sequence labels.',
                            'No clean-environment dependency validation; audit itself uses standard library.',
                            'Existing P1/P2 outputs are exploratory; no untouched evaluation partition established.']}
    (OUT / 'data_audit.json').write_text(json.dumps(data, indent=2), encoding='utf-8')
    print(json.dumps(totals, indent=2), flush=True)
    print('Wrote reports/data_audit.json and reports/eligibility_manifest.json', flush=True)


if __name__ == '__main__':
    main()
