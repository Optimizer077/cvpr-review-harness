#!/usr/bin/env python3
"""Tests for the double-blind scan (hxlib/anonymity.py): leaks are flagged, citations are not."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from hxlib.anonymity import scan_anonymity  # noqa: E402
from hxlib.paper import extract_lines  # noqa: E402

_REVIEW_COPY = [
    "CVPR 2027 Submission #1234. CONFIDENTIAL REVIEW COPY. DO NOT DISTRIBUTE.",
    "A Toy Method for Toy Problems", "Anonymous CVPR submission", "Paper ID 1234", "Abstract",
    "We study a toy problem. Code is available at https://anonymous.4open.science/r/toy-1234.",
    "1. Introduction", "Prior work [3] released code at https://github.com/someone/baseline for comparison.",
    "References", "[1] A. Author. A preprint. arXiv:2101.01234, 2021.",
    "[2] B. Author. Another one. https://github.com/other/repo.", "[3] C. Author. A paper. CVPR 2024.",
]
_CAMERA_READY = [
    "This CVPR paper is the Open Access version, provided by the Computer Vision Foundation.",
    "Except for this watermark, it is identical to the accepted version;",
    "A Toy Method for Toy Problems", "Jane Doe1 John Roe2", "1Example University 2Example Labs Inc.",
    "jane.doe@example.org", "https://janedoe.github.io/toy", "Abstract", "We study a toy problem.",
    "1. Introduction", "Building on our previous work [3], we extend the method.",
    "Acknowledgements", "This work was supported by grant No. ABC-12345.",
    "References", "[1] A. Author. A preprint. arXiv:2101.01234, 2021.",
]


def _pdf(path: Path, lines: list[str]) -> Path:
    import fitz

    doc = fitz.open()
    page, y = doc.new_page(), 40
    for text in lines:
        if y > 780:
            page, y = doc.new_page(), 40
        page.insert_text((60, y), text, fontsize=9)
        y += 14
    doc.save(path)
    return path


class AnonymityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_review_copy_with_citations_is_clean(self) -> None:
        pages = extract_lines(_pdf(self.dir / "review.pdf", _REVIEW_COPY))
        self.assertEqual(scan_anonymity(pages), [])

    def test_camera_ready_leaks_are_flagged(self) -> None:
        flags = " | ".join(scan_anonymity(extract_lines(_pdf(self.dir / "final.pdf", _CAMERA_READY))))
        for what in ("CVF Open Access", "accepted version", "author email", "affiliation in the title block",
                     "authors' own", "self-citation", "acknowledgements section", "grant number"):
            self.assertIn(what, flags)
        self.assertNotIn("arXiv", flags)  # a cited preprint is not a leak

    def test_preprint_stamp_is_flagged(self) -> None:
        lines = ["arXiv:2401.01234v2  [cs.CV]  5 Feb 2024"] + _REVIEW_COPY
        flags = scan_anonymity(extract_lines(_pdf(self.dir / "arxiv.pdf", lines)))
        self.assertTrue(any("arXiv preprint stamp" in f for f in flags), flags)


if __name__ == "__main__":
    unittest.main(verbosity=1)
