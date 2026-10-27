"""Hash-gated local replay access; preserves provider IDs and unknown states."""
import csv
import hashlib
import json
import math
import subprocess
import threading
from collections import OrderedDict
from pathlib import Path
from . import __version__


def finite_xy(value):
    return bool(value) and all(isinstance(value.get(k), (int, float)) and math.isfinite(value[k]) for k in ('x', 'y'))


def clean_json(value):
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {k: clean_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [clean_json(v) for v in value]
    return value


class ReplayStore:
    def __init__(self, root):
        self.root = Path(root).resolve()
        manifest = self.root / 'reports/eligibility_manifest.json'
        if not manifest.is_file():
            raise ValueError('Missing reports/eligibility_manifest.json. Run the Phase 0 audit first.')
        self.manifest_hash = hashlib.sha256(manifest.read_bytes()).hexdigest()
        self.allowed = {r['path']: r for r in json.loads(manifest.read_text(encoding='utf-8'))['files']}
        self.cache = OrderedDict()
        self.lock = threading.RLock()
        path = self.checked_path('data/matches.json')
        self.ids = sorted(str(r['id']) for r in json.loads(path.read_text(encoding='utf-8')))
        config_path = self.root / 'config/presslens_review.json'
        if not config_path.exists():
            raise ValueError('Missing config/presslens_review.json. Configure local review scope before starting.')
        self.config_hash = hashlib.sha256(config_path.read_bytes()).hexdigest()
        self.config = json.loads(config_path.read_text(encoding='utf-8'))
        if sorted(self.config['review_match_ids']) != self.ids or self.config.get('partition') != 'development' or self.config.get('untouched_evaluation_set'):
            raise ValueError('Review partition differs from the documented development-only scope. Review the configuration and provenance first.')
        sources = sorted([*list((self.root / 'src/presslens').glob('*.py')),
                          *list((self.root / 'viewer').glob('*')), self.root / 'scripts/run_presslens.py'])
        digest = hashlib.sha256()
        for source in sources:
            if source.is_file():
                digest.update(source.relative_to(self.root).as_posix().encode())
                digest.update(source.read_bytes())
        try:
            commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=self.root, text=True, stderr=subprocess.DEVNULL).strip()
        except (OSError, subprocess.CalledProcessError):
            commit = None
        self.software = {'version': __version__, 'implementation_sha256': digest.hexdigest(),
                         'config_sha256': self.config_hash, 'git_commit': commit,
                         'working_tree_note': 'Implementation hash identifies runtime source, including uncommitted files.'}

    def checked_path(self, relative):
        entry = self.allowed.get(relative)
        path = (self.root / relative).resolve()
        if entry is None or not path.is_relative_to(self.root) or not path.is_file():
            raise ValueError('Input is missing or outside the audited allowlist: ' + relative)
        with path.open('rb') as handle:
            digest = hashlib.sha256()
            for chunk in iter(lambda: handle.read(1024 * 1024), b''):
                digest.update(chunk)
            actual = digest.hexdigest()
        if actual != entry['sha256']:
            raise ValueError('Input hash differs from Phase 0: ' + relative + '. Re-audit before review.')
        return path

    def metadata(self, mid):
        if mid not in self.ids:
            raise ValueError('Unknown match ID')
        path = self.checked_path(f'data/matches/{mid}/{mid}_match.json')
        return json.loads(path.read_text(encoding='utf-8'))

    def catalogue(self):
        matches = []
        for mid in self.ids:
            m = self.metadata(mid)
            matches.append({'id': mid, 'home': m['home_team']['short_name'], 'away': m['away_team']['short_name'],
                            'date': m['date_time'][:10], 'partition': 'development',
                            'prior_exposure': 'Legacy P1/P2 exploratory outputs cover this match; no untouched holdout claimed.'})
        return {'matches': matches, 'version': __version__, 'scope': 'Local retrospective review only',
                'eligibility': 'Release provenance and redistribution remain pending; no publishing enabled.'}

    def load(self, mid):
        with self.lock:
            if mid in self.cache:
                result = self.cache.pop(mid)
                self.cache[mid] = result
                result.assert_unchanged()
                return result
            if mid not in self.ids:
                raise ValueError('Unknown match ID')
            paths = {suffix: self.checked_path(f'data/matches/{mid}/{mid}_{suffix}') for suffix in (
                'match.json', 'tracking_extrapolated.jsonl', 'dynamic_events.csv', 'phases_of_play.csv')}
            hashes = {key: self.allowed[path.relative_to(self.root).as_posix()]['sha256'] for key, path in paths.items()}
            result = MatchReplay(mid, paths, hashes, self.manifest_hash)
            result.software = self.software
            result.review_scope = self.config.get('press_review_scope', {'status': 'not_recorded'})
            from .candidates import POLICY
            result.candidate_policy = self.config.get('pressure_candidates', POLICY)
            self.cache[mid] = result
            if len(self.cache) > 2:
                self.cache.popitem(last=False)
            return result


class MatchReplay:
    def __init__(self, mid, paths, hashes, manifest_hash):
        self.mid, self.paths, self.hashes, self.manifest_hash = mid, paths, hashes, manifest_hash
        self.fingerprints = {key: (p.stat().st_size, p.stat().st_mtime_ns) for key, p in paths.items()}
        self.meta = json.loads(paths['match.json'].read_text(encoding='utf-8'))
        self.players = {p['id']: p for p in self.meta['players']}
        self.events = self.read_csv(paths['dynamic_events.csv'])
        self.possessions = [r for r in self.events if r['event_type'] == 'player_possession']
        self.phases = self.read_csv(paths['phases_of_play.csv'])
        self.offsets, self.periods = {}, {}
        with paths['tracking_extrapolated.jsonl'].open('rb') as handle:
            while True:
                offset = handle.tell()
                line = handle.readline()
                if not line:
                    break
                row = json.loads(line)
                frame = row['frame']
                if frame in self.offsets:
                    raise ValueError('Duplicate frame ID; replay cannot choose a record safely.')
                self.offsets[frame] = offset
                if row['period'] in (1, 2):
                    p = self.periods.setdefault(row['period'], {'start': frame, 'end': frame})
                    p['end'] = frame
        if not self.offsets:
            raise ValueError('Tracking file has no frames')
        self.first, self.last = min(self.offsets), max(self.offsets)
        self.assert_unchanged()

    @staticmethod
    def read_csv(path):
        with path.open(encoding='utf-8-sig', newline='') as handle:
            return list(csv.DictReader(handle))

    def assert_unchanged(self):
        if any((p.stat().st_size, p.stat().st_mtime_ns) != self.fingerprints[key] for key, p in self.paths.items()):
            raise ValueError('A match file changed during review. Restart and re-audit before continuing.')

    def raw(self, frame):
        self.assert_unchanged()
        if frame not in self.offsets:
            raise ValueError('Frame is absent from the source file')
        with self.paths['tracking_extrapolated.jsonl'].open('rb') as handle:
            handle.seek(self.offsets[frame])
            return json.loads(handle.readline())

    def info(self):
        return {'id': self.mid, 'home': self.meta['home_team'], 'away': self.meta['away_team'],
                'date': self.meta['date_time'][:10], 'pitch': [self.meta['pitch_length'], self.meta['pitch_width']],
                'home_directions': self.meta['home_team_side'], 'periods': self.periods,
                'first_frame': self.first, 'last_frame': self.last,
                'players': [{'id': p['id'], 'name': p['short_name'], 'number': p['number'], 'team_id': p['team_id']} for p in self.players.values()],
                'partition': 'development', 'prior_exposure': 'All local matches have legacy exploratory exposure.',
                'review_scope': self.review_scope,
                'provenance': {**self.software, 'input_sha256': self.hashes, 'manifest_sha256': self.manifest_hash},
                # Phase names are optional provider context; no outcomes or score.
                'phase_timeline': [{'period': int(r['period']), 'start': int(r['frame_start']), 'end': int(r['frame_end']),
                                    'index': r['index'], 'team_id': int(r['team_in_possession_id']),
                                    'label': r['team_out_of_possession_phase_type']} for r in self.phases]}

    def context(self, row):
        frame, period = row['frame'], row['period']
        phases = [p for p in self.phases if int(p['period']) == period and int(p['frame_start']) <= frame < int(p['frame_end'])]
        # Endpoint-inclusive event candidates are kept separately; overlaps are explicit.
        possessions = [e for e in self.possessions if int(e['period']) == period and int(e['frame_start']) <= frame <= int(e['frame_end'])]
        cid = (row.get('possession') or {}).get('player_id')
        flags = []
        if period not in (1, 2):
            flags.append('Outside a labelled playing period')
        if cid is None:
            flags.append('Tracking carrier unknown')
        if not finite_xy(row.get('ball_data')):
            flags.append('Ball position unavailable')
        if len(possessions) > 1:
            flags.append('Multiple possession-event candidates')
        if cid is not None and any(int(e['player_id']) != cid for e in possessions):
            flags.append('Tracking/event carrier disagreement')
        if any(self.players.get(int(e['player_id']), {}).get('team_id') != int(e['team_id']) for e in possessions):
            flags.append('Event player unresolved against team roster')
        if phases and any(int(e['team_id']) != int(phases[0]['team_in_possession_id']) for e in possessions):
            flags.append('Event/phase team disagreement')
        if len(phases) != 1:
            flags.append('Phase context unknown or ambiguous')
        return {'frame': frame, 'period': period, 'tracking_carrier_id': cid,
                'tracking_group': (row.get('possession') or {}).get('group'), 'flags': flags,
                'phase': [{'index': p['index'], 'team_id': int(p['team_in_possession_id']),
                           'in_possession': p['team_in_possession_phase_type'], 'out_of_possession': p['team_out_of_possession_phase_type']} for p in phases],
                # Only onset fields are sent. Event endpoints/outcomes require an explicit separate request.
                'event_candidates': [{'id': e['event_id'], 'player_id': int(e['player_id']), 'team_id': int(e['team_id']),
                                      'start_type': e['start_type'], 'at_start': int(e['frame_start']) == frame} for e in possessions],
                'conventions': 'Phase [start,end); possession candidates [start,end]. Labels are provider outputs.'}

    def window(self, start, count):
        if start < self.first or start > self.last:
            raise ValueError('Window start is outside the match frame range')
        if count < 1 or count > 200:
            raise ValueError('Window count must be between 1 and 200')
        self.assert_unchanged()
        output = []
        with self.paths['tracking_extrapolated.jsonl'].open('rb') as handle:
            for frame in range(start, min(self.last + 1, start + count)):
                if frame not in self.offsets:
                    output.append({'frame': frame, 'missing': True})
                    continue
                handle.seek(self.offsets[frame])
                row = json.loads(handle.readline())
                ps = row.get('player_data') or []
                output.append({'frame': frame, 'period': row['period'], 'timestamp': row['timestamp'],
                               'ball': row['ball_data'], 'possession': row['possession'],
                               'players': [[p['player_id'], p['x'], p['y'], p['is_detected']] for p in ps],
                               'quality': {'detected': sum(p.get('is_detected') is True and finite_xy(p) for p in ps),
                                           'extrapolated': sum(p.get('is_detected') is False and finite_xy(p) for p in ps),
                                           'invalid_xy': sum(not finite_xy(p) for p in ps)}})
        return clean_json({'frames': output, 'native_fps': 10, 'interpolation': False})

    def interval_quality(self, start, end):
        """Native-record summary for the complete saved interval, no interpolation."""
        counts = {'expected_frame_slots': end - start + 1, 'source_frames': 0,
                  'tracking_carrier_unknown_frames': 0, 'ball_xy_unavailable_frames': 0,
                  'detected_player_entries': 0, 'extrapolated_player_entries': 0}
        with self.paths['tracking_extrapolated.jsonl'].open('rb') as handle:
            handle.seek(self.offsets[start])
            for line in handle:
                row = json.loads(line)
                if row['frame'] > end:
                    break
                counts['source_frames'] += 1
                counts['tracking_carrier_unknown_frames'] += (row.get('possession') or {}).get('player_id') is None
                counts['ball_xy_unavailable_frames'] += not finite_xy(row.get('ball_data'))
                counts['detected_player_entries'] += sum(finite_xy(p) and p.get('is_detected') is True for p in row['player_data'])
                counts['extrapolated_player_entries'] += sum(finite_xy(p) and p.get('is_detected') is False for p in row['player_data'])
        counts['missing_source_frame_slots'] = counts['expected_frame_slots'] - counts['source_frames']
        return counts

    def actor_visibility(self, start, end, ids):
        """Quality for nominated actors and targets, rather than whole-pitch shares."""
        output = {str(pid): {'name': self.players.get(pid, {}).get('short_name'),
                            'detected': 0, 'extrapolated': 0, 'absent': 0,
                            'invalid_xy': 0, 'unknown_detection': 0} for pid in ids}
        seen = 0
        with self.paths['tracking_extrapolated.jsonl'].open('rb') as handle:
            handle.seek(self.offsets[start])
            for line in handle:
                row = json.loads(line)
                if row['frame'] > end:
                    break
                seen += 1
                players = {p['player_id']: p for p in row['player_data']}
                for pid in ids:
                    p = players.get(pid)
                    label = 'absent' if p is None else 'invalid_xy' if not finite_xy(p) else 'detected' if p.get('is_detected') is True else 'extrapolated' if p.get('is_detected') is False else 'unknown_detection'
                    output[str(pid)][label] += 1
        return {'window': [start, end], 'source_frames': seen, 'actors': output,
                'note': 'Counts use provider detection flags; no independent identity or pose accuracy implied.'}
