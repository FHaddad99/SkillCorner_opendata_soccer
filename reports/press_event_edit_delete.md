# Saved press event editing and deletion

Owner request: edit a saved press event and delete a saved frame/interval. Implemented as Edit and Delete on each saved pressure-event card, plus Undo delete. Source tracking frames and the detailed annotation log are not removed.

Software v0.5.0; marker review protocol 3.2. Editing can change native bounds and primary/support nominations. Every operation appends a revision. Stable event IDs distinguish event identity from interval/sequence identity; resizing replaces the active event rather than leaving two entries. The old sequence is recorded as previous_sequence_id when it changes, so future analytical passes are not silently reassigned.

Deleted events are hidden from active/latest and combined results, with deletion state retained separately from the press-positive judgement. Undo restores the most recent deletion in the page session. Existing marker records lacking IDs receive a deterministic lookup ID without modifying historical JSONL lines. Role-click evidence retained across a trimmed boundary stays at its actual source frame and is explicitly flagged when outside the new interval.

Concurrency and validation: stale base revisions, a changed event half, invalid player selections, opposing-team supports, and collisions with another saved interval are rejected. An active draft must be finished/cancelled before another saved event is edited or deleted. Cancelling an edit leaves the saved revision intact.

Validation: 30 isolated software tests passed. Updated marker browser QA edited bounds and roles via actual canvas clicks, verified the stable event ID and changed sequence ID, deleted and restored the event, reloaded it, and confirmed that editing/saving/deleting do not pause or seek full-half playback. Test records lived only in temporary files. Current evidence is `reports/press_marker_verification.json`. The original detailed annotation hash remains `d226e40eb7c06004e93d26b51f886d8a7dee52ff34112aed28648a589d0464d5`.
