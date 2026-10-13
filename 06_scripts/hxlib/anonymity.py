"""Double-blind check: find text in a submission PDF that could reveal who wrote it.

Venues with double-blind review (CVPR, ICCV, ECCV, ICLR, ICML, NeurIPS) reject or desk-reject papers
that identify their authors. Reviewer agents notice these leaks but cannot fix them, and a
de-anonymized paper also biases the simulated reviews. The scan reports what a careful area chair
would notice; the author decides what to change. Patterns are deliberately conservative: each flag
quotes the matched text and its page so it can be checked in seconds. Citations to other people's
work (reference list, arXiv ids of cited papers, links to baseline code) are not flagged.

The snapshot stores the flags of `scan_document` (`ROUND.json` paper meta `anonymity_flags`).
`hx.py new` and `round` refuse a flagged copy unless `--allow-identified` is given
(`check_identified`); an allowed copy adds `IDENTIFIED_LINE` to every reviewer prompt
(`identified_line`).
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Iterable

logger = logging.getLogger(__name__)

IDENTIFIED_LINE = ("This copy shows author or publication information; the harness has recorded it. Do not "
                   "mention it in the review and do not let it change your rating.")

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
# 'Appendix', 'A. Proofs'; a reference line that starts with initials ('K. He, X. Zhang') has a comma.
_APPENDIX = re.compile(r"^\s*(?:(?i:appendix|supplementary material)|[A-Z]\.\s+[A-Z][a-z][^,]*$)")
# 'grant No. ABC-12345', 'Grants Nos. 62076123': the id must contain a digit ('grants notable' is prose).
_GRANT = re.compile(r"\b(?:grants?|awards?)\s*(?:nos?\.|nos?\b|numbers?\b|#)\s*(?=[\w-]*\d)[A-Z0-9-]{3,}", re.I)
_URL = re.compile(r"(https?://)?(www\.)?(github\.com|gitlab\.com|bitbucket\.org|huggingface\.co|"
                  r"sites\.google\.com|[\w-]+\.github\.io)(/[\w./~-]*)?", re.I)
_ANON_URL = re.compile(r"anonymous|4open\.science|anon[\w-]*\.", re.I)
# The authors' own artefact ('our code', 'code will be released'); 'the model from <URL>' is a baseline.
_OWN_LINK = re.compile(r"\bour (code|implementation|project|website|models?|dataset)\b|"
                       r"\b(code|implementation) (is|will be) (publicly |made )?(available|released)\b|"
                       r"project page", re.I)
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
    """Return human-readable flags like "main p.1: author email 'a@b.test'" (empty = nothing found)."""
    flags: list[str] = []

    def add(pno: int, what: str, text: str) -> None:
        flag = _flag(label, pno, what, text)
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


_STAMP_LABELS = tuple(what for _pattern, what in _STAMPS)


def _flag(label: str, pno: int, what: str, text: str) -> str:
    """One flag line: document, page, what was found and the matched text."""
    return f"{label} p.{pno}: {what} {text.strip()[:70]!r}"


def scan_document(pages: list[list[tuple[str, str]]], pdf: Path, label: str = "main") -> list[str]:
    """`scan_anonymity` plus publication stamps in the raw PDF text.

    Text extraction drops running headers ('Published as a conference paper at ICLR 2024'), so the
    raw text of every page is searched for each stamp kind the extracted text did not show; a
    stamp repeated on every page is reported once.
    """
    import fitz  # PyMuPDF; imported lazily so the CLI loads without it

    flags = scan_anonymity(pages, label)
    seen = {what for what in _STAMP_LABELS if any(what in flag for flag in flags)}
    with fitz.open(pdf) as doc:
        for pno, page in enumerate(doc, start=1):
            for line in page.get_text().splitlines():
                for pattern, what in _STAMPS:
                    match = pattern.search(line) if what not in seen else None
                    if match:
                        seen.add(what)
                        flags.append(_flag(label, pno, what, match.group(0)))
    return flags


class IdentifiedCopyError(RuntimeError):
    """A snapshot shows author or publication information and the session does not allow it."""

    def __init__(self, flags: list[str]) -> None:
        super().__init__(f"{len(flags)} anonymity flags; pass --allow-identified to review this copy anyway")
        self.flags = list(flags)


def publication_stamps(flags: Iterable[str]) -> list[str]:
    """Flags that mark a camera-ready, published or preprint copy (CVF watermark, arXiv stamp, ...)."""
    return [f for f in flags if any(label in f for label in _STAMP_LABELS)]


def check_identified(paper: dict, allowed: bool) -> list[str]:
    """Anonymity flags of a snapshot (`paper` meta); raises IdentifiedCopyError if any and not `allowed`."""
    flags = list(paper.get("anonymity_flags") or [])
    if flags and not allowed:
        raise IdentifiedCopyError(flags)
    return flags


def identified_line(paper: dict) -> str:
    """The reviewer prompt line for a copy with anonymity flags ('' for a clean copy)."""
    return IDENTIFIED_LINE if paper.get("anonymity_flags") else ""


def flag_report(flags: list[str], command: str, allowed: bool, cutoff_set: bool) -> str:
    """What `hx.py new` / `round` print about a flagged copy.

    The flags, then the refusal (or, when allowed, a notice), then a --cutoff recommendation when a
    camera-ready or preprint stamp is flagged and the session has no user-given cutoff.
    """
    lines = [f"Anonymity check: the PDF shows author or publication information ({len(flags)} flags):"]
    lines += [f"  - {flag}" for flag in flags]
    if allowed:
        lines.append("--allow-identified: continuing. Every reviewer prompt says the harness has recorded this "
                     "and that it must not affect the review.")
    else:
        lines.append(f"{command} refused: a double-blind venue would desk-reject this copy, and author or venue "
                     "information biases the simulated reviewers. Use the anonymous review copy, or pass "
                     "--allow-identified to review this copy anyway (for example, a published paper as a test).")
    if publication_stamps(flags) and not cutoff_set:
        lines.append("Warning: this is a camera-ready or preprint copy and the session uses the venue's default "
                     "prior-work cutoff. Recommended: `hx.py new ... --cutoff <the paper's original submission "
                     "deadline>` (YYYY-MM-DD), so reviewers do not count later work as prior work.")
    return "\n".join(lines)
