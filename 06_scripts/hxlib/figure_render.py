"""Render what a reader sees of each figure and table, and write the figure inventory.

For every page: `pages/<doc>_pNN.png`. For every captioned figure/table that `figure_locate`
finds: a crop with its caption (`figures/<id>.png`), a grayscale preview (print) and, for colour
figures, a deuteranopia preview (Machado et al. 2009, severity 1.0, applied in linear RGB). A
caption that the text extraction found (`captions.json`) but the locator did not gets a
placeholder entry without crop, flagged `not_located`, so the figure still has to be reviewed.
`figures/figures.json` holds the inventory with measurements and objective flags; `FIGURES.md`
is the same as a table for agents and people. Measurements are facts about the PDF; whether a
figure works is for the reviewers to judge. `figure_reading_line` tells a reviewer prompt which
of these files its reading view covers.
"""
from __future__ import annotations

import json
import logging
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterator, Optional

from .common import load_json, save_json, sha256_file
from .figure_job import caption_refs
from .figure_locate import body_font_size, locate_on_page, measure, text_extent

logger = logging.getLogger(__name__)

PAGE_DPI = 150           # whole-page images: enough to see layout and Fig. 1 at a glance
CROP_LONG_SIDE_PX = 1600  # crops: long side target, so small text stays legible to a model
CROP_DPI_RANGE = (150, 300)
# grayscale / colour-vision previews: at 110 dpi reviewers sampled pixels to tell close shades apart;
# 200 dpi shows thin lines and markers. Cost on two papers with 10-11 figures and tables: previews
# 0.8-1.0 s -> 1.8-2.8 s, preview files 2-3 MB -> 6-9 MB per snapshot.
PREVIEW_DPI = 200
SMALL_TEXT_PT = 6.0      # flag: smallest vector text in a figure below this size (min_text_pt only)
LOW_PPI = 150            # flag: a raster image placed below this effective resolution
COLOUR_FRACTION = 0.01   # a crop with fewer saturated pixels than this counts as grayscale
# Supplement caps (runtime): a figure-heavy supplement costs about 0.5 s per page (layout analysis,
# crops, previews; a 40-page one added about 20 s). Only supplement pages that hold a figure or table
# get a page image (reviewers read the other pages in supplement.pdf), and pages after SUPP_MAX_PAGES
# are not inventoried; FIGURES.md says so. The main paper is never capped.
SUPP_MAX_PAGES = 60
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
# _ENC clamped to [0, 4095] and shifted by _OFF, so a mixed value v encodes as _ENC_PAD[int(v) + _OFF]
# without min/max; the matrix keeps every mixed value within (-0.23, 1.23) x 4095.
_OFF = 1024
_ENC_PAD = [_ENC[min(max(i - _OFF, 0), 4095)] for i in range(4096 + 2 * _OFF)]


def _pixels(samples: bytes) -> Iterator[tuple[int, int, int]]:
    """(r, g, b) tuples of packed RGB bytes."""
    return zip(samples[0::3], samples[1::3], samples[2::3])


def _colour_fraction(samples: bytes) -> float:
    """Share of saturated pixels; figures repeat few colours, so each distinct colour is tested once."""
    counts = Counter(_pixels(samples))
    n = sum(counts.values()) or 1
    return sum(c for (r, g, b), c in counts.items() if max(r, g, b) - min(r, g, b) > 40) / n


def _deuteranopia_pixel(rgb: tuple[int, int, int]) -> bytes:
    r, g, b = rgb
    return bytes([_ENC_PAD[int((t0[r] + t1[g] + t2[b]) * 4095) + _OFF] for t0, t1, t2 in _MIX])


def _deuteranopia(samples: bytes) -> bytes:
    """Simulate deuteranopia on packed RGB bytes (pure Python, lookup tables, one pass per colour)."""
    table = {px: _deuteranopia_pixel(px) for px in set(_pixels(samples))}
    return b"".join(map(table.__getitem__, _pixels(samples)))


class _CachedPage:
    """A page whose full text dictionary is extracted once.

    Layout analysis reads `get_text("dict")` of every page three times (body size, text extent,
    figure location); on figure-heavy PDFs that extraction dominates the run time. Other calls,
    including clipped extraction, go to the real page.
    """

    def __init__(self, page) -> None:
        self._page = page
        self._dict: Optional[dict] = None

    def get_text(self, option: str = "text", **kwargs: Any) -> Any:
        if option != "dict" or kwargs:
            return self._page.get_text(option, **kwargs)
        if self._dict is None:
            self._dict = self._page.get_text("dict")
        return self._dict

    def release(self) -> None:
        """Drop the cached dictionary once the page is done."""
        self._dict = None

    def __getattr__(self, name: str) -> Any:
        return getattr(self._page, name)


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


def _flags(item: dict, not_located: str = "not_located: use the page image") -> list[str]:
    """Objective flags. small_text uses `min_text_pt` only: never `min_script_pt`, and not when
    `text_not_measured` says the plot text is in rasters or outlines (the measured spans may then
    be only subcaptions or scripts; reviewers judge that text on the page image)."""
    flags = []
    if item["crop"] is None:
        flags.append(not_located)
    text_pt = item.get("min_text_pt")
    if text_pt is not None and text_pt < SMALL_TEXT_PT and not item.get("text_not_measured"):
        flags.append(f"small_text: smallest vector text {text_pt} pt (< {SMALL_TEXT_PT})")
    if item.get("min_image_ppi") is not None and item["min_image_ppi"] < LOW_PPI:
        flags.append(f"low_resolution: a raster image at {item['min_image_ppi']} ppi (< {LOW_PPI})")
    if item["doc"] == "main" and not item["mentions"]:
        flags.append("not_referenced: no 'Fig./Table N' mention in the main text")
    return flags


def _inventory_item(page, pno: int, f: dict, doc_label: str, dest: Path, mentions: dict[str, list[dict]],
                    items: list[dict]) -> dict:
    """One figures.json entry: identity, caption, crop and its sha256, measurements, previews, flags."""
    supp = doc_label == "supp"
    fid = f"{'supp_' if supp else ''}{'fig' if f['kind'] == 'figure' else 'tab'}_{f['number']}"
    if any(i["id"] == fid for i in items):
        fid += f"_p{pno}"
    item = {"id": fid, "doc": doc_label, "kind": f["kind"], "number": f["number"],
            "label": f"{'Supp. ' if supp else ''}{'Fig.' if f['kind'] == 'figure' else 'Tab.'} {f['number']}",
            "page": pno, "page_image": f"pages/{doc_label}_p{pno:02d}.png",
            "caption": f["caption"], "caption_words": len(f["caption"].split()),
            "full_width": f["full_width"], "crop": None, "crop_sha256": None,
            "mentions": mentions.get(f"{f['kind']} {f['number']}", [])}
    if f["region"] is not None:
        clip = ((f["region"] | f["caption_rect"]) + (-3, -3, 3, 3)) & page.rect
        crop = dest / "figures" / f"{fid}.png"
        page.get_pixmap(dpi=_crop_dpi(clip), clip=clip).save(crop)
        item["crop"] = f"figures/{fid}.png"
        item["crop_sha256"] = sha256_file(crop)  # blind pairwise detects changed figures by this hash
        item["region_pt"] = [round(v, 1) for v in f["region"]]
        item.update(measure(page, f["region"], f["caption_rect"]))
        item.update(_previews(page, clip, dest, fid))
    item["flags"] = _flags(item)
    return item


def _placeholders(doc_label: str, pages: list, refs: list[dict], items: list[dict], dest: Path,
                  mentions: dict[str, list[dict]]) -> list[dict]:
    """Entries for captions of this PDF that the text has but the locator missed (inventoried pages)."""
    known = {i["id"] for i in items}
    out = []
    for ref in refs:
        if ref["doc"] != doc_label or ref["id"] in known or not 1 <= ref["page"] <= len(pages):
            continue
        image = dest / "pages" / f"{doc_label}_p{ref['page']:02d}.png"
        if not image.exists():  # a supplement page without a located figure has no image yet
            pages[ref["page"] - 1].get_pixmap(dpi=PAGE_DPI).save(image)
        out.append(_placeholder_item(ref, mentions))
        logger.warning("%s: caption found in the text but not located on p.%d", ref["id"], ref["page"])
    return out


def _placeholder_item(ref: dict, mentions: dict[str, list[dict]]) -> dict:
    """Inventory entry for a caption the text has but the locator missed: page image, no crop."""
    supp = ref["doc"] == "supp"
    item = {"id": ref["id"], "doc": ref["doc"], "kind": ref["kind"], "number": ref["number"],
            "label": f"{'Supp. ' if supp else ''}{'Fig.' if ref['kind'] == 'figure' else 'Tab.'} {ref['number']}",
            "page": ref["page"], "page_image": f"pages/{ref['doc']}_p{ref['page']:02d}.png",
            "caption": ref["caption"], "caption_words": len(ref["caption"].split()), "full_width": None,
            "crop": None, "crop_sha256": None, "mentions": mentions.get(f"{ref['kind']} {ref['number']}", [])}
    item["flags"] = _flags(item, "not_located: caption found in text")
    return item


def _render_doc(doc_label: str, pdf: Path, dest: Path, mentions: dict[str, list[dict]],
                refs: list[dict]) -> tuple[list[dict], int]:
    """Inventory items of one PDF and the number of supplement pages left out (SUPP_MAX_PAGES).

    `refs` are the captions found in the text (`caption_refs`); one the locator did not find on
    an inventoried page becomes a placeholder item.
    """
    import fitz

    supp = doc_label == "supp"
    items: list[dict] = []
    with fitz.open(pdf) as doc:
        pages = [_CachedPage(p) for p in doc]
        skipped = max(len(pages) - SUPP_MAX_PAGES, 0) if supp else 0
        pages = pages[:len(pages) - skipped]
        body = body_font_size(pages)
        extent = text_extent(pages, body)
        for pno, page in enumerate(pages, start=1):
            found = locate_on_page(page, body, extent)
            if found or not supp:
                page.get_pixmap(dpi=PAGE_DPI).save(dest / "pages" / f"{doc_label}_p{pno:02d}.png")
            for f in found:
                items.append(_inventory_item(page, pno, f, doc_label, dest, mentions, items))
            page.release()
        items += _placeholders(doc_label, pages, refs, items, dest, mentions)
    items.sort(key=lambda i: i["page"])  # stable: placeholders follow the located items of their page
    if skipped:
        logger.warning("supplement: %d page(s) after page %d not inventoried", skipped, SUPP_MAX_PAGES)
    return items, skipped


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
    refs = caption_refs(dest)  # captions.json, written by the paper snapshot before the figures
    items, _ = _render_doc("main", main_pdf, dest, main_mentions, refs)
    skipped = 0
    if supp_pdf is not None:
        supp_items, skipped = _render_doc("supp", supp_pdf, dest, find_mentions(supp_pages or []), refs)
        items += supp_items
    save_json(dest / "figures" / "figures.json", items)
    (dest / "FIGURES.md").write_text(figures_markdown(items, skipped), encoding="utf-8")
    summary = {"figures": sum(i["kind"] == "figure" for i in items),
               "tables": sum(i["kind"] == "table" for i in items),
               "not_located": [i["id"] for i in items if i["crop"] is None],
               "flagged": sum(bool(i["flags"]) for i in items)}
    if skipped:
        summary["supp_pages_skipped"] = skipped
    return summary


def figures_markdown(items: list[dict], supp_pages_skipped: int = 0) -> str:
    """Inventory table: one row per figure/table with files, measurements and flags."""
    lines = ["# Figures and tables in this snapshot", "",
             "Measured from the PDF, not judged. `min text` is the smallest text the PDF stores as text "
             "inside the figure; it can come from panel subcaptions or sub- and superscripts, and it never "
             "covers text inside raster images or drawn as outlines ('plot text unmeasured': judge that text "
             "on the page image). `scripts` is the smallest sub- or superscript when measured apart. "
             "`min ppi` is the lowest effective resolution of a placed raster image. Previews: `_gray` "
             "(black-and-white print), `_deuteranopia` (red-green colour-vision deficiency, Machado et al. "
             "2009), colour figures only. "
             "Paths are relative to this file's folder.", ""]
    if supp_pages_skipped:
        lines += [f"Supplement pages after page {SUPP_MAX_PAGES} ({supp_pages_skipped}) are not listed here; "
                  "open `supplement.pdf` for them.", ""]
    lines += ["| id | label | page | crop | caption (start) | words | min text pt | min ppi | first mention "
              "| flags |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    for i in items:
        first = i["mentions"][0] if i["mentions"] else None
        mention = f"p.{first['page']} {first['anchor']}".strip() if first else "-"
        cap = i["caption"][:70].replace("|", "/")
        lines.append(f"| {i['id']} | {i['label']} | {i['page']} | {i['crop'] or i['page_image']} | {cap} | "
                     f"{i['caption_words']} | {_text_cell(i)} | "
                     f"{i.get('min_image_ppi') if i.get('min_image_ppi') is not None else '-'} | {mention} | "
                     f"{'; '.join(i['flags']) or '-'} |")
    return "\n".join(lines) + "\n"


def _text_cell(item: dict) -> str:
    """FIGURES.md `min text pt` cell: the value, sub/superscripts apart, and unmeasured plot text."""
    cell = str(item["min_text_pt"]) if item.get("min_text_pt") is not None else "-"
    if item.get("min_script_pt") is not None:
        cell += f" (scripts {item['min_script_pt']})"
    if item.get("text_not_measured"):
        cell += "; plot text unmeasured"
    return cell


def measured_facts(item: dict) -> str:
    """'smallest text 5.5 pt, lowest image resolution 96 ppi' for an inventory item ('' if neither)."""
    facts = []
    if item.get("min_text_pt") is not None:
        facts.append(f"smallest text {item['min_text_pt']} pt")
    if item.get("min_image_ppi") is not None:
        facts.append(f"lowest image resolution {item['min_image_ppi']} ppi")
    return ", ".join(facts)


def load_inventory(snap: Path) -> Optional[dict[str, dict]]:
    """figures.json of a snapshot keyed by id; None if the snapshot has no figure inventory."""
    if not (snap / "FIGURES.md").exists():
        return None
    try:
        return {i["id"]: i for i in load_json(snap / "figures" / "figures.json")}
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        logger.warning("unreadable figure inventory in %s: %s", snap, exc)
        return None


def figure_reading_line(snap: Path, view: str) -> Optional[str]:
    """Prompt bullet pointing a reviewer at the figure images its reading view covers.

    front: the Fig. 1 crop and the page-1 image only; skim: FIGURES.md with Fig. 1 and the crops of
    the main results table and the figures it cites; main/full: every figure and table. None when
    the snapshot has no figure inventory (figure rendering failed, or an older snapshot).
    """
    items = load_inventory(snap)
    if items is None:
        return None
    fig1 = items.get("fig_1")
    if view == "front":
        seen = [f"the page-1 image `{snap / 'pages' / 'main_p01.png'}`"]
        if fig1 and fig1["crop"]:
            facts = measured_facts(fig1)
            seen.insert(0, f"Fig. 1 with its caption `{snap / fig1['crop']}`"
                        + (f" (measured: {facts})" if facts else ""))
        elif fig1:
            seen.insert(0, f"Fig. 1 on its page image `{snap / fig1['page_image']}` (it could not be cropped)")
        return ("Figures: you look only at " + " and ".join(seen) + ". Open the PNGs to see them as "
                "printed; use measured sizes rather than guessing them.")
    if view == "skim":
        crop1 = f" (`{fig1['crop']}`)" if fig1 and fig1["crop"] else ""
        return (f"Figures: `{snap / 'FIGURES.md'}` lists every figure and table with its crop image; its "
                f"paths are relative to its folder. As a skimming reader you open only the crop of Fig. 1{crop1} "
                "and the crops of the main results table and the figures it cites; the other figures you know "
                "from their captions. Look at those crops (open the PNG) instead of judging them from captions. "
                "Use FIGURES.md measurements only for figures you opened.")
    head = (f"Figures: `{snap / 'FIGURES.md'}` lists every figure and table with its crop image, page "
            "image and measured facts (smallest text size in pt, image resolution, where it is first "
            f"referenced); its paths are relative to `{snap}`.")
    supp_note = (" Supplement entries (`supp_` ids) follow your supplement rule."
                 if view == "main" and any(i["doc"] == "supp" for i in items.values()) else "")
    return (head + " Look at the crop images (open the PNG) instead of judging from captions; use the "
            "measured sizes rather than guessing them." + supp_note)
