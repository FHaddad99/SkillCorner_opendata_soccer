# Press-event marking increment

The owner requested a focused first pass with the exact existing replay functions retained: one start/end ticker, a clicked primary presser and clicked secondary/supporting defenders. Further analytical measures will be built afterward.

The default UI is now this marker. The broader multi-question/queue prototype was replaced before handoff; its historical `focused_review_verification.json` is not evidence for the current UI. The underlying independent-review/sequence-ID storage remains reusable for a future measure, without exposing those additional questions now.

Replay preservation: no clip playback boundary, auto-loop, auto-seek, forced pause or automatic half navigation was added. The existing full-half player remains in control. Player role outlines are annotations only; native positions and detection/extrapolation styles remain distinct. The marker captures exact native start/end and click frames, validates same-half and same-team roles, and leaves an unselected primary explicitly unknown.

Events append to `pass_reviews.jsonl`; intervals append to `review_sequences.jsonl`, under ignored `.presslens/`. Detailed schema-1/schema-2 human annotations remain untouched. New records retain source hashes, reviewer, quality and implementation/configuration provenance, and stable sequence IDs for later joins. No unmarked frame is labelled negative and no funnel/trigger classification is generated.

Validation: 26 isolated standard-library software tests passed. `qa_press_marker.py` passed actual canvas-click, start/end, persistence, cross-half, and playback-continuation checks on installed Chrome. `qa_phase1_browser.py` and `qa_annotation_refinements.py` also passed against the new build. Automated events were stored only in temporary files and removed. The original human annotation file retained SHA256 `d226e40eb7c06004e93d26b51f886d8a7dee52ff34112aed28648a589d0464d5`.

Software version 0.4.0; marker record schema press-marker-1.0; marker review protocol 3.1. Current runtime verification is `press_marker_verification.json`. The living framework v0.5 records the simplified first-pass priority. No frozen charter revision, public deployment, data publication, new football dataset or automatic detector was introduced.
