"""Line-anchored text extraction and section detection for paper PDFs (used by `paper`).

Text files carry the margin line numbers of review copies as `L###` anchors. A line number is a
3-4 digit row left or right of the document's body text; numbers inside the text (table cells,
page numbers) stay text. A line number labels the text row on its baseline
on its side of the page, so review copies that print the number column as one block (ICLR) are
anchored as well as interleaved ones (CVPR).

Section headings are recognised in CVPR (`1. Introduction`), NeurIPS (`1 Introduction`) and ICLR
(`1 INTRODUCTION`) styles, also when the PDF text puts the number and the title on separate rows,
as LaTeX templates usually do. When a paper sets its numbered titles larger or bolder than body
text, only such titles count, which rules out numbered list items, footnotes and table cells.
"""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Any, Optional

_HEADER_PATTERNS = (
    re.compile(r"^CVPR$"),
    re.compile(r"^ICCV$"),
    re.compile(r"^ECCV$"),
    re.compile(r"^#\*+$"),
    re.compile(r"Submission #.*CONFIDENTIAL REVIEW COPY", re.IGNORECASE),
    re.compile(r"^(Under review|Published) as a conference paper at ", re.IGNORECASE),  # ICLR header
)
_LINE_NO = re.compile(r"^\d{3,4}$")
_BODY_WORDS = 4  # horizontal rows with at least this many words are body text
_TOP_HEADING = re.compile(r"^(\d{1,2})(?:\.\s*|\s+)(\S.{0,90})$")  # one-row numbered heading
_SECTION_NO = re.compile(r"^(\d{1,2})\.?$")  # a number alone; its title is the next row
_TITLE_START = re.compile(r"[^\W\d_]|\d[A-Z]\b")  # a letter, or a '3D'-like token
_NUMERIC = re.compile(r"^[-+−]?[\d.,]+%?$")
_BOLD_FONT = re.compile(r"bold|black|heavy|semibold|medi", re.IGNORECASE)
_MAX_HEADING_WORDS = 12
_ABSTRACT = re.compile(r"^abstract(?:[.:—-]|$)")  # on lower-case text without spaces
_REFERENCES = re.compile(r"^(?:references|bibliography)[.:]?$")
_MARGIN = "#margin"  # queue entry of a line-number row
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

Row = tuple[str, tuple, float, float]  # text, bbox (x0, y0, x1, y1), largest font size, bold share
Candidate = tuple[int, str, int, bool]  # section number, title, rows used, doubtful


def _is_header(line: str) -> bool:
    return any(p.search(line) for p in _HEADER_PATTERNS)


def _page_rows(page: Any) -> list[Row]:
    """Horizontal text rows of a page with their font size and share of bold characters."""
    rows: list[Row] = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            spans = [s for s in line["spans"] if s["text"].strip()]
            if not spans or abs(line["dir"][1]) >= 0.01:
                continue
            chars = sum(len(s["text"].strip()) for s in spans)
            bold = sum(len(s["text"].strip()) for s in spans
                       if s["flags"] & 16 or _BOLD_FONT.search(s["font"]))
            rows.append(("".join(s["text"] for s in line["spans"]).strip(), line["bbox"],
                         max(s["size"] for s in spans), bold / chars))
    return rows


def _body_boxes(rows: list[Row]) -> list[tuple]:
    """Bounding boxes of body-text rows (enough words, not a running header)."""
    return [r[1] for r in rows if len(r[0].split()) >= _BODY_WORDS and not _is_header(r[0])]


def _text_extent(pages: list[list[Row]]) -> Optional[tuple[float, float]]:
    """Left and right edge of the document's body text: 5th / 95th percentile over all body rows (at
    least one row trimmed from 10 rows on), so a few wide rows (tables running into the margin) do not
    move it."""
    x0s = sorted(b[0] for rows in pages for b in _body_boxes(rows))
    x1s = sorted(b[2] for rows in pages for b in _body_boxes(rows))
    if not x0s:
        return None
    k = max(int(0.05 * (len(x0s) - 1)), 1 if len(x0s) >= 10 else 0)
    return x0s[k], x1s[len(x1s) - 1 - k]


def _margin_numbers(rows: list[Row], extent: Optional[tuple[float, float]]) -> set[int]:
    """Indices of line-number rows: 3-4 digits, outside the document's text extent, and crossed by at
    most two body rows of the page (one wide table row may run into the margin)."""
    if extent is None:
        return set()
    body = _body_boxes(rows)
    out: set[int] = set()
    for i, (text, (x0, _, x1, _), _, _) in enumerate(rows):
        outside = x1 <= extent[0] + 0.5 or x0 >= extent[1] - 0.5
        if _LINE_NO.match(text) and outside and sum(1 for b in body if b[0] < x1 and b[2] > x0) <= 2:
            out.add(i)
    return out


def _row_queues(rows: list[Row], numbers: set[int], width: float, strong_size: float
                ) -> dict[str, list[tuple[str, bool]]]:
    """Row text -> (anchor or _MARGIN, heading style) of its occurrences in reading order.

    A margin number labels the text row on its side of the page (left numbers: rows starting left of
    the middle; right numbers: rows ending right of it) whose vertical span holds the number's centre,
    nearest to the number. A number beside a figure, with no text row on its baseline, labels nothing.
    """
    body = [(i, r[1]) for i, r in enumerate(rows) if i not in numbers]
    labels: dict[int, str] = {}
    for i in sorted(numbers, key=lambda n: rows[n][1][1]):
        x0, y0, x1, y1 = rows[i][1]
        centre, left = (y0 + y1) / 2, x1 < width / 2
        hits = [((b[0] - x1) if left else (x0 - b[2]), j) for j, b in body
                if b[1] <= centre <= b[3] and (b[0] < width / 2 if left else b[2] > width / 2)]
        if hits:
            labels.setdefault(min(hits)[1], f"L{rows[i][0]}")
    queues: dict[str, list[tuple[str, bool]]] = {}
    for i, (text, _, size, bold) in enumerate(rows):
        entry = (_MARGIN, False) if i in numbers else (labels.get(i, ""), size >= strong_size or bold >= 0.6)
        queues.setdefault(text, []).append(entry)
    return queues


def _body_size(pages: list[list[Row]]) -> float:
    """Most common font size of body rows (by characters), rounded to 0.5 pt."""
    sizes: Counter = Counter()
    for rows in pages:
        for text, _, size, _ in rows:
            if len(text.split()) >= _BODY_WORDS:
                sizes[round(size * 2) / 2] += len(text)
    return sizes.most_common(1)[0][0] if sizes else 10.0


def extract_pages(pdf: Path) -> tuple[list[list[tuple[str, str]]], list[list[bool]]]:
    """Per page (anchor, text) rows, anchor 'L###' or '', and per row whether it is heading-styled.

    Rows come from the plain-text order of the PDF; layout facts (line numbers, font) are matched by
    row text, occurrence by occurrence, so a table cell equal to a line number stays text.
    """
    import fitz  # PyMuPDF; imported lazily so the CLI loads without it

    pages: list[list[tuple[str, str]]] = []
    styles: list[list[bool]] = []
    with fitz.open(pdf) as doc:
        layouts = [_page_rows(page) for page in doc]
        strong_size, extent = _body_size(layouts) + 0.8, _text_extent(layouts)
        for page, rows_in in zip(doc, layouts):
            numbers = _margin_numbers(rows_in, extent)
            queues = _row_queues(rows_in, numbers, page.rect.width, strong_size)
            rows: list[tuple[str, str]] = []
            strong: list[bool] = []
            for raw in page.get_text().splitlines():
                line = raw.strip()
                if not line or _is_header(line):
                    continue
                queue = queues.get(line)
                anchor, styled = queue.pop(0) if queue else ("", False)
                if anchor != _MARGIN:
                    rows.append((anchor, line))
                    strong.append(styled)
            pages.append(rows)
            styles.append(strong)
    return pages, styles


def extract_lines(pdf: Path) -> list[list[tuple[str, str]]]:
    """Return per page a list of (anchor, text); anchor is 'L###' or '' (see `extract_pages`)."""
    return extract_pages(pdf)[0]


def render_pages(pages: list[list[tuple[str, str]]], label: str) -> str:
    """Render pages as text with page markers and line anchors."""
    out: list[str] = []
    for i, rows in enumerate(pages, start=1):
        out.append(f"===== [{label} p.{i}] =====")
        out.extend(f"{a:<6}{t}" for a, t in rows)
    return "\n".join(out) + "\n"


def _squash(text: str) -> str:
    """Lower-case text without spaces: small caps can extract as 'A BSTRACT' or 'R ELATED W ORK'."""
    return re.sub(r"\s+", "", text).lower()


def _canonical(name: str, seen_experiments: bool) -> str:
    """Map a heading to a section key; unnamed sections are method before experiments, analysis after."""
    low, squashed = name.lower(), _squash(name)
    for key, words in _KEYWORDS:
        if any(w in low or w.replace(" ", "") in squashed for w in words):
            return key
    return "ablations_analysis" if seen_experiments else "method"


def _heading_shape(title: str) -> bool:
    """Starts like a title (capital letter or '3D'), mostly letters (not a formula), no '#' (headers)."""
    visible = title.replace(" ", "")
    letters = sum(ch.isalpha() for ch in visible)
    return (bool(_TITLE_START.match(title)) and (title[0].isupper() or title[0].isdigit())
            and letters >= 3 and letters >= 0.6 * len(visible) and "#" not in title)


def _heading_like(title: str) -> bool:
    """A section title rather than a sentence (short, no sentence punctuation at the end)."""
    return (_heading_shape(title) and len(title.split()) <= _MAX_HEADING_WORDS
            and not title.endswith((".", ",", ";", ":")))


def is_heading_row(text: str) -> bool:
    """Whether one row reads as a numbered heading ('2. Method', '3 EXPERIMENTS')."""
    match = _TOP_HEADING.match(text)
    return bool(match) and _heading_like(match.group(2))


def _candidates(flat: list[tuple[int, str, str]], strong: Optional[list[bool]]) -> dict[int, Candidate]:
    """Rows that may open a numbered top-level section, by row index.

    Two forms: one row ('1. Introduction', '1 INTRODUCTION') or a number row followed by its title on
    the same page. A heading-styled title may be long or end in punctuation (a wrapped heading). A
    candidate is doubtful when its number follows a numeric row (axis labels, but also the last cell
    of a table) or sits on the first row of its page and equals the page number (a page header).
    """
    out: dict[int, Candidate] = {}
    for idx, (page, _, text) in enumerate(flat):
        first_on_page = idx == 0 or flat[idx - 1][0] != page
        match = _TOP_HEADING.match(text) or _SECTION_NO.match(text)
        if not match:
            continue
        number, two_rows = int(match.group(1)), match.re is _SECTION_NO
        if two_rows and (idx + 1 >= len(flat) or flat[idx + 1][0] != page):
            continue
        title = flat[idx + 1][2] if two_rows else match.group(2)
        styled = strong is not None and strong[idx + int(two_rows)]
        if _heading_like(title) or (styled and _heading_shape(title)):
            doubtful = ((first_on_page and number == page)
                        or (not first_on_page and bool(_NUMERIC.match(flat[idx - 1][2]))))
            out[idx] = (number, title, 2 if two_rows else 1, doubtful)
    return out


def _styled_only(cands: dict[int, Candidate], strong: Optional[list[bool]]) -> dict[int, Candidate]:
    """Keep candidates whose title row is heading-styled when the paper styles at least two of them."""
    if strong is None:
        return cands
    styled = {i: c for i, c in cands.items() if strong[i + c[2] - 1]}
    return styled if len({c[0] for c in styled.values()}) >= 2 else cands


def _clean_later(cands: dict[int, Candidate], start: int, number: int, stop: int) -> bool:
    """Whether a not-doubtful candidate for `number` follows `start` before section `number + 1` opens."""
    for idx in sorted(k for k in cands if start < k < stop and not cands[k][3]):
        if cands[idx][0] == number:
            return True
        if cands[idx][0] == number + 1:
            return False
    return False


def detect_sections(pages: list[list[tuple[str, str]]], styles: Optional[list[list[bool]]] = None
                    ) -> list[dict]:
    """Find title, abstract, numbered top-level sections and references in the main paper.

    Section numbers must appear in order (1, 2, 3, ...) and after the abstract heading when there is
    one; this guards against numbered list items, author affiliations, axis labels and page numbers
    that look like headings. `styles` (from `extract_pages`) adds the font check.
    """
    flat: list[tuple[int, str, str]] = [
        (p, a, t) for p, rows in enumerate(pages, start=1) for a, t in rows
    ]
    strong = [s for page in styles for s in page] if styles is not None else None
    refs = next((i for i, (_, _, t) in enumerate(flat)
                 if t[:1] in "RB" and _REFERENCES.match(_squash(t))), len(flat))
    abstract = next((i for i, (p, _, t) in enumerate(flat[:refs])
                     if p <= 2 and t[:1] == "A" and _ABSTRACT.match(_squash(t))), None)
    cands = _styled_only(_candidates(flat[:refs], strong), strong)
    marks: list[dict] = []
    if abstract is not None:
        marks.append({"key": "abstract", "heading": "Abstract", "page": flat[abstract][0], "idx": abstract})
    expected = 1
    seen_exp = False
    idx = 0 if abstract is None else abstract + 1
    while idx < refs:
        page = flat[idx][0]
        cand = cands.get(idx)
        if cand and cand[0] == expected and not (cand[3] and _clean_later(cands, idx, expected, refs)):
            heading, used = cand[1], cand[2]
            if heading.endswith("-") and idx + used < len(flat):
                heading = heading[:-1] + flat[idx + used][2]
            key = _canonical(heading, seen_exp)
            seen_exp |= key == "experiments"
            marks.append({"key": key, "heading": f"{expected}. {heading}", "page": page, "idx": idx})
            expected += 1
            idx += used
            continue
        idx += 1
    if refs < len(flat):
        marks.append({"key": "references", "heading": "References", "page": flat[refs][0], "idx": refs})
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
