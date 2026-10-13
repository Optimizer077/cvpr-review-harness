# Agent rules: Paper review harness

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
| `01_sources/` | research behind the design: official CVPR process, real-review patterns, reviewer-behaviour literature, multi-venue design, figure research | root (read-only once done) |
| `02_protocol/` | `venues.json` + `*_venue.md` (versioned venue profiles), `cvpr_form.md`, `scales.json`, `section_rubrics.md`, `section_criteria.json`, `taxonomy.json`; reviewer rules `reviewer_common.md`, `careful_review.md`, `careful_satisfaction.md`, `satisfaction_rules.md`; `fixcheck_rules.md`, `pairwise_rules.md`, `writer_rules.md`; figure job `figure_review_rules.md`, `figure_rubric.md`, `figure_criteria.json` | root only, with a backup first |
| `03_personas/` | one card per persona (R01-R16 CVPR, I01-I04 ICLR, M01-M04 ICML, N01-N06 NeurIPS, F01 figure reader), `personas.json` registry | root only, with a backup first |
| `04_panels/` | CVPR `panels.json` (panels) and `section_panel.json` (section -> personas); `iclr.json`, `icml.json`, `neurips.json` (panels and section map per venue) | root only |
| `05_templates/` | `review_schema.md`, `satisfaction_schema.md`, `evidence_audit.md`, `figure_schema.md`, `AUTHOR_CONSTRAINTS.md` | root only |
| `06_scripts/` | `hx.py` CLI + `hxlib/`, `smoke_test.py`, `test_*.py`, `export_public.py` | root only; must pass the tests |
| `assets/` | README banner, logo, venue and workflow figures | root only |
| `sessions/<date>_<paper>[_<tag>]/` | one review campaign: `SESSION.json`, `AUTHOR_CONSTRAINTS.md`, `round_NN/`, `PROGRESS.md`, `LOG.md` | see roles |

Inside `round_NN/`: `snapshot/` (frozen PDF, text, `sections.json`, views, `pages/` page images,
`figures/` crops with `_gray` and `_deuteranopia` previews and `figures.json`, and `FIGURES.md`
with measured facts and flags), `prompts/<stage>/`, `reviews/<job>/{review.md, review.json,
debrief.md}`, `heldout/<job>/` (same files, held-out group), `satisfaction/<job>/{reply.md,
satisfaction.json, OPEN_ITEMS.json, AUTHOR_RESPONSE.md}`, `fixcheck/`, `pairwise/`, `writer/`,
`SCORES.{json,md}`, `FEEDBACK.{json,md}`, `ROUND.json`.

**Persona card format.** R-cards and F01 follow the R07 structure: title, one-line summary,
Axes, Who you are, How you read this paper, What you care about, What lowers / raises your
rating (F01: score), Blind spots, How you write, How you score, When the authors answer you. I, M and N cards
are shorter: Scientific lens, What you examine, Calibration, Useful observation format. F01 is a
harness instrument (role `figure_reviewer`), not a sampled reviewer type; panels never draw it.
Every card needs an entry in `personas.json`.

## Roles
- **Root (orchestrator)**: creates sessions and rounds with `hx.py`, starts one fresh sub-agent per
  prompt, validates and aggregates, keeps `LOG.md`. It is the only role that writes session files
  other than an agent's own output folder. It never writes a review in its own context: if it
  cannot start sub-agents, it gives the launch lines to the user.
- **Reviewer** (one fresh agent per job, including FIG): reads only its prompt and the files that
  prompt lists, and writes only its own `reviews/<job>/`, `heldout/<job>/` or
  `satisfaction/<job>/`.
- **Checker and pairwise judge** (fresh agents): write `fixcheck/` or `pairwise/`.
- **Writer** (a separate agent, or the user's paper agent): reads the writer brief, then edits the
  paper in its own project and writes `writer/`. It never edits anything else in the harness.

## The loop
1. `hx.py new --paper main.pdf --supp supplement.pdf --tex <paper src> --name <paper> [--figures]`
   freezes round 1 and writes prompts. `--figures` adds the FIG job (persona F01): section-only,
   it scores every main-paper figure and table and lists located defects. `new` and `round` refuse
   a PDF with anonymity flags (author block, e-mail, CVF/arXiv stamp, acknowledgements, grant
   numbers, own code URL). Pass `--allow-identified` only when the user wants that copy reviewed
   (every reviewer prompt then says to ignore it), plus `--cutoff <original submission deadline>`
   for a camera-ready or preprint copy.
2. Root starts one fresh sub-agent per `prompts/initial/*.md`, all in parallel, with exactly:
   "Read <prompt> and follow it exactly. Write only the files it names."
3. `hx.py validate <session>` must report every job OK. Use `hx.py status <session>` to launch
   only missing or invalid jobs; valid outputs are complete. Repair a failed job once with the
   concrete validation error. If the same failure recurs without new evidence or a changed
   approach, report the blocker instead of repeating identical launches. Never hand-edit a review.
   `validate` also prints warnings that do not fail a job (`review.md` more than 20% outside the
   persona's word band, more weaknesses than `max_weaknesses`, review.md and review.json point
   counts differ, grounding problems). Report them; do not relaunch a valid job for a warning.
4. `hx.py aggregate <session>` writes `SCORES.md`, `GROUNDING.md` and `PROGRESS.md`. The
   `Grounding:` line under the SCORES.md headline counts verified quotes and bad references;
   `GROUNDING.md` lists them (held-out details only in `heldout/GROUNDING.md`). If only reviews
   were asked for, stop here and report.
5. `aggregate` also writes `FEEDBACK.md`: every open point from the feedback group with the
   reviewer's suggested fix and what would satisfy them, plus all section scores (and figure
   scores with FIG). `hx.py stage <session> writer` works on the latest non-retest round, refuses
   to run until that round validates, and pre-fills `writer/RESPONSE.md` (one block per point).
   The writer brief points to `FEEDBACK.md`, never to `SCORES.md` or `PROGRESS.md`, which can
   hold held-out results. The writer (or the user) answers every block, revises the paper and
   rebuilds the PDF.
6. `hx.py round <session> --paper <new main.pdf> ...` starts the next round; it refuses to run
   until the previous round validates. Default `--loop dialogue`: each feedback reviewer gets
   `prompts/satisfy/<id>.md`, a fresh instance of the same persona with its own thread, and rules
   each point satisfied / partly / not_satisfied against the new draft, raises new issues and
   re-scores. FIG compares the old and new crop of each open point and re-scores every figure.
   Held-out reviewers get fresh `prompts/initial/` prompts. Launch every printed prompt, validate,
   aggregate and report whether the requested fixes are resolved. Another round requires new
   evidence or a substantive new answer and useful work within the requested scope. With
   `--loop fresh`, later rounds are independent reviews.
7. Retests, extra panels, held-out benchmarking and blind comparisons are optional research
   tools, not routine work added to a review request. Run them when the user requests that
   evaluation or a specific unresolved concern warrants the check. Do not run repeated retests
   merely because a noise estimate is absent. Without them, report score changes as descriptive.
   `stage pairwise` compares changed sections and changed figure crops blind.

## Independence and anti-gaming (non-negotiable)
1. Every reviewer, checker and judge is a NEW agent instance. Never reuse one across rounds or
   jobs (never send a follow-up message to an earlier reviewer).
2. Reviewers never see other reviewers' outputs, aggregate scores, AUTHOR_CONSTRAINTS.md, LaTeX
   sources or project folders. Initial and held-out reviewers see only the current draft. Dialogue
   reviewers additionally see their own prior thread and the author's answers to their own points.
3. Persona cards, rubrics, scales and panels stay frozen within a session. A change starts a new
   session, because scores are only comparable under fixed instruments.
4. The writer never edits harness files. No number enters the paper without the paper project's
   own evidence check. Figure fixes change presentation, not the data shown (`writer_rules.md`,
   DATA LOCK).
5. If a held-out group is configured, its output is for the orchestrator's evaluation. Keep it
   out of the writer's inputs. Prefer a different model for an explicitly requested blind or
   held-out comparison. Do not add more agents solely to chase a higher simulated score.
6. Verify a revision against the concrete issues and the paper's own evidence. Fix regressions
   that matter; report unresolved scientific tradeoffs. Optional controlled comparisons may
   measure score variability, but a routine edit does not require a statistically significant
   score gain, repeated retests or a new panel before it can be delivered.
7. Default to a bounded task, not an automatic campaign: a review request ends with the review;
   a revision request ends when the requested changes are made and verified. There is no hard
   round cap on an explicitly requested iterative campaign. Continue only with a concrete
   actionable point and a changed draft, new evidence or substantive answer. Do not reopen
   resolved points without contrary evidence, repeat unchanged work, or add cosmetic edits just
   to keep the loop going. Report evidence/experiment blockers and finish the work that can be
   completed in scope. Simulated scores do not replace a human read of the final draft.
8. Prompt hashes are stored in `ROUND.json`. Do not edit a prompt after it is launched.
9. Check the "Injection / hidden-text flags" line in `SCORES.md` (key `injection_flags` in
   `SCORES.json`; hidden text or reviewer-directed sentences found in the PDF). Any flag must be
   removed from the paper before the round counts. An "Anonymity flags" line (key
   `anonymity_flags`) means the copy identifies its authors: tell the user before submission.

## Multi-agent practice
- Start one sub-agent per job (in Claude Code: individual Agent calls, not the Workflow tool).
  Agents talk only through the markdown files above. If the environment cannot start sub-agents,
  give the launch lines to the user; never review in the orchestrator's own context.
- Local files only; never publish the paper or reviews to a hosted service.
- Reviews are simulations. Never present them as real conference feedback or as an acceptance forecast.

## Environment
- Python: `python3` >= 3.9 with PyMuPDF (`pip install pymupdf`); everything else is the standard
  library. Use `python` where that is the interpreter's name.
- Tests: `python3 06_scripts/hx.py personas`, `smoke_test.py`, `test_venues.py`,
  `test_efficiency.py`, `test_figures.py`, `test_figure_job.py`, `test_figure_locate.py`,
  `test_loop_regressions.py`, `test_validation_regressions.py`, `test_grounding.py`,
  `test_anonymity.py`, `test_prompts.py` and `test_integration.py` (all in `06_scripts/`; run each
  as `python3 06_scripts/<name>.py`) must pass after any change to scripts, personas, panels or
  protocol.
- Public copy: `python3 06_scripts/export_public.py` writes a `release/` folder and zip (no
  sessions, no build notes, no raw downloads). It fails if exported text matches a generic
  identity pattern (home-directory paths, e-mail addresses) or a private pattern from
  `00_plan/deid_patterns.txt` when that file exists. It does not check git history or topic
  wording.
- Back up a protocol or persona file before editing it: `<file>.bak_before_<reason>_<YYYY-MM-DD>`.

## Venue-aware careful review
- Select the requested versioned venue profile before creating a session; do not substitute CVPR
  rules for an ML venue or silently change a year. New ML personas are curated lenses, not an
  empirical estimate of real reviewer frequencies.
- ICLR, ICML and NeurIPS default to careful reading. Check central claims, relevant supplement
  and PDF figures; keep evidence locations and unchecked coverage in the audit. Treat extracted
  section boundaries as provisional. Validate structure, then inspect scientific substance.
  With `--reading careful`, CVPR persona cards are reduced to their names as lenses (no reading
  habits, no rating offsets).
- Honor the declared NeurIPS contribution type. Do not demand empirical benchmarks for pure
  theory or a remedy for a well-supported negative result by default. The NeurIPS `theory` panel
  has the same members as `balanced`, and the NeurIPS section map assigns its specialists by
  section regardless of contribution type.
- Newly created sessions embed review instruments. Old sessions retain legacy fallbacks; start a
  new session to adopt new rules. Record the repository commit in LOG.md for code reproducibility.
- Keep the selected profile's rating provenance visible, especially the harness-defined ICLR
  scale. This is draft preparation, not the venue's official rebuttal procedure.

## Efficient execution
- Use the default full-paper panel for one initial pass; `both`, `gauntlet` and `--figures` are
  deliberate expanded coverage options, not automatic follow-ups. Reviewers may run in parallel
  with independent contexts, but do not create duplicate jobs.
- `status` prints launch instructions only for missing/invalid jobs. Do not rerun valid outputs.
- `round` skips byte-identical PDFs unless a filled, changed author answer warrants dialogue.
  Blank answer templates do not count. Use `retest` only for an intentional repeat review.
- `aggregate` validates and rebuilds the latest round by default; `--all` rebuilds history.
  After repairing an older round, rebuild that round or use `--all` before interpreting progress.
- Recheck changed evidence, affected claims and unresolved points first. Text-diff navigation
  cannot prove figures unchanged; inspect relevant PDF evidence. Do not claim to reverify what
  you only inherited from a previous pass.
