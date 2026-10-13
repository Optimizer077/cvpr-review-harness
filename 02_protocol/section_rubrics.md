# Section rubrics

Section scores are a harness addition: the official CVPR form has no per-section scores. They let a
writer agent see where a draft loses reviewers. Score only what you actually read.

**Section score (1-10), anchored on what a reviewer would do:**

| score | meaning |
|---|---|
| 9-10 | You would name this section as a strength; you have nothing to add. |
| 7-8 | Solid. At most a minor comment ("clarify", "typo", "could cite"). |
| 5-6 | Acceptable, but it earns a moderate weakness bullet. It does not decide your rating alone. |
| 3-4 | It earns a major weakness bullet and pulls your rating down by itself. |
| 1-2 | A decisive reason to reject, or the section is missing or broken. |

**Criterion score (1-5):** 1 absent or wrong; 2 weak; 3 adequate; 4 good; 5 exemplary.
A section score of 9+ needs every criterion at 4+; any criterion at 1 caps the section at 4.

For each scored section give `main_issue` (the single thing that costs the most), its `location`
(`L###`, page, Fig./Tab./Eq.), and `one_point_fix` (the change that would raise the score by at
least one point; "none possible by writing" is allowed).

## title
What reviewers check: does the title say what the method is and what it does, without a claim the paper does not support?
- `specific` - names the idea or mechanism, not only the task.
- `accurate` - no word the results do not back ("universal", "any", "optimal").
- `findable` - uses the field's terms, so the right reviewers are matched to it at bidding.

## abstract
What reviewers check: many reviewers decide their prior from the abstract alone; bidding uses it.
- `problem_gap` - the problem and what current methods fail at, in one or two sentences.
- `method_concrete` - one concrete sentence on what the method does differently (mechanism, not adjectives).
- `evidence_specific` - named benchmarks, numbers or scope that back the claim.
- `claim_calibration` - the strength of words matches the evidence (no "significantly" without a test, no "state-of-the-art" if a strong baseline is missing).
- `readability` - an adjacent-area CV reader understands it on first read; no undefined acronyms or private terms.
Typical failures: jargon soup; method described only by adjectives; a list of experiments without a takeaway; numbers without the comparison they refer to.

## introduction
What reviewers check: pages 1-2 and Fig. 1 set the rating prior for most reviewers.
- `motivation_stakes` - why the problem matters to CVPR readers, concretely.
- `gap_precision` - what exactly prior methods cannot do, with citations, stated so it can be checked.
- `insight_why` - the key idea and WHY it should work, before the details.
- `contributions_verifiable` - each listed contribution maps to a section and evidence; no padding.
- `teaser_figure` - Fig. 1 (if present) conveys the idea or the result at a glance.
- `claim_calibration` - claims stay inside what the experiments test.
Typical failures: "A+B" impression because the delta to the closest work is not stated early; contribution bullets that restate the method; motivation that is generic ("INRs are important").

## related_work
What reviewers check: whether the closest work is cited and the difference stated, not merely listed.
- `coverage_recent` - includes the strong recent (last 1-2 years) and directly competing work.
- `positioning_delta` - for the closest works, says how this paper differs and why that matters.
- `fairness_to_prior` - describes prior work accurately and without belittling it.
- `organization` - grouped by idea, not a list of one-line summaries.
Typical failures: missing the one paper the expert reviewer thinks of first; "unlike X, we ..." without saying what X actually does; concurrent work ignored.

## method
What reviewers check: can I reimplement it, is each design choice motivated, is it correct?
- `clarity_reproducible` - enough detail to reimplement from the main paper plus supplement.
- `notation_consistency` - symbols defined once, used consistently, dimensions clear.
- `design_rationale` - each component has a reason (and a pointer to the ablation that tests it).
- `correctness` - equations and claims are right.
- `cost_stated` - parameters, FLOPs, memory or time are stated or pointed to.
Typical failures: a figure that does not match the equations; unexplained hyperparameters; "we found it works better" as the only rationale.

## theory
What reviewers check: is the theory correct, needed, and connected to the empirical claim?
- `correctness` - statements and proofs are right.
- `assumptions_explicit` - assumptions stated and plausible for the setting tested.
- `link_to_claims` - the theory predicts or explains something the experiments then show.
- `nontriviality` - more than a substitution into a known result.
Typical failures: a proposition that restates a definition; theory about an idealized model that the trained network does not satisfy; no experiment testing the prediction.

## experiments
What reviewers check: the main results table first, then the setup.
- `baselines_current_strong` - the strongest recent methods, correctly configured.
- `benchmarks_scale` - standard benchmarks of adequate size and resolution for the claim.
- `fairness_compute_tuning` - matched parameters AND compute/time; baselines tuned as carefully as the method.
- `metrics_appropriate` - metrics fit the claim (perceptual metrics where perception matters, etc.).
- `statistical_reliability` - variance, seeds or per-image spread where the margin is small.
- `result_strength` - the gain is large enough to matter and consistent across settings.
Typical failures: missing the one baseline the reviewer expects; numbers for baselines lower than in their own papers; only small or old datasets; no wall-clock comparison.

## ablations_analysis
What reviewers check: does each component earn its place, and is the claimed mechanism shown?
- `component_isolation` - each component removed or replaced under the same budget.
- `mechanism_evidence` - analysis supports the paper's explanation, not only the final number.
- `failure_cases` - shows where the method does not help.
- `sensitivity` - robustness to key hyperparameters.
Typical failures: ablations only on one image or one setting; "analysis" that is a restatement of results; mechanism claims with only correlational evidence.

## figures_tables
What reviewers check: legibility on paper, captions that stand alone, consistency with the text.
- `readability` - fonts, colours and crops legible in print and for colour-blind readers.
- `captions_self_contained` - a caption says what is shown and what to conclude.
- `text_consistency` - numbers and names in figures/tables match the text.
- `visual_comparisons` - qualitative comparisons are fair (same crops, zoom-ins, not cherry-picked).
Typical failures: tiny fonts; unexplained abbreviations in tables; best-number bolding errors; qualitative crops chosen only where the method wins.

## limitations
What reviewers check: whether the authors know where their method fails.
- `honesty` - real limitations, not disguised strengths.
- `specificity` - concrete failure modes, costs or scopes.
- `scope_alignment` - claims elsewhere stay inside these limits.
Typical failures: none listed; "future work could extend to video" as the only limitation.

## conclusion
- `matches_evidence` - restates only what was shown.
- `no_new_claims` - no claims not tested in the paper.
- `takeaway` - leaves the reader with the one lesson to remember.

## supplementary
What reviewers check (when they open it): details the main paper defers, and whether they hold.
- `completeness_details` - hyperparameters, protocols, extra results that the main paper points to.
- `supports_main_claims` - the deferred evidence actually supports the main-paper statements.
- `navigability` - a reviewer can find the referenced item quickly.

## references
- `accuracy` - correct authors, venues, years; no broken entries.
- `completeness` - every compared or built-upon method is cited.
- `recency` - the bibliography is current for a submission in this review period.
