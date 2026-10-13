# Domain packs

A domain pack is what a subfield-expert reviewer knows: the lines of work, the baselines they
expect, the protocol traps they check, and the demands real reviewers in that subfield make. Only
personas with `uses_domain_pack: true` receive it. Adjacent-area and outsider personas deliberately
do not, because real reviewers from outside the subfield do not know these things.

Select a pack per session: `hx.py new ... --domain inr_neural_fields`.

To add a pack, write `<name>.md` with the same four headings as `inr_neural_fields.md`:
1. Lines of work an expert knows
2. What reviewers in this subfield have demanded (from real reviews; cite the source study)
3. Things an expert checks quickly
4. (optional) Recent concurrent work that a reviewer may raise

Ground every demand in real reviews or official guidance. A pack written from guesses makes the
expert reviewer confidently wrong. Name only real papers; check them before listing.
