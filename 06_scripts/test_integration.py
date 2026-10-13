#!/usr/bin/env python3
"""Integration tests of the anonymity gate, line-number meta, section mapping, validation warnings,
grounding report and answer-check prompt (no LLM calls). Exit code 0 = pass.

- An identified synthetic PDF (camera-ready watermark, author block, e-mail): `new` and `round`
  refuse it; with `--allow-identified` every initial and answer-check prompt (FIG included) carries
  the identified-copy line, SESSION.json records the flag, SCORES.md lists the anonymity flags.
- SCORES.md has the Grounding line right after the headline and GROUNDING.md exists; a grounding
  failure does not block aggregation.
- Null section criteria validate; long reviews, too many weaknesses and a review.md / review.json
  point-count mismatch are warnings, not failures; a fabricated quote is a grounding warning.
- Acknowledgements, funding and reproducibility statements are not scored; broader impact and
  ethics statements map to limitations.
- The answer-check prompt opens with the Targets box; a cp1252 RESPONSE.md parses; plural grant
  numbers ('Grants Nos.') are flagged.
Run: python 06_scripts/test_integration.py
"""
from __future__ import annotations

import contextlib
import io
import logging
import random
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import hx  # noqa: E402
from hxlib.aggregate import aggregate_round  # noqa: E402
from hxlib.anonymity import IDENTIFIED_LINE, scan_anonymity, scan_document  # noqa: E402
from hxlib.common import UNSCORED_SECTION, load_json, load_scales, review_dir, round_dir, save_json  # noqa: E402
from hxlib.dialogue import parse_response  # noqa: E402
from hxlib.figure_job import inventory_ids, is_figure_job, load_inventory  # noqa: E402
from hxlib.figure_prompts import has_line_anchors  # noqa: E402
from hxlib.paper import detect_sections, extract_pages  # noqa: E402
from hxlib.paper_text import _canonical  # noqa: E402
from hxlib.prompts import has_line_numbers  # noqa: E402
from hxlib.review_warnings import numbered_weaknesses, review_words  # noqa: E402
from hxlib.validate import validate_round  # noqa: E402
from smoke_test import draw_figure, fake_review, make_pdf  # noqa: E402
from test_figure_job import figure_entry  # noqa: E402
from test_prompts import make_unnumbered_pdf  # noqa: E402

FABRICATED = "Our method achieves state-of-the-art results on ImageNet by a large margin"
_CAMERA_READY_HEAD = [
    "This CVPR paper is the Open Access version, provided by the Computer Vision Foundation.",
    "Except for this watermark, it is identical to the accepted version;",
    "Toy Title For An Identified Copy", "Jane Doe1 John Roe2", "1Example University 2Example Labs Inc.",
    "jane.doe@example.test", "Abstract", "We propose a toy method. It improves a toy metric by 1 point."]


def write_lines_pdf(path: Path, lines: list[str], figure: bool = True) -> None:
    """One 9-pt text row per line at x=60, no margin line numbers; optionally a figure page."""
    import fitz

    doc = fitz.open()
    page, y = doc.new_page(), 40
    for text in lines:
        if y > 780:
            page, y = doc.new_page(), 40
        page.insert_text((60, y), text, fontsize=9)
        y += 14
    if figure:
        draw_figure(doc.new_page(), 60, 1)
    doc.save(path)


def make_identified_pdf(path: Path) -> None:
    """A camera-ready-like toy paper: CVF watermark, authors, affiliation and e-mail, one figure."""
    lines = list(_CAMERA_READY_HEAD)
    for heading in ("1. Introduction", "2. Related Work", "3. Method", "4. Experiments", "5. Conclusion"):
        lines += [heading] + [f"Body text of {heading} sentence {k}." for k in range(6)]
        if heading.endswith("Experiments"):
            lines.append("As shown in Fig. 1, the toy method wins.")
    lines += ["Table 1. Toy results. Ours is best.", "References", "[1] A. Author. A paper. CVPR 2024."]
    write_lines_pdf(path, lines)


def write_outputs(rpath: Path) -> None:
    """Valid outputs for every job of a round, initial or answer check, the FIG job included."""
    rnd = load_json(rpath / "ROUND.json")
    items = load_inventory(rpath / "snapshot")
    main = inventory_ids(items)[0] if items is not None else []
    rng = random.Random(5)
    for job in rnd["jobs"]:
        data = fake_review(job, rnd, rng)
        if is_figure_job(job):
            data["figure_scores"] = {fid: figure_entry(fid, 6) for fid in main}
            data["weaknesses"] = [dict(data["weaknesses"][0], category="figures", figure_id=main[0],
                                       defect="illegible_text", decisive=False)]
        if job.get("stage") == "satisfy":
            sdir = rpath / "satisfaction" / job["job_id"]
            data.update(stage="satisfy", previous_rating=None, new_issues=[],
                        items=[{"id": w, "status": "partly", "reason": "toy reason", "evidence": "p.1",
                                "remaining_ask": "toy ask"} for w in job["open_items"]])
            save_json(sdir / "satisfaction.json", data)
            (sdir / "reply.md").write_text("Toy reply to the authors, long enough for the size check.\n",
                                           encoding="utf-8")
            continue
        out = review_dir(rpath, job)
        save_json(out / "review.json", data)
        heads = load_scales()["review_md_headings"]
        body = "\n\n".join(f"## {h}\n" + ("1. Toy weakness." if h == "Weaknesses" else "Toy text.") for h in heads)
        (out / "review.md").write_text(body + "\n", encoding="utf-8")
        (out / "debrief.md").write_text("Toy debrief with enough content for the output-size validation.\n",
                                        encoding="utf-8")


class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        cls.patcher = patch.object(hx, "SESSIONS_DIR", cls.root / "sessions")
        cls.patcher.start()
        cls.identified, cls.numbered, cls.unnumbered = (cls.root / n for n in ("id.pdf", "num.pdf", "unnum.pdf"))
        make_identified_pdf(cls.identified)
        make_pdf(cls.numbered, 1)
        make_unnumbered_pdf(cls.unnumbered)

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

    def new(self, name: str, pdf: Path, *extra: str) -> Path:
        code, out = self.cli("new", "--paper", pdf, "--name", name, *extra)
        self.assertEqual(code, 0, out)
        return next(p for p in hx.SESSIONS_DIR.iterdir() if p.name.endswith("_" + name))

    def answered_round(self, spath: Path, pdf: Path, *extra: str) -> tuple[int, str]:
        """Valid round-1 outputs, aggregate, writer answers, then `round` on `pdf`."""
        write_outputs(round_dir(spath, 1))
        self.assertEqual(self.cli("aggregate", spath)[0], 0)
        self.assertEqual(self.cli("stage", spath, "writer")[0], 0)
        sheet = round_dir(spath, 1) / "writer" / "RESPONSE.md"
        prompt = "Answer to the reviewer (cite lines/tables/figures of the new draft):"
        sheet.write_text(sheet.read_text(encoding="utf-8").replace("Decision:", "Decision: fix_text").replace(
            prompt, prompt + " See p.1, which now states the condition."), encoding="utf-8")
        return self.cli("round", spath, "--paper", pdf, *extra)

    @staticmethod
    def prompts(rpath: Path, stage: str) -> dict[str, str]:
        return {p.stem: p.read_text(encoding="utf-8") for p in (rpath / "prompts" / stage).glob("*.md")}

    def test_new_refuses_identified_copy(self) -> None:
        code, out = self.cli("new", "--paper", self.identified, "--name", "refused", "--reviewers", "R09")
        self.assertEqual(code, 1, out)
        for needle in ("new refused", "author email 'jane.doe@example.test'", "CVF Open Access",
                       "--allow-identified", "--cutoff <the paper's original submission deadline>"):
            self.assertIn(needle, out)
        self.assertFalse(hx.SESSIONS_DIR.exists() and any(p.name.endswith("_refused") for p in hx.SESSIONS_DIR.iterdir()))
        code, out = self.cli("new", "--paper", self.identified, "--name", "refused2", "--reviewers", "R09",
                             "--cutoff", "2023-03-01")
        self.assertEqual(code, 1, out)
        self.assertNotIn("--cutoff <the paper's", out, "a given --cutoff silences the recommendation")

    def test_allowed_identified_copy_prompts_and_reports(self) -> None:
        code, out = self.cli("new", "--paper", self.identified, "--name", "allowed", "--reviewers", "R03,R09",
                             "--figures", "--allow-identified")
        self.assertEqual(code, 0, out)
        self.assertIn("--allow-identified: continuing", out)
        self.assertIn("--cutoff <the paper's original submission deadline>", out)
        spath = next(p for p in hx.SESSIONS_DIR.iterdir() if p.name.endswith("_allowed"))
        self.assertIs(load_json(spath / "SESSION.json")["allow_identified"], True)
        r1 = round_dir(spath, 1)
        paper = load_json(r1 / "ROUND.json")["paper"]
        self.assertTrue(any("author email" in f for f in paper["anonymity_flags"]), paper["anonymity_flags"])
        self.assertIs(paper["line_numbers"], False)
        initial = self.prompts(r1, "initial")
        self.assertEqual(set(initial), {"R03", "R09", "FIG"})
        for jid, text in initial.items():
            self.assertEqual(text.count(IDENTIFIED_LINE), 1, jid)
        code, out = self.answered_round(spath, self.identified)
        self.assertEqual(code, 0, out)
        satisfy = self.prompts(round_dir(spath, 2), "satisfy")
        self.assertEqual(set(satisfy), {"R03", "R09", "FIG"})
        for jid, text in satisfy.items():
            self.assertIn(IDENTIFIED_LINE, text, jid)
        scores = (r1 / "SCORES.md").read_text(encoding="utf-8")
        self.assertIn("**Anonymity flags:** main p.1:", scores)
        self.assertIn("author email", scores)
        head = scores.split("Reviews found:")[0]
        self.assertRegex(head, r"\*\*\n\nGrounding: \d+/\d+ quotes verified")
        self.assertTrue((r1 / "GROUNDING.md").exists())
        grounding = load_json(r1 / "SCORES.json")["grounding"]
        self.assertEqual(set(grounding), {"summary", "totals"})

    def test_round_refuses_identified_copy_until_allowed(self) -> None:
        spath = self.new("clean", self.numbered, "--reviewers", "R09")
        self.assertIs(load_json(spath / "SESSION.json")["allow_identified"], False)
        self.assertNotIn(IDENTIFIED_LINE, self.prompts(round_dir(spath, 1), "initial")["R09"])
        code, out = self.answered_round(spath, self.identified)
        self.assertEqual(code, 1, out)
        self.assertIn("round refused", out)
        self.assertFalse(round_dir(spath, 2).exists())
        self.assertNotIn("Anonymity flags", (round_dir(spath, 1) / "SCORES.md").read_text(encoding="utf-8"))
        code, out = self.cli("round", spath, "--paper", self.identified, "--allow-identified")
        self.assertEqual(code, 0, out)
        self.assertIs(load_json(spath / "SESSION.json")["allow_identified"], True)
        self.assertIn(IDENTIFIED_LINE, self.prompts(round_dir(spath, 2), "satisfy")["R09"])

    def test_aggregation_survives_a_grounding_failure(self) -> None:
        spath = self.new("noground", self.numbered, "--reviewers", "R09")
        rpath = round_dir(spath, 1)
        write_outputs(rpath)
        with patch("hxlib.aggregate.round_grounding", side_effect=RuntimeError("broken index")), \
                self.assertLogs("hxlib.aggregate", level="WARNING"):
            agg = aggregate_round(load_json(rpath / "ROUND.json"), rpath)
        self.assertNotIn("grounding", agg)
        self.assertEqual(agg["reviews_found"], 1)

    def test_line_numbers_meta_agrees_with_fallbacks(self) -> None:
        for name, pdf, expected in (("lines", self.numbered, True), ("nolines", self.unnumbered, False)):
            rpath = round_dir(self.new(name, pdf, "--reviewers", "R09"), 1)
            rnd = load_json(rpath / "ROUND.json")
            self.assertIs(rnd["paper"]["line_numbers"], expected, name)
            legacy = dict(rnd, paper={k: v for k, v in rnd["paper"].items() if k != "line_numbers"})
            self.assertEqual(has_line_numbers(legacy, rpath / "snapshot"), expected, name)
            self.assertEqual(has_line_anchors(legacy, rpath / "snapshot"), expected, name)

    def test_null_criteria_and_warnings(self) -> None:
        spath = self.new("warn", self.numbered, "--reviewers", "R09", "--heldout", "R11")
        rpath = round_dir(spath, 1)
        write_outputs(rpath)
        rnd = load_json(rpath / "ROUND.json")
        jobs = {j["job_id"]: j for j in rnd["jobs"]}
        held = review_dir(rpath, jobs["HR11"]) / "review.json"
        held_data = load_json(held)
        held_data["weaknesses"][0]["text"] = f'The paper says "{FABRICATED}".'
        save_json(held, held_data)
        out_dir = review_dir(rpath, jobs["R09"])
        data = load_json(out_dir / "review.json")
        section = next(iter(data["section_scores"].values()))
        first = next(iter(section["criteria"]))
        section["criteria"][first] = None
        weakness = dict(data["weaknesses"][0], text=f'The paper says "{FABRICATED}".')
        data["weaknesses"] = [dict(weakness, id=f"W{k}") for k in range(1, 6)]
        save_json(out_dir / "review.json", data)
        self.assertEqual(validate_round(rnd, rpath)["R09"], [], "null criterion = not observed")
        heads = load_scales()["review_md_headings"]
        long_md = "\n\n".join(f"## {h}\n" + ("1. First point.\n2. Second point." if h == "Weaknesses" else
                                             "word " * 100) for h in heads)
        (out_dir / "review.md").write_text(long_md + "\n\n## Section scores\n| a | b |\n" + "cell " * 300,
                                           encoding="utf-8")
        code, out = self.cli("validate", spath)
        self.assertEqual(code, 0, out)
        self.assertIn("R09: OK (", out)
        # 500 filler words + 6 in the two points + 6 heading words; the 300 words after the table do not count
        for needle in ("review.md has 512 words; the persona's band is 150-300 words (more than 20% over)",
                       "review.json has 5 weaknesses; the persona allows at most 3",
                       "review.md numbers 2 points under Weaknesses; review.json has 5 weaknesses",
                       f'quote not found in the paper: "{FABRICATED}"'):
            self.assertIn("warning: " + needle, out)
        self.assertIn("round 1: 2/2 valid;", out)
        held_block = out.split("HR11: OK", 1)[1].split("\nR09:", 1)[0].split("\nround 1:", 1)[0]
        self.assertIn("grounding warnings; held-out details go to heldout/GROUNDING.md", held_block)
        self.assertNotIn(FABRICATED, held_block, "held-out quotes stay out of the validate output")
        for bad in (6, "3"):
            section["criteria"][first] = bad
            save_json(out_dir / "review.json", data)
            self.assertTrue(any(f"criteria.{first}" in e for e in validate_round(rnd, rpath)["R09"]), bad)

    def test_review_shape_helpers(self) -> None:
        md = "Intro line\n## Summary\nOne two three.\n## Weaknesses\n1. A\n   1. nested\n2) B\n- bullet\n" \
             "## Section scores\n| x | 1 |\n"
        self.assertEqual(review_words(md), 11, "from after the Summary heading to the score table")
        self.assertEqual(numbered_weaknesses(md), 2)
        self.assertIsNone(numbered_weaknesses("## Summary\nNo weakness heading.\n"))
        self.assertEqual(review_words("**Summary:** four words are here"), 4)
        grouped = ("## Summary\nWeaknesses are minor overall.\n## Weaknesses\n### Major\n1. a\n2. b\n**Minor**\n"
                   "1. c\n## Questions\n1. q?\n")
        self.assertEqual(numbered_weaknesses(grouped), 3, "groups stay inside; a sentence is not a heading")
        self.assertEqual(numbered_weaknesses("**Weaknesses**\n1. a\n2. b\n**Questions**\n1. q?\n"), 2)

    def test_unscored_and_impact_sections(self) -> None:
        lines = ["A Toy Paper", "Anonymous CVPR submission", "Abstract", "We propose a toy method."]
        for heading in ("1. Introduction", "2. Method", "3. Experiments", "4. Conclusion", "5. Broader Impact",
                        "6. Acknowledgements", "7. Reproducibility Statement"):
            lines += [heading] + [f"Body text of {heading} sentence {k}." for k in range(3)]
            if heading.endswith("Conclusion"):
                lines.append("Limitations. The toy method only works on toys.")
        lines += ["References", "[1] A. Author. A paper. CVPR 2024."]
        pdf = self.root / "statements.pdf"
        write_lines_pdf(pdf, lines, figure=False)
        spans = {s["key"]: s for s in detect_sections(*extract_pages(pdf))}
        self.assertNotIn("ablations_analysis", spans)
        self.assertIn("5. Broader Impact", spans["limitations"]["heading"])
        self.assertEqual(spans[UNSCORED_SECTION]["heading"], "6. Acknowledgements + 7. Reproducibility Statement")
        self.assertNotIn("Acknowledgements", spans["conclusion"]["text"])
        for heading, key in (("Conclusion and Broader Impact", "conclusion"), ("Funding", UNSCORED_SECTION),
                             ("A CKNOWLEDGMENTS", UNSCORED_SECTION), ("E THICS S TATEMENT", "limitations"),
                             ("Societal Impact", "limitations"), ("Visualizations", "ablations_analysis")):
            self.assertEqual(_canonical(heading, True), key, heading)
        spath = self.new("statements", pdf, "--reviewers", "R03", "--mode", "both",
                         "--allow-identified")  # the acknowledgements heading is an anonymity flag
        rnd = load_json(round_dir(spath, 1) / "ROUND.json")
        self.assertIn(UNSCORED_SECTION, rnd["paper"]["sections_found"])
        self.assertFalse([j["job_id"] for j in rnd["jobs"] if UNSCORED_SECTION in j["sections"]])
        snap = round_dir(spath, 1) / "snapshot"
        limitations = (snap / "sections" / "limitations.txt").read_text(encoding="utf-8")
        self.assertIn("only works on toys", limitations, "the paper's own limitations paragraph is kept")
        self.assertIn("Body text of 5. Broader Impact", limitations)

    def test_satisfy_prompt_targets_box(self) -> None:
        spath = self.new("targets", self.unnumbered, "--reviewers", "R09")
        code, out = self.answered_round(spath, self.unnumbered)
        self.assertEqual(code, 0, out)
        text = self.prompts(round_dir(spath, 2), "satisfy")["R09"]
        box = text[text.index("## 0. Targets"):text.index("## 1. Who you are")]
        for needle in ("`reply.md`: at most 300 words.", "New issues: at most 3 points; at most 2 of them decisive",
                       "This PDF has no line numbers."):
            self.assertIn(needle, box)
        self.assertNotIn("debrief.md", box)
        self.assertNotIn(IDENTIFIED_LINE, text, "a clean copy gets no identified-copy line")

    def test_anonymity_patterns(self) -> None:
        head = [("", "A Toy Paper"), ("", "Anonymous CVPR submission"), ("", "Abstract")]

        def flags(*texts: str) -> str:
            return " | ".join(scan_anonymity([head + [("", t) for t in texts]]))

        self.assertIn("grant number", flags("This work was supported by Grants Nos. ABC-12345 and DEF-678."))
        self.assertEqual(flags("This design grants notable flexibility.", "It grants no-reference metrics.",
                               "She was an award nominee."), "", "prose is not a grant number")
        self.assertEqual(flags("We use the model from https://huggingface.co/someone/baseline."), "")
        self.assertIn("authors' own", flags("The code will be released at https://github.com/me/toy."))
        refs = ("References", "K. He, X. Zhang. Toy project page at https://github.com/kh/toy.")
        self.assertEqual(flags(*refs), "", "a reference line starting with initials stays in the references")
        self.assertIn("authors' own", flags(*refs, "A. Proofs", "Our code: https://github.com/me/toy."))

    def test_running_header_stamp_is_flagged_once(self) -> None:
        pdf = self.root / "iclr_final.pdf"
        body = [f"Body text of a published toy paper, sentence {k}." for k in range(70)]
        write_lines_pdf(pdf, [line for k in range(0, 70, 35)
                              for line in ["Published as a conference paper at ICLR 2024"] + body[k:k + 35]],
                        figure=False)
        pages = extract_pages(pdf)[0]
        self.assertEqual(scan_anonymity(pages), [], "text extraction drops the running header")
        stamps = [f for f in scan_document(pages, pdf) if "camera-ready header (published)" in f]
        self.assertEqual(len(stamps), 1, stamps)

    def test_windows_encoded_answer_sheet_parses(self) -> None:
        sheet = self.root / "RESPONSE.md"
        text = "# Author response\n\n### R09:W1\nDecision: fix_text\nWe clarified the authors’ claim (café).\n"
        sheet.write_bytes(text.encode("cp1252"))
        with self.assertLogs("hxlib.dialogue", level="WARNING") as logs:
            blocks = parse_response(sheet, {"R09:W1"})
        self.assertIn("authors’ claim (café)", blocks["R09:W1"])
        self.assertTrue(any("Windows-1252" in line for line in logs.output))
        sheet.write_bytes(b"\xef\xbb\xbf" + text.encode("utf-8"))
        self.assertIn("café", parse_response(sheet)["R09:W1"])
        sheet.write_bytes(text.encode("utf-16"))  # PowerShell 5 `>` writes UTF-16 with a byte-order mark
        self.assertIn("authors’ claim (café)", parse_response(sheet)["R09:W1"])


if __name__ == "__main__":
    logging.basicConfig(level=logging.ERROR)
    unittest.main()
