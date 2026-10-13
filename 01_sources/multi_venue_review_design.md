# Multi-venue review design

Research checked on **2026-10-13**. This note separates official guidance from our design choices. Profiles are pinned to a year; they are not automatically updated when a conference changes its instructions. Scope: main research tracks, not workshops, datasets tracks or ICML position papers.

## What the sources establish

| Profile | Primary evidence | Consequence for the harness |
|---|---|---|
| ICLR 2027 | [Reviewer guidelines](https://iclr.cc/Conferences/2027/ReviewerGuidelines): emphasize new knowledge, substantive scientific judgement and decision-relevant feedback. | Mechanism, empirical reliability, mathematical understanding and knowledge/scope lenses. The numeric recommendation is **harness-defined**, because a complete official 2027 rating legend was not verified. |
| ICML 2026 | [Reviewer instructions](https://icml.cc/Conferences/2026/ReviewerInstructions): separate soundness, presentation, significance and originality; publish the dimension and recommendation scales. | Validate four dimensions independently and preserve the six recommendation labels. Avoid treating low significance as proof of technical unsoundness. |
| NeurIPS 2026 | [Reviewer guidelines](https://neurips.cc/Conferences/2026/ReviewerGuidelines) and [main-track handbook](https://neurips.cc/Conferences/2026/MainTrackHandbook): evaluate five contribution types with type-sensitive criteria. | Route declared types to appropriate specialists. Preserve the four dimensions and six recommendation labels. |

The two six-point recommendation scales differ: ICML uses **Weak Reject / Weak Accept** at 3/4; NeurIPS uses **Borderline Reject / Borderline Accept**. Neither is the repository's older `six_level` profile. Never pool these scales or silently convert them.

Submission layout is separate from scientific quality. [ICML author instructions](https://icml.cc/Conferences/2026/AuthorInstructions) supply the eight-page submission budget; the NeurIPS handbook supplies nine. Exclusions and submission versus camera-ready stages matter. The ICLR 2027 budget remains an explicit author-constraint check rather than inheriting CVPR's eight pages. The older [ICLR 2026 author guide](https://iclr.cc/Conferences/2026/AuthorGuide) contains inconsistent page-limit wording across sections, so it is not used to infer the next year's limit.

ICLR's contemporaneous-work rule distinguishes publication status as well as date. Its profile records the 2027 guidance rather than importing CVPR's cutoff. ICML and NeurIPS profiles assume no universal date boundary; a novelty objection still needs a verified comparison, publication context and scientific relevance.

## Observations that shaped the design

The worked review examples in the [ICLR 2026 reviewer guide](https://iclr.cc/Conferences/2026/ReviewerGuide) illustrate useful scrutiny of assumptions and experimental comparisons. They are examples, not a representative sample from which to estimate reviewer prevalence.

[Insights from the ICLR Peer Review and Rebuttal Process](https://arxiv.org/abs/2511.15462) analyzes ICLR 2024–25 reviews and rebuttals. Its abstract reports associations between initial/co-reviewer scores and later changes. That is observational evidence, not a causal guarantee that a particular revision improves acceptance odds. Our own-thread isolation and independent retests are design safeguards, not a validated reproduction of the study.

The existing `real_review_patterns.md` examines **184 reviews of computer-vision papers** at ICLR/NeurIPS. It does not establish the distribution of all reviewers at those venues. Accordingly, the new I/M/N personas have no claimed empirical prevalence, no estimated harshness offsets and no acceptance quota. Their panels are curated, fixed sets; `--seed` does not randomize those sets.

## Original harness design

**A persona is an emphasis, not a verdict.** New cards ask different scientific questions while sharing the same standards of evidence. A theory specialist can recommend acceptance; a practical reviewer can find a decisive flaw. None must manufacture criticism to stay in character.

**Careful reading leaves an audit trail.** Reviewers map central claims to proof steps, tables, controls or other evidence, inspect relevant appendices, and record unchecked material. Structural validation requires an audit but cannot establish whether an agent actually read a proof correctly. The orchestrator must inspect the evidence and acknowledge unresolved coverage before reporting a confident conclusion.

**No paper genre gets a universal experiment checklist.** Missing evidence matters when it is needed for a claim already made. An additional task, dataset or seed is a justified request only when its scientific purpose is explained. Section rubrics are aids; contribution-sensitive guidance governs their application.

**A full view is permission to read, not proof of coverage.** Extraction may omit equations, merge columns or misidentify sections. Reviewers must check the PDF and mark inaccessible content. A numerical section score is an assessment with limitations, not a certificate of complete verification.

**Sessions preserve the instruments.** Newly created sessions embed persona cards/metadata, protocol/template/domain text, section assignments, resolved scales, criteria, taxonomy and venue settings. Later rounds use those copies. Old sessions retain the legacy fallback; they are not retroactively frozen. The Python implementation itself is not embedded: record the repository commit for reproducibility and start a new session when changing the evaluation design.

**Draft revision is author preparation.** The dialogue loop permits a new PDF and tracks whether concerns were resolved. It does not reproduce every venue's rebuttal rules; in particular, NeurIPS 2026 does not accept a revised submission PDF during rebuttal. These are simulated reviews for improving a draft, not official reviews or acceptance forecasts.

## Inspect or extend the implementation

- Profiles and policies: [`venues.json`](../02_protocol/venues.json) and the adjacent `*_venue.md` files.
- Careful read: [`careful_review.md`](../02_protocol/careful_review.md) and [`evidence_audit.md`](../05_templates/evidence_audit.md).
- Personas: [`personas.json`](../03_personas/personas.json); I01–I04, M01–M04, N01–N06.
- Panels: [`iclr.json`](../04_panels/iclr.json), [`icml.json`](../04_panels/icml.json), [`neurips.json`](../04_panels/neurips.json).
- Verification: `python 06_scripts/smoke_test.py` and `python 06_scripts/test_venues.py`.

Before adding a year or track, verify its form and criteria, record uncertainty, add a distinct profile if semantics change, and test routing, scoring and subsequent rounds. Do not silently map an unknown year to a familiar one.
