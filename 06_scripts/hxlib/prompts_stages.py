"""Prompts for the writer loop after the independent reviews.

fixcheck    - a neutral checker marks each previous-round weakness as resolved or not in the new draft
pairwise    - a blind judge compares changed sections between two drafts (order randomized)
writer      - the brief handed to the writer agent after a round
"""
from __future__ import annotations

import logging
import random
import re
from pathlib import Path

from .common import PROTOCOL_DIR, load_json, round_dir, save_json
from .prompts import read_text
from .venues import instrument

logger = logging.getLogger(__name__)


def collect_weaknesses(round_path: Path) -> list[dict]:
    """All weaknesses of a round with global ids '<job>:<W#>'."""
    items: list[dict] = []
    for path in sorted((round_path / "reviews").glob("*/review.json")):
        data = load_json(path)
        for w in data.get("weaknesses", []):
            items.append({"id": f"{data['job_id']}:{w['id']}", "severity": w.get("severity"),
                          "category": w.get("category"), "location": w.get("location"),
                          "text": w.get("text"), "fixable_by": w.get("fixable_by")})
    return items


def fixcheck_prompt(session: dict, rnd: dict, round_path: Path) -> str:
    """Neutral check of previous-round weaknesses against the new draft."""
    prev = round_dir(round_path.parent, rnd["round"] - 1)
    items = collect_weaknesses(prev)
    save_json(round_path / "fixcheck" / "previous_weaknesses.json", items)
    out = round_path / "fixcheck"
    lines = [
        f"# Fix check - {session['name']}, round {rnd['round']:02d} vs round {rnd['round'] - 1:02d}",
        instrument(session, PROTOCOL_DIR / "fixcheck_rules.md"),
        f"- Weakness list from the previous draft: `{out / 'previous_weaknesses.json'}` ({len(items)} items).",
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


def pairwise_prompt(session: dict, rnd: dict, round_path: Path, seed: int) -> str:
    """Blind A/B comparison of each section that changed between the previous and this draft."""
    prev = round_dir(round_path.parent, rnd["round"] - 1)
    rng = random.Random(seed * 1000 + rnd["round"])
    pdir = round_path / "pairwise"
    key: dict[str, dict] = {}
    for sec_file in sorted((round_path / "snapshot" / "sections").glob("*.txt")):
        old_file = prev / "snapshot" / "sections" / sec_file.name
        if not old_file.exists():
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
    save_json(pdir / "_key" / "KEY.json", key)
    lines = [
        f"# Blind pairwise judgement - {session['venue']}",
        instrument(session, PROTOCOL_DIR / "pairwise_rules.md"),
        "Sections to compare: " + (", ".join(key) or "none (no section changed)"),
        f"Files: `{pdir}/A_<section>.txt` and `{pdir}/B_<section>.txt`. Do NOT open `{pdir / '_key'}`.",
        f"Write `{pdir / 'pairwise.json'}` = [{{\"section\": str, \"preferred\": \"A|B|tie\", "
        "\"margin\": 0-3, \"reason\": str, \"reviewer_types_that_care\": [str]}].",
        "Reply with one line per section: preferred version and margin.",
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
        "suggested fix and what would satisfy them, most important first, then section scores.",
        f"- Scores: `{round_path / 'SCORES.md'}`",
        f"- Reviews, replies and debriefs: `{round_path / 'reviews'}/<id>/` and "
        f"`{round_path / 'satisfaction'}/<id>/reply.md` (if this was an answer round). Never open "
        f"`{round_path / 'heldout'}`: those reviews judge your revision and must stay unseen.",
        f"- Author constraints: `{session_path / 'AUTHOR_CONSTRAINTS.md'}`",
        f"- Paper sources you may edit: `{session.get('tex_dir') or 'see SESSION.json'}`",
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
