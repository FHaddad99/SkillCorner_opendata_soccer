"""Software tests for proposal grouping and separate funnel judgements."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from presslens.candidates import CandidateReviews, candidates, source_diagnostics
from presslens.focused import FocusedLog, SequenceBank
from presslens.replay import ReplayStore
from test_replay_review import fixture


class CandidateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        fixture(self.root, visible_support=True)
        self.match = ReplayStore(self.root).load('999')
        self.focused = FocusedLog(self.root / 'press.jsonl')
        self.log = CandidateReviews(self.root / 'candidate.jsonl')
        self.session = {'provider_revealed': set(), 'outcomes_revealed': set()}
        self.match.events += [self.event('a', 14, 16, 2), self.event('b', 15, 17, 3), self.event('c', 18, 20, 2, 'counter_press')]

    def tearDown(self):
        self.temp.cleanup()

    def event(self, eid, start, end, pid, subtype='pressure'):
        return {'event_id': eid, 'event_type': 'on_ball_engagement', 'event_subtype': subtype,
                'period': '1', 'frame_start': str(start), 'frame_end': str(end), 'player_id': str(pid),
                'player_in_possession_id': '1'}

    def save(self, **extra):
        c = candidates(self.match, 'pressure', self.focused)[0]
        return self.log.save({'match_id': '999', 'reviewer': 'Test reviewer', 'pool': 'pressure',
                             'candidate_id': c['candidate_id'], 'start_frame': c['start_frame'],
                             'end_frame': c['end_frame'], 'decision': 'yes', **extra}, self.match, self.focused, self.session)

    def test_overlapping_defenders_group_without_labelling_a_positive(self):
        rows = candidates(self.match, 'pressure', self.focused)
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]['start_frame'], rows[0]['end_frame']), (14, 17))
        self.assertEqual({e['player_id'] for e in rows[0]['engagements']}, {2, 3})
        self.assertNotIn('answer', rows[0])
        self.assertEqual(len(candidates(self.match, 'expanded', self.focused)), 2)
        self.assertEqual(self.log.records(), [])

    def test_grouping_stops_at_stoppages_team_changes_and_tracking_gaps(self):
        self.match.events[-2]['game_interruption_before'] = 'throw_in'
        self.assertEqual(len(candidates(self.match, 'pressure', self.focused)), 2)
        self.match.events[-2].pop('game_interruption_before')
        self.match.possessions.append({**self.match.possessions[0], 'frame_start': '15', 'team_id': '20'})
        self.assertEqual(len(candidates(self.match, 'pressure', self.focused)), 2)
        self.match.possessions.pop()
        self.match.events[-3]['frame_start'] = '12'
        self.assertEqual(len(candidates(self.match, 'pressure', self.focused)), 2)
        self.assertIn('Tracking gaps inside proposal', candidates(self.match, 'pressure', self.focused)[0]['flags'])

    def test_candidates_ignore_later_outcomes_and_overall_pressure(self):
        before = candidates(self.match, 'pressure', self.focused)
        for e in self.match.events:
            e.update(overall_pressure_end='very_high_pressure', force_backward='True', lead_to_goal='True')
        self.assertEqual(before, candidates(self.match, 'pressure', self.focused))

    def test_identity_is_shared_between_pools_but_changes_with_grouping_policy(self):
        primary = candidates(self.match, 'pressure', self.focused)[0]
        expanded = candidates(self.match, 'expanded', self.focused)[0]
        self.assertEqual(primary['candidate_id'], expanded['candidate_id'])
        self.match.candidate_policy = {**self.match.candidate_policy, 'version': 'new-policy'}
        self.assertNotEqual(primary['candidate_id'], candidates(self.match, 'pressure', self.focused)[0]['candidate_id'])

    def test_reviewers_remain_independent(self):
        self.save()
        self.save(reviewer='Other reviewer', decision='no')
        self.assertEqual(len(self.log.latest()), 2)
        self.assertEqual(self.log.latest('999', 'Test reviewer')[0]['funnel'], 'yes')
        self.assertEqual(self.log.latest('999', 'Other reviewer')[0]['funnel'], 'no')

    def test_decisions_are_separate_append_only_revisions_with_real_interval_ids(self):
        first = self.save()
        second = self.save(base_revision=1, start_frame=15, decision='uncertain')
        self.assertEqual(first['candidate_id'], second['candidate_id'])
        self.assertNotEqual(first['case']['sequence_id'], second['case']['sequence_id'])
        self.assertEqual(second['original_case']['start_frame'], 14)
        self.assertEqual(self.log.latest()[0]['funnel'], 'uncertain')
        self.assertEqual(len(self.log.records()), 2)
        self.assertEqual(self.focused.records(), [])
        with self.assertRaisesRegex(ValueError, 'another tab'):
            self.save(base_revision=1)

    def test_unknown_and_deferred_states_do_not_become_funnel_negatives(self):
        for revision, decision in enumerate(('unassessable', 'not_pressure', 'out_of_scope', 'unreviewed')):
            row = self.save(base_revision=revision, decision=decision, scope_reason='repress')
            self.assertEqual(row['funnel'], 'unassessable' if decision == 'unassessable' else 'not_assessed')
        self.assertEqual(row['decision'], 'unreviewed')
        with self.assertRaisesRegex(ValueError, 'excluded situation'):
            self.save(base_revision=4, decision='out_of_scope', scope_reason='anything')

    def test_cross_half_and_removed_candidate_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'original half'):
            self.save(end_frame=32)
        with self.assertRaisesRegex(ValueError, 'changed or was removed'):
            self.save(candidate_id='invented')
        self.assertEqual(self.log.records(), [])

    def test_unresolved_defenders_are_explicit_omissions(self):
        self.match.events.append(self.event('unresolved', 14, 16, 9999))
        rows = candidates(self.match, 'pressure', self.focused)
        report = source_diagnostics(self.match, False, rows)
        self.assertEqual(report['invalid_or_unavailable_bound_engagements'], 1)
        self.assertEqual(report['omitted_engagements'][0]['event_id'], 'unresolved')
        self.assertEqual(report['omitted_engagements'][0]['reason'], 'Defender ID absent from match roster')

    def test_manual_examples_keep_identity_and_scope_without_copying_funnel_labels(self):
        saved = self.focused.save_press_event({'reviewer': 'Test reviewer', 'start_frame': 14, 'end_frame': 16},
                                              self.match, SequenceBank(self.root / 'bank.jsonl'), self.session)
        rows = candidates(self.match, 'manual', self.focused)
        self.assertEqual(rows[0]['source_id'], saved['event_id'])
        self.assertNotIn('funnel', rows[0])

    def test_audit_windows_do_not_overlap_primary_candidates(self):
        rows = candidates(self.match, 'audit', self.focused)
        primary = candidates(self.match, 'pressure', self.focused)
        self.assertTrue(rows)
        self.assertTrue(all(not (a['period'] == p['period'] and a['start_frame'] <= p['end_frame'] and a['end_frame'] >= p['start_frame']) for a in rows for p in primary))


if __name__ == '__main__':
    unittest.main()
