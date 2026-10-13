#!/usr/bin/env python3
"""Reviewer prompt tests (no LLM calls).

Checks the initial reviewer prompts: the Targets box with the persona numbers, the session's
prior-work cutoff in the CVPR form, the location instruction for PDFs with and without margin line
numbers, the review.md formatting and decisive rules, careful-mode targets, the card fallback for
sessions frozen without `words`, and that the R09 prompt is smaller than before the 2026-10-14 fixes.
"""
from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import hx  # noqa: E402
from hxlib.common import load_json, round_dir  # noqa: E402
from hxlib.panel import load_personas  # noqa: E402
from hxlib.prompts import CAREFUL_TARGETS, has_line_numbers, persona_targets  # noqa: E402
from smoke_test import draw_figure, make_pdf  # noqa: E402

# Size of the R09 prompt for the smoke-test PDF (characters, session folder replaced by "<S>"),
# measured at commit 2b999fd, before the 2026-10-14 reviewer-prompt fixes.
OLD_R09_CHARS = 24337
TARGETS = {"R03": ("450-750 words", "at most 6 points"), "R08": ("300-500 words", "at most 5 points"),
           "R09": ("150-300 words", "at most 3 points")}
NO_LINES = "This PDF has no line numbers."
LINES = "Cite the line numbers printed in the PDF margin as `L###`"
CUTOFF = "2023-03-01"


def make_unnumbered_pdf(path: Path) -> None:
    """A camera-ready-like paper: the smoke PDF's headings and figure, no margin line numbers."""
    import fitz

    doc = fitz.open()
    lines = ["Toy Title For A Prompt Test", "Abstract",
             "We propose a toy method. It improves a toy metric by 1 point."]
    for heading in ("1. Introduction", "2. Related Work", "3. Method", "4. Experiments", "5. Conclusion"):
        lines += [heading] + [f"Body text of {heading} sentence {k}." for k in range(6)]
    lines += ["References", "[1] A. Author. A paper. CVPR 2024."]
    page, y = doc.new_page(), 40
    for text in lines:
        if y > 780:
            page, y = doc.new_page(), 40
        page.insert_text((60, y), text, fontsize=9)
        y += 14
    draw_figure(doc.new_page(), 60, 1)
    doc.save(path)


class PromptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        cls.patcher = patch.object(hx, "SESSIONS_DIR", root / "sessions")
        cls.patcher.start()
        numbered, unnumbered = root / "numbered.pdf", root / "unnumbered.pdf"
        make_pdf(numbered, 1)
        make_unnumbered_pdf(unnumbered)
        cls.numbered = cls.create("numbered", numbered, "--reviewers", "R03,R08,R09")
        cls.unnumbered = cls.create("unnumbered", unnumbered, "--reviewers", "R09", "--cutoff", CUTOFF)
        cls.careful = cls.create("careful", numbered, "--reading", "careful", "--reviewers", "R09")

    @classmethod
    def tearDownClass(cls):
        cls.patcher.stop()
        cls.tmp.cleanup()

    @classmethod
    def create(cls, name: str, pdf: Path, *extra: str) -> Path:
        with contextlib.redirect_stdout(io.StringIO()):
            assert hx.main(["new", "--paper", str(pdf), "--name", name, *extra]) == 0
        return next(p for p in hx.SESSIONS_DIR.iterdir() if p.name.endswith("_" + name))

    @staticmethod
    def prompt(spath: Path, jid: str) -> str:
        return (round_dir(spath, 1) / "prompts" / "initial" / f"{jid}.md").read_text(encoding="utf-8")

    def test_targets_box_has_persona_numbers(self):
        for jid, (words, points) in TARGETS.items():
            text = self.prompt(self.numbered, jid)
            box = text[text.index("## 0. Targets"):text.index("## 1. Who you are")]
            self.assertIn(f"`review.md`: {words}", box, jid)
            self.assertIn(points, box, jid)
            self.assertIn("at most 2 of them decisive", box, jid)
            self.assertIn("`debrief.md`: at most 350 words", box, jid)
            self.assertLess(text.index("## 0. Targets"), text.index("## 2. Rules for every reviewer"))

    def test_reading_block_before_form_and_rubric(self):
        text = self.prompt(self.numbered, "R09")
        order = [text.index(h) for h in ("## 2. Rules for every reviewer", "## 3. What you read",
                                         "## 4. Review form", "## 5. Sections you score",
                                         "## 6. What you write")]
        self.assertEqual(order, sorted(order))
        self.assertNotIn("Venue policy", text, "persona mode, general contribution: no venue block")
        self.assertNotIn("01_sources", text)
        self.assertNotIn("When the authors answer you", text, "answer-stage card section is dropped")
        self.assertIn("Use FIGURES.md measurements only for figures you opened", text)

    def test_cutoff_from_session(self):
        text = self.prompt(self.unnumbered, "R09")
        self.assertNotIn("2026-09-15", text)
        self.assertIn(f"papers that appeared online after {CUTOFF} are contemporaneous", text)
        self.assertNotIn("{cutoff}", text)
        self.assertNotIn("{venue}", text)
        self.assertIn("Prior work for CVPR 2027", text)

    def test_location_instruction_follows_line_numbers(self):
        numbered, unnumbered = self.prompt(self.numbered, "R09"), self.prompt(self.unnumbered, "R09")
        self.assertIn(LINES, numbered)
        self.assertNotIn(NO_LINES, numbered)
        self.assertIn(NO_LINES, unnumbered)
        self.assertIn("Never cite line numbers of the .txt files", unnumbered)
        self.assertNotIn(LINES, unnumbered)
        for spath, expected in ((self.numbered, True), (self.unnumbered, False)):
            rp = round_dir(spath, 1)
            rnd = load_json(rp / "ROUND.json")
            self.assertEqual(has_line_numbers(rnd, rp / "snapshot"), expected, spath.name)
            flagged = dict(rnd, paper=dict(rnd["paper"], line_numbers=not expected))
            self.assertEqual(has_line_numbers(flagged, rp / "snapshot"), not expected, "snapshot meta wins")

    def test_review_md_and_decisive_rules(self):
        for spath, jid in ((self.numbered, "R03"), (self.unnumbered, "R09"), (self.careful, "R09")):
            text = self.prompt(spath, jid)
            self.assertIn("Under Weaknesses, write numbered plain paragraphs", text, jid)
            self.assertIn("no weakness ids, no JSON field names", text, jid)
            self.assertIn("in order (point n = Wn)", text, jid)
            self.assertIn("Decisive test:", text, jid)
            self.assertIn("no writing-only change would satisfy you", text, jid)
            self.assertIn("is not decisive alone", text, jid)

    def test_leniency_is_a_tie_break(self):
        r03, r08, r09 = (self.prompt(self.numbered, j) for j in ("R03", "R08", "R09"))
        self.assertIn("When torn between two adjacent levels, choose the lower one.", r03)
        self.assertIn("When torn between two adjacent levels, choose the higher one.", r08)
        self.assertIn("you rate like a typical calibrated CVPR reviewer", r09)
        for text in (r03, r08, r09):
            self.assertNotIn("level(s)", text)
            self.assertNotIn("Keep this offset", text)

    def test_careful_targets_and_card_fallback(self):
        text = self.prompt(self.careful, "R09")
        self.assertIn(f"`review.md`: {CAREFUL_TARGETS[0][0]}-{CAREFUL_TARGETS[0][1]} words", text)
        self.assertIn("Upper limits for this careful review", text)
        session = load_json(self.numbered / "SESSION.json")
        personas = load_personas()
        careful_session = load_json(self.careful / "SESSION.json")
        lens = {k: v for k, v in personas["I01"].items() if k not in ("words", "max_weaknesses")}
        self.assertEqual(persona_targets(careful_session, lens), CAREFUL_TARGETS, "lens card states no length")
        self.assertEqual(persona_targets(careful_session, personas["R03"]), CAREFUL_TARGETS)
        for pid, expected in (("R09", ([150, 300], 3)), ("R03", ([450, 750], None)), ("F01", ([300, 600], 8))):
            bare = {k: v for k, v in personas[pid].items() if k not in ("words", "max_weaknesses")}
            self.assertEqual(persona_targets(session, bare), expected, pid)
            self.assertEqual(persona_targets(session, personas[pid]),
                             (personas[pid]["words"], personas[pid]["max_weaknesses"]), pid)
        for pid, persona in personas.items():
            self.assertTrue(isinstance(persona.get("words"), list) and len(persona["words"]) == 2, pid)
            self.assertLess(persona["words"][0], persona["words"][1], pid)
            self.assertIsInstance(persona.get("max_weaknesses"), int, pid)

    def test_prompt_smaller_than_before(self):
        text = self.prompt(self.numbered, "R09").replace(str(self.numbered), "<S>")
        self.assertLess(len(text), OLD_R09_CHARS)


if __name__ == "__main__":
    unittest.main()
