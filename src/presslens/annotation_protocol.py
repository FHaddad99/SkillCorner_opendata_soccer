"""Version 2 human annotation definitions and validation; no tactical detector."""
UNCERTAINTY = {'low', 'medium', 'high', 'not_assessed'}
DIRECTIONS = {'unknown', 'left', 'right', 'forward', 'backward', 'multiple'}
STAGES = ('cue_frame', 'press_onset_frame', 'reception_frame', 'action_end_frame')


def choice(value, allowed, name):
    if value not in allowed:
        raise ValueError('Choose a valid ' + name)
    return value


def native_frame(frame, match, period, name):
    if type(frame) is not int or match.raw(frame)['period'] != period:
        raise ValueError(name + ' must be a native frame in the annotated period')
    return frame


def normalize_observation(observation, match):
    if not isinstance(observation, dict):
        raise ValueError('Observation must be an object')
    if 'press_assessment' not in observation or 'funnel_assessment' not in observation:
        raise ValueError('Refresh the viewer: new observations require separate press and funnel assessments')
    start, end = observation.get('start_frame'), observation.get('end_frame')
    if type(start) is not int or type(end) is not int or start > end:
        raise ValueError('Start and end must be ordered integer frame IDs')
    first, last = match.raw(start), match.raw(end)
    period = first['period']
    if period not in (1, 2) or period != last['period']:
        raise ValueError('Choose an interval within one labelled playing period')
    context_start = observation.get('context_start_frame', start)
    native_frame(context_start, match, period, 'Context start')
    if context_start > start:
        raise ValueError('Context start must be at or before the observation start')
    press = choice(observation.get('press_assessment'), {'present', 'absent', 'uncertain', 'not_assessed'}, 'press assessment')
    funnel = choice(observation.get('funnel_assessment'), {'candidate', 'no_funnel', 'uncertain', 'unassessable', 'not_assessed'}, 'funnel assessment')
    visibility = choice(observation.get('funnel_observability', 'not_assessed'), {'adequate', 'limited', 'unassessable', 'not_assessed'}, 'funnel observability')
    if funnel in ('candidate', 'no_funnel') and press != 'present':
        raise ValueError('A funnel candidate or no-funnel pressure judgement requires a present press-like response')
    if funnel == 'no_funnel' and visibility != 'adequate':
        raise ValueError('No funnel apparent requires adequate route visibility; otherwise choose uncertain or unassessable')
    if funnel == 'candidate' and visibility in ('unassessable', 'not_assessed'):
        raise ValueError('Review route visibility before assigning a funnel candidate')
    if funnel == 'unassessable' and visibility not in ('limited', 'unassessable'):
        raise ValueError('An unassessable funnel judgement needs limited or unavailable essential geometry')
    rationale = str(observation.get('rationale', '')).strip()
    if not rationale or len(rationale) > 5000:
        raise ValueError('Enter an evidence rationale (up to 5,000 characters)')
    funnel_rationale = str(observation.get('funnel_rationale', '')).strip()
    if len(funnel_rationale) > 5000 or (funnel in ('candidate', 'no_funnel') and not funnel_rationale):
        raise ValueError('Explain the route/support evidence for the funnel or no-funnel judgement')
    team = observation.get('defending_team_id')
    teams = (match.meta['home_team']['id'], match.meta['away_team']['id'])
    if team is not None and (type(team) is not int or team not in teams):
        raise ValueError('Unknown defending team')
    attacking = next((t for t in teams if t != team), None) if team else None
    def role_player(pid, defending, name):
        if pid is not None and (type(pid) is not int or pid not in match.players or team is None or match.players[pid]['team_id'] != (team if defending else attacking)):
            raise ValueError(name + ' must belong to the selected defending team' if defending else name + ' must belong to the opposing attacking team')
    primary = observation.get('primary_presser_id')
    carrier = observation.get('nominated_carrier_id')
    role_player(primary, True, 'Primary presser')
    role_player(carrier, False, 'Nominated attacker')
    support = observation.get('supporting_roles') or []
    if not isinstance(support, list) or len(support) > 11:
        raise ValueError('Supply at most eleven supporting roles')
    normalized_roles, seen = [], set()
    for role in support:
        if not isinstance(role, dict):
            raise ValueError('Supporting role must be an object')
        pid = role.get('player_id')
        if pid is None:
            raise ValueError('Choose a supporting defender')
        role_player(pid, True, 'Supporting defender')
        if pid == primary or pid in seen:
            raise ValueError('Primary and supporting defenders must have distinct IDs')
        seen.add(pid)
        target = role.get('target_player_id')
        role_player(target, False, 'Role target')
        function = choice(role.get('function', 'not_assessed'), {'not_assessed', 'approach_carrier', 'cover_receiver', 'cover_route', 'other_observed'}, 'support function')
        description = str(role.get('description', '')).strip()
        if len(description) > 2000:
            raise ValueError('Role description is too long')
        if function == 'cover_receiver' and target is None:
            raise ValueError('Receiver coverage needs a nominated receiving target')
        if function in ('cover_route', 'other_observed') and not description:
            raise ValueError('Describe the nominated route or observed supporting function')
        normalized_roles.append({'player_id': pid, 'function': function, 'target_player_id': target,
                                 'description': description, 'uncertainty': choice(role.get('uncertainty', 'not_assessed'), UNCERTAINTY, 'role uncertainty')})
    evidence = observation.get('evidence_frames') or [start]
    if not isinstance(evidence, list) or len(evidence) > 100:
        raise ValueError('Supply at most 100 evidence frames')
    stages = observation.get('stages') or {}
    if not isinstance(stages, dict) or any(k not in STAGES for k in stages):
        raise ValueError('Unknown stage bookmark')
    normalized_stages = {}
    for name in STAGES:
        frame = stages.get(name)
        if frame is not None:
            native_frame(frame, match, period, name)
            if not context_start <= frame <= end:
                raise ValueError('Stage bookmarks must lie between context start and observation end')
        normalized_stages[name] = frame
    for frame in evidence:
        native_frame(frame, match, period, 'Evidence frame')
        if not context_start <= frame <= end:
            raise ValueError('Evidence frames must lie inside the context/observation window')
    cue = choice(observation.get('cue', 'unknown'), {'unknown', 'absent', 'backward_pass', 'wide_reception', 'other_observed'}, 'cue category')
    directions = {key: choice(observation.get(key, 'unknown'), DIRECTIONS, 'direction') for key in ('blocked_direction', 'surviving_direction')}
    if any(v in ('left', 'right', 'forward', 'backward') for v in directions.values()) and team is None:
        raise ValueError('Choose a defending team before using attack-relative directions')
    home_direction = match.meta['home_team_side'][period - 1]
    home_sign = 1 if home_direction == 'left_to_right' else -1 if home_direction == 'right_to_left' else None
    sign = home_sign if attacking == teams[0] else -home_sign if attacking and home_sign else None
    flags = []
    cue_at, onset = normalized_stages['cue_frame'], normalized_stages['press_onset_frame']
    if cue_at is not None and onset is not None and cue_at > onset:
        flags.append('Nominated cue follows nominated press onset; not a preceding-cue claim')
    if press == 'absent' and onset is not None:
        flags.append('Press onset bookmarked while press is judged absent; review this inconsistency')
    if len(set(evidence) | {f for f in normalized_stages.values() if f is not None}) < 2:
        flags.append('Only one evidence frame; movement judgement needs temporal review')
    return {'start_frame': start, 'end_frame': end, 'context_start_frame': context_start, 'period': period,
            'press_assessment': press, 'funnel_assessment': funnel, 'funnel_observability': visibility,
            'press_uncertainty': choice(observation.get('press_uncertainty', 'not_assessed'), UNCERTAINTY, 'press uncertainty'),
            'funnel_uncertainty': choice(observation.get('funnel_uncertainty', 'not_assessed'), UNCERTAINTY, 'funnel uncertainty'),
            'primary_role_uncertainty': choice(observation.get('primary_role_uncertainty', 'not_assessed'), UNCERTAINTY, 'primary-role uncertainty'),
            'cue_uncertainty': choice(observation.get('cue_uncertainty', 'not_assessed'), UNCERTAINTY, 'cue uncertainty'),
            'defending_team_id': team, 'attacking_team_id': attacking, 'primary_presser_id': primary,
            'nominated_carrier_id': carrier, 'supporting_roles': normalized_roles,
            'evidence_frames': sorted(set(evidence)), 'stages': normalized_stages, 'cue': cue, **directions,
            'direction_reference': {'convention': 'attacking_team_relative', 'forward_native_x_sign': sign,
                                    'attacking_left_native_y_sign': sign, 'body_facing_inferred': False},
            'rationale': rationale, 'funnel_rationale': funnel_rationale,
            'notes': str(observation.get('notes', ''))[:5000], 'review_flags': flags}


def replay_disclosure(payload, observation, match, prior, session):
    disclosure = payload.get('replay_review') or {}
    if not isinstance(disclosure, dict):
        raise ValueError('Replay disclosure must be an object')
    report = choice(disclosure.get('future_replay_viewed', 'unknown'), {'yes', 'no', 'unknown'}, 'future replay disclosure')
    explicit, seen = disclosure.get('reviewed_through_frame'), disclosure.get('viewer_session_max_frame')
    for name, value in (('Reviewed-through frame', explicit), ('Displayed-through frame', seen)):
        if value is not None:
            native_frame(value, match, observation['period'], name)
    key = match.mid + ':' + str(observation['period'])
    memory = session.setdefault('replay_max_seen', {})
    if seen is not None:
        memory[key] = max(memory.get(key, seen), seen)
    seen = memory.get(key)
    values = [v for v in (explicit, seen) if v is not None]
    previous = (prior or {}).get('replay_review', {})
    known_future = report == 'yes' or any(f > observation['end_frame'] for f in values) or previous.get('future_replay_exposed') is True
    historical_unknown = bool(prior and previous.get('future_replay_exposed') is not False)
    status = True if known_future else None if report == 'unknown' or historical_unknown else False
    return {'future_replay_viewed': report, 'reviewed_through_frame': explicit,
            'viewer_session_max_frame': seen, 'future_replay_exposed': status,
            'prior_revision_future_exposure': previous.get('future_replay_exposed') if prior else None,
            'measurement_note': 'Browser-reported displayed-frame maximum plus reviewer disclosure; not proof of blinding or absence of prior exposure.'}
