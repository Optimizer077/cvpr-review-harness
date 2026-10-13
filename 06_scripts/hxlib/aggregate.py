"""Aggregate a round's reviews into SCORES.json/SCORES.md and a session's rounds into PROGRESS.md.

Two reviewer groups: `feedback` (the writer reads them) and `heldout` (the writer never sees them;
their scores decide progress when present). A change in a group mean counts as a gain only when it
exceeds 2 x the standard error of a difference of two panel means, computed from the test-retest
SD measured by retest rounds (same draft, fresh reviewers).
"""
from __future__ import annotations

import logging
import math
import statistics
from collections import Counter
from pathlib import Path
from typing import Optional

from .common import SECTION_KEYS, list_rounds, load_json, load_scales, review_dir, round_dir, save_json
from .dialogue import round_items

logger = logging.getLogger(__name__)
GROUPS = ("feedback", "heldout")


def _stats(values: list[float]) -> dict:
    if not values:
        return {"n": 0}
    return {"n": len(values), "mean": round(statistics.fmean(values), 2), "min": min(values),
            "max": max(values), "sd": round(statistics.pstdev(values), 2)}


def _group_stats(rows: dict[str, dict]) -> dict:
    return {
        "overall": _stats([r["rating"] for r in rows.values() if r["rating"] is not None]),
        "first_impression": _stats([r["first_impression"] for r in rows.values()
                                    if r["first_impression"] is not None]),
        "sections": {s: st for s in SECTION_KEYS
                     if (st := _stats([r["sections"][s] for r in rows.values() if s in r["sections"]]))["n"]},
    }


def aggregate_round(rnd: dict, round_path: Path) -> dict:
    """Collect scores, weaknesses, fixcheck and pairwise outcomes, per reviewer group."""
    rows: dict[str, dict] = {}
    satisfaction: Counter = Counter()
    for job in rnd["jobs"]:
        satisfy = job.get("stage") == "satisfy"
        path = (round_path / "satisfaction" / job["job_id"] / "satisfaction.json" if satisfy
                else review_dir(round_path, job) / "review.json")
        if not path.exists():
            continue
        data = load_json(path)
        ov = data.get("overall") or {}
        first = None if satisfy else (data.get("first_impression") or {}).get("rating")
        rows[job["job_id"]] = {"reviewer": job["reviewer"], "group": job.get("group", "feedback"),
                               "stage": job.get("stage", "initial"), "rating": ov.get("rating"),
                               "previous_rating": data.get("previous_rating"),
                               "confidence": ov.get("confidence"), "first_impression": first,
                               "sections": {k: v["score"] for k, v in data["section_scores"].items()}}
        if satisfy:
            satisfaction.update(i["status"] for i in data["items"])
            satisfaction["new_issues"] += len(data.get("new_issues", []))
    weak = round_items(rnd, round_path)
    groups = {g: _group_stats({k: r for k, r in rows.items() if r["group"] == g}) for g in GROUPS}
    out = {
        "round": rnd["round"], "retest_of": rnd.get("retest_of"), "panel": rnd["panel"],
        "paper_sha256": rnd["paper"]["main_pdf_sha256"], "main_words": rnd["paper"].get("main_words"),
        "injection_flags": rnd["paper"].get("injection_flags", []),
        "reviews_found": len(rows), "jobs": len(rnd["jobs"]), "rows": rows, "groups": groups,
        "scale_max": load_scales(rnd.get("scale"))["overall"]["max"],
        "weakness_counts": {
            "by_category": dict(Counter(w["category"] for w in weak).most_common()),
            "by_severity": dict(Counter(w["severity"] for w in weak)),
            "by_fixable": dict(Counter(w["fixable_by"] for w in weak)),
            "decisive": sum(1 for w in weak if w.get("decisive")),
        },
        "decisive_weaknesses": [{"id": w["id"], "category": w["category"],
                                 "fixable_by": w["fixable_by"], "text": w["text"][:300]}
                                for w in weak if w.get("decisive")],
        "open_points": len(weak), "satisfaction": dict(satisfaction),
    }
    fix = round_path / "fixcheck" / "fixcheck.json"
    if fix.exists():
        out["fixcheck"] = dict(Counter(i.get("status") for i in load_json(fix)))
    out["pairwise"] = _decode_pairwise(round_path)
    return out


def _decode_pairwise(round_path: Path) -> list[dict]:
    res, key = round_path / "pairwise" / "pairwise.json", round_path / "pairwise" / "_key" / "KEY.json"
    if not (res.exists() and key.exists()):
        return []
    mapping = load_json(key)
    decoded = []
    for item in load_json(res):
        sec, pref = item["section"], item.get("preferred")
        winner = mapping.get(sec, {}).get(pref, "tie") if pref in ("A", "B") else "tie"
        decoded.append({"section": sec, "winner": winner, "margin": item.get("margin"),
                        "reason": item.get("reason", "")[:300]})
    return decoded


def headline(agg: dict) -> str:
    """One-line panel score: the held-out group when present, else the feedback group."""
    group = "heldout" if agg["groups"]["heldout"]["overall"].get("n") else "feedback"
    gs = agg["groups"][group]
    sec_means = [st["mean"] for st in gs["sections"].values()]
    sec_mean = round(sum(sec_means) / len(sec_means), 2) if sec_means else "-"
    ov, fi = gs["overall"], gs["first_impression"]
    champ = "yes" if ov.get("max", 0) >= champion_level(agg) else "no"
    sat = agg.get("satisfaction") or {}
    sat_txt = (f" Answers: {sat.get('satisfied', 0)} satisfied, {sat.get('partly', 0)} partly, "
               f"{sat.get('not_satisfied', 0)} not satisfied, {sat.get('new_issues', 0)} new issues." if sat else "")
    return (f"**Panel score ({group}): rating mean {ov.get('mean', '-')} (min {ov.get('min', '-')}, "
            f"max {ov.get('max', '-')}, n={ov.get('n', 0)}); champion: {champ}; first impression "
            f"{fi.get('mean', '-')}; section mean {sec_mean}/10; open points {agg.get('open_points', '-')} "
            f"(decisive {agg['weakness_counts']['decisive']}).**{sat_txt}")


def champion_level(agg: dict) -> int:
    """Lowest rating that counts as a clear accept: the second-highest level of the scale."""
    return int(agg.get("scale_max", 5)) - 1


def write_round_report(agg: dict, round_path: Path) -> None:
    """SCORES.json + SCORES.md for one round."""
    save_json(round_path / "SCORES.json", agg)
    title = f"# Scores - round {agg['round']:02d}"
    if agg.get("retest_of"):
        title += f" (retest of round {agg['retest_of']:02d})"
    lines = [title, "", headline(agg), "",
             f"Reviews found: {agg['reviews_found']}/{agg['jobs']}. Panel: "
             f"{', '.join(agg['panel'])}. Main-text words: {agg.get('main_words', '-')}.", ""]
    if agg.get("injection_flags"):
        lines += ["**Injection / hidden-text flags:** " + "; ".join(agg["injection_flags"]), ""]
    for group in GROUPS:
        g_rows = {k: r for k, r in agg["rows"].items() if r["group"] == group}
        if not g_rows:
            continue
        gs = agg["groups"][group]
        secs = list(gs["sections"])
        lines += [f"## {group} reviewers", "",
                  "| job | first impr. | rating | conf | " + " | ".join(secs) + " |",
                  "|---|---|---|---|" + "---|" * len(secs)]
        for jid, r in g_rows.items():
            cells = [str(r["sections"].get(s, "")) for s in secs]
            rating = (f"{r['previous_rating']} -> {r['rating']}" if r.get("stage") == "satisfy"
                      else str(r["rating"] or "-"))
            lines.append(f"| {jid} | {r['first_impression'] or '-'} | {rating} | "
                         f"{r['confidence'] or '-'} | " + " | ".join(cells) + " |")
        for stat in ("mean", "min"):
            lines.append(f"| **{stat}** | {gs['first_impression'].get(stat, '-')} | "
                         f"{gs['overall'].get(stat, '-')} | | "
                         + " | ".join(str(gs["sections"][s][stat]) for s in secs) + " |")
        lines.append("")
    wc = agg["weakness_counts"]
    lines += [f"Feedback weaknesses by severity: {wc['by_severity']}; decisive: {wc['decisive']}.",
              f"By category: {wc['by_category']}.", f"Fixable by: {wc['by_fixable']}.", ""]
    if agg["decisive_weaknesses"]:
        lines.append("## Decisive open points (feedback reviewers; full list in FEEDBACK.md)")
        lines += [f"- **{w['id']}** [{w['category']}, {w['fixable_by']}] {w['text']}"
                  for w in agg["decisive_weaknesses"]]
    if agg.get("fixcheck"):
        lines += ["", f"## Fix check vs previous round: {agg['fixcheck']}"]
    if agg["pairwise"]:
        lines += ["", "## Blind pairwise (new vs old draft)"]
        lines += [f"- {p['section']}: winner **{p['winner']}** (margin {p['margin']}) - {p['reason']}"
                  for p in agg["pairwise"]]
    (round_path / "SCORES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def noise_floor(session: Path) -> dict[str, dict]:
    """Single-score test-retest SD per measure: sqrt(mean(d^2) / 2) over retest pairs."""
    diffs: dict[str, list[float]] = {}
    for n in list_rounds(session):
        path = round_dir(session, n) / "SCORES.json"
        if not path.exists():
            continue
        agg = load_json(path)
        base_path = round_dir(session, agg["retest_of"]) / "SCORES.json" if agg.get("retest_of") else None
        if not base_path or not base_path.exists():
            continue
        base = load_json(base_path)
        for jid, row in agg["rows"].items():
            ref = base["rows"].get(jid)
            if not ref:
                continue
            for key in ("rating", "first_impression"):
                if row.get(key) is not None and ref.get(key) is not None:
                    diffs.setdefault(key, []).append(row[key] - ref[key])
            for sec, val in row["sections"].items():
                if sec in ref["sections"]:
                    diffs.setdefault(sec, []).append(val - ref["sections"][sec])
    return {k: {"sd": round(math.sqrt(statistics.fmean(d * d for d in v) / 2), 2), "pairs": len(v)}
            for k, v in diffs.items()}


def _verdict(delta: float, sd: Optional[float], n: int) -> str:
    if sd is None or n == 0:
        return ""
    threshold = 2 * sd * math.sqrt(2 / n)
    return f" ({'above' if abs(delta) > threshold else 'within'} noise, threshold {threshold:.2f})"


def write_progress(session: Path) -> str:
    """PROGRESS.md: per-round group means and deltas vs the previous non-retest round."""
    noise = noise_floor(session)
    rounds = [load_json(round_dir(session, n) / "SCORES.json") for n in list_rounds(session)
              if (round_dir(session, n) / "SCORES.json").exists()]
    lines = ["# Progress across rounds", "",
             "Test-retest SD per single score: " + (str(noise) if noise else
                                                    "not measured yet - run `hx.py retest` (3 times for decisions)."),
             "Progress is decided by the heldout group when it exists, else by the feedback group.", ""]
    prev: Optional[dict] = None
    for agg in rounds:
        tag = f"round {agg['round']:02d}" + (" (retest)" if agg.get("retest_of") else "")
        lines.append(f"## {tag} - words {agg.get('main_words', '-')}, decisive weaknesses "
                     f"{agg['weakness_counts']['decisive']}")
        for group in GROUPS:
            gs = agg["groups"][group]
            if not gs["overall"]["n"] and not gs["sections"]:
                continue
            lines.append(f"- **{group}**: rating mean {gs['overall'].get('mean', '-')}, first impression "
                         f"{gs['first_impression'].get('mean', '-')}")
            for sec, st in gs["sections"].items():
                delta = ""
                old = prev["groups"][group]["sections"].get(sec) if prev else None
                if old:
                    d = round(st["mean"] - old["mean"], 2)
                    delta = f", delta {d:+}" + _verdict(d, noise.get(sec, {}).get("sd"), st["n"])
                lines.append(f"  - {sec}: mean {st['mean']} (min {st['min']}){delta}")
        if not agg.get("retest_of"):
            prev = agg
        lines.append("")
    text = "\n".join(lines) + "\n"
    (session / "PROGRESS.md").write_text(text, encoding="utf-8")
    return text
