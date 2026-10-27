"""Synthetic tests for independent focused judgements and exact sequence joins."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from presslens.focused import FocusedLog, SequenceBank, build_queue, clip_id
from presslens.replay import ReplayStore
from presslens.review import ReviewLog
from test_replay_review import fixture


class FocusedTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        fixture(self.root)
        self.match = ReplayStore(self.root).load('999')
        self.detailed = ReviewLog(self.root / 'annotations.jsonl')
        self.log = FocusedLog(self.root / 'pass_reviews.jsonl')
        self.session = {'provider_revealed': set(), 'outcomes_revealed': set(), 'history_revealed': set()}
        self.case = build_queue(self.match, self.detailed, 'possession_windows')[0]

    def tearDown(self):
        self.temp.cleanup()

    def save(self, review_pass, answer, reviewer='Synthetic reviewer', **extra):
        payload = {'pass': review_pass, 'answer': answer, 'reviewer': reviewer,
                   'pool': 'possession_windows', 'sequence_id': self.case['sequence_id'], **extra}
        return self.log.save(payload, self.match, self.detailed, self.session)

    def test_queue_identity_is_shared_across_passes_but_bound_to_release(self):
        self.assertEqual(self.case, build_queue(self.match, self.detailed, 'possession_windows')[0])
        changed = {**self.case, 'end_frame': self.case['end_frame'] - 1}
        self.assertNotEqual(clip_id(changed), self.case['sequence_id'])
        self.assertNotEqual(clip_id({**self.case, 'input_revision': 'changed'}), self.case['sequence_id'])
        self.assertNotIn('SECRET_OUTCOME', json.dumps(self.case))

    def test_passes_save_independently_and_combine_without_inventing_labels(self):
        self.save('funnel', 'yes')
        combined = self.log.combined('999')['sequences'][0]
        self.assertNotIn('press', combined['questions'])
        self.save('press', 'no')
        self.save('cue', 'yes', cue_type='backward_pass')
        combined = self.log.combined('999')['sequences'][0]
        self.assertTrue(any('Funnel yes / press no' in f for f in combined['flags']))
        self.assertIn('does not establish temporal order', combined['interpretation'])
        self.assertEqual(len(self.log.records()), 3)

    def test_skip_is_retained_without_turning_into_no(self):
        row = self.save('funnel', 'skip', skip_reason='visibility')
        self.assertEqual(row['answer'], 'skip')
        self.assertEqual(row['skip_reason'], 'visibility')
        self.assertEqual(self.log.combined('999')['sequences'][0]['questions']['funnel'][0]['answer'], 'skip')

    def test_reviewers_and_cue_types_remain_distinct(self):
        self.save('press', 'yes', reviewer='A')
        self.save('press', 'no', reviewer='B')
        self.save('cue', 'yes', cue_type='backward_pass')
        self.save('cue', 'no', cue_type='wide_reception')
        combined = self.log.combined('999')['sequences'][0]
        self.assertTrue(any('Reviewer disagreement: press' == flag for flag in combined['flags']))
        self.assertEqual(len(combined['questions']['press']), 2)
        self.assertIn('cue:wide_reception', combined['questions'])

    def test_revisions_are_append_only_and_stale_writes_rejected(self):
        self.save('press', 'yes')
        with self.assertRaisesRegex(ValueError, 'another tab'):
            self.save('press', 'no')
        self.save('press', 'no', base_revision=1)
        self.assertEqual(len(self.log.records()), 2)
        self.assertEqual(self.log.latest()[0]['answer'], 'no')
        self.assertFalse(self.detailed.path.exists())

    def test_saved_interval_pool_does_not_import_old_tactical_labels(self):
        self.detailed.save({'stage': 'observation', 'reviewer': 'Synthetic reviewer',
                            'observation': {'start_frame': 14, 'end_frame': 16, 'press_assessment': 'present',
                                            'funnel_assessment': 'not_assessed', 'rationale': 'Synthetic fixture'}}, self.match, self.session)
        cases = build_queue(self.match, self.detailed, 'saved_intervals')
        self.assertEqual(len(cases), 1)
        self.assertNotIn('press_assessment', json.dumps(cases))
        self.assertEqual(self.log.latest(), [])

    def test_manual_intervals_are_shared_without_changing_or_importing_labels(self):
        bank = SequenceBank(self.root / 'review_sequences.jsonl')
        case = bank.add(self.match, 14, 16)
        self.assertEqual(case, bank.add(self.match, 14, 16))
        self.assertEqual(len(bank.cases(self.match)), 1)
        self.assertEqual(build_queue(self.match, self.detailed, 'marked_intervals', bank)[0]['sequence_id'], case['sequence_id'])
        for p in ('funnel', 'press'):
            self.log.save({'pass': p, 'answer': 'yes', 'reviewer': 'Synthetic reviewer',
                           'sequence_id': case['sequence_id'], 'pool': 'marked_intervals'},
                          self.match, self.detailed, self.session, bank)
        self.assertEqual(len(self.log.combined('999')['sequences']), 1)
        with self.assertRaisesRegex(ValueError, 'one playing period'):
            bank.add(self.match, 14, 32)

    def test_press_marker_saves_native_bounds_roles_and_future_join_id(self):
        bank = SequenceBank(self.root / 'review_sequences.jsonl')
        row = self.log.save_press_event({'reviewer': 'Synthetic reviewer', 'start_frame': 14, 'end_frame': 16,
                                        'primary_presser_id': 2, 'supporting_defender_ids': [],
                                        'selection_frames': {'2': 14}}, self.match, bank, self.session)
        self.assertEqual(row['press_event']['start_frame'], 14)
        self.assertEqual(row['press_event']['end_frame'], 16)
        self.assertEqual(row['press_event']['primary_presser_id'], 2)
        self.assertEqual(row['press_event']['defending_team_id'], 20)
        self.assertEqual(row['answer'], 'yes')
        self.assertNotIn('funnel', self.log.combined('999')['sequences'][0]['questions'])
        self.assertEqual(row['actor_visibility']['actors']['2']['extrapolated'], 3)
        self.assertEqual(bank.cases(self.match)[0]['sequence_id'], row['sequence_id'])
        self.assertFalse(self.detailed.path.exists())

    def test_press_marker_rejects_opponents_unseen_clicks_and_cross_half(self):
        bank = SequenceBank(self.root / 'review_sequences.jsonl')
        payload = {'reviewer': 'Synthetic reviewer', 'start_frame': 14, 'end_frame': 16,
                   'primary_presser_id': 2, 'supporting_defender_ids': [1], 'selection_frames': {'2': 14, '1': 14}}
        with self.assertRaisesRegex(ValueError, 'primary presser’s team'):
            self.log.save_press_event(payload, self.match, bank, self.session)
        payload['supporting_defender_ids'] = [3]
        payload['selection_frames'] = {'2': 14, '3': 14}
        with self.assertRaisesRegex(ValueError, 'not present'):
            self.log.save_press_event(payload, self.match, bank, self.session)
        payload.update(supporting_defender_ids=[], selection_frames={'2': 14}, end_frame=32)
        with self.assertRaisesRegex(ValueError, 'one playing period'):
            self.log.save_press_event(payload, self.match, bank, self.session)
        self.assertEqual(self.log.records(), [])

    def test_press_marker_can_explicitly_leave_primary_unknown(self):
        row = self.log.save_press_event({'reviewer': 'Synthetic reviewer', 'start_frame': 14, 'end_frame': 16},
                                       self.match, SequenceBank(self.root / 'review_sequences.jsonl'), self.session)
        self.assertIsNone(row['press_event']['primary_presser_id'])
        self.assertEqual(row['press_event']['supporting_defender_ids'], [])

    def test_press_event_bounds_edit_replaces_active_entry_and_keeps_identity(self):
        bank = SequenceBank(self.root / 'review_sequences.jsonl')
        payload = {'reviewer': 'Synthetic reviewer', 'start_frame': 14, 'end_frame': 16,
                   'primary_presser_id': 2, 'selection_frames': {'2': 14}}
        first = self.log.save_press_event(payload, self.match, bank, self.session)
        edited = self.log.save_press_event({**payload, 'start_frame': 15, 'end_frame': 17,
                                           'event_id': first['event_id'], 'base_revision': 1}, self.match, bank, self.session)
        self.assertEqual(first['event_id'], edited['event_id'])
        self.assertNotEqual(first['sequence_id'], edited['sequence_id'])
        self.assertEqual(edited['previous_sequence_id'], first['sequence_id'])
        self.assertEqual(edited['press_event']['selection_frames_outside_revised_interval'], {'2': 14})
        self.assertEqual(len(self.log.latest()), 1)
        self.assertEqual(len(self.log.records()), 2)
        with self.assertRaisesRegex(ValueError, 'another tab'):
            self.log.save_press_event({**payload, 'event_id': first['event_id'], 'base_revision': 1}, self.match, bank, self.session)

    def test_edit_can_add_support_from_outside_interval_without_changing_bounds(self):
        root = self.root / 'support-fixture'
        fixture(root, visible_support=True)
        match = ReplayStore(root).load('999')
        bank = SequenceBank(root / 'review_sequences.jsonl')
        payload = {'reviewer': 'Synthetic reviewer', 'start_frame': 14, 'end_frame': 16,
                   'primary_presser_id': 2, 'selection_frames': {'2': 14}}
        first = self.log.save_press_event(payload, match, bank, self.session)
        edit = {**payload, 'event_id': first['event_id'], 'base_revision': 1,
                'supporting_defender_ids': [3], 'selection_frames': {'2': 14, '3': 18}}
        revised = self.log.save_press_event(edit, match, bank, self.session)
        self.assertEqual(revised['press_event']['supporting_defender_ids'], [3])
        self.assertEqual(revised['press_event']['selection_frames_outside_revised_interval'], {'3': 18})
        self.assertEqual(revised['sequence_id'], first['sequence_id'])
        self.assertEqual(revised['event_id'], first['event_id'])
        self.assertEqual(self.log.records()[0], first)
        with self.assertRaisesRegex(ValueError, 'not present'):
            self.log.save_press_event({**edit, 'base_revision': 2, 'selection_frames': {'2': 14, '3': 32}}, match, bank, self.session)
        with self.assertRaisesRegex(ValueError, 'inside the marked event'):
            self.log.save_press_event({**payload, 'supporting_defender_ids': [3],
                                      'selection_frames': {'2': 14, '3': 18}}, match, bank, self.session)

    def test_delete_and_restore_are_revisions_not_negative_labels(self):
        bank = SequenceBank(self.root / 'review_sequences.jsonl')
        first = self.log.save_press_event({'reviewer': 'Synthetic reviewer', 'start_frame': 14, 'end_frame': 16}, self.match, bank, self.session)
        request = {'reviewer': first['reviewer'], 'event_id': first['event_id'], 'base_revision': 1, 'deleted': True}
        deleted = self.log.set_deleted(request, self.match)
        self.assertEqual(self.log.latest(), [])
        self.assertEqual(self.log.combined('999')['sequences'], [])
        self.assertEqual(deleted['answer'], 'yes')
        self.assertEqual(len(self.log.records()), 2)
        restored = self.log.set_deleted({**request, 'base_revision': 2, 'deleted': False}, self.match)
        self.assertFalse(restored['deleted'])
        self.assertEqual(restored['revision'], 3)
        self.assertEqual(len(self.log.latest()), 1)

    def test_legacy_press_event_can_be_edited_and_deleted_without_rewriting(self):
        bank = SequenceBank(self.root / 'review_sequences.jsonl')
        row = self.log.save_press_event({'reviewer': 'Synthetic reviewer', 'start_frame': 14, 'end_frame': 16}, self.match, bank, self.session)
        row.pop('event_id')
        self.log.path.write_text(json.dumps(row) + '\n')
        identity = self.log.event_id(row)
        updated = self.log.save_press_event({'reviewer': row['reviewer'], 'event_id': identity, 'base_revision': 1,
                                             'start_frame': 14, 'end_frame': 17}, self.match, bank, self.session)
        self.assertEqual(updated['event_id'], identity)
        self.assertNotIn('event_id', self.log.records()[0])
        self.log.set_deleted({'reviewer': row['reviewer'], 'event_id': identity, 'base_revision': 2, 'deleted': True}, self.match)
        self.assertEqual(self.log.latest(), [])

    def test_edit_does_not_overwrite_another_existing_interval(self):
        bank = SequenceBank(self.root / 'review_sequences.jsonl')
        first = self.log.save_press_event({'reviewer': 'Synthetic reviewer', 'start_frame': 14, 'end_frame': 16}, self.match, bank, self.session)
        self.log.save_press_event({'reviewer': 'Synthetic reviewer', 'start_frame': 17, 'end_frame': 19}, self.match, bank, self.session)
        with self.assertRaisesRegex(ValueError, 'Another saved event'):
            self.log.save_press_event({'reviewer': first['reviewer'], 'event_id': first['event_id'], 'base_revision': 1,
                                       'start_frame': 17, 'end_frame': 19}, self.match, bank, self.session)
        self.assertEqual(len(self.log.latest()), 2)

    def test_new_marker_carries_declared_exclusions_without_relabelling_old_records(self):
        self.match.review_scope = {'version': 'test-scope-1', 'excluded_situations': ['counter_attack', 'fast_break', 'repress'],
                                   'excluded_handling': 'deferred_unreviewed', 'automatic_phase_filter': False}
        bank = SequenceBank(self.root / 'review_sequences.jsonl')
        payload = {'reviewer': 'Synthetic reviewer', 'start_frame': 14, 'end_frame': 16,
                   'review_scope_version': 'test-scope-1'}
        first = self.log.save_press_event(payload, self.match, bank, self.session)
        self.assertEqual(first['review_scope'], self.match.review_scope)
        self.assertEqual(first['answer'], 'yes')
        first.pop('review_scope')
        self.log.path.write_text(json.dumps(first) + '\n')
        edited = self.log.save_press_event({**payload, 'event_id': first['event_id'], 'base_revision': 1}, self.match, bank, self.session)
        self.assertEqual(edited['review_scope']['status'], 'not_recorded_on_original_annotation')
        self.assertNotIn('review_scope', self.log.records()[0])
        self.assertEqual(edited['current_review_policy'], self.match.review_scope)

    def test_scope_does_not_change_existing_marker_during_edit_or_delete(self):
        self.match.review_scope = {'version': 'scope-1', 'excluded_situations': ['counter_attack', 'fast_break', 'repress'],
                                   'excluded_handling': 'deferred_unreviewed'}
        bank = SequenceBank(self.root / 'review_sequences.jsonl')
        first = self.log.save_press_event({'reviewer': 'Synthetic reviewer', 'start_frame': 14, 'end_frame': 16,
                                           'review_scope_version': 'scope-1'}, self.match, bank, self.session)
        original_scope = dict(first['review_scope'])
        self.match.review_scope = {'version': 'later-policy', 'excluded_situations': []}
        updated = self.log.save_press_event({'reviewer': first['reviewer'], 'event_id': first['event_id'],
                                             'base_revision': 1, 'start_frame': 14, 'end_frame': 17,
                                             'review_scope_version': 'later-policy'}, self.match, bank, self.session)
        self.assertEqual(updated['review_scope'], original_scope)
        deleted = self.log.set_deleted({'reviewer': first['reviewer'], 'event_id': first['event_id'], 'base_revision': 2, 'deleted': True}, self.match)
        self.assertEqual(deleted['review_scope'], original_scope)


if __name__ == '__main__':
    unittest.main()
