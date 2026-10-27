"""Read-only proposal counts and overlap checks; no tactical performance claims."""
import json
from run_presslens import ROOT
from presslens.candidates import candidates, source_diagnostics
from presslens.focused import FocusedLog
from presslens.replay import ReplayStore


def main():
    store = ReplayStore(ROOT)
    focused = FocusedLog(ROOT / '.presslens/pass_reviews.jsonl')
    rows, omissions = [], []
    for mid in store.ids:
        match = store.load(mid)
        primary = candidates(match, 'pressure', focused)
        human = candidates(match, 'manual', focused)
        eligible = [e for e in match.events if e['event_type'] == 'on_ball_engagement' and e.get('event_subtype') in ('pressure', 'pressing')]
        represented = {e['event_id'] for c in primary for e in c['engagements']}
        omissions.extend({'match_id': mid, **e} for e in source_diagnostics(match, False, primary)['omitted_engagements'])
        overlaps = [sum(c['period'] == h['period'] and c['start_frame'] <= h['end_frame'] and c['end_frame'] >= h['start_frame'] for c in primary) for h in human]
        row = {'match_id': mid, 'source_pressure_pressing_engagements': len(eligible),
               'represented_engagements': len(represented), 'candidate_episodes': len(primary),
               'omitted_unresolved_engagements': len(eligible)-len(represented),
               'flagged_tracking_gap_episodes': sum('Tracking gaps inside proposal' in c['flags'] for c in primary),
               'saved_human_examples': len(human), 'human_examples_without_overlap': sum(n == 0 for n in overlaps)}
        rows.append(row)
        print(json.dumps(row), flush=True)
    report = {'status': 'completed', 'software': store.software, 'policy': match.candidate_policy, 'matches': rows,
              'omitted_engagements': omissions,
              'totals': {key: sum(r[key] for r in rows) for key in rows[0] if key != 'match_id'},
              'interpretation': 'Provider-derived proposals, not confirmed pressure or funneling. Overlap is not full-match recall; source bounds and carrier identities require review. No outcome filtering or human annotation writes.'}
    (ROOT / 'reports/pressure_candidate_audit.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report['totals'], indent=2))


if __name__ == '__main__':
    main()
