"""Independent source-file recheck of Phase 0 carrier/context claims.

Uses integer IDs, exhaustive phase membership, and explicit denominator subsets.
No imports from previous audit code; no player inference or tactical labels.
Run: python scripts/verify_carrier_context.py
"""
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/carrier_context_verification'


def identifier(value):
    return None if value is None or value == '' else int(value)


def xy(obj):
    return obj and all(isinstance(obj.get(k), (int, float)) and math.isfinite(obj[k]) for k in ('x', 'y'))


def distance(a, b):
    return round(math.hypot(a['x'] - b['x'], a['y'] - b['y']), 3) if xy(a) and xy(b) else None


def members(rows, frame, convention):
    if convention == 'half_open':
        return [r for r in rows if int(r['frame_start']) <= frame < int(r['frame_end'])]
    if convention == 'inclusive':
        return [r for r in rows if int(r['frame_start']) <= frame <= int(r['frame_end'])]
    if convention == 'strict_interior':
        return [r for r in rows if int(r['frame_start']) < frame < int(r['frame_end'])]
    raise ValueError(convention)


def coverage(rows, period, limit):
    delta = [0] * (limit + 2)
    for r in rows:
        if int(r['period']) == period:
            lo, hi = int(r['frame_start']), int(r['frame_end'])
            delta[lo] += 1
            delta[hi] -= 1
    active = 0
    for i in range(len(delta)):
        active += delta[i]
        delta[i] = active
    return delta


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows):
    with path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else ['no_cases'])
        writer.writeheader()
        writer.writerows(rows)


def verify_match(directory):
    mid = directory.name
    meta = json.loads((directory / f'{mid}_match.json').read_text(encoding='utf-8'))
    teams = {p['id']: p['team_id'] for p in meta['players']}
    names = {p['id']: p['short_name'] for p in meta['players']}
    events = [e for e in read_csv(directory / f'{mid}_dynamic_events.csv') if e['event_type'] == 'player_possession']
    phases = read_csv(directory / f'{mid}_phases_of_play.csv')
    phase_by_period = {p: sorted([r for r in phases if int(r['period']) == p], key=lambda r: int(r['frame_start'])) for p in (1, 2)}
    by_index = {r['index']: r for r in phases}
    limit = max(int(r['end_frame']) for r in meta['match_periods']) + 100
    pmask = {p: coverage(phases, p, limit) for p in (1, 2)}
    emask = {p: coverage(events, p, limit) for p in (1, 2)}
    start_frames = {int(e['frame_start']) for e in events}
    stats = Counter()
    subsets = defaultdict(Counter)
    groups = Counter()
    frames = {}
    details = {}
    source_hashes = {}
    tracking = directory / f'{mid}_tracking_extrapolated.jsonl'
    hasher = hashlib.sha256()
    with tracking.open('rb') as handle:
        for line in handle:
            hasher.update(line)
            row = json.loads(line)
            stats['all_tracking_rows'] += 1
            p, f = row['period'], row['frame']
            if p not in (1, 2):
                stats['outside_period_1_2'] += 1
                continue
            pos = row.get('possession') or {}
            cid = identifier(pos.get('player_id'))
            frames[f] = (p, cid, pos.get('group'))
            unknown = cid is None
            stats['period_frames'] += 1
            stats['null_carrier_period_frames'] += unknown
            groups[str(pos.get('group'))] += 1
            ball = row.get('ball_data') or {}
            flags = {'period_1_2': True,
                     'phase_covered_half_open': f < len(pmask[p]) and pmask[p][f] > 0,
                     'possession_event_covered_half_open': f < len(emask[p]) and emask[p][f] > 0,
                     'tracking_team_group_nonnull': pos.get('group') is not None,
                     'ball_xy_finite': bool(xy(ball)),
                     'ball_detected_and_xy_finite': bool(xy(ball)) and ball.get('is_detected') is True,
                     'players_present': bool(row.get('player_data'))}
            for label, selected in flags.items():
                if selected:
                    subsets[label]['frames'] += 1
                    subsets[label]['null_carrier'] += unknown
            if f in start_frames:
                details[f] = (row.get('timestamp'), ball, {v['player_id']: v for v in row['player_data']})
    source_hashes[tracking.relative_to(ROOT).as_posix()] = hasher.hexdigest()
    for suffix in ('match.json', 'dynamic_events.csv', 'phases_of_play.csv'):
        path = directory / f'{mid}_{suffix}'
        source_hashes[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    carrier_cases, phase_cases = [], []
    for event in events:
        p, f, team, player = (int(event[k]) for k in ('period', 'frame_start', 'team_id', 'player_id'))
        stats['possession_start_rows'] += 1
        if f not in frames or frames[f][0] != p:
            stats['missing_or_wrong_period_start'] += 1
            continue
        _, tracked, group = frames[f]
        stats['start_null_carrier'] += tracked is None
        stats['start_same_carrier'] += tracked == player
        stats['start_known_carrier'] += tracked is not None
        mismatch = tracked is not None and tracked != player
        stats['start_known_carrier_disagreement'] += mismatch
        stats['event_player_metadata_team_disagreement'] += teams.get(player) != team
        pp = phase_by_period[p]
        half = members(pp, f, 'half_open')
        inclusive = members(pp, f, 'inclusive')
        interior = members(pp, f, 'strict_interior')
        for convention, matching in (('half_open', half), ('inclusive', inclusive), ('strict_interior', interior)):
            stats[convention + '_any_phase'] += bool(matching)
            stats[convention + '_multiple_phases'] += len(matching) > 1
            stats[convention + '_no_team_match'] += bool(matching) and not any(int(r['team_in_possession_id']) == team for r in matching)
        # Exactly reproduce old latest-start selection, separately from exhaustive membership.
        preceding = [r for r in pp if int(r['frame_start']) <= f]
        selected = preceding[-1] if preceding and f < int(preceding[-1]['frame_end']) else None
        conflict = selected is not None and int(selected['team_in_possession_id']) != team
        stats['latest_start_half_open_phase_present'] += selected is not None
        stats['latest_start_half_open_phase_disagreement'] += conflict
        stats['phase_disagreement_and_carrier_disagreement'] += conflict and mismatch
        if mismatch:
            timestamp, ball, players = details[f]
            other_team = teams.get(tracked) != team
            stats['carrier_mismatch_opposite_team'] += other_team
            case = {'match_id': mid, 'period': p, 'frame': f, 'timestamp': timestamp,
                    'event_id': event['event_id'], 'event_end_frame': event['frame_end'],
                    'start_type': event['start_type'], 'end_type': event['end_type'],
                    'event_team_id': team, 'event_player_id': player, 'event_player_name': names.get(player),
                    'tracking_player_id': tracked, 'tracking_player_name': names.get(tracked),
                    'tracking_player_team_id': teams.get(tracked), 'tracking_group': group,
                    'same_team': not other_team, 'event_player_detected': players.get(player, {}).get('is_detected'),
                    'tracking_player_detected': players.get(tracked, {}).get('is_detected'),
                    'event_player_ball_distance_m': distance(players.get(player), ball),
                    'tracking_player_ball_distance_m': distance(players.get(tracked), ball)}
            duration = int(event['frame_end']) - f
            inside = [(ff, frames[ff][1]) for ff in range(f, int(event['frame_end']) + 1) if ff in frames and frames[ff][0] == p]
            agreement = [ff - f for ff, cc in inside if cc == player]
            case['event_duration_frames'] = duration
            case['first_event_player_agreement_offset_in_event_frames'] = min(agreement) if agreement else None
            case['known_carrier_frames_within_event_inclusive'] = sum(cc is not None for _, cc in inside)
            case['event_player_agreement_frames_within_event_inclusive'] = len(agreement)
            stats['carrier_mismatch_event_player_seen_later_in_event'] += any(x > 0 for x in agreement)
            for shift in (-10, -5, -2, -1, 0, 1, 2, 5, 10):
                value = frames.get(f + shift)
                case[f'tracking_id_offset_{shift}'] = value[1] if value and value[0] == p else None
                stats[f'mismatch_agrees_at_offset_{shift}'] += bool(value and value[0] == p and value[1] == player)
            carrier_cases.append(case)
        if conflict:
            at_boundary = any(f in (int(row['frame_start']), int(row['frame_end'])) for row in pp)
            stats['phase_conflicts_at_any_boundary'] += at_boundary
            stats['phase_conflicts_with_inclusive_team_match'] += any(int(row['team_in_possession_id']) == team for row in inclusive)
            case = {'match_id': mid, 'period': p, 'frame': f, 'event_id': event['event_id'],
                    'start_type': event['start_type'], 'end_type': event['end_type'], 'event_team_id': team,
                    'event_phase_index': event.get('phase_index'),
                    'event_player_possession_phase_index': event.get('player_possession_phase_index'),
                    'selected_phase_index': selected['index'], 'selected_phase_start': selected['frame_start'],
                    'selected_phase_end': selected['frame_end'], 'selected_phase_team': selected['team_in_possession_id'],
                    'at_phase_boundary': at_boundary, 'half_open_candidate_count': len(half),
                    'inclusive_matching_team_indices': '|'.join(row['index'] for row in inclusive if int(row['team_in_possession_id']) == team),
                    'tracking_carrier_id': tracked, 'tracking_carrier_team': teams.get(tracked), 'tracking_group': group}
            # Only phase_index is evaluated as a candidate phase-row reference.
            # player_possession_phase_index is recorded verbatim; its name does
            # not establish that it is a foreign key into the phase CSV.
            for field in ('phase_index',):
                linked = by_index.get(event.get(field))
                case[field + '_team_matches_event'] = linked is not None and int(linked['team_in_possession_id']) == team
                case[field + '_contains_start_inclusive'] = linked is not None and int(linked['period']) == p and int(linked['frame_start']) <= f <= int(linked['frame_end'])
                stats['phase_conflict_' + field + '_team_agrees'] += case[field + '_team_matches_event']
            phase_cases.append(case)
    return {'match_id': mid, 'counts': dict(stats), 'carrier_missingness_subsets': dict(subsets),
            'tracking_group_values': dict(groups)}, carrier_cases, phase_cases, source_hashes


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ids = sorted(str(r['id']) for r in json.loads((ROOT / 'data/matches.json').read_text(encoding='utf-8')))
    total = Counter()
    subset_total = defaultdict(Counter)
    per_match, carriers, phases, hashes = [], [], [], {}
    for mid in ids:
        result, cc, pc, hh = verify_match(ROOT / 'data/matches' / mid)
        total.update(result['counts'])
        for key, value in result['carrier_missingness_subsets'].items():
            subset_total[key].update(value)
        per_match.append(result)
        carriers.extend(cc)
        phases.extend(pc)
        hashes.update(hh)
        print(mid + ': ' + str(result['counts']['null_carrier_period_frames']) + ' null carriers; ' + str(len(cc)) + ' carrier conflicts; ' + str(len(pc)) + ' phase conflicts', flush=True)
    old = json.loads((ROOT / 'reports/data_audit.json').read_text())
    old_manifest = json.loads((ROOT / 'reports/eligibility_manifest.json').read_text())
    old_hashes = {r['path']: r['sha256'] for r in old_manifest['files']}
    changed = [path for path, digest in hashes.items() if old_hashes.get(path) != digest]
    assert not changed, f'Inputs changed since Phase 0: {changed}'
    assert total['period_frames'] == old['totals']['counts']['active_period_frames']
    assert total['null_carrier_period_frames'] == old['totals']['carrier_frames']['unknown_carrier']
    assert total['start_known_carrier_disagreement'] == old['totals']['start_frame_route_visibility']['known_tracking_carrier_disagrees_starts']
    assert total['latest_start_half_open_phase_disagreement'] == old['totals']['boundaries']['phase_team_disagree']
    result = {'generated_utc': datetime.now(timezone.utc).isoformat(),
              'method': 'Independent raw-source pass; integer IDs; all phase memberships enumerated; no inferred carrier labels.',
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'all_80_input_hashes_match_original_manifest': not changed,
              'counts': dict(total), 'carrier_missingness_subsets': dict(subset_total),
              'matches': per_match, 'input_sha256': hashes,
              'limitations': ['Phase coverage is a provider-label proxy for in-play, not independently verified ball state.',
                              'Adjacent-frame agreement diagnoses boundary sensitivity; it cannot establish correct tactical ownership.',
                              'Event intervals and linked phase fields may contain retrospective information. No online reconstruction validated.']}
    (OUT / 'verification.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    write_csv(OUT / 'carrier_disagreements.csv', carriers)
    write_csv(OUT / 'phase_disagreements.csv', phases)
    print(json.dumps({'counts': dict(total), 'subsets': dict(subset_total)}, indent=2))


if __name__ == '__main__':
    main()
