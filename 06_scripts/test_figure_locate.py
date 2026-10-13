"""Regression tests for hxlib.figure_locate on synthetic PDFs (plain asserts, no pytest).

Run: python 06_scripts/test_figure_locate.py   -> prints one line per case and OK.
Each case builds a small PDF with PyMuPDF that reproduces one layout the locator must handle.
"""
from __future__ import annotations

import fitz

from hxlib.figure_locate import body_font_size, locate_on_page, measure, text_extent

W, H = 612, 792
WORDS = ("the proposed method is evaluated on several benchmarks and we report the average error "
         "over three runs while keeping the training schedule fixed for every baseline in this study ").split()


def prose(page, rect: fitz.Rect, size: float = 10, seed: int = 0) -> None:
    """Fill a rectangle with body-text lines (one text block)."""
    n = int(rect.width / (size * 0.5))
    words = (WORDS[seed % len(WORDS):] + WORDS * 40)
    text = " ".join(words)[: n * int(rect.height / (size * 1.2))]
    assert page.insert_textbox(rect, text, fontsize=size, fontname="tiro") >= 0, "prose overflow"


def chart(page, rect: fitz.Rect, label: str = "accuracy") -> None:
    """A bar chart with zero-width axis lines (the y axis is taller than every bar)."""
    page.draw_line((rect.x0, rect.y0), (rect.x0, rect.y1), color=(0, 0, 0), width=0)
    page.draw_line((rect.x0, rect.y1), (rect.x1, rect.y1), color=(0, 0, 0), width=0)
    n = 5
    for i in range(n):
        x = rect.x0 + 10 + i * (rect.width - 20) / n
        top = rect.y0 + 25 + 8 * i
        page.draw_rect(fitz.Rect(x, top, x + 12, rect.y1), color=None, fill=(0.2, 0.4, 0.8))
    page.insert_text((rect.x0 + 4, rect.y1 + 9), label, fontsize=6, fontname="helv")


def image(page, rect: fitz.Rect) -> None:
    w, h = 32, 24
    samples = bytes(((x * 8) % 256 if c == 0 else (y * 10) % 256 if c == 1 else 128)
                    for y in range(h) for x in range(w) for c in range(3))
    page.insert_image(rect, pixmap=fitz.Pixmap(fitz.csRGB, w, h, samples, False), keep_proportion=False)


def table(page, x0: float, y0: float, x1: float, rows: int = 4, size: float = 8) -> float:
    """Booktabs-style table: rules plus gapped numeric cells; returns the bottom y."""
    page.draw_line((x0, y0), (x1, y0), color=(0, 0, 0), width=0.8)
    cols = 4
    y = y0 + 4
    for r in range(rows):
        y += size * 1.4
        for c in range(cols):
            text = "Method" if (c == 0 and r == 0) else (f"M{r}" if c == 0 else f"{30 + r + c / 10:.2f}")
            page.insert_text((x0 + 4 + c * (x1 - x0) / cols, y), text, fontsize=size, fontname="helv")
        if r == 0:
            page.draw_line((x0, y + 3), (x1, y + 3), color=(0, 0, 0), width=0.5)
    page.draw_line((x0, y + 4), (x1, y + 4), color=(0, 0, 0), width=0.8)
    return y + 4


def caption(page, rect: fitz.Rect, text: str, size: float = 9) -> None:
    assert page.insert_textbox(rect, text, fontsize=size, fontname="tiro") >= 0, "caption overflow"


def new_doc(pages: int = 1, two_col: bool = True):
    """Document whose extra pages are plain body text (so the body size and text area are known)."""
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page(width=W, height=H)
        if i:
            cols = [fitz.Rect(54, 72, 300, 720), fitz.Rect(312, 72, 558, 720)] if two_col else [fitz.Rect(72, 72, 540, 720)]
            for j, r in enumerate(cols):
                prose(page, r, seed=i + j)
    return doc


def locate(doc, pno: int = 0) -> list[dict]:
    body = body_font_size(doc)
    return locate_on_page(doc[pno], body, text_extent(doc, body))


def one(found: list[dict], kind: str, number: str) -> dict:
    hits = [f for f in found if f["kind"] == kind and f["number"] == number]
    assert len(hits) == 1, f"{kind} {number}: {[(f['kind'], f['number']) for f in found]}"
    return hits[0]


def inside(region, rect: fitz.Rect, tol: float = 8) -> bool:
    return (region.x0 >= rect.x0 - tol and region.y0 >= rect.y0 - tol and region.x1 <= rect.x1 + tol
            and region.y1 <= rect.y1 + tol)


def covers(region, rect: fitz.Rect, tol: float = 3) -> bool:
    return (region.x0 <= rect.x0 + tol and region.y0 <= rect.y0 + tol and region.x1 >= rect.x1 - tol
            and region.y1 >= rect.y1 - tol)


def test_figure_above_caption_two_column() -> None:
    doc = new_doc(3)
    page = doc[0]
    fig = fitz.Rect(64, 180, 290, 300)
    prose(page, fitz.Rect(54, 72, 300, 170))
    chart(page, fig)
    caption(page, fitz.Rect(54, 315, 300, 345), "Figure 1. Accuracy of every method on the test split; higher is better.")
    prose(page, fitz.Rect(54, 352, 300, 720), seed=3)
    prose(page, fitz.Rect(312, 72, 558, 720), seed=5)
    f = one(locate(doc), "figure", "1")
    assert f["side"] == "above" and not f["full_width"], f
    assert covers(f["region"], fig), f"axis top or bars cut: {f['region']} vs {fig}"
    assert f["region"].x1 <= 306, f"region leaks into the right column: {f['region']}"
    m = measure(page, f["region"], f["caption_rect"])
    assert m["min_text_pt"] == 6.0 and m["raster_images"] == 0, m


def test_table_below_caption() -> None:
    doc = new_doc(3)
    page = doc[0]
    prose(page, fitz.Rect(54, 72, 300, 200))
    caption(page, fitz.Rect(54, 210, 300, 232), "Table 1. Results on the validation set. Best in bold.")
    bottom = table(page, 60, 240, 296)
    prose(page, fitz.Rect(54, bottom + 20, 300, 720), seed=2)
    prose(page, fitz.Rect(312, 72, 558, 720), seed=4)
    t = one(locate(doc), "table", "1")
    assert t["side"] == "below", t
    assert covers(t["region"], fitz.Rect(60, 240, 296, bottom)), t["region"]
    assert t["region"].y1 <= bottom + 8, f"table region runs into prose: {t['region']}"


def test_full_width_figure() -> None:
    doc = new_doc(3)
    page = doc[0]
    fig = fitz.Rect(60, 80, 552, 260)
    image(page, fitz.Rect(60, 80, 300, 260))
    image(page, fitz.Rect(312, 80, 552, 260))
    caption(page, fitz.Rect(54, 270, 558, 292), "Figure 2: Qualitative comparison of all methods on two scenes of the dataset.")
    prose(page, fitz.Rect(54, 305, 300, 720), seed=1)
    prose(page, fitz.Rect(312, 305, 558, 720), seed=6)
    f = one(locate(doc), "figure", "2")
    assert f["full_width"] and covers(f["region"], fig), f
    assert measure(page, f["region"], f["caption_rect"])["raster_images"] == 2


def test_two_column_figure_with_one_column_caption() -> None:
    doc = new_doc(3)
    page = doc[0]
    fig = fitz.Rect(60, 80, 552, 240)
    image(page, fig)
    caption(page, fitz.Rect(54, 250, 300, 280), "Figure 3. A wide teaser whose caption sits in the left column only.")
    prose(page, fitz.Rect(54, 290, 300, 720), seed=1)
    prose(page, fitz.Rect(312, 250, 558, 720), seed=6)
    f = one(locate(doc), "figure", "3")
    assert covers(f["region"], fig), f"wide figure cut to one column: {f['region']}"


def test_adjacent_figure_and_table() -> None:
    """Figure graphics, figure caption, table caption, table: each caption gets its own content."""
    doc = new_doc(3)
    page = doc[0]
    fig = fitz.Rect(64, 80, 290, 200)
    chart(page, fig)
    caption(page, fitz.Rect(54, 215, 300, 237), "Figure 4. Training loss over time for all models.")
    caption(page, fitz.Rect(54, 245, 300, 267), "Table 2. Ablation of each component on the test set.")
    bottom = table(page, 60, 274, 296)
    prose(page, fitz.Rect(54, bottom + 20, 300, 720), seed=2)
    prose(page, fitz.Rect(312, 72, 558, 720), seed=4)
    found = locate(doc)
    f, t = one(found, "figure", "4"), one(found, "table", "2")
    assert f["side"] == "above" and covers(f["region"], fig), f
    assert t["side"] == "below" and t["region"].y0 >= 237, t
    assert not f["region"].intersects(t["region"]), (f["region"], t["region"])


def test_table_with_caption_below() -> None:
    doc = new_doc(3)
    page = doc[0]
    prose(page, fitz.Rect(54, 72, 300, 150))
    bottom = table(page, 60, 165, 296)
    caption(page, fitz.Rect(54, bottom + 8, 300, bottom + 30), "Table 3: Runtime per image; captions below tables.")
    prose(page, fitz.Rect(54, bottom + 40, 300, 720), seed=2)
    prose(page, fitz.Rect(312, 72, 558, 720), seed=4)
    t = one(locate(doc), "table", "3")
    assert t["side"] == "above" and covers(t["region"], fitz.Rect(60, 165, 296, bottom)), t


def test_caption_continuation_block() -> None:
    doc = new_doc(3)
    page = doc[0]
    chart(page, fitz.Rect(64, 80, 290, 200))
    lines = ("Figure 5. First part of a long justified caption that", "wraps over two lines of the left column here and",
             "continues in a second text block that has the same", "edges as the first block above it in this column.")
    for y, text in zip((225, 236, 250, 261), lines):  # the wider gap makes MuPDF start a second block
        page.insert_text((54, y), text, fontsize=9, fontname="tiro")
    starts = [b["lines"][0]["spans"][0]["text"] for b in page.get_text("dict")["blocks"] if b.get("lines")]
    assert any(s.startswith("continues") for s in starts), "precondition: the caption must span two blocks"
    prose(page, fitz.Rect(54, 280, 300, 720), seed=2)
    prose(page, fitz.Rect(312, 72, 558, 720), seed=4)
    f = one(locate(doc), "figure", "5")
    assert "same edges" in f["caption"] and f["caption_rect"].y1 >= 250, f["caption"]


def test_caption_inside_label_block() -> None:
    """A caption line in the same text block as the panel labels above it (not at the block start)."""
    doc = new_doc(3)
    page = doc[0]
    for i, x in enumerate((64, 140, 216)):
        image(page, fitz.Rect(x, 90, x + 70, 150))
        page.insert_text((x + 20, 158), ("GT", "Ours", "Baseline")[i], fontsize=6.5, fontname="tiro")
    page.insert_text((80, 168), "Figure 9. Qualitative comparisons on the test images.", fontsize=9, fontname="tiro")
    prose(page, fitz.Rect(54, 190, 300, 720), seed=2)
    prose(page, fitz.Rect(312, 72, 558, 720), seed=4)
    starts = [b["lines"][0]["spans"][0]["text"] for b in page.get_text("dict")["blocks"] if b.get("lines")]
    assert not any(s.startswith("Figure 9") for s in starts), "precondition: caption must not start a block"
    f = one(locate(doc), "figure", "9")
    assert f["caption"].startswith("Figure 9") and covers(f["region"], fitz.Rect(64, 90, 286, 150)), f


def test_measure_subcaptions_scripts_and_rasters() -> None:
    """Sub-captions are not figure text, subscripts are reported apart, raster-heavy crops are flagged."""
    doc = new_doc(3)
    page = doc[0]
    plot = fitz.Rect(70, 90, 290, 190)
    chart(page, plot)
    for i, x in enumerate(range(80, 290, 40)):  # tick labels at 5 pt
        page.insert_text((x, plot.y1 + 18), f"{i * 0.2:.1f}", fontsize=5, fontname="helv")
    page.insert_text((60, 120), "w", fontsize=6, fontname="helv")  # axis symbol with a 3.5 pt subscript
    page.insert_text((64, 121.5), "0", fontsize=3.5, fontname="helv")
    page.insert_text((140, 222), "(a) Training curve", fontsize=8, fontname="tiro")
    caption(page, fitz.Rect(54, 232, 300, 254), "Figure 7. Loss and a photo of the scene.")
    photo = fitz.Rect(64, 290, 290, 420)
    image(page, photo)
    page.insert_text((150, 432), "(b) Scene", fontsize=8, fontname="tiro")
    caption(page, fitz.Rect(54, 442, 300, 464), "Figure 8. The capture setup used for every sequence.")
    prose(page, fitz.Rect(54, 480, 300, 720), seed=2)
    prose(page, fitz.Rect(312, 72, 558, 720), seed=4)
    found = locate(doc)
    f7, f8 = one(found, "figure", "7"), one(found, "figure", "8")
    m7 = measure(page, f7["region"], f7["caption_rect"])
    assert m7["min_text_pt"] == 5.0 and m7["min_script_pt"] == 3.5, m7
    assert m7["text_not_measured"] is False and m7["images"] == [] and m7["raster_images"] == 0, m7
    m8 = measure(page, f8["region"], f8["caption_rect"])
    assert m8["text_not_measured"] is True and m8["min_text_pt"] is None, m8  # only a sub-caption: unmeasured
    assert len(m8["images"]) == 1 and m8["images"][0]["ppi"] == m8["min_image_ppi"] == round(32 / (photo.width / 72))
    assert covers(fitz.Rect(m8["images"][0]["bbox_pt"]), photo, tol=1), m8["images"]


def test_review_line_numbers() -> None:
    doc = new_doc(3)
    page = doc[0]
    for i, y in enumerate(range(84, 720, 12)):
        page.insert_text((30, y), f"{i + 1:03d}", fontsize=7, fontname="helv")
        page.insert_text((566, y), f"{i + 1:03d}", fontsize=7, fontname="helv")
    prose(page, fitz.Rect(54, 72, 300, 170))
    fig = fitz.Rect(64, 180, 290, 300)
    chart(page, fig)
    caption(page, fitz.Rect(54, 315, 300, 345), "Figure 6. Per-class error under the review layout.")
    prose(page, fitz.Rect(54, 352, 300, 720), seed=3)
    prose(page, fitz.Rect(312, 72, 558, 720), seed=5)
    f = one(locate(doc), "figure", "6")
    assert covers(f["region"], fig) and f["region"].x0 >= 50, f["region"]
    assert not any(ch.isdigit() for ch in f["caption"][len("Figure 6"):]), f"line number in caption: {f['caption']}"


def test_side_by_side_tables_in_one_column() -> None:
    doc = new_doc(3, two_col=False)
    page = doc[0]
    prose(page, fitz.Rect(72, 72, 540, 150))
    caption(page, fitz.Rect(72, 160, 296, 182), "Table 4: Accuracy on the first benchmark.")
    caption(page, fitz.Rect(316, 160, 540, 182), "Table 5: Accuracy on the second benchmark.")
    b1 = table(page, 76, 190, 292)
    table(page, 320, 190, 536)
    prose(page, fitz.Rect(72, b1 + 20, 540, 720), seed=2)
    found = locate(doc)
    t4, t5 = one(found, "table", "4"), one(found, "table", "5")
    assert inside(t4["region"], fitz.Rect(72, 185, 300, b1)) and inside(t5["region"], fitz.Rect(312, 185, 540, b1)), \
        (t4["region"], t5["region"])


def test_single_column_short_caption() -> None:
    """A short left-aligned caption in a one-column paper spans the whole text width."""
    doc = new_doc(3, two_col=False)
    page = doc[0]
    prose(page, fitz.Rect(72, 72, 540, 150))
    caption(page, fitz.Rect(72, 158, 250, 174), "Table 6. Overview.")
    bottom = table(page, 80, 180, 532)
    prose(page, fitz.Rect(72, bottom + 20, 540, 720), seed=2)
    t = one(locate(doc), "table", "6")
    assert t["full_width"] and covers(t["region"], fitz.Rect(80, 180, 532, bottom)), t


def test_appendix_and_roman_numbering() -> None:
    doc = new_doc(3, two_col=False)
    page = doc[0]
    chart(page, fitz.Rect(90, 80, 520, 200))
    caption(page, fitz.Rect(72, 215, 540, 237), "Figure A1: Additional results in the appendix.")
    caption(page, fitz.Rect(72, 250, 540, 272), "Table S2. Supplementary hyperparameters.")
    bottom = table(page, 80, 280, 532)
    caption(page, fitz.Rect(72, bottom + 15, 540, bottom + 37), "TABLE IV")
    table(page, 80, bottom + 45, 532)
    found = locate(doc)
    assert one(found, "figure", "A1")["region"] is not None
    assert one(found, "table", "S2")["region"] is not None
    assert one(found, "table", "IV")["region"] is not None


def test_orphan_caption_has_no_region() -> None:
    doc = new_doc(3)
    page = doc[0]
    prose(page, fitz.Rect(54, 72, 300, 300))
    caption(page, fitz.Rect(54, 308, 300, 328), "Table 7. A caption whose table is on another page.")
    prose(page, fitz.Rect(54, 335, 300, 720), seed=2)
    prose(page, fitz.Rect(312, 72, 558, 720), seed=4)
    assert one(locate(doc), "table", "7")["region"] is None


def test_page_without_figures_and_scan() -> None:
    doc = new_doc(3)
    assert locate(doc, 1) == []
    scan = fitz.open()
    image(scan.new_page(width=W, height=H), fitz.Rect(0, 0, W, H))
    assert body_font_size(scan) == 10.0 and locate(scan) == []


def test_rotated_page_sideways_table() -> None:
    """A landscape table on a page with /Rotate 90: located, and returned in page.rect coordinates."""
    src = fitz.open()
    land = src.new_page(width=H, height=W)
    land.insert_text((100, 100), "Table 8. A sideways table with many columns.", fontsize=9, fontname="tiro")
    for r in range(5):
        for c in range(6):
            land.insert_text((110 + c * 90, 130 + r * 14), f"{r}.{c}5", fontsize=8, fontname="helv")
    for y in (118, 205):
        land.draw_line((100, y), (650, y), color=(0, 0, 0), width=0.6)
    doc = new_doc(3)
    page = doc[0]
    page.show_pdf_page(page.rect, src, 0, rotate=90)  # content drawn sideways on a portrait page ...
    page.set_rotation(90)  # ... and the page turned so it displays upright
    assert page.get_text("dict")["blocks"][0]["lines"][0]["dir"] == (0.0, -1.0), "precondition: vertical text"
    t = one(locate(doc), "table", "8")
    assert t["side"] == "below" and t["region"] in page.rect, t
    assert covers(t["region"], fitz.Rect(100, 118, 650, 205)), f"not in displayed coordinates: {t['region']}"
    assert covers(t["caption_rect"], fitz.Rect(102, 93, 260, 100)), t["caption_rect"]
    assert measure(page, t["region"], t["caption_rect"])["min_text_pt"] == 8.0


def main() -> None:
    tests = [v for k, v in globals().items() if k.startswith("test_") and callable(v)]
    for test in tests:
        test()
        print(f"  {test.__name__}: ok")
    print(f"OK ({len(tests)} figure-locator cases)")


if __name__ == "__main__":
    main()
