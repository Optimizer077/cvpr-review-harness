"""Validation warnings: findings that `hx.py validate` prints but that do not make a job invalid.

For an initial review (`review.md` + `review.json`):
- length: the words of review.md between the Summary heading and the first score table ('Section
  scores', or 'Figure scores' for FIG; from the file start or to its end when one is missing) lie
  more than 20% outside the persona's band, the numbers its Targets box showed
  (`prompts.persona_targets`). A section-only job and a careful review are held to the upper limit
  only, as their Targets box says;
- points: review.json has more weaknesses than the persona's `max_weaknesses`;
- numbering: the numbered points under the Weaknesses heading of review.md are not as many as the
  weaknesses in review.json (the prompt asks for point n = Wn).
For every valid job, satisfy stage included: the grounding warnings (quotes not found in the paper,
anchors, pages and Fig./Tab./Eq. numbers it does not have; `grounding_report`). A held-out job
shows only their number, as GROUNDING.md keeps held-out details in `heldout/GROUNDING.md`.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Iterable, Optional

from .common import load_json, read_text, review_dir
from .grounding_report import grounding_warnings, job_grounding
from .panel import load_personas
from .prompts import persona_targets
from .venues import careful

logger = logging.getLogger(__name__)

LENGTH_TOLERANCE = 0.2  # a review this far outside the persona's word band gets a warning

def _heading(word: str) -> re.Pattern:
    """A heading line for `word`: '## 3. Word ...', '**Word:** ...' (label) or a bare 'Word:' line.

    A sentence that starts with the word ('Weaknesses are minor.') is not a heading. Group 1 holds
    the '#' marks of an ATX heading.
    """
    return re.compile(rf"(?im)^[ \t]{{0,3}}(?:(#{{1,6}})[ \t]*(?:\d+\.?[ \t]*)?{word}\b[^\n]*$"
                      rf"|\*\*[ \t]*{word}\b[^*\n]*\*\*[ \t:]*|{word}[ \t]*:?[ \t]*$)")


_SUMMARY = _heading("summary")
_WEAKNESSES = _heading("weaknesses")
_SCORE_TABLE = re.compile(r"(?im)^[^\w\n]*(?:section|figure) scores\b")
_ATX = re.compile(r"^[ \t]{0,3}(#{1,6})[ \t]")
_BOLD_LINE = re.compile(r"^[ \t]*\*\*[^*]+\*\*[ \t:]*$")
_NUMBERED = re.compile(r"^ ?(?:\*\*)?\d{1,2}[.)][ \t]")  # top level only: nested items are indented


def review_words(md: str) -> int:
    """Words of a review between the Summary heading and the first score table (see module doc).

    A word is a whitespace-separated token with at least one letter or digit, so markdown marks
    ('##', '-', '|') do not count.
    """
    summary = _SUMMARY.search(md)
    start = summary.end() if summary else 0
    table = _SCORE_TABLE.search(md, start)
    body = md[start:table.start() if table else len(md)]
    return sum(1 for token in body.split() if any(ch.isalnum() for ch in token))


def numbered_weaknesses(md: str) -> Optional[int]:
    """Top-level numbered points ('1.', '2)') under the Weaknesses heading; None without the heading.

    The section ends at the next heading of the same or a higher level ('### Major' groups under
    '## Weaknesses' are inside it) or at the score table. Under a bold or bare 'Weaknesses' label it
    ends at any '#' heading or bold-only line.
    """
    lines = md.splitlines()
    found = next(((i, m) for i, line in enumerate(lines) if (m := _WEAKNESSES.match(line))), None)
    if found is None:
        return None
    start, match = found
    level = len(match.group(1)) if match.group(1) else None
    count = 0
    for line in lines[start + 1:]:
        atx = _ATX.match(line)
        if (_SCORE_TABLE.match(line) or (atx and (level is None or len(atx.group(1)) <= level))
                or (level is None and _BOLD_LINE.match(line))):
            break
        count += bool(_NUMBERED.match(line))
    return count


def _length_warning(words: int, band: list[int], upper_only: bool) -> Optional[str]:
    """A warning when `words` is more than LENGTH_TOLERANCE outside `band` (or above its maximum)."""
    low, high = band
    if words > high * (1 + LENGTH_TOLERANCE):
        limit = f"the limit is {high} words" if upper_only else f"the persona's band is {low}-{high} words"
        return f"review.md has {words} words; {limit} (more than 20% over)"
    if not upper_only and words < low * (1 - LENGTH_TOLERANCE):
        return f"review.md has {words} words; the persona's band is {low}-{high} words (more than 20% under)"
    return None


def shape_warnings(job: dict, round_path: Path, session: dict, personas: dict[str, dict]) -> list[str]:
    """Length, number of points and numbering warnings for one valid initial review."""
    out_dir = review_dir(round_path, job)
    md, data = read_text(out_dir / "review.md"), load_json(out_dir / "review.json")
    weaknesses = data.get("weaknesses") or []
    persona = personas.get(job["reviewer"])
    out: list[str] = []
    if persona is not None:
        band, most = persona_targets(session, persona)
        if band:
            warning = _length_warning(review_words(md), band, careful(session) or not job["overall"])
            out += [warning] if warning else []
        if most and len(weaknesses) > most:
            out.append(f"review.json has {len(weaknesses)} weaknesses; the persona allows at most {most}")
    numbered = numbered_weaknesses(md)
    if numbered is not None and numbered != len(weaknesses):
        out.append(f"review.md numbers {numbered} points under Weaknesses; review.json has {len(weaknesses)} "
                   "weaknesses (point n should be Wn)")
    return out


def _session(round_path: Path) -> dict:
    """SESSION.json of the round's session ({} when absent, e.g. a bare round folder)."""
    path = round_path.parent / "SESSION.json"
    return load_json(path) if path.exists() else {}


def job_warnings(job: dict, rnd: dict, round_path: Path, session: dict, personas: dict[str, dict]) -> list[str]:
    """All warnings of one valid job. A failing check is reported as a warning, never raised."""
    out: list[str] = []
    if job.get("stage", "initial") == "initial":
        try:
            out += shape_warnings(job, round_path, session, personas)
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            out.append(f"length and point checks skipped: {type(exc).__name__}: {exc}")
    try:
        grounding = grounding_warnings(job_grounding(job, rnd, round_path))
        if grounding and job.get("group") == "heldout":  # quotes of held-out reviews stay out of this output
            out.append(f"{len(grounding)} grounding warnings; held-out details go to heldout/GROUNDING.md "
                       "(written by aggregate)")
        else:
            out += grounding
    except Exception as exc:  # noqa: BLE001 - grounding is advisory; it must never break validation
        logger.warning("grounding check of %s failed: %s", job["job_id"], exc)
        out.append(f"grounding check skipped: {type(exc).__name__}: {exc}")
    return out


def round_warnings(rnd: dict, round_path: Path, valid: Iterable[str]) -> dict[str, list[str]]:
    """job_id -> warnings for the jobs named in `valid` (jobs that passed validation)."""
    session = _session(round_path)
    personas = session.get("instruments", {}).get("personas") or load_personas()
    wanted = set(valid)
    return {job["job_id"]: job_warnings(job, rnd, round_path, session, personas)
            for job in rnd["jobs"] if job["job_id"] in wanted}


def validation_report(number: int, results: dict[str, list[str]], warnings: dict[str, list[str]]) -> str:
    """What `hx.py validate` prints: OK/FAIL per job with its errors, then its warnings, then a total.

    Warnings never count as failures.
    """
    lines: list[str] = []
    for jid, errs in results.items():
        warns = warnings.get(jid, [])
        lines.append(f"{jid}: {'OK' if not errs else 'FAIL'}" + (f" ({len(warns)} warnings)" if warns else ""))
        lines += [f"    - {err}" for err in errs]
        lines += [f"    warning: {warn}" for warn in warns]
    bad = sum(1 for errs in results.values() if errs)
    total = sum(len(w) for w in warnings.values())
    lines.append(f"round {number}: {len(results) - bad}/{len(results)} valid"
                 + (f"; {total} warnings (advisory, not failures)" if total else ""))
    return "\n".join(lines)


__all__ = ["job_warnings", "numbered_weaknesses", "review_words", "round_warnings", "shape_warnings",
           "validation_report"]
