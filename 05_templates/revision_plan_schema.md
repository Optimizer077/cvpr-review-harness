### revision_plan.json format

```json
{
  "round": 1,
  "paper_sha256": "<given in the prompt>",
  "summary": "<3-5 sentences: what the paper contributes, where it stands with reviewers, the main lever>",
  "strengths_to_keep": [{"text": "<what works and why to keep it>", "location": "p.2, Fig. 1",
                         "from": ["R03:S1", "R09:S2"]}],
  "items": [{
    "id": "P1", "priority": 1, "from": ["R03:W2", "R08:W1"],
    "type": "writing | existing_evidence | new_experiment | figure | not_fixable",
    "section": "<a section key or 'global'>",
    "location": "p.2, Sec. 1, para. 3",
    "problem": "<what readers misunderstand or doubt, specific to this paper>",
    "why_it_matters": "<which reviewer types react and how it moves their rating>",
    "action": "<the concrete change>",
    "proposed_text": "<replacement or new text for writing/figure items; '' otherwise>",
    "verification": "<how the next round or the writer can confirm it is fixed>",
    "effort": "small | medium | large"
  }],
  "experiment_requests": [{"from": ["R03:W4"], "request": "<the run reviewers ask for>",
                           "minimum_version": "<the smallest run that would answer it>",
                           "if_not_possible": "<honest framing or limitation text to use instead>"}],
  "conflicts": [{"from": ["R02:W1", "R12:S1"], "advice": "<how to satisfy both or which to prioritize, and why>"}],
  "deferred": [{"from": ["R15:W3"], "reason": "<generic, lazy or out of scope; why not to act>"}]
}
```

Field rules:
1. Coverage: every open point id in the prompt appears exactly once across `items[].from`,
   `experiment_requests[].from` and `deferred[].from`. No point is lost and none is planned twice.
2. `from` lists only the open point ids and strength ids given in the prompt (`<job>:S<n>` is the
   n-th entry of `strengths` in that reviewer's review.json). Every entry has at least one id;
   a conflict has at least two.
3. `items`: few and merged, at most 12 (a plan, not a list). `id` is `P1`, `P2`, ... `priority` is
   1..N, each number once, 1 = most important; priorities 1-5 are "the changes that matter most".
4. `type` and `effort` take one of the listed values. `section` is a section key named in the
   prompt or `global`.
5. `proposed_text` is the text to paste, in the paper's voice and within the page budget. It is
   required for `writing` items; it may be '' for a figure that needs regeneration and for other
   types.
6. Every other text field is a non-empty string. Never invent results, numbers or citations: an
   experiment item says what to run and what to write if it cannot be run.
7. `strengths_to_keep` names what works, with its location, so the revision does not cut it.
