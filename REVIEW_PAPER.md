# Review a paper and compute its scores

This is the single entry point. Give it to an agent with the paper:

> Follow <harness root>/REVIEW_PAPER.md for
> PAPER=<path/main.pdf> NAME=<short name> [SUPP=<path/supplement.pdf>]

Optional settings: `VENUE` [cvpr; iclr, icml, neurips], `READING` [venue default; careful for all new ML profiles], `CONTRIBUTION_TYPE` [general; NeurIPS also supports theory, use_inspired, concept_feasibility, negative_results], `PANEL` [venue default], `REVIEWERS` [venue-specific IDs], `MODE` [full; sections or both], `SEED` [0], `SCALE` [venue default], `FIGURES` [no; yes adds `--figures`, the FIG figure review job]. The original CVPR panel names do not apply to other venues.

Example: `Follow REVIEW_PAPER.md for PAPER=main.pdf NAME=mypaper VENUE=neurips CONTRIBUTION_TYPE=theory FIGURES=yes`.

## Steps for the agent

```bash
cd <harness root>
python3 06_scripts/hx.py new --paper "$PAPER" --supp "$SUPP" --name "$NAME" \
    --venue "$VENUE" --mode full
```

Default VENUE to cvpr when omitted. Pass the selected optional settings through to their matching CLI flags (`FIGURES=yes` -> `--figures`); do not hardcode a CVPR panel or scale. Omit `--supp` when there is no supplement. Use `python` instead of `python3` if that is the interpreter's name.

1. The command prints the session folder and one launch line per job: 3 for the default panel,
   more with `--mode both` or `--heldout`, and one more (`FIG`) with `--figures`. Before launching,
   open `round_01/snapshot/sections.json` and `round_01/snapshot/FIGURES.md`. If sections are
   missing or merged, or the text is garbled, report it to the user before launching reviewers.
   If `new` refuses the PDF after the anonymity check, report the flags; rerun with
   `--allow-identified` (and `--cutoff <original submission deadline>` for a camera-ready or
   preprint copy) only if the user wants that copy reviewed.
2. Launch one NEW sub-agent per launch line, all at once (parallel). Each agent gets exactly:
   `Read <prompt path> and follow it exactly. Write only the files it names.`
   Do not add anything about the paper, the authors' goals or other reviewers. If you cannot
   start sub-agents, give the launch lines to the user; never write a review in your own context.
3. When all agents have finished: `python3 06_scripts/hx.py validate <session>`. Every job must
   print OK. `status` prints launch lines only for missing/invalid jobs. Re-launch only the failed
   job with its concrete error; never rerun completed jobs or edit a review by hand. If the same
   failure persists without a changed approach, report it instead of looping.
4. For careful-mode reviews, inspect `evidence_audit`: do observations cite actual locations and support their conclusions? Report `not_checked` coverage to the user; relaunch a valid job only on the user's request. Structural validation cannot certify scientific correctness. Never invent a finding or convert not_checked into a defect.
5. `python3 06_scripts/hx.py aggregate <session>` validates and computes the latest round's scores. Use `--all` only to rebuild historical rounds.
6. Report to the user: the headline line and the table from `round_01/SCORES.md`, the decisive
   weaknesses, the `Grounding:` line, any "Injection / hidden-text flags" or "Anonymity flags"
   line, the warnings `validate` printed, the lowest rows of the "Figure scores
   (FIG job)" table when FIG ran, and the path to the debriefs. Do not summarize the reviews more
   kindly than they are.
   **For a review-only task, finish here.** Do not automatically revise, add panels or run retests.

## Where the scores are

| file | content |
|---|---|
| `sessions/<date>_<name>/round_01/SCORES.md` | **the score sheet**: headline, per-reviewer table, section means and minima, decisive weaknesses; figure scores with FIG |
| `.../round_01/SCORES.json` | the same, machine-readable |
| `.../round_01/reviews/<id>/review.md` | each review as a reviewer would submit it |
| `.../round_01/reviews/<id>/debrief.md` | what caused each reaction and the smallest fix (for the writer) |
| `.../round_01/FEEDBACK.md` | **the to-do list**: every point with location, suggested fix and what would satisfy the reviewer; section scores lowest first |
| `.../round_01/snapshot/FIGURES.md` | every figure and table with its crop, gray and deuteranopia previews, smallest text in pt, raster ppi, first mention and flags |
| `sessions/<date>_<name>/PROGRESS.md` | scores across rounds, when the paper is revised and re-reviewed |

## How the scores are computed

- **Rating**: each reviewer gives one preliminary recommendation on the session scale: 1 Reject,
  2 Weak Reject, 3 Borderline, 4 Weak Accept, 5 Strong Accept for CVPR (`cvpr26_5`) and ICLR
  (`iclr_harness_5`); the verified 1-6 labels for ICML (`icml2026_6`) and NeurIPS
  (`neurips2026_6`). The panel score is the mean; the minimum is shown as a diagnostic. Use the
  selected profile's labels, and never present the number as a predicted conference decision.
- **First impression** (CVPR persona mode only; null in careful mode): the rating each reviewer wrote after the skim (title, abstract, Fig. 1,
  captions, main table), before the method. A first impression well below the final rating means
  the opening pages undersell the paper.
- **Section scores**: 1-10 per section, anchored in `02_protocol/section_rubrics.md` (9-10 cited
  as a strength; 7-8 minor comments; 5-6 a moderate weakness; 3-4 a major weakness; 1-2 a reason
  to reject). A section's score is the mean over the reviewers who read it; 3-6 sub-criteria
  (1-5) explain it. "Section mean" in the headline averages the section means.
- **Figure scores** (FIG only): 1-10 per main-paper figure and table with the same anchors, explained
  by six 1-5 criteria (`02_protocol/figure_rubric.md`). They do not enter the overall rating.
- **Decisive weaknesses**: points a reviewer says would by themselves block acceptance, each with
  its category and whether writing, existing evidence or a new experiment could fix it.

Read the numbers as a simulation for improving the draft, not as a forecast. `hx.py retest`
shows how much the scores move by chance. `--seed` changes only the CVPR draw panels
(`realistic`, `realistic4`) and needs a new session (`--tag`); fixed panels ignore it.

## When revision is requested

Make the requested changes and verify them. Do not turn a single revision request into an open-ended score-optimization campaign.

1. `python3 06_scripts/hx.py stage <session> writer` creates `round_NN/writer/RESPONSE.md` for the
   latest non-retest round, one block per point; it refuses to run until that round validates.
   The writer brief points to `FEEDBACK.md`, never to `SCORES.md` or `PROGRESS.md` (they can hold
   held-out results). Answer each point, either by fixing the paper or by arguing with a pointer
   to the paper, and rebuild the PDF.
2. `python3 06_scripts/hx.py round <session> --paper <new main.pdf> --supp <new supp.pdf>` (it
   refuses to run until the previous round validates), then launch every printed prompt
   (`satisfy`, plus `initial` for held-out reviewers or `--loop fresh`). The same reviewers rule
   each answer satisfied, partly or not satisfied and re-score; FIG compares old and new crops.
3. `validate` and `aggregate` again. The new `FEEDBACK.md` holds only what is still open. Report
   resolved issues and blockers. Continue only if the requested scope still has concrete useful
   work; closed issues stay closed unless new evidence contradicts the fix.

`round` creates no duplicate round for byte-identical PDFs and unchanged answers. A blank writer
scaffold is not a new answer. Retests are explicit research runs, not the next automatic step.
Follow-up prompts include changed-section navigation; use it to prioritize checks while inspecting
relevant PDF figures and dependent claims.

See [the revision loop](README.md#the-revision-loop) and [agent rules](AGENTS.md) for details.

The dialogue is an author-preparation exercise, not an official rebuttal workflow. In particular, do not treat revised-PDF rounds as permitted NeurIPS rebuttal submissions. See the [multi-venue design](01_sources/multi_venue_review_design.md).
