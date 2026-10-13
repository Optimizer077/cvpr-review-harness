"""Build self-contained reviewer prompts for the initial (independent) review stage.

A prompt inlines the persona card, the common reviewer rules, the CVPR form (whole-paper jobs),
and the rubric of the assigned sections, then lists the only files the reviewer
may read and the exact files it must write.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional

from .common import (PERSONA_DIR, PROTOCOL_DIR, TEMPLATE_DIR, load_json, load_scales,
                     review_dir, scale_wording)

from .venues import instrument, scales_for, careful, reviewer_card, common_rules, venue_block

logger = logging.getLogger(__name__)

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


def read_text(path: Path) -> str:
    """Read a UTF-8 text file."""
    return path.read_text(encoding="utf-8")


def rubric_for(sections: list[str], session: Optional[dict] = None) -> str:
    """Return the rubric blocks (`## <key>` headings in section_rubrics.md) for the given sections."""
    text = instrument(session or {}, PROTOCOL_DIR / "section_rubrics.md")
    blocks = re.split(r"(?m)^## ", text)
    head, chunks = blocks[0], {b.split("\n", 1)[0].strip(): "## " + b for b in blocks[1:]}
    picked = [chunks[s] for s in sections if s in chunks]
    missing = [s for s in sections if s not in chunks]
    if missing:
        logger.warning("No rubric block for sections %s", missing)
    return head.strip() + "\n\n" + "\n".join(picked)


def initial_prompt(session: dict, rnd: dict, job: dict, personas: dict[str, dict],
                   round_path: Path) -> str:
    """Compose the initial-review prompt for one job."""
    persona = personas[job["reviewer"]]
    snap = round_path / "snapshot"
    out_dir = review_dir(round_path, job)
    view_file, view_desc = _VIEW_TEXT[job["view"]]
    has_supp = (snap / "supplement.pdf").exists()
    supp_line = _SUPP_POLICY[persona.get("reads_supplement", "if_needed")] if has_supp else \
        "No separate supplement PDF was provided; check appendices in main.pdf."
    if job["view"] == "full" and has_supp:
        supp_line = _SUPP_POLICY["yes"]
    venue = session["venue"]
    parts: list[str] = [
        f"# Review job {job['job_id']} - {venue}, session {session['name']}, round {rnd['round']:02d}, "
        "stage: initial independent review",
        f"You are about to act as one simulated reviewer for {venue}. Read this whole prompt first. "
        "Stay in character for the review; step out of character only in `debrief.md`.",
        "## 1. Who you are\n\n" + reviewer_card(session, persona) + ("" if careful(session) else _leniency_line(persona)),
        "## 2. Rules for every reviewer\n\n" + common_rules(session),
    ]
    if job["overall"]:
        if session.get("venue_profile", {}).get("venue", "cvpr") == "cvpr":
            parts.append("## 3. Review form\n\n" + instrument(session, PROTOCOL_DIR / "cvpr_form.md"))
        else:
            parts.append("## 3. Review report\n\nUse Summary, Strengths, Weaknesses, Preliminary recommendation, Justification and Confidence headings. Add decision-relevant questions and limitations; assess the venue dimensions specified below.")
    else:
        parts.append("## 3. Section-only job\n\nThis job scores sections only. Do NOT give an overall "
                     "rating: set `overall` to null in review.json and omit the rating fields in review.md. "
                     "Still write strengths, weaknesses and questions for the assigned sections.")
    if job["sections"]:
        parts.append("## 4. Sections you score (harness addition to the official form)\n\n"
                     f"Score exactly these sections: {', '.join(job['sections'])}.\n\n"
                     + rubric_for(job["sections"], session))
    parts.append(_reading_block(snap, view_file, view_desc, supp_line, persona, job, session))
    parts.append(_output_block(out_dir, job, session, rnd))
    parts.append(venue_block(session, job))
    return "\n\n".join(parts) + "\n"


def _leniency_line(persona: dict) -> str:
    """Fixed calibration offset of this persona relative to a calibrated reviewer."""
    off = float(persona.get("leniency", 0.0))
    if off == 0:
        return "\n\n**Your calibration:** you rate like a typical calibrated CVPR reviewer."
    side = "above" if off > 0 else "below"
    return (f"\n\n**Your calibration:** on average you rate about {abs(off):g} level(s) {side} a "
            "calibrated CVPR reviewer for the same paper. Keep this offset; it is part of who you are.")


def _reading_block(snap: Path, view_file: str, view_desc: str, supp_line: str, persona: dict,
                   job: dict, session: dict) -> str:
    sec_files = ", ".join(f"`{snap / 'sections' / (s + '.txt')}`" for s in job["sections"])
    web = ("You MAY use WebSearch/WebFetch to look for the closest prior work, the way a real reviewer "
           "searches before writing 'this resembles X'. Cite only papers you actually found (title, "
           "venue or arXiv id, URL). Do not search for the submission itself or try to identify its "
           "authors (double-blind)." if persona.get("web_search") or careful(session) else
           "You do not search the web; you rely on what you already know, as this reviewer would.")
    return "\n".join([
        "## 5. What you read (and nothing else)",
        f"- Your reading view: `{snap / view_file}` - {view_desc}",
        f"- Assigned section texts (same content, split by section): {sec_files or 'none'}",
        f"- The review-copy PDF: `{snap / 'main.pdf'}`. Look at figures by reading PDF pages "
        "(Read tool with `pages`). Cite locations as `L###` line anchors, page numbers, "
        "`Fig. N`, `Tab. N` or `Eq. N`.",
        f"- {supp_line}",
        f"- {web}",
        f"- Review period: {session['venue']}. Prior-work search boundary: {session.get('prior_work_cutoff') or 'none assumed'}. "
        "Apply the venue policy below; date alone does not establish a mandatory comparison.",
        "- Do NOT open any other file: no other reviews, no earlier rounds, no session or harness "
        "files, no author notes, no project folders, no LaTeX sources. You are a reviewer who only "
        "received the PDF.",
        "",
        ("**Reading order.** Map the contribution, read and verify the evidence, then form your recommendation. Set first_impression to null. Record anything not checked." if careful(session) else
         "**Reading order.** Skim the opening and record first_impression before the detailed read. Then read according to the persona and explain changes in your final judgement."),
    ])


def _output_block(out_dir: Path, job: dict, session: dict, rnd: dict) -> str:
    schema = instrument(session, TEMPLATE_DIR / "review_schema.md")
    scales = scales_for(session)
    tax = {"categories": session["review_config"]["categories"]} if "review_config" in session else load_json(PROTOCOL_DIR / "taxonomy.json")
    return "\n".join([
        "## 6. What you write (exactly three files)",
        f"1. `{out_dir / 'review.md'}` - the in-character review as it would be submitted on the "
        "review site, following the form above, then a 'Section scores' table.",
        f"2. `{out_dir / 'review.json'}` - the same review, machine-readable, schema below. "
        f"`job_id`='{job['job_id']}', `reviewer_id`='{job['reviewer']}', `round`={rnd['round']}, "
        f"`stage`='initial', `paper_sha256`='{rnd['paper']['main_pdf_sha256']}'.",
        f"3. `{out_dir / 'debrief.md'}` - OUT of character, for the authors' writer: for every "
        "weakness and every section score below 8, quote the exact sentence, figure or table that "
        "triggered your reaction, say why a reviewer like you reacts to it, and give the smallest "
        "change (wording, order, a pointer to an existing result, a figure fix) that would have "
        "prevented it, or say that no text change can fix it. Label each of your own comments that is "
        "an unsupported heuristic under the selected venue rules (e.g. 'not novel' without a citation, 'needs more "
        "experiments' with no specific experiment, 'not SOTA' as the only reason, a request for "
        "contemporaneous work): `[lazy]`. List what you did not read and so could not credit, and "
        "say what moved you between your first impression and your final rating. The debrief never "
        "softens the in-character review.",
        "",
        f"Preliminary recommendation (overall rating) scale: {scale_wording(scales['overall'])}",
        f"Confidence scale: {scale_wording(scales['confidence'])}",
        f"Section score scale: {scales['section']['wording']}",
        "Weakness categories (use these ids): "
        + "; ".join(f"{k} ({v})" for k, v in tax["categories"].items()),
        "",
        schema,
        "",
        "When the three files are written, reply with one line: the overall rating (or 'sections "
        "only'), confidence, and the number of major weaknesses. Do not paste the review.",
    ])


def write_initial_prompts(session: dict, rnd: dict, personas: dict[str, dict], round_path: Path) -> list[Path]:
    """Write one prompt file per job; return their paths."""
    out: list[Path] = []
    pdir = round_path / "prompts" / "initial"
    pdir.mkdir(parents=True, exist_ok=True)
    for job in rnd["jobs"]:
        if job.get("stage", "initial") != "initial":
            continue
        path = pdir / f"{job['job_id']}.md"
        path.write_text(initial_prompt(session, rnd, job, personas, round_path), encoding="utf-8")
        review_dir(round_path, job).mkdir(parents=True, exist_ok=True)
        out.append(path)
    return out
