"""Build self-contained reviewer prompts for the initial (independent) review stage.

A prompt opens with a Targets box (length, number of points, location format), then inlines the
persona card, the common reviewer rules, the files the reviewer may read, the review form
(whole-paper jobs) and the rubric of the assigned sections, and ends with the exact files the
reviewer must write.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional

from .anonymity import identified_line
from .common import PROTOCOL_DIR, TEMPLATE_DIR, load_json, review_dir, scale_wording
from .paper_text import line_numbered

from .venues import instrument, scales_for, careful, reviewer_card, common_rules, venue_block

logger = logging.getLogger(__name__)

DEBRIEF_WORDS = 350
# Careful mode replaces an R persona's reading habits, so its card length does not apply; the
# I/M/N lens cards carry the same default in personas.json.
CAREFUL_TARGETS: tuple[list[int], int] = ([400, 900], 8)
MAX_DECISIVE = 2
# Category ids that read ambiguously without their definition. The review_schema.md rules define
# marginal_gains and overclaiming; every other category is listed by id only.
_DEFINED_CATEGORIES = ("mechanism", "fairness", "positioning")
# Card section used only when the reviewer judges the authors' answers (satisfy stage).
_ANSWER_SECTION = re.compile(r"(?ms)^## When the authors answer you\s*$.*?(?=^## |\Z)")

_VIEW_TEXT = {
    "front": ("view_front.txt", "the title, abstract and introduction only. You may open the PDF "
              "page(s) holding Fig. 1. You do not read further: you form your judgement from the "
              "opening pages."),
    "skim": ("view_skim.txt", "the title, abstract, introduction, every figure/table caption, the "
             "section headings and the conclusion. Open the PDF pages that hold Fig. 1 and the main "
             "results table to look at them. You do not read the method or the experiments text in "
             "detail; consult `paper_main.txt` only to check one specific doubt, and say so."),
    "main": ("view_main.txt", "the full main paper, including references. Open PDF pages to inspect "
             "figures and tables."),
    "full": ("view_full.txt", "the full main paper and the supplementary material. Open PDF pages to "
             "inspect figures and tables."),
}
_SUPP_POLICY = {
    "no": "You do not open the supplementary material (many CVPR reviewers never do).",
    "if_needed": ("You open the supplementary material only when the main paper defers something you "
                  "need to judge a specific claim; then read only that part (`paper_supp.txt` / "
                  "`supplement.pdf`) and record in review.json `reading.opened_supplement` what you opened."),
    "yes": "You read the supplementary material (`paper_supp.txt`, `supplement.pdf`).",
}
_LOSSY_TEXT = ("The .txt files are lossy: superscripts, fractions, roots and symbols are often lost "
               "(\"10^0\" can read \"100\"). Check numbers, exponents, formulas and table values on the PDF "
               "page before quoting or arguing from them; quote what the page shows.")
_NO_LINE_NUMBERS = ("This PDF has no line numbers. Cite page, column and paragraph (\"p.4, left col., "
                    "para. 2\"), Fig., Tab. or Eq. Never cite line numbers of the .txt files.")
_LINE_NUMBERS = ("Cite the line numbers printed in the PDF margin as `L###` (the `L###` anchors in the "
                 ".txt files carry the same numbers), or page, Fig., Tab. or Eq.")

_PAGE_MARK = re.compile(r"(?m)^===== \[main p\.\d+\] =====$")
_ANCHOR = re.compile(r"(?m)^L\d{3,4}\b")
_NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
                 "eight": 8, "nine": 9, "ten": 10}
_CARD_WORDS = re.compile(r"(\d{2,4})\s*-\s*(\d{2,4})\s+words")
_CARD_POINTS = re.compile(r"(?:at\s+most|up\s+to|or)\s+(\d+|" + "|".join(_NUMBER_WORDS) + r")\s+"
                          r"(?:weakness|point)|weaknesses\s*\(at\s+most\s+(\d+)", re.IGNORECASE)
_TRAILING_NOTE = re.compile(r"\s*\([^()]*\)\s*$")
_OLD_CUTOFF = re.compile(r"Prior work for [^:\n]+: papers that appeared online after \d{4}-\d{2}-\d{2}")


def read_text(path: Path) -> str:
    """Read a UTF-8 text file."""
    return path.read_text(encoding="utf-8")


def rubric_for(sections: list[str], session: Optional[dict] = None) -> str:
    """Return the rubric blocks (`## <key>` headings in section_rubrics.md) for the given sections."""
    text = instrument(session or {}, PROTOCOL_DIR / "section_rubrics.md")
    blocks = re.split(r"(?m)^## ", text)
    head, chunks = blocks[0], {b.split("\n", 1)[0].strip(): "## " + b for b in blocks[1:]}
    head = re.sub(r"^# Section rubrics\s*", "", head.strip())
    picked = [chunks[s] for s in sections if s in chunks]
    missing = [s for s in sections if s not in chunks]
    if missing:
        logger.warning("No rubric block for sections %s", missing)
    return head.strip() + "\n\n" + "\n".join(picked)


def has_line_numbers(rnd: dict, snap: Path) -> bool:
    """Whether the review-copy PDF prints line numbers.

    The snapshot meta (`paper.line_numbers`) decides when present. Older snapshots are checked here
    with the rule the snapshot uses (`paper_text.line_numbered`) on the `L###` anchors of each page
    of `paper_main.txt`: numbered when at least half of the pages carry at least 10 anchors.
    """
    flag = rnd.get("paper", {}).get("line_numbers")
    if isinstance(flag, bool):
        return flag
    path = snap / "paper_main.txt"
    if not path.exists():
        return False
    return line_numbered([len(_ANCHOR.findall(page)) for page in _PAGE_MARK.split(read_text(path))[1:]])


def persona_targets(session: dict, persona: dict) -> tuple[Optional[list[int]], Optional[int]]:
    """(words [min, max], most weakness points) for the Targets box.

    From personas.json; for a session frozen before those fields existed, parsed from the card.
    Careful mode uses CAREFUL_TARGETS for R personas, whose card it replaces, and as the default
    for lens cards that state no length.
    """
    if careful(session):
        if persona["id"].startswith("R"):
            return CAREFUL_TARGETS
        return persona.get("words") or CAREFUL_TARGETS[0], persona.get("max_weaknesses") or CAREFUL_TARGETS[1]
    words, most = persona.get("words"), persona.get("max_weaknesses")
    if words is None or most is None:
        card = reviewer_card(session, persona)
        found = _CARD_WORDS.search(card)
        if words is None and found:
            words = [int(found[1]), int(found[2])]
        found = _CARD_POINTS.search(card)
        if most is None and found:
            value = (found[1] or found[2]).lower()
            most = int(value) if value.isdigit() else _NUMBER_WORDS[value]
    return words, most


def review_form(session: dict) -> str:
    """The CVPR review form with the session's venue label and prior-work cutoff filled in."""
    cutoff = str(session.get("prior_work_cutoff") or "the submission deadline")
    text = instrument(session, PROTOCOL_DIR / "cvpr_form.md")
    text = _OLD_CUTOFF.sub(f"Prior work for {session['venue']}: papers that appeared online after {cutoff}", text)
    return text.replace("{venue}", session["venue"]).replace("{cutoff}", cutoff)


def initial_prompt(session: dict, rnd: dict, job: dict, personas: dict[str, dict],
                   round_path: Path) -> str:
    """Compose the initial-review prompt for one job."""
    persona = personas[job["reviewer"]]
    snap = round_path / "snapshot"
    out_dir = review_dir(round_path, job)
    has_supp = (snap / "supplement.pdf").exists()
    supp_line = _SUPP_POLICY[persona.get("reads_supplement", "if_needed")] if has_supp else \
        "No separate supplement PDF was provided; check appendices in main.pdf."
    if job["view"] == "full" and has_supp:
        supp_line = _SUPP_POLICY["yes"]
    venue = session["venue"]
    with_form = bool(job["overall"]) and session.get("venue_profile", {}).get("venue", "cvpr") == "cvpr"
    parts: list[str] = [
        f"# Review job {job['job_id']} - {venue}, session {session['name']}, round {rnd['round']:02d}, "
        "stage: initial independent review\n\n"
        f"You are about to act as one simulated reviewer for {venue}. Read this whole prompt first. "
        "Stay in character for the review; step out of character only in `debrief.md`.",
        targets_block(session, persona, job, has_line_numbers(rnd, snap)),
        "## 1. Who you are\n\n" + _ANSWER_SECTION.sub("", reviewer_card(session, persona)).rstrip()
        + ("" if careful(session) else _leniency_line(persona)),
        "## 2. Rules for every reviewer\n\n" + common_rules(session),
        _reading_block(snap, supp_line, persona, job, session, with_form, identified_line(rnd["paper"])),
    ]
    if with_form:
        parts.append("## 4. Review form\n\n" + review_form(session))
    elif job["overall"]:
        parts.append("## 4. Review report\n\nUse Summary, Strengths, Weaknesses, Preliminary recommendation, Justification and Confidence headings. Add decision-relevant questions and limitations; assess the venue dimensions specified below.")
    else:
        parts.append("## 4. Section-only job\n\nThis job scores sections only. Do NOT give an overall "
                     "rating: set `overall` to null in review.json and omit the rating fields in review.md. "
                     "Still write strengths, weaknesses and questions for the assigned sections.")
    if job["sections"]:
        parts.append("## 5. Sections you score\n\n"
                     f"Score exactly these sections: {', '.join(job['sections'])}.\n\n"
                     + rubric_for(job["sections"], session))
    parts.append(_output_block(out_dir, job, session, rnd))
    parts.append(venue_block(session, job))
    return "\n\n".join(p for p in parts if p) + "\n"


def targets_block(session: dict, persona: dict, job: dict, line_numbers: bool, stage: str = "initial") -> str:
    """Hard limits right after the title: length, points, decisive points, location format, debrief.

    A section-only job covers part of the paper, so it gets only the upper word limit. The answer
    check (`stage` 'satisfy', dialogue.satisfy_prompt) writes reply.md and new issues instead of
    review.md, weaknesses and debrief.md; its box keeps the same numbers.
    """
    words, most = persona_targets(session, persona)
    satisfy = stage == "satisfy"
    lines = ["## 0. Targets", "",
             "Upper limits for this careful review, not quotas." if careful(session) else
             "Hard limits from your persona card; they override the rules below." if satisfy else
             "Hard limits from your persona card; they override the review form and rule 12."]
    if words and satisfy:
        lines.append(f"- `reply.md`: at most {words[1]} words.")
    elif words:
        span = f"{words[0]}-{words[1]} words" if job["overall"] else f"at most {words[1]} words"
        lines.append(f"- `review.md`: {span}, not counting the Section scores table.")
    points = f"at most {most} points; " if most else ""
    lines.append(f"- {'New issues' if satisfy else 'Weaknesses'}: {points}at most {MAX_DECISIVE} of them "
                 "decisive (zero is normal).")
    lines.append("- Locations: " + (_LINE_NUMBERS if line_numbers else _NO_LINE_NUMBERS))
    if not satisfy:
        lines.append(f"- `debrief.md`: at most {DEBRIEF_WORDS} words.")
    return "\n".join(lines)


def _leniency_line(persona: dict) -> str:
    """Calibration of this persona relative to a calibrated reviewer, as a tie-break rule."""
    off = float(persona.get("leniency", 0.0))
    if off == 0:
        return "\n\n**Your calibration:** you rate like a typical calibrated CVPR reviewer."
    side, pick = ("more lenient", "higher") if off > 0 else ("stricter", "lower")
    return (f"\n\n**Your calibration:** you are {side} than a typical calibrated CVPR reviewer. When torn "
            f"between two adjacent levels, choose the {pick} one.")


def _period_line(session: dict, with_form: bool) -> Optional[str]:
    """Review period and prior-work cutoff, unless the review form already states the policy."""
    if with_form:
        return None
    venue, cutoff = session["venue"], session.get("prior_work_cutoff")
    if careful(session):
        return (f"- Review period: {venue}. Prior-work search boundary: {cutoff or 'none assumed'}. "
                "Apply the venue policy below; date alone does not establish a mandatory comparison.")
    after = (f" Papers that appeared online after {cutoff} are contemporaneous and not grounds for "
             "rejection." if cutoff else "")
    return f"- Review period: {venue}.{after} Date alone does not make a comparison mandatory."


def _reading_block(snap: Path, supp_line: str, persona: dict, job: dict, session: dict,
                   with_form: bool, identified: str = "") -> str:
    """Section 3: the files this reviewer may read; `identified` is the identified-copy line or ''."""
    from .figure_render import figure_reading_line

    view_file, view_desc = _VIEW_TEXT[job["view"]]
    sections = f"`sections/<section>.txt` for {', '.join(job['sections'])}" if job["sections"] else "none"
    web = ("You MAY use WebSearch/WebFetch to look for the closest prior work, the way a real reviewer "
           "searches before writing 'this resembles X'. Cite only papers you actually found (title, "
           "venue or arXiv id, URL). Do not search for the submission itself or try to identify its "
           "authors (double-blind)." if persona.get("web_search") or careful(session) else
           "You do not search the web; you rely on what you already know, as this reviewer would. "
           "Cite from memory as method name + first author + \"(from memory)\"; add venue and year "
           "only if you are sure of both.")
    figures = figure_reading_line(snap, job["view"])
    period = _period_line(session, with_form)
    return "\n".join([
        "## 3. What you read (and nothing else)",
        f"Paths are relative to the snapshot folder `{snap}`.",
        f"- Your reading view: `{view_file}` - {view_desc}",
        f"- Assigned section texts (same content, split by section): {sections}.",
        "- The review-copy PDF: `main.pdf`. Look at figures by reading PDF pages (Read tool with `pages`).",
        *([f"- {identified}"] if identified else []),
        f"- {_LOSSY_TEXT}",
        *([f"- {figures}"] if figures else []),
        f"- {supp_line}",
        f"- {web}",
        *([period] if period else []),
        "- Do NOT open any other file: no other reviews, no earlier rounds, no session or harness "
        "files, no author notes, no project folders, no LaTeX sources. You are a reviewer who only "
        "received the PDF.",
        "",
        ("**Reading order.** Map the contribution, read and verify the evidence, then form your recommendation. Set first_impression to null. Record anything not checked." if careful(session) else
         "**Reading order.** Skim the opening and record first_impression before the detailed read. Then read according to the persona and explain changes in your final judgement."),
    ])


def _categories_line(tax: dict[str, str]) -> str:
    """Every category id, with a definition only where the id alone is not enough."""
    defs = "; ".join(f"{k} = {_TRAILING_NOTE.sub('', tax[k])}" for k in _DEFINED_CATEGORIES if k in tax)
    return f"Weakness categories (use these ids): {', '.join(tax)}. Definitions: {defs}."


def _output_block(out_dir: Path, job: dict, session: dict, rnd: dict) -> str:
    schema = instrument(session, TEMPLATE_DIR / "review_schema.md")
    scales = scales_for(session)
    tax = session["review_config"]["categories"] if "review_config" in session else \
        load_json(PROTOCOL_DIR / "taxonomy.json")["categories"]
    scale_lines = []
    if job["overall"]:
        scale_lines += [f"Rating scale (preliminary recommendation): {scale_wording(scales['overall'])}",
                        f"Confidence scale: {scale_wording(scales['confidence'])}"]
    if not job["sections"]:
        scale_lines.append(f"Section score scale: {scales['section']['wording']}")
    return "\n".join([
        "## 6. What you write (exactly three files)",
        f"Write them into `{out_dir}`.",
        "1. `review.md` - the review as submitted on the review site: the headings above, then a "
        "'Section scores' table. Under Weaknesses, write numbered plain paragraphs, most important "
        "first, and say in words which are your main concerns. No bold titles, no tags such as "
        "\"(major, decisive)\", no weakness ids, no JSON field names (unless your card asks for that style).",
        f"2. `review.json` - the same review, machine-readable, format below: `job_id`='{job['job_id']}', "
        f"`reviewer_id`='{job['reviewer']}', `round`={rnd['round']}, `stage`='initial', "
        f"`paper_sha256`='{rnd['paper']['main_pdf_sha256']}'.",
        f"3. `debrief.md` - OUT of character, at most {DEBRIEF_WORDS} words, no scientific point beyond "
        "the review and no repeat of it:",
        "   - Fixes: one bullet per root cause: weakness ids, quote or PDF location, smallest fix, fix "
        "type (writing, existing_evidence, new_experiment), effect on your rating.",
        "   - Gaps: one line per `[lazy]` point (persona heuristic, not checked evidence), per material "
        "reading gap, and on a first-impression change.",
        "   - Harness issues: one line each (identified copy, broken extraction, wrong section mapping, "
        "missing file).",
        "",
        *scale_lines,
        _categories_line(tax),
        "",
        schema,
        "",
        "When the three files are written, reply with one line: the overall rating (or 'sections "
        "only'), confidence, and the number of major weaknesses. Do not paste the review.",
    ])


def write_initial_prompts(session: dict, rnd: dict, personas: dict[str, dict], round_path: Path) -> list[Path]:
    """Write one prompt file per job; return their paths. The figure job (kind 'figures') gets its own prompt."""
    from .figure_prompts import figure_initial_prompt  # lazy: figure_prompts imports this module

    out: list[Path] = []
    pdir = round_path / "prompts" / "initial"
    pdir.mkdir(parents=True, exist_ok=True)
    for job in rnd["jobs"]:
        if job.get("stage", "initial") != "initial":
            continue
        path = pdir / f"{job['job_id']}.md"
        build = figure_initial_prompt if job.get("kind") == "figures" else initial_prompt
        path.write_text(build(session, rnd, job, personas, round_path), encoding="utf-8")
        review_dir(round_path, job).mkdir(parents=True, exist_ok=True)
        out.append(path)
    return out
