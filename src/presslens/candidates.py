"""Provider-derived review proposals, kept separate from human judgements."""
import copy
import hashlib
import json
from datetime import datetime, timezone

from .focused import FocusedLog, clip_id
from .annotation_protocol import replay_disclosure

POLICY = {'version': 'engagement-candidates-1.0', 'gap_frames': 0, 'context_frames': 30}


def source_diagnostics(match, expanded, cases):
    eligible = [e for e in match.events if e['event_type'] == 'on_ball_engagement'
                and (expanded or e.get('event_subtype') in ('pressure', 'pressing'))]
    represented = {e['event_id'] for c in cases for e in c.get('engagements', [])}
    omitted = []
    for e in eligible:
        if e['event_id'] in represented:
            continue
        reason = 'Invalid or unavailable bounds/period'
        try:
            if int(e['player_id']) not in match.players:
                reason = 'Defender ID absent from match roster'
        except (ValueError, KeyError):
            reason = 'Defender ID unresolved'
        omitted.append({k: e.get(k) for k in ('event_id', 'period', 'frame_start', 'frame_end', 'player_id')} | {'reason': reason})
    return {'source_engagements': len(eligible), 'represented_engagements': len(represented),
            'invalid_or_unavailable_bound_engagements': len(omitted), 'omitted_engagements': omitted}


def candidates(match, pool, focused):
    if pool not in ('pressure', 'expanded', 'manual', 'audit'):
        raise ValueError('Unknown candidate pool')
    policy = getattr(match, 'candidate_policy', POLICY)
    if (type(policy.get('gap_frames')) is not int or not 0 <= policy['gap_frames'] <= 10
            or type(policy.get('context_frames')) is not int or not 0 <= policy['context_frames'] <= 100):
        raise ValueError('Candidate policy requires gap 0–10 and context 0–100 native frames')
    revision = hashlib.sha256(json.dumps(match.hashes, sort_keys=True).encode()).hexdigest()

    def case(start, end, period, source, team=None, members=None):
        c = {'match_id': match.mid, 'period': period, 'start_frame': start, 'end_frame': end,
             'anchor_frame': start, 'source_kind': source, 'source_id': members or f'{start}-{end}',
             'input_revision': revision, 'source_team_id': team, 'pool': pool,
             'candidate_policy': copy.deepcopy(policy)}
        c['sequence_id'] = clip_id(c)
        c['candidate_id'] = hashlib.sha256((c['sequence_id'] + json.dumps(policy, sort_keys=True)).encode()).hexdigest()[:24]
        limits = match.periods[period]
        c['context_start_frame'] = max(limits['start'], start-policy['context_frames'])
        c['context_end_frame'] = min(limits['end'], end+policy['context_frames'])
        return c

    if pool == 'manual':
        result = []
        for r in focused.latest(match.mid, 'press'):
            if not r.get('press_event'):
                continue
            e = r['press_event']
            c = case(e['start_frame'], e['end_frame'], e['period'], 'human_marked_press',
                     e['defending_team_id'], r['event_id'] if r.get('event_id') else focused.event_id(r))
            c['source_review_scope'] = r.get('review_scope', {'status': 'not_recorded'})
            result.append(c)
        return sorted(result, key=lambda c: (c['period'], c['start_frame'], c['candidate_id']))

    events = []
    for e in match.events:
        if e['event_type'] != 'on_ball_engagement':
            continue
        if pool != 'expanded' and e.get('event_subtype') not in ('pressure', 'pressing'):
            continue
        try:
            start, end, period, pid = (int(e[k]) for k in ('frame_start', 'frame_end', 'period', 'player_id'))
            team = match.players[pid]['team_id']
            if period not in match.periods or start > end or match.raw(start)['period'] != period or match.raw(end)['period'] != period:
                continue
        except (ValueError, KeyError):
            continue
        events.append((period, team, start, end, e))
    # Boundaries with an interruption or an attacking-team change block grouping.
    barriers = {p: set() for p in match.periods}
    for e in match.events:
        try:
            p, start, end = int(e['period']), int(e['frame_start']), int(e['frame_end'])
            for key, f in [('game_interruption_before', start), ('game_interruption_after', end)]:
                if e.get(key) not in (None, '', 'none', 'unknown'):
                    barriers.get(p, set()).add(f)
        except (ValueError, KeyError):
            continue
    for p in match.periods:
        poss = sorted((e for e in match.possessions if int(e['period']) == p), key=lambda e: int(e['frame_start']))
        for a, b in zip(poss, poss[1:]):
            if a['team_id'] != b['team_id']:
                barriers[p].add(int(b['frame_start']))
    groups = []
    for period, team, start, end, e in sorted(events, key=lambda e: e[:4]):
        previous = groups[-1] if groups else None
        merge = previous and previous['period'] == period and previous['team'] == team and start <= previous['end'] + policy['gap_frames']
        if merge:
            merge = not any(previous['start'] < b <= max(previous['end'], end) for b in barriers[period])
            merge = merge and all(f in match.offsets for f in range(previous['start'], max(previous['end'], end)+1))
        if merge:
            previous['end'] = max(previous['end'], end)
            previous['members'].append(e)
        else:
            groups.append({'period': period, 'team': team, 'start': start, 'end': end, 'members': [e]})
    result = []
    for g in groups:
        members = [{'event_id': e['event_id'], 'start_frame': int(e['frame_start']), 'end_frame': int(e['frame_end']),
                    'player_id': int(e['player_id']), 'carrier_id': int(e['player_in_possession_id']) if e.get('player_in_possession_id') else None,
                    'provider_team_id': e.get('team_id'),
                    'subtype': e.get('event_subtype'), 'pressing_chain_index': e.get('pressing_chain_index')} for e in g['members']]
        c = case(g['start'], g['end'], g['period'], 'provider_engagement_candidate', g['team'],
                 '|'.join(sorted(e['event_id'] for e in members)))
        c['engagements'] = members
        c['flags'] = ['Provider proposal; pressure and scope not confirmed']
        if any(f not in match.offsets for f in range(g['start'], g['end']+1)):
            c['flags'].append('Tracking gaps inside proposal')
        if any(g['start'] < b < g['end'] for b in barriers[g['period']]):
            c['flags'].append('Interruption or possession-team change inside source proposal; check bounds')
        if any(e['provider_team_id'] not in (None, '', str(g['team'])) for e in members):
            c['flags'].append('Engagement team disagrees with defender roster team')
        if any(e['carrier_id'] not in match.players for e in members):
            c['flags'].append('Engagement carrier missing or unresolved against roster')
        result.append(c)
    if pool == 'audit':
        # Ten-second windows outside the primary candidate intervals, throughout both halves.
        audit = []
        for period, limits in match.periods.items():
            for start in range(limits['start'], limits['end']+1, 100):
                end = min(start+99, limits['end'])
                if not any(c['period'] == period and c['start_frame'] <= end and c['end_frame'] >= start for c in result):
                    audit.append(case(start, end, period, 'noncandidate_audit_window'))
        return audit
    return sorted(result, key=lambda c: (c['period'], c['start_frame'], c['candidate_id']))


class CandidateReviews(FocusedLog):
    def latest(self, mid=None, reviewer=None):
        with self.lock:
            rows = {}
            for r in self.records():
                rows[(r['candidate_id'], r['reviewer'])] = r
            return [r for r in rows.values() if (mid is None or r['match_id'] == mid) and (reviewer is None or r['reviewer'] == reviewer)]

    def save(self, payload, match, focused, session):
        with self.lock:
            reviewer = str(payload.get('reviewer', '')).strip()
            if not reviewer or len(reviewer) > 100:
                raise ValueError('Enter your reviewer name')
            original = next((c for c in candidates(match, payload.get('pool'), focused) if c['candidate_id'] == payload.get('candidate_id')), None)
            if original is None:
                raise ValueError('Candidate changed or was removed. Reload the queue.')
            prior = next((r for r in self.latest(match.mid, reviewer) if r['candidate_id'] == original['candidate_id']), None)
            if payload.get('base_revision', 0) != (prior['revision'] if prior else 0):
                raise ValueError('Review changed in another tab. Reload the queue.')
            start, end = payload.get('start_frame'), payload.get('end_frame')
            if type(start) is not int or type(end) is not int or start > end:
                raise ValueError('Enter ordered start and end frames')
            if match.raw(start)['period'] != original['period'] or match.raw(end)['period'] != original['period']:
                raise ValueError('Keep the interval in its original half')
            decision = payload.get('decision')
            if decision not in ('yes', 'no', 'uncertain', 'unassessable', 'not_pressure', 'out_of_scope', 'unreviewed'):
                raise ValueError('Choose a review decision')
            scope = payload.get('scope_reason')
            if decision == 'out_of_scope' and scope not in ('counter_attack', 'fast_break', 'repress'):
                raise ValueError('Choose the excluded situation')
            revised = {**original, 'start_frame': start, 'end_frame': end, 'anchor_frame': start}
            revised['sequence_id'] = clip_id(revised)
            limits = match.periods[original['period']]
            revised['context_start_frame'] = max(limits['start'], start-original['candidate_policy']['context_frames'])
            revised['context_end_frame'] = min(limits['end'], end+original['candidate_policy']['context_frames'])
            row = {'schema_version': 'candidate-review-1.0', 'match_id': match.mid,
                   'candidate_id': original['candidate_id'], 'original_case': original, 'case': revised,
                   'reviewer': reviewer, 'revision': prior['revision']+1 if prior else 1,
                   'saved_utc': datetime.now(timezone.utc).isoformat(), 'decision': decision,
                   'funnel': decision if decision in ('yes', 'no', 'uncertain', 'unassessable') else 'not_assessed',
                   'pressure_status': 'rejected' if decision == 'not_pressure' else 'not_independently_confirmed',
                   'scope_reason': scope if decision == 'out_of_scope' else None,
                   'review_scope': copy.deepcopy(match.review_scope),
                   'replay_review': replay_disclosure(payload, revised, match, prior, session),
                   'interval_quality': match.interval_quality(start, end),
                   'provenance': {'input_sha256': match.hashes, 'software': match.software, 'outcome_filtered': False,
                                  'provider_context_revealed': True, 'partition': 'development'},
                   'semantics': 'Candidate-conditioned funnel review. Deferred, unknown and unreviewed decisions are not negatives.'}
            self._append(row)
            return row
