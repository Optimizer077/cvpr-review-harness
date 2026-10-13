"""Avoid repeating review work without new paper evidence or author answers."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .common import read_text, sha256_file
from .dialogue import DECISIONS, parse_response

_LINE_ANCHOR = re.compile(r'(?m)^L\d{3,4}[ \t]*')  # rendered rows: 'L012  text'
_CAPTION_ANCHOR = re.compile(r'(\[(?:main|supp) p\.\d+) L\d{3,4}\]')  # captions: '[main p.2 L045]'


def response_fingerprint(path: Path, open_ids: set[str]) -> str | None:
    """Hash filled answer blocks only; empty writer scaffolds are not new evidence."""
    answered = {}
    for key, block in parse_response(path).items():
        if key not in open_ids:
            continue
        decision = re.search(r"(?m)^Decision:[ \t]*([a-z_]+)\b", block)
        answer = re.search(r"(?m)^Answer to the reviewer[^\n]*?:[ \t]*(.*(?:\n.*)*)", block)
        if decision and decision.group(1) in DECISIONS and answer and answer.group(1).strip():
            answered[key] = " ".join(block.split())
    if not answered:
        return None
    return hashlib.sha256(json.dumps(answered, sort_keys=True).encode()).hexdigest()


def same_paper(pdf: Path, supp: Path | None, previous: dict) -> bool:
    return (sha256_file(pdf) == previous['paper']['main_pdf_sha256']
            and (sha256_file(supp) if supp else None) == previous['paper'].get('supp_pdf_sha256'))


def _normalized(text: str) -> str:
    """Section text without margin line anchors and layout whitespace.

    An inserted sentence shifts every later `L###` anchor; comparing raw text would mark every
    later section as changed.
    """
    text = _CAPTION_ANCHOR.sub(r'\1]', _LINE_ANCHOR.sub('', text))
    return ' '.join(text.split())


def changed_sections(previous: Path, current: Path) -> dict:
    """Extracted-text changes (anchors and whitespace ignored) are navigation hints, not proof of
    visual equivalence."""
    old = {p.stem: _normalized(read_text(p)) for p in (previous / 'sections').glob('*.txt')}
    new = {p.stem: _normalized(read_text(p)) for p in (current / 'sections').glob('*.txt')}
    return {
        'changed': sorted(k for k in old.keys() | new.keys() if old.get(k) != new.get(k)),
        'added': sorted(new.keys() - old.keys()), 'removed': sorted(old.keys() - new.keys()),
        'note': 'Extracted text only. Inspect changed PDF figures/tables and claim dependencies; text equality does not prove unchanged visual evidence.'}
