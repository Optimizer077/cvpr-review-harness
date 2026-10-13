"""Page layout primitives for `figure_locate`: text blocks in the reading frame, captions, graphics.

Text blocks come from PyMuPDF without image bytes, are turned into the frame where most text runs
left to right (rotated pages, sideways tables), lose review-copy line numbers, and are split where
a caption line starts inside a block (panel labels or table text above it). Each block is
described with the facts the locator needs: size, rows, tabular, prose, heading, monospace,
vertical, caption label. Graphics are images, vector paths (hairlines widened) and boxes (visible
frames and coloured panels).
"""
from __future__ import annotations

import re
from collections import Counter
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    import fitz

_NUM = r"(?:[A-Z]\.?)?\d+(?:\.\d+)?"
CAPTION = re.compile(rf"^\s*(Figure|Fig\.|Table)\s*({_NUM})\s*[.:|]")
_CAPTION_CAPS = re.compile(rf"^\s*(TABLE|FIGURE|FIG\.)\s*({_NUM}|[IVXL]+)(?:\s*[.:|]|\s*$)")
_LINE_NO = re.compile(r"^\d{3,4}$")
_INT = re.compile(r"^\d{1,4}$")
HEADING = re.compile(r"^(?:\d{1,2}(?:\.\d{1,2}){0,3}\.?|[A-H](?:\.\d{1,2}){0,3}\.?)\s+[A-Z]")
_MONO = re.compile(r"Mono|Courier|Typewriter|CMTT|SFTT|Consol|Menlo|Inconsolata", re.I)
_WORD = re.compile(r"\b[A-Za-z][A-Za-z'-]*[a-z]\b")


def text_dict(page, clip=None) -> dict:
    """`page.get_text("dict")` without image bytes (much faster on photo-heavy pages)."""
    import fitz

    return page.get_text("dict", clip=clip, flags=fitz.TEXTFLAGS_DICT & ~fitz.TEXT_PRESERVE_IMAGES)


def is_identity(m: fitz.Matrix) -> bool:
    return tuple(m) == (1, 0, 0, 1, 0, 0)


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


def caption_label(text: str, first_line: str) -> Optional[tuple[str, str]]:
    """(kind, number) when a block starts with a caption label."""
    m = CAPTION.match(text) or _CAPTION_CAPS.match(first_line)
    return ("table" if m.group(1).lower().startswith("tab") else "figure", m.group(2)) if m else None


def line_text(line: dict) -> str:
    return "".join(s["text"] for s in line["spans"]).strip()


def _rebox(block: dict, lines: list[dict]) -> dict:
    """A copy of a raw block holding only `lines`, with bounding boxes recomputed."""
    import fitz

    out = []
    for ln in lines:
        box = fitz.Rect(ln["spans"][0]["bbox"])
        for s in ln["spans"][1:]:
            box |= fitz.Rect(s["bbox"])
        out.append(dict(ln, bbox=tuple(box)))
    box = fitz.Rect(out[0]["bbox"])
    for ln in out[1:]:
        box |= fitz.Rect(ln["bbox"])
    return dict(block, lines=out, bbox=tuple(box))


def _strip_line_numbers(blocks: list[dict]) -> list[dict]:
    """Drop review-copy line numbers: integer spans left or right of all other text on the page."""
    spans = [s for b in blocks for ln in b.get("lines", []) for s in ln["spans"] if s["text"].strip()]
    words = [s for s in spans if not _INT.match(s["text"].strip())]
    if not words:
        return blocks
    lo, hi = min(s["bbox"][0] for s in words), max(s["bbox"][2] for s in words)
    drop = {id(s) for s in spans if _INT.match(s["text"].strip())
            and (s["bbox"][2] <= lo + 1 or s["bbox"][0] >= hi - 1)}
    if len(drop) < 5:
        return blocks
    out = []
    for b in blocks:
        lines = [dict(ln, spans=[s for s in ln["spans"] if id(s) not in drop]) for ln in b.get("lines", [])]
        lines = [ln for ln in lines if any(s["text"].strip() for s in ln["spans"])]
        if lines:
            out.append(_rebox(b, lines))
    return out


def _split_captions(blocks: list[dict]) -> list[dict]:
    """Start a new block at a caption line that follows labels or table text in the same block."""
    out = []
    for b in blocks:
        lines, cuts = b.get("lines", []), [0]
        for i in range(1, len(lines)):
            text, prev, cur = line_text(lines[i]), lines[i - 1], lines[i]
            if not (CAPTION.match(text) or _CAPTION_CAPS.match(text)):
                continue
            size = cur["spans"][0]["size"]
            if (abs(prev["spans"][0]["size"] - size) >= 0.5 or abs(prev["bbox"][0] - cur["bbox"][0]) > 3
                    or cur["bbox"][1] - prev["bbox"][3] > 0.6 * size):
                cuts.append(i)  # a prose line that merely starts with "Fig. 3." keeps its paragraph
        out += [_rebox(b, lines[a:z]) for a, z in zip(cuts, cuts[1:] + [len(lines)])] if len(cuts) > 1 else [b]
    return out


def _frame(blocks: list[dict]) -> fitz.Matrix:
    """Matrix taking text coordinates to a frame where most characters run left to right."""
    import fitz

    count: Counter = Counter()
    for b in blocks:
        for ln in b.get("lines", []):
            count[(round(ln["dir"][0]), round(ln["dir"][1]))] += sum(len(s["text"].strip()) for s in ln["spans"])
    turns = {(0, -1): fitz.Matrix(0, 1, -1, 0, 0, 0), (0, 1): fitz.Matrix(0, -1, 1, 0, 0, 0),
             (-1, 0): fitz.Matrix(-1, 0, 0, -1, 0, 0)}
    return turns.get(count.most_common(1)[0][0], fitz.Identity) if count else fitz.Identity


def _transform(blocks: list[dict], m: fitz.Matrix) -> list[dict]:
    import fitz

    def span(s: dict) -> dict:
        return dict(s, bbox=tuple(fitz.Rect(s["bbox"]) * m), origin=tuple(fitz.Point(s["origin"]) * m))
    return [dict(b, bbox=tuple(fitz.Rect(b["bbox"]) * m),
                 lines=[dict(ln, bbox=tuple(fitz.Rect(ln["bbox"]) * m), dir=tuple(fitz.Point(ln["dir"]) * m),
                             spans=[span(s) for s in ln["spans"]]) for ln in b.get("lines", [])]) for b in blocks]


def layout_blocks(page) -> tuple[list[dict], fitz.Matrix]:
    """Raw text blocks in the reading frame (line numbers dropped, captions split) and its matrix."""
    raw = [b for b in text_dict(page)["blocks"] if b.get("type", 0) == 0 and b.get("lines")]
    m = _frame(raw)
    if not is_identity(m):
        raw = _transform(raw, m)
    return _split_captions(_strip_line_numbers(raw)), m


def graphics(page, m) -> tuple[list, list, list]:
    """(images, drawings, boxes) in the reading frame; page-sized backgrounds and white fills dropped."""
    import fitz

    pr = page.rect * page.derotation_matrix

    def big(r) -> bool:
        return r.width > 0.85 * pr.width and r.height > 0.85 * pr.height
    images = [fitz.Rect(i["bbox"]) & pr for i in page.get_image_info()]
    images = [r * m for r in images if r.width > 3 and r.height > 3 and not big(r)]
    drawings, boxes = [], []
    for path in page.get_drawings():
        r = fitz.Rect(path["rect"])
        if r.width < 1:  # hairlines (axes, rules, frame edges) get a width so they can be matched
            r = fitz.Rect(r.x0 - 0.5, r.y0, r.x1 + 0.5, r.y1)
        if r.height < 1:
            r = fitz.Rect(r.x0, r.y0 - 0.5, r.x1, r.y1 + 0.5)
        r &= pr
        fill = path.get("fill")
        white = path.get("color") is None and fill is not None and min(fill) > 0.97
        if r.is_empty or big(r) or (white and r.get_area() > 0.35 * pr.get_area()):
            continue  # invisible backgrounds; small white fills mark figure canvases and stay
        drawings.append(r * m)
        items = path.get("items") or [("",)]
        shut = (path.get("closePath") or any(it[0] in ("re", "qu") for it in items)
                or (len(items) >= 4 and abs(fitz.Point(items[0][1]) - fitz.Point(items[-1][-1])) < 1))
        closed = (fill is not None and not white) or (path.get("color") is not None and shut)
        if closed and r.width >= 40 and r.height >= 15 and r.get_area() < 0.3 * pr.get_area():
            boxes.append(r * m)
    return images, drawings, boxes


def describe(raw: dict) -> dict:
    """block_info plus line rects, gapped rows, digit share and caption/heading/prose/mono/vertical flags."""
    import fitz

    info = block_info(raw)
    spans = [s for ln in raw.get("lines", []) for s in ln["spans"] if s["text"].strip()]
    chars = sum(len(s["text"]) for s in spans) or 1
    words = _WORD.findall(info["text"])
    bold = sum(len(s["text"]) for s in spans if s.get("flags", 0) & 16) > 0.7 * chars
    turned = sum(len(line_text(ln)) for ln in raw.get("lines", []) if ln["dir"][0] < 0.9)
    info.update(line_rects=[fitz.Rect(ln["bbox"]) for ln in raw.get("lines", [])], vertical=turned > 0.5 * chars,
                gapped_rows=sum(_gapped(r) for r in _rows(spans)),
                digits=sum(ch.isdigit() for ch in info["text"]) / max(len(info["text"].replace(" ", "")), 1),
                cap=caption_label(info["text"], line_text(raw["lines"][0]) if raw.get("lines") else ""),
                mono=sum(len(s["text"]) for s in spans if _MONO.search(s.get("font", ""))) > 0.7 * chars,
                prose=len(words) >= 4 and sum(w[0].islower() for w in words) >= 0.5 * len(words),
                heading=(info["rows"] == 1 and len(info["text"].split()) <= 12
                         and bool(re.search(r"[A-Za-z]{2}", info["text"]))
                         and (bool(HEADING.match(info["text"])) or (bold and len(info["text"]) >= 6))))
    return info


def merge_caption_continuations(blocks: list[dict]) -> list[dict]:
    """A block right under a caption with the same edges and size continues that caption."""
    out: list[dict] = []
    for b in sorted(blocks, key=lambda x: (x["rect"].y0, x["rect"].x0)):
        prev = next((c for c in reversed(out) if c["cap"]), None)
        if (prev is not None and not b["cap"] and not b["lineno"] and 0 <= b["rect"].y0 - prev["rect"].y1 <= 3
                and abs(b["rect"].x0 - prev["rect"].x0) <= 4 and abs(b["rect"].x1 - prev["rect"].x1) <= 4
                and abs(b["size"] - prev["size"]) <= 0.6):
            prev["rect"] = prev["rect"] | b["rect"]
            prev["text"] += " " + b["text"]
            prev["lines"] += b["lines"]
            prev["line_rects"] = prev["line_rects"] + b["line_rects"]
            continue
        out.append(b)
    return out


def doc_single_column(page, width: float) -> bool:
    """Whether long text blocks elsewhere in the document run across the text width."""
    wide = narrow = 0
    for other in page.parent:
        for x0, _, x1, _, text, _, kind in other.get_text("blocks"):
            if kind == 0 and len(text) > 200:
                wide += x1 - x0 >= 0.65 * width
                narrow += x1 - x0 <= 0.55 * width
        if wide + narrow >= 10:
            break
    return wide >= narrow
