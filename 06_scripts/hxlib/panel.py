"""Reviewer panels: load personas, draw a seeded panel, and turn it into review jobs."""
from __future__ import annotations

import logging
import random
from typing import Optional

from .common import PANEL_DIR, PERSONA_DIR, SECTION_KEYS, load_json
from .figure_job import FIGURE_SECTION, figure_job

logger = logging.getLogger(__name__)
REVIEWER_ROLE = "reviewer"

# Sections a reviewer can score from each reading view (what that reviewer actually reads).
VIEW_SECTIONS: dict[str, tuple[str, ...]] = {
    "front": ("title", "abstract", "introduction"),
    "skim": ("title", "abstract", "introduction", "figures_tables", "limitations", "conclusion"),
    "main": tuple(k for k in SECTION_KEYS if k != "supplementary"),
    "full": SECTION_KEYS,
}


def load_personas(venue: str | None = None) -> dict[str, dict]:
    """Persona registry keyed by id (R01...)."""
    reg = load_json(PERSONA_DIR / "personas.json")
    return {p["id"]: p for p in reg["personas"] if venue is None or p.get("venue", "cvpr") == venue}


def load_panels(venue: str = "cvpr") -> dict[str, dict]:
    """Panel definitions from 04_panels/panels.json."""
    return load_json(PANEL_DIR / ("panels.json" if venue == "cvpr" else f"{venue}.json"))["panels"]


def load_section_map(venue: str = "cvpr") -> dict[str, list[str]]:
    """Section -> reviewer ids for section-mode review."""
    return load_json(PANEL_DIR / ("section_panel.json" if venue == "cvpr" else f"{venue}.json"))["sections"]


def is_reviewer(persona: dict) -> bool:
    """Whether a persona is a sampled reviewer type (role 'reviewer'), not a harness instrument."""
    return persona.get("role", REVIEWER_ROLE) == REVIEWER_ROLE


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


def draw_panel(panel_name: str, seed: int, personas: Optional[dict[str, dict]] = None, venue: str = "cvpr") -> list[str]:
    """Return reviewer ids for a named panel. Draw panels are seeded and sample without replacement.

    Draws and kind 'all' consider only role 'reviewer' personas, so harness instruments such as
    the figure reader (F01) never enter a panel.
    """
    personas = personas or load_personas(venue)
    personas = {k: p for k, p in personas.items() if p.get("venue", "cvpr") == venue}
    reviewers = [p for p in personas.values() if is_reviewer(p)]
    spec = load_panels(venue)[panel_name]
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
               heldout_ids: Optional[list[str]] = None, section_map: Optional[dict] = None,
               reading: str = "persona", figures: bool = False) -> list[dict]:
    """Turn a panel into review jobs.

    mode 'full': each panel reviewer writes the whole-paper review and scores the sections they read.
    mode 'sections': reviewers from section_panel.json score only their assigned sections.
    mode 'both': union of the two. A section a full-review job already scores is not repeated;
    other assigned sections go to a separate '<id>-sec' job so a skimming reviewer's overall
    rating is not changed by a deep section read.
    heldout_ids: extra full-review jobs ('H<id>', group 'heldout') whose reviews the writer never sees.
    figures: add the opt-in figure job 'FIG' (persona F01, section figures_tables, main view). It
    keeps its main view in careful sessions and is added even when only_sections omits figures_tables,
    because --figures is an explicit request.
    """
    wanted = [s for s in (only_sections or sections_present) if s in sections_present]
    jobs: dict[str, dict] = {}
    if mode in ("full", "both"):
        for rid in panel_ids:
            view = "full" if reading == "careful" else personas[rid]["reading_view"]
            secs = [s for s in VIEW_SECTIONS[view] if s in wanted]
            jobs[rid] = {"job_id": rid, "reviewer": rid, "overall": True, "sections": secs,
                         "view": view}
    if mode in ("sections", "both"):
        for sec, rids in (section_map if section_map is not None else load_section_map()).items():
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
        view = "full" if reading == "careful" else personas[rid]["reading_view"]
        jid = f"H{rid}"
        jobs[jid] = {"job_id": jid, "reviewer": rid, "overall": True, "group": "heldout",
                     "sections": [s for s in VIEW_SECTIONS[view] if s in wanted], "view": view}
    order = {k: i for i, k in enumerate(SECTION_KEYS)}
    for job in jobs.values():
        job.setdefault("group", "feedback")
        if reading == "careful":
            job["view"] = "full"
            job["careful"] = True
        job["sections"].sort(key=lambda s: order[s])
    if figures and FIGURE_SECTION in sections_present:
        fig = figure_job()
        if reading == "careful":
            fig["careful"] = True
        jobs[fig["job_id"]] = fig
    return list(jobs.values())
