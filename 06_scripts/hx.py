#!/usr/bin/env python3
"""Paper review harness CLI.

    hx.py personas                                   list reviewer personas
    hx.py new --paper main.pdf [--supp s.pdf] [--tex DIR] --name mypaper [--panel realistic] ...
    hx.py round SESSION --paper main.pdf [...]       next round on a revised draft (same panel)
    hx.py retest SESSION [--of N]                    same draft again, fresh reviewers (noise floor)
    hx.py stage SESSION {fixcheck,pairwise,writer} [--round N]   writer loop helpers
    hx.py validate SESSION [--round N]
    hx.py aggregate SESSION [--round N]
    hx.py status SESSION [--round N]                 jobs, files present, launch lines for the orchestrator
"""
from __future__ import annotations

import argparse
import hashlib
import logging
import shutil
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from hxlib.aggregate import aggregate_round, write_progress, write_round_report  # noqa: E402
from hxlib.common import (PROTOCOL_DIR, SESSIONS_DIR, TEMPLATE_DIR, list_rounds, load_json,  # noqa: E402
                          load_scales, now_iso, resolve_session, review_dir, round_dir, save_json, today)
from hxlib.panel import build_jobs, draw_panel, load_personas, load_section_map
from hxlib.venues import profile_for, freeze  # noqa: E402
from hxlib.paper import snapshot_paper  # noqa: E402
from hxlib.prompts import write_initial_prompts  # noqa: E402
from hxlib import dialogue  # noqa: E402
from hxlib import prompts_stages as stages  # noqa: E402
from hxlib.validate import validate_round  # noqa: E402

logger = logging.getLogger("hx")


def _make_round(session_path: Path, session: dict, number: int, pdf: Optional[Path], supp: Optional[Path],
                tex: Optional[Path], retest_of: Optional[int] = None) -> Path:
    """Create round folder, snapshot (or copy a previous snapshot for a retest), jobs and prompts."""
    personas = session.get("instruments", {}).get("personas") or load_personas()
    rpath = round_dir(session_path, number)
    if rpath.exists():
        raise FileExistsError(f"{rpath} already exists")
    if retest_of is not None:
        src = round_dir(session_path, retest_of)
        shutil.copytree(src / "snapshot", rpath / "snapshot")
        paper = load_json(src / "ROUND.json")["paper"]
    else:
        paper = snapshot_paper(pdf, rpath / "snapshot", supp, tex)
    sections = load_json(rpath / "snapshot" / "sections.json")
    present = [s["key"] for s in sections]
    jobs = build_jobs(session["mode"], session["panel_ids"], present, personas, session.get("only_sections"),
                      session.get("heldout_ids"), session.get("instruments", {}).get("section_map"),
                      session.get("reading_mode", "persona"))
    rnd = {"round": number, "created": now_iso(), "retest_of": retest_of, "paper": paper,
           "panel": session["panel_ids"], "mode": session["mode"], "scale": session["scale"], "jobs": jobs}
    if "review_config" in session:
        rnd["review_config"] = session["review_config"]
    if retest_of is None and session.get("loop", "dialogue") == "dialogue" and number > 1:
        dialogue.prepare_satisfaction(session_path, rnd, rpath)
    paths = write_initial_prompts(session, rnd, personas, rpath)
    sat_dir = rpath / "prompts" / "satisfy"
    for job in (j for j in jobs if j.get("stage") == "satisfy"):
        sat_dir.mkdir(parents=True, exist_ok=True)
        path = sat_dir / f"{job['job_id']}.md"
        path.write_text(dialogue.satisfy_prompt(session, rnd, job, personas, rpath, session_path), encoding="utf-8")
        paths.append(path)
    rnd["prompt_sha256"] = {p.stem: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    save_json(rpath / "ROUND.json", rnd)
    session.setdefault("rounds", []).append(number)
    save_json(session_path / "SESSION.json", session)
    return rpath


def cmd_new(args: argparse.Namespace) -> None:
    profile = profile_for(args.venue)
    venue = profile["venue"]
    reading = args.reading or profile["reading"]
    if venue != "cvpr" and reading != "careful":
        raise ValueError("New ML venue profiles require careful reading; behavioral simulation is CVPR-only")
    contribution = args.contribution_type
    if contribution not in profile["contribution_types"]:
        raise ValueError(f"Unsupported contribution type for {venue}: {contribution}")
    panel_name = args.panel or (contribution if venue == "neurips" and contribution != "general" else profile["panel"])
    scale = args.scale or profile["scale"]
    if venue != "cvpr" and scale != profile["scale"]:
        raise ValueError(f"{profile['label']} requires scale {profile['scale']}")
    load_scales(scale)
    personas = load_personas(venue)
    panel_ids = [x.strip() for x in args.reviewers.split(",")] if args.reviewers else draw_panel(panel_name, args.seed, personas, venue)
    unknown = [r for r in panel_ids + (args.heldout.split(",") if args.heldout else []) if r not in personas]
    if unknown:
        raise KeyError(f"Unknown persona ids: {unknown}")
    name = f"{today()}_{args.name}" + (f"_{args.tag}" if args.tag else "")
    spath = SESSIONS_DIR / name
    if spath.exists():
        raise FileExistsError(f"{spath} exists; use --tag")
    session = {"name": name, "created": now_iso(), "venue": profile["label"], "prior_work_cutoff": args.cutoff or profile["cutoff"],
               "venue_profile": profile, "reading_mode": reading, "contribution_type": contribution,
               "scale": scale,
               "domain": args.domain, "panel_name": panel_name if not args.reviewers else "custom",
               "panel_ids": panel_ids, "seed": args.seed, "mode": args.mode,
               "heldout_ids": args.heldout.split(",") if args.heldout else [], "loop": args.loop,
               "only_sections": args.sections.split(",") if args.sections else None,
               "tex_dir": str(Path(args.tex).resolve()) if args.tex else None, "rounds": []}
    freeze(session, personas, load_section_map(venue))
    if args.domain and f"07_domain_packs/{args.domain}.md" not in session["instruments"]["texts"]:
        raise ValueError(f"Unknown domain pack: {args.domain}")
    spath.mkdir(parents=True)
    constraints = (TEMPLATE_DIR / "AUTHOR_CONSTRAINTS.md").read_text(encoding="utf-8")
    constraints = constraints.replace("8 content pages + references; supplement unlimited.", profile["page_budget"])
    (spath / "AUTHOR_CONSTRAINTS.md").write_text(constraints, encoding="utf-8")
    rpath = _make_round(spath, session, 1, Path(args.paper), Path(args.supp) if args.supp else None,
                        Path(args.tex) if args.tex else None)
    print(f"session {spath}\npanel {panel_ids}\nround 1 -> {rpath}")
    _print_launch(rpath, "initial")


def cmd_round(args: argparse.Namespace) -> None:
    spath = resolve_session(args.session)
    session = load_json(spath / "SESSION.json")
    number = (list_rounds(spath) or [0])[-1] + 1
    tex = Path(args.tex) if args.tex else (Path(session["tex_dir"]) if session.get("tex_dir") else None)
    rpath = _make_round(spath, session, number, Path(args.paper), Path(args.supp) if args.supp else None, tex)
    print(f"round {number} -> {rpath}")
    _print_launch(rpath, "initial")
    _print_launch(rpath, "satisfy")


def cmd_retest(args: argparse.Namespace) -> None:
    spath = resolve_session(args.session)
    session = load_json(spath / "SESSION.json")
    rounds = list_rounds(spath)
    base = args.of or max(n for n in rounds if not load_json(round_dir(spath, n) / "ROUND.json").get("retest_of"))
    rpath = _make_round(spath, session, rounds[-1] + 1, None, None, None, retest_of=base)
    print(f"retest of round {base} -> {rpath}")
    _print_launch(rpath, "initial")


def _round_arg(spath: Path, value: Optional[int]) -> tuple[int, Path, dict]:
    number = value or list_rounds(spath)[-1]
    rpath = round_dir(spath, number)
    return number, rpath, load_json(rpath / "ROUND.json")


def cmd_stage(args: argparse.Namespace) -> None:
    spath = resolve_session(args.session)
    session = load_json(spath / "SESSION.json")
    _, rpath, rnd = _round_arg(spath, args.round)
    pdir = rpath / "prompts" / args.stage
    pdir.mkdir(parents=True, exist_ok=True)
    if args.stage == "fixcheck":
        if rnd["round"] < 2:
            raise ValueError("fixcheck needs a previous round")
        (pdir / "FIXCHECK.md").write_text(stages.fixcheck_prompt(session, rnd, rpath), encoding="utf-8")
    elif args.stage == "pairwise":
        if rnd["round"] < 2:
            raise ValueError("pairwise needs a previous round")
        (pdir / "PAIRWISE.md").write_text(stages.pairwise_prompt(session, rnd, rpath, session["seed"]),
                                          encoding="utf-8")
    elif args.stage == "writer":
        (rpath / "writer").mkdir(exist_ok=True)
        if not (rpath / "FEEDBACK.json").exists():
            dialogue.write_feedback(rnd, rpath, session.get("instruments", {}).get("personas") or load_personas())
        print(f"answer sheet: {dialogue.write_response_scaffold(rpath)}")
        (pdir / "WRITER.md").write_text(stages.writer_prompt(session, rnd, rpath, spath), encoding="utf-8")
    _print_launch(rpath, args.stage)


def cmd_validate(args: argparse.Namespace) -> int:
    spath = resolve_session(args.session)
    number, rpath, rnd = _round_arg(spath, args.round)
    results = validate_round(rnd, rpath)
    bad = 0
    for jid, errs in results.items():
        print(f"{jid}: {'OK' if not errs else 'FAIL'}")
        for err in errs:
            print(f"    - {err}")
        bad += bool(errs)
    print(f"round {number}: {len(results) - bad}/{len(results)} valid")
    return 1 if bad else 0


def cmd_aggregate(args: argparse.Namespace) -> int:
    spath = resolve_session(args.session)
    session = load_json(spath / "SESSION.json")
    numbers = [args.round] if args.round else list_rounds(spath)
    for n in numbers:
        rp = round_dir(spath, n)
        invalid = {jid: errors for jid, errors in validate_round(load_json(rp / "ROUND.json"), rp).items() if errors}
        if invalid:
            print(f"round {n}: aggregation refused; validate and repair invalid jobs: {', '.join(invalid)}")
            return 1
    for n in numbers:
        rpath = round_dir(spath, n)
        rnd = load_json(rpath / "ROUND.json")
        agg = aggregate_round(rnd, rpath)
        write_round_report(agg, rpath)
        if not rnd.get("retest_of"):
            items = dialogue.write_feedback(rnd, rpath, session.get("instruments", {}).get("personas") or load_personas())
            print(f"round {n}: FEEDBACK.md with {len(items)} open points")
        fb = agg["groups"]["feedback"]["overall"]
        print(f"round {n}: {agg['reviews_found']}/{agg['jobs']} reviews, feedback rating {fb}")
    print(write_progress(spath))
    return 0


def _print_launch(rpath: Path, stage: str) -> None:
    pdir = rpath / "prompts" / stage
    if not pdir.exists():
        return
    print(f"\nLaunch one fresh agent per prompt ({stage}); give each exactly this instruction:")
    for p in sorted(pdir.glob("*.md")):
        print(f"  [{p.stem}] Read {p} and follow it exactly. Write only the files it names.")


def cmd_status(args: argparse.Namespace) -> None:
    spath = resolve_session(args.session)
    number, rpath, rnd = _round_arg(spath, args.round)
    print(f"{spath.name} round {number} (retest_of={rnd.get('retest_of')}), mode {rnd['mode']}")
    for job in rnd["jobs"]:
        if job.get("stage") == "satisfy":
            have = [f for f in ("reply.md", "satisfaction.json")
                    if (rpath / "satisfaction" / job["job_id"] / f).exists()]
        else:
            have = [f for f in ("review.md", "review.json", "debrief.md") if (review_dir(rpath, job) / f).exists()]
        print(f"  {job['job_id']:<8} {job.get('group', 'feedback'):<8} {job.get('stage', 'initial'):<7} view={job['view']:<5} overall={job['overall']!s:<5} "
              f"sections={len(job['sections'])} files={have}")
    _print_launch(rpath, "initial")
    _print_launch(rpath, "satisfy")


def cmd_personas(args: argparse.Namespace) -> None:
    for pid, p in load_personas(profile_for(args.venue)["venue"] if args.venue else None).items():
        print(f"{pid:<4} {p.get('name', ''):<34} pool={','.join(p.get('pool', [])):<16} "
              f"view={p.get('reading_view', '-'):<5} w={p.get('draw_weight', '-')}")


def main(argv: Optional[list[str]] = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    q = sub.add_parser("personas")
    q.add_argument("--venue")
    q.set_defaults(fn=cmd_personas)
    p = sub.add_parser("new")
    p.add_argument("--paper", required=True)
    p.add_argument("--supp")
    p.add_argument("--tex")
    p.add_argument("--name", required=True)
    p.add_argument("--tag")
    p.add_argument("--panel", help="venue-specific panel; defaults to realistic (CVPR) or balanced")
    p.add_argument("--reviewers", help="comma list of persona ids; overrides --panel")
    p.add_argument("--heldout", help="comma list of persona ids for held-out reviewers the writer never sees")
    p.add_argument("--loop", choices=("dialogue", "fresh"), default="dialogue",
                   help="later rounds: the same reviewers judge your answers (dialogue) or fresh reviews (fresh)")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--mode", choices=("full", "sections", "both"), default="full")
    p.add_argument("--sections", help="comma list of section keys to restrict scoring")
    p.add_argument("--domain", default=None, help="domain pack name in 07_domain_packs (no .md)")
    p.add_argument("--venue", default="cvpr", help="cvpr, iclr, icml, neurips (versioned profiles)")
    p.add_argument("--reading", choices=("persona", "careful"))
    p.add_argument("--contribution-type", default="general", choices=("general", "theory", "use_inspired", "concept_feasibility", "negative_results"))
    p.add_argument("--cutoff", default=None,
                   help="optional search date boundary; does not override the venue publication-status policy")
    p.add_argument("--scale", default=None, help="rating profile in 02_protocol/scales.json (default: selected venue profile)")
    p.set_defaults(fn=cmd_new)
    for name, fn in (("round", cmd_round),):
        q = sub.add_parser(name)
        q.add_argument("session")
        q.add_argument("--paper", required=True)
        q.add_argument("--supp")
        q.add_argument("--tex")
        q.set_defaults(fn=fn)
    q = sub.add_parser("retest")
    q.add_argument("session")
    q.add_argument("--of", type=int)
    q.set_defaults(fn=cmd_retest)
    q = sub.add_parser("stage")
    q.add_argument("session")
    q.add_argument("stage", choices=("fixcheck", "pairwise", "writer"))
    q.add_argument("--round", type=int)
    q.set_defaults(fn=cmd_stage)
    for name, fn in (("validate", cmd_validate), ("aggregate", cmd_aggregate), ("status", cmd_status)):
        q = sub.add_parser(name)
        q.add_argument("session")
        q.add_argument("--round", type=int)
        q.set_defaults(fn=fn)
    args = ap.parse_args(argv)
    result = args.fn(args)
    return int(result or 0)


if __name__ == "__main__":
    sys.exit(main())
