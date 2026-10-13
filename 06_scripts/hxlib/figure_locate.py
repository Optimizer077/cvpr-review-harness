"""Locate figures and tables on PDF pages from their captions, and measure what a reader sees.

A figure is found from its caption ("Figure 3.", "Fig. 3:", "Table 2.", "Figure S1:", "Table A.2",
"TABLE IV"), also when the caption starts inside a text block. The content region is the union
of graphics (images, vector paths, labels, tabular text) on one side of the caption that are
contiguous with it, inside the caption's cell (its column, narrowed by side-by-side captions or
wrapped prose) and not past a wall (prose, a numbered heading, a running header, another caption).
Figure labels, table header rows, code listings and text inside boxes or images are content.
Captions of one kind are assigned jointly: the most captions get disjoint regions (a region
between two captions goes to the one with no other choice), then the best score (width coverage,
distance, and the CVPR convention of figure captions below and table captions above). Figures
claim their graphics before tables. Pages are read in the frame where their text is horizontal
(rotated pages, sideways tables) and regions are returned in `page.rect` coordinates, as
`Page.get_pixmap(clip=...)` expects. Review-copy line numbers are ignored; pages without a text
layer (scans) yield nothing. Tested on CVPR/ICCV, ECCV (LNCS), NeurIPS, ICLR, TMLR, AAAI, IEEE,
SIGGRAPH and arXiv layouts, with supplements and appendices. Text and graphics primitives
(blocks in the reading frame, caption labels, line numbers, boxes) live in `figure_layout`.
"""
from __future__ import annotations

import itertools
import logging
import re
import statistics
from collections import Counter
from typing import TYPE_CHECKING, Optional

from .figure_layout import (CAPTION, HEADING, block_info, describe, doc_single_column, graphics, is_identity,
                            layout_blocks, line_text, merge_caption_continuations, text_dict)

if TYPE_CHECKING:
    import fitz

__all__ = ["CAPTION", "block_info", "body_font_size", "text_extent", "locate_on_page", "measure"]
logger = logging.getLogger(__name__)

GAP_PT = 24.0          # a larger vertical gap between graphics ends a figure
FIRST_GAP_PT = 40.0    # the content must start this close to its caption
COLUMN_SLACK_PT = 6.0  # graphics may overhang their column by this much
MAX_COMBOS = 5000      # joint caption assignment is exhaustive up to this many combinations
_SUBCAPTION = re.compile(r"^\(?[a-z]\)\s")  # "(a) Image representation", "b) ..."


def body_font_size(doc) -> float:
    """Most common body size weighted by characters, in 0.5 pt bins (micro-text in figures ignored)."""
    bins: Counter = Counter()
    exact: dict[float, Counter] = {}
    for page in doc:
        for block in text_dict(page)["blocks"]:
            for line in block.get("lines", []):
                for span in line["spans"]:
                    n = len(span["text"].strip())
                    if n and span["size"] >= 4.5:
                        key = round(span["size"] * 2) / 2
                        bins[key] += n
                        exact.setdefault(key, Counter())[round(span["size"], 1)] += n
    return exact[bins.most_common(1)[0][0]].most_common(1)[0][0] if bins else 10.0


def text_extent(doc, body: float) -> tuple[float, float, float, float]:
    """(left, top, right, bottom) of body paragraphs over the document, margin numbers excluded."""
    import fitz

    rects = []
    for page in doc:
        blocks, m = layout_blocks(page)
        if not is_identity(m):
            continue  # sideways pages do not define the portrait text area
        lines = []
        for block in blocks:
            info = block_info(block)
            if info["lineno"] or abs(info["size"] - body) > 0.6:
                continue
            if info["lines"] >= 3:
                rects.append(info["rect"])
            lines += [fitz.Rect(ln["bbox"]) for ln in block["lines"] if len(line_text(ln)) >= 30]
        lines.sort(key=lambda r: r.y0)  # double-spaced text: one-line blocks with close neighbours
        rects += [r for i, r in enumerate(lines) if any(
            0 < abs(o.y0 - r.y0) <= 2.6 * body and min(o.x1, r.x1) - max(o.x0, r.x0) > 0.5 * r.width
            for o in lines[max(i - 2, 0):i + 3])]
    if not rects:
        r = doc[0].rect
        return (r.x0, r.y0, r.x1, r.y1)
    return (min(r.x0 for r in rects), min(r.y0 for r in rects), max(r.x1 for r in rects),
            max(r.y1 for r in rects))


class _Page:
    """Per-page layout facts shared by all captions on the page, in the reading frame."""

    def __init__(self, page, body: float, extent: tuple[float, float, float, float]) -> None:
        self.page, self.body = page, body
        raw, self.m = layout_blocks(page)
        self.rect = page.rect * page.derotation_matrix * self.m
        blocks = [b for b in (describe(x) for x in raw) if b["text"]]
        self.blocks = merge_caption_continuations(blocks)
        self.caps = [b for b in self.blocks if b["cap"]]
        self.images, self.drawings, self.boxes = graphics(page, self.m) if self.caps else ([], [], [])
        self.left, self.top, self.right, self.bottom = extent
        rects = [b["rect"] for b in blocks if not b["lineno"]] + self.images + self.drawings
        if not is_identity(self.m) and rects:  # sideways page: its own content area
            self.left, self.top = min(r.x0 for r in rects), min(r.y0 for r in rects)
            self.right, self.bottom = max(r.x1 for r in rects), max(r.y1 for r in rects)
        self.mid = (self.left + self.right) / 2
        self._single: Optional[bool] = None

    @property
    def single(self) -> bool:
        """Whether the page is set in one column (body prose runs across the text width)."""
        if self._single is None:
            width = self.right - self.left
            prose = [b["rect"].width for b in self.blocks if b["rows"] >= 2 and b["prose"] and not b["cap"]
                     and abs(b["size"] - self.body) <= 0.6 and not self.in_graphic(b["rect"])]
            wide, narrow = sum(w >= 0.65 * width for w in prose), sum(w <= 0.55 * width for w in prose)
            self._single = wide > narrow if wide != narrow else doc_single_column(self.page, width)
        return self._single

    def has_graphics(self, region) -> bool:
        """Whether a region holds an image, a vector path or tabular text (not only prose)."""
        return (any((r & region).get_area() > 0 for r in self.images + self.drawings)
                or any(b["tabular"] and region.contains(b["rect"]) for b in self.blocks))

    def in_graphic(self, r) -> bool:
        """Text drawn over an image or inside a box (prompt panels, framed listings)."""
        return (any((r & im).get_area() > 0.3 * max(r.get_area(), 1) for im in self.images)
                or any((bx + (-2, -2, 2, 2)).contains(r) for bx in self.boxes))

    def is_wall(self, b: dict, span_w: float, x0: float, for_figure: bool) -> bool:
        """Text that bounds a figure: prose, numbered headings, running headers, other captions."""
        if b["lineno"]:
            return False
        if b["cap"] or b["rect"].y1 < self.top - 2 or b["rect"].y0 > self.bottom + 2:
            return True
        if b["rect"].x0 < x0 - 0.25 * span_w or b["rect"].x1 > x0 + 1.25 * span_w:
            return True  # text running far out of the cell belongs to something else
        if b["tabular"]:  # a table next to a figure; two rows of words are panel titles, not a table
            return (for_figure and b["size"] >= self.body - 1.5
                    and (b["rows"] >= 3 or (b["gapped_rows"] >= 2 and b["digits"] >= 0.4)))
        if b["mono"] or b["vertical"] or self.in_graphic(b["rect"]):
            return False  # listings, axis labels, text in boxes or images
        min_size = self.body - (2.5 if HEADING.match(b["text"]) else 0.6)  # numbered small caps
        if (b["heading"] and abs(b["rect"].x0 - x0) <= 12 and b["size"] >= min_size
                and b["rect"].width > 2 * b["rect"].height
                and not any(b["rect"].intersects(g) for g in self.boxes + self.images)):
            return True  # section heading at the column edge (not a label on a diagram)
        if b["size"] < self.body - 0.6 or not b["prose"]:
            return False  # labels, table header rows, equations
        if b["rows"] >= 2:
            return b["rect"].width >= 0.25 * span_w or b["rows"] >= 3
        return b["rect"].width >= 0.5 * span_w and b["rect"].x0 - x0 <= 20

    def right_wrap(self, cap: dict) -> bool:
        """A narrow caption at the right margin of a one-column page: a wrapped figure or table."""
        cr, width = cap["rect"], self.right - self.left
        return self.single and cr.width < 0.6 * width and (cr.x0 + cr.x1) / 2 > self.mid + 0.15 * width

    def cell(self, cap: dict) -> tuple[float, float, bool]:
        """(x0, x1, full_width) for a caption: its column, narrowed by text beside the caption."""
        cr = cap["rect"]
        full = self.single or (cr.x0 < self.mid - 10 and cr.x1 > self.mid + 10)
        x0, x1 = ((self.left, self.right) if full else
                  (self.left, self.mid) if cr.x1 <= self.mid + 10 else (self.mid, self.right))
        if self.right_wrap(cap):
            x0 = max(self.left, cr.x0 - 0.1 * (self.right - self.left))
        for b in self.blocks:
            if b is cap or b["lineno"]:
                continue
            para = b["prose"] and b["rows"] >= 2 and abs(b["size"] - self.body) <= 0.6
            for r in b["line_rects"]:  # lines, so text wrapped around a figure counts
                overlap = min(r.y1, cr.y1) - max(r.y0, cr.y0)
                if overlap <= 2 and not (para and overlap > -14):
                    continue
                if x0 < r.x1 <= cr.x0 + 1:
                    x0 = r.x1 + 2
                elif cr.x1 - 1 <= r.x0 < x1:
                    x1 = r.x0 - 2
        return x0, x1, full

    def side(self, cap: dict, side: str, x0: float, x1: float, strict: bool,
             claimed: list) -> Optional[fitz.Rect]:
        """Content region on one side of a caption within [x0, x1], or None."""
        import fitz

        span_w = x1 - x0
        for_fig = cap["cap"][0] == "figure" and strict

        def overlaps(r) -> bool:
            return min(r.x1, x1) - max(r.x0, x0) > 0.3 * max(min(r.width, span_w), 1)

        others = [b for b in self.blocks if b is not cap]
        walls = [r for b in others if overlaps(b["rect"]) and self.is_wall(b, span_w, x0, for_fig)
                 for r in (b["line_rects"] if b["rows"] >= 2 and not b["cap"] else [b["rect"]]) if overlaps(r)]
        edge = cap["rect"].x0 if self.right_wrap(cap) else -1e9  # wrapped: nothing wholly left of it

        def free(r) -> bool:
            return r.x1 > edge and not any((r & c).get_area() > 0.5 * max(r.get_area(), 0.1) for c in claimed)

        prims = [r for r in self.drawings if free(r)]
        prims += [b["rect"] for b in others if not b["lineno"] and free(b["rect"])
                  and not self.is_wall(b, span_w, x0, for_fig)]
        imgs = [r for r in self.images if free(r & self.rect)]
        reg = _grow(cap["rect"], side, x0, x1, walls, prims, imgs, self.rect)
        if reg is None:
            return None
        return fitz.Rect(max(reg.x0, x0 - COLUMN_SLACK_PT), max(reg.y0, self.top - 12),
                         min(reg.x1, x1 + COLUMN_SLACK_PT), min(reg.y1, self.bottom + 12))

    def candidates(self, cap: dict, claimed: list) -> list[tuple]:
        """(score, side, region) for each side of a caption that holds graphics."""
        import fitz

        x0, x1, full = self.cell(cap)
        conventional = "above" if cap["cap"][0] == "figure" else "below"
        reach = 0.3 * (self.right - self.left) / 2
        for strict in (True, False):
            found = []
            for side in ("above", "below"):
                lo, hi = x0, x1
                reg = self.side(cap, side, lo, hi, strict, claimed)
                cr = cap["rect"]
                near = (fitz.Rect(x0, cr.y0 - FIRST_GAP_PT, x1, cr.y0) if side == "above"
                        else fitz.Rect(x0, cr.y1, x1, cr.y1 + FIRST_GAP_PT))
                probe = reg or near
                if not full and any(  # a two-column figure with a one-column caption
                        r.x0 < self.mid - reach and r.x1 > self.mid + reach and r.intersects(probe)
                        and (reg is None or (r.y0 >= reg.y0 - 2 and r.y1 <= reg.y1 + 2))
                        for r in self.images + self.drawings):
                    lo, hi = self.left, self.right
                    reg = self.side(cap, side, lo, hi, strict, claimed) or reg
                if reg is None or not self.has_graphics(reg):
                    continue
                gap = (cap["rect"].y0 - reg.y1) if side == "above" else (reg.y0 - cap["rect"].y1)
                score = (min(reg.width / max(hi - lo, 1), 1.0) + (0.15 if side == conventional else 0)
                         - max(gap, 0) / 200)
                found.append((score, side, reg))
            if found:
                return found
        return []


def _grow(cr, side: str, x0: float, x1: float, walls: list, prims: list, images: list,
          page_rect) -> Optional[fitz.Rect]:
    """Union of primitives contiguous with the caption on one side; None if nothing is there."""
    import fitz

    def in_span(r) -> bool:
        return min(r.x1, x1 + COLUMN_SLACK_PT) - max(r.x0, x0 - COLUMN_SLACK_PT) >= 0.7 * max(r.width, 0.1)

    if side == "above":
        top = max([w.y1 for w in walls if w.y1 <= cr.y0 + 1] + [page_rect.y0])
        band = fitz.Rect(x0 - COLUMN_SLACK_PT, top, x1 + COLUMN_SLACK_PT, cr.y0 + 2)
    else:
        bot = min([w.y0 for w in walls if w.y0 >= cr.y1 - 1] + [page_rect.y1])
        band = fitz.Rect(x0 - COLUMN_SLACK_PT, cr.y1 - 2, x1 + COLUMN_SLACK_PT, bot)
    cands = [r for r in prims if in_span(r) and band.contains(r)]
    cands += [r & band for r in images if (r & band).width > 3 and (r & band).height > 3]
    if side == "above":
        cands.sort(key=lambda r: -r.y1)
    else:
        cands.sort(key=lambda r: r.y0)
    edge, gap, region = (cr.y0 if side == "above" else cr.y1), FIRST_GAP_PT, None
    for r in cands:
        if (side == "above" and r.y1 < edge - gap) or (side == "below" and r.y0 > edge + gap):
            break
        region = fitz.Rect(r) if region is None else region | r
        edge = min(edge, r.y0) if side == "above" else max(edge, r.y1)
        gap = GAP_PT
    return region if region is not None and region.height >= 8 else None


def _assign(options: list[list[tuple]]) -> list[Optional[tuple]]:
    """One candidate or None per caption: most captions with disjoint regions, then highest score."""
    def clash(a, b) -> bool:
        return (a & b).get_area() > 0.3 * max(min(a.get_area(), b.get_area()), 1)

    choices = [opts + [None] for opts in options]
    combos = 1
    for c in choices:
        combos *= len(c)
    if combos > MAX_COMBOS:  # greedy: captions in reading order take their best free candidate
        picked: list[Optional[tuple]] = []
        for opts in options:
            picked.append(next((o for o in sorted(opts, key=lambda o: -o[0])
                                if not any(p and clash(o[2], p[2]) for p in picked)), None))
        return picked
    best, key = [None] * len(options), (-1, 0.0)
    for combo in itertools.product(*choices):
        chosen = [c for c in combo if c]
        k = (len(chosen), round(sum(c[0] for c in chosen), 6))
        if k > key and not any(clash(a[2], b[2]) for a, b in itertools.combinations(chosen, 2)):
            best, key = list(combo), k
    return best


def locate_on_page(page, body: float, extent: tuple[float, float, float, float]) -> list[dict]:
    """Every captioned figure/table on a page with its content region (None if not located)."""
    ctx = _Page(page, body, extent)
    out_m = ~ctx.m * page.rotation_matrix  # reading frame -> page.rect coordinates
    claimed: list = []
    found = []
    for kind in ("figure", "table"):
        group = [c for c in ctx.caps if c["cap"][0] == kind]
        picks = _assign([ctx.candidates(c, claimed) for c in group])
        for cap, pick in zip(group, picks):
            region = side = None
            if pick:
                _, side, region = pick
                claimed.append(region)
                region = region * out_m
            found.append({"kind": kind, "number": cap["cap"][1], "caption": cap["text"],
                          "caption_rect": cap["rect"] * out_m, "region": region, "side": side,
                          "full_width": ctx.cell(cap)[2]})
    if not is_identity(ctx.m) and found:
        logger.debug("page %d read in a turned frame (rotation %d)", page.number + 1, page.rotation)
    return sorted(found, key=lambda f: (f["caption_rect"].y0, f["caption_rect"].x0))


def measure(page, region, caption_rect) -> dict:
    """Vector text sizes inside the region (caption excluded) and raster image resolution.

    Panel sub-captions ("(a) ...") are not figure text and are skipped. Spans smaller than ~0.8x the
    dominant text size on and touching their line are sub/superscripts, reported as `min_script_pt`.
    `text_not_measured` is True when rasters cover over 30% of the region or no text is left, so
    the size facts may miss text drawn inside images or as outlines. `images` lists each raster.
    """
    import fitz

    region, caption_rect = fitz.Rect(region), fitz.Rect(caption_rect)
    if page.rotation:  # regions are in page.rect coordinates; text and images are not rotated
        region, caption_rect = region * page.derotation_matrix, caption_rect * page.derotation_matrix
    lines = []  # (line rect, characters per size, spans inside the region)
    for block in text_dict(page, clip=region)["blocks"]:
        sub = None  # (bottom, size) of the sub-caption line above, so its wrapped lines are skipped too
        for line in block.get("lines", []):
            spans = [s for s in line["spans"] if s["text"].strip()]
            if not spans:
                continue
            size, box = max(s["size"] for s in spans), fitz.Rect(line["bbox"])
            if _SUBCAPTION.match(line_text(line)) or (
                    sub and abs(size - sub[1]) <= 0.3 and -1 <= box.y0 - sub[0] <= 0.6 * size):
                sub = (box.y1, size)
                continue
            sub = None
            chars: Counter = Counter()
            for s in spans:
                chars[round(s["size"], 1)] += len(s["text"].strip())
            inside = [s for s in spans if fitz.Rect(s["bbox"]).intersects(region)
                      and not fitz.Rect(s["bbox"]).intersects(caption_rect)]
            lines.append((box, chars, inside))
    lines.sort(key=lambda t: t[0].y0)
    sizes, scripts = [], []
    for i, (rect, _, inside) in enumerate(lines):  # reference: the size with most characters around the line
        near: Counter = Counter()
        for r, c, _ in lines[max(i - 8, 0):i + 9]:
            if (r + (-1, -1, 1, 1)).intersects(rect):
                near.update(c)
        ref = max(near.items(), key=lambda kv: (kv[1], kv[0]))[0]
        for s in inside:
            (scripts if s["size"] < 0.82 * ref else sizes).append(round(s["size"], 1))
    images, covered = [], 0.0
    for info in page.get_image_info():
        full = fitz.Rect(info["bbox"])
        if (full & region).width > 10 and (full & region).height > 10 and full.width > 0:
            covered += (full & region).get_area()
            images.append({"bbox_pt": [round(v, 1) for v in full * page.rotation_matrix],
                           "ppi": round(info["width"] / (full.width / 72))})
    ppi = [i["ppi"] for i in images]
    return {"vector_text_spans": len(sizes), "min_text_pt": min(sizes) if sizes else None,
            "median_text_pt": statistics.median(sizes) if sizes else None,
            "min_script_pt": min(scripts) if scripts else None,
            "text_not_measured": covered > 0.3 * region.get_area() or not sizes,
            "raster_images": len(ppi), "min_image_ppi": min(ppi) if ppi else None, "images": images}
