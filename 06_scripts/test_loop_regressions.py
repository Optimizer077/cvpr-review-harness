#!/usr/bin/env python3
"""Regression tests for the review / answer / revise loop (no LLM calls).

Each test reproduces one defect found in a bug hunt: the writer brief pointing at held-out scores,
answer blocks leaking between reviewers, writer answers lost after a retest, partial folders left by
a failed `new` or `round`, rounds started on unvalidated reviews, fixcheck/pairwise comparing with a
retest or satisfy round, held-out reviews repeated on an unchanged PDF, silent `--sections` typos
and incomplete CLI usage. The figure features (FIG job, figure crops, figure pairwise) run along.
Exit code 0 = pass.
"""
from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Optional
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import hx  # noqa: E402
from hxlib.common import list_rounds, load_json, review_dir, round_dir, save_json  # noqa: E402
from hxlib.dialogue import parse_response  # noqa: E402
from smoke_test import make_pdf, write_reviews, write_satisfaction  # noqa: E402
from test_figure_job import make_figure_pdf, write_outputs  # noqa: E402

_ANSWER = "Answer to the reviewer (cite lines/tables/figures of the new draft):"


class LoopRegressionTests(unittest.TestCase):
    """CLI-level checks in a temporary sessions folder."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.pdfs: dict[int, Path] = {}
        for variant in (1, 2, 3):  # variants 2 and 3 differ in text only; their figure is identical
            self.pdfs[variant] = self.root / f"v{variant}.pdf"
            make_pdf(self.pdfs[variant], variant)
        self.patcher = patch.object(hx, "SESSIONS_DIR", self.root / "sessions")
        self.patcher.start()

    def tearDown(self) -> None:
        self.patcher.stop()
        self.tmp.cleanup()

    def cli(self, *args: object) -> tuple[int, str]:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = hx.main([str(a) for a in args])
        return code, buf.getvalue()

    def new(self, name: str, *extra: str, pdf: Optional[Path] = None) -> Path:
        self.assertEqual(self.cli("new", "--paper", pdf or self.pdfs[1], "--name", name, *extra)[0], 0)
        return next(p for p in hx.SESSIONS_DIR.iterdir() if p.name.endswith("_" + name))

    def sessions(self) -> list[Path]:
        return sorted(hx.SESSIONS_DIR.iterdir()) if hx.SESSIONS_DIR.exists() else []

    def figure_pdf(self, variant: int) -> Path:
        path = self.root / f"fig_v{variant}.pdf"
        if not path.exists():
            make_figure_pdf(path, variant)
        return path

    @staticmethod
    def answer(rpath: Path, text: str = "See L012, which now states the condition.") -> None:
        """Fill every block of the round's answer sheet with a contest decision and `text`."""
        sheet = rpath / "writer" / "RESPONSE.md"
        sheet.write_text(sheet.read_text(encoding="utf-8").replace("Decision:", "Decision: contest")
                         .replace(_ANSWER, f"{_ANSWER} {text}"), encoding="utf-8")

    @staticmethod
    def set_weakness(rpath: Path, job_id: str, text: str) -> None:
        path = review_dir(rpath, {"job_id": job_id}) / "review.json"
        data = load_json(path)
        data["weaknesses"][0]["text"] = text
        save_json(path, data)

    def test_writer_brief_never_points_at_heldout_scores(self) -> None:
        """Bug 1: SCORES.md and PROGRESS.md carry held-out rows; the brief may name them only as off limits."""
        spath = self.new("brief", "--reviewers", "R07,R09", "--heldout", "R11", "--figures",
                         pdf=self.figure_pdf(1))
        r1 = round_dir(spath, 1)
        write_outputs(r1)
        self.assertEqual(self.cli("aggregate", spath)[0], 0)
        self.assertIn("HR11", (r1 / "SCORES.md").read_text(encoding="utf-8"))
        feedback = (r1 / "FEEDBACK.md").read_text(encoding="utf-8")
        self.assertNotIn("HR11", feedback)
        self.assertIn("## Figure scores (FIG job", feedback)
        self.assertEqual(self.cli("stage", spath, "writer")[0], 0)
        brief = (r1 / "prompts" / "writer" / "WRITER.md").read_text(encoding="utf-8")
        named = [line for line in brief.splitlines()
                 if any(n in line for n in ("SCORES.md", "SCORES.json", "PROGRESS.md", "heldout"))]
        self.assertTrue(named)
        for line in named:
            self.assertTrue(line.startswith("- Never open"), line)
        for name in ("SCORES.md", "SCORES.json", "PROGRESS.md", str(r1 / "heldout")):
            self.assertIn(name, named[0])

    def test_answer_blocks_stay_with_their_reviewer(self) -> None:
        """Bug 2: annotated headings, other headings and code fences do not merge answer blocks."""
        sheet = self.root / "RESPONSE.md"
        sheet.write_text("\n".join([
            "# Author response", "", "### R02:W1", "Decision: fix_text", "R02 answer", "```", "",
            "### R03:W1 (novelty)", "Decision: contest", "R03 answer", "```", "# a code comment", "```", "",
            "### R03:W12", "W12 answer", "", "### Notes for the editor", "loose note", "",
            "### R09:W1", "R09 answer", "```", "## Summary of all changes", "R02 rewritten; R03 contested.",
        ]) + "\n", encoding="utf-8")
        with self.assertLogs("hxlib.dialogue", level="WARNING") as logs:
            blocks = parse_response(sheet, {"R02:W1", "R03:W1", "R09:W1"})
        self.assertEqual(set(blocks), {"R02:W1", "R03:W1", "R03:W12", "R09:W1"})
        self.assertEqual(blocks["R02:W1"], "Decision: fix_text\nR02 answer\n```")  # an open fence stops at ###
        self.assertEqual(blocks["R03:W1"], "Decision: contest\nR03 answer\n```\n# a code comment\n```")
        self.assertEqual(blocks["R03:W12"], "W12 answer")
        self.assertEqual(blocks["R09:W1"], "R09 answer\n```")  # an open fence does not hide the summary heading
        warned = "\n".join(logs.output)
        self.assertIn("Notes for the editor", warned)
        self.assertIn("R03:W12", warned)

        spath = self.new("blocks", "--reviewers", "R02,R03,R09")
        r1 = round_dir(spath, 1)
        write_reviews(r1, 1)
        for jid in ("R02", "R03", "R09"):
            self.set_weakness(r1, jid, f"SECRET complaint of {jid}")
        self.cli("aggregate", spath)
        self.cli("stage", spath, "writer")
        self.answer(r1)
        response = r1 / "writer" / "RESPONSE.md"
        text = response.read_text(encoding="utf-8").replace("### R03:W1", "### R03:W1 (novelty)")
        response.write_text(text + "\n## Summary of all changes\n- R03 contested.\n", encoding="utf-8")
        self.assertEqual(self.cli("round", spath, "--paper", self.pdfs[2])[0], 0)
        for jid in ("R02", "R03", "R09"):
            seen = (round_dir(spath, 2) / "satisfaction" / jid / "AUTHOR_RESPONSE.md").read_text(encoding="utf-8")
            self.assertNotIn("did not answer", seen, jid)
            self.assertNotIn("Summary of all changes", seen, jid)
            foreign = [o for o in ("R02", "R03", "R09") if o != jid and f"SECRET complaint of {o}" in seen]
            self.assertEqual(foreign, [], jid)

    def test_writer_answers_dialogue_round_after_retest(self) -> None:
        """Bug 3: after a retest the writer stage targets the last review round; a retest round is refused."""
        spath = self.new("retest", "--reviewers", "R02,R03")
        r1, r2 = round_dir(spath, 1), round_dir(spath, 2)
        write_reviews(r1, 1)
        self.cli("aggregate", spath)
        self.assertEqual(self.cli("retest", spath)[0], 0)
        write_reviews(r2, 2)
        self.cli("aggregate", spath)
        self.assertEqual(self.cli("stage", spath, "writer")[0], 0)
        self.assertTrue((r1 / "writer" / "RESPONSE.md").exists())
        self.assertFalse((r2 / "writer").exists())
        with self.assertRaises(ValueError) as err:
            self.cli("stage", spath, "writer", "--round", "2")
        self.assertIn("retest", str(err.exception))
        self.assertFalse((r2 / "prompts" / "writer").exists())
        self.answer(r1, "See L012, which states the condition.")
        self.assertEqual(self.cli("round", spath, "--paper", self.pdfs[2])[0], 0)
        seen = (round_dir(spath, 3) / "satisfaction" / "R03" / "AUTHOR_RESPONSE.md").read_text(encoding="utf-8")
        self.assertIn("See L012, which states the condition.", seen)
        self.assertNotIn("did not answer", seen)

    def test_failed_new_and_round_leave_no_partial_folders(self) -> None:
        """Bug 4: missing inputs fail before any folder exists; later failures remove the partial folder."""
        missing = self.root / "typo_supp.pdf"
        with self.assertRaises(FileNotFoundError):
            self.cli("new", "--paper", self.pdfs[1], "--supp", missing, "--name", "orphan")
        with self.assertRaises(FileNotFoundError):
            self.cli("new", "--paper", self.pdfs[1], "--tex", self.root / "no_such_dir", "--name", "orphan")
        with patch("hx.write_initial_prompts", side_effect=RuntimeError("prompt writing failed")):
            with self.assertRaises(RuntimeError):
                self.cli("new", "--paper", self.pdfs[1], "--name", "orphan")
        self.assertEqual(self.sessions(), [])
        spath = self.new("orphan", "--reviewers", "R02")
        write_reviews(round_dir(spath, 1), 1)
        with self.assertRaises(FileNotFoundError):
            self.cli("round", spath, "--paper", self.pdfs[2], "--supp", missing)
        with patch("hx.write_initial_prompts", side_effect=RuntimeError("prompt writing failed")):
            with self.assertRaises(RuntimeError):
                self.cli("round", spath, "--paper", self.pdfs[2])
        self.assertEqual(list_rounds(spath), [1])
        self.assertEqual(load_json(spath / "SESSION.json")["rounds"], [1])
        for command in ("status", "validate", "aggregate"):
            self.assertEqual(self.cli(command, spath)[0], 0, command)
        self.assertEqual(self.cli("round", spath, "--paper", self.pdfs[2])[0], 0)
        self.assertEqual(list_rounds(spath), [1, 2])

    def test_round_and_writer_refuse_unvalidated_previous_round(self) -> None:
        """Bug 5: pending or malformed reviews block `round` and `stage writer` with the job list."""
        spath = self.new("gate", "--reviewers", "R02,R03")
        r1 = round_dir(spath, 1)
        write_reviews(r1, 1)
        for name in ("review.md", "review.json", "debrief.md"):
            (review_dir(r1, {"job_id": "R03"}) / name).unlink()
        code, out = self.cli("stage", spath, "writer")
        self.assertEqual(code, 1)
        self.assertIn("R03", out)
        self.assertFalse((r1 / "writer").exists())
        code, out = self.cli("round", spath, "--paper", self.pdfs[2])
        self.assertEqual(code, 1)
        self.assertIn("R03", out)
        self.assertEqual(list_rounds(spath), [1])
        write_reviews(r1, 1)
        (review_dir(r1, {"job_id": "R02"}) / "review.json").write_text(
            '{"job_id": "R02", "reviewer_id": "R02", "round": 1, "stage": "initial", ', encoding="utf-8")
        code, out = self.cli("round", spath, "--paper", self.pdfs[2])
        self.assertEqual(code, 1)
        self.assertIn("R02", out)
        write_reviews(r1, 1)
        self.assertEqual(self.cli("stage", spath, "writer")[0], 0)
        self.assertEqual(self.cli("round", spath, "--paper", self.pdfs[2])[0], 0)

    def test_fixcheck_uses_open_points_of_last_dialogue_round(self) -> None:
        """Bug 6a: in the dialogue loop fixcheck lists the open points the writer answered."""
        spath = self.new("fixd", "--reviewers", "R02,R03")
        r1, r2, r3 = (round_dir(spath, n) for n in (1, 2, 3))
        write_reviews(r1, 1)
        self.cli("aggregate", spath)
        self.cli("stage", spath, "writer")
        self.answer(r1)
        self.assertEqual(self.cli("round", spath, "--paper", self.pdfs[2])[0], 0)
        write_satisfaction(r2)
        self.assertEqual(self.cli("aggregate", spath)[0], 0)
        self.cli("stage", spath, "writer")
        self.answer(r2)
        self.assertEqual(self.cli("round", spath, "--paper", self.pdfs[3])[0], 0)
        self.assertEqual(self.cli("stage", spath, "fixcheck")[0], 0)
        items = load_json(r3 / "fixcheck" / "previous_weaknesses.json")
        open_points = load_json(r2 / "FEEDBACK.json")
        self.assertTrue(items)
        self.assertEqual([i["id"] for i in items], [i["id"] for i in open_points])
        self.assertIn("round 03 vs round 02", (r3 / "prompts" / "fixcheck" / "FIXCHECK.md").read_text(encoding="utf-8"))

    def test_fixcheck_and_pairwise_skip_retest_rounds(self) -> None:
        """Bug 6b: with a retest of an older draft in between, compare with the last review round."""
        spath = self.new("fixf", "--reviewers", "R02", "--loop", "fresh")
        r1, r2, r3, r4 = (round_dir(spath, n) for n in (1, 2, 3, 4))
        write_reviews(r1, 1)
        self.assertEqual(self.cli("round", spath, "--paper", self.pdfs[2])[0], 0)
        write_reviews(r2, 2)
        self.set_weakness(r2, "R02", "ROUND-2 weakness")
        self.assertEqual(self.cli("retest", spath, "--of", "1")[0], 0)
        write_reviews(r3, 3)
        self.set_weakness(r3, "R02", "RETEST-ONLY weakness")
        self.assertEqual(self.cli("round", spath, "--paper", self.pdfs[3])[0], 0)
        for stage in ("fixcheck", "pairwise"):
            self.assertEqual(self.cli("stage", spath, stage)[0], 0, stage)
            with self.assertRaises(ValueError):
                self.cli("stage", spath, stage, "--round", "3")
        self.assertEqual([i["text"] for i in load_json(r4 / "fixcheck" / "previous_weaknesses.json")],
                         ["ROUND-2 weakness"])
        key = load_json(r4 / "pairwise" / "_key" / "KEY.json")
        old_side = "A" if key["method"]["A"] == "old" else "B"
        self.assertIn("variant 2", (r4 / "pairwise" / f"{old_side}_method.txt").read_text(encoding="utf-8"))
        self.assertNotIn("figure:fig_1", key, "drafts 2 and 3 share the figure; only the retest's draft 1 differs")
        self.assertEqual(self.cli("stage", spath, "pairwise", "--round", "2")[0], 0)
        self.assertIn("figure:fig_1", load_json(r2 / "pairwise" / "_key" / "KEY.json"))

    def test_unchanged_pdf_with_new_answers_skips_heldout(self) -> None:
        """Bug 7: answers alone start an answer-check round without repeating held-out reviews."""
        spath = self.new("same", "--reviewers", "R07", "--heldout", "R11", "--figures", pdf=self.figure_pdf(1))
        r1, r2 = round_dir(spath, 1), round_dir(spath, 2)
        write_outputs(r1)
        self.assertEqual(self.cli("aggregate", spath)[0], 0)
        self.cli("stage", spath, "writer")
        self.answer(r1)
        code, out = self.cli("round", spath, "--paper", self.figure_pdf(1))
        self.assertEqual(code, 0)
        self.assertIn("held-out", out)
        rnd2 = load_json(r2 / "ROUND.json")
        self.assertEqual({j["job_id"]: j.get("stage") for j in rnd2["jobs"]}, {"R07": "satisfy", "FIG": "satisfy"})
        self.assertIn("heldout_skipped", rnd2)
        self.assertTrue((r2 / "prompts" / "satisfy" / "FIG.md").exists())
        self.assertEqual(list((r2 / "prompts" / "initial").glob("*.md")), [])
        write_outputs(r2)
        self.assertEqual(self.cli("aggregate", spath)[0], 0)
        self.assertEqual(self.cli("round", spath, "--paper", self.figure_pdf(2))[0], 0)
        jobs3 = {j["job_id"]: j for j in load_json(round_dir(spath, 3) / "ROUND.json")["jobs"]}
        self.assertEqual(jobs3["HR11"].get("stage", "initial"), "initial")

    def test_unknown_section_keys_are_rejected(self) -> None:
        """Bug 8: a `--sections` typo, or sections the paper lacks, fail instead of creating 0 jobs."""
        with self.assertRaises(ValueError) as err:
            self.cli("new", "--paper", self.pdfs[1], "--name", "typo", "--mode", "sections",
                     "--sections", "experimnts")
        self.assertIn("experimnts", str(err.exception))
        self.assertIn("experiments", str(err.exception))
        with self.assertRaises(ValueError):
            self.cli("new", "--paper", self.pdfs[1], "--name", "typo", "--mode", "sections", "--sections", "theory")
        self.assertEqual(self.sessions(), [])
        spath = self.new("typo", "--mode", "sections", "--sections", "experiments,method")
        jobs = load_json(round_dir(spath, 1) / "ROUND.json")["jobs"]
        self.assertTrue(jobs)
        self.assertTrue(all(set(j["sections"]) <= {"experiments", "method"} for j in jobs))

    def test_usage_lists_every_command_option(self) -> None:
        """Bug 9: the module usage and `new --help` describe every command and the venue defaults."""
        for needle in ("personas [--venue V]", "--venue V", "--figures", "aggregate SESSION [--round N | --all]",
                       "stage SESSION {fixcheck,pairwise,writer}"):
            self.assertIn(needle, hx.__doc__)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), self.assertRaises(SystemExit):
            hx.main(["new", "--help"])
        options = buf.getvalue().rsplit("--panel PANEL", 1)[1]  # the options list, not the usage line
        panel_help = " ".join(options.split("--reviewers", 1)[0].split())
        for needle in ("venue", "realistic", "balanced"):
            self.assertIn(needle, panel_help)


if __name__ == "__main__":
    unittest.main()
