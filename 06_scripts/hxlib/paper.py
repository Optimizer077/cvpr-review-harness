"""Paper snapshot: copy the PDF(s), extract line-anchored text, detect sections, build reading views.

Reviewers read what a real CVPR reviewer reads: the review-copy PDF. Text files carry the
CVPR margin line numbers as `L###` anchors so reviews can cite locations the way real reviews do.
"""
from __future__ import annotations

import logging
import re
import shutil
from pathlib import Path
from typing import Optional

from .common import SECTION_KEYS, save_json, sha256_file

logger = logging.getLogger(__name__)

_HEADER_PATTERNS = (
    re.compile(r"^CVPR$"),
    re.compile(r"^ICCV$"),
    re.compile(r"^ECCV$"),
    re.compile(r"^#\*+$"),
    re.compile(r"Submission #.*CONFIDENTIAL REVIEW COPY", re.IGNORECASE),
)
_LINE_NO = re.compile(r"^\d{3,4}$")
_TOP_HEADING = re.compile(r"^(\d{1,2})\.\s+([A-Z].{1,90})$")
_APPENDIX_HEADING = re.compile(r"^([A-Z])\.\s+([A-Z].{1,90})$")
_CAPTION = re.compile(r"^(Figure|Fig\.|Table)\s*S?\d+[.:]")
_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("introduction", ("introduction",)),
    ("related_work", ("related", "background", "prior work", "preliminar")),
    ("limitations", ("limitation",)),
    ("conclusion", ("conclusion", "concluding")),
    ("theory", ("theory", "theoretical")),
    ("ablations_analysis", ("ablation", "analysis", "discussion", "understanding")),
    ("experiments", ("experiment", "evaluation", "results")),
    ("method", ("method", "approach", "proposed", "framework")),
)
_CAPTION_MAX_LINES = 10
_INJECTION = re.compile(
    r"(ignore (all |any )?(previous|prior|above) instructions|as an? (ai|language model)|"
    r"\b(llm|language model|chatgpt|gpt-?\d)s?\b.{0,40}\b(review|rate|score)|"
    r"(give|assign|recommend) (this paper )?(a )?(high|positive|strong) (score|rating)|"
    r"\breviewers? (should|must|will|may)\b|to address (possible|potential) (reviewer )?concerns)",
    re.IGNORECASE)


def _is_header(line: str) -> bool:
    return any(p.search(line) for p in _HEADER_PATTERNS)


def extract_lines(pdf: Path) -> list[list[tuple[str, str]]]:
    """Return per page a list of (anchor, text); anchor is 'L###' or ''."""
    import fitz  # PyMuPDF; imported lazily so the CLI loads without it

    pages: list[list[tuple[str, str]]] = []
    with fitz.open(pdf) as doc:
        for page in doc:
            rows: list[list[str]] = []
            for raw in page.get_text().splitlines():
                line = raw.strip()
                if not line or _is_header(line):
                    continue
                if _LINE_NO.match(line):
                    if rows and not rows[-1][0]:
                        rows[-1][0] = f"L{line}"
                    continue
                rows.append(["", line])
            pages.append([(a, t) for a, t in rows])
    return pages


def render_pages(pages: list[list[tuple[str, str]]], label: str) -> str:
    """Render pages as text with page markers and line anchors."""
    out: list[str] = []
    for i, rows in enumerate(pages, start=1):
        out.append(f"===== [{label} p.{i}] =====")
        out.extend(f"{a:<6}{t}" for a, t in rows)
    return "\n".join(out) + "\n"


def _canonical(name: str, seen_experiments: bool) -> str:
    """Map a heading to a section key; unnamed sections are method before experiments, analysis after."""
    low = name.lower()
    for key, words in _KEYWORDS:
        if any(w in low for w in words):
            return key
    return "ablations_analysis" if seen_experiments else "method"


def detect_sections(pages: list[list[tuple[str, str]]]) -> list[dict]:
    """Find title, abstract, numbered top-level sections and references in the main paper."""
    flat: list[tuple[int, str, str]] = [
        (p, a, t) for p, rows in enumerate(pages, start=1) for a, t in rows
    ]
    marks: list[dict] = []
    expected = 1
    seen_exp = False
    for idx, (page, _anchor, text) in enumerate(flat):
        if text == "Abstract" and not marks:
            marks.append({"key": "abstract", "heading": "Abstract", "page": page, "idx": idx})
            continue
        if text == "References":
            marks.append({"key": "references", "heading": "References", "page": page, "idx": idx})
            break
        match = _TOP_HEADING.match(text)
        if not match or int(match.group(1)) != expected:
            continue
        heading = match.group(2)
        if heading.endswith("-") and idx + 1 < len(flat):
            heading = heading[:-1] + flat[idx + 1][2]
        key = _canonical(heading, seen_exp)
        seen_exp |= key == "experiments"
        marks.append({"key": key, "heading": f"{expected}. {heading}", "page": page, "idx": idx})
        expected += 1
    title_lines = [t for p, _, t in flat[: marks[0]["idx"] if marks else 0]
                   if p == 1 and not t.startswith(("Anonymous", "Paper ID"))]
    spans: list[dict] = [{"key": "title", "heading": "Title", "text": " ".join(title_lines),
                          "page_start": 1, "page_end": 1}]
    for k, mark in enumerate(marks):
        end = marks[k + 1]["idx"] if k + 1 < len(marks) else len(flat)
        chunk = flat[mark["idx"]:end]
        spans.append({
            "key": mark["key"], "heading": mark["heading"],
            "page_start": mark["page"], "page_end": chunk[-1][0] if chunk else mark["page"],
            "text": "\n".join(f"{a:<6}{t}" for _, a, t in chunk),
        })
    return _merge_duplicate_keys(spans)


def _merge_duplicate_keys(spans: list[dict]) -> list[dict]:
    """Two numbered sections may map to one key (e.g. two method sections); concatenate them."""
    merged: dict[str, dict] = {}
    for span in spans:
        if span["key"] in merged:
            prev = merged[span["key"]]
            prev["heading"] += " + " + span["heading"]
            prev["text"] += "\n" + span["text"]
            prev["page_end"] = span["page_end"]
        else:
            merged[span["key"]] = dict(span)
    return list(merged.values())


def extract_captions(pages: list[list[tuple[str, str]]], label: str) -> list[dict]:
    """Figure/table captions with page numbers (approximate: up to 10 lines after the start)."""
    caps: list[dict] = []
    for p, rows in enumerate(pages, start=1):
        for i, (anchor, text) in enumerate(rows):
            if not _CAPTION.match(text):
                continue
            body = [text]
            for _, nxt in rows[i + 1:i + _CAPTION_MAX_LINES]:
                if _CAPTION.match(nxt) or _TOP_HEADING.match(nxt):
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


def scan_hidden_and_injection(pdf: Path, label: str) -> list[str]:
    """Flag white or near-invisible text spans and reviewer/LLM-directed sentences."""
    import fitz

    flags: list[str] = []
    with fitz.open(pdf) as doc:
        for pno, page in enumerate(doc, start=1):
            for block in page.get_text("dict")["blocks"]:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        if len(text) < 4:
                            continue
                        if span.get("color") == 0xFFFFFF or span.get("size", 10) < 2.5:
                            flags.append(f"{label} p.{pno}: hidden-looking text {text[:60]!r}")
            for match in _INJECTION.finditer(page.get_text()):
                flags.append(f"{label} p.{pno}: reviewer/LLM-directed phrase {match.group(0)[:60]!r}")
    return flags


def snapshot_paper(pdf: Path, dest: Path, supp: Optional[Path] = None,
                   tex_dir: Optional[Path] = None) -> dict:
    """Copy inputs into `dest`, extract text, write sections and reading views. Returns metadata."""
    dest.mkdir(parents=True, exist_ok=True)
    meta: dict = {"main_pdf_source": str(pdf.resolve())}
    shutil.copy2(pdf, dest / "main.pdf")
    meta["main_pdf_sha256"] = sha256_file(dest / "main.pdf")
    main_pages = extract_lines(dest / "main.pdf")
    meta["main_pages"] = len(main_pages)
    main_txt = render_pages(main_pages, "main")
    (dest / "paper_main.txt").write_text(main_txt, encoding="utf-8")
    meta["injection_flags"] = scan_hidden_and_injection(dest / "main.pdf", "main")

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

    spans = detect_sections(main_pages)
    body = [s for s in spans if s["key"] not in ("references", "title")]
    meta["main_words"] = sum(len(re.sub(r"(?m)^L\d{3,4}\s+", "", s["text"]).split()) for s in body)
    if not any(s["key"] == "limitations" for s in spans):
        lim = _limitations_span(spans)
        if lim:
            spans.append(lim)
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
    if tex_dir is not None:
        meta["tex_files"] = _snapshot_tex(tex_dir, dest / "tex")
    meta["sections_found"] = [s["key"] for s in index]
    return meta


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
