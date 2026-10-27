"""Synthetic software tests only; these fixtures are not football evidence."""
import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location('audit', Path(__file__).parents[1] / 'scripts/audit_phase0.py')
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


class AuditTests(unittest.TestCase):
    def test_missingness_and_frame_period_alignment(self):
        with tempfile.TemporaryDirectory() as temporary:
            d = Path(temporary) / '999'
            d.mkdir()
            meta = {'players': [{'id': 1, 'team_id': 10}, {'id': 2, 'team_id': 20}],
                    'home_team': {'id': 10}, 'away_team': {'id': 20}, 'pitch_length': 105, 'pitch_width': 68}
            (d / '999_match.json').write_text(json.dumps(meta))
            fields = ['event_type', 'frame_start', 'frame_end', 'period', 'player_id', 'team_id', 'attacking_side', 'time_start', 'time_end', 'start_type']
            with (d / '999_dynamic_events.csv').open('w', newline='') as h:
                w = csv.DictWriter(h, fieldnames=fields)
                w.writeheader()
                w.writerow(dict(zip(fields, ['player_possession', 1, 1, 1, 1, 10, 'left_to_right', '00:00.1', '00:00.1', 'reception'])))
                w.writerow(dict(zip(fields, ['player_possession', 2, 2, 2, 1, 10, 'left_to_right', '00:00.2', '00:00.2', 'reception'])))
            def row(frame, detected):
                return {'frame': frame, 'period': 1, 'timestamp': f'00:00:00.{frame}',
                        'possession': {'player_id': 1, 'group': 'home team'},
                        'ball_data': {'x': 0, 'y': 0, 'is_detected': True},
                        'player_data': [{'player_id': 1, 'x': 0, 'y': 0, 'is_detected': detected},
                                        {'player_id': 2, 'x': 2, 'y': 0, 'is_detected': False}]}
            (d / '999_tracking_extrapolated.jsonl').write_text('\n'.join(json.dumps(row(f, flag)) for f, flag in [(1, True), (2, False)]))
            result = audit.audit_match(d)
            self.assertEqual(result['carrier_frames'], {'detected': 1, 'extrapolated': 1})
            self.assertEqual(result['boundaries']['period_mismatch'], 1)
            self.assertEqual(result['boundaries']['carrier_and_ball_detected'], 1)
            self.assertEqual(result['counts']['timestamp_not_0.1s'], 0)
            self.assertEqual(result['counts']['unknown_player_ids'], 0)
            self.assertEqual(result['missing_event_endpoint_frames'], 0)

    def test_nonfinite_coordinates_abstain(self):
        self.assertEqual(audit.state({'x': float('nan'), 'y': 0, 'is_detected': True}), 'absent_or_invalid')
        self.assertEqual(audit.state({'x': 1, 'y': 0, 'is_detected': False}), 'extrapolated')
        self.assertAlmostEqual(audit.clock('01:02:03.4'), 3723.4)


if __name__ == '__main__':
    unittest.main()
