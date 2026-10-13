The CVPR review form (pre-rebuttal review). Field order and content follow the official CVPR 2026
reviewer training and guidelines and the CVPR 2024 program chairs' form outline. The exact
on-screen field titles are not public (see 01_sources/cvpr_official_process.md).

Write `review.md` with these headings, in this order:

## Summary
2-4 sentences in your own words: what the paper does, what it claims, and why it matters if true.
Official guidance: "This is your abstract of the paper ... the summary helps the AC and the authors
... be confident that you understand the paper."

## Strengths
What gives the paper value, with specific evidence: ideas that are experimentally validated, an
insightful organization of related work, new tools, impressive results. "Most importantly, what
can someone interested in the topic learn from the paper?"

## Weaknesses
What detracts from the contributions, with specific evidence and locations: missing controlled
experiments, misleading claims, technical errors, whether the method can be understood and
reproduced. Mark which weaknesses are major. Official guidance: "Bullet lists with one short phrase
per bullet are NOT a detailed review."

## Preliminary recommendation
One rating from the scale given at the end of this prompt, written as `<number> - <label>`.

## Justification
Explain why the paper should be accepted or not. Make clear which strengths and weaknesses you
consider most significant, and connect them to the rating. Add constructive suggestions and the
questions you want answered in the rebuttal. Ask only for clarifications or small experiments that
fit a one-week rebuttal with academic resources.

## Additional comments
Minor suggestions, typos, corrections. Not crucial to the recommendation.

## Confidence
One level from the confidence scale, written as `<number> - <label>`, plus one sentence on your
expertise for this paper.

Official reviewer rules (CVPR 2026 guidelines; CVPR 2027 call for papers):
- Not beating the state of the art on a benchmark is not grounds for rejection by itself. Weigh
  novelty and potential impact together with performance.
- A claim that the work "has been done before" must name specific references and explain how close
  they are. "This is well known" is not sufficient.
- Minor flaws that can easily be corrected should not be a reason to reject.
- Do not ask for substantial new experiments (what a major revision would need), and do not
  penalize their absence.
- Prior work for CVPR 2027: papers that appeared online after 2026-09-15 are contemporaneous; the
  submission is not rejected because of comparison to them. arXiv and published papers are
  treated alike.
- An honest limitations discussion should count positively, not against the paper.
- Refer to "the paper", not "you" or "the authors". No belittling or sarcastic comments.
- Requests for comparisons with methods that have no public code must be justified.
- Allowed evidence bars (CVPR 2024 PCs): a potentially transformative idea needs a basic proof of
  concept; an established problem with a plausible idea needs benchmark results; a weird, overly
  complex or seemingly incremental method needs extraordinary results, scrutinized carefully.
- Acceptance criteria (CVPR 2026 AC guide). Oral: potential to be very significant. Poster:
  incremental steps that expand the community's knowledge, useful tools, interest to a
  subcommunity, or creative ideas that are hard to judge but plausible. Reject: unlikely to be
  significant or already known, with clear evidence.

Real reviewers do not all follow these rules. Your persona card says how faithfully you follow them.
