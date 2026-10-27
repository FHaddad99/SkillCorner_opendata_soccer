# Current-pass exclusions and removal of Detailed Annotation

Subsequent owner clarification: also exclude represses. Config v3.4 / press-scope-1.1 now lists `counter_attack`, `fast_break` and `repress`, all deferred/unreviewed. The UI and prospective record scope were updated; older scopes and original human annotations are retained unchanged. No automatic definition/detector of repressing was introduced.

Owner instruction: do not mark pressure during counter-attacks or fast breaks in this pass; those events may be reviewed later. Remove the Detailed Annotation tab.

Implemented in software v0.6.0 and config v3.3:

- Declared review scope explicitly excludes `counter_attack` and `fast_break`, with `excluded_handling=deferred_unreviewed`. Identification is the reviewer's judgement. No automated phase filter, event rejection based on provider phase labels, raw-data deletion, or playback skipping was added.
- New marker drafts carry the scope version; saved records carry that declared scope and current policy. Editing/deleting/restoring earlier markers retains their original recorded scope. Legacy/old drafts without scope evidence remain unknown, rather than being relabelled after the fact.
- Removed the detailed tab, form, form-only client handlers and detailed-history editing entry point. Previous detailed records remain in the unchanged JSONL and in **Download review history**, which now bundles press revisions and shared intervals as well. Backend compatibility for historical schemas remains.
- Preserved full halves, native playback, scrubbing, speeds, steps, half switching, detection display, optional provider context, press markers, role clicks, edit/delete/undo and local storage.

Validation: 32 standard-library software tests passed. Marker browser QA passed on desktop/mobile, including scope recording and removal of the form. Replay browser QA passed frame/keyboard stepping, speed/playback, half switching, provider conflicts, extrapolation toggles, and export of the unchanged historical annotation. Verification files: `press_marker_verification.json` and `replay_current_verification.json`. Test data were temporary. The original human annotation SHA256 remains `d226e40eb7c06004e93d26b51f886d8a7dee52ff34112aed28648a589d0464d5`.

Interpretation: deferred or unmarked situations are unreviewed, not negatives. This annotation selection does not establish counter/fast-break pressure rates, population prevalence or independent detector performance. No new tactical threshold, external match data, model, hosting or public data release was introduced.
