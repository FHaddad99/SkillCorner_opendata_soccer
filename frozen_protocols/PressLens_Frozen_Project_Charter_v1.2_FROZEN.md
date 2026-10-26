# PressLens — Frozen Project Charter

**Document type:** Stable governing framework  
**Version:** 1.2 (approved amendment to the formally frozen charter)  
**Established:** 26 October 2026  
**Status:** **FROZEN / FORMALLY APPROVED**; v1.2 amendments explicitly directed by the project owner on 26 October 2026. Further foundational changes require an explicit, recorded charter revision  
**Companion:** `PressLens_Living_Technical_Framework_v0.2.md`

> **How to use these two documents:** This charter governs *why* PressLens exists, what it may claim, and which constraints it must satisfy. The living framework governs *how* the tool is currently designed and built. Do not treat an initial algorithm, metric list, user-interface concept, or implementation plan as permanently fixed.

## 1. Identity and purpose

**Working project name:** PressLens — Dynamic Pressing, Press-Trigger, and Funneling Analysis.

**Mission:** Create an interpretable, reproducible, open-source analytical tool that uses permitted SkillCorner soccer tracking and event data to identify, inspect, and visually explain candidate pressing situations, observable cues associated with pressing, directional suppression/funneling, the role of supporting defenders, and subsequent attacking responses.

**Intended users:** Performance analysts, coaches, tactical researchers, and the open-source soccer analytics community.

**Persistent user problem:** Ordinary event counts such as pressures, tackles, and turnovers often do not explain the evolving interaction between defenders and the attacking options they constrain. PressLens seeks to make those interactions inspectable in a pitch-centered, time-resolved representation.

**Core footballing lens (an organizing principle, not a universal empirical theorem):** Defending can influence attacking behaviour by restricting *options*, *time*, and *space*. Coordinated funneling is one tactical mechanism through which defenders may shape the attacker's available directions and actions. Whether any detected example is effective is an empirical or coaching-evaluation question, not a given.

**Core product promise:** Show **what was observed**, **what the current method estimates**, **which choices appeared constrained or available**, **how the configuration developed**, and **what the attack actually did afterward**.

**Durable development philosophy:** Expert football observation informs the first operational concepts; documented data and methodological tests determine whether those concepts can be measured. Implementation, empirical inspection and independent evaluation iteratively shape the living methods. Neither the current metric list nor the first detector is frozen. Preserving methodological flexibility does **not** permit shifting the evaluation target after inspecting held-out results without disclosure.

## 2. Stable scope boundaries

PressLens is an **applied tactical analytics and visualization tool**, supported by transparent measurements, empirical evaluation, and reusable software. It is *not required* to be a journal-style hypothesis-driven scientific paper, an entirely new pitch-control model, or a production live-match service.

The tool should remain capable of addressing these enduring football questions even as functionality evolves:

1. Where and when do candidate pressing situations appear?
2. Which observable preceding cues could be relevant to pressure initiation?
3. How does the defensive unit change the ball carrier's accessible passing and carrying directions, time, and space?
4. Do positions and movements of secondary defenders plausibly support a directional funnel?
5. How does the attacking team respond, and how does the sequence resolve?
6. Which observable candidate cues precede pressing responses, and what coordinated movements distinguish a response from an ordinary defensive adjustment?
7. Where measurable, how does primary pressure interact with secondary route coverage and local defending structure?

These are **domains to support**, not a frozen list of specific metrics, thresholds, labels, or features. A future version may measure them more accurately, add dimensions, remove weak metrics, or offer alternative representations.

## 3. Non-negotiable competition and data compliance

The following reflects the competition requirements **provided by the project owner**. If the organizers clarify or amend their rules, the official rules take precedence; record the change rather than silently contradicting them.

### 3.1 Eligible data only

- Use **only SkillCorner datasets expressly supplied or permitted for the current and/or prior Analytics Cups** for all empirical computation, fitting/calibration, analysis, evaluation, and match-derived demonstration material.
- Do **not** introduce external football match data, tracking/event files, match video, third-party scouting labels, or model weights trained on impermissible football data. Published methods and appropriately licensed software may be used without importing their research datasets.
- Do not assume that additional finalist-only data are available. Use those data only if actually provided under the applicable competition conditions and EULA.
- Synthetic geometries and fabricated fixture records may be used as clearly identified **software unit tests only**. They cannot be presented as observed football evidence.
- Raw competition datasets must not be committed to the public submission repository. Handle derived assets in accordance with the applicable dataset licence/EULA; do not assume every reconstruction or animation is freely redistributable.
- Maintain a machine-readable, explicit data-source allowlist and provenance manifest. Unknown or unapproved input sources must fail closed rather than being silently incorporated.

### 3.2 Original work and intellectual property

- Produce **substantial new work created specifically for the Analytics Cup**, in detection logic, analytical integration, tactical representations, validation, visualization, software, or another defensible contribution.
- Reused libraries, open-source algorithms, frameworks, snippets, and pretrained *generic* utilities must have compatible licences and explicit attribution. Do not merely resubmit a previously completed project or lightly adapt it.
- Respect ownership and third-party permission requirements; do not include proprietary employer, club, university, or other restricted materials.
- The submitted work must remain available under an open-source licence in perpetuity, per the provided rules. A permitted licence (e.g. MIT or Apache-2.0) and a `LICENSE.md` file are required.

### 3.3 Reproducibility and deliverables

- The submitted code and analysis must run **without proprietary software** (no mandatory Excel, Tableau, Power BI, closed paid APIs, or private credentials).
- Publish a public GitHub repository containing the code and other permitted resources needed to reproduce the submission, **excluding the restricted data**. Instructions must make the permitted data-acquisition or local-data-placement step explicit.
- Provide an executable, documented clean-environment workflow with pinned/controlled dependencies, tests, and actionable failure messages. Do not claim it works out of the box until tested in a clean environment.
- Submit a personally voiced/presented YouTube elevator-pitch video of **no more than 60 seconds**.
- Keep the **submission `README.md` at or under 1,000 words**, with **no more than two combined figures and/or tables**. Longer technical documentation belongs in separate `docs/` files.
- Meet the organizer's official submission deadline and other current conditions. Deadline dates are **not hardcoded into analytical logic**; reconfirm them before final submission.
- Follow the competition code of conduct and avoid misleading or false information in submission material.

### 3.4 Comprehensive resource use, with strict data separation

- **Systematically inventory the entire competition-permitted SkillCorner resource set** before selecting or rejecting data inputs: current-Cup and eligible prior-Cup datasets, full-match XY tracking, event and possession data, Phases of Play, provider-calculated metrics, body pose where supplied, physical/aggregated data where supplied, metadata, schemas, glossaries, release notes, examples, notebooks, tutorials, and official technical documentation. This inventory is a discovery obligation, **not a requirement to force every data type into every feature**.
- **Use each relevant, technically suitable resource to its full defensible potential.** For a resource not integrated into a particular method, document whether it is irrelevant, redundant, unreliable, unavailable, restricted, or deferred. Revisit those decisions when a limitation or new feature creates a reason to do so.
- **Consult SkillCorner's external references and third-party resources** when relevant: linked methodological papers, public technical guidance, open-source libraries and examples, research implementations, and relevant domain expertise. Follow references to their original sources where possible rather than treating provider links or summaries as proof that a method or claim is valid.
- **Maintain a strict distinction between resources used for knowledge or software and resources used as empirical data.** Reading external papers, documentation, code, algorithms, and licence-compatible general-purpose tools is permitted. Ingesting additional football tracking, event datasets, match footage, scouting labels, annotated clips, fitted football-model weights, or other disallowed observational/training material into the Cup project is **not permitted**, regardless of whether it is openly accessible or linked from SkillCorner materials. Verify ambiguous cases against official competition rules before use.
- **Log resource provenance and licensing** in the living development records: provider or author, exact title/resource, stable URL or repository and version when available, access/review date, licence/usage restriction, the methodological relevance, and whether anything was incorporated into code, data, models, or outputs. Do not redistribute source data or other assets merely because the documentation links to them.
- **Keep the resource inventory and research/reference register up to date throughout development.** The obligation to consult, evaluate, and disclose resources is frozen; the lists of actual resources, preferred libraries, metrics, and integrations are deliberately variable.

## 4. Scientific and interpretive integrity

These safeguards do not change when the algorithms do.

1. **Separate evidence types.** Distinguish (a) observed tracking/events, (b) provider-generated estimates/labels, (c) our calculated heuristic/model outputs, (d) human tactical annotations, and (e) subsequent observed outcomes.
2. **Do not overclaim intention.** Tracking can identify *patterns consistent with* pressing or funneling; it cannot establish private team instructions or deliberate intent. Use `candidate`, `consistent with`, or equivalent phrasing where appropriate.
3. **Do not overclaim causality.** A detected funnel that precedes a turnover does not prove that the funnel caused the turnover. Report associations and sequences faithfully.
4. **Do not invent probabilities or evidence.** A normalized geometric accessibility score is not a calibrated pass-completion or turnover probability. No fabricated matches, metrics, accuracy, p-values, source citations, or successful validation results.
5. **Detect separately from outcomes.** Never define candidate press/funnel detection using the later result and then treat those same outcomes as independent proof of success. Preserve temporal ordering and label hindsight-derived features.
6. **Respect data quality.** Missing, extrapolated, mistimed, or uncertain player positions must propagate quality flags. The tool must abstain or expose uncertainty instead of showing false precision.
7. **Validate claims appropriate to their strength.** Software correctness requires tests; detection validity requires independently reviewed cases or defensible benchmarks; probabilistic accuracy requires calibration; broad effectiveness claims require appropriate empirical design. Human labels are operational reference judgements—not incontrovertible proof of intention.
8. **Keep development and evaluation evidence separate.** Analyst-labelled examples may guide detector construction. Reserve untouched matches/sequences for evaluation where feasible; avoid adjacent-frame leakage; disclose when sample limits make truly independent assessment impossible. If evaluation labels are reviewed after seeing results, disclose the exploratory status of subsequent changes.
9. **Maintain traceability.** Every key metric and classification needs a definition, units or scale, input provenance, software/configuration version, assumptions, and relevant uncertainty notes.
10. **Report failure as a result.** Ambiguous cases, detector errors, negative findings, and insufficient data must be visible rather than discarded to create a compelling presentation.
11. **Do not equate modelled positional contribution with causal responsibility.** Counterfactual spatial scores and simulated removal of a defender describe a defined model; they are not proof that one player caused a later turnover.
12. **Keep trigger language honest.** A backward pass, wide reception, or observed coordinated movement may be a *candidate cue* or an associated response; the data do not directly reveal a team's tactical trigger instructions.

### 4.1 Permanent anti-fabrication and research-quality protocol

**This protocol applies to humans and coding/AI assistants alike.** Scientific-sounding prose, plausible citations, generated analyses, or elegant figures are never evidence by themselves.

1. **Verify bibliographic identity before citing.** Confirm the existence of each cited paper or resource using the original publisher, journal, conference, institutional repository, author-maintained manuscript, or authoritative bibliographic index as appropriate. Verify the **exact title, author names, publication year, venue, DOI or persistent identifier, and publication status**. Never generate a DOI, author list, or citation from a plausible title or an AI recollection. If it cannot be verified, mark it **unverified and do not use it as substantiation**.
2. **Read enough of the underlying source to verify the actual claim.** A title, search snippet, abstract alone, or second-hand summary is not sufficient to assert a specific experiment, method, equation, dataset size, performance result, or limitation that it does not explicitly support. Distinguish what the paper actually tested from our extrapolations and proposed adaptations.
3. **No fabricated results or numerical precision.** Never invent match counts, sample sizes, annotations, model performance, thresholds validated in practice, statistical tests, effect sizes, confidence intervals, p-values, or findings. Each reported figure must be traceable to an inspected source, recorded permitted-data computation, or clearly labelled illustrative/synthetic example. Preserve denominators, units, analysis population, and relevant uncertainty.
4. **Apply critical appraisal, not citation accumulation.** Consider whether a source is peer reviewed, a preprint, conference presentation, vendor white paper, software documentation, or a blog; distinguish these types explicitly. Examine study design, sample representativeness, appropriate controls, measurement quality, evaluation leakage, limitations, evidence of retraction/correction when material, and reproducibility. Do not treat a large bibliography, confident academic tone, or AI-generated text as scientific credibility.
5. **Prefer primary and reproducible evidence.** When possible, consult the published paper and its actual supplementary materials or accessible code, check the assumptions behind methods proposed for reuse, and record what has and has not been independently reproduced. Do not imply independent validation when only authors' reported results were inspected.
6. **Consult relevant empirical research throughout the build.** Perform targeted literature and existing-tool reviews at consequential development points: before adopting or replacing an analytical model, when encountering a substantive technical limitation, when proposing a new metric or pressing/funneling construct, when designing validation, and before finalizing claims or competition submission. Consult SkillCorner documentation again when its definitions or release capabilities affect those decisions. This is a recurring evidence practice, **not a one-time prefatory review**.
7. **Maintain an auditable evidence register.** For material outside claims and borrowed methods, record source identity and link, verification status/date, the exact claim or component it supports, page/section or code reference when available, source type, limitations, and any adaptation made for PressLens. Include a separate list of unresolved or rejected citations/claims. Record the calculation or test that supports each original empirical result.
8. **Make uncertainty and gaps visible.** State when the full paper, relevant source code, raw permitted match frames, provider definition, or data needed to validate a claim could not be accessed. Do not fill missing evidence with a plausible story. If reliable evidence conflicts, report the disagreement and its implications instead of inventing consensus.
9. **Correct transparently.** When a citation, source interpretation, computation, model evaluation, or data provenance is found to be wrong, correct the affected claim and downstream analyses, preserve the change record, and rerun relevant checks. Never quietly replace a fabricated number or invalid citation with another unsupported one.

**Source-use distinction:** Published studies using external football datasets can inform the *design* of PressLens, subject to source-quality review; they cannot authorize importing those datasets, labels, match videos, or impermissibly trained football-model weights into the Analytics Cup build.

## 5. Product integrity and user experience principles

- The central interface is **pitch-oriented, time-aware, and explainable**: users can connect a metric or label to observed player positions and movements.
- Visual clarity must never override factual correctness; use distinctive visual styles for observed paths, hypothetical routes, estimated accessibility, uncertainty, and post-event outcomes.
- **“Live” means frame-synchronized updating during replay of the permitted historical data**, unless a separately authorized future product explicitly supports genuine live feeds. Do not market the Cup submission as live-match streaming.
- A specialized and credible account of pressing/funneling is preferred over a broad but shallow analytics dashboard.
- New metrics, categories, detectors, overlays, comparisons, and reports are welcome when they support the mission and survive suitable evaluation; **there is no frozen feature ceiling**.
- **Analyst-guided observation and review are legitimate inputs** to method development. Keep human annotations, provider outputs, model inferences and later outcome labels visually and programmatically distinct. A manual tactical label may describe a candidate funnel but cannot establish private tactical intent.
- Give priority to added practical value against existing pressure metrics, pressing-chain labels, pitch-control replay, and published press-trap tools. Do not claim that pressing detection or tactical visualization is itself novel.
- Prioritize accessibility to coaches and analysts alongside usability for developers: interpretability, understandable legends/labels, reproducible exports, and inspectable parameters.

## 6. Governance: what is frozen and what is not

### Frozen under this charter

- Competition and data-eligibility commitments.
- The enduring footballing lens and project mission.
- Integrity, uncertainty, licensing, reproducibility, and evidence-provenance requirements.
- The requirement that the tool communicates observable defensive–attacking interactions, not imagined intentions or causal certainties.
- The **expert-guided, evidence-driven development principle**: examine football sequences, operationalize tactical constructs, test them and revise methods with an audit trail.
- The **independent-evaluation principle**: distinguish exploratory/training labels and thresholds from the evidence used to support final performance claims.
- The **prior-art and value principle**: explicitly compare relevant existing tools/methods and substantiate the contribution instead of asserting first-of-kind novelty.
- The **comprehensive-resource principle**: systematically review the permitted SkillCorner data and documentation, relevant SkillCorner-linked/third-party resources, and document purposeful use or justified exclusion without relaxing data eligibility.
- The **continuous empirical-research and anti-fabrication principles**: revisit verified relevant literature throughout development; verify bibliographic and numerical claims at the source; reject invented citations, statistics, unsupported methodologies, and uncritical low-quality research.

### Deliberately *not* frozen

- Metric inventory, formulas, weights, thresholds, time windows, feature priorities.
- Exact trigger/press/funnel definitions and state machines.
- Algorithms, libraries, architectures, layouts, chart designs, exports.
- MVP feature list, performance targets, schedule, milestone order, and optional investigations.
- Which previously proposed hypotheses are analyzed, deferred, or removed.
- Exact annotation interface, taxonomy, annotation sampling, inter-rater workflow, evaluation split design, pose features, route model and attribution method (subject to the principles above).
- The current resource inventory, empirical papers reviewed, tool/library choices, evidence-register contents, and specific research questions prioritized (while the requirements to maintain and verify them remain fixed).

### Change control

- **Living-framework changes:** make a versioned edit, explain why, note impact on metrics/tests and whether old outputs remain comparable. No charter amendment is needed.
- **Charter changes:** require an explicit decision by the project owner, a new charter version, a written rationale, and an audit of competition compliance. The original is retained for traceability.
- **Rule changes:** update the compliance interpretation promptly to remain eligible; identify the external requirement that changed and synchronize both documents.
- **Release reproducibility:** although exploratory development stays flexible, the submitted release must pin code, data manifest, configurations, and measured results so that its demonstration can be reproduced exactly.

## 7. Interpretation hierarchy when documents conflict

1. Organizer's official current rules and applicable dataset EULA.
2. This **Frozen Project Charter** (latest explicitly approved version).
3. The **Living Technical Framework** (latest version).
4. Historical project specifications, informal notes, and coding-agent suggestions.

Older documents remain useful references, but they do **not** freeze implementation details. In particular, `PressLens_Analytics_Cup_Project_Specification.md` is an earlier proposed design and is subordinate to this charter and the current living framework.

## 8. Stable definition of success

PressLens succeeds as a competition project when it delivers **substantial original, lawful, reproducible and intelligible functionality** for exploring pressing and funnel-like constraints in the permitted SkillCorner data, with clear limits on what its outputs mean. Success does **not** depend on discovering a universal defensive law, proving a causal effect, using the most sophisticated model, or shipping every initially imagined metric.

---

**Formal approval record**  
Project owner approval/date: **v1.1 explicitly approved and v1.2 changes directly requested in the project conversation, 26 October 2026** (not a signed legal document).  
Change record:
- `v1.0 (candidate)` — First draft of the stable charter; approval previously pending.
- `v1.1 (FROZEN)` — Formally approved; incorporated expert-guided observation, separation of development and held-out evaluation, explicit evidence provenance for human labels, and an originality/value-comparison obligation. No additional datasets or competition exemptions authorized.
- `v1.2 (FROZEN)` — Owner-directed revision adds comprehensive appraisal of permitted SkillCorner data, documentation and linked third-party resources; recurring empirical-method review; mandatory source verification, numerical traceability, critical appraisal, evidence logs, and transparent correction. Reaffirmed that external resources may inform methods but cannot supply impermissible football data or weights.

**Next permitted changes:** Only via an explicit project-owner charter-revision decision or an overriding change in organizer requirements. The living technical framework may continue to evolve without amendment to this charter.
