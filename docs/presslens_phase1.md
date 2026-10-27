# PressLens local review workspace

Current software: v0.7.0. Start with [pressure candidates and funnel review](pressure_candidate_review.md) to review proposed episodes without manually marking every pressure event. The [simple press-event marker](press_event_marking.md) remains available for missed events and primary/supporting nominations. Markers can be edited, deleted and restored with Undo. The Detailed Annotation tab and form remain removed; existing records are preserved in the review-history download.

## Start

From the repository root on this Windows machine:

```powershell
.\start_presslens.cmd
```

Open **http://127.0.0.1:8765**. Leave the terminal running and use Ctrl+C to stop. On another machine with Python 3.11+, run `python scripts/run_presslens.py`. No third-party Python packages, Node, remote assets or proprietary runtime are required.

The input files must match `reports/eligibility_manifest.json`; configuration is `config/presslens_review.json`. The application reads local native tracking records, with no interpolated players or automatic carrier inference. Full-half playback, frame steps, scrubber, speeds and half buttons remain available. Marker actions do not pause or move playback.

## Current annotation scope

Do not mark pressure during counter-attacks or fast breaks, or represses, in this pass. Those situations may be annotated later and remain **deferred/unreviewed**, not negative examples. The scope is reviewer-defined; no automatic phase filter or removal of replay frames is applied. New marker records carry the declared scope; older records are not retroactively reclassified.

Press markers append to ignored `.presslens/pass_reviews.jsonl`; shared intervals are in `.presslens/review_sequences.jsonl`. Previous detailed annotations remain in `.presslens/annotations.jsonl`. Candidate/funnel reviews append separately to `.presslens/candidate_reviews.jsonl`. **Download review history** includes all four histories. Stable event IDs retain edit/delete history; interval IDs identify the exact source/bounds for later measures.

All 20 matches remain development with legacy exploratory exposure. Source-release and redistribution questions from Phase 0 remain open. Local replay and human review do not establish tactical intent, causality, independent validation or permission to publish match-derived assets.

## Verification

`python -m unittest discover -s tests` passed 44 tests. Optional browser QA (requiring an existing Playwright/Chrome setup) uses `scripts/qa_candidate_review.py`, `scripts/qa_press_marker.py` and `scripts/qa_replay_current.py`. Current outputs are `reports/candidate_review_verification.json`, `reports/press_marker_verification.json` and `reports/replay_current_verification.json`. The latter also updates ignored `.presslens/qa/browser-results.json`.

Earlier audit/verification reports and the [historical detailed protocol](annotation_protocol.md) remain available for traceability. Historical detailed-form browser scripts apply to superseded UI versions. Automated QA records use separate temporary logs and are not human tactical annotations. The actual human annotation file remained unchanged.
