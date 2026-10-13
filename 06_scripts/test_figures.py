#!/usr/bin/env python3
"""Unit tests of the figure snapshot (figure_render.snapshot_figures) on synthetic PDFs.

Layouts: a figure above its caption, a table below its caption, a two-column page, pages without
figures, supplement caps, deterministic crop hashes for blind pairwise, and a failure inside the
figure code that must leave the paper snapshot usable. Also: placeholders for captions the text
has but the locator missed, flags and prompt lines for unmeasured plot text, and line-anchor
detection for the figure prompt. PyMuPDF and the standard library only.
"""
from __future__ import annotations

import random
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fitz  # noqa: E402

from hxlib import figure_render  # noqa: E402
from hxlib.common import load_json, save_json, sha256_file  # noqa: E402
from hxlib.figure_job import caption_ids, inventory_ids  # noqa: E402
from hxlib.figure_locate import body_font_size, locate_on_page, text_extent  # noqa: E402
from hxlib.figure_prompts import _figure_lines, has_line_anchors  # noqa: E402
from hxlib.paper import extract_lines, snapshot_paper  # noqa: E402
from hxlib.prompts_stages import _figure_pairs  # noqa: E402

_WORDS = ("the method improves the baseline on every benchmark we tried and the gains hold across "
          "seeds datasets and resolutions while the cost stays").split()
LETTER = (612, 792)


def prose(page, rect, size: float = 9.0, lead: str = "") -> None:
    """Fill a rectangle with body prose (one multi-line text block)."""
    for n in range(400, 10, -10):
        text = lead + " ".join(_WORDS[i % len(_WORDS)] for i in range(n))
        if page.insert_textbox(fitz.Rect(rect), text, fontsize=size) >= 0:
            return
    raise ValueError(f"no prose fits {rect}")


def bar_chart(page, rect, label_pt: float = 5.0, colour: bool = True, heights=(0.3, 0.5, 0.7, 0.9)) -> None:
    """Vector bar chart inside `rect`: two axes, one bar per height, an axis label of `label_pt`."""
    x0, y0, x1, y1 = rect
    base = y1 - 10
    page.draw_line((x0 + 10, y0), (x0 + 10, base))
    page.draw_line((x0 + 10, base), (x1, base))
    w = (x1 - x0 - 20) / len(heights)
    for k, h in enumerate(heights):
        fill = (0.9 - 0.2 * k, 0.3, 0.2 + 0.2 * k) if colour else (0.15 * k, 0.15 * k, 0.15 * k)
        page.draw_rect(fitz.Rect(x0 + 15 + k * w, base - h * (base - y0), x0 + 5 + (k + 1) * w, base),
                       color=(0, 0, 0), fill=fill)
    page.insert_text(((x0 + x1) / 2 - 15, y1 - 1), "accuracy (%)", fontsize=label_pt)


def ruled_table(page, x0: float, x1: float, top: float, size: float = 8.0) -> float:
    """Booktabs-like table under `top`: rules and a header plus three rows; returns its bottom."""
    rows = [("Method", "PSNR", "SSIM"), ("Baseline", "30.1", "0.91"), ("Prior", "31.4", "0.92"),
            ("Ours", "32.0", "0.94")]
    cw = (x1 - x0) / 3
    page.draw_line((x0, top), (x1, top))
    y = top + size + 3
    for row in rows:
        for c, cell in enumerate(row):
            page.insert_text((x0 + 6 + c * cw, y), cell, fontsize=size)
        y += size + 4
    page.draw_line((x0, y - size), (x1, y - size))
    return y - size


def single_column_pdf(path: Path, heights=(0.3, 0.5, 0.7, 0.9), extra_page: bool = True) -> None:
    """Page 1: prose, Fig. 1 above its caption, prose, Tab. 1 caption above its table, prose.

    Captions follow LaTeX: a one-line caption is centred, a longer one wraps over the text width.
    """
    doc = fitz.open()
    page = doc.new_page(width=LETTER[0], height=LETTER[1])
    prose(page, (72, 60, 540, 160), lead="As Fig. 1 shows, ")
    bar_chart(page, (90, 180, 520, 330), label_pt=5.0, heights=heights)
    page.insert_textbox(fitz.Rect(72, 338, 540, 364), "Figure 1. A toy bar chart. The last bar is ours.",
                        fontsize=9, align=fitz.TEXT_ALIGN_CENTER)
    prose(page, (72, 380, 540, 510))
    page.insert_textbox(fitz.Rect(72, 524, 540, 552), "Table 1. Toy numbers on three benchmarks. Higher is "
                        "better for both metrics; the best result in each column is the last row, which is "
                        "our method.", fontsize=9)
    bottom = ruled_table(page, 150, 460, 560)
    prose(page, (72, bottom + 20, 540, 740))
    if extra_page:
        prose(doc.new_page(width=LETTER[0], height=LETTER[1]), (72, 60, 540, 700))
    doc.save(path)


def two_column_pdf(path: Path) -> None:
    """Left column: prose, Fig. 1 above its caption, prose. Right column: prose, Tab. 1 caption, table, prose."""
    doc = fitz.open()
    page = doc.new_page(width=LETTER[0], height=LETTER[1])
    left, right = (54, 297), (315, 558)
    prose(page, (left[0], 60, left[1], 200))
    bar_chart(page, (left[0] + 6, 214, left[1] - 6, 330), label_pt=7.0, colour=False)
    page.insert_textbox(fitz.Rect(left[0], 338, left[1], 362), "Figure 1. Left column chart.", fontsize=9)
    prose(page, (left[0], 376, left[1], 740), lead="Fig. 1 and Tab. 1 summarize the results. ")
    prose(page, (right[0], 60, right[1], 300))
    page.insert_textbox(fitz.Rect(right[0], 314, right[1], 330), "Table 1. Right column table.", fontsize=9)
    bottom = ruled_table(page, right[0] + 4, right[1] - 4, 338)
    prose(page, (right[0], bottom + 18, right[1], 740))
    doc.save(path)


def prose_only_pdf(path: Path, pages: int = 2) -> None:
    doc = fitz.open()
    for _ in range(pages):
        prose(doc.new_page(width=LETTER[0], height=LETTER[1]), (72, 60, 540, 700))
    doc.save(path)


def snapshot(pdf: Path, dest: Path, supp: Path | None = None) -> tuple[dict, dict[str, dict]]:
    summary = figure_render.snapshot_figures(dest, pdf, extract_lines(pdf), supp,
                                             extract_lines(supp) if supp else None)
    return summary, {i["id"]: i for i in load_json(dest / "figures" / "figures.json")}


class FigureSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_figure_above_caption_and_table_below_caption(self):
        pdf = self.root / "one.pdf"
        single_column_pdf(pdf)
        summary, items = snapshot(pdf, self.root / "snap")
        self.assertEqual((summary["figures"], summary["tables"], summary["not_located"]), (1, 1, []))
        fig, tab = items["fig_1"], items["tab_1"]
        x0, y0, x1, y1 = fig["region_pt"]
        self.assertTrue(85 <= x0 and x1 <= 525 and 175 <= y0 and y1 <= 338, fig["region_pt"])
        self.assertLess(y0, 200, "the whole chart, not just the axis label")
        tx0, ty0, tx1, ty1 = tab["region_pt"]
        self.assertTrue(ty0 >= 550 and ty1 <= 620 and tx0 >= 140 and tx1 <= 470, tab["region_pt"])
        snap = self.root / "snap"
        for item in (fig, tab):
            self.assertTrue((snap / item["crop"]).exists() and (snap / item["gray_preview"]).exists())
            self.assertEqual(item["crop_sha256"], sha256_file(snap / item["crop"]))
        self.assertEqual(fig["min_text_pt"], 5.0)
        self.assertTrue(any(f.startswith("small_text") for f in fig["flags"]), fig["flags"])
        self.assertTrue(fig["cvd_preview"] and (snap / fig["cvd_preview"]).exists(), "colour chart")
        self.assertIsNone(tab["cvd_preview"], "black-and-white table")
        self.assertEqual(fig["mentions"][0]["page"], 1)
        self.assertTrue(any(f.startswith("not_referenced") for f in tab["flags"]))
        self.assertIn("| fig_1 | Fig. 1 | 1 | figures/fig_1.png |",
                      (snap / "FIGURES.md").read_text(encoding="utf-8"))

    def test_two_column_layout_keeps_regions_in_their_columns(self):
        pdf = self.root / "two.pdf"
        two_column_pdf(pdf)
        summary, items = snapshot(pdf, self.root / "snap")
        self.assertEqual((summary["figures"], summary["tables"], summary["not_located"]), (1, 1, []))
        fig, tab = items["fig_1"], items["tab_1"]
        self.assertFalse(fig["full_width"] or tab["full_width"])
        self.assertTrue(fig["region_pt"][2] <= 306 and fig["region_pt"][1] >= 200, fig["region_pt"])
        self.assertTrue(tab["region_pt"][0] >= 306 and tab["region_pt"][1] >= 330, tab["region_pt"])
        self.assertEqual(fig["min_text_pt"], 7.0)
        self.assertFalse(any(f.startswith("small_text") for f in fig["flags"]))
        self.assertIsNone(fig["cvd_preview"], "gray chart gets no colour-vision preview")
        self.assertTrue(fig["mentions"] and tab["mentions"])

    def test_cached_pages_locate_exactly_like_raw_pages(self):
        def layout(pages: list) -> tuple:
            body = body_font_size(pages)
            extent = text_extent(pages, body)
            return body, extent, [(f["kind"], f["number"], f["caption"], tuple(f["region"]))
                                  for p in pages for f in locate_on_page(p, body, extent)]

        for build in (single_column_pdf, two_column_pdf):
            pdf = self.root / f"{build.__name__}.pdf"
            build(pdf)
            with fitz.open(pdf) as doc:
                raw = layout(list(doc))
                self.assertEqual(layout([figure_render._CachedPage(p) for p in doc]), raw)
                self.assertTrue(raw[2], build.__name__)

    def test_pages_without_figures(self):
        pdf = self.root / "prose.pdf"
        prose_only_pdf(pdf)
        summary, items = snapshot(pdf, self.root / "snap")
        self.assertEqual(summary, {"figures": 0, "tables": 0, "not_located": [], "flagged": 0})
        self.assertEqual(items, {})
        snap = self.root / "snap"
        self.assertTrue((snap / "pages" / "main_p01.png").exists() and (snap / "pages" / "main_p02.png").exists())
        line = figure_render.figure_reading_line(snap, "front")
        self.assertIn("main_p01.png", line)
        self.assertNotIn("fig_1", line)
        mixed = self.root / "mixed.pdf"
        single_column_pdf(mixed)
        _, items = snapshot(mixed, self.root / "snap_mixed")
        self.assertTrue(all(i["page"] == 1 for i in items.values()), "page 2 is prose only")

    def test_supplement_ids_and_caps(self):
        main, supp = self.root / "main.pdf", self.root / "supp.pdf"
        prose_only_pdf(main, 1)
        doc = fitz.open()
        for k in range(3):  # figure page, prose page, figure page
            page = doc.new_page(width=LETTER[0], height=LETTER[1])
            if k == 1:
                prose(page, (72, 60, 540, 700))
                continue
            prose(page, (72, 60, 540, 160))
            bar_chart(page, (90, 180, 520, 330))
            page.insert_textbox(fitz.Rect(72, 338, 540, 364), f"Figure {k + 1}. Supplement chart.", fontsize=9)
            prose(page, (72, 380, 540, 700))
        doc.save(supp)
        with patch.object(figure_render, "SUPP_MAX_PAGES", 2):
            summary, items = snapshot(main, self.root / "snap", supp)
        snap = self.root / "snap"
        self.assertEqual(list(items), ["supp_fig_1"])
        self.assertEqual(items["supp_fig_1"]["label"], "Supp. Fig. 1")
        self.assertNotIn("not_referenced: no 'Fig./Table N' mention in the main text", items["supp_fig_1"]["flags"])
        self.assertEqual(summary["supp_pages_skipped"], 1)
        self.assertTrue((snap / "pages" / "supp_p01.png").exists())
        self.assertFalse((snap / "pages" / "supp_p02.png").exists(), "supplement page without figures: no image")
        self.assertFalse((snap / "pages" / "supp_p03.png").exists(), "pages past the cap are skipped")
        self.assertIn("Supplement pages after page 2 (1)", (snap / "FIGURES.md").read_text(encoding="utf-8"))
        self.assertIn("follow your supplement rule", figure_render.figure_reading_line(snap, "main"))
        self.assertNotIn("supplement rule", figure_render.figure_reading_line(snap, "full"))

    def test_crop_hash_is_deterministic_and_drives_figure_pairs(self):
        v1, v2 = self.root / "v1.pdf", self.root / "v2.pdf"
        single_column_pdf(v1)
        single_column_pdf(v2, heights=(0.9, 0.7, 0.5, 0.3))
        snaps = {}
        for name, pdf in (("a", v1), ("b", v1), ("c", v2)):
            snaps[name] = self.root / name
            snapshot(pdf, snaps[name])
        sha = {n: load_json(s / "figures" / "figures.json")[0]["crop_sha256"] for n, s in snaps.items()}
        self.assertEqual(sha["a"], sha["b"], "same PDF, same crop bytes")
        self.assertNotEqual(sha["a"], sha["c"])
        pdir = self.root / "pairwise"
        self.assertEqual(_figure_pairs(snaps["a"], snaps["b"], pdir, random.Random(1)), ({}, []))
        key, facts = _figure_pairs(snaps["a"], snaps["c"], pdir, random.Random(1))
        self.assertEqual(list(key), ["figure:fig_1"])
        self.assertEqual(sorted(key["figure:fig_1"].values()), ["new", "old"])
        self.assertIn("smallest text 5.0 pt", facts[0])
        new_side = next(s for s, v in key["figure:fig_1"].items() if v == "new")
        self.assertEqual(sha256_file(pdir / f"{new_side}_fig_fig_1.png"), sha["c"])
        self.assertEqual(_figure_pairs(self.root / "legacy", snaps["c"], pdir, random.Random(1)), ({}, []))

    def test_figure_failure_leaves_snapshot_usable(self):
        pdf = self.root / "one.pdf"
        single_column_pdf(pdf)
        dest = self.root / "snap"
        with patch.object(figure_render, "locate_on_page", side_effect=RuntimeError("synthetic locator bug")), \
                self.assertLogs("hxlib.paper", level="WARNING"):
            meta = snapshot_paper(pdf, dest)
        self.assertEqual(meta["figures"], {"error": "RuntimeError: synthetic locator bug"})
        self.assertTrue(meta["main_pdf_sha256"] and meta["sections_found"])
        self.assertTrue((dest / "view_main.txt").exists() and (dest / "sections.json").exists())
        self.assertFalse((dest / "FIGURES.md").exists() or (dest / "figures" / "figures.json").exists())
        self.assertIsNone(figure_render.figure_reading_line(dest, "main"))
        ok = snapshot_paper(pdf, self.root / "snap_ok")
        self.assertEqual(ok["figures"]["figures"], 1)

    def test_caption_in_text_but_not_located_gets_placeholder(self):
        main, supp = self.root / "main.pdf", self.root / "supp.pdf"
        single_column_pdf(main)  # p.1: Fig. 1 and Tab. 1; p.2: prose only
        prose_only_pdf(supp, 3)
        snap = self.root / "snap"
        snap.mkdir()
        save_json(snap / "captions.json", [
            {"doc": "main", "page": 1, "anchor": "", "text": "Figure 1. A toy bar chart. The last bar is ours."},
            {"doc": "main", "page": 1, "anchor": "", "text": "Fig. 1. Additionally, a wrapped mention."},
            {"doc": "main", "page": 2, "anchor": "", "text": "Figure 2.  A figure the locator\nmisses."},
            {"doc": "main", "page": 9, "anchor": "", "text": "Table 9. Past the last page."},
            {"doc": "supp", "page": 2, "anchor": "", "text": "Figure 1. A supplement figure."},
            {"doc": "supp", "page": 3, "anchor": "", "text": "Figure 2. Past the supplement cap."}])
        with patch.object(figure_render, "SUPP_MAX_PAGES", 2), \
                self.assertLogs("hxlib.figure_render", level="WARNING"):
            summary, items = snapshot(main, snap, supp)
        self.assertEqual(list(items), ["fig_1", "tab_1", "fig_2", "supp_fig_1"])
        self.assertEqual(summary["not_located"], ["fig_2", "supp_fig_1"])
        fig2 = items["fig_2"]
        self.assertEqual((fig2["crop"], fig2["crop_sha256"], fig2["page_image"]), (None, None, "pages/main_p02.png"))
        self.assertEqual(fig2["caption"], "Figure 2. A figure the locator misses.")
        self.assertEqual(fig2["flags"][0], "not_located: caption found in text")
        self.assertTrue(any(f.startswith("not_referenced") for f in fig2["flags"]))
        self.assertTrue((snap / "pages" / "supp_p02.png").exists(), "placeholder page gets a page image")
        self.assertFalse((snap / "pages" / "supp_p03.png").exists(), "pages past the cap are skipped")
        self.assertEqual(inventory_ids(list(items.values()))[0], ["fig_1", "tab_1", "fig_2"])
        self.assertEqual(caption_ids(snap), ["fig_1", "fig_2", "tab_9"])
        self.assertIn("| fig_2 | Fig. 2 | 2 | pages/main_p02.png |", (snap / "FIGURES.md").read_text(encoding="utf-8"))
        self.assertIn("NOT LOCATED, use page image", _figure_lines(snap, [fig2])[0])

    def test_unmeasured_plot_text_flags_and_prompt_lines(self):
        snap = self.root / "snap"
        item = {"id": "fig_1", "doc": "main", "kind": "figure", "number": "1", "label": "Fig. 1", "page": 1,
                "page_image": "pages/main_p01.png", "caption": "Figure 1. Toy.", "caption_words": 3,
                "crop": "figures/fig_1.png", "mentions": [{"page": 1, "anchor": ""}], "min_text_pt": 5.0,
                "min_script_pt": 4.0, "text_not_measured": True, "min_image_ppi": None, "flags": []}
        self.assertFalse(any(f.startswith("small_text") for f in figure_render._flags(item)),
                         "unmeasured plot text: no small_text flag from subcaption or script sizes")
        self.assertTrue(any("5.0 pt" in f for f in figure_render._flags(dict(item, text_not_measured=False))))
        self.assertFalse(figure_render._flags(dict(item, min_text_pt=7.0, text_not_measured=False)),
                         "scripts alone (4.0 pt) never raise small_text")
        self.assertIn("| 5.0 (scripts 4.0); plot text unmeasured |", figure_render.figures_markdown([item]))
        line = _figure_lines(snap, [item])[0]
        self.assertIn("; plot text unmeasured (raster or outlined): judge it on the page image", line)
        self.assertIn(str(snap / "pages" / "main_p01.png"), line)
        self.assertIn("sub/superscripts 4.0 pt", line)
        legacy = {k: v for k, v in item.items() if k not in ("min_script_pt", "text_not_measured")}
        self.assertNotIn("unmeasured", _figure_lines(snap, [legacy])[0])
        self.assertIn("| 5.0 |", figure_render.figures_markdown([legacy]))

    def test_line_anchor_detection(self):
        snap = self.root / "snap"
        snap.mkdir()
        self.assertFalse(has_line_anchors({"paper": {}}, snap), "no view_main.txt")
        self.assertTrue(has_line_anchors({"paper": {"line_numbers": True}}, snap))
        page = "\n".join(f"L{100 + i:03d}  line {i}" for i in range(12))
        (snap / "view_main.txt").write_text(f"===== [main p.1] =====\n{page}\n===== [main p.2] =====\n{page}\n",
                                            encoding="utf-8")
        self.assertTrue(has_line_anchors({"paper": {}}, snap), "12 anchors per page")
        self.assertFalse(has_line_anchors({"paper": {"line_numbers": False}}, snap), "recorded value wins")
        stray = "===== [main p.1] =====\nL101  a\n      b\n===== [main p.2] =====\nL202  c\n      d\n"
        (snap / "view_main.txt").write_text(stray, encoding="utf-8")
        self.assertFalse(has_line_anchors({"paper": {}}, snap), "a few stray numbers are not anchors")


if __name__ == "__main__":
    unittest.main()
