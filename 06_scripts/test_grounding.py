#!/usr/bin/env python3
"""Tests of the grounding check (hxlib/grounding*.py). No LLM calls. Exit code 0 = pass.

Builds a synthetic CVPR-style PDF (as smoke_test.make_pdf does) with a line-end hyphenation, a
line whose ligature glyphs survive extraction and one whose ligature glyphs are lost, creates a
session with `hx.main(["new", ...])` in a temporary SESSIONS_DIR, writes fake reviews and asserts:
exact, hyphenated and ligature quotes verify; a light paraphrase is near, a heavy one and a
fabricated quote are not found; L999, Fig. 9, Eq. 7, Tab. 4, Sec. 7 and page 40 are flagged;
own-wording and cited-title quotes are skipped; GROUNDING.md keeps held-out details out; the CLI runs.

Optional false-positive measurement on real text (nothing about DIR is written anywhere):
    python 06_scripts/test_grounding.py --real-pdfs DIR [--n 20]
quotes random sentences copied from the snapshot text of each PDF in DIR (>= 95% must verify) and,
when pypdf is installed, from a second extractor (reported only).
"""
from __future__ import annotations

import argparse
import contextlib
import io
import logging
import random
import re
import subprocess
import sys
import tempfile
import time
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import hx  # noqa: E402
from hxlib import common  # noqa: E402
from hxlib.common import load_json, load_scales, review_dir, round_dir, save_json  # noqa: E402
from hxlib.grounding import check_grounding, extract_quotes  # noqa: E402
from hxlib.grounding_index import build_index, plain_paper_text  # noqa: E402
from hxlib.grounding_report import (grounding_summary, grounding_warnings, round_grounding,  # noqa: E402
                                    write_grounding_md)
from smoke_test import draw_figure, fake_review, write_satisfaction  # noqa: E402

logger = logging.getLogger("test_grounding")
HXLIB = Path(__file__).resolve().parent / "hxlib"
# (text, font): None = Helvetica; "keep" = HTML box (ligature glyphs extract as U+FB01 ...);
# "lost" = a fallback font whose ligature glyphs do not extract ("eﬀect" -> "eect").
PAPER: list[tuple[str, str | None]] = [
    ("CVPR", None), ("#*****", None), ("Grounded Toy Networks For Synthetic Review Tests", None),
    ("Anonymous CVPR submission", None), ("Abstract", None),
    ("We propose a toy network that learns grounded representations from synthetic data.", None),
    ("It improves the toy accuracy by 2.5 points over the strongest baseline.", None),
    ("1. Introduction", None),
    ("Reviewers often quote the paper when they criticise its central claims.", None),
    ("We study whether such quotes can be checked automatically against the text.", None),
    ("2. Related Work", None),
    ("Prior work on toy models focuses on accuracy rather than on grounding.", None),
    ("3. Method", None), ("3.1. Encoder", None),
    ("The encoder maps each input to a compact latent code with sixteen channels.", None),
    ("L = Lc + 0.1 Lr (1)", None), ("3.2. Decoder", None),
    ("The decoder is a two-layer network that predicts the class of each toy sample.", None),
    ("4. Experiments", None),
    ("Our multi-scale encoder achieves a consistent improvement on every bench-", None),
    ("mark we evaluated in this study, as summarised in Table 1.", None),
    ("The ﬁnal model is ﬁne-tuned on the oﬃcial training split for ten epochs.", "keep"),
    ("We observe a ﬁne-grained eﬀect of the ﬂow prior on rare toys.", "lost"),
    ("As shown in Fig. 1, the toy network outperforms all baselines on every split.", None),
    ("5. Conclusion", None), ("We showed that toy networks can be grounded in their own text.", None),
    ("Limitations. The toy network only works on toys.", None), ("Table 1. Toy results. Ours is best.", None),
    ("References", None), ("[1] A. Author. A paper. CVPR 2024.", None),
]
EXACT = "The encoder maps each input to a compact latent code with sixteen channels."
HYPHEN = "Our multi-scale encoder achieves a consistent improvement on every benchmark we evaluated in this study"
LIG_KEEP = "The ﬁnal model is ﬁne‑tuned on the official training split for ten epochs"  # U+FB01, U+2011
LIG_LOST = "We observe a fine-grained effect of the flow prior on rare toys"
NEAR = "The decoder is a two-layer network that predicts the label of each toy sample"
PARAPHRASE = "The decoding module is a shallow network predicting a category for every sample"
FABRICATED = "Our method achieves state-of-the-art results on ImageNet by a large margin"
HELDOUT_FAKE = "Our held-out reviewer quote is entirely fabricated for this test"
ANSWER = "We now explain in the method section that sixteen channels fit the memory of the toy GPU"


def make_grounding_pdf(path: Path, revised: bool = False) -> None:
    """Page 1: the PAPER rows with margin line numbers; page 2: one captioned figure (Fig. 1).

    `revised` adds one sentence before the Limitations line (a new draft for an answer round)."""
    import fitz

    rows = list(PAPER)
    if revised:
        rows.insert(len(rows) - 4, ("The revision explains the channel count of the encoder.", None))
    doc = fitz.open()
    page, y = doc.new_page(), 40
    for n, (text, font) in enumerate(rows, start=1):
        if font == "keep":
            page.insert_htmlbox(fitz.Rect(60, y - 9, 580, y + 5), text, css="* {font-size: 9pt;}")
        else:
            page.insert_text((60, y), text, fontsize=9, fontname="china-s" if font == "lost" else "helv")
        page.insert_text((20, y), f"{n:03d}", fontsize=6)
        y += 14
    draw_figure(doc.new_page(), 60, 1)
    doc.save(path)


def crafted_review(job: dict, rnd: dict) -> tuple[dict, str]:
    """review.json / review.md with one case of every classification."""
    data = fake_review(job, rnd, random.Random(5))
    base = dict(data["weaknesses"][0], decisive=False)
    texts = [
        ("L999", f'The method section says "{EXACT}" but never justifies sixteen.'),
        ("L019-L020", f"The claim “{HYPHEN}” is not supported by Fig. 9."),
        ("p. 40", f'Training details are thin: "{LIG_KEEP}" names no optimiser, and "{LIG_LOST}" is unquantified.'),
        ("Sec. 3.2", f'The text states "{NEAR}", which is vague.'),
        ("Sec. 3.2", f'The paper claims "{PARAPHRASE}".'),
        ("Abstract", f'The abstract claims "{FABRICATED}", which is not shown.'),
        ("Sec. 7", "Eq. (1) is fine but Eq. (7) is missing; see Table 1 and Table 4. The L2 loss is not discussed."),
    ]
    data["weaknesses"] = [dict(base, id=f"W{k}", location=loc, text=text) for k, (loc, text) in enumerate(texts, 1)]
    data["weaknesses"][-1]["suggested_fix"] = 'Add a sentence such as "We report results in Table 6 for all variants."'
    data["strengths"] = [{"text": 'I would describe this as "a careful and honest toy study of grounded reviewing"',
                          "location": "Fig. 1"}]
    data["questions"] = ['Is Smith et al., "A Much Longer Title Of Another Toy Grounding Paper", CVPR 2023 related?']
    md = (f"## Summary\nAs the paper puts it, \"{EXACT}\" (p. 2, L012).\n\n## Strengths\nClear Sec. 3.1.\n\n"
          "## Weaknesses\nSee the JSON. The L1 norm and Section 3.2 are fine.\n")
    return data, md


def quiet_hx(args: list[str]) -> int:
    """hx.main with its console output captured."""
    with contextlib.redirect_stdout(io.StringIO()):
        return hx.main(args)


def write_job(rpath: Path, job: dict, rnd: dict, data: dict, md: str) -> None:
    """Review files of one job; review.md gets any required heading it lacks, so validation passes."""
    out = review_dir(rpath, job)
    save_json(out / "review.json", data)
    missing = [h for h in load_scales()["review_md_headings"] if h.lower() not in md.lower()]
    md += "".join(f"\n## {h}\ntoy text for the grounding test, long enough.\n" for h in missing)
    (out / "review.md").write_text(md, encoding="utf-8")
    (out / "debrief.md").write_text("toy debrief, long enough to pass the size check....\n", encoding="utf-8")


def check_snapshot(snap: Path) -> None:
    """The PDF rows reach the snapshot as intended (hyphen, kept and lost ligatures, anchors)."""
    text = (snap / "paper_main.txt").read_text(encoding="utf-8")
    assert "every bench-" in text and "ﬁnal" in text and "eect of the" in text, text[:2000]
    index = build_index(snap)
    assert index.pages == {"main": 2} and index.anchor_ok(12) and not index.anchor_ok(999)
    assert index.refs["figure"] == {"1"} and index.refs["table"] == {"1"} and "1" in index.refs["equation"]
    assert {"1", "2", "3", "3.1", "3.2", "4", "5"} <= index.sections, index.sections


def check_crafted(findings: dict) -> None:
    """Every planted case lands in its class."""
    status = {q["quote"][:30]: q["status"] for q in findings["quotes"]}
    expect = {EXACT: "verified", HYPHEN: "verified", LIG_KEEP: "verified", LIG_LOST: "verified",
              NEAR: "near", PARAPHRASE: "not_found", FABRICATED: "not_found"}
    for quote, want in expect.items():
        key = " ".join(quote.split())[:30]
        assert status.get(key) == want, (quote, status.get(key), findings["quotes"])
    near = next(q for q in findings["quotes"] if q["status"] == "near")
    assert "predicts the class" in near["paper_text"] and near["at"].startswith("main p.1 L"), near
    bad = {(b["kind"], b["ref"]) for b in findings["bad_refs"]}
    assert bad == {("anchor", "L999"), ("figure", "Fig. 9"), ("page", "p.40"), ("equation", "Eq. 7"),
                   ("table", "Tab. 4"), ("section", "Sec. 7")}, bad
    t = findings["totals"]
    assert (t["quotes"], t["verified"], t["near"], t["not_found"], t["skipped"]) == (7, 4, 1, 2, 2), t
    assert (t["bad_anchors"], t["bad_pages"], t["bad_refs"], t["bad_sections"]) == (1, 1, 3, 1), t
    reasons = {s["reason"] for s in findings["skipped_quotes"]}
    assert reasons == {"reviewer's own or proposed wording", "title of a cited work"}, reasons
    assert len(grounding_warnings(findings)) == 3 + len(bad)


def check_units(snap: Path) -> None:
    """Quote extraction, figure image text, the authors' answers as a source, short anchors."""
    quotes = extract_quotes('a 5" screen; "too short quote"; "this one has exactly six words" ok')
    assert quotes == [("this one has exactly six words", "")], quotes
    fig = {"weaknesses": [{"id": "W1", "figure_id": "fig_1", "location": "Fig. 1",
                           "text": 'The legend reads "Ours with the full refinement stage enabled".'}]}
    assert check_grounding(fig, "", snap)["quotes"][0]["status"] == "image_text"
    answer = "We now state that the encoder uses sixteen channels because of memory limits on toys."
    sat = {"items": [{"id": "W1", "status": "partly", "evidence": "L014",
                      "reason": f'The authors answer "{answer}" but the text does not change.'}]}
    found = check_grounding(sat, "", snap, extra_texts={"authors' answers": answer})["quotes"][0]
    assert found["status"] == "verified" and found["source"] == "authors' answers", found
    loc = check_grounding({"weaknesses": [{"id": "W1", "location": "L1", "text": "An L2 penalty."}]}, "", snap)
    assert loc["checked"].get("anchor") == 1 and not loc["bad_refs"], loc
    other = {"weaknesses": [{"id": "W1", "location": "Sec. 3", "text": "Compare Fig. 5 of [12] and Table 3 in "
                             "Smith et al. (Proc. CVPR 2023, pp. 123-131); add a new Table 6."}]}
    assert not check_grounding(other, "", snap)["bad_refs"], "other papers' items and requests are not refs"
    supp = {"weaknesses": [{"id": "W1", "location": "L2 loss term, L014", "text": "See p. 1 of the supplement."}]}
    found = check_grounding(supp, "", snap)
    assert [b["ref"] for b in found["bad_refs"]] == ["supp p.1"] and found["checked"]["anchor"] == 1, found
    md = f'I suggest more baselines. The abstract claims "{FABRICATED}".'
    assert check_grounding({}, md, snap)["quotes"][0]["status"] == "not_found", "a suggestion ends at its sentence"


def check_round(rpath: Path) -> None:
    """Round report, GROUNDING.md with held-out details kept out, and the CLI."""
    rnd = load_json(rpath / "ROUND.json")
    started = time.perf_counter()
    result = round_grounding(rnd, rpath)
    assert time.perf_counter() - started < 10, "grounding must be fast"
    assert set(result["jobs"]) == {j["job_id"] for j in rnd["jobs"]}, result["jobs"].keys()
    check_crafted(result["jobs"]["R02"])
    assert result["jobs"]["R03"]["totals"]["verified"] == 1 and not result["jobs"]["R03"]["bad_refs"]
    assert result["jobs"]["HR11"]["totals"]["not_found"] == 1
    summary = grounding_summary(result)
    assert summary == ("Grounding: 5/9 quotes verified, 1 near, 3 not found; 1 bad anchor, 1 bad page, "
                       "3 bad Fig./Tab./Eq. references, 1 unknown section (3 reviews)."), summary
    md = write_grounding_md(result, rpath).read_text(encoding="utf-8")
    assert summary in md and FABRICATED in md and "L999" in md and "held-out (1 job)" in md
    assert HELDOUT_FAKE not in md, "held-out quotes must stay out of the round GROUNDING.md"
    assert HELDOUT_FAKE in (rpath / "heldout" / "GROUNDING.md").read_text(encoding="utf-8")
    run = subprocess.run([sys.executable, str(HXLIB / "grounding.py"), str(rpath)], capture_output=True,
                         text=True, encoding="utf-8", check=False)
    assert run.returncode == 0 and run.stdout.startswith(summary), (run.stdout, run.stderr)


def run_synthetic() -> None:
    """Round 1 with a crafted, a clean and a held-out review, then an answer round."""
    with tempfile.TemporaryDirectory() as tmp:
        tmpd = Path(tmp)
        common.SESSIONS_DIR = tmpd / "sessions"
        hx.SESSIONS_DIR = common.SESSIONS_DIR
        make_grounding_pdf(tmpd / "paper.pdf")
        assert quiet_hx(["new", "--paper", str(tmpd / "paper.pdf"), "--name", "ground", "--reviewers",
                        "R02,R03", "--heldout", "R11"]) == 0
        rpath = round_dir(next(common.SESSIONS_DIR.iterdir()), 1)
        check_snapshot(rpath / "snapshot")
        rnd = load_json(rpath / "ROUND.json")
        jobs = {j["job_id"]: j for j in rnd["jobs"]}
        write_job(rpath, jobs["R02"], rnd, *crafted_review(jobs["R02"], rnd))
        clean = fake_review(jobs["R03"], rnd, random.Random(3))
        clean["weaknesses"][0]["text"] = f'Fig. 1 and Tab. 1 support "{EXACT}" only on toys (L014, p. 1).'
        write_job(rpath, jobs["R03"], rnd, clean, "## Summary\nNothing to quote here.\n")
        held = fake_review(jobs["HR11"], rnd, random.Random(4))
        held["weaknesses"][0]["text"] = f'The paper says "{HELDOUT_FAKE}".'
        write_job(rpath, jobs["HR11"], rnd, held, "## Summary\nShort.\n")
        check_units(rpath / "snapshot")
        check_round(rpath)
        make_grounding_pdf(tmpd / "paper_v2.pdf", revised=True)
        check_answer_round(rpath.parent, tmpd / "paper_v2.pdf")


def check_answer_round(session: Path, pdf: Path) -> None:
    """Round 2: an answer-check reviewer's quote of the authors' answers verifies with that source."""
    for cmd in (["validate", str(session)], ["aggregate", str(session)], ["stage", str(session), "writer"]):
        assert quiet_hx(cmd) == 0, cmd
    sheet = round_dir(session, 1) / "writer" / "RESPONSE.md"
    sheet.write_text(sheet.read_text(encoding="utf-8").replace("Decision:", f"Decision: fix_text. {ANSWER}."),
                     encoding="utf-8")
    assert quiet_hx(["round", str(session), "--paper", str(pdf)]) == 0
    r2 = round_dir(session, 2)
    write_satisfaction(r2)
    path = r2 / "satisfaction" / "R03" / "satisfaction.json"
    data = load_json(path)
    data["items"][0]["reason"] = f'The authors write "{ANSWER}", but "{EXACT}" is unchanged (L015).'
    save_json(path, data)
    result = round_grounding(load_json(r2 / "ROUND.json"), r2)
    assert set(result["jobs"]) == {"R02", "R03"}, result["jobs"].keys()  # HR11 has no review yet
    quotes = {q["quote"]: q for q in result["jobs"]["R03"]["quotes"]}
    assert quotes[ANSWER]["status"] == "verified" and quotes[ANSWER]["source"] == "authors' answers", quotes
    assert quotes[EXACT]["source"] == "main" and result["jobs"]["R03"]["stage"] == "satisfy", quotes


def _llm_copy(sentence: str) -> str:
    """How a reader copies a sentence: ligatures expanded, spaces normalised."""
    return " ".join(unicodedata.normalize("NFKC", sentence).split())


def _sentences(text: str) -> list[str]:
    """Body sentences (before References) of 8-40 mostly alphabetic words, without double quotes."""
    text = re.split(r"\n\s*References\s*\n", text)[0]
    text = " ".join(re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text).split())
    parts = re.split(r"(?<=[a-z0-9)][.!?])\s+(?=[A-Z])", text)
    return [p for p in parts if 8 <= len(p.split()) <= 40 and not set(p) & set('"“”')
            and sum(c.isalpha() for c in p) >= 0.75 * len(p.replace(" ", ""))]


def _pypdf_text(pdf: Path) -> str:
    from pypdf import PdfReader  # optional second extractor

    return "\n".join(page.extract_text() or "" for page in PdfReader(str(pdf)).pages)


def measure_real(pdf_dir: Path, n: int, seed: int = 0) -> int:
    """Verify rate of quotes copied from real PDFs; returns 0 when >= 95% of snapshot quotes verify."""
    from hxlib.paper import extract_lines, render_pages

    rng = random.Random(seed)
    sources: dict[str, list[tuple[Path, str]]] = {"snapshot": [], "pypdf": []}
    with tempfile.TemporaryDirectory() as tmp:
        for k, pdf in enumerate(sorted(pdf_dir.glob("*.pdf"))):
            snap = Path(tmp) / f"p{k:02d}"
            snap.mkdir()
            (snap / "paper_main.txt").write_text(render_pages(extract_lines(pdf), "main"), encoding="utf-8")
            text = plain_paper_text((snap / "paper_main.txt").read_text(encoding="utf-8"))
            sources["snapshot"] += [(snap, s) for s in _sentences(text)]
            try:
                sources["pypdf"] += [(snap, s) for s in _sentences(_pypdf_text(pdf))]
            except Exception as exc:  # noqa: BLE001 - optional extractor; any failure only skips it
                logger.info("pypdf skipped for one PDF: %s", type(exc).__name__)
        rates = {}
        for name, pool in sources.items():
            if not pool:
                continue
            counts = {"verified": 0, "near": 0, "not_found": 0}
            for snap, sentence in rng.sample(pool, min(n, len(pool))):
                review = {"weaknesses": [{"id": "W1", "location": "-", "text": f'It says "{_llm_copy(sentence)}".'}]}
                quotes = check_grounding(review, "", snap)["quotes"]
                counts[quotes[0]["status"] if quotes else "not_found"] += 1
                if quotes and quotes[0]["status"] != "verified":
                    logger.info("%s %s: %r", name, quotes[0]["status"], sentence[:80])
            total = sum(counts.values())
            rates[name] = counts["verified"] / total
            print(f"{name}: {counts['verified']}/{total} verified, {counts['near']} near, "
                  f"{counts['not_found']} not found")
    return 0 if rates.get("snapshot", 0) >= 0.95 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--real-pdfs", type=Path, help="folder of PDFs for the false-positive measurement")
    parser.add_argument("--n", type=int, default=20, help="sentences per source (default 20)")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING)
    if args.real_pdfs:
        return measure_real(args.real_pdfs, args.n, args.seed)
    run_synthetic()
    print("GROUNDING TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
