# Phase 1 verification record

Date: 26 October 2026. User story: choose an audited match → inspect native tracking in a local browser → record an observation → separately review outcomes → reopen the persistent revision history.

| Boundary | Result | Evidence |
|---|---|---|
| Local runtime and UI | Passed | Standard-library server plus local HTML/JS/CSS; desktop and 390px mobile browser screenshots in ignored `.presslens/qa/`. No browser errors in the completed flow. |
| Input access | Passed for local review | All 20 matches loaded; 80 source hashes verified against the Phase 0 manifest. Release/redistribution eligibility remains unresolved. |
| Native frame delivery | Passed sampled checks | First/last native frames of both periods for every match: 80 records. Exact source IDs and period values retained; no interpolated positions. `phase1_validation.json` records per-match checks and runtime implementation/config hashes. |
| Raw data → conflict display | Passed | Actual match 1874553: frame 8958 shows B. Vriends versus B. Halloran; frame 6732 shows event versus phase team disagreement. |
| Browser playback | Passed | Native playback advanced; previous/next frame controls and half selection updated the cursor and canvas. |
| Observation → local persistence | Passed | Browser filled and saved a test observation at frame 6732; source context and provenance were recorded. The test used a separate temporary annotation log. |
| Outcome separation | Passed | Optional provider outcome labels required explicit reveal; separate save created revision 2 with exposure disclosure. Default observation responses exclude end-type, pass-outcome and match-score fields. |
| Persistence → reopened UI | Passed | Page reload, saved-history reveal and opening the annotation restored revision 2. |
| Failure cases | Passed software tests | Changed source hashes, unknown match IDs, cross-period intervals, wrong-team roles, stale base revisions and unapproved-origin writes were rejected. Missing frame slots remained missing. |
| Tactical validity / human reference labels | Pending | No human labels, reviewer agreement or automatic detector validity were invented. |

Executed checks:

```text
python -I -S -m unittest discover -s tests -v
python scripts/verify_phase1_inputs.py
python scripts/qa_phase1_browser.py
git diff --check
```

The isolated test run used Python 3.14.5 and passed ten tests with third-party packages disabled. Browser QA used a pre-existing Playwright installation in another local Python environment and the installed Chrome executable; neither is needed to run the viewer. This is not a clean installation test of the larger upstream notebook dependency set.

Browser QA initial attempts exposed a Python-version compatibility assumption in the new file-hashing code and an incompatibility between the installed browser driver polling helper and the application's content security policy. Hashing now uses a standard chunked digest; browser checks use locator assertions without relaxing the application policy. Subsequent browser runs passed. Aborted navigation requests are handled without trying to send a second response.

Automated UI annotations were explicitly marked as software verification and removed with their temporary log. The real `.presslens/annotations.jsonl` did not exist at verification completion. No raw records, derived replay assets or screenshots were committed or published.

The original frozen charter, living framework v0.2, source data and historical outputs were preserved. New v0.3 records the implementation and remaining human-review/eligibility gates.

The initial PowerShell launcher was blocked by this machine's execution policy. It was replaced with `start_presslens.cmd`; no execution policy was changed. The replacement launcher started the local server successfully.
