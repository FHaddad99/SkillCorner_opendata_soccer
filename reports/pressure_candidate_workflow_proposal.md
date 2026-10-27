# Proposal: pressure candidates followed by funnel review

Status: researched proposal, not an implemented detector or changed annotation policy.

Implementation follow-up: the owner subsequently authorized this workflow. Software v0.7.0 implements provider-derived candidates and separate funnel reviews; see `docs/pressure_candidate_review.md`, `reports/candidate_review_verification.json` and `reports/pressure_candidate_audit.json`. The proposal below remains as the preimplementation record.

## Local data findings

Read-only CSV enumeration on 2026-10-26 found 20 match event files containing:

| Provider event/subtype | Rows |
| --- | ---: |
| on_ball_engagement / pressure | 4,622 |
| on_ball_engagement / pressing | 3,813 |
| on_ball_engagement / recovery_press | 4,019 |
| on_ball_engagement / counter_press | 1,622 |
| on_ball_engagement / other | 3,324 |

All 17,400 engagement rows have nonempty frame_start, frame_end, player_id and player_in_possession_id. This is field completeness, not timing or actor correctness. There are 18,792 player_possession rows; overall_pressure_start is nonempty in 13,251 and overall_pressure_end in 13,298. Those boundary fields are not continuous pressure measurements. No annotations or source data were changed.

The 8,435 pressure/pressing rows are individual engagements before deduplication, episode grouping, scope review and quality checks. They are not an episode count or a performance result.

## Recommended first prototype

1. Use provider pressure and pressing engagements as the initial candidate stream, retaining exact event IDs, original bounds, actors and provider labels. Use an optional expansion stream for other subtypes and unmatched human examples so the initial filter cannot silently define all pressure.
2. Combine overlapping compatible engagements and test short-gap grouping within a half and consistent defending team. A carrier change may occur within one team pressure episode; record the constituent carrier/engagement segments. Do not merge across stoppages, unobserved gaps or team changes. Pressing-chain IDs are supporting evidence to inspect, not an assumed globally unique or complete episode key. Version all grouping parameters.
3. Display editable proposed bounds and a small configurable amount of preceding/following replay context. Context frames remain separate from event bounds. Candidate navigation is explicit; full-half replay and existing manual marking remain available.
4. Let the reviewer record funnel yes/no/uncertain/unassessable, with unreviewed as the untouched default. Provide a separate action for not pressure or out of current scope. Do not require actor nomination to advance; provider nominees stay distinct from reviewer-confirmed roles.
5. Keep counter-attacks, fast breaks and represses deferred/unreviewed. Provider counter_press or recovery_press labels can help prioritize scope checks, but neither establishes equivalence with the owner's exclusions. Expose filtered/deferred pools and allow recovery of misclassified candidates.
6. Compare candidate coverage and proposed timing against existing human-marked events, accounting for one-to-many matches. Have the reviewer inspect both candidate samples and randomly/stratified sampled noncandidate windows. Report candidate acceptance, missed observed examples, timing disagreements, quality abstentions, and review time. Saved positives alone cannot estimate full-match recall or precision.

## Definition and independence

FIFA describes on-ball pressure as closing the space to the ball carrier, reducing time and options. This is a credible conceptual anchor, but does not supply validated distance/speed/duration thresholds for these files. A custom tracking detector should be a later comparator if provider candidates miss relevant examples. Distance, closing speed, approach geometry and persistence would need calibration; proximity alone should remain a baseline. Retain unknown carrier/quality states rather than interpolating a presumed actor through disagreement.

Pressure candidate generation must not require funneling, a backward pass or a turnover. SkillCorner overall pressure includes passing-option ease, so filtering only on that measure could enrich the sample for option restriction before funnel review. Prefer engagement-based candidates initially and document provider dependencies. A result among these selected candidates describes that sample, not all match pressure.

## Sources

- FIFA, pressure on the ball: https://www.fifatrainingcentre.com/en/fwc2022/efi-metrics/efi-metric--pressure-on-the-ball.php
- SkillCorner, on-ball engagement overview: https://skillcorner.com/articles/gi-oop
- SkillCorner, open-data pressure field documentation: https://skillcorner.github.io/opendata/#pressure-and-difficulty
- SkillCorner, components of overall pressure: https://landing.skillcorner.com/articles/metric-explainer-drawing-pressure

These pages inform definitions only. The proposed prototype uses the existing local permitted match files; no external match data is added.
