"""Inspect source support for a saved human annotation without changing it.

Outputs role-specific visibility, separations and nearby provider possessions.
Usage: python scripts/inspect_annotation_evidence.py ANNOTATION_ID
This is evidence inspection, not a detector or an automatic annotation correction.
"""
import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('annotation_id')
    args = parser.parse_args()
    log = ROOT / '.presslens/annotations.jsonl'
    records = [json.loads(line) for line in log.read_text(encoding='utf-8').splitlines() if line.strip()]
    matching = [r for r in records if r['annotation_id'] == args.annotation_id]
    if not matching:
        raise SystemExit('Annotation ID not found')
    record = max(matching, key=lambda r: r['revision'])
    mid, observation = record['match_id'], record['observation']
    directory = ROOT / 'data/matches' / mid
    for suffix, expected in record['provenance']['input_sha256'].items():
        with (directory / f'{mid}_{suffix}').open('rb') as handle:
            if hashlib.file_digest(handle, 'sha256').hexdigest() != expected:
                raise SystemExit('Source changed since annotation: ' + suffix)
    metadata = json.loads((directory / f'{mid}_match.json').read_text(encoding='utf-8'))
    roster = {p['id']: p for p in metadata['players']}
    start, end = observation['start_frame'], observation['end_frame']
    # One adjacent ten-second window is a diagnostic context choice, not a detector threshold.
    lower, upper = max(0, start - 100), end + 100
    rows = []
    with (directory / f'{mid}_tracking_extrapolated.jsonl').open(encoding='utf-8') as handle:
        for line in handle:
            r = json.loads(line)
            if r['frame'] > upper:
                break
            if lower <= r['frame'] <= upper and r['period'] == observation['period']:
                rows.append(r)
    selected = [r for r in rows if start <= r['frame'] <= end]
    with (directory / f'{mid}_dynamic_events.csv').open(encoding='utf-8-sig', newline='') as handle:
        possessions = [e for e in csv.DictReader(handle) if e['event_type'] == 'player_possession' and int(e['period']) == observation['period'] and lower <= int(e['frame_start']) <= upper]
    ids = {observation.get('primary_presser_id'), observation.get('nominated_carrier_id'), *observation.get('supporting_defender_ids', [])}
    for role in observation.get('supporting_roles', []):
        ids.update((role['player_id'], role.get('target_player_id')))
    ids.update(int(e['player_id']) for e in possessions)
    target = 50994 if mid == '1874553' else None
    # Include Brown only for the explicitly reviewed first case; this is not inferred target selection.
    if target in roster:
        ids.add(target)
    actors = []
    for pid in sorted(p for p in ids if p is not None):
        counts = Counter()
        for r in selected:
            p = next((p for p in r['player_data'] if p['player_id'] == pid), None)
            counts['absent' if p is None else 'detected' if p.get('is_detected') is True else 'extrapolated' if p.get('is_detected') is False else 'unknown_detection'] += 1
        actors.append({'player_id': pid, 'name': roster.get(pid, {}).get('short_name'), 'counts': dict(counts)})
    keys = ('event_id', 'frame_start', 'frame_end', 'player_id', 'player_name', 'start_type', 'end_type',
            'pass_direction_received', 'player_targeted_id', 'player_targeted_name', 'pass_outcome')
    output = {'annotation_id': record['annotation_id'], 'revision_reviewed': record['revision'], 'match_id': mid,
              'source_hashes_match_saved_annotation': True, 'saved_observation': observation,
              'scope': 'Recorded interval and at most ten seconds of same-period context either side; includes retrospective provider labels.',
              'annotation_log_unchanged': True, 'selected_frame_count': len(selected),
              'role_and_carrier_visibility': actors,
              'nearby_provider_possessions': [{k: e.get(k) for k in keys} for e in possessions],
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    if mid == '1874553' and start == 32 and end == 61:
        import math
        output['first_case_mauk_warland_distances_m'] = []
        for r in selected:
            if r['frame'] in (32, 42, 50, 61):
                ps = {p['player_id']: p for p in r['player_data']}
                a, b = ps[50959], ps[51050]
                output['first_case_mauk_warland_distances_m'].append({'frame': r['frame'], 'distance_m': round(math.hypot(a['x'] - b['x'], a['y'] - b['y']), 3)})
    folder = ROOT / '.presslens/annotation_reviews'
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f'{record["annotation_id"]}_evidence.json'
    path.write_text(json.dumps(output, indent=2), encoding='utf-8')
    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
