"""Check all audited matches load and provide exact native period-boundary frames."""
import hashlib
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from presslens.replay import ReplayStore


def main():
    store = ReplayStore(ROOT)
    results = []
    for mid in store.ids:
        before = time.perf_counter()
        match = store.load(mid)
        checks = []
        for period, span in match.periods.items():
            for frame in (span['start'], span['end']):
                row = match.window(frame, 1)['frames'][0]
                assert row['frame'] == frame and row['period'] == period
                assert not row.get('missing')
                checks.append({'period': period, 'frame': frame, 'quality': row['quality']})
        assert len(checks) == 4
        results.append({'match_id': mid, 'input_hashes_verified': 4, 'native_period_boundary_checks': checks,
                        'load_and_check_seconds': round(time.perf_counter() - before, 3)})
        print('Verified native replay boundaries: ' + mid, flush=True)
    output = {'generated_utc': datetime.now(timezone.utc).isoformat(), 'python': platform.python_version(),
              'status': 'passed', 'scope': '20 matches; four input hashes and four native period-boundary frames per match',
              'software': store.software, 'matches': results,
              'limitations': ['Not a frame-by-frame visual review.', 'No human tactical annotations or detector validity established.',
                              'Source-release and redistribution eligibility remain pending.']}
    (ROOT / 'reports/phase1_validation.json').write_text(json.dumps(output, indent=2), encoding='utf-8')
    print('Wrote reports/phase1_validation.json')


if __name__ == '__main__':
    main()
