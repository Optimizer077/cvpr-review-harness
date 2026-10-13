"""Prompts for the opt-in figure review job (FIG, persona F01).

The figure reader sees real images: a crop of every figure and table, grayscale and colour-vision
previews, page images and the measured facts in FIGURES.md, plus the main text to check claims
against. Initial prompt order: persona card, figure review rules, figure rubric, the
`figures_tables` section rubric, inputs, outputs with the figure schema (the generic review
schema is replaced by a short list of the rules the figure schema does not show). The
answer-check prompt adds, per open point tied to a figure, the previous and the new crop path.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional

from .common import HARNESS_ROOT, PERSONA_DIR, PROTOCOL_DIR, TEMPLATE_DIR, load_json, review_dir, \
    round_dir, sha256_file
from .dialogue import _thread  # the reviewer's own earlier rounds, shared with satisfy_prompt
from .figure_job import FALLBACK_TEXTS, FIGURE_SECTION, caption_ids, figure_criteria, image_path, \
    inventory_ids, load_inventory
from .prompts import rubric_for
from .venues import careful, instrument, scales_for, venue_block

logger = logging.getLogger(__name__)

# Weakness categories a figure finding can carry (the defect table's category column uses only these).
FIGURE_CATEGORIES = ("figures", "visual_results", "notation", "overclaiming", "clarity", "correctness")
ANCHORS_PER_PAGE = 10  # view_main.txt has margin line numbers when it averages this many `L###` lines a page
_ANCHOR_LINE = re.compile(r"^L\d{3,4} ", re.MULTILINE)
_PAGE_MARK = re.compile(r"^===== \[main p\.\d+\] =====$", re.MULTILINE)
# The review.json rules that figure_schema.md does not show (it replaces review_schema.md here).
_REVIEW_RULES = (
    "### review.json: rules the example below does not show\n\n"
    "- Weakness `id`: W1, W2, ... `severity`: major | moderate | minor. `decisive`: true only when this "
    "point alone would keep you from recommending acceptance. `fixable_by`: writing | existing_evidence | "
    "new_experiment | not_fixable (your honest guess).\n"
    "- `suggested_fix` and `would_change_mind` are required and specific: the authors answer each point, "
    "and you later judge whether the answer satisfies you. `location` is required for every weakness, "
    "strength and section entry.\n"
    "- `section_scores` has exactly `figures_tables`, with exactly the criteria of its rubric above.")


def has_line_anchors(rnd: dict, snap: Path) -> bool:
    """Whether the paper has margin line numbers (`L###` anchors in view_main.txt).

    Uses `rnd["paper"]["line_numbers"]` when the snapshot recorded it; otherwise counts anchor
    lines per page of view_main.txt (camera-ready PDFs have none, or a few stray numbers).
    """
    known = rnd.get("paper", {}).get("line_numbers")
    if known is not None:
        return bool(known)
    path = snap / "view_main.txt"
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    pages = len(_PAGE_MARK.findall(text)) or rnd.get("paper", {}).get("main_pages") or 1
    return len(_ANCHOR_LINE.findall(text)) >= ANCHORS_PER_PAGE * pages


def optional_instrument(session: dict, path: Path) -> str:
    """Frozen (or live) text of a figure protocol file, or its built-in fallback when absent.

    New sessions freeze the fallback under the file's key (venues.freeze), so the text a session
    starts with never changes; the fallback here covers sessions without frozen instruments.
    """
    key = path.relative_to(HARNESS_ROOT).as_posix()
    if "instruments" in session:
        text = session["instruments"]["texts"].get(key)
    else:
        text = path.read_text(encoding="utf-8") if path.exists() else None
    if text is None:
        logger.warning("%s is not available; using the built-in fallback text", key)
        return FALLBACK_TEXTS[key]
    return text


def _figure_lines(snap: Path, items: list[dict]) -> list[str]:
    """One line per figure/table: crop (or page image), previews, measured flags and text caveats."""
    lines = []
    for item in items:
        files = [f"crop `{image_path(snap, item)}`" if item.get("crop")
                 else f"NOT LOCATED, use page image `{image_path(snap, item)}`"]
        files += [f"{name} `{snap / item[key]}`" for key, name in
                  (("gray_preview", "gray"), ("cvd_preview", "deuteranopia")) if item.get(key)]
        notes = f"; flags: {'; '.join(item['flags'])}" if item.get("flags") else ""
        if item.get("min_script_pt") is not None:
            notes += f"; sub/superscripts {item['min_script_pt']} pt (not in min text)"
        if item.get("text_not_measured"):
            notes += ("; plot text unmeasured (raster or outlined): judge it on the page image "
                      f"`{snap / item['page_image']}`")
        lines.append(f"- `{item['id']}` ({item['label']}, p.{item['page']}): " + ", ".join(files) + notes)
    return lines


def _keys_line(snap: Path, items: Optional[list[dict]]) -> str:
    """Which ids figure_scores must have (from the inventory, else from the extracted captions)."""
    if items is None:
        found = caption_ids(snap)
        return ("No figure inventory exists for this snapshot. `figure_scores` keys: at least "
                f"{', '.join(found) or 'every figure and table you find'} (from the extracted captions); "
                "name any other figure `fig_<n>` and table `tab_<n>` by the paper's own numbering.")
    main, every = inventory_ids(items)
    supp = [i for i in every if i not in main]
    return (f"`figure_scores` keys: exactly these main-paper ids: {', '.join(main) or 'none'}"
            + (f"; supplement ids are optional: {', '.join(supp)}" if supp else "") + ".")


def _criteria_line(session: dict, rubric: str) -> str:
    """The frozen role, criterion and defect keys that validation checks.

    The lists are printed only when the rubric text above lacks one of the keys (the built-in
    fallback rubric has no defect table); otherwise the rubric is the one place they appear.
    """
    fc = figure_criteria(session)
    nullable = ", ".join(fc["nullable"])
    if all(f"`{key}`" in rubric for key in (*fc["roles"], *fc["criteria"], *fc["defects"])):
        return ("Machine-checked keys (frozen for this session): the role, criterion and defect ids of this "
                f"rubric, spelled as in its backticks; only {nullable} may be null.")
    return ("Machine-checked keys (frozen for this session): roles " + ", ".join(fc["roles"])
            + "; criteria " + ", ".join(fc["criteria"]) + f" (nullable: {nullable}); defects "
            + ", ".join(fc["defects"]) + ".")


def _rubric_block(session: dict) -> str:
    """Figure rubric text followed by the machine-checked keys line."""
    rubric = optional_instrument(session, PROTOCOL_DIR / "figure_rubric.md")
    return rubric + "\n\n" + _criteria_line(session, rubric)


def _inputs_block(snap: Path, items: Optional[list[dict]], title: str, rnd: dict) -> str:
    """Files the figure reader may open, with every crop and preview listed."""
    lines = [title]
    if items is None:
        lines.append(f"- No figure inventory or crops were produced for this snapshot: open the pages of "
                     f"`{snap / 'main.pdf'}` (Read tool with `pages`) to see each figure and table at "
                     "print size. You cannot measure text size or resolution; say so instead of guessing.")
    else:
        lines += [f"- Figure inventory: `{snap / 'FIGURES.md'}` (crop, page, caption start, smallest text "
                  "in pt, lowest image ppi, first mention, flags) and the same as JSON in "
                  f"`{snap / 'figures' / 'figures.json'}`. These measurements are facts about the PDF: use "
                  "them instead of estimating text size, resolution or whether a figure is referenced.",
                  "- Each figure and table (open every PNG with the Read tool; the crop first, then the "
                  "previews):"]
        lines += ["  " + line for line in _figure_lines(snap, items)]
        lines.append(f"- Page images `{snap / 'pages' / 'main_pNN.png'}` (NN = page number) show each "
                     "figure at its place and print size.")
    anchors = ("with `L###` line anchors" if has_line_anchors(rnd, snap)
               else "no margin line numbers: cite page and figure panel")
    lines += [f"- The main text `{snap / 'view_main.txt'}` ({anchors}) to check what the text "
              f"and the tables claim about each figure; `{snap / 'main.pdf'}` when a crop is cut or missing.",
              "- You open the supplement only if a main-paper figure defers to it; then record it in "
              "`reading.opened_supplement`." if (snap / "supplement.pdf").exists() else
              "- No supplement PDF was provided.",
              "- You do not search the web. Do NOT open any other file: no other reviews, no session "
              "or harness files, no LaTeX or plotting sources, no project folders."]
    return "\n".join(lines)


def _scales_lines(session: dict) -> list[str]:
    """Score scales and weakness categories (frozen when the session has a review_config)."""
    scales = scales_for(session)
    tax = session["review_config"]["categories"] if "review_config" in session else \
        load_json(PROTOCOL_DIR / "taxonomy.json")["categories"]
    tax = {k: tax[k] for k in FIGURE_CATEGORIES if k in tax} or tax
    return [f"Figure and section score scale: {scales['section']['wording']}",
            f"Criterion scale: {scales['criterion']['wording']}",
            "Weakness categories (use these ids): " + "; ".join(f"{k} ({v})" for k, v in tax.items())]


def _head(session: dict, persona: dict, title: str) -> list[str]:
    """Title, persona card and figure review rules: the first parts of both FIG prompts."""
    return [title,
            "## 1. Who you are\n\n" + instrument(session, PERSONA_DIR / persona["file"]),
            "## 2. Figure review rules\n\n" + optional_instrument(session, PROTOCOL_DIR / "figure_review_rules.md")]


def figure_initial_prompt(session: dict, rnd: dict, job: dict, personas: dict[str, dict],
                          round_path: Path) -> str:
    """Initial prompt for the figure job: score every main-paper figure and table."""
    snap, out_dir = round_path / "snapshot", review_dir(round_path, job)
    items = load_inventory(snap)
    parts = _head(session, personas[job["reviewer"]],
                  f"# Figure review job {job['job_id']} - {session['venue']}, session {session['name']}, "
                  f"round {rnd['round']:02d}, stage: initial independent review\n\nYou review the figures "
                  "and tables of one submission. Read this whole prompt first.")
    parts += ["## 3. Figure rubric\n\n" + _rubric_block(session),
              "## 4. Section you score (section-only job)\n\nScore exactly `figures_tables`. Do NOT give an "
              "overall rating: `overall` and `first_impression` are null.\n\n" + rubric_for([FIGURE_SECTION], session),
              _inputs_block(snap, items, "## 5. What you read (and nothing else)", rnd)
              + "\n\n**Work order.** One figure at a time: describe what the graphics show (perceived "
              "message), compare it with what the caption and text claim (intended message), check numbers "
              "against the tables and FIGURES.md, then critique with a defect name. Judge unmeasured plot "
              "text on the page image, not the crop. Check each strength against every figure it names."]
    parts.append("\n".join([
        "## 6. What you write (exactly three files)",
        f"1. `{out_dir / 'review.md'}` - Summary, Strengths, Weaknesses (most important first, each naming "
        "its figure id and defect), then a 'Figure scores' table (id | role | score | main issue) and a "
        "'Section scores' table.",
        f"2. `{out_dir / 'review.json'}` - schema below. `job_id`='{job['job_id']}', "
        f"`reviewer_id`='{job['reviewer']}', `round`={rnd['round']}, `stage`='initial', "
        f"`paper_sha256`='{rnd['paper']['main_pdf_sha256']}'.",
        f"3. `{out_dir / 'debrief.md'}` - OUT of character: the smallest useful fix per figure, grouped by "
        "cause; which fixes would change plotted data, axis limits, baselines shown or crop locations "
        "(evidence edits that need the authors' approval, not presentation edits); and what you could "
        "not determine from the images.",
        "", _keys_line(snap, items), "", *_scales_lines(session), "",
        _REVIEW_RULES, "",
        instrument(session, TEMPLATE_DIR / "figure_schema.md"), "",
        "When the three files are written, reply with one line: the number of figures and tables "
        "scored, the lowest figure score and the number of weaknesses. Do not paste the review."]))
    parts.append(venue_block(session, job))
    return "\n\n".join(p for p in parts if p) + "\n"


def _crop_pairs(open_items: list[dict], prev_snap: Path, prev_items: Optional[list[dict]],
                snap: Path, items: Optional[list[dict]]) -> list[str]:
    """Per open point: the previous and the new crop of its figure, matched by id."""
    old = {i["id"]: i for i in prev_items or []}
    new = {i["id"]: i for i in items or []}
    lines = []
    for point in open_items:
        fid = point.get("figure_id")
        tag = f"- {point['wid']} ({fid or 'no figure id'}, {point.get('defect') or 'no defect'}): "
        if not fid or fid == "global":
            lines.append(tag + "not tied to one figure; check the figures the point names.")
            continue
        before = str(image_path(prev_snap, old[fid])) if fid in old else None
        after = str(image_path(snap, new[fid])) if fid in new else None
        same = (before and after and Path(before).exists() and Path(after).exists()
                and sha256_file(Path(before)) == sha256_file(Path(after)))
        lines.append(tag + f"previous `{before or 'not in the previous inventory'}`; new `"
                     + (after or "not found in the new inventory (renumbered or removed? check FIGURES.md)")
                     + "`" + (" (byte-identical: this figure did not change)" if same else ""))
    return lines


def figure_satisfy_prompt(session: dict, rnd: dict, job: dict, personas: dict[str, dict], rpath: Path,
                          session_path: Path) -> str:
    """Answer-check prompt for the figure job: judge answers on old vs new crops and re-score all figures."""
    snap, sdir = rpath / "snapshot", rpath / "satisfaction" / job["job_id"]
    items = load_inventory(snap)
    prev_snap = round_dir(session_path, job["answers_from_round"]) / "snapshot"
    open_items = load_json(sdir / "OPEN_ITEMS.json")
    parts = _head(session, personas[job["reviewer"]],
                  f"# Answer check {job['job_id']} - {session['venue']}, round {rnd['round']:02d}: the authors "
                  "answered your figure review and revised the paper")
    parts += ["## 3. How to judge the answers\n\n" + instrument(session, PROTOCOL_DIR / (
                  "careful_satisfaction.md" if careful(session) else "satisfaction_rules.md"))
              + "\n\nFor a point tied to a figure, compare its previous crop with its new crop (listed in "
              "section 5). The point is satisfied only if the named defect is gone in the new crop. A new "
              "version that changes what data is shown (axis limits or direction, removed baselines or "
              "error bars, different crops or zoom regions) is not a fix: keep the point open unless the "
              "change is neutral, and raise a new issue (defect unfair_comparison or misleading_encoding). "
              "Do not prefer a version for decoration, saturation or density. You give no overall rating, so "
              "the rating base rates above do not apply; re-score every figure and the section instead.",
              "## 4. Your thread so far (read in this order)\n\n" + "\n".join(
                  f"- {t}" for t in _thread(session_path, job["job_id"], rnd["round"])),
              _inputs_block(snap, items, "## 5. This round: the NEW draft", rnd)
              + f"\n- Your open points: `{sdir / 'OPEN_ITEMS.json'}` (ids {', '.join(job['open_items']) or 'none'})."
              f"\n- The authors' answers to them: `{sdir / 'AUTHOR_RESPONSE.md'}`."
              "\n\nPrevious and new crop per open point:\n"
              + ("\n".join(_crop_pairs(open_items, prev_snap, load_inventory(prev_snap), snap, items)) or "- none"),
              "## 6. Re-score every figure and the section on the new draft\n\n"
              + _rubric_block(session) + "\n\n" + _keys_line(snap, items) + "\n\n"
              + rubric_for([FIGURE_SECTION], session)]
    parts.append("\n".join([
        "## 7. What you write (exactly two files)",
        f"1. `{sdir / 'reply.md'}` - addressed to the authors: point by point, what the new crops show, what "
        "convinced you, what did not and why, what you still need.",
        f"2. `{sdir / 'satisfaction.json'}` - format below. `job_id`='{job['job_id']}', `round`={rnd['round']}, "
        f"`stage`='satisfy', `paper_sha256`='{rnd['paper']['main_pdf_sha256']}'. This is a section-only "
        "job: set `overall` and `previous_rating` to null. Add `figure_scores` for the new snapshot; every "
        "entry of `new_issues` has `figure_id` and `defect`.",
        "", *_scales_lines(session), "",
        instrument(session, TEMPLATE_DIR / "satisfaction_schema.md"), "",
        instrument(session, TEMPLATE_DIR / "figure_schema.md"), "",
        "Reply with one line: counts of satisfied / partly / not_satisfied, new issues, lowest figure score."]))
    parts.append(venue_block(session, job))
    return "\n\n".join(p for p in parts if p) + "\n"
