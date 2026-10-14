#!/usr/bin/env python3
"""Paper review harness CLI.

    hx.py personas [--venue V]                       list reviewer personas (all, or one venue's)
    hx.py new --paper main.pdf [--supp s.pdf] [--tex DIR] --name mypaper [--venue V] [--panel P]
              [--reviewers IDS] [--heldout IDS] [--figures] [--mode full|sections|both] [--sections KEYS]
              [--cutoff YYYY-MM-DD] [--allow-identified] ...
    hx.py round SESSION --paper main.pdf [--supp s.pdf] [--tex DIR] [--allow-identified]
                                                     next round on a revised draft
    hx.py retest SESSION [--of N]                    same draft again, fresh reviewers (noise floor)
    hx.py stage SESSION {fixcheck,pairwise,writer} [--round N]   writer loop helpers; default: the last
                                                     review round (retest rounds are refused)
    hx.py stage SESSION coach [--round N]            revision plan from the feedback reviews (hxlib/coach.py)
    hx.py validate SESSION [--round N]
    hx.py aggregate SESSION [--round N | --all]      SCORES, FEEDBACK.md, PROGRESS.md (default: latest round)
    hx.py status SESSION [--round N]                 jobs, files present, launch lines for the orchestrator

`round`, `stage writer` and `stage coach` refuse to build on a review round with pending or invalid
jobs; `validate` also checks `round_NN/coach/revision_plan.json` (job COACH) when it exists.
`new` and `round` refuse a PDF that shows author or publication information (hxlib/anonymity.py)
unless `--allow-identified` is given; `validate` prints advisory warnings (hxlib/review_warnings.py).
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
from hxlib.anonymity import IdentifiedCopyError, check_identified, flag_report  # noqa: E402
from hxlib.cli_status import (identified_notice, invalid_jobs, print_launch, print_personas,  # noqa: E402
                              print_status, round_arg, round_is_valid, stage_round, user_cutoff)
from hxlib.common import (PROTOCOL_DIR, SESSIONS_DIR, TEMPLATE_DIR, list_rounds, load_json,  # noqa: E402
                          load_scales, now_iso, resolve_session, round_dir, save_json, today)
from hxlib.panel import (build_jobs, check_section_keys, draw_panel, is_reviewer, load_personas,  # noqa: E402
                         load_section_map)
from hxlib.figure_job import figure_personas, is_figure_job  # noqa: E402
from hxlib.figure_prompts import figure_satisfy_prompt  # noqa: E402
from hxlib.venues import profile_for, freeze  # noqa: E402
from hxlib.paper import snapshot_paper  # noqa: E402
from hxlib.prompts import write_initial_prompts  # noqa: E402
from hxlib import coach, dialogue  # noqa: E402
from hxlib import prompts_stages as stages  # noqa: E402
from hxlib.validate import validate_round  # noqa: E402
from hxlib.review_warnings import round_warnings, validation_report  # noqa: E402
from hxlib.efficiency import response_fingerprint, same_paper, changed_sections  # noqa: E402

logger = logging.getLogger("hx")


def _require_inputs(pdf: Optional[Path], supp: Optional[Path], tex: Optional[Path]) -> None:
    """Fail before any folder is created when a named PDF or LaTeX folder does not exist."""
    for flag, path, is_dir in (("--paper", pdf, False), ("--supp", supp, False), ("--tex", tex, True)):
        if path is not None and not (path.is_dir() if is_dir else path.is_file()):
            raise FileNotFoundError(f"{flag} {path}: no such {'folder' if is_dir else 'file'}")


def _same_draft(paper: dict, previous: dict) -> bool:
    """Whether two snapshots hold the same main PDF and the same (or no) supplement."""
    return (paper["main_pdf_sha256"] == previous["main_pdf_sha256"]
            and paper.get("supp_pdf_sha256") == previous.get("supp_pdf_sha256"))


def _round_jobs(session: dict, rpath: Path, personas: dict, skip_heldout: bool) -> list[dict]:
    """Review jobs of a round (held-out jobs left out when `skip_heldout`); raises if there are none."""
    present = [s["key"] for s in load_json(rpath / "snapshot" / "sections.json")]
    jobs = build_jobs(session["mode"], session["panel_ids"], present, personas, session.get("only_sections"),
                      None if skip_heldout else session.get("heldout_ids"),
                      session.get("instruments", {}).get("section_map"), session.get("reading_mode", "persona"),
                      figures=session.get("figures", False))
    if not jobs:
        raise ValueError(f"No review jobs: the selected sections {session.get('only_sections')} are not "
                         f"among the sections found in the paper ({', '.join(present)})")
    return jobs


def _write_satisfy_prompts(session: dict, rnd: dict, personas: dict, rpath: Path, session_path: Path) -> list[Path]:
    """prompts/satisfy/<job>.md for every answer-check job (the figure job has its own builder)."""
    paths: list[Path] = []
    for job in (j for j in rnd["jobs"] if j.get("stage") == "satisfy"):
        path = rpath / "prompts" / "satisfy" / f"{job['job_id']}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        build = figure_satisfy_prompt if is_figure_job(job) else dialogue.satisfy_prompt
        path.write_text(build(session, rnd, job, personas, rpath, session_path), encoding="utf-8")
        paths.append(path)
    return paths


def _build_round(session_path: Path, session: dict, number: int, rpath: Path, pdf: Optional[Path],
                 supp: Optional[Path], tex: Optional[Path], retest_of: Optional[int]) -> None:
    """Fill a new round folder: snapshot, jobs, answer-check inputs, prompts, then ROUND.json.

    A non-retest round whose PDFs equal the previous review round's gets no held-out jobs: the
    held-out reviewers already judged that draft, and only the authors' answers changed. A new
    snapshot with anonymity flags raises IdentifiedCopyError unless the session allows it.
    """
    personas = session.get("instruments", {}).get("personas") or load_personas()
    if retest_of is not None:
        src = round_dir(session_path, retest_of)
        shutil.copytree(src / "snapshot", rpath / "snapshot")
        paper = load_json(src / "ROUND.json")["paper"]
    else:
        paper = snapshot_paper(pdf, rpath / "snapshot", supp, tex)
        check_identified(paper, bool(session.get("allow_identified")))
    prev_n = dialogue.last_dialogue_round(session_path, number) if retest_of is None and number > 1 else None
    previous = round_dir(session_path, prev_n) if prev_n else None
    prev_rnd = load_json(previous / "ROUND.json") if previous else None
    same_draft = prev_rnd is not None and _same_draft(paper, prev_rnd["paper"])
    jobs = _round_jobs(session, rpath, personas, skip_heldout=same_draft)
    rnd = {"round": number, "created": now_iso(), "retest_of": retest_of, "paper": paper,
           "panel": session["panel_ids"], "mode": session["mode"], "scale": session["scale"], "jobs": jobs}
    if "review_config" in session:
        rnd["review_config"] = session["review_config"]
    if same_draft and session.get("heldout_ids"):
        rnd["heldout_skipped"] = (f"same main and supplement PDF as round {prev_n:02d}; held-out reviews of "
                                  "an unchanged draft are not repeated")
    if previous is not None:
        open_ids = {item["id"] for item in dialogue.round_items(prev_rnd, previous)}
        rnd["response_fingerprint"] = response_fingerprint(previous / "writer" / "RESPONSE.md", open_ids)
        rnd["changes"] = changed_sections(previous / "snapshot", rpath / "snapshot")
        if session.get("loop", "dialogue") == "dialogue":
            dialogue.prepare_satisfaction(session_path, rnd, rpath)
    paths = write_initial_prompts(session, rnd, personas, rpath)
    paths += _write_satisfy_prompts(session, rnd, personas, rpath, session_path)
    rnd["prompt_sha256"] = {p.stem: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    save_json(rpath / "ROUND.json", rnd)


def _make_round(session_path: Path, session: dict, number: int, pdf: Optional[Path], supp: Optional[Path],
                tex: Optional[Path], retest_of: Optional[int] = None) -> Path:
    """Create round folder, snapshot (or copy a previous snapshot for a retest), jobs and prompts.

    On any failure the partial round folder is removed before the error propagates, so a failed
    round never leaves a `round_NN/` without ROUND.json that would break every later command.
    """
    rpath = round_dir(session_path, number)
    if rpath.exists():
        raise FileExistsError(f"{rpath} already exists")
    try:
        _build_round(session_path, session, number, rpath, pdf, supp, tex, retest_of)
    except IdentifiedCopyError:  # an expected refusal: the caller prints the flags
        shutil.rmtree(rpath, ignore_errors=True)
        raise
    except BaseException:  # any failure, Ctrl-C included: never leave a partial round behind
        logger.warning("round %d failed; removing the partial folder %s", number, rpath)
        shutil.rmtree(rpath, ignore_errors=True)
        raise
    session.setdefault("rounds", []).append(number)
    save_json(session_path / "SESSION.json", session)
    return rpath


def cmd_new(args: argparse.Namespace) -> int:
    pdf, supp, tex = Path(args.paper), Path(args.supp) if args.supp else None, Path(args.tex) if args.tex else None
    _require_inputs(pdf, supp, tex)
    only_sections = check_section_keys([s.strip() for s in args.sections.split(",")]) if args.sections else None
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
    if args.figures:  # the figure reader is a harness instrument usable with every venue profile
        personas.update(figure_personas(load_personas()))
    panel_ids = [x.strip() for x in args.reviewers.split(",")] if args.reviewers else draw_panel(panel_name, args.seed, personas, venue)
    named = panel_ids + (args.heldout.split(",") if args.heldout else [])
    unknown = [r for r in named if r not in personas]
    if unknown:
        raise KeyError(f"Unknown persona ids: {unknown}")
    instruments = [r for r in named if not is_reviewer(personas[r])]
    if instruments:
        raise ValueError(f"{instruments} are not reviewer personas; use --figures for the figure job")
    name = f"{today()}_{args.name}" + (f"_{args.tag}" if args.tag else "")
    spath = SESSIONS_DIR / name
    if spath.exists():
        raise FileExistsError(f"{spath} exists; use --tag")
    session = {"name": name, "created": now_iso(), "venue": profile["label"], "prior_work_cutoff": args.cutoff or profile["cutoff"],
               "venue_profile": profile, "reading_mode": reading, "contribution_type": contribution,
               "scale": scale,
               "panel_name": panel_name if not args.reviewers else "custom",
               "panel_ids": panel_ids, "seed": args.seed, "mode": args.mode,
               "heldout_ids": args.heldout.split(",") if args.heldout else [], "loop": args.loop,
               "figures": bool(args.figures), "only_sections": only_sections,
               "allow_identified": bool(args.allow_identified),
               "tex_dir": str(tex.resolve()) if tex else None, "rounds": []}
    freeze(session, personas, load_section_map(venue))
    spath.mkdir(parents=True)
    try:
        constraints = (TEMPLATE_DIR / "AUTHOR_CONSTRAINTS.md").read_text(encoding="utf-8")
        constraints = constraints.replace("8 content pages + references; supplement unlimited.", profile["page_budget"])
        (spath / "AUTHOR_CONSTRAINTS.md").write_text(constraints, encoding="utf-8")
        rpath = _make_round(spath, session, 1, pdf, supp, tex)
    except IdentifiedCopyError as exc:  # refused: no session is created
        shutil.rmtree(spath, ignore_errors=True)
        print(flag_report(exc.flags, "new", allowed=False, cutoff_set=bool(args.cutoff)))
        return 1
    except BaseException:  # a session without a usable round 1 would only block the name
        logger.warning("session %s failed; removing %s", name, spath)
        shutil.rmtree(spath, ignore_errors=True)
        raise
    print(f"session {spath}\npanel {panel_ids}\nround 1 -> {rpath}")
    identified_notice(rpath, "new", bool(args.cutoff))
    print_launch(rpath, "initial")
    return 0


def cmd_round(args: argparse.Namespace) -> int:
    spath = resolve_session(args.session)
    session = load_json(spath / "SESSION.json")
    pdf, supp = Path(args.paper), Path(args.supp) if args.supp else None
    _require_inputs(pdf, supp, Path(args.tex) if args.tex else None)
    number = (list_rounds(spath) or [0])[-1] + 1
    prev_n = dialogue.last_dialogue_round(spath, number)
    previous_path = round_dir(spath, prev_n)
    previous = load_json(previous_path / "ROUND.json")
    if not round_is_valid("round", spath, prev_n, previous, previous_path):
        return 1
    paper_unchanged = same_paper(pdf, supp, previous)
    open_ids = {item["id"] for item in dialogue.round_items(previous, previous_path)}
    answer_hash = response_fingerprint(previous_path / "writer" / "RESPONSE.md", open_ids)
    new_answer = (session.get("loop", "dialogue") == "dialogue" and answer_hash is not None
                  and answer_hash != previous.get("response_fingerprint"))
    if paper_unchanged and not new_answer:
        print("No new round: the PDFs and substantive author answers are unchanged. "
              "Use status to resume pending jobs, or retest for an intentional repeat review.")
        return 0
    tex = Path(args.tex) if args.tex else (Path(session["tex_dir"]) if session.get("tex_dir") else None)
    if args.allow_identified:  # kept in SESSION.json once the round is built
        session["allow_identified"] = True
    try:
        rpath = _make_round(spath, session, number, pdf, supp, tex)
    except IdentifiedCopyError as exc:
        print(flag_report(exc.flags, "round", allowed=False, cutoff_set=user_cutoff(session)))
        return 1
    print(f"round {number} -> {rpath}")
    identified_notice(rpath, "round", user_cutoff(session))
    skipped = load_json(rpath / "ROUND.json").get("heldout_skipped")
    if skipped:
        print(f"held-out reviewers skipped: {skipped}")
    print_launch(rpath, "initial")
    print_launch(rpath, "satisfy")
    return 0


def cmd_retest(args: argparse.Namespace) -> None:
    spath = resolve_session(args.session)
    session = load_json(spath / "SESSION.json")
    rounds = list_rounds(spath)
    base = args.of or max(n for n in rounds if not load_json(round_dir(spath, n) / "ROUND.json").get("retest_of"))
    rpath = _make_round(spath, session, rounds[-1] + 1, None, None, None, retest_of=base)
    print(f"retest of round {base} -> {rpath}")
    print_launch(rpath, "initial")


def _writer_brief(session: dict, rnd: dict, rpath: Path, spath: Path) -> str:
    """Answer sheet (and FEEDBACK if missing) for the writer, then the brief text."""
    (rpath / "writer").mkdir(exist_ok=True)
    coach.ensure_feedback(session, rnd, rpath)
    print(f"answer sheet: {dialogue.write_response_scaffold(rpath)}")
    return stages.writer_prompt(session, rnd, rpath, spath)


def cmd_stage(args: argparse.Namespace) -> int:
    spath = resolve_session(args.session)
    session = load_json(spath / "SESSION.json")
    number, rpath, rnd = stage_round(spath, args.round)
    if args.stage in ("writer", "coach"):
        if not round_is_valid(f"stage {args.stage}", spath, number, rnd, rpath):
            return 1
        brief = _writer_brief if args.stage == "writer" else coach.coach_brief
        text = brief(session, rnd, rpath, spath)
    elif args.stage == "fixcheck":
        text = stages.fixcheck_prompt(session, rnd, rpath)
    else:
        text = stages.pairwise_prompt(session, rnd, rpath, session["seed"])
    pdir = rpath / "prompts" / args.stage
    pdir.mkdir(parents=True, exist_ok=True)
    (pdir / f"{args.stage.upper()}.md").write_text(text, encoding="utf-8")
    print_launch(rpath, args.stage)
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    spath = resolve_session(args.session)
    number, rpath, rnd = round_arg(spath, args.round)
    results = validate_round(rnd, rpath)
    warnings = round_warnings(rnd, rpath, [jid for jid, errs in results.items() if not errs])
    results, warnings = coach.with_coach_check(rnd, rpath, results, warnings)
    print(validation_report(number, results, warnings))
    return 1 if any(results.values()) else 0


def cmd_aggregate(args: argparse.Namespace) -> int:
    spath = resolve_session(args.session)
    session = load_json(spath / "SESSION.json")
    numbers = list_rounds(spath) if args.all else [args.round or list_rounds(spath)[-1]]
    for n in numbers:
        rp = round_dir(spath, n)
        invalid = invalid_jobs(load_json(rp / "ROUND.json"), rp)
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


def cmd_status(args: argparse.Namespace) -> None:
    spath = resolve_session(args.session)
    number, rpath, rnd = round_arg(spath, args.round)
    print_status(spath, number, rpath, rnd)


def cmd_personas(args: argparse.Namespace) -> None:
    print_personas(args.venue)


def main(argv: Optional[list[str]] = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    q = sub.add_parser("personas")
    q.add_argument("--venue", help="list only this venue's personas (cvpr, iclr, icml, neurips)")
    q.set_defaults(fn=cmd_personas)
    p = sub.add_parser("new")
    p.add_argument("--paper", required=True)
    p.add_argument("--supp")
    p.add_argument("--tex", help="folder with the paper's LaTeX sources (snapshotted each round)")
    p.add_argument("--name", required=True)
    p.add_argument("--tag")
    p.add_argument("--panel", help="panel name from the venue's panel file; default: the venue profile's panel "
                                   "(CVPR: realistic; ICLR, ICML: balanced; NeurIPS: balanced, or the panel named "
                                   "after a non-general --contribution-type)")
    p.add_argument("--reviewers", help="comma list of persona ids; overrides --panel")
    p.add_argument("--heldout", help="comma list of persona ids for held-out reviewers the writer never sees")
    p.add_argument("--loop", choices=("dialogue", "fresh"), default="dialogue",
                   help="later rounds: the same reviewers judge your answers (dialogue) or fresh reviews (fresh)")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--mode", choices=("full", "sections", "both"), default="full")
    p.add_argument("--sections", help="comma list of section keys to restrict scoring (unknown keys are rejected)")
    p.add_argument("--venue", default="cvpr", help="cvpr, iclr, icml, neurips (versioned profiles)")
    p.add_argument("--reading", choices=("persona", "careful"))
    p.add_argument("--contribution-type", default="general", choices=("general", "theory", "use_inspired", "concept_feasibility", "negative_results"))
    p.add_argument("--cutoff", default=None,
                   help="optional search date boundary; does not override the venue publication-status policy")
    p.add_argument("--scale", default=None, help="rating profile in 02_protocol/scales.json (default: selected venue profile)")
    p.add_argument("--figures", action="store_true",
                   help="add the opt-in figure review job FIG (persona F01) to every round of the session")
    identified = ("review a PDF that shows author or publication information (author block, e-mail, "
                  "camera-ready or arXiv stamp, acknowledgements); reviewers are told to ignore it")
    p.add_argument("--allow-identified", action="store_true", help=identified)
    p.set_defaults(fn=cmd_new)
    q = sub.add_parser("round")
    q.add_argument("session")
    q.add_argument("--paper", required=True)
    q.add_argument("--supp")
    q.add_argument("--tex")
    q.add_argument("--allow-identified", action="store_true", help=identified + " (kept for the session)")
    q.set_defaults(fn=cmd_round)
    q = sub.add_parser("retest")
    q.add_argument("session")
    q.add_argument("--of", type=int)
    q.set_defaults(fn=cmd_retest)
    q = sub.add_parser("stage")
    q.add_argument("session")
    q.add_argument("stage", choices=("fixcheck", "pairwise", "writer", "coach"))
    q.add_argument("--round", type=int, help="review round to work on (default: the last non-retest round)")
    q.set_defaults(fn=cmd_stage)
    for name, fn in (("validate", cmd_validate), ("aggregate", cmd_aggregate), ("status", cmd_status)):
        q = sub.add_parser(name)
        q.add_argument("session")
        if name == "aggregate":
            selection = q.add_mutually_exclusive_group()
            selection.add_argument("--round", type=int)
            selection.add_argument("--all", action="store_true", help="rebuild every round; default: latest only")
        else:
            q.add_argument("--round", type=int)
        q.set_defaults(fn=fn)
    args = ap.parse_args(argv)
    result = args.fn(args)
    return int(result or 0)


if __name__ == "__main__":
    sys.exit(main())
