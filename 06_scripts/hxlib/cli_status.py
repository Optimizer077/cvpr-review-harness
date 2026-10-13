"""Read-only helpers of the `hx.py` CLI: round selection, launch lines, `status`, `personas`, the
validation gate that `round`, `stage writer` and `aggregate` share, and the notice for an allowed
identified copy.

Nothing here writes session files; the commands that build rounds stay in `hx.py`.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from .anonymity import flag_report
from .common import list_rounds, load_json, review_dir, round_dir
from .dialogue import last_dialogue_round
from .figure_job import inventory_ids, is_figure_job, load_inventory
from .panel import load_personas
from .validate import validate_round
from .venues import profile_for

logger = logging.getLogger(__name__)


def round_arg(spath: Path, value: Optional[int]) -> tuple[int, Path, dict]:
    """(number, folder, ROUND.json) of round `value`, or of the latest round."""
    number = value or list_rounds(spath)[-1]
    rpath = round_dir(spath, number)
    return number, rpath, load_json(rpath / "ROUND.json")


def stage_round(spath: Path, value: Optional[int]) -> tuple[int, Path, dict]:
    """Round a writer-loop stage works on: `--round N`, else the last review (non-retest) round.

    A retest repeats an older draft with fresh reviewers: the writer answers review rounds, and
    fixcheck and pairwise compare review rounds, so a retest round is refused.
    """
    latest = last_dialogue_round(spath, list_rounds(spath)[-1] + 1)
    number = value or latest
    rpath = round_dir(spath, number)
    rnd = load_json(rpath / "ROUND.json")
    if rnd.get("retest_of"):
        raise ValueError(f"round {number} is a retest of round {rnd['retest_of']}; writer-loop stages work "
                         f"on review rounds (latest: {latest}). Omit --round or name a review round.")
    return number, rpath, rnd


def invalid_jobs(rnd: dict, rpath: Path) -> dict[str, list[str]]:
    """Jobs of a round whose outputs are missing or fail validation."""
    return {jid: errors for jid, errors in validate_round(rnd, rpath).items() if errors}


def round_is_valid(action: str, spath: Path, number: int, rnd: dict, rpath: Path) -> bool:
    """Gate for commands that build on a round's reviews (the gate `aggregate` uses); prints why not."""
    invalid = invalid_jobs(rnd, rpath)
    if not invalid:
        return True
    print(f"{action} refused: round {number} has pending or invalid jobs: {', '.join(invalid)}")
    for jid, errors in invalid.items():
        print(f"    {jid}: {errors[0]}" + (f" (+{len(errors) - 1} more)" if len(errors) > 1 else ""))
    print(f"Run `hx.py status {spath.name} --round {number}`, finish or repair these jobs, then retry.")
    return False


def identified_notice(rpath: Path, command: str, cutoff_set: bool) -> None:
    """After a round is built from an allowed identified copy: print its anonymity flags."""
    flags = load_json(rpath / "ROUND.json")["paper"].get("anonymity_flags") or []
    if flags:
        print(flag_report(flags, command, allowed=True, cutoff_set=cutoff_set))


def user_cutoff(session: dict) -> bool:
    """Whether the session's prior-work cutoff differs from its venue profile's default (`--cutoff`)."""
    return session.get("prior_work_cutoff") != session.get("venue_profile", {}).get("cutoff")


def print_launch(rpath: Path, stage: str, checks: Optional[dict] = None) -> None:
    """Launch lines for the prompts of `stage`; initial and satisfy prompts only for pending jobs."""
    pdir = rpath / "prompts" / stage
    if not pdir.exists():
        return
    paths = sorted(pdir.glob("*.md"))
    if stage in ("initial", "satisfy"):
        if checks is None:
            checks = validate_round(load_json(rpath / "ROUND.json"), rpath)
        paths = [p for p in paths if checks.get(p.stem)]
    if not paths:
        return
    print(f"\nLaunch one fresh agent per pending prompt ({stage}); give each exactly this instruction:")
    for p in paths:
        print(f"  [{p.stem}] Read {p} and follow it exactly. Write only the files it names.")


def print_status(spath: Path, number: int, rpath: Path, rnd: dict) -> None:
    """`hx.py status`: jobs, output files present, and launch lines for pending jobs."""
    checks = validate_round(rnd, rpath)
    print(f"{spath.name} round {number} (retest_of={rnd.get('retest_of')}), mode {rnd['mode']}")
    if rnd.get("heldout_skipped"):
        print(f"  held-out reviewers skipped: {rnd['heldout_skipped']}")
    for job in rnd["jobs"]:
        if job.get("stage") == "satisfy":
            have = [f for f in ("reply.md", "satisfaction.json")
                    if (rpath / "satisfaction" / job["job_id"] / f).exists()]
        else:
            have = [f for f in ("review.md", "review.json", "debrief.md") if (review_dir(rpath, job) / f).exists()]
        print(f"  {job['job_id']:<8} {job.get('group', 'feedback'):<8} {job.get('stage', 'initial'):<7} view={job['view']:<5} overall={job['overall']!s:<5} "
              f"sections={len(job['sections'])} files={have}" + (figure_status(rpath) if is_figure_job(job) else ""))
    pending = sum(bool(errors) for errors in checks.values())
    print(f"{len(checks) - pending} complete; {pending} pending. Valid jobs do not need to run again.")
    print_launch(rpath, "initial", checks)
    print_launch(rpath, "satisfy", checks)


def figure_status(rpath: Path) -> str:
    """Suffix for the FIG job in `status`: how many figures/tables the snapshot inventory lists."""
    items = load_inventory(rpath / "snapshot")
    if items is None:
        return " kind=figures inventory=missing"
    main, every = inventory_ids(items)
    return f" kind=figures figures={len(main)} main/{len(every)} total"


def print_personas(venue: Optional[str]) -> None:
    """`hx.py personas`: one line per persona (all, or one venue's)."""
    for pid, p in load_personas(profile_for(venue)["venue"] if venue else None).items():
        print(f"{pid:<4} {p.get('name', ''):<34} role={p.get('role', 'reviewer'):<15} "
              f"pool={','.join(p.get('pool', [])) or '-':<16} "
              f"view={p.get('reading_view', '-'):<5} w={p.get('draw_weight', '-')}")
