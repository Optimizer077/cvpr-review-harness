"""Shared paths and small helpers for the Paper review harness."""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

HARNESS_ROOT: Path = Path(__file__).resolve().parents[2]
PROTOCOL_DIR: Path = HARNESS_ROOT / "02_protocol"
PERSONA_DIR: Path = HARNESS_ROOT / "03_personas"
PANEL_DIR: Path = HARNESS_ROOT / "04_panels"
TEMPLATE_DIR: Path = HARNESS_ROOT / "05_templates"
DOMAIN_DIR: Path = HARNESS_ROOT / "07_domain_packs"
SESSIONS_DIR: Path = HARNESS_ROOT / "sessions"

# Canonical section keys, in paper order. Section rubrics, panels and scores use these keys.
SECTION_KEYS: tuple[str, ...] = (
    "title",
    "abstract",
    "introduction",
    "related_work",
    "method",
    "theory",
    "experiments",
    "ablations_analysis",
    "figures_tables",
    "limitations",
    "conclusion",
    "supplementary",
    "references",
)


def load_json(path: Path) -> Any:
    """Read a JSON file."""
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def save_json(path: Path, obj: Any) -> None:
    """Write JSON with stable formatting, creating parent folders."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def load_scales(profile: str | None = None) -> dict:
    """Scales with `overall` resolved to the session's rating profile (default from scales.json)."""
    raw = load_json(PROTOCOL_DIR / "scales.json")
    name = profile or raw["default_overall"]
    if name not in raw["overall_profiles"]:
        raise KeyError(f"Unknown rating profile {name!r}; have {sorted(raw['overall_profiles'])}")
    out = {k: v for k, v in raw.items() if k != "overall_profiles"}
    out["overall"] = dict(raw["overall_profiles"][name], profile=name)
    return out


def scale_wording(scale: dict) -> str:
    """'1 = Reject; 2 = Weak Reject; ...' for prompts."""
    return "; ".join(f"{k} = {v}" for k, v in scale["labels"].items())


def sha256_file(path: Path) -> str:
    """Return the SHA-256 hex digest of a file."""
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def now_iso() -> str:
    """Local time stamp, second resolution."""
    return _dt.datetime.now().replace(microsecond=0).isoformat()


def today() -> str:
    """Local date as YYYY-MM-DD."""
    return _dt.date.today().isoformat()


def round_dir(session: Path, number: int) -> Path:
    """Folder of round `number` inside a session."""
    return session / f"round_{number:02d}"


def review_dir(round_path: Path, job: dict) -> Path:
    """Output folder of a job: reviews/<job> for feedback reviewers, heldout/<job> for held-out ones."""
    sub = "heldout" if job.get("group") == "heldout" else "reviews"
    return round_path / sub / job["job_id"]


def list_rounds(session: Path) -> list[int]:
    """Existing round numbers of a session, ascending."""
    out: list[int] = []
    for child in session.glob("round_*"):
        suffix = child.name.split("_", 1)[-1]
        if child.is_dir() and suffix.isdigit():
            out.append(int(suffix))
    return sorted(out)


def resolve_session(arg: str) -> Path:
    """Accept a session folder path or a bare session name under sessions/."""
    path = Path(arg)
    if not path.is_absolute() and not path.exists():
        path = SESSIONS_DIR / arg
    path = path.resolve()
    if not (path / "SESSION.json").exists():
        raise FileNotFoundError(f"No SESSION.json in {path}")
    return path
