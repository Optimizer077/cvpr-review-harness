### satisfaction.json format

```json
{
  "job_id": "R03",
  "round": 2,
  "stage": "satisfy",
  "paper_sha256": "<given in the prompt>",
  "previous_rating": 2,
  "overall": {"rating": 3, "confidence": 4, "justification": "<what decided the updated rating>"},
  "items": [
    {"id": "W1", "status": "satisfied | partly | not_satisfied",
     "reason": "<why, citing the new draft (page and paragraph, Tab., Fig.)>",
     "evidence": "<location in the new draft you checked>",
     "remaining_ask": "<what would still satisfy you; empty if satisfied>"}
  ],
  "new_issues": [
    {"id": "W7", "severity": "moderate", "category": "overclaiming", "location": "p.1, Abstract",
     "text": "<issue the revision introduced>", "decisive": false, "fixable_by": "writing",
     "suggested_fix": "<smallest change>", "would_change_mind": "<what would satisfy you>"}
  ],
  "section_scores": {
    "abstract": {"score": 7, "criteria": {"problem_gap": 4, "method_concrete": 4, "evidence_specific": 4,
                 "claim_calibration": 3, "readability": 4},
                 "main_issue": "<...>", "location": "p.1, Abstract", "one_point_fix": "<...>"}
  }
}
```

Rules:
1. `items` has exactly one entry per open point id given in the prompt.
2. `new_issues` may be empty and uses the weakness categories; `category` says why the issue
   costs rating, not what the remedy is.
3. Decisive test: a new issue is `decisive` only if it alone keeps you from acceptance, no
   writing-only change would satisfy you, and its category is novelty, overclaiming, mechanism,
   correctness or marginal_gains (any other category names the central claim it invalidates).
4. `section_scores` re-scores exactly the sections listed, with that section's criterion ids
   (null for a criterion you could not observe).
5. Locations cite the new draft's PDF: page and paragraph, Fig., Tab. or Eq.; a line number only
   where the PDF prints line numbers.
