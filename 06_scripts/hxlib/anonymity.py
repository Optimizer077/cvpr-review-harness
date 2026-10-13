"""Double-blind check: find text in a submission PDF that could reveal who wrote it.

Venues with double-blind review (CVPR, ICCV, ECCV, ICLR, ICML, NeurIPS) reject or desk-reject papers
that identify their authors. Reviewer agents notice these leaks but cannot fix them, and a
de-anonymized paper also biases the simulated reviews. The scan reports what a careful area chair
would notice; the author decides what to change. Patterns are deliberately conservative: each flag
quotes the matched text and its page so it can be checked in seconds. Citations to other people's
work (reference list, arXiv ids of cited papers, links to baseline code) are not flagged.
"""
from __future__ import annotations

import logging
import re
from typing import Iterable

logger = logging.getLogger(__name__)

# Stamps that only appear on accepted, published or preprint versions of the paper itself.
_STAMPS = (
    (re.compile(r"open access version, provided by the computer vision foundation", re.I),
     "camera-ready watermark (CVF Open Access)"),
    (re.compile(r"identical to the accepted version", re.I), "camera-ready watermark (accepted version)"),
    (re.compile(r"\barXiv:\d{4}\.\d{4,5}v\d+\s*\[[\w.-]+\]"), "arXiv preprint stamp"),
    (re.compile(r"published as a conference paper at", re.I), "camera-ready header (published)"),
    (re.compile(r"(©|\(c\)|copyright)\s*(19|20)\d\d\b", re.I), "copyright line"),
    (re.compile(r"\b(camera[- ]ready|accepted (at|to|by) (CVPR|ICCV|ECCV|ICLR|ICML|NeurIPS))\b", re.I),
     "acceptance statement"),
)
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+(\.[\w-]+)+\b")
_AFFILIATION = re.compile(r"\b(University|Universit[äaé]t?|Institute|Instituto|Laborator(y|ies)|College|"
                          r"School of|Department of|Research (Lab|Center|Centre)|Inc\.|Ltd\.|Corporation|GmbH)\b")
_ACK_HEADING = re.compile(r"^\s*(\d+\.?\s*)?acknowledge?ments?\b", re.I)
_REFERENCES = re.compile(r"^\s*(\d+\.?\s*)?(references|bibliography)\s*$", re.I)
_APPENDIX = re.compile(r"^\s*(appendix|supplementary material|[A-Z]\.\s+[A-Z][a-z])", re.I)
_GRANT = re.compile(r"\b(grant|award)\s*(no\.?|number|#)\s*[A-Z0-9-]{3,}", re.I)
_URL = re.compile(r"(https?://)?(www\.)?(github\.com|gitlab\.com|bitbucket\.org|huggingface\.co|"
                  r"sites\.google\.com|[\w-]+\.github\.io)(/[\w./~-]*)?", re.I)
_ANON_URL = re.compile(r"anonymous|4open\.science|anon[\w-]*\.", re.I)
_OWN_LINK = re.compile(r"\b(our|the) (code|implementation|project|website|models?|dataset)\b|"
                       r"code (is|will be) (publicly |made )?available|project page", re.I)
_SELF_CITE = re.compile(r"\b(our|we) (previous|prior|earlier) (work|paper|method)s?\s*\[\d", re.I)
_REVIEW_COPY = re.compile(r"anonymous|confidential review copy|submission #|paper id", re.I)


def _lines(pages: list[list[tuple[str, str]]]) -> Iterable[tuple[int, str, bool]]:
    """(page, text, in_references) for every line. The reference list ends at an appendix heading."""
    in_refs = False
    for pno, rows in enumerate(pages, start=1):
        for _anchor, text in rows:
            if _REFERENCES.match(text):
                in_refs = True
            elif in_refs and (_ACK_HEADING.match(text) or _APPENDIX.match(text)) and len(text) < 80:
                in_refs = False
            yield pno, text, in_refs


def _title_block(pages: list[list[tuple[str, str]]]) -> list[str]:
    """Lines of page 1 before the abstract heading (where an author block would be)."""
    out: list[str] = []
    for _anchor, text in pages[0] if pages else []:
        if text.strip().lower().rstrip(".") == "abstract":
            break
        out.append(text)
    return out


def scan_anonymity(pages: list[list[tuple[str, str]]], label: str = "main") -> list[str]:
    """Return human-readable flags like "main p.1: author email 'a@b.org'" (empty = nothing found)."""
    flags: list[str] = []

    def add(pno: int, what: str, text: str) -> None:
        flag = f"{label} p.{pno}: {what} {text.strip()[:70]!r}"
        if flag not in flags:
            flags.append(flag)

    title = set(_title_block(pages)) if label == "main" else set()
    for pno, text, in_refs in _lines(pages):
        for pattern, what in _STAMPS:
            match = pattern.search(text)
            if match:
                add(pno, what, match.group(0))
        if in_refs:
            continue
        if text in title or _OWN_LINK.search(text):
            for match in _URL.finditer(text):
                if not _ANON_URL.search(match.group(0)):
                    add(pno, "code/project URL presented as the authors' own", match.group(0))
        match = _SELF_CITE.search(text)
        if match:
            add(pno, "self-citation in the first person", match.group(0))
        if _ACK_HEADING.match(text) and len(text) < 80:
            add(pno, "acknowledgements section (remove for review)", text)
        match = _GRANT.search(text)
        if match:
            add(pno, "grant number", match.group(0))
    if title:
        anonymous = any(_REVIEW_COPY.search(t) for t in title)
        for text in title:
            for match in _EMAIL.finditer(text):
                add(1, "author email", match.group(0))
            if not anonymous and _AFFILIATION.search(text):
                add(1, "affiliation in the title block", text)
    return flags
