"""Versioned venue policies and immutable per-session review instruments."""
from __future__ import annotations

from pathlib import Path

from .common import HARNESS_ROOT, PROTOCOL_DIR, load_json, load_scales


def profile_for(name: str) -> dict:
    profiles = load_json(PROTOCOL_DIR / "venues.json")
    key = name.strip().lower()
    for venue, profile in profiles.items():
        if key in (venue, profile["label"].lower(), profile["id"]):
            return dict(profile, venue=venue)
    raise ValueError(f"Unknown venue/version {name!r}; choose {', '.join(profiles)}")


def freeze(session: dict, personas: dict, section_map: dict) -> None:
    texts = {}
    for folder in ("02_protocol", "03_personas", "05_templates"):
        for path in (HARNESS_ROOT / folder).glob("*.md"):
            texts[path.relative_to(HARNESS_ROOT).as_posix()] = path.read_text(encoding="utf-8")
    session["instruments"] = {"texts": texts, "personas": personas, "section_map": section_map}
    session["review_config"] = {
        "profile": session["venue_profile"], "reading": session["reading_mode"],
        "contribution_type": session["contribution_type"], "scales": load_scales(session["scale"]),
        "criteria": load_json(PROTOCOL_DIR / "section_criteria.json")["criteria"],
        "categories": load_json(PROTOCOL_DIR / "taxonomy.json")["categories"],
    }


def instrument(session: dict, path: Path) -> str:
    if "instruments" in session:
        return session["instruments"]["texts"][path.relative_to(HARNESS_ROOT).as_posix()]
    return path.read_text(encoding="utf-8")


def scales_for(context: dict) -> dict:
    if "review_config" in context:
        return context["review_config"]["scales"]
    return load_scales(context.get("scale"))


def careful(session: dict) -> bool:
    return session.get("reading_mode") == "careful"


def reviewer_card(session: dict, persona: dict) -> str:
    if careful(session) and persona["id"].startswith("R"):
        return (f"# {persona['name']}\nUse this specialty as a lens for evidence checking. "
                "This careful review does not simulate hurried reading, hostility, rating offsets "
                "or acceptance quotas. Apply the careful-reading protocol to the entire assigned scope.")
    return instrument(session, HARNESS_ROOT / "03_personas" / persona["file"])


def common_rules(session: dict) -> str:
    name = "careful_review.md" if careful(session) else "reviewer_common.md"
    return instrument(session, PROTOCOL_DIR / name)


def venue_block(session: dict, job: dict) -> str:
    if "review_config" not in session:
        return ""
    config = session["review_config"]
    profile = config["profile"]
    parts = ["## Venue policy and output additions", f"Profile: {profile['id']} (main track).",
             f"Contribution type: {config['contribution_type']}.",
             instrument(session, PROTOCOL_DIR / profile["guidance"]),
             "Scale provenance: " + config["scales"]["overall"]["source"],
             "Section scores and confidence descriptions are harness instruments; scores across "
             "different venues, scales or reading modes are not interchangeable."]
    if config["contribution_type"] != "general":
        parts.append(profile["contribution_types"][config["contribution_type"]])
    if profile["dimensions"]:
        dims = ", ".join(profile["dimensions"])
        parts.append(f"In review.json AND satisfaction.json add `venue_assessment`: "
                     f"{{\"profile\": \"{profile['id']}\", \"dimensions\": {{...}}}}. "
                     f"For whole-paper jobs, dimensions has exactly: {dims}. Each entry is "
                     "{\"score\": integer 1-4, \"reason\": nonempty string, \"location\": nonempty string}. "
                     "Anchors: 1 poor, 2 fair, 3 good, 4 excellent. For section-only jobs, use "
                     "dimensions: {} because the assigned scope cannot support a whole-paper judgement.")
    if careful(session):
        parts.append(instrument(session, HARNESS_ROOT / "05_templates" / "evidence_audit.md"))
        parts.append("These careful-mode rules supersede the generic schema examples: set "
                     "first_impression to null; do not assign a rating before completing the read. "
                     "An empty weaknesses/new_issues list is valid when justified; never invent an issue. "
                     "Set reading.time_spent_min to null unless elapsed time was actually measured.")
    return "\n\n".join(parts)


def check_extensions(job: dict, rnd: dict, data: dict) -> list[str]:
    config = rnd.get("review_config")
    if not config:
        return []
    errs = []
    profile = config["profile"]
    if profile["dimensions"]:
        assessment = data.get("venue_assessment")
        if not isinstance(assessment, dict) or assessment.get("profile") != profile["id"]:
            errs.append("venue_assessment.profile missing or mismatched")
        else:
            dims = assessment.get("dimensions")
            expected = set(profile["dimensions"]) if job["overall"] else set()
            if not isinstance(dims, dict) or set(dims) != expected:
                errs.append("venue_assessment.dimensions do not match assigned scope")
            else:
                for key, value in dims.items():
                    if not isinstance(value, dict):
                        errs.append(f"venue dimension {key} must be an object")
                        continue
                    score = value.get("score")
                    if type(score) is not int or not 1 <= score <= 4:
                        errs.append(f"venue dimension {key}.score must be 1-4")
                    for field in ("reason", "location"):
                        if not isinstance(value.get(field), str) or not value[field].strip():
                            errs.append(f"venue dimension {key}.{field} is empty")
    if config["reading"] != "careful":
        return errs
    if data.get("first_impression") is not None:
        errs.append("careful mode requires first_impression = null")
    audit = data.get("evidence_audit")
    if not isinstance(audit, dict):
        return errs + ["careful mode requires evidence_audit"]
    coverage = audit.get("coverage")
    if not isinstance(coverage, dict) or set(coverage) != set(job["sections"]):
        errs.append("evidence_audit.coverage must cover exactly the assigned sections")
    else:
        for sec, entry in coverage.items():
            if (not isinstance(entry, dict) or entry.get("status") not in ("checked", "not_checked")
                    or not isinstance(entry.get("note"), str) or not entry["note"].strip()):
                errs.append(f"evidence_audit.coverage.{sec} needs status and location/reason note")
    claims = audit.get("claim_checks")
    if not isinstance(claims, list) or not claims:
        errs.append("evidence_audit.claim_checks requires at least one assessed claim")
    else:
        for entry in claims:
            if not isinstance(entry, dict):
                errs.append("claim check must be an object")
                continue
            for field in ("claim", "location", "evidence"):
                if not isinstance(entry.get(field), str) or not entry[field].strip():
                    errs.append(f"claim check lacks {field}")
            if entry.get("verdict") not in ("supported", "partial", "unsupported", "not_checked"):
                errs.append("claim check verdict invalid")
    return errs
