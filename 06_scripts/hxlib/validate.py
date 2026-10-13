"""Validate reviewer outputs of a round against the job list, scales, rubric criteria and taxonomy.

Agent output must be UTF-8 (a byte-order mark is accepted); other encodings are reported as a
validation failure, so `status` lists the job as pending instead of crashing. Required text fields
must be non-empty strings (null is not text). Section-only jobs have no first impression.
`previous_rating` in a satisfaction verdict must be null or a rating on the overall scale; aggregation
takes the authoritative value from the job's recorded rating (`aggregate.recorded_rating`).
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from .common import PROTOCOL_DIR, load_json, read_text, review_dir
from .figure_job import caption_ids, figure_criteria, inventory_ids, is_figure_job, load_inventory

from .venues import scales_for, check_extensions

logger = logging.getLogger(__name__)

SEVERITIES = ("major", "moderate", "minor")
FIXABLE = ("writing", "existing_evidence", "new_experiment", "not_fixable")
_WID = re.compile(r"^W\d+$")
_FIGURE_ID = re.compile(r"^(supp_)?(fig|tab)_[A-Za-z0-9_]+$")
_FIGURE_TEXT_FIELDS = ("perceived_message", "intended_message", "visible_evidence", "main_issue",
                       "location", "one_point_fix")


def _in_range(value: object, scale: dict) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and scale["min"] <= value <= scale["max"]


def _text(value: object) -> bool:
    """A required text field: a string with visible content (None, numbers and blanks fail)."""
    return isinstance(value, str) and bool(value.strip())


def _encoding_error(name: str, exc: UnicodeDecodeError) -> str:
    """Message for an agent file that is not UTF-8 (e.g. cp1252 or UTF-16 written by Windows tools)."""
    return (f"{name} is not UTF-8 text ({exc.reason} at byte {exc.start}); "
            "rewrite it as UTF-8 (a byte-order mark is accepted)")


def _load_output(path: Path) -> tuple[object, list[str]]:
    """(data, []) for a readable JSON output, else (None, [problem])."""
    try:
        return load_json(path), []
    except UnicodeDecodeError as exc:
        return None, [_encoding_error(path.name, exc)]
    except json.JSONDecodeError as exc:
        return None, [f"{path.name} is not valid JSON: {exc}"]


def _review_config(rnd: dict) -> tuple[dict[str, list[str]], set[str]]:
    """Rubric criteria and weakness categories: frozen in review_config, else the live protocol files."""
    if "review_config" in rnd:
        return rnd["review_config"]["criteria"], set(rnd["review_config"]["categories"])
    return (load_json(PROTOCOL_DIR / "section_criteria.json")["criteria"],
            set(load_json(PROTOCOL_DIR / "taxonomy.json")["categories"]))


def check_review(job: dict, rnd: dict, round_path: Path) -> list[str]:
    """Return a list of problems for one job (empty = valid)."""
    scales = scales_for(rnd)
    criteria, categories = _review_config(rnd)
    out_dir = review_dir(round_path, job)
    errs: list[str] = []
    for name in ("review.md", "review.json", "debrief.md"):
        path = out_dir / name
        if not path.exists() or path.stat().st_size < 50:
            errs.append(f"missing or empty {name}")
    if errs:
        return errs
    data, errs = _load_output(out_dir / "review.json")
    if errs:
        return errs
    if not isinstance(data, dict):
        return ["review.json must be a JSON object"]
    for key in ("job_id", "reviewer_id", "round", "stage", "paper_sha256", "reading", "overall",
                "section_scores", "strengths", "weaknesses", "questions"):
        if key not in data:
            errs.append(f"review.json lacks '{key}'")
    if errs:
        return errs
    errs = _containers(data, ("strengths", "weaknesses", "questions"))
    if not isinstance(data["weaknesses"], list) or not isinstance(data["section_scores"], dict):
        return errs  # the field checks below iterate these
    if data["job_id"] != job["job_id"]:
        errs.append(f"job_id {data['job_id']!r} != {job['job_id']!r}")
    if data["reviewer_id"] != job["reviewer"] or data["round"] != rnd["round"] or data["stage"] != "initial":
        errs.append("reviewer_id/round/stage mismatch")
    if data["paper_sha256"] != rnd["paper"]["main_pdf_sha256"]:
        errs.append("paper_sha256 does not match the round snapshot")
    errs += check_extensions(job, rnd, data)
    errs += _check_overall(job, data, scales)
    errs += _check_sections(job, data, scales, criteria)
    errs += _check_weaknesses(data, categories)
    if is_figure_job(job):
        errs += _check_figure_job(data.get("figure_scores"), data["weaknesses"], rnd, round_path, scales)
    try:
        md = read_text(out_dir / "review.md").lower()
    except UnicodeDecodeError as exc:
        return errs + [_encoding_error("review.md", exc)]
    for heading in scales["review_md_headings"] if job["overall"] else ("strengths", "weaknesses"):
        if heading.lower() not in md:
            errs.append(f"review.md lacks heading '{heading}'")
    return errs


def _containers(data: dict, lists: tuple[str, ...]) -> list[str]:
    """Container types the field checks rely on: the named lists and the section_scores object."""
    errs = [f"{key} must be a list" for key in lists if not isinstance(data.get(key), list)]
    if not isinstance(data.get("section_scores"), dict):
        errs.append("section_scores must be an object")
    return errs


def _check_overall(job: dict, data: dict, scales: dict, initial: bool = True) -> list[str]:
    """Overall verdict; an `initial` review also has a first impression, null for section-only jobs."""
    ov = data["overall"]
    first = data.get("first_impression")
    if not job["overall"]:
        errs = [] if ov is None else ["section-only job must have overall = null"]
        if initial and first is not None:
            errs.append("section-only job must have first_impression = null")
        return errs
    if not isinstance(ov, dict):
        return ["overall must be an object"]
    errs = []
    if initial and not job.get("careful") and (
            not isinstance(first, dict) or not _in_range(first.get("rating"), scales["overall"])):
        errs.append("first_impression.rating missing or out of range")
    if not _in_range(ov.get("rating"), scales["overall"]):
        errs.append(f"overall.rating {ov.get('rating')!r} out of range")
    if not _in_range(ov.get("confidence"), scales["confidence"]):
        errs.append(f"overall.confidence {ov.get('confidence')!r} out of range")
    if not _text(ov.get("justification")):
        errs.append("overall.justification is empty")
    return errs


def _check_sections(job: dict, data: dict, scales: dict, criteria: dict[str, list[str]]) -> list[str]:
    errs = []
    got, want = set(data["section_scores"]), set(job["sections"])
    if got != want:
        errs.append(f"section_scores keys {sorted(got)} != assigned {sorted(want)}")
    for sec, entry in data["section_scores"].items():
        if not isinstance(entry, dict):
            errs.append(f"{sec} must be an object")
            continue
        if not _in_range(entry.get("score"), scales["section"]):
            errs.append(f"{sec}.score {entry.get('score')!r} out of range")
        crit = entry.get("criteria", {})
        if set(crit) != set(criteria.get(sec, [])):
            errs.append(f"{sec}.criteria keys {sorted(crit)} != {criteria.get(sec)}")
        for cname, val in crit.items():
            if not _in_range(val, scales["criterion"]):
                errs.append(f"{sec}.criteria.{cname} {val!r} out of range")
        for field in ("main_issue", "location", "one_point_fix"):
            if not _text(entry.get(field)):
                errs.append(f"{sec}.{field} is empty")
    return errs


def _check_weaknesses(data: dict, categories: set[str]) -> list[str]:
    errs = []
    seen: set[str] = set()
    for w in data["weaknesses"]:
        if not isinstance(w, dict):
            errs.append(f"weakness {str(w)[:40]!r} must be an object")
            continue
        wid = w.get("id", "?")
        if not _WID.match(str(wid)) or wid in seen:
            errs.append(f"weakness id {wid!r} invalid or duplicated")
        seen.add(str(wid))
        if w.get("severity") not in SEVERITIES:
            errs.append(f"{wid}.severity {w.get('severity')!r} invalid")
        if w.get("category") not in categories:
            errs.append(f"{wid}.category {w.get('category')!r} not in taxonomy")
        if w.get("fixable_by") not in FIXABLE:
            errs.append(f"{wid}.fixable_by {w.get('fixable_by')!r} invalid")
        if not isinstance(w.get("decisive"), bool):
            errs.append(f"{wid}.decisive must be true/false")
        for field in ("location", "text", "suggested_fix", "would_change_mind"):
            if not _text(w.get(field)):
                errs.append(f"{wid}.{field} is empty")
    return errs


def _check_figure_job(scores: object, weaknesses: list, rnd: dict, round_path: Path,
                      scales: dict) -> list[str]:
    """Figure job: figure_scores for every main-paper id of the snapshot, defect-tagged weaknesses."""
    if not isinstance(scores, dict):
        return ["figure_scores must be an object keyed by figure id"]
    fc = figure_criteria(rnd)
    items = load_inventory(round_path / "snapshot")
    errs: list[str] = []
    if items is None:  # no inventory: require the captioned ids, accept other well-formed ids
        main, known = caption_ids(round_path / "snapshot"), set(scores)
        errs += [f"figure_scores key {k!r} is not a figure id (fig_<n> / tab_<n>)"
                 for k in scores if not _FIGURE_ID.match(str(k))]
    else:
        main, every = inventory_ids(items)
        known = set(every)
        unknown = sorted(set(scores) - known)
        if unknown:
            errs.append(f"figure_scores has ids not in figures.json {unknown}")
    missing = [i for i in main if i not in scores]
    if missing:
        errs.append(f"figure_scores lacks main-paper ids {missing}")
    for fid, entry in scores.items():
        errs += _check_figure_entry(str(fid), entry, fc, scales)
    for w in (w for w in weaknesses if isinstance(w, dict)):
        wid = w.get("id", "?")
        if w.get("figure_id") != "global" and w.get("figure_id") not in known:
            errs.append(f"{wid}.figure_id {w.get('figure_id')!r} is not a known figure id or 'global'")
        if w.get("defect") not in fc["defects"]:
            errs.append(f"{wid}.defect {w.get('defect')!r} not in the defect list")
    return errs


def _check_figure_entry(fid: str, entry: object, fc: dict, scales: dict) -> list[str]:
    """One figure_scores entry: role, 1-10 score, exact 1-5 criteria (null only if nullable), texts."""
    if not isinstance(entry, dict):
        return [f"figure {fid} must be an object"]
    errs = []
    if entry.get("role") not in fc["roles"]:
        errs.append(f"figure {fid}.role {entry.get('role')!r} not in {fc['roles']}")
    if not _in_range(entry.get("score"), scales["section"]):
        errs.append(f"figure {fid}.score {entry.get('score')!r} out of range")
    crit = entry.get("criteria")
    if not isinstance(crit, dict) or set(crit) != set(fc["criteria"]):
        errs.append(f"figure {fid}.criteria keys {sorted(crit) if isinstance(crit, dict) else crit!r} "
                    f"!= {fc['criteria']}")
    else:
        for name, val in crit.items():
            if val is None and name in fc["nullable"]:
                continue
            if not _in_range(val, scales["criterion"]):
                errs.append(f"figure {fid}.criteria.{name} {val!r} out of range")
    for field in _FIGURE_TEXT_FIELDS:
        if not _text(entry.get(field)):
            errs.append(f"figure {fid}.{field} is empty")
    return errs


def check_satisfaction(job: dict, rnd: dict, round_path: Path) -> list[str]:
    """Validate a reviewer's verdict on the authors' answers (stage 'satisfy')."""
    scales = scales_for(rnd)
    criteria, categories = _review_config(rnd)
    sdir = round_path / "satisfaction" / job["job_id"]
    errs = [f"missing or empty {n}" for n in ("reply.md", "satisfaction.json")
            if not (sdir / n).exists() or (sdir / n).stat().st_size < 50]
    if errs:
        return errs
    data, errs = _load_output(sdir / "satisfaction.json")
    if errs:
        return errs
    if not isinstance(data, dict):
        return ["satisfaction.json must be a JSON object"]
    errs = [f"satisfaction.json lacks '{key}'" for key in ("items", "section_scores") if key not in data]
    if errs:
        return errs
    data = {"new_issues": [], **data}
    errs = _containers(data, ("items", "new_issues"))
    if not errs:
        errs = [f"item {str(i)[:40]!r} must be an object" for i in data["items"] if not isinstance(i, dict)]
    if errs:
        return errs
    if data.get("job_id") != job["job_id"] or data.get("stage") != "satisfy":
        errs.append("job_id/stage mismatch")
    if data.get("round") != rnd["round"]:
        errs.append("round mismatch")
    if data.get("paper_sha256") != rnd["paper"]["main_pdf_sha256"]:
        errs.append("paper_sha256 does not match the round snapshot")
    previous = data.get("previous_rating")
    if previous is not None and not _in_range(previous, scales["overall"]):
        errs.append(f"previous_rating {previous!r} must be null or a rating on the overall scale")
    got = [i.get("id") for i in data["items"]]
    if sorted(map(str, got)) != sorted(job.get("open_items", [])):
        errs.append(f"items {got} != open points {job.get('open_items')}")
    for item in data["items"]:
        if item.get("status") not in ("satisfied", "partly", "not_satisfied"):
            errs.append(f"{item.get('id')}.status {item.get('status')!r} invalid")
        if not _text(item.get("reason")):
            errs.append(f"{item.get('id')}.reason is empty")
    new = data["new_issues"]
    if new:
        errs += _check_weaknesses({"weaknesses": new}, categories)
        clash = {w.get("id") for w in new if isinstance(w, dict)} & set(job.get("open_items", []))
        if clash:
            errs.append(f"new_issues reuse open ids {sorted(clash)}")
    errs += _check_overall(job, {"overall": data.get("overall")}, scales, initial=False)
    errs += _check_sections(job, data, scales, criteria)
    errs += check_extensions(job, rnd, data)
    if is_figure_job(job):
        errs += _check_figure_job(data.get("figure_scores"), new, rnd, round_path, scales)
    return errs


def validate_round(rnd: dict, round_path: Path) -> dict[str, list[str]]:
    """Validate every job; return job_id -> problems."""
    results = {}
    for job in rnd["jobs"]:
        check = check_satisfaction if job.get("stage") == "satisfy" else check_review
        try:
            results[job["job_id"]] = check(job, rnd, round_path)
        except (TypeError, AttributeError, KeyError, ValueError) as exc:
            # Malformed model output must remain a pending job, not crash resume/status.
            results[job["job_id"]] = [f"invalid output structure: {type(exc).__name__}: {exc}"]
    return results
