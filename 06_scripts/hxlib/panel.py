"""Reviewer panels: load personas, draw a seeded panel, and turn it into review jobs."""
from __future__ import annotations

import logging
import random
from typing import Optional

from .common import PANEL_DIR, PERSONA_DIR, SECTION_KEYS, load_json

logger = logging.getLogger(__name__)

# Sections a reviewer can score from each reading view (what that reviewer actually reads).
VIEW_SECTIONS: dict[str, tuple[str, ...]] = {
    "front": ("title", "abstract", "introduction"),
    "skim": ("title", "abstract", "introduction", "figures_tables", "limitations", "conclusion"),
    "main": tuple(k for k in SECTION_KEYS if k != "supplementary"),
    "full": SECTION_KEYS,
}


def load_personas() -> dict[str, dict]:
    """Persona registry keyed by id (R01...)."""
    reg = load_json(PERSONA_DIR / "personas.json")
    return {p["id"]: p for p in reg["personas"]}


def load_panels() -> dict[str, dict]:
    """Panel definitions from 04_panels/panels.json."""
    return load_json(PANEL_DIR / "panels.json")["panels"]


def load_section_map() -> dict[str, list[str]]:
    """Section -> reviewer ids for section-mode review."""
    return load_json(PANEL_DIR / "section_panel.json")["sections"]


def _weighted_pick(rng: random.Random, candidates: list[dict]) -> dict:
    total = sum(max(c.get("draw_weight", 0.0), 0.0) for c in candidates)
    if total <= 0:
        return rng.choice(candidates)
    x = rng.uniform(0.0, total)
    acc = 0.0
    for cand in candidates:
        acc += max(cand.get("draw_weight", 0.0), 0.0)
        if x <= acc:
            return cand
    return candidates[-1]


def draw_panel(panel_name: str, seed: int, personas: Optional[dict[str, dict]] = None) -> list[str]:
    """Return reviewer ids for a named panel. Draw panels are seeded and sample without replacement."""
    personas = personas or load_personas()
    reviewers = list(personas.values())
    spec = load_panels()[panel_name]
    kind = spec["kind"]
    if kind == "all":
        return sorted(p["id"] for p in reviewers)
    if kind == "fixed":
        missing = [m for m in spec["members"] if m not in personas]
        if missing:
            raise KeyError(f"Panel {panel_name} names unknown personas: {missing}")
        return list(spec["members"])
    if kind != "draw":
        raise ValueError(f"Unknown panel kind {kind!r}")
    rng = random.Random(seed)
    chosen: list[str] = []
    max_killers = spec.get("max_killers", 1)
    for slot in spec["slots"]:
        pools = set(slot["pool"])
        killers = sum(1 for c in chosen if personas[c].get("killer"))
        cands = [p for p in reviewers if p["id"] not in chosen
                 and ("any" in pools or pools & set(p.get("pool", [])))
                 and not (p.get("killer") and killers >= max_killers)]
        if not cands:
            raise ValueError(f"No candidates left for slot {slot} in panel {panel_name}")
        chosen.append(_weighted_pick(rng, cands)["id"])
    return chosen


def build_jobs(mode: str, panel_ids: list[str], sections_present: list[str],
               personas: dict[str, dict], only_sections: Optional[list[str]] = None,
               heldout_ids: Optional[list[str]] = None) -> list[dict]:
    """Turn a panel into review jobs.

    mode 'full': each panel reviewer writes the whole-paper review and scores the sections they read.
    mode 'sections': reviewers from section_panel.json score only their assigned sections.
    mode 'both': union of the two. A section a full-review job already scores is not repeated;
    other assigned sections go to a separate '<id>-sec' job so a skimming reviewer's overall
    rating is not changed by a deep section read.
    heldout_ids: extra full-review jobs ('H<id>', group 'heldout') whose reviews the writer never sees.
    """
    wanted = [s for s in (only_sections or sections_present) if s in sections_present]
    jobs: dict[str, dict] = {}
    if mode in ("full", "both"):
        for rid in panel_ids:
            view = personas[rid]["reading_view"]
            secs = [s for s in VIEW_SECTIONS[view] if s in wanted]
            jobs[rid] = {"job_id": rid, "reviewer": rid, "overall": True, "sections": secs,
                         "view": view}
    if mode in ("sections", "both"):
        for sec, rids in load_section_map().items():
            if sec not in wanted:
                continue
            for rid in rids:
                if rid in jobs and jobs[rid]["overall"] and sec in jobs[rid]["sections"]:
                    continue
                jid = f"{rid}-sec" if (rid in jobs and jobs[rid]["overall"]) else rid
                job = jobs.setdefault(jid, {"job_id": jid, "reviewer": rid, "overall": False,
                                            "sections": [], "view": "main"})
                if sec not in job["sections"]:
                    job["sections"].append(sec)
                if sec == "supplementary":
                    job["view"] = "full"
    for rid in heldout_ids or []:
        view = personas[rid]["reading_view"]
        jid = f"H{rid}"
        jobs[jid] = {"job_id": jid, "reviewer": rid, "overall": True, "group": "heldout",
                     "sections": [s for s in VIEW_SECTIONS[view] if s in wanted], "view": view}
    order = {k: i for i, k in enumerate(SECTION_KEYS)}
    for job in jobs.values():
        job.setdefault("group", "feedback")
        job["sections"].sort(key=lambda s: order[s])
    return list(jobs.values())
