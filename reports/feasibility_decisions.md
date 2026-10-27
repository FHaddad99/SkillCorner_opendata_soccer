# Phase 0 feasibility decisions

Date: 26 October 2026. Scope: first framework step only. These are provisional engineering decisions; no frozen charter changes.

| Component | Decision | Evidence and condition |
|---|---|---|
| Local tracking replay and annotation | ADAPT | All 20 local match groups parsed. Distinguish null periods, missing ball/carrier and extrapolated players. Source-release identity is pending before analytical release. |
| Carrier assignment | ADAPT | Sparse tracking carrier plus boundary disagreement prevents simple forward filling. Preserve event and tracking identities separately and abstain on unresolved conflicts. |
| Events and phases | ADAPT | Frames resolve; engagement time_start maps to frame_physical_start, explaining apparent offsets. Phase-team disagreements and tactical onset semantics need review. |
| Attacking direction | SUPPORTED AS PROVIDER CONTEXT | All 80 period/team groups agree with metadata. Event/XY coordinate transformation remains unvalidated. |
| Pass/carry accessibility | DEFER | Start-frame corridor visibility measured; continuous route quality, event-to-XY transforms and models remain unvalidated. No pass-probability claim. |
| Pressure context comparisons | ADAPT | Newer context fields exist only in 16 matches. Preserve separate denominators and boundary timing; they are vendor outputs. |
| Cue/press/funnel classifiers | DEFER | No independently reviewed labels or complete sequence-quality policy. Point-quality counts cannot prove sufficient training/evaluation sample. |
| Velocities/closing speed | DEFER | Regular 10Hz timestamps; raw speed warnings require robust smoothing and segmentation review. |
| Pose orientation | DEFER, optional | Two archive hashes match; bounded identity/XY/joint inspection only. Whole-match alignment and orientation uncertainty remain open. |
| Season physical/OBR/passing aggregates | CONTEXT ONLY | Inventoried; player-season summaries cannot resolve individual frame geometry or onset. |
| External model weights/data/video | EXCLUDE | No new observational sources were ingested. Literature/software review does not grant data permission. |
| Public raw-data release | STOP | Existing tracked datasets conflict with submission exclusion; prepare a separate code-only submission repository. Do not erase this working repository automatically. |
| Derived replay/video publication | UNRESOLVED | Verify licence/EULA for specific assets and release. No public sequence exported. |
| Held-out tactical validation | UNRESOLVED | Legacy P1/P2 outputs cover all matches. Reconstruct prior exposure before declaring any untouched test set. |

The Phase 0 audit execution is complete; its full exit gate remains open. A pending legal/quality check is not a negative finding about the football or an authorization to invent missing labels.

Suggested living-framework v0.3 edits: correct charter link to v1.2; record 20 local event-rich matches and the four older schemas; require event-specific time semantics, sparse-carrier handling and phase-team conflict flags; describe bounded pose verification; record legacy all-match exploratory exposure. Keep proposed detector thresholds provisional. The supplied protocols were preserved for owner review.
