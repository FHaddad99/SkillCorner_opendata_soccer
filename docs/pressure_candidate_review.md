# Pressure candidates and funnel review

PressLens v0.7 adds a faster review path above the manual pressure marker. Start the local viewer with `start_presslens.cmd`; restart an existing server and refresh after updating.

## Review an episode

1. Enter your reviewer name. The default queue contains provider `pressure` and `pressing` engagements grouped into candidate episodes. Opening a queue creates no human judgement.
2. Click **Replay with context**, or select another episode. The cursor moves to three seconds before the proposed start, bounded by the half. Use the normal Play, speed, step and scrub controls. Replay continues through the full half rather than looping or stopping at the proposed end.
3. Select **Yes**, **No**, **Unsure** or **Cannot assess** for observed funneling. Consider whether the approaching defender and supporting geometry appear to restrict alternatives while leaving or directing play toward a particular route. Pressure, a backward pass or a turnover alone is insufficient. No requires adequate visibility; insufficient visibility belongs under Cannot assess.
4. Use **Not a pressure episode** for a false candidate. Use **Outside current scope** and choose counter-attack, fast break or repress for an excluded situation. These actions leave funneling unassessed; they are not funnel negatives.
5. Click **Save review** to save without changing playback. **Save + next replay** explicitly saves and navigates to the next visible proposal. Revise saved judgements by saving another revision, or save **Unreviewed / clear decision** to withdraw an assessment while retaining its history.

You can edit start/end numbers before saving. Source bounds remain in `original_case`; your revised interval has its own exact sequence ID. Keep bounds in the original half. Role nomination is optional: displayed provider engagement actors are source nominees, never copied into your manually confirmed P/S roles.

Opening/reloading/filtering a queue does not seek or pause. Selecting an episode, Previous/Next + replay, Replay with context and Save + next replay are explicit navigation actions and pause at the context start. Ordinary Save review leaves playback unchanged. Manual start/end marking, role selection, edit/delete/undo and full-half controls remain available.

Unsaved candidate selections/bounds are retained in the browser tab's session storage per match/reviewer/candidate. Reload restores the queue without seeking to a draft. Saved reviews load for the entered reviewer. Finish or cancel a manual pressure draft before saving a funnel review.

## Pools and checks for misses

- **Pressure + pressing candidates:** the main shortlist; provider proposals, not certified pressure.
- **All engagement types:** adds counterpress, recovery and other engagements for comparison. These are not automatically eligible for the current scope.
- **Saved pressure examples:** active manually marked events from all reviewers, retaining source IDs and original scope metadata. No old tactical labels are imported as new funnel decisions.
- **Outside-candidate windows:** systematic ten-second windows with no overlap with the main shortlist, throughout both halves. Use them to look for missed pressure. They are not prelabelled negatives. This diagnostic sample does not cover every noncandidate frame.

The queue reports how many active saved examples have any temporal overlap with a main candidate. It includes all reviewers and uses inclusive interval overlap within a half. Several candidates can overlap one manual example, and overlap can be slight. This does not establish matching timing/scope/meaning or full-match recall. Inspect the saved-examples pool for disagreements.

## Episode construction

Version `engagement-candidates-1.0` uses existing audited local Dynamic Events. It groups overlapping same-team engagements within a half. The default gap is zero native frames; changing the configurable grouping policy changes candidate identity. Grouping breaks at interruption/attacking-team-change boundaries and missing source frames. A single source engagement can itself cross a questionable boundary; these proposals remain visible with a flag rather than being presented as repaired ground truth. Source engagements, defenders, carrier nominees, labels and original bounds remain inspectable. Invalid or unresolved source bounds/actors are omitted and counted in queue diagnostics.

The initial protocol avoids guessed distance/speed thresholds, success/outcome filters and overall-pressure-band filtering. SkillCorner overall pressure includes passing-option ease, risking selection for the construct subsequently reviewed. No equivalence is assumed between provider `counter_press`/`recovery_press` and the owner's excluded represses/fast breaks. Scope still requires reviewer judgement.

Unknown tracking carriers, extrapolated positions and event disagreements remain visible in the existing replay. Proposed boundaries/actors have not been independently validated. Candidate-conditioned funnel labels describe the selected sample and do not establish tactical intention or full-match prevalence.

## Storage and verification

`.presslens/candidate_reviews.jsonl` stores append-only candidate-review revisions separately from pressure markers and legacy detailed annotations. Records retain original/reviewed cases, grouping identity, scope, decision, source/implementation/configuration hashes, interval quality and replay exposure. Stale revisions are rejected. Download review history includes `candidate_review_revisions` alongside older histories.

Software checks: `python -m unittest discover -s tests` (44 tests passed). Browser checks: `python scripts/qa_candidate_review.py`, `python scripts/qa_press_marker.py`, `python scripts/qa_replay_current.py` with Playwright/Chrome available. Browser QA uses temporary logs and verifies human files remain unchanged. `python scripts/audit_pressure_candidates.py` reports counts and saved-example overlaps without writing annotations.

Sources and preimplementation findings: `reports/pressure_candidate_workflow_proposal.md`. Current evidence: `reports/candidate_review_verification.json` and `reports/pressure_candidate_audit.json`. Software success is not tactical validation.
