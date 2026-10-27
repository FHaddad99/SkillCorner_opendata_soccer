"""Add start-frame route visibility and bounded pose alignment to Phase 0.

Run after audit_phase0.py. Diagnostics are not tactical detectors.
"""
import csv
import gzip
import json
import math
import re
import zipfile
from collections import Counter

from audit_phase0 import ROOT, OUT, finite_xy, state, quantiles, sha, clock


def corridor_distance(point, start, end):
    dx, dy = end['x'] - start['x'], end['y'] - start['y']
    norm = dx * dx + dy * dy
    if norm == 0:
        return None
    u = ((point['x'] - start['x']) * dx + (point['y'] - start['y']) * dy) / norm
    if not 0 < u < 1:
        return None
    return math.hypot(point['x'] - start['x'] - u * dx, point['y'] - start['y'] - u * dy)


def main():
    data = json.loads((OUT / 'data_audit.json').read_text())
    totals = Counter()
    for result in data['matches']:
        ident = result['match_id']
        directory = ROOT / 'data/matches' / ident
        meta = json.loads((directory / f'{ident}_match.json').read_text(encoding='utf-8'))
        teams = {str(p['id']): str(p['team_id']) for p in meta['players']}
        with (directory / f'{ident}_dynamic_events.csv').open(encoding='utf-8-sig', newline='') as h:
            events = list(csv.DictReader(h))
        starts = {}
        for e in events:
            if e['event_type'] == 'player_possession':
                starts.setdefault(int(e['frame_start']), []).append(e)
        c = Counter()
        endpoint_rows = {}
        offsets = {}
        for e in events:
            for edge in ('start', 'end'):
                endpoint_rows.setdefault(int(e['frame_' + edge]), []).append((e, edge))
        with (directory / f'{ident}_tracking_extrapolated.jsonl').open(encoding='utf-8') as h:
            for line in h:
                match = re.match(r'\s*\{\s*"frame"\s*:\s*(\d+)', line)
                if match and int(match[1]) not in endpoint_rows:
                    continue
                frame = json.loads(line)
                for e, edge in endpoint_rows.get(frame['frame'], []):
                    t, et = clock(frame.get('timestamp')), clock(e.get('time_' + edge))
                    if t is not None and et is not None:
                        key = e['event_type'] + ':' + edge
                        offsets.setdefault(key, Counter())[str(round(et - t, 3))] += 1
                rows = starts.get(frame['frame'], [])
                ps = {str(p['player_id']): p for p in frame.get('player_data', [])}
                for e in rows:
                    if str(frame['period']) != e['period']:
                        continue
                    carrier = ps.get(e['player_id'])
                    c['possession_starts'] += 1
                    c['tracking_carrier_unknown_starts'] += frame.get('possession', {}).get('player_id') is None
                    if frame.get('possession', {}).get('player_id') is not None:
                        c['known_tracking_carrier_disagrees_starts'] += str(frame['possession']['player_id']) != e['player_id']
                    if e['start_type'] == 'pass_reception':
                        c['pass_reception_starts'] += 1
                        c['pass_reception_carrier_ball_detected'] += state(carrier) == state(frame.get('ball_data')) == 'detected'
                    if not carrier or not finite_xy(carrier):
                        c['carrier_invalid_starts'] += 1
                        continue
                    c['finite_carrier_starts'] += 1
                    c['all_present_opponents_detected_starts'] += all(state(p) == 'detected' for pid, p in ps.items() if teams.get(pid) and teams[pid] != e['team_id'])
                    expected = set()
                    for player in meta['players']:
                        intervals = player.get('playing_time', {}).get('by_period', [])
                        if any(v.get('name') == f"period_{e['period']}" and v.get('start_frame', math.inf) <= frame['frame'] < v.get('end_frame', -math.inf) for v in intervals):
                            expected.add(str(player['id']))
                    c['expected_active_player_slots'] += len(expected)
                    c['expected_active_slots_absent_or_invalid'] += sum(state(ps.get(pid)) == 'absent_or_invalid' for pid in expected)
                    for pid, target in ps.items():
                        if pid == e['player_id'] or teams.get(pid) != e['team_id'] or not finite_xy(target):
                            continue
                        c['teammate_routes'] += 1
                        c['carrier_receiver_both_detected_routes'] += state(carrier) == state(target) == 'detected'
                        corridor = []
                        for oid, opponent in ps.items():
                            if teams.get(oid) and teams[oid] != e['team_id'] and finite_xy(opponent):
                                distance = corridor_distance(opponent, carrier, target)
                                if distance is not None and distance <= 2:
                                    corridor.append(state(opponent))
                        c['routes_with_known_corridor_opponent'] += bool(corridor)
                        c['routes_with_extrapolated_corridor_opponent'] += 'extrapolated' in corridor
                        c['routes_with_all_known_corridor_opponents_detected'] += bool(corridor) and all(s == 'detected' for s in corridor)
        result['start_frame_route_visibility'] = dict(c)
        result['event_clock_offsets_by_type_and_edge_seconds'] = offsets
        result['possession_start_types'] = dict(Counter(e['start_type'] for e in events if e['event_type'] == 'player_possession'))
        totals.update(c)
        print('Route diagnostics ' + ident, flush=True)
    data['totals']['start_frame_route_visibility'] = dict(totals)
    # Exact shared ticks only. Pose frame/2.5 must be an integer; never round silently.
    for pose in data['poses']:
        ident = pose['path'].split('/')[-1].split('.')[0]
        samples = {}
        counts = Counter()
        joint_fields = Counter()
        with zipfile.ZipFile(ROOT / pose['path']) as archive:
            with archive.open(pose['members'][0]) as h:
                for line in h:
                    row = json.loads(line)
                    if not row.get('player_data'):
                        continue
                    counts['frames'] += 1
                    for p in row['player_data']:
                        joints = p.get('joints')
                        counts['player_entries'] += 1
                        counts['entries_with_joints'] += bool(joints)
                        if joints:
                            counts['joints_on_nondetected_entry'] += p.get('is_detected') is not True
                            counts['joint_observations'] += len(joints)
                            for j in joints.values():
                                joint_fields.update(j.keys())
                    if row['frame'] % 5 == 0:
                        samples[int(row['frame'] / 2.5)] = row
                    if counts['frames'] == 250:
                        break
        deltas = []
        tracking = ROOT / f'data/matches/{ident}/{ident}_tracking_extrapolated.jsonl'
        with tracking.open(encoding='utf-8') as h:
            for line in h:
                row = json.loads(line)
                if row['frame'] in samples:
                    pp = {p['player_id']: p for p in samples[row['frame']]['player_data']}
                    for p in row['player_data']:
                        q = pp.get(p['player_id'])
                        if q and finite_xy(p) and finite_xy(q):
                            deltas.append(math.hypot(p['x'] - q['x'], p['y'] - q['y']))
                            counts['shared_tick_player_pairs'] += 1
                            counts['shared_tick_detection_disagreement'] += p.get('is_detected') != q.get('is_detected')
                    counts['shared_tick_period_disagreement'] += row['period'] != samples[row['frame']]['period']
                if samples and row['frame'] > max(samples):
                    break
        pose['bounded_alignment'] = {'counts': dict(counts), 'joint_fields_counts': dict(joint_fields),
                                     'xy_delta_m_quantiles': quantiles(deltas),
                                     'scope': 'First 250 nonempty pose frames; 50 exact shared ticks. Not representative of full match.'}
    sample_counts = Counter()
    with gzip.open(ROOT / 'data/bodypose/sample_1925299_phase406.jsonl.gz', 'rt', encoding='utf-8') as h:
        for line in h:
            row = json.loads(line)
            sample_counts['frames'] += 1
            sample_counts['joint_observations'] += sum(len(p.get('joints') or {}) for p in row['player_data'])
    data['pose_sample_counts'] = dict(sample_counts)
    data['diagnostic_parameters']['corridor_half_width_m'] = 2
    data['detail_script_sha256'] = sha(ROOT / 'scripts/audit_phase0_details.py')
    data['limitations'][1] = 'Route visibility measured only at possession starts using 2m corridors between listed teammates; absent off-camera opponents cannot be inferred. No continuous route validation.'
    (OUT / 'data_audit.json').write_text(json.dumps(data, indent=2), encoding='utf-8')
    print(json.dumps(totals, indent=2))


if __name__ == '__main__':
    main()
