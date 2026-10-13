"""Paper snapshot: copy the PDF(s), extract line-anchored text, detect sections, build reading views,
and render page images and figure crops with measurements (`figure_render`).

Reviewers read what a real CVPR reviewer reads: the review-copy PDF. Text files carry the
margin line numbers of review copies as `L###` anchors so reviews can cite locations the way real
reviews do. Text extraction and section detection live in `paper_text` and are re-exported here.
"""
from __future__ import annotations

import logging
import re
import shutil
from pathlib import Path
from typing import Any, Optional

from .anonymity import scan_document
from .common import SECTION_KEYS, save_json, sha256_file
from .paper_text import (detect_sections, extract_lines, extract_pages, is_heading_row, line_numbered,
                         render_pages)

__all__ = ["detect_sections", "extract_captions", "extract_lines", "extract_pages", "injection_phrases",
           "render_pages", "scan_hidden_and_injection", "snapshot_paper"]

logger = logging.getLogger(__name__)

_CAPTION = re.compile(r"^(Figure|Fig\.|Table)\s*S?\d+[.:]")
_CAPTION_MAX_LINES = 10
_DARK_FILL = 0.75  # mean RGB (0-1) below which a filled shape is a dark background for white text
# Instructions aimed at the (LLM) reviewer, not sentences about LLMs: overriding instructions,
# addressing an AI, telling reviewers/LLMs to rate this paper, ordering a positive review.
_INJECTION = re.compile(
    r"\b(?:ignore|disregard|forget)\s+(?:all\s+|any\s+)?(?:the\s+)?(?:previous|prior|above|preceding|earlier)"
    r"\s+(?:instructions|prompts?|directions)"
    r"|\bif\s+you\s+are\s+an?\s+(?:ai|llm|(?:large\s+)?language\s+model|(?:ai|automated)\s+reviewer)\b"
    r"|\bas\s+an?\s+(?:ai|llm|automated|language[\s-]model)\s+reviewer\b"
    r"|\b(?:note|message|instructions?)\s+(?:to|for)\s+(?:the\s+|any\s+|all\s+)?"
    r"(?:llm|ai|language[\s-]model|automated)\s+reviewers?\b"
    r"|\bdeserves?\s+(?:a|an)\s+(?:strong\s+|clear\s+)?(?:accept|acceptance|high\s+(?:score|rating))\b"
    r"|(?:^|[.!?]\s+|\bplease\s+)(?:rate|score|accept)\s+(?:this|the)\s+(?:paper|work|submission|manuscript)\b"
    r"|\b(?:llms?|ai|(?:large\s+)?language\s+models?|chatgpt|gpt-?\d\w*|assistants?|reviewers?)\b[^.!?]{0,40}?"
    r"\b(?:should|must|shall|(?:is|are)\s+instructed\s+to)\s+(?:\w+\s+){0,3}?"
    r"(?:rate|score|recommend|accept|praise|give|assign)\b[^.!?]{0,40}?"
    r"\b(?:this|the|our)\s+(?:paper|work|submission|manuscript)\b"
    r"|(?:^|[.!?]\s+|\b(?:please|now|just|only)\s+)(?:give|assign|award|write|provide)\s+(?:only\s+)?"
    r"(?:this\s+(?:paper|work|submission)\s+)?an?\s+(?:very\s+)?"
    r"(?:high|positive|strong|favou?rable|perfect|top|glowing)\s+(?:score|rating|review|evaluation|assessment)"
    r"|\bdo\s+not\s+(?:highlight|mention|point\s+out|list|discuss)\s+(?:any\s+)?"
    r"(?:negatives|weaknesses|flaws|limitations)",
    re.IGNORECASE)


def extract_captions(pages: list[list[tuple[str, str]]], label: str) -> list[dict]:
    """Figure/table captions with page numbers (approximate: up to 10 lines after the start)."""
    caps: list[dict] = []
    for p, rows in enumerate(pages, start=1):
        for i, (anchor, text) in enumerate(rows):
            if not _CAPTION.match(text):
                continue
            body = [text]
            for _, nxt in rows[i + 1:i + _CAPTION_MAX_LINES]:
                if _CAPTION.match(nxt) or is_heading_row(nxt):
                    break
                body.append(nxt)
                if nxt.endswith(".") and len(" ".join(body)) > 300:
                    break
            caps.append({"doc": label, "page": p, "anchor": anchor, "text": " ".join(body)})
    return caps


def _limitations_span(spans: list[dict]) -> Optional[dict]:
    """If there is no Limitations section, point to a 'Limitations' paragraph inside the text."""
    for span in spans:
        lines = span.get("text", "").splitlines()
        for i, line in enumerate(lines):
            if re.search(r"\bLimitations?\b[.:]", line):
                return {"key": "limitations", "heading": f"Limitations paragraph in {span['heading']}",
                        "page_start": span["page_start"], "page_end": span["page_end"],
                        "text": "\n".join(lines[i:i + 25])}
    return None


def _add_limitations_paragraph(spans: list[dict]) -> None:
    """Without a 'Limitations' section, use the 'Limitations' paragraph of another section.

    A limitations span made only of impact or ethics statements (`paper_text._canonical`) gets that
    paragraph put in front of it, so the paper's own limitations stay in the scored text.
    """
    current = next((s for s in spans if s["key"] == "limitations"), None)
    if current is not None and "limitation" in current["heading"].lower():
        return
    para = _limitations_span([s for s in spans if s is not current])
    if para is None:
        return
    if current is None:
        spans.append(para)
        return
    current.update(heading=f"{para['heading']} + {current['heading']}", text=para["text"] + "\n" + current["text"],
                   page_start=min(para["page_start"], current["page_start"]),
                   page_end=max(para["page_end"], current["page_end"]))


def injection_phrases(text: str) -> list[str]:
    """Instructions aimed at the reviewer or an LLM reviewer in `text` (line breaks are ignored).

    Sentences about LLMs ('GPT-4 achieves a win rate ...') are not instructions and are not flagged.
    """
    return [m.group(0) for m in _INJECTION.finditer(" ".join(text.split()))]


def _near_white(color: object) -> bool:
    """Whether an sRGB integer colour (0xRRGGBB) is white or nearly so."""
    return isinstance(color, int) and all(((color >> shift) & 0xFF) >= 0xF0 for shift in (16, 8, 0))


def _dark_backgrounds(page: Any) -> list[Any]:
    """Rectangles of images and dark filled drawings: white text on them is a visible figure label."""
    import fitz

    rects = [fitz.Rect(info["bbox"]) for info in page.get_image_info()]
    for drawing in page.get_drawings():
        fill, opacity = drawing.get("fill"), drawing.get("fill_opacity")
        if fill and sum(fill) / len(fill) < _DARK_FILL and (opacity is None or opacity > 0.3):
            rects.append(fitz.Rect(drawing["rect"]))
    return rects


def _hidden_spans(page: Any) -> list[str]:
    """Texts of spans a reader cannot see: tiny (< 2.5 pt), or near-white on the page background.

    Near-white text that lies mostly over an image or a dark filled shape (labels drawn on error maps,
    photos or coloured boxes) is visible and not reported.
    """
    import fitz

    spans = [span for block in page.get_text("dict")["blocks"] for line in block.get("lines", [])
             for span in line.get("spans", []) if len(span.get("text", "").strip()) >= 4]
    backgrounds: Optional[list[Any]] = None
    hidden: list[str] = []
    for span in spans:
        if span.get("size", 10) >= 2.5 and not _near_white(span.get("color")):
            continue
        if span.get("size", 10) >= 2.5:
            backgrounds = _dark_backgrounds(page) if backgrounds is None else backgrounds
            box = fitz.Rect(span["bbox"])
            area = box.get_area() or 1.0
            if any((fitz.Rect(box) & bg).get_area() >= 0.5 * area for bg in backgrounds
                   if box.intersects(bg)):
                continue
        hidden.append(span["text"].strip())
    return hidden


def scan_hidden_and_injection(pdf: Path, label: str) -> list[str]:
    """Flag hidden-looking text spans (`_hidden_spans`) and reviewer/LLM-directed sentences."""
    import fitz

    flags: list[str] = []
    with fitz.open(pdf) as doc:
        for pno, page in enumerate(doc, start=1):
            flags += [f"{label} p.{pno}: hidden-looking text {text[:60]!r}" for text in _hidden_spans(page)]
            for phrase in injection_phrases(page.get_text()):
                flags.append(f"{label} p.{pno}: reviewer/LLM-directed phrase {phrase[:60]!r}")
    return flags


def snapshot_paper(pdf: Path, dest: Path, supp: Optional[Path] = None,
                   tex_dir: Optional[Path] = None) -> dict:
    """Copy inputs into `dest`, extract text, write sections and reading views. Returns metadata.

    The metadata includes `line_numbers` (the main PDF prints margin line numbers, see
    `paper_text.line_numbered`), `injection_flags` and `anonymity_flags` (main and supplement).
    """
    dest.mkdir(parents=True, exist_ok=True)
    meta: dict = {"main_pdf_source": str(pdf.resolve())}
    shutil.copy2(pdf, dest / "main.pdf")
    meta["main_pdf_sha256"] = sha256_file(dest / "main.pdf")
    main_pages, main_styles = extract_pages(dest / "main.pdf")
    meta["main_pages"] = len(main_pages)
    meta["line_numbers"] = line_numbered([sum(1 for anchor, _ in rows if anchor) for rows in main_pages])
    main_txt = render_pages(main_pages, "main")
    (dest / "paper_main.txt").write_text(main_txt, encoding="utf-8")
    meta["injection_flags"] = scan_hidden_and_injection(dest / "main.pdf", "main")
    meta["anonymity_flags"] = scan_document(main_pages, dest / "main.pdf", "main")

    supp_txt = ""
    supp_pages: list[list[tuple[str, str]]] = []
    if supp is not None:
        meta["supp_pdf_source"] = str(supp.resolve())
        shutil.copy2(supp, dest / "supplement.pdf")
        meta["supp_pdf_sha256"] = sha256_file(dest / "supplement.pdf")
        supp_pages = extract_lines(dest / "supplement.pdf")
        meta["supp_pages"] = len(supp_pages)
        supp_txt = render_pages(supp_pages, "supp")
        (dest / "paper_supp.txt").write_text(supp_txt, encoding="utf-8")
        meta["injection_flags"] += scan_hidden_and_injection(dest / "supplement.pdf", "supp")
        meta["anonymity_flags"] += scan_document(supp_pages, dest / "supplement.pdf", "supp")

    spans = detect_sections(main_pages, main_styles)
    body = [s for s in spans if s["key"] not in ("references", "title")]
    meta["main_words"] = sum(len(re.sub(r"(?m)^L\d{3,4}\s+", "", s["text"]).split()) for s in body)
    _add_limitations_paragraph(spans)
    if supp_txt:
        spans.append({"key": "supplementary", "heading": "Supplementary material",
                      "page_start": 1, "page_end": len(supp_pages), "text": supp_txt})
    captions = extract_captions(main_pages, "main") + extract_captions(supp_pages, "supp")
    cap_text = "\n".join(f"[{c['doc']} p.{c['page']} {c['anchor']}] {c['text']}" for c in captions)
    spans.append({"key": "figures_tables", "heading": "All figure and table captions",
                  "page_start": 1, "page_end": len(main_pages), "text": cap_text})

    sec_dir = dest / "sections"
    sec_dir.mkdir(exist_ok=True)
    for span in spans:
        (sec_dir / f"{span['key']}.txt").write_text(span["text"] + "\n", encoding="utf-8")
    index = [{k: v for k, v in s.items() if k != "text"} for s in spans]
    order = {k: i for i, k in enumerate(SECTION_KEYS)}
    index.sort(key=lambda s: order.get(s["key"], 99))
    save_json(dest / "sections.json", index)
    save_json(dest / "captions.json", captions)
    _write_views(dest, spans, main_txt, supp_txt, cap_text)
    meta["figures"] = _snapshot_figures(dest, main_pages, supp_pages if supp is not None else None)
    if tex_dir is not None:
        meta["tex_files"] = _snapshot_tex(tex_dir, dest / "tex")
    meta["sections_found"] = [s["key"] for s in index]
    return meta


def _snapshot_figures(dest: Path, main_pages: list[list[tuple[str, str]]],
                      supp_pages: Optional[list[list[tuple[str, str]]]]) -> dict:
    """Page images, figure crops and FIGURES.md (figure_render); returns the summary for ROUND.json.

    Figure code never blocks a snapshot: on any error the snapshot keeps its text and reading views,
    the inventory files are removed (prompts then fall back to PDF pages), and the summary is
    {"error": message}.
    """
    try:
        from .figure_render import snapshot_figures
        return snapshot_figures(dest, dest / "main.pdf", main_pages,
                                dest / "supplement.pdf" if supp_pages is not None else None, supp_pages)
    except Exception as exc:  # noqa: BLE001 - any failure in figure code must leave the snapshot usable
        logger.warning("figure snapshot failed; continuing without figures: %s", exc)
        for name in ("FIGURES.md", "figures/figures.json"):
            (dest / name).unlink(missing_ok=True)
        return {"error": f"{type(exc).__name__}: {exc}"}


def _write_views(dest: Path, spans: list[dict], main_txt: str, supp_txt: str, cap_text: str) -> None:
    by_key = {s["key"]: s for s in spans}

    def part(key: str) -> str:
        span = by_key.get(key)
        return f"--- {span['heading']} (p.{span['page_start']}) ---\n{span['text']}\n" if span else ""

    front = part("title") + part("abstract") + part("introduction")
    headings = "\n".join(f"- {s['heading']} (p.{s['page_start']}-{s['page_end']})"
                         for s in spans if s["key"] not in ("figures_tables", "supplementary"))
    skim = (front + "\n--- Section headings ---\n" + headings + "\n\n--- Captions ---\n" + cap_text
            + "\n\n" + part("limitations") + part("conclusion"))
    (dest / "view_front.txt").write_text(front, encoding="utf-8")
    (dest / "view_skim.txt").write_text(skim, encoding="utf-8")
    (dest / "view_main.txt").write_text(main_txt, encoding="utf-8")
    (dest / "view_full.txt").write_text(main_txt + ("\n" + supp_txt if supp_txt else ""),
                                        encoding="utf-8")


def _snapshot_tex(tex_dir: Path, out: Path) -> dict[str, str]:
    """Copy LaTeX sources (no backups) for round-to-round diffs; return name -> sha256."""
    hashes: dict[str, str] = {}
    for src in sorted(list(tex_dir.glob("*.tex")) + list(tex_dir.glob("sections/*.tex"))):
        rel = src.relative_to(tex_dir)
        target = out / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
        hashes[str(rel)] = sha256_file(target)
    return hashes
