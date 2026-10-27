"""Check whether engagement time_start maps to frame_physical_start locally."""
import csv
import json
from collections import Counter

from audit_phase0 import ROOT, OUT, clock, sha


def main():
    audit = json.loads((OUT / 'data_audit.json').read_text())
    total = Counter()
    for match in audit['matches']:
        c = Counter()
        ident = match['match_id']
        period_offsets = {}
        for key in match['timestamp_frame_offsets_frames']:
            period, offset = key.split(':')
            period_offsets.setdefault(int(period), set()).add(float(offset))
        with (ROOT / f'data/matches/{ident}/{ident}_dynamic_events.csv').open(encoding='utf-8-sig', newline='') as h:
            for event in csv.DictReader(h):
                if event['event_type'] != 'on_ball_engagement':
                    continue
                c['engagement_rows'] += 1
                options = period_offsets.get(int(event['period']), set())
                if len(options) != 1 or not event.get('frame_physical_start'):
                    c['unresolved'] += 1
                    continue
                expected = (int(event['frame_physical_start']) - next(iter(options))) / 10
                c['physical_start_time_agrees'] += abs(clock(event['time_start']) - expected) < 1e-5
        meta = json.loads((ROOT / f'data/matches/{ident}/{ident}_match.json').read_text(encoding='utf-8'))
        opposite = {'left_to_right': 'right_to_left', 'right_to_left': 'left_to_right'}
        for period in (1, 2):
            for team, expected in ((meta['home_team']['id'], meta['home_team_side'][period - 1]),
                                   (meta['away_team']['id'], opposite[meta['home_team_side'][period - 1]])):
                actual = match['provider_attacking_side_by_period_team'].get(f'{period}:{team}')
                c['direction_period_team_groups'] += 1
                c['direction_groups_agree_metadata'] += actual == [expected]
        match['event_semantics_diagnostics'] = dict(c)
        total.update(c)
    audit['totals']['event_semantics_diagnostics'] = dict(total)
    audit['event_semantics_script_sha256'] = sha(ROOT / 'scripts/audit_event_semantics.py')
    (OUT / 'data_audit.json').write_text(json.dumps(audit, indent=2), encoding='utf-8')
    print(json.dumps(total, indent=2))


if __name__ == '__main__':
    main()
