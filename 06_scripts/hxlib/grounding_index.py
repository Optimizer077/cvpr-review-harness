"""Paper index for the grounding check (stdlib only).

Built from a round snapshot (`paper_main.txt`, `paper_supp.txt`, `captions.json`, `sections.json`,
`figures/figures.json`), the index holds what a reviewer's citations are checked against:

- normalized text streams of the main paper and the supplement, with a map back to page and `L###`.
  Normalization drops case, whitespace, punctuation, quote and dash styles, accents and line-end
  hyphenation, and expands ligatures, so "repre-\\nsentation" and "ﬁne" match "representation"
  and "fine";
- the `L###` anchors and page count of each document;
- the figure, table and equation numbers and the section numbers the paper has (from captions, the
  figure inventory, equation numbers at line ends, headings, and the paper's own cross-references).

The reference patterns live here because the paper side and the review side share them.
"""
from __future__ import annotations

import bisect
import json
import logging
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable, Optional

logger = logging.getLogger(__name__)

ANCHOR_SLACK = 30      # lines: margin numbers beside graphics or blank lines carry no text row
ANCHOR_DENSITY = 0.3   # share of numbers in [min, max] present for a numbering to count as dense
_LIGATURE_LETTERS = re.compile("ffi|ffl|ff|fi|fl")
_PAGE_MARK = re.compile(r"^===== \[(main|supp) p\.(\d+)\] =====\s*$")
_ANCHOR = re.compile(r"^L(\d{3,4})$")
_SEP = r"\s*(?:,|and|&|or|-|–|to)\s*"
_REF_TOKEN = r"(?:(?-i:[A-Z])\.?)?\d{1,3}"
REF_PATTERN = re.compile(
    r"(?P<supp>\bsupp(?:lementary|l)?\.?\s+)?"
    r"\b(?P<kw>figures?|figs?\.|fig(?=\s*\d)|tables?|tabs?\.|tab(?=\s*\d)|equations?|eqns?\.|eqs?\.|"
    r"eqn?(?=\s*\(?\d))"
    rf"\s*~?\s*(?P<list>\(?{_REF_TOKEN}[a-z]?\)?(?:{_SEP}\(?{_REF_TOKEN}[a-z]?\)?)*)",
    re.IGNORECASE)
_SEC_TOKEN = r"(?:(?-i:[A-Z])|\d{1,2})(?:\.\d{1,2}){0,3}"
SEC_PATTERN = re.compile(
    r"(?:\b(?P<kw>sections?|secs?\.|sec(?=\s*\d)|sect\.|appendix|appendices|app\.)|(?P<sign>§§?))\s*~?\s*"
    rf"(?P<list>{_SEC_TOKEN}(?:{_SEP}{_SEC_TOKEN})*)(?![\w])",
    re.IGNORECASE)
_PLURAL_KW = {"figures", "figs", "tables", "tabs", "equations", "eqs", "eqns", "sections", "secs",
              "appendices"}
_EQ_AT_END = re.compile(r"\(((?:[A-Z]\.?)?\d{1,3})[a-z]?\)\s*$")
_CAPTION = re.compile(r"^\s*(Figure|Fig\.|Table)\s*((?:[A-Z]\.?)?\d{1,3})")
_NUM_HEADING = re.compile(r"^(\d{1,2}(?:\.\d{1,2}){0,3})\.?\s+[A-Z]")
# A heading line: a section id, then a title of letters only (no digits, commas or final period).
_SECTION_ID = r"(?:[1-9]\d?(?:\.\d{1,2}){0,3}|[A-Z](?:\.\d{1,2}){0,3})"
_TITLE = r"[A-Z][A-Za-z'-]*(?:\s+(?:[A-Za-z'-]+|&|:))*\s*:?"
_HEADING_LINE = re.compile(rf"^({_SECTION_ID})\.?\s+{_TITLE}$")
_ID_LINE = re.compile(rf"^({_SECTION_ID})\.?$")  # "1" / "Introduction" extracted as two lines
_TITLE_LINE = re.compile(rf"^{_TITLE}$")
_HEADING_MAX_CHARS = 80


def compact(text: str) -> str:
    """Lower-case alphanumerics only: NFKD expands ligatures and strips accents; everything else
    (whitespace, punctuation, quote and dash styles, line-end hyphens) is dropped."""
    return "".join(ch for ch in unicodedata.normalize("NFKD", text).casefold() if ch.isalnum())


def ligature_blind(stream: str) -> str:
    """A compact stream without the letter pairs that PDF ligatures cover (some PDFs drop or garble
    the ligature glyph, so "eﬀect" extracts as "eect")."""
    return _LIGATURE_LETTERS.sub("", stream)


def kind_of(keyword: str) -> str:
    """'figure', 'table' or 'equation' for a reference keyword such as 'Fig.' or 'Eqs.'."""
    low = keyword.lower()
    return "figure" if low.startswith("fig") else "table" if low.startswith("tab") else "equation"


def ref_tokens(keyword: str, listing: str) -> list[str]:
    """Normalized numbers of a reference list ('Figs. 3 and 4' -> ['3', '4']; 'Eq. (S2)' -> ['S2']).

    A singular keyword stops at the first comma ('Table 3, 5 of 8 methods' -> ['3'])."""
    if keyword.lower().rstrip(".") not in _PLURAL_KW:
        listing = listing.split(",")[0]
    return [t.upper().replace(".", "") for t in re.findall(r"((?:[A-Z]\.?)?\d{1,3})", listing)]


def sec_tokens(keyword: str, listing: str) -> list[str]:
    """Section ids of a section reference ('Secs. 3.1 and 4' -> ['3.1', '4'])."""
    if keyword.lower().rstrip(".") not in _PLURAL_KW:
        listing = listing.split(",")[0]
    return re.findall(r"(?:[A-Z]|\d{1,2})(?:\.\d{1,2}){0,3}", listing)


@dataclass
class Corpus:
    """One normalized text stream with a map from stream offsets back to the source lines."""

    name: str
    stream: str = ""
    starts: list[int] = field(default_factory=list)
    lines: list[tuple[int, str, str]] = field(default_factory=list)  # (page, anchor, raw text)
    blind: str = field(init=False, default="")  # `stream` without ff/fi/fl/ffi/ffl (lost ligature glyphs)

    def __post_init__(self) -> None:
        self.blind = ligature_blind(self.stream)

    @classmethod
    def from_lines(cls, name: str, lines: Iterable[tuple[int, str, str]]) -> "Corpus":
        """Build the stream; line ends join directly, which removes line-end hyphenation."""
        rows = list(lines)
        parts: list[str] = []
        starts: list[int] = []
        pos = 0
        for _page, _anchor, text in rows:
            starts.append(pos)
            part = compact(text)
            parts.append(part)
            pos += len(part)
        return cls(name, "".join(parts), starts, rows)

    @classmethod
    def from_text(cls, name: str, text: str) -> "Corpus":
        """A corpus without pages or anchors (author answers, earlier review texts)."""
        return cls.from_lines(name, ((0, "", line) for line in text.splitlines()))

    def _line(self, pos: int) -> int:
        return max(bisect.bisect_right(self.starts, pos) - 1, 0)

    def where(self, pos: int) -> str:
        """'main p.3 L123' for a stream offset ('' for a corpus without pages)."""
        if not self.lines:
            return ""
        page, anchor, _ = self.lines[self._line(pos)]
        if not page:
            return self.name
        return f"{self.name} p.{page}" + (f" {anchor}" if anchor else "")

    def excerpt(self, start: int, end: int, limit: int = 240) -> str:
        """Raw text of the lines that cover stream offsets [start, end), shortened to `limit`."""
        if not self.lines:
            return ""
        first, last = self._line(start), self._line(max(end - 1, start))
        text = " ".join(t.strip() for _, _, t in self.lines[first:last + 1])
        return text if len(text) <= limit else text[:limit - 3] + "..."


@dataclass
class PaperIndex:
    """What a review's quotes and references are checked against."""

    corpora: list[Corpus]
    pages: dict[str, int]
    anchors: dict[str, list[int]]  # sorted L### numbers per document
    refs: dict[str, set[str]]
    sections: set[str]

    def anchor_ok(self, number: int) -> bool:
        """Whether line `number` exists: within a dense numbering (CVPR margin numbers) or close to an
        extracted anchor. Margin numbers next to graphics have no text row, hence the slack."""
        for nums in self.anchors.values():
            if not nums:
                continue
            lo, hi = nums[0], nums[-1]
            dense = len(nums) >= 10 and len(nums) >= ANCHOR_DENSITY * (hi - lo + 1)
            if dense and lo - ANCHOR_SLACK <= number <= hi + ANCHOR_SLACK:
                return True
            k = bisect.bisect_left(nums, number)
            near = [nums[i] for i in (k - 1, k) if 0 <= i < len(nums)]
            if any(abs(number - n) <= ANCHOR_SLACK for n in near):
                return True
        return False

    def anchor_span(self) -> str:
        """'L003-L053' style description of the extracted line anchors."""
        spans = [f"{doc} L{nums[0]:03d}-L{nums[-1]:03d}" for doc, nums in self.anchors.items() if nums]
        return ", ".join(spans) or "no line numbers"

    def max_number(self, kind: str) -> int:
        """Largest plain number known for a reference kind (0 when none)."""
        return max((int(t) for t in self.refs.get(kind, set()) if t.isdigit()), default=0)


def _parse_paper_text(text: str, doc: str) -> list[tuple[int, str, str]]:
    """(page, anchor, text) rows of a `paper_main.txt` / `paper_supp.txt` file."""
    rows: list[tuple[int, str, str]] = []
    page = 1
    for line in text.splitlines():
        mark = _PAGE_MARK.match(line)
        if mark:
            page = int(mark.group(2)) if mark.group(1) == doc else page
            continue
        head = line[:6].strip()
        if _ANCHOR.match(head):
            rows.append((page, head, line[6:].strip()))
        elif line.strip():
            rows.append((page, "", line.strip()))
    return rows


def plain_paper_text(text: str, doc: str = "main") -> str:
    """A snapshot text file without page markers and `L###` anchors (for earlier drafts)."""
    return "\n".join(t for _, _, t in _parse_paper_text(text, doc))


def _read_json(path: Path) -> Any:
    """Parsed JSON or None when the file is missing or unreadable."""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        logger.warning("grounding: cannot read %s: %s", path, exc)
        return None


def _paper_mentions(text: str, refs: dict[str, set[str]], sections: set[str]) -> None:
    """Add the paper's own Fig./Tab./Eq./Sec. cross-references to the known sets."""
    for match in REF_PATTERN.finditer(text):
        refs[kind_of(match.group("kw"))].update(ref_tokens(match.group("kw"), match.group("list")))
    for match in SEC_PATTERN.finditer(text):
        sections.update(sec_tokens(match.group("kw") or "sections", match.group("list")))


def _known_items(snapshot: Path, rows: dict[str, list[tuple[int, str, str]]]) -> tuple[dict[str, set[str]], set[str]]:
    """Figure/table/equation numbers and section ids the paper has."""
    refs: dict[str, set[str]] = {"figure": set(), "table": set(), "equation": set()}
    sections: set[str] = set()
    for cap in _read_json(snapshot / "captions.json") or []:
        match = _CAPTION.match(str(cap.get("text", ""))) if isinstance(cap, dict) else None
        if match:
            refs["table" if match.group(1) == "Table" else "figure"].add(match.group(2).replace(".", ""))
    for item in _read_json(snapshot / "figures" / "figures.json") or []:
        if isinstance(item, dict) and item.get("kind") in ("figure", "table") and item.get("number"):
            refs[item["kind"]].add(str(item["number"]).upper().replace(".", ""))
    for entry in _read_json(snapshot / "sections.json") or []:
        match = _NUM_HEADING.match(str(entry.get("heading", ""))) if isinstance(entry, dict) else None
        if match:
            sections.add(match.group(1))
    for doc_rows in rows.values():
        previous = ""
        for _page, _anchor, text in doc_rows:
            eq = _EQ_AT_END.search(text)
            if eq:
                refs["equation"].add(eq.group(1).upper().replace(".", ""))
            if len(text) <= _HEADING_MAX_CHARS:
                heading = _HEADING_LINE.match(text)
                split = _ID_LINE.match(previous) if _TITLE_LINE.match(text) else None
                sections.update(m.group(1) for m in (heading, split) if m)
            previous = text
        _paper_mentions(" ".join(t for _, _, t in doc_rows), refs, sections)
    return refs, sections


def build_index(snapshot: Path) -> PaperIndex:
    """Index a round snapshot; raises FileNotFoundError without `paper_main.txt`."""
    if not (snapshot / "paper_main.txt").exists():
        raise FileNotFoundError(f"no paper_main.txt in {snapshot}")
    texts = {doc: (snapshot / f"paper_{doc}.txt").read_text(encoding="utf-8")
             for doc in ("main", "supp") if (snapshot / f"paper_{doc}.txt").exists()}
    rows = {doc: _parse_paper_text(text, doc) for doc, text in texts.items()}
    pages = {doc: sum(1 for line in text.splitlines() if _PAGE_MARK.match(line)) for doc, text in texts.items()}
    anchors = {doc: sorted({int(a[1:]) for _, a, _ in doc_rows if a}) for doc, doc_rows in rows.items()}
    refs, sections = _known_items(snapshot, rows)
    corpora = [Corpus.from_lines(doc, doc_rows) for doc, doc_rows in rows.items()]
    return PaperIndex(corpora, pages, anchors, refs, sections)


_CACHE: dict[tuple[str, float], PaperIndex] = {}


def load_index(snapshot: Path) -> PaperIndex:
    """`build_index` with a per-process cache keyed by path and paper_main.txt mtime."""
    key = (str(snapshot.resolve()), (snapshot / "paper_main.txt").stat().st_mtime)
    if key not in _CACHE:
        _CACHE[key] = build_index(snapshot)
    return _CACHE[key]


def _aligned_ratio(needle: str, window: str) -> tuple[float, int, int]:
    """difflib ratio of `needle` against the part of `window` it aligns to (unmatched ends included)."""
    blocks = [m for m in SequenceMatcher(None, window, needle, autojunk=False).get_matching_blocks()
              if m.size >= 3]
    if not blocks:
        return 0.0, 0, 0
    start = max(0, blocks[0].a - blocks[0].b)
    end = min(len(window), blocks[-1].a + blocks[-1].size + len(needle) - blocks[-1].b - blocks[-1].size)
    return SequenceMatcher(None, window[start:end], needle, autojunk=False).ratio(), start, end


def fuzzy_find(needle: str, stream: str, max_candidates: int = 8) -> tuple[float, int, int]:
    """Best (ratio, start, end) of `needle` over windows of `stream`.

    Candidate windows come from short shingles of the needle found verbatim in the stream (votes per
    position bucket), so only a few windows are compared with difflib."""
    size = len(needle)
    if size < 8 or not stream:
        return 0.0, -1, -1
    gram = 6 if size < 60 else 8
    bucket = max(8, size // 3)
    votes: Counter = Counter()
    for off in range(0, size - gram + 1, max(1, gram // 2)):
        piece, hits = needle[off:off + gram], 0
        pos = stream.find(piece)
        while pos >= 0 and hits < 50:
            votes[max(0, pos - off) // bucket] += 1
            pos, hits = stream.find(piece, pos + 1), hits + 1
    best = (0.0, -1, -1)
    ranked = votes.most_common(max_candidates)
    for slot, count in ranked:
        if count < ranked[0][1] * 0.25:
            break
        lo = max(0, slot * bucket - size // 2)
        hi = min(len(stream), slot * bucket + bucket + size + size // 2)
        ratio, start, end = _aligned_ratio(needle, stream[lo:hi])
        if ratio > best[0]:
            best = (ratio, lo + start, lo + end)
    return best


def search(needle: str, corpora: list[Corpus]) -> tuple[float, Optional[Corpus], int, int]:
    """Exact substring first (ratio 1.0; ligature letters ignored as a second try), else the best
    fuzzy window over all corpora. Offsets of a ligature-blind hit are estimated proportionally."""
    for corpus in corpora:
        pos = corpus.stream.find(needle)
        if pos >= 0:
            return 1.0, corpus, pos, pos + len(needle)
    blind = ligature_blind(needle)
    for corpus in corpora:
        pos = corpus.blind.find(blind) if len(blind) >= len(needle) * 0.8 else -1
        if pos >= 0:
            scale = len(corpus.stream) / max(len(corpus.blind), 1)
            return 1.0, corpus, int(pos * scale), int((pos + len(blind)) * scale)
    best: tuple[float, Optional[Corpus], int, int] = (0.0, None, -1, -1)
    for corpus in corpora:
        ratio, start, end = fuzzy_find(needle, corpus.stream)
        if ratio > best[0]:
            best = (ratio, corpus, start, end)
    return best
