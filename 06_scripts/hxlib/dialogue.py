"""Fight-and-satisfy dialogue between the authors (writer agent or user) and the same reviewers.

round N (initial reviews) -> FEEDBACK.md (detailed to-do list) + writer/RESPONSE.md (answer sheet)
-> authors answer every point and revise the paper -> round N+1: each feedback reviewer (a fresh
instance of the same persona, given its own thread) checks the answers against the NEW draft and
marks each point satisfied / partly / not_satisfied, may raise new issues, and re-scores.
Open points carry forward until satisfied. Held-out reviewers never see any of this.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional

from .common import PERSONA_DIR, PROTOCOL_DIR, TEMPLATE_DIR, list_rounds, load_json, load_scales, \
    review_dir, round_dir, save_json, scale_wording
from .prompts import read_text, rubric_for
from .figure_job import figure_summary, figure_table

from .venues import instrument, scales_for, reviewer_card, common_rules, venue_block, careful

logger = logging.getLogger(__name__)

STATUSES = ("satisfied", "partly", "not_satisfied")
DECISIONS = ("fix_text", "use_existing_evidence", "contest", "constrained", "accept_as_limitation",
             "request_experiment", "low_value")
# Answer sheet parsing: a `###` heading that starts with a point id (`### R03:W1`, optionally followed
# by text) starts a block; any other ATX heading outside a code fence ends it.
_HEADING = re.compile(r"^ {0,3}(?P<hashes>#{1,6})(?:[ \t]+(?P<title>.*?))?[ \t]*$")
_ITEM_ID = re.compile(r"^(?P<id>[A-Za-z0-9\-]+:W\d+)(?!\w)")
_FENCE = re.compile(r"^ {0,3}(```|~~~)")
_SEV = {"major": 0, "moderate": 1, "minor": 2}


def _item(job: dict, w: dict, round_no: int, status: str) -> dict:
    return {"id": f"{job['job_id']}:{w['id']}", "job_id": job["job_id"], "wid": w["id"],
            "reviewer": job["reviewer"], "severity": w.get("severity"), "decisive": bool(w.get("decisive")),
            "category": w.get("category"), "location": w.get("location"), "text": w.get("text"),
            "suggested_fix": w.get("suggested_fix", ""), "would_change_mind": w.get("would_change_mind", ""),
            "fixable_by": w.get("fixable_by"), "raised_in_round": round_no, "status": status,
            **{k: w[k] for k in ("figure_id", "defect") if k in w}}  # figure job (FIG) points only


def round_items(rnd: dict, round_path: Path) -> list[dict]:
    """Points still open after this round, for every feedback reviewer, with full details."""
    items: list[dict] = []
    for job in (j for j in rnd["jobs"] if j.get("group", "feedback") == "feedback"):
        if job.get("stage", "initial") == "initial":
            path = review_dir(round_path, job) / "review.json"
            if path.exists():
                items += [_item(job, w, rnd["round"], "open") for w in load_json(path)["weaknesses"]]
            continue
        sdir = round_path / "satisfaction" / job["job_id"]
        if not (sdir / "satisfaction.json").exists():
            continue
        data = load_json(sdir / "satisfaction.json")
        prev = {i["wid"]: i for i in load_json(sdir / "OPEN_ITEMS.json")}
        for st in data["items"]:
            if st["status"] != "satisfied" and st["id"] in prev:
                items.append({**prev[st["id"]], "status": st["status"], "reviewer_reason": st.get("reason", ""),
                              "remaining_ask": st.get("remaining_ask", "")})
        items += [_item(job, w, rnd["round"], "new") for w in data.get("new_issues", [])]
    items.sort(key=lambda i: (not i["decisive"], _SEV.get(i["severity"], 3), i["id"]))
    return items


def _section_rows(rnd: dict, round_path: Path) -> list[tuple]:
    rows = []
    for job in (j for j in rnd["jobs"] if j.get("group", "feedback") == "feedback"):
        name = "satisfaction/" + job["job_id"] + "/satisfaction.json" if job.get("stage") == "satisfy" \
            else None
        path = round_path / name if name else review_dir(round_path, job) / "review.json"
        if path.exists():
            for sec, e in load_json(path).get("section_scores", {}).items():
                rows.append((e["score"], sec, job["job_id"], e.get("main_issue", ""), e.get("location", ""),
                             e.get("one_point_fix", "")))
    return sorted(rows)


def write_feedback(rnd: dict, round_path: Path, personas: dict[str, dict]) -> list[dict]:
    """FEEDBACK.md + FEEDBACK.json: every open point and every section score, most important first."""
    items = round_items(rnd, round_path)
    save_json(round_path / "FEEDBACK.json", items)
    n_dec = sum(i["decisive"] for i in items)
    lines = [f"# Feedback to act on - round {rnd['round']:02d}", "",
             f"{len(items)} open points ({n_dec} decisive). If the task is review-only, report these "
             "findings and finish. If revision is requested, answer the points in `writer/RESPONSE.md` "
             "and verify the changed evidence. Do not start another round without a new draft or "
             "filled author answers; unresolved experiment requests are blockers, not a reason to repeat unchanged work.", ""]
    for i in items:
        name = personas.get(i["reviewer"], {}).get("name", i["reviewer"])
        tags = ", ".join(t for t in (i["severity"], "decisive" if i["decisive"] else "", i["category"]) if t)
        lines += [f"### {i['id']} - {tags} - {name} [{i['status']}]",
                  f"- **Where:** {i['location']}", f"- **Complaint:** {i['text']}",
                  f"- **Their suggested fix:** {i['suggested_fix'] or '-'}",
                  f"- **What would satisfy them:** {i['would_change_mind'] or '-'}",
                  f"- **Fixable by (their guess):** {i['fixable_by']}"]
        if i.get("figure_id"):
            lines.append(f"- **Figure / defect:** {i['figure_id']} / {i.get('defect') or '-'}")
        if i.get("reviewer_reason"):
            lines += [f"- **Their last verdict ({i['status']}):** {i['reviewer_reason']}",
                      f"- **Still asking for:** {i.get('remaining_ask') or '-'}"]
        lines.append("")
    lines += ["## Section scores (lowest first)", "", "| score | section | reviewer | main issue | where | one-point fix |",
              "|---|---|---|---|---|---|"]
    lines += [f"| {s} | {sec} | {jid} | {iss} | {loc} | {fix} |" for s, sec, jid, iss, loc, fix in
              _section_rows(rnd, round_path)]
    figures = figure_summary(rnd, round_path)
    if figures:
        lines += ["", "## Figure scores (FIG job, lowest first)", "", *figure_table(figures, detailed=True)]
    lines += ["", "Detailed causes and smallest fixes per reviewer: `reviews/<id>/debrief.md` (round of the "
              "first review)."]
    (round_path / "FEEDBACK.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return items


def write_response_scaffold(round_path: Path) -> Path:
    """writer/RESPONSE.md with one block per open point (kept if it already exists)."""
    path = round_path / "writer" / "RESPONSE.md"
    if path.exists():
        return path
    items = load_json(round_path / "FEEDBACK.json")
    lines = ["# Author response", "", "One block per point. `Decision` is one of: " + ", ".join(DECISIONS) + ".",
             "Reviewers accept only answers that point to the NEW draft (line, section, table, figure).",
             "Promises for later do not count. Do not rename the `###` headings. Each reviewer sees only "
             "the text under its own heading, up to the next heading of any level: put general notes "
             "under a heading of their own, not inside a block.", ""]
    for i in items:
        quote = [f"> {line}" for line in str(i["text"]).splitlines()] or [">"]
        lines += [f"### {i['id']}", *quote, "", "Decision:", "Changed (where in the new draft):",
                  "Answer to the reviewer (cite lines/tables/figures of the new draft):", ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _item_heading(line: str) -> tuple[bool, Optional[str]]:
    """(line is a `###` heading, the point id it starts with or None)."""
    heading = _HEADING.match(line)
    if heading is None or len(heading.group("hashes")) != 3:
        return False, None
    item = _ITEM_ID.match(heading.group("title") or "")
    return True, item.group("id") if item else None


def _block_text(lines: list[str]) -> str:
    """Text of one answer block: its lines up to the first other heading outside a code fence.

    If a code fence is left open, any heading ends the block, so a stray fence never pulls a later
    section (such as a summary for all reviewers) into this block.
    """
    for fence_aware in (True, False):
        fenced, end = False, len(lines)
        for k, line in enumerate(lines):
            if fence_aware and _FENCE.match(line):
                fenced = not fenced
            elif not fenced and _HEADING.match(line):
                end = k
                break
        if not fenced:
            break
    return "\n".join(lines[:end]).strip()


def parse_response(path: Path, open_ids: Optional[set[str]] = None) -> dict[str, str]:
    """Map item id -> the authors' block text.

    A block starts at a `### <job>:W<n>` heading (text may follow the id, e.g. `### R03:W1 (novelty)`)
    and ends at the next such heading, even inside a code fence, or at any other markdown heading
    outside a code fence. So neither an annotated heading nor a trailing summary section ends up in
    another reviewer's block. With `open_ids`, every `###` heading that names no open point is logged
    as a warning: its text reaches no reviewer.
    """
    if not path.exists():
        return {}
    segments: dict[str, list[list[str]]] = {}
    current: Optional[list[str]] = None
    for line in path.read_text(encoding="utf-8").splitlines():
        level3, key = _item_heading(line)
        if level3 and open_ids is not None and key not in open_ids:
            logger.warning("%s: heading %r names no open point; no reviewer sees its text", path, line.strip())
        if key is None:
            if current is not None:
                current.append(line)
            continue
        if key in segments:
            logger.warning("%s: point %s has more than one block; the blocks are joined", path, key)
        current = []
        segments.setdefault(key, []).append(current)
    return {key: "\n\n".join(t for t in map(_block_text, parts) if t) for key, parts in segments.items()}


def last_dialogue_round(session_path: Path, before: int) -> int:
    """Most recent non-retest round before `before`."""
    cands = [n for n in list_rounds(session_path) if n < before
             and not load_json(round_dir(session_path, n) / "ROUND.json").get("retest_of")]
    if not cands:
        raise ValueError("no previous round to answer")
    return cands[-1]


def prepare_satisfaction(session_path: Path, rnd: dict, rpath: Path) -> None:
    """For each feedback job: carry its open points forward and extract the authors' answers."""
    prev_n = last_dialogue_round(session_path, rnd["round"])
    prev_path = round_dir(session_path, prev_n)
    prev_rnd = load_json(prev_path / "ROUND.json")
    open_items = round_items(prev_rnd, prev_path)
    answers = parse_response(prev_path / "writer" / "RESPONSE.md", {i["id"] for i in open_items})
    for job in (j for j in rnd["jobs"] if j.get("group", "feedback") == "feedback"):
        mine = [i for i in open_items if i["job_id"] == job["job_id"]]
        sdir = rpath / "satisfaction" / job["job_id"]
        sdir.mkdir(parents=True, exist_ok=True)
        save_json(sdir / "OPEN_ITEMS.json", mine)
        blocks = [f"### {i['wid']}\n**Your point:** {i['text']}\n\n**Authors' answer:**\n"
                  f"{answers.get(i['id']) or '(the authors did not answer this point)'}\n" for i in mine]
        (sdir / "AUTHOR_RESPONSE.md").write_text("# Authors' answers to your points\n\n" + "\n".join(blocks),
                                                 encoding="utf-8")
        job.update(stage="satisfy", open_items=[i["wid"] for i in mine], answers_from_round=prev_n)


def _thread(session_path: Path, job_id: str, upto: int) -> list[str]:
    """Earlier files of this reviewer's thread, oldest first."""
    out: list[str] = []
    for n in list_rounds(session_path):
        if n >= upto:
            break
        rp = round_dir(session_path, n)
        r = load_json(rp / "ROUND.json")
        if r.get("retest_of"):
            continue
        job = next((j for j in r["jobs"] if j["job_id"] == job_id), None)
        if job is None:
            continue
        if job.get("stage", "initial") == "initial":
            out.append(f"round {n:02d} - your review: `{review_dir(rp, job) / 'review.md'}`")
        else:
            sd = rp / "satisfaction" / job_id
            out.append(f"round {n:02d} - authors' answers: `{sd / 'AUTHOR_RESPONSE.md'}`; your reply: "
                       f"`{sd / 'reply.md'}`")
    return out


def satisfy_prompt(session: dict, rnd: dict, job: dict, personas: dict[str, dict], rpath: Path,
                   session_path: Path) -> str:
    """Prompt for one reviewer to judge the authors' answers against the new draft."""
    from .figure_render import figure_reading_line

    persona = personas[job["reviewer"]]
    snap, sdir = rpath / "snapshot", rpath / "satisfaction" / job["job_id"]
    scales = scales_for(session)
    view = {"front": "view_front.txt", "skim": "view_skim.txt", "main": "view_main.txt",
            "full": "view_full.txt"}[job["view"]]
    figures = figure_reading_line(snap, job["view"])
    parts = [
        f"# Answer check {job['job_id']} - {session['venue']}, round {rnd['round']:02d}: the authors "
        "answered your review and revised the paper",
        "## 1. Who you are\n\n" + reviewer_card(session, persona),
        "## 2. Rules for every reviewer\n\n" + common_rules(session),
        "## 3. How to judge the answers\n\n" + instrument(session, PROTOCOL_DIR / (
            "careful_satisfaction.md" if careful(session) else "satisfaction_rules.md")),
        "## 4. Your thread so far (read in this order)\n\n" + "\n".join(
            f"- {t}" for t in _thread(session_path, job["job_id"], rnd["round"])),
        "## 5. This round\n\n"
        f"- Your open points: `{sdir / 'OPEN_ITEMS.json'}` (ids {', '.join(job['open_items']) or 'none'}).\n"
        f"- The authors' answers to them: `{sdir / 'AUTHOR_RESPONSE.md'}`.\n"
        f"- The NEW draft: `{snap / view}` and `{snap / 'main.pdf'}`"
        + (f", supplement `{snap / 'supplement.pdf'}`" if (snap / "supplement.pdf").exists() else "") + ".\n"
        + (f"- {figures}\n" if figures else "") +
        "- Nothing else: no other reviewers, no held-out folders, no LaTeX, no project folders.",
    ]
    if job["sections"]:
        parts.append(f"## 6. Re-score these sections on the new draft: {', '.join(job['sections'])}\n\n"
                     + rubric_for(job["sections"], session))
    if rnd.get("changes"):
        parts.append("## Revision navigation\n\nExtracted sections changed: "
                     + (", ".join(rnd["changes"]["changed"]) or "none")
                     + ". " + rnd["changes"]["note"]
                     + " Start with open points, the latest answers and changed evidence; consult older "
                     "thread entries only when needed to resolve an issue. Check dependent claims and "
                     "visual evidence before judging a fix. Do not reopen a resolved issue without "
                     "new contrary evidence. Record checks you did not repeat honestly in the audit.")
    parts.append("\n".join([
        "## 7. What you write (exactly two files)",
        f"1. `{sdir / 'reply.md'}` - in character, addressed to the authors: point by point, what "
        "convinced you, what did not and why, what you still need; then your updated recommendation.",
        f"2. `{sdir / 'satisfaction.json'}` - format below. `job_id`='{job['job_id']}', `round`={rnd['round']}, "
        f"`stage`='satisfy', `paper_sha256`='{rnd['paper']['main_pdf_sha256']}'.",
        "", f"Rating scale: {scale_wording(scales['overall'])}",
        f"Confidence scale: {scale_wording(scales['confidence'])}", "",
        instrument(session, TEMPLATE_DIR / "satisfaction_schema.md"),
        "" if job["overall"] else "This is a section-only job: set `overall` and `previous_rating` to null.",
        "Reply with one line: counts of satisfied / partly / not_satisfied, new issues, old -> new rating.",
    ]))
    parts.append(venue_block(session, job))
    return "\n\n".join(parts) + "\n"
