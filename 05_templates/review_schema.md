### review.json format

```json
{
  "job_id": "R03",
  "reviewer_id": "R03",
  "round": 1,
  "stage": "initial",
  "paper_sha256": "<given in the prompt>",
  "reading": {
    "time_spent_min": 90,
    "read": ["abstract", "introduction", "method", "experiments"],
    "skimmed": ["related_work", "conclusion"],
    "opened_supplement": "no | yes: <which part and why>"
  },
  "first_impression": {
    "rating": 3,
    "after": "title, abstract, Fig. 1, captions, contributions, main table",
    "note": "<one sentence: what formed this impression>"
  },
  "overall": {
    "rating": 3,
    "confidence": 4,
    "justification": "<the reasons that decided the rating>"
  },
  "section_scores": {
    "abstract": {
      "score": 6,
      "criteria": {"problem_gap": 3, "method_concrete": 2, "evidence_specific": 4, "claim_calibration": 3, "readability": 3},
      "main_issue": "<the single thing in this section that costs the most>",
      "location": "L005-L012",
      "one_point_fix": "<the change that would raise this section by at least one point>"
    }
  },
  "strengths": [
    {"text": "<specific strength with evidence>", "location": "Tab. 1"}
  ],
  "weaknesses": [
    {
      "id": "W1",
      "severity": "major",
      "category": "novelty",
      "location": "L141-L152",
      "text": "<the weakness, specific to this paper, with the evidence for it>",
      "decisive": true,
      "fixable_by": "new_experiment",
      "suggested_fix": "<the concrete change you want: what to add, rewrite or show, and where>",
      "would_change_mind": "<what would satisfy you: the evidence or text that would make you drop this point>"
    }
  ],
  "questions": ["<question for the rebuttal>"]
}
```

Field rules:
- `overall` and `first_impression` are `null` for section-only jobs. `first_impression.rating` uses the same scale as `overall.rating` and is recorded before reading the method in detail.
- `section_scores` has exactly the assigned sections; `criteria` has exactly that section's criterion ids.
- `severity`: major | moderate | minor. `decisive`: would this point alone keep you from recommending acceptance?
- `fixable_by`: writing | existing_evidence | new_experiment | not_fixable. This is your honest guess as a reviewer.
- `suggested_fix` and `would_change_mind` are required and specific: the authors will answer each point, and you (or a reviewer like you) will later judge whether the answer satisfies you.
- `location` is required for every weakness and every section entry.
- Write the review in your persona's own voice, length and level of detail. JSON fields do not make a review longer than you would really write: a terse reviewer has short texts and few weaknesses.
