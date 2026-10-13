# Review a paper and compute its scores

This is the single entry point. Give it to an agent with the paper:

> Follow <harness root>/REVIEW_PAPER.md for
> PAPER=<path/main.pdf> NAME=<short name> [SUPP=<path/supplement.pdf>]

Optional settings: `VENUE` [cvpr; iclr, icml, neurips], `READING` [venue default; careful for all new ML profiles], `CONTRIBUTION_TYPE` [general; NeurIPS also supports theory, use_inspired, concept_feasibility, negative_results], `PANEL` [venue default], `REVIEWERS` [venue-specific IDs], `MODE` [full; sections or both], `SEED` [0], `SCALE` [venue default]. The original CVPR panel names do not apply to other venues.

Example: `Follow REVIEW_PAPER.md for PAPER=main.pdf NAME=mypaper VENUE=neurips CONTRIBUTION_TYPE=theory`.

## Steps for the agent

```bash
cd <harness root>
python3 06_scripts/hx.py new --paper "$PAPER" --supp "$SUPP" --name "$NAME" \
    --venue "$VENUE" --mode full
```

Default VENUE to cvpr when omitted. Pass the selected optional settings through to their matching CLI flags; do not hardcode a CVPR panel or scale. Omit `--supp` when there is no supplement.

1. The command prints the session folder and one launch line per reviewer.
2. Launch one NEW agent per launch line, all in one message (parallel). Each agent gets exactly:
   `Read <prompt path> and follow it exactly. Write only the files it names.`
   Do not add anything about the paper, the authors' goals or other reviewers.
3. When all agents have finished: `python3 06_scripts/hx.py validate <session>`. Every job must
   print OK. Re-launch a FAIL job with a fresh agent; never edit a review by hand.
4. For careful-mode reviews, inspect `evidence_audit`: do observations cite actual locations and support their conclusions? Report unchecked coverage, and re-launch a fresh reviewer to resolve consequential omissions when the material is accessible. Structural validation cannot certify scientific correctness. Never invent a finding or convert not_checked into a defect.
5. `python3 06_scripts/hx.py aggregate <session>` computes the scores.
6. Report to the user: the headline line and the table from `round_01/SCORES.md`, the decisive
   weaknesses, and the path to the debriefs. Do not summarize the reviews more kindly than they are.

## Where the scores are

| file | content |
|---|---|
| `sessions/<date>_<name>/round_01/SCORES.md` | **the score sheet**: headline, per-reviewer table, section means and minima, decisive weaknesses |
| `.../round_01/SCORES.json` | the same, machine-readable |
| `.../round_01/reviews/<id>/review.md` | each review as a reviewer would submit it |
| `.../round_01/reviews/<id>/debrief.md` | what caused each reaction and the smallest fix (for the writer) |
| `.../round_01/FEEDBACK.md` | **the to-do list**: every point with location, suggested fix and what would satisfy the reviewer; section scores lowest first |
| `sessions/<date>_<name>/PROGRESS.md` | scores across rounds, when the paper is revised and re-reviewed |

## How the scores are computed

- **Rating**: each reviewer gives one preliminary recommendation on the session scale (default
  1 Reject, 2 Weak Reject, 3 Borderline, 4 Weak Accept, 5 Strong Accept). The panel score is the
  mean; the minimum is shown as a diagnostic. Use the selected profile's labels, and never present the number as a predicted conference decision.
- **First impression** (CVPR persona mode only; null in careful mode): the rating each reviewer wrote after the skim (title, abstract, Fig. 1,
  captions, main table), before the method. A first impression well below the final rating means
  the opening pages undersell the paper.
- **Section scores**: 1-10 per section, anchored in `02_protocol/section_rubrics.md` (9-10 cited
  as a strength; 7-8 minor comments; 5-6 a moderate weakness; 3-4 a major weakness; 1-2 a reason
  to reject). A section's score is the mean over the reviewers who read it; 2-6 sub-criteria
  (1-5) explain it. "Section mean" in the headline averages the section means.
- **Decisive weaknesses**: points a reviewer says would by themselves block acceptance, each with
  its category and whether writing, existing evidence or a new experiment could fix it.

Read the numbers as a simulation for improving the draft, not as a forecast. A second draw
(`--seed 1`) or `hx.py retest` shows how much the scores move by chance.

## Then: revise and recheck

1. `python3 06_scripts/hx.py stage <session> writer` creates `round_01/writer/RESPONSE.md`, one
   block per point. Answer each point, either by fixing the paper or by arguing with a pointer to
   the paper, and rebuild the PDF.
2. `python3 06_scripts/hx.py round <session> --paper <new main.pdf> --supp <new supp.pdf>`, then
   launch the printed `satisfy` prompts. The same reviewers rule each answer satisfied, partly or
   not satisfied and re-score.
3. `validate` and `aggregate` again. The new `FEEDBACK.md` holds only what is still open. Repeat.

See [the revision loop](README.md#the-revision-loop) and [agent rules](AGENTS.md) for details.

The dialogue is an author-preparation exercise, not an official rebuttal workflow. In particular, do not treat revised-PDF rounds as permitted NeurIPS rebuttal submissions. See the [multi-venue design](01_sources/multi_venue_review_design.md).
