"""Prompts for the writer loop after the independent reviews.

fixcheck    - a neutral checker marks each point the writer was asked to fix as resolved or not in
              the new draft
pairwise    - a blind judge compares changed sections and changed figure crops between two drafts
              (order randomized)
writer      - the brief handed to the writer agent after a round

fixcheck and pairwise compare a round with the last earlier review round, never a retest: a retest
repeats an older draft, and in the dialogue loop the points to check are the open points that the
writer answered after that review round (not only the first-round weaknesses).
"""
from __future__ import annotations

import logging
import random
import re
import shutil
from pathlib import Path

from .common import PROTOCOL_DIR, UNSCORED_SECTION, load_json, round_dir, save_json
from .dialogue import last_dialogue_round, round_items
from .figure_render import load_inventory, measured_facts
from .prompts import read_text
from .venues import instrument

logger = logging.getLogger(__name__)
_POINT_FIELDS = ("id", "severity", "category", "location", "text", "fixable_by", "figure_id")


def previous_review_round(round_path: Path, rnd: dict) -> tuple[int, Path]:
    """Number and folder of the last review (non-retest) round before this one."""
    try:
        number = last_dialogue_round(round_path.parent, rnd["round"])
    except ValueError as exc:
        raise ValueError(f"round {rnd['round']} has no earlier review round to compare with") from exc
    return number, round_dir(round_path.parent, number)


def open_points(round_path: Path) -> list[dict]:
    """Points the writer was asked to fix after a round: FEEDBACK.json, else recomputed from outputs.

    Feedback reviewers only; held-out points never reach the writer or the checker.
    """
    path = round_path / "FEEDBACK.json"
    items = load_json(path) if path.exists() else round_items(load_json(round_path / "ROUND.json"), round_path)
    return [{k: item[k] for k in _POINT_FIELDS if k in item} for item in items]


def fixcheck_prompt(session: dict, rnd: dict, round_path: Path) -> str:
    """Neutral check of the previous review round's open points against the new draft."""
    prev_n, prev = previous_review_round(round_path, rnd)
    items = open_points(prev)
    save_json(round_path / "fixcheck" / "previous_weaknesses.json", items)
    out = round_path / "fixcheck"
    lines = [
        f"# Fix check - {session['name']}, round {rnd['round']:02d} vs round {prev_n:02d}",
        instrument(session, PROTOCOL_DIR / "fixcheck_rules.md"),
        f"- Open points on the previous draft: `{out / 'previous_weaknesses.json'}` ({len(items)} items).",
        f"- New draft: `{round_path / 'snapshot' / 'view_full.txt'}` and `{round_path / 'snapshot' / 'main.pdf'}`.",
        f"- Previous draft (to see what changed): `{prev / 'snapshot' / 'view_full.txt'}`.",
        f"Write `{out / 'fixcheck.json'}` = [{{\"id\": str, \"status\": \"resolved|partly|unresolved|"
        "regressed|not_applicable\", \"evidence\": \"location + short quote in the new draft\", "
        "\"note\": str}], one entry per item, and a short `fixcheck.md` summary.",
        "Reply with one line: counts per status.",
    ]
    return "\n\n".join(lines) + "\n"


def _norm(text: str) -> str:
    text = re.sub(r"(?m)^L\d{3,4}\s+", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _figure_pairs(old_snap: Path, new_snap: Path, pdir: Path,
                  rng: random.Random) -> tuple[dict[str, dict], list[str]]:
    """Copy the crops of every figure whose crop changed to A_fig_<id>.png / B_fig_<id>.png.

    A figure counts as changed when its id is in both inventories and the crop sha256 differs.
    Returns the key entries ('figure:<id>') and one line of measured facts per pair.
    """
    old_items, new_items = load_inventory(old_snap) or {}, load_inventory(new_snap) or {}
    key: dict[str, dict] = {}
    facts: list[str] = []
    for fid, new in new_items.items():
        old = old_items.get(fid)
        hashes = (old or {}).get("crop_sha256"), new.get("crop_sha256")
        if None in hashes or hashes[0] == hashes[1]:
            continue
        new_is_a = rng.random() < 0.5
        new_pair, old_pair = (new, new_snap / new["crop"]), (old, old_snap / old["crop"])
        (a, a_png), (b, b_png) = (new_pair, old_pair) if new_is_a else (old_pair, new_pair)
        pdir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(a_png, pdir / f"A_fig_{fid}.png")
        shutil.copyfile(b_png, pdir / f"B_fig_{fid}.png")
        key[f"figure:{fid}"] = {"A": "new" if new_is_a else "old", "B": "old" if new_is_a else "new"}
        facts.append(f"- figure:{fid} ({new['label']}): A {measured_facts(a) or 'nothing measurable'}; "
                     f"B {measured_facts(b) or 'nothing measurable'}.")
    return key, facts


def pairwise_prompt(session: dict, rnd: dict, round_path: Path, seed: int) -> str:
    """Blind A/B comparison of each section and figure that changed since the previous review round."""
    _, prev = previous_review_round(round_path, rnd)
    rng = random.Random(seed * 1000 + rnd["round"])
    pdir = round_path / "pairwise"
    key: dict[str, dict] = {}
    for sec_file in sorted((round_path / "snapshot" / "sections").glob("*.txt")):
        old_file = prev / "snapshot" / "sections" / sec_file.name
        if not old_file.exists() or sec_file.stem == UNSCORED_SECTION:  # acknowledgements etc. are not judged
            continue
        new_t, old_t = read_text(sec_file), read_text(old_file)
        if _norm(new_t) == _norm(old_t):
            continue
        new_is_a = rng.random() < 0.5
        a_text, b_text = (new_t, old_t) if new_is_a else (old_t, new_t)
        (pdir / f"A_{sec_file.stem}.txt").parent.mkdir(parents=True, exist_ok=True)
        (pdir / f"A_{sec_file.stem}.txt").write_text(a_text, encoding="utf-8")
        (pdir / f"B_{sec_file.stem}.txt").write_text(b_text, encoding="utf-8")
        key[sec_file.stem] = {"A": "new" if new_is_a else "old", "B": "old" if new_is_a else "new"}
    sections = list(key)
    fig_key, fig_facts = _figure_pairs(prev / "snapshot", round_path / "snapshot", pdir, rng)
    key.update(fig_key)
    save_json(pdir / "_key" / "KEY.json", key)
    lines = [
        f"# Blind pairwise judgement - {session['venue']}",
        instrument(session, PROTOCOL_DIR / "pairwise_rules.md"),
        "Sections to compare: " + (", ".join(sections) or "none (no section changed)"),
        f"Files: `{pdir}/A_<section>.txt` and `{pdir}/B_<section>.txt`. Do NOT open `{pdir / '_key'}`.",
        "Figures to compare (the crop image changed): " + (", ".join(fig_key) or "none"),
    ]
    if fig_key:
        lines.append(f"Figure files: `{pdir}/A_fig_<id>.png` and `{pdir}/B_fig_<id>.png` (figure with its "
                     "caption, as printed). Open both images. Measured from the PDF (smallest vector text, "
                     "lowest raster resolution):\n" + "\n".join(fig_facts))
    lines += [
        f"Write `{pdir / 'pairwise.json'}` = [{{\"section\": str, \"preferred\": \"A|B|tie\", "
        "\"margin\": 0-3, \"reason\": str, \"reviewer_types_that_care\": [str]}]. For a figure, "
        "`section` is its `figure:<id>` name.",
        "Reply with one line per section or figure: preferred version and margin.",
    ]
    return "\n\n".join(lines) + "\n"


def writer_prompt(session: dict, rnd: dict, round_path: Path, session_path: Path) -> str:
    """Brief for the writer agent (or the user) after a round has been reviewed and aggregated."""
    lines = [
        f"# Writer brief - {session['name']}, after round {rnd['round']:02d}",
        instrument(session, PROTOCOL_DIR / "writer_rules.md"),
        f"Venue: {session['venue']}; contribution type: {session.get('contribution_type', 'general')}. "
        "Use the submission-stage page budget in AUTHOR_CONSTRAINTS.md. This is author preparation, not an official rebuttal submission.",
        "## Inputs",
        f"- The to-do list: `{round_path / 'FEEDBACK.md'}` - every open point with the reviewer's "
        "suggested fix and what would satisfy them, most important first, then the section scores "
        "(and the figure scores when the figure job ran). It carries every score you need.",
        f"- Reviews, replies and debriefs: `{round_path / 'reviews'}/<id>/` and "
        f"`{round_path / 'satisfaction'}/<id>/reply.md` (if this was an answer round).",
        f"- Author constraints: `{session_path / 'AUTHOR_CONSTRAINTS.md'}`",
        f"- Paper sources you may edit: `{session.get('tex_dir') or 'see SESSION.json'}`",
        f"- Never open `{round_path / 'heldout'}`, `{round_path / 'SCORES.md'}`, "
        f"`{round_path / 'SCORES.json'}` or `{session_path / 'PROGRESS.md'}`, nor these files of any "
        "other round: they hold held-out reviews and scores that judge your revision and must stay unseen.",
        "## Outputs",
        f"1. `{round_path / 'writer' / 'RESPONSE.md'}` - the answer sheet is pre-filled with one block "
        "per point; fill in every block (decision, what changed where, answer to the reviewer). The "
        "same reviewers will read your answers next round and check them against the new draft.",
        f"2. `{round_path / 'writer' / 'CHANGES.md'}` - every edit: file, section, before/after gist, point ids, "
        "tag presentation|evidence, word count before/after.",
        f"3. `{round_path / 'writer' / 'EXPERIMENT_REQUESTS.md'}` - requests that need new runs (for the user).",
        "4. The edited paper sources, rebuilt to PDF with the project's own build command.",
    ]
    return "\n\n".join(lines) + "\n"
