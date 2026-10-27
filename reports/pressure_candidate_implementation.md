# Pressure candidate workflow: implementation decisions

The owner authorized automatic candidate proposals followed by simple human funnel review. Software v0.7.0 implements this alongside the existing manual pressure marker, using the existing audited local inputs only.

## Delivered behaviour

- Main queue: provider pressure/pressing engagements grouped conservatively by overlapping time, half and defending team. Grouping stops at interruptions, attacking-team changes and missing tracking frames. The configurable gap defaults to zero. Provider-chain IDs are retained as source metadata rather than assumed to define validated episodes.
- Other queues: all engagement types, active saved human pressure examples across reviewers, and systematic ten-second windows outside the main proposals.
- Funnel decisions: yes, no, uncertain, unassessable; separate not-pressure/out-of-scope states and withdrawal to unreviewed. Counter-attacks, fast breaks and represses remain deferred. No automatic mapping from provider counterpress/recovery subtypes to the owner's exclusions is asserted.
- Full-half replay remains available. Loading/filtering/saving does not seek or pause. Explicit candidate navigation seeks to preceding context; playback continues through the half when the reviewer presses Play. Ordinary saving retains the selected episode even when its saved decision no longer matches the active filter.
- Review bounds are editable within the original half. Original bounds remain in the record, exact interval sequence IDs change with revised bounds, and stable candidate IDs retain review lineage. New grouping policies produce new candidate identities. Compatible identical proposals share IDs across the main/expanded pools.
- Human funnel reviews append to `.presslens/candidate_reviews.jsonl`, separate from all older files. Stale writes are rejected; reviewers remain independent. Exports include every revision, source/implementation/configuration hashes, source nominees, scope and interval/replay-quality disclosures.

## Data findings and limitations

The local audit found 8,435 source pressure/pressing engagements, 8,434 represented engagements, and 7,880 grouped proposals across 20 matches. One engagement is omitted: match 1953632, event 9_726, frames 55586–55597, defender 973077 absent from the match roster. Queue diagnostics expose omitted source event IDs, bounds and reasons. No roster actor is guessed.

All six active saved human pressure examples overlap a main proposal. This is only inclusive within-half temporal overlap, allowing multiple matches; it does not validate episode onset, scope, actor identities, pressure meaning, full-match recall or funnel classification. The expanded/audit pools support further checking. Candidate generation uses no funnel labels, overall-pressure bands or subsequent success/outcome criteria.

This implementation is provider-assisted triage rather than a calibrated tracking classifier. Existing carrier/context reliability findings remain relevant and visible in replay. No model is trained on the small human example set, and no detector performance or scientific novelty is asserted. The viewer records observed patterns consistent with funneling, not coaching intent or causality.

## Validation

44 software tests passed. Three browser regressions passed: candidate review, existing manual marker/edit/delete/undo, and full-half replay. Checks cover real saves and API revisions, stale-write rejection, replay continuity, reviewed/deferred filters, explicit next navigation, original/revised bounds, scope exclusions and export history. All automated writes used temporary logs. Existing human files remained byte-for-byte unchanged, and no real candidate-review file was created by QA.

Evidence: `reports/candidate_review_verification.json`, `reports/press_marker_verification.json`, `reports/replay_current_verification.json`, `reports/pressure_candidate_audit.json`. User instructions: `docs/pressure_candidate_review.md`.
