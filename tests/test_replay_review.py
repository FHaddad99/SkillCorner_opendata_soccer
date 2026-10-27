"""Synthetic replay/review fixtures. These are software tests, not match evidence."""
import csv
import hashlib
import importlib.util
import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from presslens.replay import ReplayStore
from presslens.review import ReviewLog

SPEC = importlib.util.spec_from_file_location('presslens_server', ROOT / 'scripts/run_presslens.py')
server_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(server_module)


def fixture(root, visible_support=False):
    directory = root / 'data/matches/999'
    directory.mkdir(parents=True)
    (root / 'reports').mkdir()
    (root / 'config').mkdir()
    (root / 'config/presslens_review.json').write_text(json.dumps({'review_match_ids': ['999'], 'partition': 'development', 'untouched_evaluation_set': []}))
    meta = {'home_team': {'id': 10, 'short_name': 'Home'}, 'away_team': {'id': 20, 'short_name': 'Away'},
            'date_time': '2000-01-01T00:00:00Z', 'pitch_length': 105, 'pitch_width': 68,
            'home_team_side': ['left_to_right', 'right_to_left'], 'home_team_score': 99,
            'players': [{'id': p, 'team_id': team, 'short_name': f'Player {p}', 'number': p} for p, team in [(1, 10), (2, 20), (3, 20)]]}
    (directory / '999_match.json').write_text(json.dumps(meta))
    (root / 'data/matches.json').write_text(json.dumps([{'id': 999}]))
    rows = []
    for f in list(range(10, 21)) + list(range(30, 36)):
        if f == 13:
            continue
        rows.append({'frame': f, 'period': 1 if f < 30 else 2, 'timestamp': f'00:00:{f/10:05.2f}',
                     'ball_data': {'x': 0, 'y': 0, 'is_detected': True},
                     'possession': {'player_id': 2 if f == 14 else None, 'group': 'home team'},
                     'player_data': [{'player_id': 1, 'x': 0, 'y': 0, 'is_detected': True},
                                     {'player_id': 2, 'x': 2, 'y': 0, 'is_detected': False}]})
    if visible_support:
        for row in rows:
            row['player_data'].append({'player_id': 3, 'x': 4, 'y': 0, 'is_detected': True})
    (directory / '999_tracking_extrapolated.jsonl').write_text('\n'.join(json.dumps(r) for r in rows) + '\n')
    events = [{'event_id': '8_1', 'event_type': 'player_possession', 'period': 1, 'frame_start': 14, 'frame_end': 16,
               'player_id': 1, 'team_id': 10, 'start_type': 'pass_reception', 'end_type': 'shot', 'pass_outcome': 'SECRET_OUTCOME'}]
    phases = [{'index': 0, 'period': 1, 'frame_start': 10, 'frame_end': 15, 'team_in_possession_id': 10,
               'team_in_possession_phase_type': 'create', 'team_out_of_possession_phase_type': 'medium_block'},
              {'index': 1, 'period': 1, 'frame_start': 15, 'frame_end': 21, 'team_in_possession_id': 20,
               'team_in_possession_phase_type': 'transition', 'team_out_of_possession_phase_type': 'transition'}]
    for suffix, data in [('dynamic_events.csv', events), ('phases_of_play.csv', phases)]:
        with (directory / f'999_{suffix}').open('w', newline='') as h:
            writer = csv.DictWriter(h, fieldnames=list(data[0]))
            writer.writeheader()
            writer.writerows(data)
    inputs = [p for p in (root / 'data').rglob('*') if p.is_file()]
    manifest = {'files': [{'path': p.relative_to(root).as_posix(), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in inputs]}
    (root / 'reports/eligibility_manifest.json').write_text(json.dumps(manifest))


class ReplayTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        fixture(self.root)
        self.store = ReplayStore(self.root)
        self.match = self.store.load('999')
        self.log = ReviewLog(self.root / 'review.jsonl')
        self.session = {'outcomes_revealed': set(), 'provider_revealed': set(), 'history_revealed': set()}

    def tearDown(self):
        self.temporary.cleanup()

    def payload(self):
        return {'match_id': '999', 'stage': 'observation', 'reviewer': 'SYNTHETIC TEST',
                'observation': {'start_frame': 14, 'end_frame': 16, 'press_assessment': 'uncertain', 'funnel_assessment': 'not_assessed',
                                'rationale': 'Synthetic software fixture', 'defending_team_id': 20,
                                'primary_presser_id': 2, 'supporting_roles': [{'player_id': 3}], 'evidence_frames': [14]}}

    def test_native_frames_and_conflicts_are_preserved_without_outcomes(self):
        window = self.match.window(12, 4)['frames']
        self.assertTrue(window[1]['missing'])
        self.assertIsNone(window[0]['possession']['player_id'])
        self.assertFalse(window[0]['players'][1][3])
        self.assertIn('Tracking/event carrier disagreement', self.match.context(self.match.raw(14))['flags'])
        context = self.match.context(self.match.raw(15))
        self.assertEqual(context['phase'][0]['team_id'], 20)
        self.assertIn('Event/phase team disagreement', context['flags'])
        observation_response = json.dumps([self.match.info(), context, window])
        self.assertNotIn('SECRET_OUTCOME', observation_response)
        self.assertNotIn('end_type', observation_response)
        self.assertNotIn('home_team_score', observation_response)

    def test_source_tampering_and_unknown_matches_fail_closed(self):
        with self.assertRaises(ValueError):
            self.store.load('../999')
        p = self.root / 'data/matches/999/999_match.json'
        p.write_text(p.read_text() + ' ')
        with self.assertRaisesRegex(ValueError, 'hash differs'):
            ReplayStore(self.root).load('999')
        with self.assertRaisesRegex(ValueError, 'changed during review'):
            self.match.raw(14)

    def test_revision_history_and_outcome_exposure(self):
        first = self.log.save(self.payload(), self.match, self.session)
        self.assertIsNone(first['outcome'])
        self.assertFalse(first['provenance']['outcomes_revealed_in_session'])
        next_payload = {'stage': 'outcome', 'reviewer': 'SYNTHETIC TEST', 'annotation_id': first['annotation_id'],
                        'base_revision': 1, 'outcome': {'label': 'unknown'}}
        with self.assertRaisesRegex(ValueError, 'Reveal outcomes'):
            self.log.save(next_payload, self.match, self.session)
        self.session['outcomes_revealed'].add('999')
        second = self.log.save(next_payload, self.match, self.session)
        self.assertEqual(second['revision'], 2)
        with self.assertRaisesRegex(ValueError, 'another tab'):
            self.log.save(next_payload, self.match, self.session)
        self.assertEqual(len(self.log.records()), 2)
        self.assertEqual(self.log.latest()[0]['revision'], 2)
        observation = self.payload()
        observation.update(annotation_id=first['annotation_id'], base_revision=2)
        self.session['outcomes_revealed'].clear()
        third = self.log.save(observation, self.match, self.session)
        self.assertTrue(third['provenance']['outcomes_exposed_in_previous_revision'])

    def test_cross_period_annotations_and_wrong_team_roles_rejected(self):
        payload = self.payload()
        payload['observation']['end_frame'] = 32
        with self.assertRaisesRegex(ValueError, 'one labelled playing period'):
            self.log.save(payload, self.match, self.session)
        payload = self.payload()
        payload['observation']['primary_presser_id'] = 1
        with self.assertRaisesRegex(ValueError, 'defending team'):
            self.log.save(payload, self.match, self.session)

    def test_complete_interval_quality_counts_missing_frames(self):
        counts = self.match.interval_quality(12, 16)
        self.assertEqual(counts['expected_frame_slots'], 5)
        self.assertEqual(counts['missing_source_frame_slots'], 1)
        self.assertEqual(counts['tracking_carrier_unknown_frames'], 3)

    def test_separate_assessments_and_negative_visibility_requirement(self):
        payload = self.payload()
        o = payload['observation']
        o.update(press_assessment='present', funnel_assessment='no_funnel', funnel_rationale='No directional support pattern in synthetic fixture.')
        with self.assertRaisesRegex(ValueError, 'adequate route visibility'):
            self.log.save(payload, self.match, self.session)
        o['funnel_observability'] = 'adequate'
        saved = self.log.save(payload, self.match, self.session)
        self.assertEqual(saved['schema_version'], '2.0')
        self.assertEqual(saved['observation']['funnel_assessment'], 'no_funnel')
        o['press_assessment'] = 'absent'
        with self.assertRaisesRegex(ValueError, 'requires a present'):
            self.log.save(payload, self.match, self.session)
        o.update(press_assessment='present', funnel_assessment='unassessable', funnel_observability='unassessable')
        self.assertEqual(self.log.save(payload, self.match, self.session)['observation']['funnel_assessment'], 'unassessable')

    def test_stages_allow_prior_context_and_flag_late_cues(self):
        payload = self.payload()
        o = payload['observation']
        o.update(context_start_frame=10, evidence_frames=[10, 14, 16],
                 stages={'cue_frame': 10, 'press_onset_frame': 14, 'reception_frame': 14, 'action_end_frame': 16})
        saved = self.log.save(payload, self.match, self.session)
        self.assertEqual(saved['observation']['stages']['cue_frame'], 10)
        o['stages']['cue_frame'] = 15
        saved = self.log.save(payload, self.match, self.session)
        self.assertTrue(any('follows nominated press onset' in flag for flag in saved['observation']['review_flags']))
        o['stages']['cue_frame'] = 30
        with self.assertRaisesRegex(ValueError, 'annotated period'):
            self.log.save(payload, self.match, self.session)

    def test_role_targets_visibility_and_attack_relative_directions(self):
        payload = self.payload()
        o = payload['observation']
        o.update(nominated_carrier_id=1, blocked_direction='left', press_uncertainty='low', funnel_uncertainty='high',
                 supporting_roles=[{'player_id': 3, 'function': 'cover_receiver', 'target_player_id': 1, 'uncertainty': 'high'}])
        saved = self.log.save(payload, self.match, self.session)
        self.assertEqual(saved['observation']['direction_reference']['attacking_left_native_y_sign'], 1)
        self.assertEqual(saved['actor_visibility']['actors']['2']['extrapolated'], 3)
        self.assertEqual(saved['actor_visibility']['actors']['3']['absent'], 3)
        self.assertEqual(saved['observation']['press_uncertainty'], 'low')
        self.assertEqual(saved['observation']['funnel_uncertainty'], 'high')
        o.update(start_frame=30, end_frame=32, evidence_frames=[30])
        saved = self.log.save(payload, self.match, self.session)
        self.assertEqual(saved['observation']['direction_reference']['attacking_left_native_y_sign'], -1)
        o['supporting_roles'][0]['target_player_id'] = 2
        with self.assertRaisesRegex(ValueError, 'opposing attacking team'):
            self.log.save(payload, self.match, self.session)

    def test_raw_replay_exposure_survives_revision_and_quality_pass(self):
        payload = self.payload()
        payload['replay_review'] = {'future_replay_viewed': 'no', 'viewer_session_max_frame': 20}
        first = self.log.save(payload, self.match, self.session)
        self.assertTrue(first['replay_review']['future_replay_exposed'])
        self.assertFalse(first['provenance']['outcomes_revealed_in_session'])
        quality = {'stage': 'quality', 'reviewer': 'SYNTHETIC TEST', 'annotation_id': first['annotation_id'],
                   'base_revision': 1, 'data_quality_notes': 'Synthetic later-frame uncertainty; no correction inferred.',
                   'replay_review': {'future_replay_viewed': 'unknown', 'reviewed_through_frame': 20}}
        second = self.log.save(quality, self.match, self.session)
        self.assertEqual(second['observation'], first['observation'])
        self.assertIsNone(second['outcome'])
        self.assertEqual(second['review_pass'], 'quality')
        self.session['replay_max_seen'].clear()
        payload.update(annotation_id=first['annotation_id'], base_revision=2)
        payload['replay_review'] = {'future_replay_viewed': 'no', 'viewer_session_max_frame': 14}
        third = self.log.save(payload, self.match, self.session)
        self.assertTrue(third['replay_review']['future_replay_exposed'])

    def test_legacy_record_is_not_relabelled_or_reinterpreted_on_read(self):
        legacy = {'annotation_id': 'legacy-id', 'revision': 1, 'schema_version': '1.0', 'match_id': '999',
                  'reviewer': 'SYNTHETIC TEST', 'outcome': None,
                  'observation': {'start_frame': 14, 'end_frame': 16, 'period': 1, 'label': 'non_funnel_pressure',
                                  'uncertainty': 'low', 'blocked_direction': 'left', 'notes': 'Legacy future hypothesis'},
                  'provenance': {'outcomes_revealed_in_session': False}}
        self.log.path.write_text(json.dumps(legacy) + '\n')
        self.assertEqual(self.log.latest()[0], legacy)
        payload = self.payload()
        payload.update(annotation_id='legacy-id', base_revision=1)
        second = self.log.save(payload, self.match, self.session)
        self.assertEqual(self.log.records()[0], legacy)
        self.assertEqual(second['schema_version'], '2.0')
        self.assertNotIn('label', second['observation'])
        self.assertEqual(second['observation']['funnel_assessment'], 'not_assessed')
        self.assertEqual(second['observation']['blocked_direction'], 'unknown')
        self.assertEqual(second['provenance']['legacy_source_revision'], 1)
        self.assertIsNone(second['replay_review']['future_replay_exposed'])

    def test_http_local_flow_and_origin_checks(self):
        server = server_module.make_server(self.root, port=0, log_path=self.root / 'http-reviews.jsonl')
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f'http://127.0.0.1:{server.server_port}'
        def request(path, payload=None, headers=None):
            raw = None if payload is None else json.dumps(payload).encode()
            req = urllib.request.Request(base + path, data=raw, headers=headers or {})
            with urllib.request.urlopen(req) as response:
                return json.load(response)
        try:
            token = request('/api/session')['session']
            headers = {'X-Review-Session': token, 'Origin': base}
            context = request('/api/matches/999/context?frame=15', headers=headers)
            self.assertIn('Event/phase team disagreement', context['flags'])
            saved = request('/api/annotations', self.payload(), headers)
            self.assertTrue(saved['provenance']['provider_context_revealed_in_session'])
            revealed = request('/api/reveal-outcomes', {'match_id': '999', 'start_frame': 14, 'end_frame': 16}, headers)
            self.assertEqual(revealed['outcomes'][0]['pass_outcome'], 'SECRET_OUTCOME')
            with self.assertRaises(urllib.error.HTTPError) as error:
                request('/api/annotations', self.payload(), {'X-Review-Session': token, 'Origin': 'http://untrusted.invalid'})
            self.assertEqual(error.exception.code, 403)
            error.exception.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_quality_followup_preserves_legacy_observation_schema(self):
        legacy = {'annotation_id': 'legacy-quality', 'revision': 1, 'schema_version': '1.0', 'match_id': '999',
                  'reviewer': 'SYNTHETIC TEST', 'outcome': None,
                  'observation': {'start_frame': 14, 'end_frame': 16, 'period': 1,
                                  'label': 'non_funnel_pressure', 'uncertainty': 'low', 'notes': 'Original text'},
                  'provenance': {'outcomes_revealed_in_session': False}}
        self.log.path.write_text(json.dumps(legacy) + '\n')
        second = self.log.save({'stage': 'quality', 'reviewer': 'SYNTHETIC TEST',
                                'annotation_id': 'legacy-quality', 'base_revision': 1,
                                'data_quality_notes': 'Separate synthetic follow-up',
                                'replay_review': {'future_replay_viewed': 'yes', 'reviewed_through_frame': 20}},
                               self.match, self.session)
        self.assertEqual(second['schema_version'], '1.0')
        self.assertEqual(second['review_protocol_version'], '2.0')
        self.assertEqual(second['observation'], legacy['observation'])
        self.assertTrue(second['replay_review']['future_replay_exposed'])
        self.assertEqual(self.log.records()[0], legacy)


if __name__ == '__main__':
    unittest.main()
