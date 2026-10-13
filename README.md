# CVPR review harness

This harness writes realistic CVPR reviews of a paper draft. Sixteen reviewer personas are modelled
on real reviewer types. They review the whole paper on the CVPR form and also score every section (title, abstract, introduction, related work, method, theory, experiments,
ablations/analysis, figures/tables, limitations, conclusion, supplement, references). The harness
then runs rounds against a writer agent: the writer revises, fresh reviewers review the revision,
and the scores show whether the paper really got better.

**To review a paper and get its scores, use `REVIEW_PAPER.md`** (single entry point; the score
sheet is `sessions/<date>_<name>/round_01/SCORES.md`). Rules for agents are in `AGENTS.md`. The evidence behind the personas is in `01_sources/`.

## Quick start

```bash
cd path/to/CVPR_review_harness
H=06_scripts/hx.py
P=path/to/your/paper   # folder with main.pdf, supplement.pdf and the LaTeX sources

# 1. Freeze the draft and write one prompt per reviewer job (realistic 3-reviewer draw + section panel)
python3 $H new --paper $P/main.pdf --supp $P/supplement.pdf --tex $P \
    --name mypaper --panel realistic --mode both --domain inr_neural_fields

# 2. In Claude Code: launch one fresh agent per printed prompt, all in parallel, each told:
#    "Read <prompt path> and follow it exactly. Write only the files it names."

# 3. Check and score
python3 $H validate mypaper          # every job must be OK
python3 $H aggregate mypaper         # writes round_01/SCORES.md and PROGRESS.md
```

`mypaper` here stands for the session folder name that `new` prints, e.g.
`sessions/<date>_mypaper`.

## Modes and panels

`--mode full` gives whole-paper reviews on the CVPR form; each reviewer also scores the sections
they actually read. `--mode sections` has the section panel (`04_panels/section_panel.json`) score
each section, with no overall rating. `--mode both` (the default) runs both.

| panel | members | use it to |
|---|---|---|
| `realistic` | seeded draw: 1 expert slot, 1 expert/adjacent, 1 any | estimate a real assignment; change `--seed` for another draw |
| `realistic4` | as above + 1 any | borderline papers often get a 4th reviewer |
| `quick` | R09 busy senior, R03 expert, R08 adjacent | cheap first look |
| `stress` | R02 skeptic, R03 expert, R05 methodologist, R11 hostile | find the decisive weaknesses |
| `writing` | R07 clarity, R08 adjacent, R09 busy senior, R12 champion | prose and story passes |
| `core` | R01 R02 R03 R05 R07 R09 R11 | balanced pre-submission check |
| `gauntlet` | all 16 | final check before submission |

Use `--reviewers R03,R11` for a custom panel and `--sections abstract,introduction` to score only
some sections.

## The reviewers

| id | persona | what it stresses in your paper |
|---|---|---|
| R01 | Leaderboard reviewer | main table, recent baselines, benchmark size |
| R02 | Novelty skeptic | "A + B" reading, closest prior work, what is truly new |
| R03 | Subfield expert | protocol traps, implausible baseline numbers, precise terms |
| R04 | Theory checker | equations, proofs, notation, theory that is decoration |
| R05 | Rigor methodologist | tuning fairness, selection on test data, variance, ablation design |
| R06 | Efficiency pragmatist | wall-clock, memory, equal-time comparisons, scaling |
| R07 | Clarity editor | undefined terms, flow, figure legibility, line-level issues |
| R08 | Adjacent-area generalist | why CVPR should care; intuition; visuals |
| R09 | Busy senior | the first two pages, Fig. 1 and the main table only |
| R10 | Junior checklist | code, limitations, recent arXiv baselines, completeness |
| R11 | Hostile "Reviewer 2" | hedges, buried evidence, misreadable claims |
| R12 | Champion | whether the paper gives a supporter quotable arguments |
| R13 | Reproducibility auditor | missing settings, numbers that do not add up, code |
| R14 | Competing lab | credit and comparison to the closest line of work |
| R15 | LLM-assisted reviewer | generic criticisms that a quick reader will raise |
| R16 | Misassigned outsider | whether the paper communicates beyond the subfield |

Each review comes as three files: `review.md` (in character, as submitted), `review.json` (scores,
a first-impression rating given after the skim and before the method, weaknesses with location,
severity and how fixable they are), and `debrief.md`. The debrief is out
of character: it quotes the sentence that caused each reaction and the smallest fix. It is the
writer's main input.

## Fight and satisfy the reviewers

1. **Review** (round 1): as in Quick start. `aggregate` also writes `round_01/FEEDBACK.md`, the
   to-do list. It gives every point with its location, the complaint, the reviewer's suggested fix
   and "what would satisfy them", decisive and major points first. Then come all section scores,
   lowest first.
2. **Answer**: `python3 $H stage mypaper writer` pre-fills `round_01/writer/RESPONSE.md` with one
   block per point. You or the writer agent fill in `Decision`, `Changed (where in the new
   draft)` and the answer, and revise the paper. Answers must point to the new draft; promises do
   not count.
3. **Reviewers judge**: `python3 $H round mypaper --paper <new main.pdf> --supp <new supp.pdf>`. Each
   reviewer, a fresh instance of the same persona given its own thread, checks every answer
   against the new draft. It marks each point satisfied, partly or not satisfied, may raise new
   issues the revision introduced, and re-scores. Launch the printed `satisfy` prompts.
4. **See where you stand**: `validate`, then `aggregate`. The `SCORES.md` headline shows
   "Answers: N satisfied, M partly, K not satisfied" and the old -> new rating per reviewer. The
   new `FEEDBACK.md` lists only what is still open, with the reviewer's reason.
5. Repeat 2-4 until the reviewers are satisfied or the remaining points need new experiments.

Add held-out reviewers at `new` time (e.g. `--heldout R02,R11`). They review every draft from
scratch and never see the argument, so they show whether the paper improved or the reviewers were
only talked round. Run them on a different model than the writer. `python3 $H retest mypaper`
measures how much scores move by chance. `--loop fresh` replaces the dialogue with entirely new
reviews each round; then also use `stage fixcheck` and `stage pairwise`.

The writer may not inflate claims, invent numbers or edit harness files
(`02_protocol/writer_rules.md`). Put your project-specific limits (no new experiments of type X,
names that must not appear, style rules) in the session's `AUTHOR_CONSTRAINTS.md`. Reviewers never
see that file; the writer must respect it.

## Limits
- This is a simulation for improving drafts. It is not real CVPR feedback and not an acceptance
  forecast.
- All personas run on language models. They share some blind spots, e.g. a tendency toward
  balanced, mid-scale scores. The personas, reading budgets and the hostile and LLM-assisted
  reviewers push against this, but cannot remove it.
- Scores move between runs. Measure the noise floor with `retest` before reading meaning into
  small changes.
- Personas, rubrics and panels are frozen within a session. Changing them starts a new session.
- Reviews only: there is no rebuttal, discussion or area-chair stage.
