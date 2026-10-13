"""Locate figures and tables on PDF pages from their captions, and measure what a reader sees.

A figure is found from its caption ("Figure 3.", "Fig. 3:", "Table 2."): the content region is the
union of graphics (images, vector paths, small or tabular text) on one side of the caption that
are contiguous with it, inside the caption's column, and not past a wall (a prose paragraph,
heading, running header or another caption). Figures claim their graphics before tables. Both
sides are scored by width coverage and distance; the CVPR convention (figure captions below,
table captions above) breaks ties. Tested on CVPR, ECCV (LNCS), NeurIPS and SIGGRAPH layouts.
"""
from __future__ import annotations

import logging
import re
import statistics
from collections import Counter
from typing import Optional

logger = logging.getLogger(__name__)

CAPTION = re.compile(r"^\s*(Figure|Fig\.|Table)\s*(S?\d+)\s*[.:|]")
_LINE_NO = re.compile(r"^\d{3,4}$")
GAP_PT = 24.0          # a larger vertical gap between graphics ends a figure
FIRST_GAP_PT = 40.0    # the content must start this close to its caption
COLUMN_SLACK_PT = 6.0  # graphics may overhang their column by this much


def _rows(spans: list[dict]) -> list[list[dict]]:
    """Group spans into visual rows by baseline; superscripts join their row."""
    rows: list[list[dict]] = []
    for span in sorted(spans, key=lambda s: s["origin"][1]):
        if rows and span["origin"][1] - rows[-1][0]["origin"][1] <= 0.6 * max(span["size"], 1):
            rows[-1].append(span)
        else:
            rows.append([span])
    return rows


def _gapped(row: list[dict]) -> bool:
    row = sorted(row, key=lambda s: s["bbox"][0])
    return any(b["bbox"][0] - a["bbox"][2] > 1.5 * max(a["size"], 1) for a, b in zip(row, row[1:]))


def _char_median_size(spans: list[dict]) -> float:
    """Median font size weighted by characters (small caps and symbols do not skew it)."""
    weighted = sorted((s["size"], len(s["text"].strip())) for s in spans)
    half, acc = sum(n for _, n in weighted) / 2, 0
    for size, n in weighted:
        acc += n
        if acc >= half:
            return size
    return 0.0


def block_info(block: dict) -> dict:
    """Text block summary: rect, text, size, rows, and whether it is tabular or a line number."""
    import fitz

    spans = [s for ln in block.get("lines", []) for s in ln["spans"] if s["text"].strip()]
    rows = _rows(spans)
    gapped = sum(_gapped(r) for r in rows)
    return {"rect": fitz.Rect(block["bbox"]), "text": " ".join(s["text"].strip() for s in spans),
            "lines": len(block.get("lines", [])), "rows": len(rows), "size": _char_median_size(spans),
            "tabular": bool(rows) and gapped >= 0.5 * len(rows),
            "lineno": bool(spans) and all(_LINE_NO.match(s["text"].strip()) for s in spans)}


def body_font_size(doc) -> float:
    """Most common span size weighted by characters: the body text size."""
    sizes: Counter = Counter()
    for page in doc:
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                for span in line["spans"]:
                    sizes[round(span["size"], 1)] += len(span["text"].strip())
    return sizes.most_common(1)[0][0] if sizes else 10.0


def text_extent(doc, body: float) -> tuple[float, float, float, float]:
    """(left, top, right, bottom) of body paragraphs over the document, margin numbers excluded."""
    rects = []
    for page in doc:
        for block in page.get_text("dict")["blocks"]:
            info = block_info(block)
            if info["lines"] >= 3 and abs(info["size"] - body) <= 0.6 and not info["lineno"]:
                rects.append(info["rect"])
    if not rects:
        r = doc[0].rect
        return (r.x0, r.y0, r.x1, r.y1)
    return (min(r.x0 for r in rects), min(r.y0 for r in rects), max(r.x1 for r in rects),
            max(r.y1 for r in rects))


def _graphics(page) -> tuple[list, list]:
    """(images, drawings) rectangles on the page; page-sized backgrounds dropped."""
    import fitz

    pr = page.rect
    images = [fitz.Rect(i["bbox"]) for i in page.get_image_info()]
    images = [r for r in images if (r & pr).width > 3 and (r & pr).height > 3]
    drawings = []
    for path in page.get_drawings():
        r = fitz.Rect(path["rect"]) & pr
        if r.width > 0.9 * pr.width and r.height > 0.9 * pr.height:
            continue
        if r.width > 0.5 or r.height > 0.5:
            drawings.append(fitz.Rect(r.x0, r.y0 - 0.5, r.x1, r.y1 + 0.5) if r.height < 1 else r)
    return images, drawings


def _merge_caption_continuations(blocks: list[dict]) -> list[dict]:
    """A block right under a caption with the same left and right edges continues that caption."""
    out: list[dict] = []
    for b in sorted(blocks, key=lambda x: (x["rect"].y0, x["rect"].x0)):
        prev = next((c for c in reversed(out) if CAPTION.match(c["text"])), None)
        if (prev is not None and not CAPTION.match(b["text"]) and 0 <= b["rect"].y0 - prev["rect"].y1 <= 3
                and abs(b["rect"].x0 - prev["rect"].x0) <= 4 and abs(b["rect"].x1 - prev["rect"].x1) <= 4):
            prev["rect"] = prev["rect"] | b["rect"]
            prev["text"] += " " + b["text"]
            prev["lines"] += b["lines"]
            continue
        out.append(b)
    return out


class _Page:
    """Per-page layout facts shared by all captions on the page."""

    def __init__(self, page, body: float, extent: tuple[float, float, float, float]):
        self.page, self.body = page, body
        self.left, self.top, self.right, self.bottom = extent
        self.mid = (self.left + self.right) / 2
        blocks = [b for b in (block_info(x) for x in page.get_text("dict")["blocks"] if x["type"] == 0)
                  if b["text"]]
        self.blocks = _merge_caption_continuations(blocks)
        self.images, self.drawings = _graphics(page)

    def has_graphics(self, region) -> bool:
        """Whether a region holds an image, a vector path or tabular text (not only prose)."""
        return (any((r & region).get_area() > 0 for r in self.images + self.drawings)
                or any(b["tabular"] and region.contains(b["rect"]) for b in self.blocks))

    def in_image(self, r) -> bool:
        return any((r & im).get_area() > 0.3 * max(r.get_area(), 1) for im in self.images)

    def is_wall(self, b: dict, span_w: float, for_figure: bool) -> bool:
        """Text that bounds a figure: prose, headings, running headers, other captions."""
        if b["lineno"]:
            return False
        if CAPTION.match(b["text"]) or b["rect"].y1 < self.top - 2 or b["rect"].y0 > self.bottom + 2:
            return True
        if b["tabular"]:
            return for_figure and b["rows"] >= 2 and b["size"] >= self.body - 1.5
        prose = b["size"] >= self.body - 0.6 and (b["rect"].width >= 0.25 * span_w or b["lines"] >= 3)
        return prose and not self.in_image(b["rect"])


def _grow(cr, side: str, x0: float, x1: float, walls: list, prims: list, images: list, page_rect):
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


def locate_on_page(page, body: float, extent: tuple[float, float, float, float]) -> list[dict]:
    """Every captioned figure/table on a page with its content region (None if not located)."""
    import fitz

    ctx = _Page(page, body, extent)
    caps = []
    for b in ctx.blocks:
        m = CAPTION.match(b["text"])
        if m:
            caps.append(dict(b, kind="table" if m.group(1) == "Table" else "figure", number=m.group(2)))
    caps.sort(key=lambda c: c["kind"] != "figure")
    claimed: list = []
    found = []
    for cap in caps:
        cr = cap["rect"]
        full = cr.x0 < ctx.mid - 10 and cr.x1 > ctx.mid + 10
        x0, x1 = ((ctx.left, ctx.right) if full else
                  (ctx.left, ctx.mid) if cr.x1 <= ctx.mid + 10 else (ctx.mid, ctx.right))
        span_w = x1 - x0

        def overlaps(r) -> bool:
            return min(r.x1, x1) - max(r.x0, x0) > 0.3 * max(min(r.width, span_w), 1)

        def free(r) -> bool:
            return not any((r & c).get_area() > 0.5 * max(r.get_area(), 0.1) for c in claimed)

        best = None
        for strict in (True, False):
            for_fig = cap["kind"] == "figure" and strict
            walls = [b["rect"] for b in ctx.blocks if b is not cap and overlaps(b["rect"])
                     and ctx.is_wall(b, span_w, for_fig)]
            prims = [r for r in ctx.drawings if free(r)]
            prims += [b["rect"] for b in ctx.blocks if b is not cap and not b["lineno"] and free(b["rect"])
                      and not ctx.is_wall(b, span_w, for_fig)]
            imgs = [r for r in ctx.images if free(r & page.rect)]
            conventional = "above" if cap["kind"] == "figure" else "below"
            for side in ("above", "below"):
                reg = _grow(cr, side, x0, x1, walls, prims, imgs, page.rect)
                if reg is None:
                    continue
                gap = (cr.y0 - reg.y1) if side == "above" else (reg.y0 - cr.y1)
                score = (min(reg.width / span_w, 1.0) + (0.15 if side == conventional else 0)
                         - max(gap, 0) / 200 - (0 if ctx.has_graphics(reg) else 0.5))
                if best is None or score > best[0]:
                    best = (score, side, reg)
            if best:
                break
        region = side = None
        if best:
            _, side, region = best
            region = fitz.Rect(max(region.x0, x0 - COLUMN_SLACK_PT), max(region.y0, ctx.top - 12),
                               min(region.x1, x1 + COLUMN_SLACK_PT), min(region.y1, ctx.bottom + 12))
            claimed.append(region)
        found.append({"kind": cap["kind"], "number": cap["number"], "caption": cap["text"],
                      "caption_rect": cr, "region": region, "side": side, "full_width": full})
    return sorted(found, key=lambda f: (f["caption_rect"].y0, f["caption_rect"].x0))


def measure(page, region, caption_rect) -> dict:
    """Vector text sizes inside the region (caption excluded) and raster image resolution."""
    import fitz

    sizes = []
    for block in page.get_text("dict", clip=region)["blocks"]:
        for line in block.get("lines", []):
            for span in line["spans"]:
                r = fitz.Rect(span["bbox"])
                if span["text"].strip() and r.intersects(region) and not r.intersects(caption_rect):
                    sizes.append(round(span["size"], 1))
    ppi = []
    for info in page.get_image_info():
        full = fitz.Rect(info["bbox"])
        if (full & region).width > 10 and (full & region).height > 10 and full.width > 0:
            ppi.append(round(info["width"] / (full.width / 72)))
    return {"vector_text_spans": len(sizes), "min_text_pt": min(sizes) if sizes else None,
            "median_text_pt": statistics.median(sizes) if sizes else None,
            "raster_images": len(ppi), "min_image_ppi": min(ppi) if ppi else None}
