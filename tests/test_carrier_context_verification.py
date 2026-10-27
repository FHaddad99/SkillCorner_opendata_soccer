"""Synthetic boundary/missingness tests; no empirical football evidence."""
import importlib.util
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location('verify', Path(__file__).parents[1] / 'scripts/verify_carrier_context.py')
verify = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verify)


class ContextVerificationTests(unittest.TestCase):
    def test_team_change_boundary_is_ambiguous_if_inclusive(self):
        rows = [{'frame_start': '10', 'frame_end': '20', 'period': '1', 'team_in_possession_id': '1'},
                {'frame_start': '20', 'frame_end': '30', 'period': '1', 'team_in_possession_id': '2'}]
        self.assertEqual([r['team_in_possession_id'] for r in verify.members(rows, 20, 'half_open')], ['2'])
        self.assertEqual([r['team_in_possession_id'] for r in verify.members(rows, 20, 'inclusive')], ['1', '2'])
        self.assertEqual(verify.members(rows, 20, 'strict_interior'), [])
        self.assertEqual(verify.members(rows, 30, 'half_open'), [])

    def test_coverage_counts_union_without_including_other_period(self):
        rows = [{'frame_start': '1', 'frame_end': '4', 'period': '1'},
                {'frame_start': '3', 'frame_end': '5', 'period': '1'},
                {'frame_start': '0', 'frame_end': '7', 'period': '2'}]
        mask = verify.coverage(rows, 1, 8)
        self.assertEqual(mask[:7], [0, 1, 1, 2, 1, 0, 0])
        self.assertEqual(sum(v > 0 for v in mask), 4)
        self.assertIsNone(verify.identifier(None))
        self.assertEqual(verify.identifier('001'), 1)


if __name__ == '__main__':
    unittest.main()
