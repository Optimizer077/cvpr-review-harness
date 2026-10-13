# Blind pairwise rules

You compare two versions, A and B, of the same section of a CVPR submission. You do not know which
version is newer, and you must not try to find out. For each section, judge which version the CVPR
reviewer pool would criticize less and rate higher on that section's rubric criteria
(02_protocol/section_rubrics.md).

Rules:
1. Length is not merit. A longer version wins only if the added content removes a likely criticism.
2. A stronger claim is not better unless the text itself supports it. Overclaiming loses.
3. Ignore artifacts of text extraction (hyphenation, line anchors, figure-label fragments).
4. Ground the reason in specific differences: quote the two phrasings that decided it.
5. Margin: 0 tie / 1 slight (one reviewer type would notice) / 2 clear (most reviewers would
   notice) / 3 decisive (changes whether a weakness bullet is written).
6. Name which reviewer types care about the difference (e.g. "busy senior", "novelty skeptic",
   "subfield expert", "adjacent-area reader").

## Figures

Some pairs are figure crops, `A_fig_<id>.png` and `B_fig_<id>.png` (the figure with its caption, as
printed). Open both images and write the entry with `"section": "figure:<id>"`.
7. Compare A and B on the `figures_tables` rubric criteria: readability (text legible at print size,
   colours that survive gray print and colour-vision deficiency), a caption that says what is shown
   and what to conclude, consistency with the text, and fair visual comparisons. Use the measured
   text sizes given in the prompt instead of guessing them.
8. Do not prefer a version for decoration, saturation or density.
9. A version that changes what data is shown (axis limits, removed baselines, different crops or
   zoom regions) loses unless the change is neutral.
10. If you see no difference a reader would notice (the figure was only re-rendered or moved),
    answer tie with margin 0.
