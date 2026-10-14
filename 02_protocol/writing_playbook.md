# Writing playbook for CV and ML papers

How to write a computer-vision or machine-learning paper that a busy reviewer understands in one
pass and cannot easily misread. The writer uses it for every passage it rewrites; the coach cites
guideline ids (e.g. "A2") in its plan. Every guideline is a check you can run on the draft. A tag
in parentheses names the source (list at the end); counts from 184 real CV reviews come from
`01_sources/real_review_patterns.md`. Examples are generic.

**Fix what reviewers read first.** Most reviewers make one pass over a paper (Keshav 2007), and
they first look at the pictures (Kajiya 1993). Pages 1-2 and Fig. 1 set most reviewers' rating
prior, and the main results table is the first thing they check in the experiments
(`section_rubrics.md`). Start there.

## 0. One central contribution
- **G1.** You can state the contribution in one sentence, and the title, abstract, introduction,
  Fig. 1 and conclusion all state that same one (Mensh & Kording 2017, rule 1; Peyton Jones).
- **G2.** Every claim in the introduction has a forward reference to the section, figure or table
  that supports it (Peyton Jones).

## 1. Title
- **T1.** It names the idea or mechanism, not only the task: "Depth-guided kernels for single-image
  deblurring", not "Towards better deblurring" (Mensh & Kording 2017, rule 1; `section_rubrics.md`).
- **T2.** No word the results do not back: "universal", "any", "optimal", "real-time" without a
  measured frame rate.
- **T3.** It uses the field's standard terms, so bidding matches it to the right reviewers.

## 2. Abstract
Context and gap, then what you did, then the evidence, then a calibrated conclusion (Mensh &
Kording 2017, rule 5; Peyton Jones: the problem, why it is interesting, what the solution
achieves, what follows from it).
- **A1.** The first one or two sentences say what current methods fail at, specifically
  ("instance segmentation methods miss thin structures such as poles and wires"), not that the
  task is important.
- **A2.** One sentence says what the method does differently, as a mechanism a reader could
  sketch ("predicts a per-pixel blur kernel from estimated depth"), not as adjectives ("a novel,
  efficient framework").
- **A3.** The evidence names the benchmarks and gives at least one number with its comparison
  ("+<x> mask AP over <strongest baseline> on <dataset>"); the numbers match the main table.
- **A4.** The verbs match the evidence: "state of the art" only when the strongest recent
  baselines are compared under matched settings; "significantly" only with a test; the scope
  (tasks, data) is stated. Overclaiming separates rejecting from accepting reviews: 42% of
  reject-side vs 19% of accept-side reviews (`real_review_patterns.md`, sec. 2).
- **A5.** It lists only tasks and settings for which the paper shows results.
- **A6.** No undefined acronym or private term; a reader from an adjacent area understands it on
  the first read (Mensh & Kording 2017, rule 2).

## 3. Introduction and Fig. 1
- **I1.** Stakes: the first paragraph names a concrete consequence (a failure case, a cost, a use)
  for the intended community, not "X has attracted increasing attention".
- **I2.** Gap: what exactly prior methods cannot do, with citations, stated so a reader can check
  it ("<cited methods> need hours of per-scene optimisation") (Mensh & Kording 2017, rule 6).
- **I3.** The key insight and why it should work, as intuition, before any detail (Peyton Jones:
  "Conveying the intuition is primary").
- **I4.** What is new and what isn't, up front: one sentence on the difference from the closest
  prior work, named (Kajiya 1993). Without it reviewers read "A + B" (`section_rubrics.md`).
  Novelty is the most frequent complaint in reject-side reviews (64%, vs 24% accept-side), and
  differentiating from the named prior work while rewriting the contributions is the only
  observed way a novelty reject flipped (`real_review_patterns.md`, secs. 2 and 6).
- **I5.** Contributions are a bulleted list of refutable claims, each pointing to the section and
  the table or figure that tests it ("We show that ... (Sec. 4.2, Tab. 3)"). No bullet only
  restates the method's name (Peyton Jones).
- **I6.** Fig. 1 conveys the idea or the headline result at a glance: one message, consistent with
  the abstract, readable at its printed width, with a caption that alone gives the point
  (Kajiya 1993: reviewers "first look at the pictures"; `figure_rubric.md`, role `teaser`).
- **I7.** Skip "the rest of this paper is organized as follows" when space is tight; forward
  references in the narrative do its job (Peyton Jones).

## 4. Related work as positioning
- **R1.** Grouped by idea, with a short paragraph title per group; not one sentence per paper
  (Huang, related-work tips).
- **R2.** Each group ends with how this paper differs and why that matters ("Unlike voxel-based
  reconstruction, we ..."). For the closest work, say what it does, not only that it differs.
- **R3.** It covers the strongest recent method of the same family and the method the paper builds
  on: the works reviewers most often name as missing baselines (`real_review_patterns.md`, sec. 2).
- **R4.** Fair to prior work: accurate and never belittling; giving credit costs nothing
  (Peyton Jones; Huang, related-work tips).

## 5. Method
- **M1.** An overview paragraph and figure come first; the figure uses the equations' symbols and
  maps to the subsections (Huang, writing tips; `figure_rubric.md`, role `method_diagram`).
- **M2.** Every symbol and term is defined once, before its first use, and keeps its meaning; one
  word per concept (Mensh & Kording 2017, rule 2; Gopen & Swan 1990). When a symbol returns after
  a while, give its name too ("the depth confidence c") (Huang, writing tips).
- **M3.** Each design choice gives its reason and points to the ablation that tests it.
- **M4.** Explanation and speculation are kept apart: an intuition no experiment tests is stated
  as a hypothesis (Lipton & Steinhardt 2018).
- **M5.** Mathematics clarifies rather than impresses: every equation is used later, and no
  proposition only restates a definition (Lipton & Steinhardt 2018; `section_rubrics.md`, theory).
- **M6.** Cost is stated: parameters, FLOPs, memory, and wall-clock time for training and inference
  with the hardware. 28% of real CV reviews ask for efficiency, usually wall-clock time in addition
  to FLOPs (`real_review_patterns.md`, sec. 2).
- **M7.** The main paper plus supplement suffice to reimplement it; the main text points to the
  supplement section for each deferred detail.

## 6. Experiments
- **E1.** Baselines include the strongest recent same-family methods and the method the paper
  builds on; reproduced and copied numbers are marked. Not beating the state of the art is not
  grounds for rejection by itself (CVPR 2026 reviewer guidelines): report it, do not hide it.
- **E2.** Budgets are matched and stated for every method: parameters, compute, training data,
  iterations, tuning effort. Gains credited to a new design but caused by tuning are a classic
  failure (Lipton & Steinhardt 2018); in deep metric learning, four years of claimed gains proved
  "marginal at best" under a fair protocol (Musgrave et al. 2020).
- **E3.** Hyperparameters, checkpoints and stopping points are chosen without test labels or
  ground truth, and the text says how.
- **E4.** Metrics test the claim: a perceptual metric for a perceptual claim, small-object AP for a
  small-object claim; every metric carries ↑ or ↓.
- **E5.** The main results sit in a table, not only in figure insets; numbers are identical in
  tables, text, figures and abstract.
- **E6.** Each results paragraph opens with what the table or figure compares and ends with the
  conclusion it supports, one claim per paragraph (Mensh & Kording 2017, rule 7: "Each paragraph
  convinces the reader of the answer given in its last sentence").
- **E7.** Where margins are small, show the spread (seeds, or per-image or per-scene standard
  deviation) and say what the error bars capture (NeurIPS paper checklist). Small gains separate
  rejecting from accepting reviews (23% vs 5%): say where the gain is consistent instead of
  rounding it up into a general claim (`real_review_patterns.md`, sec. 2).
- **E8.** General claims rest on standard benchmarks of adequate size, not on one image or one
  scene per task.

## 7. Ablations and analysis as mechanism evidence
- **X1.** Each component is removed or replaced under the same budget, on the main benchmark, not
  on one example (Lipton & Steinhardt 2018: identify the sources of empirical gains).
- **X2.** The analysis tests the paper's explanation with a prediction that could have failed, not
  only the final number ("if the depth prior drives the gain, the gain should grow with depth
  variation across scenes").
- **X3.** Failure cases appear, each with one line on why (`figure_rubric.md`,
  `missing_failure_cases`).
- **X4.** Sensitivity to the key hyperparameters is shown or pointed to.

## 8. Figures, tables and captions
Use `figure_rubric.md` (criteria, roles, defects) and the fix recipes and DATA LOCK in
`writer_rules.md`. The checks reviewers apply first:
- **F1.** Captions are self-contained: what is shown, the setting, every symbol and abbreviation,
  and what to conclude (Huang, writing tips; `figure_rubric.md`, `caption_alignment`).
- **F2.** Every caption claim is visible in the figure or stated in a table.
- **F3.** Each table conveys one thing (Huang, writing tips); best-value marks match the printed
  numbers, ties included.
- **F4.** Every figure and table is cited where its claim is made.

## 9. Limitations
- **L1.** Specific failure modes, costs or scope limits, each tied to evidence (a figure, a table,
  a setting), not "future work could extend this to video" (`section_rubrics.md`, limitations).
- **L2.** It says how the method's assumptions could fail in practice and what would follow.
  NeurIPS asks for a separate section and tells reviewers "to not penalize honesty concerning
  limitations" (NeurIPS paper checklist).
- **L3.** Claims elsewhere stay inside these limits. Do not pad the section with minor limitations
  to steer reviewers (`writer_rules.md`, hard rule 9).

## 10. Conclusion
- **C1.** It says how the results filled the gap stated in the introduction, with the abstract's
  scope words, and adds no claim the experiments did not test (Mensh & Kording 2017, rule 8;
  `section_rubrics.md`, conclusion).
- **C2.** It ends with the one lesson to remember; future work takes one sentence at most, since
  promises earn no credit (`reviewer_common.md`, rule 6).

## 11. Sentences and paragraphs
Readers expect certain information in certain places (Gopen & Swan 1990).
- **S1.** Topic position: begin a sentence with old information, the thing whose story it tells,
  linked to the sentence before.
- **S2.** Stress position: end the sentence with the new information to emphasise: the finding,
  the number, the contrast.
- **S3.** Follow the grammatical subject soon with its verb, and put the action in the verb ("we
  compare", not "a comparison is performed").
- **S4.** Give context before anything new: define a term or symbol before the sentence that
  needs it.
- **S5.** One point per paragraph, stated in its first sentence or its last (Gopen & Swan 1990:
  every unit of discourse should "make a single point"; Mensh & Kording 2017, rule 3).
- **S6.** One idea per sentence; split sentences that chain "which" clauses or "respectively"
  (Huang, writing tips).
- **S7.** The same word for the same concept everywhere; no term of art with a suggestive everyday
  meaning ("understands", "reasons", "imagines") unless it is defined (Mensh & Kording 2017,
  rule 2; Lipton & Steinhardt 2018).
- **S8.** Replace adjectives of merit ("superior", "remarkable", "significant") with the measured
  comparison.

Example (S1-S3). Before: "Improvements on all three deblurring benchmarks, which we attribute to
the depth prior, are observed in Tab. 4." After: "Tab. 4 isolates the depth prior: without it,
PSNR drops on all three deblurring benchmarks." The table the reader knows comes first, the verb
follows at once, and the finding ends the sentence.

## 12. Final check: the one-pass test
- **K1.** Someone outside the subfield reads only the title, abstract, Fig. 1, contribution list
  and main table for ten minutes, then states the contribution, the evidence and the difference
  from the closest work. If they cannot, fix those parts first: "If a reviewer cannot understand
  the gist after one pass, the paper will likely be rejected" (Keshav 2007).

## Sources
- Gopen & Swan 1990, The Science of Scientific Writing, American Scientist 78(6):550-558:
  https://www.americanscientist.org/blog/the-long-view/the-science-of-scientific-writing
- Mensh & Kording 2017, Ten simple rules for structuring papers, PLoS Comput Biol 13(9):e1005619:
  https://doi.org/10.1371/journal.pcbi.1005619
- Lipton & Steinhardt 2018, Troubling Trends in Machine Learning Scholarship (ICML 2018 Debates):
  https://arxiv.org/abs/1807.03341
- Peyton Jones, How to write a great research paper (talk and slides):
  https://www.microsoft.com/en-us/research/academic-program/write-great-research-paper/
- Kajiya 1993, How to Get Your SIGGRAPH Paper Rejected:
  https://ics-websites.science.uu.nl/docs/vakken/mcrws/xtra/kajiya.pdf
- Keshav 2007, How to Read a Paper, ACM SIGCOMM CCR 37(3):83-84:
  https://www.cs.princeton.edu/courses/archive/fall10/cos597B/papers/howtoread-keshav.pdf
- Huang, writing tips: https://github.com/jbhuang0604/awesome-tips/blob/master/paper-writing.md;
  related-work tips: https://github.com/jbhuang0604/awesome-tips/blob/master/related-work.md
- Musgrave, Belongie & Lim 2020, A Metric Learning Reality Check, ECCV 2020:
  https://www.ecva.net/papers/eccv_2020/papers_ECCV/html/5170_ECCV_2020_paper.php
- NeurIPS Paper Checklist Guidelines: https://neurips.cc/public/guides/PaperChecklist
- CVPR 2026 Reviewer Guidelines: https://cvpr.thecvf.com/Conferences/2026/ReviewerGuidelines
