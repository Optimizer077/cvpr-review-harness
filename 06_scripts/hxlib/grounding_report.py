"""Round-level grounding report: the grounding check over every job of a round, GROUNDING.md, the
one-line summary for SCORES.md and per-job warnings for `validate`.

Held-out reviews must never reach the writer, so `round_NN/GROUNDING.md` details feedback jobs only
and gives held-out totals; held-out details go to `round_NN/heldout/GROUNDING.md`.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Iterable, Optional

from .common import list_rounds, load_json, review_dir, round_dir
from .grounding import check_grounding
from .grounding_index import plain_paper_text

logger = logging.getLogger(__name__)

_TOTAL_KEYS = ("quotes", "verified", "near", "not_found", "image_text", "skipped", "bad_anchors",
               "bad_pages", "bad_refs", "bad_sections")
_BAD_LABELS = (("bad_anchors", "bad anchor", "bad anchors"), ("bad_pages", "bad page", "bad pages"),
               ("bad_refs", "bad Fig./Tab./Eq. reference", "bad Fig./Tab./Eq. references"),
               ("bad_sections", "unknown section", "unknown sections"))


def job_paths(job: dict, round_path: Path) -> tuple[Path, Path]:
    """(JSON, markdown) outputs of a job: satisfaction.json + reply.md, or review.json + review.md."""
    if job.get("stage") == "satisfy":
        sdir = round_path / "satisfaction" / job["job_id"]
        return sdir / "satisfaction.json", sdir / "reply.md"
    out = review_dir(round_path, job)
    return out / "review.json", out / "review.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def dialogue_texts(job: dict, rnd: dict, round_path: Path) -> dict[str, str]:
    """What an answer-check reviewer was given besides the new draft and may quote: the authors'
    answers, its open points, its own earlier texts, and the draft the answers refer to."""
    if job.get("stage") != "satisfy":
        return {}
    sdir = round_path / "satisfaction" / job["job_id"]
    texts = {"authors' answers": _read(sdir / "AUTHOR_RESPONSE.md"), "open points": _read(sdir / "OPEN_ITEMS.json")}
    session = round_path.parent
    for n in (n for n in list_rounds(session) if n < rnd["round"]):
        earlier = round_dir(session, n)
        thread = [earlier / "reviews" / job["job_id"] / "review.md",
                  earlier / "satisfaction" / job["job_id"] / "reply.md",
                  earlier / "satisfaction" / job["job_id"] / "AUTHOR_RESPONSE.md"]
        texts[f"thread round {n:02d}"] = "\n".join(_read(p) for p in thread)
    prev = job.get("answers_from_round")
    if prev:
        snap = round_dir(session, int(prev)) / "snapshot"
        texts["previous draft"] = "\n".join(plain_paper_text(_read(snap / f"paper_{d}.txt"), d)
                                            for d in ("main", "supp"))
    return {k: v for k, v in texts.items() if v.strip()}


def job_grounding(job: dict, rnd: dict, round_path: Path) -> Optional[dict]:
    """Grounding findings of one job, or None when its outputs are missing or unreadable."""
    json_path, md_path = job_paths(job, round_path)
    if not json_path.exists():
        return None
    try:
        data = load_json(json_path)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        logger.warning("grounding: %s unreadable: %s", json_path, exc)
        return None
    if not isinstance(data, dict):
        return None
    findings = check_grounding(data, _read(md_path), round_path / "snapshot",
                               extra_texts=dialogue_texts(job, rnd, round_path), md_name=md_path.name)
    findings.update(group=job.get("group", "feedback"), stage=job.get("stage", "initial"))
    return findings


def round_grounding(rnd: dict, round_path: Path) -> dict:
    """Grounding findings for every job with outputs, summed totals and the SCORES.md summary line."""
    jobs: dict[str, dict] = {}
    error = ""
    for job in rnd.get("jobs", []):
        try:
            findings = job_grounding(job, rnd, round_path)
        except FileNotFoundError as exc:  # no snapshot text: nothing to check against
            logger.warning("grounding skipped: %s", exc)
            error = str(exc)
            break
        if findings is not None:
            jobs[job["job_id"]] = findings
    result = {"round": rnd.get("round"), "jobs": jobs, "totals": sum_totals(jobs.values())}
    if error:
        result["error"] = error
    result["summary"] = grounding_summary(result)
    return result


def sum_totals(findings: Iterable[dict]) -> dict[str, int]:
    """Totals summed over several jobs' findings."""
    out = dict.fromkeys(_TOTAL_KEYS, 0)
    for f in findings:
        for key in _TOTAL_KEYS:
            out[key] += f["totals"].get(key, 0)
    return out


def _plural(n: int, one: str, many: str) -> str:
    return f"{n} {one if n == 1 else many}"


def counts_text(t: dict[str, int]) -> str:
    """'41/44 quotes verified, 2 near, 1 not found; 1 bad anchor' for a totals dict."""
    parts = [f"{t['verified']}/{t['quotes']} quotes verified"]
    parts += [f"{t[k]} {label}" for k, label in (("near", "near"), ("not_found", "not found"),
                                                  ("image_text", "possibly image text")) if t.get(k)]
    bad = [_plural(t[k], one, many) for k, one, many in _BAD_LABELS if t.get(k)]
    return ", ".join(parts) + "; " + (", ".join(bad) if bad else "no bad anchors or references")


def grounding_summary(result: dict) -> str:
    """One line for SCORES.md, e.g. 'Grounding: 41/44 quotes verified, 2 not found; 1 bad anchor (6 reviews).'"""
    n = len(result.get("jobs", {}))
    if not n:
        return "Grounding: no reviews checked" + (f" ({result['error']})." if result.get("error") else ".")
    return f"Grounding: {counts_text(result['totals'])} ({_plural(n, 'review', 'reviews')})."


def job_line(job_id: str, findings: dict) -> str:
    """'R02: 5/6 quotes verified, 1 not found; 1 bad anchor'."""
    return f"{job_id}: {counts_text(findings['totals'])}"


def grounding_warnings(findings: Optional[dict]) -> list[str]:
    """Human-readable warnings for one job (for `validate`: print them, do not fail the job)."""
    if not findings:
        return []
    out = [f"quote not found in the paper: \"{q['quote'][:120]}\" ({q['where']})"
           for q in findings["quotes"] if q["status"] == "not_found"]
    out += [f"quote differs from the paper (ratio {q['ratio']}): \"{q['quote'][:120]}\" ({q['where']}); "
            f"paper{' ' + q['at'] if q.get('at') else ''}: \"{q.get('paper_text', '')[:120]}\""
            for q in findings["quotes"] if q["status"] == "near"]
    out += [f"{b['ref']} ({b['where']}): {b['reason']}" for b in findings["bad_refs"]]
    return out


def round_warnings(rnd: dict, round_path: Path) -> dict[str, list[str]]:
    """job_id -> grounding warnings, for every job with outputs."""
    return {jid: grounding_warnings(f) for jid, f in round_grounding(rnd, round_path)["jobs"].items()}


def _job_section(job_id: str, f: dict) -> list[str]:
    lines = [f"## {job_id} ({f['group']}, {f['stage']})", "", counts_text(f["totals"]) + ".", ""]
    groups = (("not_found", "Quotes not found in the paper"),
              ("near", "Quotes that differ from the paper text (altered quote or PDF extraction noise)"),
              ("image_text", "Quotes not in the extracted text (may be text inside a figure image)"))
    for status, title in groups:
        rows = [q for q in f["quotes"] if q["status"] == status]
        if not rows:
            continue
        lines.append(f"{title}:")
        for q in rows:
            row = f"- \"{q['quote']}\" (`{q['where']}`)"
            if status == "near":
                row += f", ratio {q['ratio']}; paper ({q.get('at', '?')}): \"{q.get('paper_text', '')}\""
            lines.append(row)
        lines.append("")
    if f["bad_refs"]:
        lines.append("References the paper does not have:")
        lines += [f"- {b['ref']} (`{b['where']}`): {b['reason']}" for b in f["bad_refs"]]
        lines.append("")
    if f["skipped_quotes"]:
        lines += [(f"Skipped {len(f['skipped_quotes'])} quoted passages as the reviewer's own or proposed "
                   "wording, or titles of cited works."), ""]
    return lines


_TABLE_HEAD = "| job | quotes | verified | near | not found | bad anchors | bad pages | bad refs | unknown sections |"
_INTRO = ("Automatic check of quotes, line anchors, page numbers, Fig./Tab./Eq. numbers and section ids "
          "against this round's snapshot (main paper and supplement). Warnings, not validation failures. "
          "`near` = a quote that differs slightly from the paper text (altered quote or PDF extraction noise); "
          "`not found` = no matching passage. Quotes marked as paraphrase or proposed wording are skipped.")


def write_grounding_md(result: dict, round_path: Path) -> Path:
    """Write round_NN/GROUNDING.md (feedback jobs in detail, held-out totals only) and, when there
    are held-out jobs, round_NN/heldout/GROUNDING.md with their details. Returns the round file."""
    jobs = result.get("jobs", {})
    shown = {j: f for j, f in jobs.items() if f.get("group") != "heldout"}
    held = {j: f for j, f in jobs.items() if f.get("group") == "heldout"}
    head = [f"# Grounding - round {result.get('round', 0):02d}", "", result.get("summary", grounding_summary(result)),
            "", _INTRO, "", _TABLE_HEAD, "|---|---|---|---|---|---|---|---|---|"]
    rows = [(j, f["totals"]) for j, f in shown.items()]
    if held:
        rows.append((f"held-out ({_plural(len(held), 'job', 'jobs')})", sum_totals(held.values())))
    head += [f"| {j} | {t['quotes']} | {t['verified']} | {t['near']} | {t['not_found']} | {t['bad_anchors']} | "
             f"{t['bad_pages']} | {t['bad_refs']} | {t['bad_sections']} |" for j, t in rows]
    body = [line for j, f in shown.items() for line in _job_section(j, f)]
    note = ["", "Held-out details are in `heldout/GROUNDING.md`."] if held else []
    path = round_path / "GROUNDING.md"
    path.write_text("\n".join(head + note + [""] + body).rstrip() + "\n", encoding="utf-8")
    if held:
        lines = [f"# Grounding - round {result.get('round', 0):02d}, held-out reviews", "", _INTRO, ""]
        lines += [line for j, f in held.items() for line in _job_section(j, f)]
        (round_path / "heldout").mkdir(exist_ok=True)
        (round_path / "heldout" / "GROUNDING.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


__all__ = ["dialogue_texts", "grounding_summary", "grounding_warnings", "job_grounding", "job_line",
           "job_paths", "round_grounding", "round_warnings", "sum_totals", "write_grounding_md"]
