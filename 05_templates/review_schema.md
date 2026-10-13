### review.json format

```json
{
  "job_id": "<job id>", "reviewer_id": "<your id>", "round": 1, "stage": "initial",
  "paper_sha256": "<given in the prompt>",
  "reading": {"time_spent_min": 30, "read": ["<section key>"], "skimmed": ["<section key>"],
              "opened_supplement": "no | yes: <which part and why>"},
  "first_impression": {"rating": 3, "after": "<what you had read>", "note": "<one sentence>"},
  "overall": {"rating": 3, "confidence": 4, "justification": "<what decided the rating>"},
  "section_scores": {"<section key>": {"score": 6, "criteria": {"<criterion id>": 3},
    "main_issue": "<...>", "location": "p.3, Sec. 3.2, para. 2", "one_point_fix": "<...>"}},
  "strengths": [{"text": "<strength with evidence>", "location": "Tab. 1"}],
  "weaknesses": [{"id": "W1", "severity": "major | moderate | minor", "category": "<category id>",
    "location": "p.3, Sec. 3.2, para. 2", "text": "<the point and its evidence>", "decisive": false,
    "fixable_by": "writing | existing_evidence | new_experiment | not_fixable",
    "suggested_fix": "<what to add, rewrite or show, and where>",
    "would_change_mind": "<what would make you drop this point>"}],
  "questions": ["<question for the rebuttal>"]
}
```

Field rules:
1. `overall` and `first_impression` are null for section-only jobs.
2. `section_scores` has exactly the assigned sections; `criteria` has exactly that section's
   criterion ids, each 1-5, or null if you could not observe it.
3. `weaknesses` are exactly the points under Weaknesses in `review.md`, in order (point n = Wn).
4. `category` says why the point costs rating, not the remedy: small or within-noise gains are
   `marginal_gains`, a claim beyond its evidence is `overclaiming`, whatever you ask for.
5. Decisive test: `decisive` is true only if (a) the point alone keeps you from recommending
   acceptance; (b) no writing-only change would satisfy you (if the fix allows "or drop / scope
   the claim", the point is `overclaiming`, not decisive); (c) its category is `novelty` (naming the
   prior work), `overclaiming`, `mechanism`, `correctness` or `marginal_gains`, or the point names
   the central claim it invalidates. Prior work that appeared after the prior-work cutoff, or is
   only "newer", is not decisive alone. At most two decisive points.
6. `suggested_fix` and `would_change_mind` are specific: the authors answer each point and you
   judge the answer on the next draft. `would_change_mind` fits a one-week rebuttal: at most one
   new table or figure per weakness, on existing data; if only a larger study would do, say so in
   `text` and do not mark the point decisive. `fixable_by` is your honest guess.
7. Mark in JSON texts what no page states: "[inferred from <location>]" for a deduced setting or
   explanation, "[read off Fig. N]" for a value read from a plot.
8. `ac_note` (optional string): anonymity, dual-submission or misconduct concerns; never in
   `weaknesses`.
9. JSON texts are no longer than your review: a terse reviewer writes short texts.
