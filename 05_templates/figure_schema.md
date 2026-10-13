### review.json additions for the figure job (FIG)

The figure job writes the review.json above as a section-only review (`overall` and
`first_impression` are `null`; `section_scores` has only `figures_tables`), plus `figure_scores`
and two extra fields on every weakness:

```json
{
  "job_id": "FIG",
  "reviewer_id": "F01",
  "round": 1,
  "stage": "initial",
  "paper_sha256": "<given in the prompt>",
  "reading": {"time_spent_min": null, "read": ["figures_tables"], "skimmed": ["experiments"],
              "opened_supplement": "no"},
  "first_impression": null,
  "overall": null,
  "section_scores": {
    "figures_tables": {
      "score": 6,
      "criteria": {"readability": 3, "captions_self_contained": 3, "text_consistency": 4, "visual_comparisons": 3},
      "main_issue": "<the figure problem that costs the most>",
      "location": "Fig. 3",
      "one_point_fix": "<the change that would raise this section by at least one point>"
    }
  },
  "figure_scores": {
    "fig_1": {
      "role": "teaser",
      "perceived_message": "<what the graphics show you, judged from the image rather than the caption>",
      "intended_message": "<what the caption and text say it should show>",
      "score": 6,
      "criteria": {"message_clarity": 3, "legibility": 4, "encoding_fit": 4, "accessibility": 3,
                   "caption_alignment": 3, "comparison_fairness": null},
      "visible_evidence": "<quoted visible text or values the judgement relies on>",
      "main_issue": "<the single thing in this figure that costs the most>",
      "location": "Fig. 1, right panel",
      "one_point_fix": "<the change that would raise this figure by at least one point>"
    }
  },
  "strengths": [{"text": "<specific strength>", "location": "Fig. 2"}],
  "weaknesses": [
    {
      "id": "W1",
      "severity": "moderate",
      "category": "figures",
      "figure_id": "fig_3",
      "defect": "illegible_text",
      "location": "Fig. 3, legend",
      "text": "<the problem, with the quoted visible evidence or the FIGURES.md measurement>",
      "decisive": false,
      "fixable_by": "writing",
      "suggested_fix": "<the concrete change: what to redraw, enlarge, relabel or recaption>",
      "would_change_mind": "<what the new crop must show for you to drop this point>"
    }
  ],
  "questions": []
}
```

Field rules:
- `figure_scores` has one entry for EVERY main-paper id in `figures/figures.json` (figures AND
  tables; ids such as `fig_1`, `tab_2`). Supplement ids (`supp_fig_1`, ...) are optional. No other keys.
- `role`: teaser | method_diagram | quantitative_plot | qualitative_comparison | table | other.
- `score`: integer 1-10 with the section-score anchors (9-10 a strength; 5-6 earns a moderate
  point; 3-4 a major point; 1-2 broken or missing).
- `criteria`: exactly message_clarity, legibility, encoding_fit, accessibility, caption_alignment,
  comparison_fairness; integers 1-5 (1 absent or wrong, 2 weak, 3 adequate, 4 good, 5 exemplary).
  Only `comparison_fairness` may be `null`, and only when the figure shows no comparison.
- `perceived_message` comes from the graphics (what a reader would conclude from the plot,
  diagram or table itself); `intended_message` from the caption and the text. A gap between the
  two is evidence for `unclear_message` or `caption_text_mismatch`. Write "cannot determine" when
  the image does not let you tell.
- `visible_evidence` quotes what is visible (labels, legend entries, printed numbers) or cites a
  FIGURES.md measurement ("smallest text 5.0 pt"). Never an estimate of an unlabelled value.
- `visible_evidence`, `main_issue`, `location`, `one_point_fix`, `perceived_message` and
  `intended_message` are required and non-empty for every entry, including good figures.
- Every weakness has `figure_id` (an id from figures.json, or `"global"` for an issue across
  figures) and `defect`: illegible_text | low_resolution | clutter | unclear_message |
  misleading_encoding | inappropriate_chart | missing_labels_or_units | colour_inaccessible |
  caption_not_self_contained | caption_text_mismatch | figure_text_inconsistency |
  diagram_equation_mismatch | unfair_comparison | missing_failure_cases | inconsistent_style |
  redundant_with_table | not_referenced | other. `category` still uses the weakness categories
  (usually figures, visual_results, notation, overclaiming or clarity).
- In an answer round, satisfaction.json carries the same `figure_scores`, re-scored for every
  main-paper id of the NEW snapshot, and each entry of `new_issues` carries `figure_id` and `defect`.
