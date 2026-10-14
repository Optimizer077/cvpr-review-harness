#!/usr/bin/env python3
"""Tests for the revision coach (`hx.py stage <session> coach`, hxlib/coach.py). No LLM calls.

- `stage coach` refuses an unvalidated round and a retest round, builds FEEDBACK.json when
  `aggregate` has not run, writes prompts/coach/COACH.md and prints the launch line.
- The prompt lists the files the coach may read and one never-open line, and names no held-out
  folder or id; in an answer-check round it lists this round's reply and the thread's review.
- A valid plan validates; missing coverage, duplicate coverage, a held-out id, bad enums, an empty
  proposed_text of a writing item, bad priorities, an unknown section, wrong heading order and a
  missing closing line each fail.
- The writer brief lists REVISION_PLAN.md first when the plan exists; `validate` shows COACH.
Run: python 06_scripts/test_coach.py
"""
from __future__ import annotations

import contextlib
import copy
import io
import logging
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Callable, Optional
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import hx  # noqa: E402
from hxlib.coach import (FALLBACK_TEXTS, FINAL_LINE, PLAN_HEADINGS, check_revision_plan, coach_text,  # noqa: E402
                         open_ids, plan_paths, strength_ids)
from hxlib.common import PROTOCOL_DIR, load_json, review_dir, round_dir, save_json  # noqa: E402
from smoke_test import make_pdf, write_reviews, write_satisfaction  # noqa: E402

_ANSWER = "Answer to the reviewer (cite lines/tables/figures of the new draft):"


def plan_markdown(number: int, headings: tuple[str, ...] = PLAN_HEADINGS, closing: str = FINAL_LINE) -> str:
    """A REVISION_PLAN.md with the title, the given headings and the closing line."""
    lines = [f"# Revision plan - Toy Title For A Smoke Test - round {number:02d}", ""]
    for heading in headings:
        lines += [f"## {heading}", "Toy plan text for this part, specific and constructive.", ""]
    return "\n".join(lines + [closing]) + "\n"


def make_plan(rpath: Path) -> dict:
    """A valid revision_plan.json: the first open points as writing items, the last one deferred."""
    rnd = load_json(rpath / "ROUND.json")
    points, strengths = open_ids(rnd, rpath), strength_ids(rnd, rpath)
    items = [{"id": f"P{k}", "priority": k, "from": [pid], "type": "writing", "section": "introduction",
              "location": "p.1, Sec. 1, para. 2", "problem": "Readers miss the condition.",
              "why_it_matters": "Skimming reviewers stop at the introduction.",
              "action": "State the condition in the first paragraph.",
              "proposed_text": "Our method assumes a toy condition, stated here.",
              "verification": "The condition appears on p.1.", "effort": "small"}
             for k, pid in enumerate(points[:-1], start=1)]
    return {"round": rnd["round"], "paper_sha256": rnd["paper"]["main_pdf_sha256"],
            "summary": "A toy method with a toy gain. Reviewers doubt the condition. Stating it is the main lever.",
            "strengths_to_keep": [{"text": "Clear figure.", "location": "Fig. 1", "from": strengths[:1]}],
            "items": items, "experiment_requests": [],
            "conflicts": [{"from": [points[0], strengths[-1]], "advice": "Keep the figure; move detail to the supplement."}],
            "deferred": [{"from": [points[-1]], "reason": "Generic request that fits any paper."}]}


def write_plan(rpath: Path, data: dict, markdown: Optional[str] = None) -> None:
    """Save the plan's two files (the markdown defaults to a valid one)."""
    md_path, json_path = plan_paths(rpath)
    save_json(json_path, data)
    md_path.write_text(markdown if markdown is not None else plan_markdown(data["round"]), encoding="utf-8")


class CoachTests(unittest.TestCase):
    """CLI-level checks in a temporary sessions folder."""

    tmp: tempfile.TemporaryDirectory
    root: Path
    pdfs: dict[int, Path]
    tex: Path
    patcher: Any

    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        cls.pdfs = {v: cls.root / f"v{v}.pdf" for v in (1, 2)}
        for variant, path in cls.pdfs.items():
            make_pdf(path, variant)
        cls.tex = cls.root / "latex"
        cls.tex.mkdir()
        (cls.tex / "main.tex").write_text("\\documentclass{article}\n", encoding="utf-8")
        cls.patcher = patch.object(hx, "SESSIONS_DIR", cls.root / "sessions")
        cls.patcher.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.patcher.stop()
        cls.tmp.cleanup()

    @staticmethod
    def cli(*args: object) -> tuple[int, str]:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = hx.main([str(a) for a in args])
        return code, buf.getvalue()

    def new(self, name: str, *extra: str) -> Path:
        code, out = self.cli("new", "--paper", self.pdfs[1], "--name", name, *extra)
        self.assertEqual(code, 0, out)
        return next(p for p in hx.SESSIONS_DIR.iterdir() if p.name.endswith("_" + name))

    def reviewed(self, name: str, *extra: str) -> tuple[Path, Path]:
        """A session whose round 1 has valid reviews and has been aggregated."""
        spath = self.new(name, *extra)
        r1 = round_dir(spath, 1)
        write_reviews(r1, 1)
        self.assertEqual(self.cli("aggregate", spath)[0], 0)
        return spath, r1

    def test_stage_coach_gates_and_builds_feedback(self) -> None:
        spath = self.new("gate", "--reviewers", "R03,R09")
        r1, r2 = round_dir(spath, 1), round_dir(spath, 2)
        write_reviews(r1, 1)
        for name in ("review.md", "review.json", "debrief.md"):
            (review_dir(r1, {"job_id": "R03"}) / name).unlink()
        code, out = self.cli("stage", spath, "coach")
        self.assertEqual(code, 1)
        self.assertIn("stage coach refused", out)
        self.assertIn("R03", out)
        self.assertFalse((r1 / "prompts" / "coach").exists())
        write_reviews(r1, 1)
        self.assertFalse((r1 / "FEEDBACK.json").exists())
        code, out = self.cli("stage", spath, "coach")
        self.assertEqual(code, 0, out)
        self.assertEqual([i["id"] for i in load_json(r1 / "FEEDBACK.json")], ["R03:W1", "R09:W1"])
        self.assertIn(f"[COACH] Read {r1 / 'prompts' / 'coach' / 'COACH.md'} and follow it exactly.", out)
        self.assertEqual(self.cli("retest", spath)[0], 0)
        write_reviews(r2, 2)
        with self.assertRaises(ValueError) as err:
            self.cli("stage", spath, "coach", "--round", "2")
        self.assertIn("retest", str(err.exception))
        self.assertEqual(self.cli("stage", spath, "coach")[0], 0)
        self.assertFalse((r2 / "prompts" / "coach").exists(), "the default round skips the retest")

    def test_prompt_lists_allowed_and_forbidden_files(self) -> None:
        spath, r1 = self.reviewed("prompt", "--reviewers", "R03,R09", "--heldout", "R11", "--tex", str(self.tex))
        self.assertTrue((r1 / "heldout" / "HR11").exists())
        self.assertEqual(self.cli("stage", spath, "coach")[0], 0)
        text = (r1 / "prompts" / "coach" / "COACH.md").read_text(encoding="utf-8")
        snap = r1 / "snapshot"
        md_path, json_path = plan_paths(r1)
        rnd = load_json(r1 / "ROUND.json")
        for path in (r1 / "FEEDBACK.md", r1 / "FEEDBACK.json", r1 / "reviews" / "R03", r1 / "reviews" / "R09",
                       spath / "AUTHOR_CONSTRAINTS.md", snap / "main.pdf", snap / "view_main.txt",
                       snap / "FIGURES.md", snap / "pages", md_path, json_path):
            self.assertIn(f"`{path}`", text)
        for needle in (rnd["paper"]["main_pdf_sha256"], "R03:W1, R09:W1", "R03:S1, R09:S1", "or `global`",
                       "## 1. Coach rules", "## 2. Writing playbook", "### revision_plan.json format", FINAL_LINE,
                       coach_text({}, PROTOCOL_DIR / "coach_rules.md").strip()[:60]):
            self.assertIn(needle, text)
        never = [line for line in text.splitlines() if line.startswith("- Never open")]
        self.assertEqual(len(never), 1)
        for needle in ("`heldout/`", "SCORES.md", "SCORES.json", "GROUNDING.md", str(spath / "PROGRESS.md"),
                       str(snap / "tex"), str(self.tex)):
            self.assertIn(needle, never[0])
        for line in text.splitlines():
            if any(n in line for n in ("SCORES", "PROGRESS.md", "heldout", "GROUNDING")):
                self.assertEqual(line, never[0])
        self.assertNotIn("HR11", text)
        self.assertNotIn(str(r1 / "heldout"), text)

    def test_answer_round_prompt_and_plan(self) -> None:
        spath, r1 = self.reviewed("answer", "--reviewers", "R03")
        r2 = round_dir(spath, 2)
        self.assertEqual(self.cli("stage", spath, "writer")[0], 0)
        sheet = r1 / "writer" / "RESPONSE.md"
        sheet.write_text(sheet.read_text(encoding="utf-8").replace("Decision:", "Decision: fix_text").replace(
            _ANSWER, f"{_ANSWER} See L012."), encoding="utf-8")
        self.assertEqual(self.cli("round", spath, "--paper", self.pdfs[2])[0], 0)
        write_satisfaction(r2)
        self.assertEqual(self.cli("aggregate", spath)[0], 0)
        self.assertEqual(self.cli("stage", spath, "coach")[0], 0)
        text = (r2 / "prompts" / "coach" / "COACH.md").read_text(encoding="utf-8")
        self.assertIn(f"`{r2 / 'satisfaction' / 'R03' / 'reply.md'}`", text)
        self.assertIn(f"`{r1 / 'reviews' / 'R03'}`", text, "the thread's review folder")
        self.assertIn("round 02", text)
        rnd2 = load_json(r2 / "ROUND.json")
        self.assertEqual(open_ids(rnd2, r2), ["R03:W99"])
        self.assertEqual(strength_ids(rnd2, r2), ["R03:S1"])
        write_plan(r2, make_plan(r2))  # R03:W99 deferred; the thread's strength R03:S1 is citable
        self.assertEqual(check_revision_plan(rnd2, r2), [])
        code, out = self.cli("validate", spath)
        self.assertEqual(code, 0, out)
        self.assertIn("COACH: OK", out)

    def test_plan_validation(self) -> None:
        spath, r1 = self.reviewed("plan", "--reviewers", "R03,R09", "--heldout", "R11")
        rnd = load_json(r1 / "ROUND.json")
        valid = make_plan(r1)
        write_plan(r1, valid)
        self.assertEqual(check_revision_plan(rnd, r1), [])
        figure = copy.deepcopy(valid)
        figure["items"][0].update(type="figure", proposed_text="", section="figures_tables")
        write_plan(r1, figure)
        self.assertEqual(check_revision_plan(rnd, r1), [], "a figure item may leave proposed_text empty")

        def item(**fields: object) -> Callable[[dict], None]:
            return lambda d: d["items"][0].update(fields)

        cases: list[tuple[str, Callable[[dict], None], str]] = [
            ("missing coverage", lambda d: d.update(deferred=[]), "open point R09:W1 is not covered"),
            ("duplicate coverage", lambda d: d["items"][0]["from"].append("R09:W1"),
             "open point R09:W1 is covered 2 times"),
            ("held-out id", lambda d: d["items"][0]["from"].append("HR11:W1"), "held-out id 'HR11:W1'"),
            ("unknown id", lambda d: d["strengths_to_keep"][0]["from"].append("R03:S9"), "unknown id 'R03:S9'"),
            ("bad type", item(type="rewrite"), "items P1.type 'rewrite'"),
            ("bad effort", item(effort="huge"), "items P1.effort 'huge'"),
            ("empty proposed_text", item(proposed_text=" "), "proposed_text is empty for a writing item"),
            ("unknown section", item(section="intro"), "items P1.section 'intro'"),
            ("bad priority", item(priority=2), "priorities [2] must be the integers 1..1"),
            ("empty text", item(problem=""), "items P1.problem is empty"),
            ("one-sided conflict", lambda d: d["conflicts"][0].update({"from": ["R03:W1"]}), "at least 2"),
            ("wrong paper", lambda d: d.update(paper_sha256="0" * 64), "paper_sha256"),
        ]
        for name, mutate, expected in cases:
            data = copy.deepcopy(valid)
            mutate(data)
            write_plan(r1, data)
            errors = check_revision_plan(rnd, r1)
            self.assertTrue(any(expected in e for e in errors), f"{name}: {errors}")
        swapped = (PLAN_HEADINGS[1], PLAN_HEADINGS[0]) + PLAN_HEADINGS[2:]
        for name, markdown, expected in (
                ("heading order", plan_markdown(1, swapped), "headings out of order: '## Keep these strengths' comes before"),
                ("missing heading", plan_markdown(1, PLAN_HEADINGS[:-1]), "lacks the heading '## Points not worth"),
                ("closing line", plan_markdown(1, closing="Good luck."), "must end with the line")):
            write_plan(r1, valid, markdown)
            errors = check_revision_plan(rnd, r1)
            self.assertTrue(any(expected in e for e in errors), f"{name}: {errors}")

    def test_writer_brief_and_validate_show_the_plan(self) -> None:
        spath, r1 = self.reviewed("brief", "--reviewers", "R03,R09")
        brief_path = r1 / "prompts" / "writer" / "WRITER.md"
        self.assertEqual(self.cli("stage", spath, "writer")[0], 0)
        self.assertNotIn("REVISION_PLAN.md", brief_path.read_text(encoding="utf-8"))
        code, out = self.cli("validate", spath)
        self.assertEqual(code, 0, out)
        self.assertNotIn("COACH", out, "no plan, no COACH entry")
        write_plan(r1, make_plan(r1))
        code, out = self.cli("validate", spath)
        self.assertEqual(code, 0, out)
        self.assertIn("COACH: OK", out)
        self.assertIn("round 1: 3/3 valid", out)
        self.assertEqual(self.cli("stage", spath, "writer")[0], 0)
        brief = brief_path.read_text(encoding="utf-8")
        first_input = brief.split("## Inputs\n\n", 1)[1].splitlines()[0]
        self.assertEqual(first_input, f"- First, the revision plan: `{plan_paths(r1)[0]}` - follow its priorities; "
                                      "RESPONSE.md still answers every point.")
        broken = make_plan(r1)
        broken["items"][0]["type"] = "rewrite"
        write_plan(r1, broken)
        code, out = self.cli("validate", spath)
        self.assertEqual(code, 1, out)
        self.assertIn("COACH: FAIL", out)
        self.assertIn("type 'rewrite'", out)

    def test_coach_text_sources(self) -> None:
        key = "02_protocol/coach_rules.md"
        frozen = {"instruments": {"texts": {key: "FROZEN RULES"}}}
        self.assertEqual(coach_text(frozen, PROTOCOL_DIR / "coach_rules.md"), "FROZEN RULES")
        with patch("hxlib.coach.Path.exists", return_value=False), self.assertLogs("hxlib.coach", "WARNING"):
            self.assertEqual(coach_text({"instruments": {"texts": {}}}, PROTOCOL_DIR / "coach_rules.md"),
                             FALLBACK_TEXTS[key])


if __name__ == "__main__":
    logging.basicConfig(level=logging.ERROR)
    unittest.main()
