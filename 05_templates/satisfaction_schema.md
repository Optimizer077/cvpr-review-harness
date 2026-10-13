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
     "reason": "<why, citing the new draft (L###, Tab., Fig.)>",
     "evidence": "<location in the new draft you checked>",
     "remaining_ask": "<what would still satisfy you; empty if satisfied>"}
  ],
  "new_issues": [
    {"id": "W7", "severity": "moderate", "category": "overclaiming", "location": "L012",
     "text": "<issue the revision introduced>", "decisive": false, "fixable_by": "writing",
     "suggested_fix": "<smallest change>", "would_change_mind": "<what would satisfy you>"}
  ],
  "section_scores": {
    "abstract": {"score": 7, "criteria": {"problem_gap": 4, "method_concrete": 4, "evidence_specific": 4,
                 "claim_calibration": 3, "readability": 4},
                 "main_issue": "<...>", "location": "L005", "one_point_fix": "<...>"}
  }
}
```

Rules: `items` has exactly one entry per open point id given in the prompt. `new_issues` may be
empty and uses the weakness categories. `section_scores` re-scores exactly the sections listed,
with that section's criterion ids.
