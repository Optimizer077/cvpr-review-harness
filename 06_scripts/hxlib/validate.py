"""Validate reviewer outputs of a round against the job list, scales, rubric criteria and taxonomy."""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from .common import PROTOCOL_DIR, load_json, load_scales, review_dir

from .venues import scales_for, check_extensions

logger = logging.getLogger(__name__)

SEVERITIES = ("major", "moderate", "minor")
FIXABLE = ("writing", "existing_evidence", "new_experiment", "not_fixable")
_WID = re.compile(r"^W\d+$")


def _in_range(value: object, scale: dict) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and scale["min"] <= value <= scale["max"]


def check_review(job: dict, rnd: dict, round_path: Path) -> list[str]:
    """Return a list of problems for one job (empty = valid)."""
    scales = scales_for(rnd)
    criteria = rnd["review_config"]["criteria"] if "review_config" in rnd else load_json(PROTOCOL_DIR / "section_criteria.json")["criteria"]
    categories = set(rnd["review_config"]["categories"] if "review_config" in rnd else load_json(PROTOCOL_DIR / "taxonomy.json")["categories"])
    out_dir = review_dir(round_path, job)
    errs: list[str] = []
    for name in ("review.md", "review.json", "debrief.md"):
        path = out_dir / name
        if not path.exists() or path.stat().st_size < 50:
            errs.append(f"missing or empty {name}")
    if errs:
        return errs
    try:
        data = load_json(out_dir / "review.json")
    except json.JSONDecodeError as exc:
        return [f"review.json is not valid JSON: {exc}"]
    for key in ("job_id", "reviewer_id", "round", "stage", "paper_sha256", "reading", "overall",
                "section_scores", "strengths", "weaknesses", "questions"):
        if key not in data:
            errs.append(f"review.json lacks '{key}'")
    if errs:
        return errs
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
    md = (out_dir / "review.md").read_text(encoding="utf-8").lower()
    for heading in scales["review_md_headings"] if job["overall"] else ("strengths", "weaknesses"):
        if heading.lower() not in md:
            errs.append(f"review.md lacks heading '{heading}'")
    return errs


def _check_overall(job: dict, data: dict, scales: dict) -> list[str]:
    ov = data["overall"]
    if not job["overall"]:
        return [] if ov is None else ["section-only job must have overall = null"]
    if not isinstance(ov, dict):
        return ["overall must be an object"]
    errs = []
    first = data.get("first_impression")
    if not job.get("careful") and (not isinstance(first, dict) or not _in_range(first.get("rating"), scales["overall"])):
        errs.append("first_impression.rating missing or out of range")
    if not _in_range(ov.get("rating"), scales["overall"]):
        errs.append(f"overall.rating {ov.get('rating')!r} out of range")
    if not _in_range(ov.get("confidence"), scales["confidence"]):
        errs.append(f"overall.confidence {ov.get('confidence')!r} out of range")
    if not str(ov.get("justification", "")).strip():
        errs.append("overall.justification is empty")
    return errs


def _check_sections(job: dict, data: dict, scales: dict, criteria: dict[str, list[str]]) -> list[str]:
    errs = []
    got, want = set(data["section_scores"]), set(job["sections"])
    if got != want:
        errs.append(f"section_scores keys {sorted(got)} != assigned {sorted(want)}")
    for sec, entry in data["section_scores"].items():
        if not _in_range(entry.get("score"), scales["section"]):
            errs.append(f"{sec}.score {entry.get('score')!r} out of range")
        crit = entry.get("criteria", {})
        if set(crit) != set(criteria.get(sec, [])):
            errs.append(f"{sec}.criteria keys {sorted(crit)} != {criteria.get(sec)}")
        for cname, val in crit.items():
            if not _in_range(val, scales["criterion"]):
                errs.append(f"{sec}.criteria.{cname} {val!r} out of range")
        for field in ("main_issue", "location", "one_point_fix"):
            if not str(entry.get(field, "")).strip():
                errs.append(f"{sec}.{field} is empty")
    return errs


def _check_weaknesses(data: dict, categories: set[str]) -> list[str]:
    errs = []
    seen: set[str] = set()
    for w in data["weaknesses"]:
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
            if not str(w.get(field, "")).strip():
                errs.append(f"{wid}.{field} is empty")
    return errs


def check_satisfaction(job: dict, rnd: dict, round_path: Path) -> list[str]:
    """Validate a reviewer's verdict on the authors' answers (stage 'satisfy')."""
    scales = scales_for(rnd)
    criteria = rnd["review_config"]["criteria"] if "review_config" in rnd else load_json(PROTOCOL_DIR / "section_criteria.json")["criteria"]
    categories = set(rnd["review_config"]["categories"] if "review_config" in rnd else load_json(PROTOCOL_DIR / "taxonomy.json")["categories"])
    sdir = round_path / "satisfaction" / job["job_id"]
    errs = [f"missing or empty {n}" for n in ("reply.md", "satisfaction.json")
            if not (sdir / n).exists() or (sdir / n).stat().st_size < 50]
    if errs:
        return errs
    try:
        data = load_json(sdir / "satisfaction.json")
    except json.JSONDecodeError as exc:
        return [f"satisfaction.json is not valid JSON: {exc}"]
    if data.get("job_id") != job["job_id"] or data.get("stage") != "satisfy":
        errs.append("job_id/stage mismatch")
    if data.get("round") != rnd["round"]:
        errs.append("round mismatch")
    if data.get("paper_sha256") != rnd["paper"]["main_pdf_sha256"]:
        errs.append("paper_sha256 does not match the round snapshot")
    got = [i.get("id") for i in data.get("items", [])]
    if sorted(got) != sorted(job.get("open_items", [])):
        errs.append(f"items {got} != open points {job.get('open_items')}")
    for item in data.get("items", []):
        if item.get("status") not in ("satisfied", "partly", "not_satisfied"):
            errs.append(f"{item.get('id')}.status {item.get('status')!r} invalid")
        if not str(item.get("reason", "")).strip():
            errs.append(f"{item.get('id')}.reason is empty")
    new = data.get("new_issues", [])
    if new:
        errs += _check_weaknesses({"weaknesses": new}, categories)
        clash = {w.get("id") for w in new} & set(job.get("open_items", []))
        if clash:
            errs.append(f"new_issues reuse open ids {sorted(clash)}")
    errs += _check_overall(job, {"overall": data.get("overall"),
                                 "first_impression": {"rating": (data.get("overall") or {}).get("rating")}}, scales)
    errs += _check_sections(job, {"section_scores": data.get("section_scores", {})}, scales, criteria)
    errs += check_extensions(job, rnd, data)
    return errs


def validate_round(rnd: dict, round_path: Path) -> dict[str, list[str]]:
    """Validate every job; return job_id -> problems."""
    return {job["job_id"]: (check_satisfaction if job.get("stage") == "satisfy" else check_review)(
        job, rnd, round_path) for job in rnd["jobs"]}
