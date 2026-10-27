# Phase 0 execution and validation

Executed 26 October 2026 from the repository root using `C:/Users/PC/.local/bin/python3.14.exe` (Python 3.14.5).

Commands completed successfully:

```text
python scripts/audit_phase0.py
python scripts/audit_phase0_details.py
python scripts/audit_event_semantics.py
python scripts/report_phase0.py
python -m unittest discover -s tests -v
git diff --check
```

Two synthetic software tests passed. They check unknown/nonfinite coordinates, detected versus extrapolated carriers, valid clock increments, and rejection of mismatched event periods. Synthetic fixtures are not empirical football evidence.

Additional assertions passed against the generated artifacts: 20 match results; carrier and ball frame categories sum to their recorded denominators; all event rows have both frame endpoints found; both pose hashes match the local manifest; pose schema summaries contain integer counts rather than raw joint coordinates; all 17,400 engagement start clocks match frame_physical_start; unknown source quarantine is empty and analytical/publication permission gates remain disabled.

The detailed route pass was rerun after verification caught a schema-summary implementation error that retained joint values rather than counting field names. The corrected reports contain field counts only. No raw joint records were committed or published.

The original protocols, match files and historical outputs were preserved. Only scripts, tests and reports were added. No package install, Git commit, push or public export was performed.

These checks support audit implementation and recorded arithmetic. They do not establish tactical validity, pose accuracy, complete sequence eligibility, redistribution permission or a clean installation of the eventual application.
