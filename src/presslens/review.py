"""Append-only human review records with revisions and disclosure provenance."""
import json
import os
import threading
import uuid
from datetime import datetime, timezone
from . import __version__
from .annotation_protocol import normalize_observation, replay_disclosure


OUTCOMES = {'pass', 'carry', 'turnover', 'dead_ball', 'shot', 'unknown'}


class ReviewLog:
    def __init__(self, path):
        self.path = path
        self.lock = threading.RLock()

    def records(self):
        if not self.path.exists():
            return []
        with self.path.open(encoding='utf-8') as handle:
            return [json.loads(line) for line in handle if line.strip()]

    def latest(self, mid=None):
        with self.lock:
            result = {}
            for row in self.records():
                result[row['annotation_id']] = row
            return [r for r in result.values() if mid is None or r['match_id'] == mid]

    def save(self, payload, match, session):
        with self.lock:
            prior = next((r for r in self.latest() if r['annotation_id'] == payload.get('annotation_id')), None)
            if payload.get('annotation_id') and prior is None:
                raise ValueError('Unknown annotation ID')
            if prior and prior['match_id'] != match.mid:
                raise ValueError('Cannot move an annotation to a different match')
            if prior and payload.get('base_revision') != prior['revision']:
                raise ValueError('Annotation changed in another tab. Reload the saved review before editing.')
            stage = payload.get('stage')
            if stage not in ('observation', 'outcome', 'quality'):
                raise ValueError('Choose observation, outcome or data-quality review')
            reviewer = str(payload.get('reviewer', '')).strip()
            if not reviewer or len(reviewer) > 100:
                raise ValueError('Enter a reviewer name (up to 100 characters)')
            quality_review = prior.get('quality_review') if prior else None
            if stage == 'observation':
                observation = normalize_observation(payload.get('observation'), match)
                outcome = prior.get('outcome') if prior else None
                if prior and (observation['start_frame'], observation['end_frame']) != (prior['observation']['start_frame'], prior['observation']['end_frame']) and (outcome or quality_review):
                    raise ValueError('A follow-up-reviewed interval is fixed. Create a new annotation to change its boundaries.')
            else:
                if prior is None:
                    raise ValueError('Save an observation before reviewing outcomes or data quality')
                observation = prior['observation']
                outcome = prior.get('outcome')
                if stage == 'outcome':
                    if match.mid not in session['outcomes_revealed']:
                        raise ValueError('Reveal outcomes explicitly before saving an outcome review')
                    outcome = payload.get('outcome') or {}
                    if not isinstance(outcome, dict) or outcome.get('label') not in OUTCOMES:
                        raise ValueError('Unknown outcome label')
                    outcome = {'label': outcome['label'], 'notes': str(outcome.get('notes', ''))[:5000],
                               'evidence_type': 'human judgement after separate outcome review'}
                else:
                    notes = str(payload.get('data_quality_notes', '')).strip()
                    if not notes or len(notes) > 5000:
                        raise ValueError('Enter a data-quality observation (up to 5,000 characters)')
                    quality_review = {'notes': notes, 'reviewer': reviewer,
                                      'saved_utc': datetime.now(timezone.utc).isoformat(),
                                      'evidence_type': 'human data-quality judgement; not a source correction'}
            disclosure = replay_disclosure(payload, observation, match, prior, session)
            schema = '2.0' if stage == 'observation' else prior.get('schema_version', '1.0')
            context = match.context(match.raw(observation['start_frame']))
            record = {'schema_version': schema, 'review_protocol_version': '2.0', 'annotation_id': prior['annotation_id'] if prior else str(uuid.uuid4()),
                      'revision': prior['revision'] + 1 if prior else 1, 'match_id': match.mid,
                      'reviewer': reviewer, 'review_pass': stage, 'saved_utc': datetime.now(timezone.utc).isoformat(),
                      'observation': observation, 'outcome': outcome, 'quality_review': quality_review,
                      'replay_review': disclosure, 'start_context': context,
                      'interval_quality': match.interval_quality(observation['start_frame'], observation['end_frame']),
                      'provenance': {'evidence_type': 'human tactical judgement; not confirmed intention',
                                     'software_version': __version__, 'software': match.software, 'input_sha256': match.hashes,
                                     'eligibility_manifest_sha256': match.manifest_hash,
                                     'partition': 'development', 'prior_exposure': 'legacy_all_match_exploration',
                                     'provider_context_revealed_in_session': match.mid in session['provider_revealed'],
                                     'outcomes_revealed_in_session': match.mid in session['outcomes_revealed'],
                                     'outcomes_exposed_in_previous_revision': bool(prior and (prior.get('outcome') or prior['provenance'].get('outcomes_revealed_in_session') or prior['provenance'].get('outcomes_exposed_in_previous_revision'))),
                                     'annotation_history_revealed_in_session': match.mid in session['history_revealed'],
                                     'source_release_eligibility': 'pending; local review only',
                                     'supersedes_revision': prior['revision'] if prior else None,
                                     'legacy_source_revision': prior['revision'] if prior and prior.get('schema_version') == '1.0' and stage == 'observation' else None,
                                     'detector_version': None}}
            actor_ids = {observation.get('primary_presser_id'), observation.get('nominated_carrier_id')}
            for role in observation.get('supporting_roles', []):
                actor_ids.update((role['player_id'], role.get('target_player_id')))
            actor_ids.update(observation.get('supporting_defender_ids', []))
            record['actor_visibility'] = match.actor_visibility(
                observation['start_frame'], observation['end_frame'], {p for p in actor_ids if p is not None})
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open('a', encoding='utf-8', newline='\n') as handle:
                handle.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + '\n')
                handle.flush()
                os.fsync(handle.fileno())
            return record
