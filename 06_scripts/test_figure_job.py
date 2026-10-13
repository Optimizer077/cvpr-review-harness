#!/usr/bin/env python3
"""Tests for the opt-in figure review job (FIG, persona F01; `hx.py new --figures`). No LLM calls.

Builds a synthetic paper with a captioned vector figure and a table, runs a --figures session,
writes fake outputs and checks: job and prompt (slimmed: no generic schema or sources, figure
categories only, line anchors only when the paper has margin numbers), validation (valid passes;
wrong keys, bad defect, missing figure fail), aggregation tables, the round-2 answer-check prompt
with old and new crops, a caption the locator missed (placeholder, required id), frozen criteria,
other venues, and that panels never draw F01. Exit code 0 = pass.
"""
from __future__ import annotations

import contextlib
import copy
import io
import logging
import random
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Optional
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import hx  # noqa: E402
from hxlib.common import PROTOCOL_DIR, load_json, load_scales, review_dir, round_dir, save_json  # noqa: E402
from hxlib.figure_job import FALLBACK_TEXTS, figure_job, inventory_ids, load_inventory  # noqa: E402
from hxlib.figure_prompts import figure_initial_prompt, optional_instrument  # noqa: E402
from hxlib.figure_render import snapshot_figures  # noqa: E402
from hxlib.panel import draw_panel, load_personas  # noqa: E402
from hxlib.paper import extract_lines  # noqa: E402
from hxlib.validate import validate_round  # noqa: E402
from smoke_test import fake_review  # noqa: E402
from test_venues import extensions  # noqa: E402

logger = logging.getLogger("test_figure_job")
_SNAPSHOT = hx.snapshot_paper
_BODY = ("This paragraph is ordinary body text of the toy paper, long enough to wrap over several "
         "lines so that the locator sees a prose block of body size around the figure and table. ")


def make_figure_pdf(path: Path, variant: int) -> None:
    """One page: title, abstract, sections, a vector bar plot (Fig. 1) and a table (Tab. 1).

    Variant 2 enlarges the bar labels and changes the bars, so only the figure crop changes.
    """
    import fitz

    doc = fitz.open()
    page = doc.new_page(width=612, height=792)

    def para(rect: tuple, text: str) -> None:
        page.insert_textbox(fitz.Rect(*rect), text, fontsize=9, fontname="helv")

    page.insert_text((60, 50), "Toy Title For A Figure Test", fontsize=14)
    page.insert_text((60, 70), "Abstract", fontsize=10)
    para((60, 75, 552, 120), "We propose a toy method. It improves a toy metric by 1 dB. " * 3)
    page.insert_text((60, 135), "1. Introduction", fontsize=10)
    para((60, 140, 552, 200), _BODY * 2 + "As Fig. 1 shows, ours is better. Tab. 1 lists results.")
    top = 215
    page.draw_rect(fitz.Rect(150, top, 450, top + 120), color=(0, 0, 0), width=0.8)
    for k, h in enumerate((40, 70, 100) if variant == 1 else (50, 80, 110)):
        page.draw_rect(fitz.Rect(180 + 80 * k, top + 120 - h, 220 + 80 * k, top + 120),
                       color=(0.1, 0.3, 0.8), fill=(0.1 + 0.3 * k, 0.3, 0.8 - 0.3 * k))
    for x, label in ((170, "A"), (250, "B"), (330, "Ours")):
        page.insert_text((x, top + 132), label, fontsize=5 if variant == 1 else 8)
    para((60, top + 140, 552, top + 170), "Figure 1. Toy bar plot. Our method reaches the highest toy score.")
    page.insert_text((60, 410), "2. Method", fontsize=10)
    para((60, 415, 552, 470), _BODY * 2)
    para((60, 478, 552, 500), "Table 1. Toy results on the toy benchmark for three methods and two "
                              "metrics. The best result per column is bold.")
    for r, row in enumerate((("Method", "PSNR", "SSIM"), ("A", "30.1", "0.91"), ("Ours", "31.2", "0.93"))):
        for c, cell in enumerate(row):
            page.insert_text((150 + 110 * c, 510 + 13 * r), cell, fontsize=8)
    for y, heading in ((570, "3. Experiments"), (645, "4. Conclusion")):
        page.insert_text((60, y), heading, fontsize=10)
        para((60, y + 5, 552, y + 60), _BODY * 2)
    page.insert_text((60, 715), "References", fontsize=10)
    page.insert_text((60, 730), "[1] A. Author. A paper. CVPR 2024.", fontsize=9)
    doc.save(path)
    doc.close()


def snapshot_with_figures(pdf: Path, dest: Path, supp: Optional[Path] = None, tex: Optional[Path] = None) -> dict:
    """Stand-in for the paper snapshot wiring: add figures/ when the snapshot does not write it yet."""
    meta = _SNAPSHOT(pdf, dest, supp, tex)
    if not (dest / "figures" / "figures.json").exists():
        meta["figures"] = snapshot_figures(dest, dest / "main.pdf", extract_lines(dest / "main.pdf"))
    return meta


def run_cli(*args: str) -> tuple[int, str]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        result = hx.main(list(args))
    return result, buf.getvalue()


def figure_entry(fid: str, score: int) -> dict:
    table = fid.startswith("tab")
    return {"role": "table" if table else "quantitative_plot",
            "perceived_message": "three bars; the rightmost is tallest" if not table else "Ours row is highest",
            "intended_message": "ours scores highest", "score": score,
            "criteria": {"message_clarity": 3, "legibility": 2, "encoding_fit": 4, "accessibility": 3,
                         "caption_alignment": 3, "comparison_fairness": 4 if table else None},
            "visible_evidence": "labels 'A', 'B', 'Ours'; FIGURES.md smallest text 5.0 pt",
            "main_issue": "labels too small at print size", "location": f"{fid}, x-axis",
            "one_point_fix": "set labels to at least 7 pt at column width"}


def figure_weaknesses(main: list[str]) -> list[dict]:
    base = {"severity": "moderate", "category": "figures", "decisive": False, "fixable_by": "writing",
            "suggested_fix": "enlarge the labels", "would_change_mind": "labels readable in the new crop"}
    return [dict(base, id="W1", figure_id=main[0], defect="illegible_text", location="Fig. 1", text="tiny labels"),
            dict(base, id="W2", figure_id=main[1], defect="caption_not_self_contained", location="Tab. 1",
                 text="caption does not say what to conclude"),
            dict(base, id="W3", figure_id="global", defect="inconsistent_style", location="Fig. 1, Tab. 1",
                 text="method names differ between figure and table")]


def write_outputs(rpath: Path) -> None:
    """Valid outputs for every job of a round; the FIG job gets figure_scores and tagged weaknesses."""
    rnd = load_json(rpath / "ROUND.json")
    items = load_inventory(rpath / "snapshot")
    main = inventory_ids(items)[0] if items is not None else ["fig_1", "tab_1"]
    for job in rnd["jobs"]:
        data = extensions(fake_review(job, rnd, random.Random(3)), job, rnd)
        if job.get("kind") == "figures":
            data["first_impression"] = None
            data["figure_scores"] = {fid: figure_entry(fid, 4 + k) for k, fid in enumerate(main)}
            data["weaknesses"] = figure_weaknesses(main)
        if job.get("stage") == "satisfy":
            out = rpath / "satisfaction" / job["job_id"]
            new = [dict(data["weaknesses"][0], id="W9")] if job.get("kind") == "figures" else []
            data.update(stage="satisfy", previous_rating=None if not job["overall"] else 3, new_issues=new,
                        items=[{"id": w, "status": "satisfied" if k == 0 else "partly", "reason": "toy",
                                "evidence": "Fig. 1"} for k, w in enumerate(job["open_items"])])
            save_json(out / "satisfaction.json", data)
            (out / "reply.md").write_text("Toy answer check with enough content for the size check.\n")
            continue
        out = review_dir(rpath, job)
        save_json(out / "review.json", data)
        heads = load_scales()["review_md_headings"]
        (out / "review.md").write_text("\n".join(f"## {h}\ntoy review text." for h in heads) + "\n")
        (out / "debrief.md").write_text("Toy debrief with enough content for the output-size validation.\n")


def check_invalid_figure_reviews(rpath: Path) -> None:
    """Wrong keys, bad defect, missing figure, bad role, bad null, unknown figure id must fail."""
    rnd = load_json(rpath / "ROUND.json")
    job = next(j for j in rnd["jobs"] if j["job_id"] == "FIG")
    path = review_dir(rpath, job) / "review.json"
    good = load_json(path)
    assert validate_round(rnd, rpath)["FIG"] == [], validate_round(rnd, rpath)["FIG"]
    breakages = {
        "missing_figure": lambda d: d["figure_scores"].pop("tab_1"),
        "unknown_key": lambda d: d["figure_scores"].__setitem__("fig_99", figure_entry("fig_99", 5)),
        "wrong_criteria": lambda d: d["figure_scores"]["fig_1"]["criteria"].pop("legibility"),
        "bad_null": lambda d: d["figure_scores"]["fig_1"]["criteria"].__setitem__("legibility", None),
        "out_of_range": lambda d: d["figure_scores"]["fig_1"].__setitem__("score", 11),
        "bad_role": lambda d: d["figure_scores"]["fig_1"].__setitem__("role", "poster"),
        "empty_evidence": lambda d: d["figure_scores"]["tab_1"].__setitem__("visible_evidence", " "),
        "bad_defect": lambda d: d["weaknesses"][0].__setitem__("defect", "ugly"),
        "unknown_figure_id": lambda d: d["weaknesses"][1].__setitem__("figure_id", "fig_7"),
        "no_figure_scores": lambda d: d.pop("figure_scores"),
        "first_impression": lambda d: d.__setitem__("first_impression", {"rating": 3}),
    }
    for name, breakage in breakages.items():
        data = copy.deepcopy(good)
        breakage(data)
        save_json(path, data)
        assert validate_round(rnd, rpath)["FIG"], f"{name} must fail validation"
    save_json(path, good)
    print(f"OK validation: valid FIG review passes; {len(breakages)} broken variants fail")
    check_without_inventory(rnd, rpath, job, path, good)


def check_without_inventory(rnd: dict, rpath: Path, job: dict, path: Path, good: dict) -> None:
    """No (or a corrupt) figures.json: captioned ids are required, other keys must look like ids."""
    inventory = rpath / "snapshot" / "figures" / "figures.json"
    shutil.move(inventory, inventory.with_suffix(".bak"))
    assert validate_round(rnd, rpath)["FIG"] == []
    for name, breakage in (("non_id_key", lambda d: d["figure_scores"].__setitem__("figure one", figure_entry("fig_1", 5))),
                           ("missing_captioned_id", lambda d: d["figure_scores"].pop("tab_1")),
                           ("empty", lambda d: d["figure_scores"].clear())):
        data = copy.deepcopy(good)
        breakage(data)
        save_json(path, data)
        assert validate_round(rnd, rpath)["FIG"], f"{name} must fail without an inventory"
    save_json(path, good)
    session = load_json(rpath.parent / "SESSION.json")
    text = figure_initial_prompt(session, rnd, job, session["instruments"]["personas"], rpath)
    assert "No figure inventory or crops were produced" in text and "at least fig_1, tab_1" in text, text[:200]
    assert "FIGURES.md` (crop" not in text
    inventory.write_text("{broken JSON", encoding="utf-8")
    assert validate_round(rnd, rpath)["FIG"] == [], "a corrupt inventory falls back to the captions"
    assert "inventory=missing" in run_cli("status", str(rpath.parent))[1]
    inventory.unlink()
    shutil.move(inventory.with_suffix(".bak"), inventory)
    print("OK no or corrupt inventory: captioned ids required, prompt points to the PDF pages")


def check_cvpr_session(tmpd: Path) -> None:
    """--figures session: job, prompt, validation, aggregate, round-2 crops, retest, status."""
    pdf1, pdf2 = tmpd / "v1.pdf", tmpd / "v2.pdf"
    make_figure_pdf(pdf1, 1)
    make_figure_pdf(pdf2, 2)
    assert run_cli("new", "--paper", str(pdf1), "--name", "figs", "--reviewers", "R07,R09", "--figures")[0] == 0
    spath = next(p for p in hx.SESSIONS_DIR.iterdir() if p.name.endswith("_figs"))
    session = load_json(spath / "SESSION.json")
    assert session["figures"] is True and session["panel_ids"] == ["R07", "R09"]
    assert session["review_config"]["figure_criteria"] == load_json(PROTOCOL_DIR / "figure_criteria.json")
    r1 = round_dir(spath, 1)
    jobs = {j["job_id"]: j for j in load_json(r1 / "ROUND.json")["jobs"]}
    assert jobs["FIG"] == figure_job(), jobs["FIG"]
    assert all("kind" not in j for jid, j in jobs.items() if jid != "FIG")
    prompt = (r1 / "prompts" / "initial" / "FIG.md").read_text(encoding="utf-8")
    for needle in (str(r1 / "snapshot" / "figures" / "fig_1.png"), str(r1 / "snapshot" / "FIGURES.md"),
                   "exactly these main-paper ids: fig_1, tab_1", "figure_scores", "comparison_fairness",
                   "illegible_text", "view_main.txt", "## figures_tables", "deuteranopia"):
        assert needle in prompt, needle
    assert "## 3. Review form" not in prompt and "figure_scores" not in \
        (r1 / "prompts" / "initial" / "R07.md").read_text(encoding="utf-8")
    check_slim_prompt(prompt, r1)
    print("OK --figures session: FIG job and prompt (crops, ids, criteria, schema)")
    write_outputs(r1)
    check_invalid_figure_reviews(r1)
    code, text = run_cli("status", str(spath))
    assert code == 0 and "FIG" in text and "kind=figures figures=2 main/2 total" in text, text
    assert run_cli("aggregate", str(spath))[0] == 0
    scores = load_json(r1 / "SCORES.json")
    assert scores["figures"]["fig_1"] == {"score": 4, "role": "quantitative_plot", "main_issue":
                                          "labels too small at print size", "location": "fig_1, x-axis",
                                          "one_point_fix": "set labels to at least 7 pt at column width"}
    assert scores["groups"]["feedback"]["overall"]["n"] == 2, "FIG must not count as an overall rating"
    md = (r1 / "SCORES.md").read_text(encoding="utf-8")
    assert "## Figure scores (FIG job)" in md and md.index("| fig_1 |") < md.index("| tab_1 |")
    feedback = (r1 / "FEEDBACK.md").read_text(encoding="utf-8")
    assert "## Figure scores (FIG job, lowest first)" in feedback and "**Figure / defect:** fig_1 / illegible_text" in feedback
    assert "figures (FIG job)**: mean 4.5" in (spath / "PROGRESS.md").read_text(encoding="utf-8")
    print("OK aggregate: SCORES.json/SCORES.md/FEEDBACK.md figure tables, PROGRESS.md figure mean")

    assert run_cli("round", str(spath), "--paper", str(pdf2))[0] == 0
    r2 = round_dir(spath, 2)
    fig2 = next(j for j in load_json(r2 / "ROUND.json")["jobs"] if j["job_id"] == "FIG")
    assert fig2["stage"] == "satisfy" and fig2["open_items"] == ["W1", "W2", "W3"] and fig2["kind"] == "figures"
    assert load_json(r2 / "satisfaction" / "FIG" / "OPEN_ITEMS.json")[0]["figure_id"] == "fig_1"
    sat = (r2 / "prompts" / "satisfy" / "FIG.md").read_text(encoding="utf-8")
    old_crop, new_crop = r1 / "snapshot" / "figures" / "fig_1.png", r2 / "snapshot" / "figures" / "fig_1.png"
    w1 = next(line for line in sat.splitlines() if line.startswith("- W1 (fig_1"))
    assert f"previous `{old_crop}`" in w1 and f"new `{new_crop}`" in w1 and "byte-identical" not in w1, w1
    w2 = next(line for line in sat.splitlines() if line.startswith("- W2 (tab_1"))
    assert "byte-identical" in w2 and str(r1 / "snapshot" / "figures" / "tab_1.png") in w2, w2
    assert "- W3 (global" in sat and "round 01 - your review" in sat and "figure_scores" in sat
    assert str(review_dir(r1, {"job_id": "R07"})) not in sat, "the figure reader must not see other reviews"
    print("OK round 2: FIG answer-check prompt lists previous and new crop per open point")
    assert run_cli("validate", str(spath))[0] == 1, "missing verdicts must fail"
    write_outputs(r2)
    assert run_cli("validate", str(spath))[0] == 0
    sat_path = r2 / "satisfaction" / "FIG" / "satisfaction.json"
    good = load_json(sat_path)
    for breakage in ("figure_scores", "defect"):
        data = copy.deepcopy(good)
        if breakage == "figure_scores":
            data.pop("figure_scores")
        else:
            data["new_issues"][0]["defect"] = "not_a_defect"
        save_json(sat_path, data)
        assert validate_round(load_json(r2 / "ROUND.json"), r2)["FIG"], breakage
    save_json(sat_path, good)
    assert run_cli("aggregate", str(spath))[0] == 0
    assert load_json(r2 / "SCORES.json")["figures"]["tab_1"]["score"] == 5
    assert "figures (FIG job)**: mean 4.5 (min 4, n=2), delta +0.0" in (spath / "PROGRESS.md").read_text(encoding="utf-8")
    print("OK round 2: satisfaction validation and aggregation for FIG")
    assert run_cli("retest", str(spath))[0] == 0
    assert any(j["job_id"] == "FIG" for j in load_json(round_dir(spath, 3) / "ROUND.json")["jobs"])
    print("OK retest keeps the FIG job")


def check_slim_prompt(prompt: str, rpath: Path) -> None:
    """FIG prompt: no generic schema, sources or off-topic categories; line anchors only when the paper has them."""
    assert "### review.json format" not in prompt and "rules the example below does not show" in prompt
    assert "## Sources" not in prompt and "p = 0.82" not in prompt, "study statistics live in 01_sources"
    categories = next(line for line in prompt.splitlines() if line.startswith("Weakness categories"))
    assert "figures (" in categories and "visual_results (" in categories and "baselines (" not in categories
    assert "defects illegible_text" not in prompt, "the defect ids are listed by the rubric, not again"
    assert "no margin line numbers: cite page and figure panel" in prompt and "with `L###`" not in prompt
    assert "Judge unmeasured plot text on the page image" in prompt
    rnd = load_json(rpath / "ROUND.json")
    session = load_json(rpath.parent / "SESSION.json")
    job = next(j for j in rnd["jobs"] if j["job_id"] == "FIG")
    rnd["paper"]["line_numbers"] = True
    text = figure_initial_prompt(session, rnd, job, session["instruments"]["personas"], rpath)
    assert "(with `L###` line anchors)" in text and "no margin line numbers" not in text


def snapshot_missing_fig_2(pdf: Path, dest: Path, supp: Optional[Path] = None, tex: Optional[Path] = None) -> dict:
    """Snapshot whose text has a 'Figure 2.' caption that the figure locator does not find."""
    meta = snapshot_with_figures(pdf, dest, supp, tex)
    caps = load_json(dest / "captions.json")
    save_json(dest / "captions.json", caps + [{"doc": "main", "page": 1, "anchor": "",
                                               "text": "Figure 2. A figure the locator missed."}])
    meta["figures"] = snapshot_figures(dest, dest / "main.pdf", extract_lines(dest / "main.pdf"))
    return meta


def check_placeholder_figure(tmpd: Path) -> None:
    """A caption found in the text but not located is listed, flagged and required in figure_scores."""
    with patch.object(hx, "snapshot_paper", snapshot_missing_fig_2):
        assert run_cli("new", "--paper", str(tmpd / "v1.pdf"), "--name", "missed", "--reviewers", "R07",
                       "--figures")[0] == 0
    spath = next(p for p in hx.SESSIONS_DIR.iterdir() if p.name.endswith("_missed"))
    r1 = round_dir(spath, 1)
    rnd = load_json(r1 / "ROUND.json")
    assert rnd["paper"]["figures"]["not_located"] == ["fig_2"], rnd["paper"]["figures"]
    prompt = (r1 / "prompts" / "initial" / "FIG.md").read_text(encoding="utf-8")
    assert "exactly these main-paper ids: fig_1, tab_1, fig_2." in prompt
    line = next(x for x in prompt.splitlines() if "`fig_2` (Fig. 2, p.1)" in x)
    assert "NOT LOCATED, use page image" in line and "not_located: caption found in text" in line, line
    assert "| fig_2 | Fig. 2 | 1 | pages/main_p01.png |" in (r1 / "snapshot" / "FIGURES.md").read_text(encoding="utf-8")
    write_outputs(r1)
    assert validate_round(rnd, r1)["FIG"] == []
    path = review_dir(r1, {"job_id": "FIG"}) / "review.json"
    data = load_json(path)
    data["figure_scores"].pop("fig_2")
    save_json(path, data)
    assert any("lacks main-paper ids ['fig_2']" in e for e in validate_round(rnd, r1)["FIG"])
    assert "kind=figures figures=3 main/3 total" in run_cli("status", str(spath))[1]
    print("OK caption found in the text but not located: placeholder listed, flagged and required")


def check_other_venue_and_defaults(tmpd: Path) -> None:
    """ICML (careful) with --figures gets F01; without --figures no FIG job; F01 is not a reviewer."""
    pdf = tmpd / "v1.pdf"
    assert run_cli("new", "--paper", str(pdf), "--name", "icmlfig", "--venue", "icml", "--figures")[0] == 0
    spath = next(p for p in hx.SESSIONS_DIR.iterdir() if p.name.endswith("_icmlfig"))
    rp = round_dir(spath, 1)
    rnd = load_json(rp / "ROUND.json")
    fig = next(j for j in rnd["jobs"] if j["job_id"] == "FIG")
    assert fig["view"] == "main" and fig.get("careful") is True and fig["reviewer"] == "F01"
    assert "F01" in load_json(spath / "SESSION.json")["instruments"]["personas"]
    assert all(j["reviewer"].startswith("M") for j in rnd["jobs"] if j["job_id"] != "FIG")
    assert "evidence_audit" in (rp / "prompts" / "initial" / "FIG.md").read_text(encoding="utf-8")
    write_outputs(rp)
    assert all(not errs for errs in validate_round(rnd, rp).values()), validate_round(rnd, rp)
    assert run_cli("new", "--paper", str(pdf), "--name", "plain", "--reviewers", "R03")[0] == 0
    plain = next(p for p in hx.SESSIONS_DIR.iterdir() if p.name.endswith("_plain"))
    assert not load_json(plain / "SESSION.json")["figures"]
    assert [j["job_id"] for j in load_json(round_dir(plain, 1) / "ROUND.json")["jobs"]] == ["R03"]
    for bad in (("--reviewers", "F01"), ("--heldout", "F01")):
        try:
            run_cli("new", "--paper", str(pdf), "--name", "bad", *bad)
        except ValueError:
            continue
        raise AssertionError(f"{bad} must be rejected")
    key = "02_protocol/figure_review_rules.md"
    assert optional_instrument({"instruments": {"texts": {}}}, PROTOCOL_DIR / "figure_review_rules.md") \
        == FALLBACK_TEXTS[key]
    assert key in load_json(spath / "SESSION.json")["instruments"]["texts"], "rules text must be frozen"
    print("OK other venue (ICML careful) with --figures; default sessions have no FIG; F01 cannot review")


def check_panels() -> None:
    """Realistic draws and the gauntlet never contain F01."""
    personas = load_personas()
    assert personas["F01"]["role"] == "figure_reviewer"
    for seed in range(300):
        for panel in ("realistic", "realistic4"):
            assert "F01" not in draw_panel(panel, seed, personas), (panel, seed)
    gauntlet = draw_panel("gauntlet", 0, personas)
    assert "F01" not in gauntlet and len(gauntlet) == 16 and all(r.startswith("R") for r in gauntlet)
    for venue in ("iclr", "icml", "neurips"):
        assert "F01" not in draw_panel("gauntlet", 0, load_personas(venue), venue)
    print("OK panels: realistic draws (300 seeds) and gauntlet never contain F01")


def main() -> int:
    logging.basicConfig(level=logging.ERROR)
    with tempfile.TemporaryDirectory() as tmp:
        tmpd = Path(tmp)
        with patch.object(hx, "SESSIONS_DIR", tmpd / "sessions"), \
                patch.object(hx, "snapshot_paper", snapshot_with_figures):
            check_panels()
            check_cvpr_session(tmpd)
            check_placeholder_figure(tmpd)
            check_other_venue_and_defaults(tmpd)
    print("FIGURE JOB TEST PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
