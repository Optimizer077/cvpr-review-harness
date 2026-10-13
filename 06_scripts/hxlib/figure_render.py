"""Render what a reader sees of each figure and table, and write the figure inventory.

For every page: `pages/<doc>_pNN.png`. For every captioned figure/table that `figure_locate`
finds: a crop with its caption (`figures/<id>.png`), a grayscale preview (print) and, for colour
figures, a deuteranopia preview (Machado et al. 2009, severity 1.0, applied in linear RGB).
`figures/figures.json` holds the inventory with measurements and objective flags; `FIGURES.md`
is the same as a table for agents and people. Measurements are facts about the PDF; whether a
figure works is for the reviewers to judge.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional

from .common import save_json
from .figure_locate import body_font_size, locate_on_page, measure, text_extent

logger = logging.getLogger(__name__)

PAGE_DPI = 150           # whole-page images: enough to see layout and Fig. 1 at a glance
CROP_LONG_SIDE_PX = 1600  # crops: long side target, so small text stays legible to a model
CROP_DPI_RANGE = (150, 300)
PREVIEW_DPI = 110        # grayscale / colour-vision previews: colours and contrast, not small text
SMALL_TEXT_PT = 6.0      # flag: smallest vector text in a figure below this size
LOW_PPI = 150            # flag: a raster image placed below this effective resolution
COLOUR_FRACTION = 0.01   # a crop with fewer saturated pixels than this counts as grayscale
# Machado, Oliveira & Fernandes (2009), IEEE TVCG 15(6):1291-1298, deuteranopia (severity 1.0).
DEUTERANOPIA = ((0.367322, 0.860646, -0.227968),
                (0.280085, 0.672501, 0.047413),
                (-0.011820, 0.042940, 0.968881))
_MENTION = re.compile(r"\b(Fig(?:ure)?s?\.?|Tab(?:le)?s?\.?)\s*~?((?:S?\d+[a-z]?(?:\s*(?:,|and|&|-|–)\s*)?)+)")


def _srgb_to_linear(v: int) -> float:
    c = v / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _linear_to_srgb(x: float) -> int:
    x = min(max(x, 0.0), 1.0)
    c = 12.92 * x if x <= 0.0031308 else 1.055 * x ** (1 / 2.4) - 0.055
    return int(round(c * 255))


_LIN = [_srgb_to_linear(v) for v in range(256)]
_ENC = [_linear_to_srgb(i / 4095) for i in range(4096)]
_MIX = [[[m * _LIN[v] for v in range(256)] for m in row] for row in DEUTERANOPIA]


def _colour_fraction(samples: bytes) -> float:
    rs, gs, bs = samples[0::3], samples[1::3], samples[2::3]
    n = len(rs) or 1
    return sum(1 for r, g, b in zip(rs, gs, bs) if max(r, g, b) - min(r, g, b) > 40) / n


def _deuteranopia(samples: bytes) -> bytes:
    """Simulate deuteranopia on packed RGB bytes (pure Python, lookup tables)."""
    rs, gs, bs = samples[0::3], samples[1::3], samples[2::3]
    out = bytearray(len(samples))
    for ch, (t0, t1, t2) in enumerate(_MIX):
        out[ch::3] = bytes(_ENC[min(max(int((t0[r] + t1[g] + t2[b]) * 4095), 0), 4095)]
                           for r, g, b in zip(rs, gs, bs))
    return bytes(out)


def _crop_dpi(rect) -> int:
    long_in = max(rect.width, rect.height) / 72
    lo, hi = CROP_DPI_RANGE
    return int(min(max(CROP_LONG_SIDE_PX / max(long_in, 0.1), lo), hi))


def find_mentions(pages: list[list[tuple[str, str]]]) -> dict[str, list[dict]]:
    """'figure 3' / 'table 2' -> [{page, anchor}] for every text mention outside captions."""
    out: dict[str, list[dict]] = {}
    for pno, rows in enumerate(pages, start=1):
        for anchor, text in rows:
            for m in _MENTION.finditer(text):
                if m.start() == 0 and re.match(r"\s*(Figure|Fig\.|Table)\s*S?\d+\s*[.:|]", text):
                    continue  # the caption itself
                kind = "table" if m.group(1).lower().startswith("tab") else "figure"
                for num in re.findall(r"S?\d+", m.group(2)):
                    out.setdefault(f"{kind} {num}", []).append({"page": pno, "anchor": anchor})
    return out


def _flags(item: dict) -> list[str]:
    flags = []
    if item["crop"] is None:
        flags.append("not_located: use the page image")
    if item.get("min_text_pt") is not None and item["min_text_pt"] < SMALL_TEXT_PT:
        flags.append(f"small_text: smallest vector text {item['min_text_pt']} pt (< {SMALL_TEXT_PT})")
    if item.get("min_image_ppi") is not None and item["min_image_ppi"] < LOW_PPI:
        flags.append(f"low_resolution: a raster image at {item['min_image_ppi']} ppi (< {LOW_PPI})")
    if item["doc"] == "main" and not item["mentions"]:
        flags.append("not_referenced: no 'Fig./Table N' mention in the main text")
    return flags


def _render_doc(doc_label: str, pdf: Path, dest: Path, mentions: dict[str, list[dict]]) -> list[dict]:
    import fitz

    items: list[dict] = []
    with fitz.open(pdf) as doc:
        body = body_font_size(doc)
        extent = text_extent(doc, body)
        for pno, page in enumerate(doc, start=1):
            page.get_pixmap(dpi=PAGE_DPI).save(dest / "pages" / f"{doc_label}_p{pno:02d}.png")
            for f in locate_on_page(page, body, extent):
                fid = f"{'supp_' if doc_label == 'supp' else ''}{'fig' if f['kind'] == 'figure' else 'tab'}_{f['number']}"
                if any(i["id"] == fid for i in items):
                    fid += f"_p{pno}"
                item = {"id": fid, "doc": doc_label, "kind": f["kind"], "number": f["number"],
                        "label": f"{'Supp. ' if doc_label == 'supp' else ''}{'Fig.' if f['kind'] == 'figure' else 'Tab.'} {f['number']}",
                        "page": pno, "page_image": f"pages/{doc_label}_p{pno:02d}.png",
                        "caption": f["caption"], "caption_words": len(f["caption"].split()),
                        "full_width": f["full_width"], "crop": None,
                        "mentions": mentions.get(f"{f['kind']} {f['number']}", [])}
                if f["region"] is not None:
                    clip = ((f["region"] | f["caption_rect"]) + (-3, -3, 3, 3)) & page.rect
                    page.get_pixmap(dpi=_crop_dpi(clip), clip=clip).save(dest / "figures" / f"{fid}.png")
                    item["crop"] = f"figures/{fid}.png"
                    item["region_pt"] = [round(v, 1) for v in f["region"]]
                    item.update(measure(page, f["region"], f["caption_rect"]))
                    item.update(_previews(page, clip, dest, fid))
                item["flags"] = _flags(item)
                items.append(item)
    return items


def _previews(page, clip, dest: Path, fid: str) -> dict:
    """Grayscale preview always; deuteranopia preview only for colour crops."""
    import fitz

    page.get_pixmap(dpi=PREVIEW_DPI, clip=clip, colorspace=fitz.csGRAY).save(dest / "figures" / f"{fid}_gray.png")
    pix = page.get_pixmap(dpi=PREVIEW_DPI, clip=clip, colorspace=fitz.csRGB, alpha=False)
    frac = _colour_fraction(pix.samples)
    out = {"gray_preview": f"figures/{fid}_gray.png", "colour_fraction": round(frac, 3), "cvd_preview": None}
    if frac >= COLOUR_FRACTION:
        sim = fitz.Pixmap(fitz.csRGB, pix.width, pix.height, _deuteranopia(pix.samples), False)
        sim.save(dest / "figures" / f"{fid}_deuteranopia.png")
        out["cvd_preview"] = f"figures/{fid}_deuteranopia.png"
    return out


def snapshot_figures(dest: Path, main_pdf: Path, main_pages: list, supp_pdf: Optional[Path] = None,
                     supp_pages: Optional[list] = None) -> dict:
    """Write pages/, figures/, figures/figures.json and FIGURES.md under `dest`; return a summary."""
    (dest / "pages").mkdir(parents=True, exist_ok=True)
    (dest / "figures").mkdir(parents=True, exist_ok=True)
    main_mentions = find_mentions(main_pages)
    items = _render_doc("main", main_pdf, dest, main_mentions)
    if supp_pdf is not None:
        items += _render_doc("supp", supp_pdf, dest, find_mentions(supp_pages or []))
    save_json(dest / "figures" / "figures.json", items)
    (dest / "FIGURES.md").write_text(figures_markdown(items), encoding="utf-8")
    return {"figures": sum(i["kind"] == "figure" for i in items), "tables": sum(i["kind"] == "table" for i in items),
            "not_located": [i["id"] for i in items if i["crop"] is None],
            "flagged": sum(bool(i["flags"]) for i in items)}


def figures_markdown(items: list[dict]) -> str:
    """Inventory table: one row per figure/table with files, measurements and flags."""
    lines = ["# Figures and tables in this snapshot", "",
             "Measured from the PDF, not judged. `min text` is the smallest vector text inside the figure "
             "(text inside raster images cannot be measured); `min ppi` is the lowest effective resolution "
             "of a placed raster image. Previews: `_gray` (black-and-white print), `_deuteranopia` "
             "(red-green colour-vision deficiency, Machado et al. 2009), colour figures only.", "",
             "| id | page | crop | caption (start) | words | min text pt | min ppi | first mention | flags |",
             "|---|---|---|---|---|---|---|---|---|"]
    for i in items:
        first = i["mentions"][0] if i["mentions"] else None
        mention = f"p.{first['page']} {first['anchor']}".strip() if first else "-"
        cap = i["caption"][:70].replace("|", "/")
        lines.append(f"| {i['label']} | {i['page']} | {i['crop'] or i['page_image']} | {cap} | {i['caption_words']} | "
                     f"{i.get('min_text_pt') if i.get('min_text_pt') is not None else '-'} | "
                     f"{i.get('min_image_ppi') if i.get('min_image_ppi') is not None else '-'} | {mention} | "
                     f"{'; '.join(i['flags']) or '-'} |")
    return "\n".join(lines) + "\n"
