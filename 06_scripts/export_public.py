#!/usr/bin/env python3
"""Build a de-identified public copy of the harness and a zip of it.

    python3 06_scripts/export_public.py [--out release]

Copies only the reusable parts (protocol, personas, panels, templates, scripts, domain packs,
research summaries, docs). Leaves out sessions (papers and reviews), build notes (00_plan), raw
review downloads, backups and caches. Then scans every exported text file for identifying strings
and fails if one is found. Output: <out>/cvpr-review-harness/ and <out>/cvpr-review-harness.zip.
"""
from __future__ import annotations

import argparse
import logging
import re
import shutil
import sys
import zipfile
from pathlib import Path

logger = logging.getLogger("export")

ROOT = Path(__file__).resolve().parents[1]
NAME = "cvpr-review-harness"
INCLUDE = ("README.md", "REVIEW_PAPER.md", "AGENTS.md", "CLAUDE.md", "01_sources", "02_protocol",
           "03_personas", "04_panels", "05_templates", "06_scripts", "07_domain_packs", "assets")
SKIP_PARTS = {"raw_reviews", "__pycache__", "sessions", "00_plan", "release"}
SKIP_NAME = re.compile(r"\.bak_|\.pyc$|^\.DS_Store$")
TEXT_SUFFIXES = {".md", ".py", ".json", ".txt", ".csv", ".yaml", ".yml", ".svg", ""}
# Generic identifying strings (case-insensitive). Project-specific ones (names, paper titles,
# folder names) live in a private, never-exported file: 00_plan/deid_patterns.txt, one regex per line.
GENERIC_FORBIDDEN = (r"/home/[a-z0-9_.-]+", r"/Users/[A-Za-z0-9_.-]+", r"/NAS\d", r"[\w.+-]+@[\w-]+\.(com|org|edu|net)\b",
                     r"claude-\d{4}", r"scratch[p]ad")
PRIVATE_PATTERNS = ROOT / "00_plan" / "deid_patterns.txt"


def forbidden_regex() -> re.Pattern:
    """Generic patterns plus the private project-specific ones, if that file exists."""
    pats = list(GENERIC_FORBIDDEN)
    if PRIVATE_PATTERNS.exists():
        pats += [ln.strip() for ln in PRIVATE_PATTERNS.read_text(encoding="utf-8").splitlines()
                 if ln.strip() and not ln.startswith("#")]
    else:
        logger.warning("no %s: only generic identity patterns are checked", PRIVATE_PATTERNS)
    return re.compile("|".join(f"(?:{p})" for p in pats), re.IGNORECASE)


GITIGNORE = """# review sessions hold paper snapshots and reviews: keep them local
sessions/*
!sessions/README.md
release/
__pycache__/
*.pyc
*.bak_*
01_sources/raw_reviews/
"""
SESSIONS_README = """# sessions/

`hx.py new` creates one folder per review session here. Sessions contain frozen copies of your
paper and the reviews of it, so they are git-ignored. Keep them local.
"""
SOURCES_NOTE = """# 01_sources/

Research behind the personas and protocol:

- `cvpr_official_process.md`: official CVPR review form, guidelines, policies and timelines
  (primary sources quoted with URLs).
- `real_review_patterns.md`: patterns measured in 184 public OpenReview reviews of computer-vision
  papers (ICLR 2024-2026, NeurIPS 2024-2025): weakness frequencies, lengths, reviewer types,
  rebuttal dynamics. Quotes are short excerpts with their forum ids.
- `reviewer_behavior_literature.md`: studies of reviewer behaviour, LLM reviewers and
  reward hacking, with design rules derived from them.

The raw review downloads used for the counts are not redistributed. They come from public
OpenReview data and its HuggingFace mirrors named in `real_review_patterns.md`.
"""


def _wanted(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    return not (SKIP_PARTS & set(rel.parts) or SKIP_NAME.search(path.name))


def build(out_dir: Path) -> Path:
    """Copy the public parts into out_dir/NAME and return that folder."""
    dest = out_dir / NAME
    if dest.exists():  # replace the files but keep a git repository living here
        for child in dest.iterdir():
            if child.name != ".git":
                shutil.rmtree(child) if child.is_dir() else child.unlink()
    for item in INCLUDE:
        src = ROOT / item
        files = [src] if src.is_file() else sorted(p for p in src.rglob("*") if p.is_file())
        for path in files:
            if _wanted(path):
                target = dest / path.relative_to(ROOT)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target)
    (dest / ".gitignore").write_text(GITIGNORE, encoding="utf-8")
    (dest / "sessions").mkdir(exist_ok=True)
    (dest / "sessions" / "README.md").write_text(SESSIONS_README, encoding="utf-8")
    (dest / "01_sources" / "README.md").write_text(SOURCES_NOTE, encoding="utf-8")
    return dest


def scan(dest: Path) -> list[str]:
    """Return 'file:line: match' for every forbidden string in exported text files."""
    forbidden = forbidden_regex()
    hits: list[str] = []
    for path in sorted(p for p in dest.rglob("*") if p.is_file() and ".git" not in p.parts):
        if path.suffix not in TEXT_SUFFIXES:
            continue
        for n, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            for m in forbidden.finditer(line):
                hits.append(f"{path.relative_to(dest)}:{n}: {m.group(0)!r}")
    return hits


def make_zip(dest: Path) -> Path:
    """Zip dest (without .git) next to it."""
    zpath = dest.parent / f"{NAME}.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(p for p in dest.rglob("*") if p.is_file() and ".git" not in p.parts):
            zf.write(path, Path(NAME) / path.relative_to(dest))
    return zpath


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(ROOT / "release"), help="output folder")
    args = ap.parse_args()
    dest = build(Path(args.out).resolve())
    hits = scan(dest)
    if hits:
        logger.error("identifying strings found; nothing zipped:\n  %s", "\n  ".join(hits))
        return 1
    zpath = make_zip(dest)
    n_files = sum(1 for p in dest.rglob("*") if p.is_file() and ".git" not in p.parts)
    logger.info("exported %d files to %s; zip %s (%.0f KB); identity scan clean",
                n_files, dest, zpath, zpath.stat().st_size / 1024)
    return 0


if __name__ == "__main__":
    sys.exit(main())
