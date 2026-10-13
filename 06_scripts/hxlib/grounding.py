"""Grounding check: are a review's quotes, line anchors, pages and Fig./Tab./Eq./Sec. references
anchored in the paper? (stdlib only)

LLM reviewers fabricate or alter quotes and cite lines, pages, figures and sections that do not
exist (reviewer_common.md rules 3-5). `check_grounding` checks one review (review.json or
satisfaction.json, plus review.md or reply.md) against the round snapshot:

- quotes: double-quoted strings (straight or curly) of at least MIN_QUOTE_WORDS words, presented as
  paper text, are matched against the normalized main paper and supplement. Exact substring ->
  `verified`; difflib ratio >= NEAR_RATIO on the best window -> `near` (an altered quote or PDF
  extraction noise); otherwise `not_found`. Quotes marked as paraphrase, as the reviewer's own or
  proposed wording, and quoted titles of cited papers are skipped. Under `figure_scores` and on
  figure-tagged weaknesses a quote may be text inside an image: not found there -> `image_text`.
- references: `L###` anchors and "lines N-M", page numbers, Fig./Tab./Eq. numbers, Sec./Appendix
  ids and quoted section names that the paper does not have.

Proposal fields (suggested_fix, would_change_mind, one_point_fix, remaining_ask) are not checked:
they describe text or figures the reviewer wants added. Results are warnings, never failures.

CLI (before integration): python 06_scripts/hxlib/grounding.py <round_dir> [--write]
"""
from __future__ import annotations

import json
import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Optional

if __package__ in (None, ""):  # run as a script: make `hxlib` importable
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from hxlib.grounding_index import (REF_PATTERN, SEC_PATTERN, Corpus, PaperIndex, compact,  # noqa: E402
                                       kind_of, load_index, ref_tokens, search, sec_tokens)
else:
    from .grounding_index import (REF_PATTERN, SEC_PATTERN, Corpus, PaperIndex, compact, kind_of,
                                  load_index, ref_tokens, search, sec_tokens)

logger = logging.getLogger(__name__)

MIN_QUOTE_WORDS = 6
NEAR_RATIO = 0.9
MIN_FRAGMENT_CHARS = 12
_SKIP_KEYS = frozenset({"job_id", "reviewer_id", "round", "stage", "paper_sha256", "id", "severity",
                        "category", "fixable_by", "decisive", "defect", "figure_id", "role", "status",
                        "verdict", "profile", "reading", "criteria", "score", "rating", "confidence",
                        "previous_rating"})
_PROPOSAL_KEYS = frozenset({"suggested_fix", "would_change_mind", "one_point_fix", "remaining_ask"})
_LOCATION_KEYS = frozenset({"location", "evidence"})

_STRAIGHT = re.compile(r'(?<![\w"])"(?![\s"])((?:[^"\n]|\n(?![ \t]*\n))+?)(?<!\s)"(?!\w)')
_CURLY = re.compile(r"“((?:[^”“\n]|\n(?![ \t]*\n))+?)”")
_SENTENCE_END = re.compile(r"(?<=[a-z0-9)][.!?])\s+(?=[A-Z*#])|\n")
_FRAGMENT_SPLIT = re.compile(r"\s*(?:\.{3}|…|\[[^\]]{0,60}\])\s*")
_OWN_WORDS = re.compile(
    r"paraphras|\bin other words\b|\bsomething (?:like|along)\b|\balong the lines of\b|"
    r"\bto the effect (?:of|that)\b|\bmy (?:own )?(?:words|wording|summary|paraphrase|reading|term)\b|"
    r"\b(?:i|we) (?:would|'d|might|could) (?:call|describe|say|write|phrase|summari[sz]e|put|frame)\b|"
    r"\b(?:describ|call|label|dubb?|characteri[sz]|summari[sz])(?:e|es|ed|ing|s)? "
    r"(?:it|this|that|them|these|the \w+(?: \w+)?) as\b|"
    r"\b(?:replac|rewrit|rephras|reword|renam|retitl|soften)\w*|"
    r"\b(?:should|could|would|might|please|instead)\b[^\"“”]{0,40}\b(?:write|say|state|read|phrase|add|"
    r"include|insert)\w*\b|"
    r"\b(?:add|adding|insert|inserting|include|including|introduce)\b[^\"“”]{0,40}\b(?:sentence|phrase|"
    r"statement|caveat|clarification|note|footnote|claim|disclaimer|remark)s?\b|"
    r"\b(?:a|one|the|new) (?:sentence|phrase|statement|claim|wording|title|caption|caveat) "
    r"(?:like|such as|e\.g\.)|"
    r"\b(?:i|we) (?:suggest|recommend|propose)\w*|\bsuggest(?:ion|ed)\b|"
    r"\bconsider (?:writing|saying|stating|phrasing|adding)\b|\bhypothetical\b|\bimagine\b",
    re.IGNORECASE)
_OWN_WORDS_AFTER = re.compile(r"^\W{0,3}(?:paraphras\w*|my (?:words|wording|paraphrase)|not (?:a )?verbatim|"
                              r"approximately|roughly|or similar|or words to that effect)", re.IGNORECASE)
_CITATION_BEFORE = re.compile(r"(?:\bet al\.?|\b(?:en)?titled|\bcf\.)[^\"“”]{0,25}$", re.IGNORECASE)
_CITATION_AFTER = re.compile(
    r"^\W{0,4}(?:\(?(?:19|20)\d{2}\b|(?:in\s+)?(?:Proc\.|CVPR|ICCV|ECCV|NeurIPS|NIPS|ICML|ICLR|AAAI|IJCAI|"
    r"T?PAMI|TIP|TOG|SIGGRAPH|arXiv|ACL|EMNLP|NAACL|BMVC|WACV|3DV|IJCV|JMLR|TMLR)\b)")
_ANCHOR = re.compile(r"\bL(?P<a>\d{1,4})(?:\s*(?:-|–|—|to)\s*L?(?P<b>\d{1,4}))?\b")
_LINES = re.compile(r"\b(?:lines?|ll\.)\s*(?P<a>\d{1,4})(?:\s*(?:-|–|—|to|and)\s*(?P<b>\d{1,4}))?\b",
                    re.IGNORECASE)
# The *_AFTER patterns below are applied with `.match(text, pos)`, so they carry no `^`.
_NOT_MARGIN_LINE = re.compile(r"\s*(?:of|in)\s+(?:the\s+)?(?:alg|pseudo|listing|code|eq|tab|fig|appendix)",
                              re.IGNORECASE)
_NORM_AFTER = re.compile(r"\s*-?\s*(?:loss|norm|dist|error|penalt|regulari|reg\b|space|ball|cache|metric|"
                         r"objective|term|sensitiv|bound|constraint|weight|similar|attention|smooth)",
                         re.IGNORECASE)
_PAGE = re.compile(r"(?P<supp>\bsupp\w*\.?\s+)?\b(?:pp?\.|pages?|pg\.)\s*(?P<a>\d{1,3})"
                   r"(?:\s*(?:-|–|to)\s*(?P<b>\d{1,3}))?(?![\d.]\d)", re.IGNORECASE)
_SUPP_AFTER = re.compile(r"\s*(?:of|in)\s+(?:the\s+)?(?:supp|appendi)", re.IGNORECASE)
_CITATION_BEFORE_PAGE = re.compile(r"(?:\b(?:19|20)\d{2}\b|\bProc\.|\bvol\.|\bJournal\b|\bTrans\.|\bet al\b)"
                                   r"[^\n]{0,50}$", re.IGNORECASE)
_OTHER_WORK_AFTER = re.compile(r"[^.;\n]{0,8}?\b(?:of|in|from)\s+(?:\[\d|ref\.|their\b|prior\b|"
                               r"the (?:original|cited|baseline)\b|[A-Z][\w-]+(?:\s+et al\b|\s*\[\d))")
_NEW_ITEM_BEFORE = re.compile(r"\b(?:add|adding|new|additional|extra|another|include|including|introduce|"
                              r"missing|separate)\b\W+(?:\w+\W+){0,2}$", re.IGNORECASE)
_SEC_NAME = re.compile(r"(?:\b(?:sections?|sec\.|subsection)|§)\s*[\"“]([^\"”\n]{3,80})[\"”]|"
                       r"[\"“]([^\"”\n]{3,80})[\"”]\s+(?:sub)?section\b", re.IGNORECASE)
_TITLE_SEC = re.compile(r"\bthe\s+((?:[A-Z][\w-]*\s+){1,5})(?:sub)?section\b")
_GENERIC_WORDS = frozenset(
    "introduction related work works method methods methodology approach experiments experiment experimental "
    "results result evaluation conclusion conclusions discussion limitations limitation abstract analysis "
    "ablation ablations background preliminaries supplementary appendix references setup implementation "
    "details future broader impact ethics statement overview main first second last final previous next "
    "this that".split())


@dataclass(frozen=True)
class Field:
    """One reviewer-written string: where it sits, its JSON key, and whether it may quote image text."""

    path: str
    key: str
    text: str
    image: bool = False


def iter_fields(obj: Any, path: str = "", key: str = "", image: bool = False) -> Iterator[Field]:
    """Reviewer-written strings of a review/satisfaction JSON, skipping ids, enums and proposals."""
    if isinstance(obj, str):
        if obj.strip():
            yield Field(path, key, obj, image)
    elif isinstance(obj, dict):
        tagged = image or "figure_id" in obj
        for sub_key, value in obj.items():
            if sub_key in _SKIP_KEYS or sub_key in _PROPOSAL_KEYS:
                continue
            sub_path = f"{path}.{sub_key}" if path else str(sub_key)
            yield from iter_fields(value, sub_path, str(sub_key), tagged or sub_key == "figure_scores")
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            label = item.get("id", i) if isinstance(item, dict) else i
            yield from iter_fields(item, f"{path}[{label}]", key, image)


def _skip_reason(text: str, start: int, end: int) -> str:
    """Why a quoted span is not presented as paper text ('' when it is). Looks back to the start of
    the sentence (at most 120 characters) and 60 characters ahead."""
    before = _SENTENCE_END.split(text[max(0, start - 120):start])[-1]
    after = text[end:end + 60]
    if _CITATION_BEFORE.search(before) or _CITATION_AFTER.match(after):
        return "title of a cited work"
    if _OWN_WORDS.search(before) or _OWN_WORDS_AFTER.match(after):
        return "reviewer's own or proposed wording"
    return ""


def extract_quotes(text: str) -> list[tuple[str, str]]:
    """(quote, skip_reason) for every double-quoted span of at least MIN_QUOTE_WORDS words."""
    found: list[tuple[int, str, str]] = []
    for pattern in (_STRAIGHT, _CURLY):
        for match in pattern.finditer(text):
            quote = " ".join(match.group(1).split())
            if len(quote.split()) >= MIN_QUOTE_WORDS:
                found.append((match.start(), quote, _skip_reason(text, match.start(), match.end())))
    return [(quote, reason) for _, quote, reason in sorted(found)]


def classify_quote(quote: str, corpora: list[Corpus], image: bool = False) -> Optional[dict]:
    """verified / near / not_found (image_text) for one quote; None when nothing checkable remains."""
    frags = [c for c in (compact(f) for f in _FRAGMENT_SPLIT.split(quote)) if len(c) >= MIN_FRAGMENT_CHARS]
    if not frags:
        return None
    hits = [(frag, *search(frag, corpora)) for frag in frags]
    ratio = sum(len(f) * r for f, r, *_ in hits) / sum(len(f) for f in frags)
    status = ("verified" if all(r == 1.0 for _, r, *_ in hits)
              else "near" if ratio >= NEAR_RATIO else "image_text" if image else "not_found")
    _frag, best, corpus, start, end = max(hits, key=lambda h: len(h[0]))
    out = {"status": status, "ratio": round(ratio, 3), "source": ""}
    if corpus is not None and best >= NEAR_RATIO:
        out["source"] = corpus.name
        out["at"] = corpus.where(start)
        if status != "verified":
            out["paper_text"] = corpus.excerpt(start, end)
    return out


def _bad(kind: str, ref: str, field: Field, reason: str) -> dict:
    return {"kind": kind, "ref": ref, "where": field.path, "reason": reason}


def _check_anchors(field: Field, index: PaperIndex) -> Iterator[tuple[str, str, Optional[dict]]]:
    """('anchor', 'L123', problem or None) for every line anchor of a field."""
    text = field.text
    for pattern in (_ANCHOR, _LINES):
        for m in pattern.finditer(text):
            a, b = m.group("a"), m.group("b")
            if pattern is _ANCHOR and len(a) < 3 and b is None and field.key not in _LOCATION_KEYS:
                continue  # "L1 loss", "L2 norm": short L-numbers count only in location fields
            if _NORM_AFTER.match(text, m.end()) or (pattern is _LINES and _NOT_MARGIN_LINE.match(text, m.end())):
                continue
            for num in dict.fromkeys(int(x) for x in (a, b) if x):
                ok = index.anchor_ok(num)
                yield "anchor", f"L{num:03d}", None if ok else _bad(
                    "anchor", f"L{num:03d}", field, f"no such line (paper: {index.anchor_span()})")


def _check_pages(field: Field, index: PaperIndex) -> Iterator[tuple[str, str, Optional[dict]]]:
    """('page', 'p.3', problem or None) for every page number of a field."""
    text = field.text
    main, supp = index.pages.get("main", 0), index.pages.get("supp", 0)
    for m in _PAGE.finditer(text):
        if _CITATION_BEFORE_PAGE.search(text[max(0, m.start() - 60):m.start()]):
            continue  # "CVPR 2023, pp. 123-131": a citation, not this paper
        in_supp = bool(m.group("supp")) or bool(_SUPP_AFTER.match(text, m.end()))
        for num in dict.fromkeys(int(x) for x in (m.group("a"), m.group("b")) if x):
            ok = 1 <= num <= supp if in_supp else 1 <= num <= max(main, supp)
            label = f"{'supp ' if in_supp else ''}p.{num}"
            yield "page", label, None if ok else _bad(
                "page", label, field, f"paper has {main} main pages" + (f", {supp} supplement pages" if supp
                                                                      else ", no supplement"))


def _ref_ok(kind: str, token: str, index: PaperIndex, supp: bool) -> bool:
    known = index.refs[kind]
    if token in known or (supp and f"S{token}" in known):
        return True
    return token.isdigit() and 1 <= int(token) <= index.max_number(kind)


def _check_items(field: Field, index: PaperIndex) -> Iterator[tuple[str, str, Optional[dict]]]:
    """(kind, 'Fig. 3', problem or None) for every figure, table and equation number of a field."""
    text = field.text
    names = {"figure": "Fig.", "table": "Tab.", "equation": "Eq."}
    for m in REF_PATTERN.finditer(text):
        kind = kind_of(m.group("kw"))
        if (not index.refs.get(kind) or _NEW_ITEM_BEFORE.search(text[max(0, m.start() - 40):m.start()])
                or _OTHER_WORK_AFTER.match(text, m.end())):
            continue  # numbering unknown, "add a new Table 6", or "Fig. 5 of [12]"
        supp = bool(m.group("supp")) or bool(_SUPP_AFTER.match(text, m.end()))
        for token in dict.fromkeys(ref_tokens(m.group("kw"), m.group("list"))):
            label = f"{names[kind]} {token}"
            known = sorted(index.refs[kind], key=lambda t: (len(t), t))
            yield kind, label, None if _ref_ok(kind, token, index, supp) else _bad(
                kind, label, field, f"paper has {names[kind]} {', '.join(known)}")


def _run_max(values: set[int]) -> int:
    """Largest n of the run 1, 2, 3, ... in `values`, allowing single gaps (a missed heading)."""
    best, n = 0, 1
    while n <= max(values, default=0):
        if n in values:
            best = n
        elif n + 1 not in values:
            break
        n += 1
    return best


def _section_ok(token: str, known: set[str]) -> Optional[bool]:
    """Whether a section id exists; None when the paper's numbering cannot tell.

    Top-level numbers and appendix letters must fall inside the run 1, 2, 3, ... (A, B, C, ...) of
    known ids, which ignores stray matches such as table rows or author initials."""
    if token in known:
        return True
    head, *rest = token.split(".")
    if head.isdigit():
        tops = _run_max({int(k.split(".")[0]) for k in known if k.split(".")[0].isdigit()})
        if not tops:
            return None
        if int(head) > tops:
            return False
        subs = [int(k.split(".")[1]) for k in known if k.startswith(head + ".") and k.split(".")[1].isdigit()]
        return not (rest and rest[0].isdigit() and subs and int(rest[0]) > max(subs) + 1)
    letters = _run_max({ord(k[0]) - ord("A") + 1 for k in known if k[0].isalpha()})
    return ord(head) - ord("A") + 1 <= letters


def _check_sections(field: Field, index: PaperIndex) -> Iterator[tuple[str, str, Optional[dict]]]:
    """('section', 'Sec. 3.2', problem or None) for section ids and quoted / specific section names."""
    text = field.text
    for m in SEC_PATTERN.finditer(text):
        if _NEW_ITEM_BEFORE.search(text[max(0, m.start() - 40):m.start()]) or _OTHER_WORK_AFTER.match(text, m.end()):
            continue
        for token in dict.fromkeys(sec_tokens(m.group("kw") or "sections", m.group("list"))):
            ok = _section_ok(token, index.sections)
            if ok is not None:
                yield "section", f"Sec. {token}", None if ok else _bad("section", f"Sec. {token}", field,
                                                           "no such section in the paper")
    names = [a or b for a, b in _SEC_NAME.findall(text)]
    names += [n.strip() for n in _TITLE_SEC.findall(text)
              if not set(n.lower().split()) <= _GENERIC_WORDS]
    for name in dict.fromkeys(names):
        needle = compact(name)
        if len(needle) < 4:
            continue
        ratio = search(needle, index.corpora)[0]
        yield "section", f'section "{name}"', None if ratio >= NEAR_RATIO else _bad(
            "section", f'section "{name}"', field, "no heading or text with this name in the paper")


def check_fields(fields: list[Field], index: PaperIndex, extra: Optional[list[Corpus]] = None) -> dict:
    """Grounding findings for a list of fields (quotes de-duplicated by normalized text)."""
    corpora = index.corpora + list(extra or [])
    quotes: list[dict] = []
    skipped: list[dict] = []
    seen_quotes: set[str] = set()
    bad: list[dict] = []
    checked: dict[str, set[str]] = {}
    for fld in fields:
        for quote, reason in extract_quotes(fld.text):
            key = compact(quote)
            if key in seen_quotes:
                continue
            seen_quotes.add(key)
            result = None if reason else classify_quote(quote, corpora, fld.image)
            if result is None:
                skipped.append({"quote": quote[:300], "where": fld.path, "reason": reason or "too short"})
            else:
                quotes.append({"quote": quote[:300], "where": fld.path, **result})
        for checker in (_check_anchors, _check_pages, _check_items, _check_sections):
            for kind, label, problem in checker(fld, index):
                if label in checked.setdefault(kind, set()):
                    continue
                checked[kind].add(label)
                if problem:
                    bad.append(problem)
    return {"quotes": quotes, "skipped_quotes": skipped, "bad_refs": bad,
            "checked": {k: len(v) for k, v in checked.items()}, "totals": totals(quotes, skipped, bad)}


def totals(quotes: list[dict], skipped: list[dict], bad: list[dict]) -> dict[str, int]:
    """Counts per quote status and per kind of bad reference."""
    out = {"quotes": len(quotes), "skipped": len(skipped)}
    for status in ("verified", "near", "not_found", "image_text"):
        out[status] = sum(1 for q in quotes if q["status"] == status)
    groups = {"bad_anchors": ("anchor",), "bad_pages": ("page",), "bad_refs": ("figure", "table", "equation"),
              "bad_sections": ("section",)}
    for name, kinds in groups.items():
        out[name] = sum(1 for b in bad if b["kind"] in kinds)
    return out


def check_grounding(review_json: dict, review_md: str, snapshot_dir: Path, *,
                    extra_texts: Optional[dict[str, str]] = None, md_name: str = "review.md") -> dict:
    """Check one review's quotes and references against a round snapshot.

    Args:
        review_json: parsed review.json or satisfaction.json.
        review_md: review.md (or reply.md) text; '' when absent.
        snapshot_dir: the round's `snapshot/` folder.
        extra_texts: name -> text of other material the reviewer was given and may quote (the
            authors' answers, an earlier draft); a quote found there is verified with that source.
        md_name: label of the markdown text in the findings ('reply.md' for an answer check).

    Returns:
        {"quotes": [...], "skipped_quotes": [...], "bad_refs": [...], "checked": {...}, "totals": {...}}
    """
    index = load_index(snapshot_dir)
    fields = list(iter_fields(review_json)) + ([Field(md_name, "markdown", review_md)] if review_md else [])
    extra = [Corpus.from_text(name, text) for name, text in (extra_texts or {}).items() if text]
    return check_fields(fields, index, extra)


def main(argv: Optional[list[str]] = None) -> int:
    """Print the grounding summary of a round folder; `--write` also writes GROUNDING.md."""
    args = list(sys.argv[1:] if argv is None else argv)
    write = "--write" in args
    args = [a for a in args if a != "--write"]
    if len(args) != 1 or not (Path(args[0]) / "ROUND.json").exists():
        print("usage: python 06_scripts/hxlib/grounding.py <round_dir> [--write]", file=sys.stderr)
        return 2
    logging.basicConfig(level=logging.WARNING)
    if __package__ in (None, ""):
        from hxlib.grounding_report import grounding_summary, job_line, round_grounding, write_grounding_md
    else:
        from .grounding_report import grounding_summary, job_line, round_grounding, write_grounding_md
    round_path = Path(args[0])
    rnd = json.loads((round_path / "ROUND.json").read_text(encoding="utf-8"))
    result = round_grounding(rnd, round_path)
    print(grounding_summary(result))
    for job_id, findings in result["jobs"].items():
        print(f"  {job_line(job_id, findings)}")
    if write:
        print(f"wrote {write_grounding_md(result, round_path)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
