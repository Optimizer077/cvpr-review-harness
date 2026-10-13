# Agent rules: CVPR review harness

These rules apply to every agent (Claude Code, Codex, others) and every person who runs this
harness. `README.md` is the human guide. Rules here are about how reviews are run, kept separate
and logged. They state no research direction and no opinion on any paper.

## What the harness is for
It produces simulated CVPR, ICLR, ICML and NeurIPS reviews of a draft: independent reviews by reviewer personas modelled on
real reviewer types, a score for every section, and a debrief telling the writer what caused each
reaction. It also runs a loop against a writer agent: the writer revises, and fresh reviewers
review the revision. It does NOT simulate an entire official conference process (no rebuttal, discussion or
area-chair stage, by design). The aim is a paper that real reviewers accept. A high
simulated score is not the aim.

## Layout

| Path | Content | Who writes |
|---|---|---|
| `00_plan/` | `task_plan.md`, `notes.md` for building the harness | root |
| `01_sources/` | research behind the personas: official CVPR process, real-review patterns, reviewer-behaviour literature | root (read-only once done) |
| `02_protocol/` | form, scales, section rubrics and criteria, taxonomy, reviewer/fix-check/pairwise/writer rules | root only, with a backup first |
| `03_personas/` | one card per reviewer persona, `personas.json` registry | root only, with a backup first |
| `04_panels/` | `panels.json` (panel definitions), `section_panel.json` (section -> personas) | root only |
| `05_templates/` | review JSON format, author-constraints template | root only |
| `06_scripts/` | `hx.py` CLI + `hxlib/` | root only; must pass the smoke test |
| `07_domain_packs/` | subfield knowledge for expert personas | root only |
| `sessions/<date>_<paper>_<tag>/` | one review campaign: `SESSION.json`, `AUTHOR_CONSTRAINTS.md`, `round_NN/`, `PROGRESS.md`, `LOG.md` | see roles |

Inside `round_NN/`: `snapshot/` (frozen PDF, text, sections, views), `prompts/<stage>/`,
`reviews/<job>/{review.md, review.json, debrief.md}`, `fixcheck/`, `pairwise/`, `writer/`,
`SCORES.{json,md}`, `ROUND.json`.

## Roles
- **Root (orchestrator)**: creates sessions and rounds with `hx.py`, launches one fresh agent per
  prompt, validates and aggregates, keeps `LOG.md`. It is the only role that writes session files
  other than an agent's own output folder.
- **Reviewer** (one fresh agent per job): reads only its prompt and the files that prompt lists, and
  writes only its own `reviews/<job>/`.
- **Checker and pairwise judge** (fresh agents): write `fixcheck/` or `pairwise/`.
- **Writer** (a separate agent, or the user's paper agent): reads the writer brief, then edits the
  paper in its own project and writes `writer/`. It never edits anything else in the harness.

## The loop
1. `hx.py new --paper main.pdf --supp supplement.pdf --tex <paper src> --name <paper> --domain <pack>`
   freezes round 1 and writes prompts.
2. Root launches one fresh agent per `prompts/initial/*.md`, all in parallel, with exactly:
   "Read <prompt> and follow it exactly. Write only the files it names."
3. `hx.py validate <session>` must report every job OK. Re-launch any FAIL job with a fresh agent and
   log it. Never hand-edit a review.
4. `hx.py aggregate <session>` writes `SCORES.md` and `PROGRESS.md`. If only reviews were asked
   for, stop here and report.
5. `aggregate` also writes `FEEDBACK.md`: every open point with the reviewer's suggested fix and
   what would satisfy them, plus all section scores. `hx.py stage <session> writer` pre-fills
   `writer/RESPONSE.md` (one block per point). The writer (or the user) answers every block,
   revises the paper and rebuilds the PDF.
6. `hx.py round <session> --paper <new main.pdf> ...` starts the next round. Default `--loop
   dialogue`: each feedback reviewer gets `prompts/satisfy/<id>.md`, a fresh instance of the same
   persona with its own thread, and rules each point satisfied / partly / not_satisfied against
   the new draft, raises new issues and re-scores. Held-out reviewers get fresh `prompts/initial/`
   prompts. Launch both, then validate, aggregate, and repeat from step 5 with the new
   FEEDBACK.md (only unsatisfied and new points). With `--loop fresh`, every round is a full fresh
   review; then also run `stage fixcheck` and `stage pairwise`.
7. Measure the noise floor: `hx.py retest <session>` reviews an unchanged draft again with fresh
   agents (once to start, three times before trusting small gains). `PROGRESS.md` turns the
   test-retest SD into a threshold for each section mean.

## Independence and anti-gaming (non-negotiable)
1. Every reviewer, checker and judge is a NEW agent instance. Never reuse one across rounds or
   jobs (no SendMessage to an old reviewer).
2. Reviewers never see other reviewers' outputs, aggregate scores, AUTHOR_CONSTRAINTS.md, LaTeX
   sources or project folders. Initial and held-out reviewers see only the current draft. Dialogue
   reviewers additionally see their own prior thread and the author's answers to their own points.
3. Persona cards, rubrics, scales and panels stay frozen within a session. A change starts a new
   session, because scores are only comparable under fixed instruments.
4. The writer never edits harness files. No number enters the paper without the paper project's
   own evidence check.
5. Keep a held-out group for the loop (`hx.py new ... --heldout R02,R11`): their reviews go to
   `round_NN/heldout/`, the writer never reads them, and their scores decide progress. Run the
   held-out reviewers and the blind pairwise judge on a different model than the writer (e.g. Agent
   `model: sonnet` when the writer is Opus, or Codex), because a judge from the writer's own model
   prefers its own style.
6. A revision is accepted only if the blind pairwise judge prefers it AND the held-out (or, without
   held-out, feedback) section means rise above the noise threshold printed in `PROGRESS.md` AND
   the fix check finds no new issues it introduced. Otherwise revert the losing sections. A gain in
   one place with regressions elsewhere is a trade-off, not progress; report it as such.
   Presentation-only rounds (CHANGES.md tags) need the pairwise and held-out confirmation; length
   growth is reported next to every gain.
7. There is no fixed round cap or automatic stop after a score plateau. Continue the requested
   revision loop while there is actionable work within the user's scope. Report stalled scores
   and experiment-dependent weaknesses, and continue addressing independent actionable points.
   Finish when the requested work is complete or the user stops the loop; if further progress
   requires missing evidence or input, report the blocker. Simulated scores do not replace a
   human read of the final draft.
8. Prompt hashes are stored in `ROUND.json`. Do not edit a prompt after it is launched.
9. Check `injection_flags` in `SCORES.md` (hidden text or reviewer-directed sentences found in the
   PDF). Any flag must be removed from the paper before the round counts.

## Multi-agent practice
- Use individual named Agent calls; do not use the Workflow tool. Agents talk only through the
  markdown files above.
- Local files only; never publish the paper or reviews to a hosted service.
- Reviews are simulations. Never present them as real conference feedback or as an acceptance forecast.

## Environment
- Python: `python3` >= 3.9 with PyMuPDF (`pip install pymupdf`); everything else is the standard library.
- Smoke test: `python3 06_scripts/hx.py personas` and `python3 06_scripts/smoke_test.py` must pass
  after any change to scripts, personas, panels or protocol. Also run `python3 06_scripts/test_venues.py`.
- Public copy: `python3 06_scripts/export_public.py` writes a de-identified `release/` folder and zip
  (no sessions, no build notes, no raw downloads) and fails if an identifying string remains.
- Back up a protocol or persona file before editing it: `<file>.bak_before_<reason>_<YYYY-MM-DD>`.

## Venue-aware careful review
- Select the requested versioned venue profile before creating a session; do not substitute CVPR
  rules for an ML venue or silently change a year. New ML personas are curated lenses, not an
  empirical estimate of real reviewer frequencies.
- ICLR, ICML and NeurIPS default to careful reading. Check central claims, relevant supplement
  and PDF figures; keep evidence locations and unchecked coverage in the audit. Treat extracted
  section boundaries as provisional. Validate structure, then inspect scientific substance.
- Honor the declared NeurIPS contribution type. Do not demand empirical benchmarks for pure
  theory or a remedy for a well-supported negative result by default.
- Newly created sessions embed review instruments. Old sessions retain legacy fallbacks; start a
  new session to adopt new rules. Record the repository commit in LOG.md for code reproducibility.
- Keep the selected profile's rating provenance visible, especially the harness-defined ICLR
  scale. This is draft preparation, not the venue's official rebuttal procedure.
