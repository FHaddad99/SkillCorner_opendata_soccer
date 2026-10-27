"""Focused yes/no review passes with explicit abstention and exact clip joins."""
import hashlib
import json
import os
import threading
import uuid
import copy
from datetime import datetime, timezone

from . import __version__
from .annotation_protocol import replay_disclosure

PASSES = {'press', 'funnel', 'cue'}
CUES = {'backward_pass', 'wide_reception'}


def clip_id(case):
    identity = {key: case[key] for key in ('match_id', 'period', 'start_frame', 'end_frame', 'source_kind', 'source_id', 'input_revision')}
    return hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:24]


def build_queue(match, detailed, pool, bank=None):
    """Sampling windows only; no detector, outcome filter, or positive prelabels."""
    cases = []
    if pool == 'possession_windows':
        for e in match.possessions:
            period, anchor = int(e['period']), int(e['frame_start'])
            if period not in match.periods:
                continue
            limits = match.periods[period]
            cases.append({'match_id': match.mid, 'period': period,
                          'start_frame': max(limits['start'], anchor - 30),
                          'end_frame': min(limits['end'], int(e['frame_end']) + 50), 'anchor_frame': anchor,
                          'source_kind': 'provider_possession_window', 'source_id': e['event_id'],
                          'source_team_id': int(e['team_id'])})
    elif pool == 'marked_intervals':
        cases = bank.cases(match) if bank else []
    elif pool == 'saved_intervals':
        for record in detailed.latest(match.mid):
            if record.get('provenance', {}).get('input_sha256') != match.hashes:
                raise ValueError('A saved detailed interval refers to a different input release; review its provenance before reusing it.')
            o = record['observation']
            cases.append({'match_id': match.mid, 'period': o['period'],
                          'start_frame': o.get('context_start_frame', o['start_frame']),
                          'end_frame': o['end_frame'], 'anchor_frame': o['start_frame'],
                          'source_kind': 'saved_detailed_interval', 'source_id': record['annotation_id'],
                          'source_team_id': None})
    else:
        raise ValueError('Unknown review pool')
    for case in cases:
        case['input_revision'] = hashlib.sha256(json.dumps(match.hashes, sort_keys=True).encode()).hexdigest()
        case['sequence_id'] = clip_id(case)
        case['pool'] = pool
    return sorted(cases, key=lambda c: (c['period'], c['anchor_frame'], c['sequence_id']))


class SequenceBank:
    """Shared manually marked intervals, independent of all pass judgements."""
    def __init__(self, path):
        self.path = path
        self.lock = threading.RLock()

    def cases(self, match):
        if not self.path.exists():
            return []
        revision = hashlib.sha256(json.dumps(match.hashes, sort_keys=True).encode()).hexdigest()
        with self.lock, self.path.open(encoding='utf-8') as h:
            rows = [json.loads(line) for line in h if line.strip()]
        rows = [r for r in rows if r['match_id'] == match.mid]
        if any(r['input_revision'] != revision for r in rows):
            raise ValueError('A marked interval refers to a different input release. Review source provenance before reusing it.')
        return rows

    def records(self):
        if not self.path.exists():
            return []
        with self.lock, self.path.open(encoding='utf-8') as h:
            return [json.loads(line) for line in h if line.strip()]

    def add(self, match, start, end):
        if type(start) is not int or type(end) is not int or start > end:
            raise ValueError('Mark an ordered native start/end interval')
        first, last = match.raw(start), match.raw(end)
        if first['period'] not in (1, 2) or first['period'] != last['period']:
            raise ValueError('Mark an interval inside one playing period')
        case = {'match_id': match.mid, 'period': first['period'], 'start_frame': start,
                'end_frame': end, 'anchor_frame': start, 'source_kind': 'manual_marked_interval',
                'source_id': f'{start}-{end}', 'source_team_id': None, 'pool': 'marked_intervals',
                'input_revision': hashlib.sha256(json.dumps(match.hashes, sort_keys=True).encode()).hexdigest()}
        case['sequence_id'] = clip_id(case)
        with self.lock:
            existing = next((r for r in self.cases(match) if r['sequence_id'] == case['sequence_id']), None)
            if existing:
                return existing
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open('a', encoding='utf-8', newline='\n') as h:
                h.write(json.dumps(case) + '\n')
                h.flush()
                os.fsync(h.fileno())
        return case


def question_key(review_pass, cue_type=None):
    if review_pass not in PASSES:
        raise ValueError('Unknown focused pass')
    if review_pass == 'cue':
        if cue_type not in CUES:
            raise ValueError('Choose one cue type for this pass')
        return 'cue:' + cue_type
    return review_pass


class FocusedLog:
    def __init__(self, path):
        self.path = path
        self.lock = threading.RLock()

    def records(self):
        if not self.path.exists():
            return []
        with self.path.open(encoding='utf-8') as h:
            return [json.loads(line) for line in h if line.strip()]

    def latest(self, mid=None, question=None, reviewer=None, include_deleted=False):
        with self.lock:
            latest = {}
            for row in self.records():
                key = (self.event_id(row) if row.get('press_event') else row['sequence_id'], row['question_key'], row['reviewer'])
                latest[key] = row
            return [r for r in latest.values() if (mid is None or r['match_id'] == mid)
                    and (question is None or r['question_key'] == question)
                    and (reviewer is None or r['reviewer'] == reviewer) and (include_deleted or not r.get('deleted', False))]

    @staticmethod
    def event_id(row):
        return row.get('event_id') or 'legacy-press-' + hashlib.sha256((row['match_id'] + ':' + row['reviewer'] + ':' + row['sequence_id']).encode()).hexdigest()[:24]

    def set_deleted(self, payload, match):
        with self.lock:
            reviewer = str(payload.get('reviewer', '')).strip()
            if not reviewer:
                raise ValueError('Specify the event reviewer')
            prior = next((r for r in self.latest(match.mid, 'press', reviewer, include_deleted=True)
                          if r.get('press_event') and self.event_id(r) == payload.get('event_id')), None)
            if prior is None:
                raise ValueError('Saved press event not found')
            if payload.get('base_revision') != prior['revision']:
                raise ValueError('Event changed in another tab. Reload saved events before continuing.')
            if type(payload.get('deleted')) is not bool:
                raise ValueError('Specify delete or restore')
            row = copy.deepcopy(prior)
            row.update(event_id=self.event_id(prior), revision=prior['revision'] + 1,
                       deleted=payload['deleted'], saved_utc=datetime.now(timezone.utc).isoformat(),
                       review_protocol_version='3.2',
                       record_action='delete' if payload['deleted'] else 'restore')
            row['provenance'].update(software_version=__version__, software=match.software)
            self._append(row)
            return row

    def _append(self, row):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open('a', encoding='utf-8', newline='\n') as h:
            h.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + '\n')
            h.flush()
            os.fsync(h.fileno())

    def save(self, payload, match, detailed, session, bank=None):
        with self.lock:
            reviewer = str(payload.get('reviewer', '')).strip()
            if not reviewer or len(reviewer) > 100:
                raise ValueError('Enter your reviewer name once before reviewing clips')
            question = question_key(payload.get('pass'), payload.get('cue_type'))
            queue = build_queue(match, detailed, payload.get('pool'), bank)
            case = next((c for c in queue if c['sequence_id'] == payload.get('sequence_id')), None)
            if case is None:
                raise ValueError('This clip is no longer in the queue. Reload the queue before saving.')
            answer = payload.get('answer')
            if answer not in ('yes', 'no', 'skip'):
                raise ValueError('Choose yes, no or skip')
            reason = payload.get('skip_reason', 'uncertain') if answer == 'skip' else None
            if reason not in (None, 'uncertain', 'visibility', 'not_applicable'):
                raise ValueError('Unknown skip reason')
            prior = next((r for r in self.latest(match.mid, question, reviewer) if r['sequence_id'] == case['sequence_id']), None)
            expected_revision = prior['revision'] if prior else 0
            if payload.get('base_revision', 0) != expected_revision:
                raise ValueError('This decision changed in another tab. Reload the pass before revising it.')
            disclosure = replay_disclosure(payload, case, match, prior, session)
            row = {'schema_version': 'focused-1.0', 'review_protocol_version': '3.0',
                   'sequence_id': case['sequence_id'], 'case': case, 'match_id': match.mid,
                   'question_key': question, 'pass': payload['pass'],
                   'cue_type': payload.get('cue_type') if payload['pass'] == 'cue' else None,
                   'reviewer': reviewer, 'revision': expected_revision + 1,
                   'answer': answer, 'skip_reason': reason, 'note': str(payload.get('note', ''))[:2000],
                   'saved_utc': datetime.now(timezone.utc).isoformat(), 'replay_review': disclosure,
                   'provenance': {'software_version': __version__, 'software': match.software,
                                  'input_sha256': match.hashes, 'manifest_sha256': match.manifest_hash,
                                  'partition': 'development', 'prior_exposure': 'legacy_all_match_exploration',
                                  'sampling_pool': case['pool'], 'outcome_filtered': False,
                                  'provider_context_revealed_in_session': match.mid in session['provider_revealed'],
                                  'outcomes_revealed_in_session': match.mid in session['outcomes_revealed'],
                                  'combined_pass_results_revealed': match.mid in session.get('pass_results_revealed', set()),
                                  'source_release_eligibility': 'pending; local review only'},
                   'answer_semantics': 'No = assessed negative with adequate relevant visibility; skip is excluded from binary negatives.'}
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open('a', encoding='utf-8', newline='\n') as handle:
                handle.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + '\n')
                handle.flush()
                os.fsync(handle.fileno())
            return row

    def combined(self, mid):
        sequences = {}
        for row in self.latest(mid):
            item = sequences.setdefault(row['sequence_id'], {'sequence_id': row['sequence_id'], 'case': row['case'], 'questions': {}})
            item['questions'].setdefault(row['question_key'], []).append({
                'reviewer': row['reviewer'], 'answer': row['answer'], 'skip_reason': row['skip_reason'], 'revision': row['revision']})
        for item in sequences.values():
            flags = []
            for question, labels in item['questions'].items():
                answers = {r['answer'] for r in labels if r['answer'] != 'skip'}
                if len(answers) > 1:
                    flags.append('Reviewer disagreement: ' + question)
            questions = item['questions']
            # Compare each reviewer's linked judgements; never overwrite a conflict.
            press = {r['reviewer']: r['answer'] for r in questions.get('press', [])}
            for funnel in questions.get('funnel', []):
                if funnel['answer'] == 'yes' and press.get(funnel['reviewer']) == 'no':
                    flags.append('Funnel yes / press no requires joint review: ' + funnel['reviewer'])
            item['flags'] = flags
            item['interpretation'] = 'Same-clip judgements only. Cue plus press does not establish temporal order, a trigger, intent or causality.'
        return {'sequences': sorted(sequences.values(), key=lambda x: (x['case']['period'], x['case']['start_frame'])),
                'review_records': self.latest(mid),
                'review_history': [r for r in self.records() if r['match_id'] == mid],
                'join_rule': 'Exact sequence ID, source and native interval only; no automatic overlap joins',
                'unreviewed_semantics': 'Missing pass = not assessed; skip is not no.'}

    def save_press_event(self, payload, match, bank, session):
        """One start/end marker plus manually clicked defenders; no funnel inference."""
        with self.lock:
            reviewer = str(payload.get('reviewer', '')).strip()
            if not reviewer or len(reviewer) > 100:
                raise ValueError('Enter your reviewer name once before marking events')
            prior = None
            if payload.get('event_id'):
                prior = next((r for r in self.latest(match.mid, 'press', reviewer)
                              if r.get('press_event') and self.event_id(r) == payload['event_id']), None)
                if prior is None:
                    raise ValueError('Saved press event is missing or deleted. Reload events before editing.')
                if payload.get('base_revision') != prior['revision']:
                    raise ValueError('Event changed in another tab. Reload saved events before editing.')
            start, end = payload.get('start_frame'), payload.get('end_frame')
            if type(start) is not int or type(end) is not int or start > end:
                raise ValueError('Pressure end must be at or after its start')
            first, last = match.raw(start), match.raw(end)
            if first['period'] not in (1, 2) or first['period'] != last['period']:
                raise ValueError('A pressure event must stay within one playing period; return to that half or cancel the marker')
            if prior and prior['press_event']['period'] != first['period']:
                raise ValueError('Keep an edited event in its original half; mark a new event in the other half')
            primary = payload.get('primary_presser_id')
            support = payload.get('supporting_defender_ids', [])
            if not isinstance(support, list) or len(support) > 10 or any(type(p) is not int for p in support) or len(set(support)) != len(support):
                raise ValueError('Supporting pressers must be distinct player IDs')
            if primary is None and support:
                raise ValueError('Choose the primary presser before supporting defenders')
            ids = ([primary] if primary is not None else []) + support
            if any(type(p) is not int or p not in match.players for p in ids) or primary in support:
                raise ValueError('Primary and supporting pressers must be distinct match players')
            team = match.players[primary]['team_id'] if primary is not None else None
            if any(match.players[p]['team_id'] != team for p in support):
                raise ValueError('Supporting pressers must be on the primary presser’s team')
            selections = payload.get('selection_frames', {})
            if not isinstance(selections, dict):
                raise ValueError('Invalid player selection evidence')
            checked = {}
            for pid in ids:
                frame = selections.get(str(pid))
                # Saved-event edits may nominate roles retrospectively from another
                # frame in the same half. Keep the actual click frame, never clamp it.
                if type(frame) is not int or (not start <= frame <= end and prior is None):
                    raise ValueError('Player clicks must refer to a frame inside the marked event')
                record = match.raw(frame)
                if record['period'] != first['period'] or not any(p['player_id'] == pid for p in record['player_data']):
                    raise ValueError('Selected player was not present at the recorded click frame')
                checked[str(pid)] = frame
            case = bank.add(match, start, end)
            duplicate = next((r for r in self.latest(match.mid, 'press', reviewer) if r['sequence_id'] == case['sequence_id'] and (prior is None or self.event_id(r) != self.event_id(prior))), None)
            if duplicate is not None:
                raise ValueError('Another saved event already uses this exact interval')
            expected = prior['revision'] if prior else 0
            if payload.get('base_revision', 0) != expected:
                raise ValueError('This exact event already has a decision. Existing records were preserved; use a different interval or review its history.')
            disclosure = replay_disclosure(payload, case, match, prior, session)
            row = {'schema_version': 'press-marker-1.0', 'review_protocol_version': '3.2',
                   'event_id': self.event_id(prior) if prior else str(uuid.uuid4()), 'deleted': False,
                   'record_action': 'edit' if prior else 'create',
                   'previous_sequence_id': prior['sequence_id'] if prior and prior['sequence_id'] != case['sequence_id'] else None,
                   'sequence_id': case['sequence_id'], 'case': case, 'match_id': match.mid,
                   'question_key': 'press', 'pass': 'press', 'cue_type': None,
                   'reviewer': reviewer, 'revision': expected + 1, 'answer': 'yes', 'skip_reason': None,
                   'note': '', 'saved_utc': datetime.now(timezone.utc).isoformat(), 'replay_review': disclosure,
                   'review_scope': copy.deepcopy(prior.get('review_scope', {'status': 'not_recorded_on_original_annotation'})) if prior else (
                       copy.deepcopy(match.review_scope) if payload.get('review_scope_version') == match.review_scope.get('version') else {'status': 'not_recorded'}),
                   'current_review_policy': copy.deepcopy(match.review_scope),
                   'press_event': {'start_frame': start, 'end_frame': end, 'period': first['period'],
                                   'defending_team_id': team, 'primary_presser_id': primary,
                                   'supporting_defender_ids': support, 'selection_frames': checked,
                                   'selection_frames_outside_revised_interval': {pid: f for pid, f in checked.items() if not start <= f <= end},
                                   'selection_frame_semantics': 'Actual review click frames; outside-interval selections are retrospective role nominations, not in-event observation evidence',
                                   'role_semantics': 'Human-nominated pressers; functional coverage and funnel status not assessed'},
                   'interval_quality': match.interval_quality(start, end),
                   'actor_visibility': match.actor_visibility(start, end, set(ids)),
                   'provenance': {'software_version': __version__, 'software': match.software,
                                  'input_sha256': match.hashes, 'manifest_sha256': match.manifest_hash,
                                  'partition': 'development', 'prior_exposure': 'legacy_all_match_exploration',
                                  'sampling_pool': 'manual_marked_intervals', 'outcome_filtered': False,
                                  'provider_context_revealed_in_session': match.mid in session['provider_revealed'],
                                  'outcomes_revealed_in_session': match.mid in session['outcomes_revealed'],
                                  'source_release_eligibility': 'pending; local review only'}}
            self._append(row)
            return row
