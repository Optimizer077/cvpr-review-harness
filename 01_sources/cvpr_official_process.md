# CVPR Official Peer-Review Process: Source Dossier for the Reviewer Simulator

Compiled 2026-10-13. All pages accessed 2026-10-13 (fetched with curl + pandoc, then read in full; quotes are copied from the fetched text).

## Labels

- **VERIFIED (primary source)**: read directly on an official CVF / CVPR / ICCV / ECVA page, an official CVPR press page, official PC slides linked from the CVPR site, or the official OpenReview venue configuration (public API).
- **SECONDARY (blog/forum)**: news sites, blogs, Zhihu/Reddit, Paper Copilot, or search-result snippets of pages that could not be fetched.
- **NOT FOUND**: no primary source located. Best secondary evidence is listed separately and must not be treated as fact.
- **INFERRED**: my reconstruction from verified facts. Use only where the simulator needs a concrete value.

## Primary source index

| ID | URL | What it holds |
|---|---|---|
| RG26 | https://cvpr.thecvf.com/Conferences/2026/ReviewerGuidelines | CVPR 2026 reviewer guidelines (process, timeline, policies, FAQ) |
| RT26 | https://cvpr.thecvf.com/Conferences/2026/ReviewerTrainingMaterial | CVPR 2026 reviewer training: review structure, final-justification examples, error catalogue, checklist |
| AC26 | https://cvpr.thecvf.com/Conferences/2026/ACGuides | CVPR 2026 AC guidelines: triplets, meta-review, findings track, contemporaneous rule |
| SAC26 | https://cvpr.thecvf.com/Conferences/2026/SACGuides | CVPR 2026 SAC guidelines |
| AG26 | https://cvpr.thecvf.com/Conferences/2026/AuthorGuidelines | CVPR 2026 author guidelines: page limit, rebuttal, supplementary, LLM, arXiv |
| CFP26 | https://cvpr.thecvf.com/Conferences/2026/CallForPapers | CVPR 2026 dates and submission policies |
| D26 | https://cvpr.thecvf.com/Conferences/2026/Dates | CVPR 2026 official dates |
| TP26 | https://cvpr.thecvf.com/Conferences/2026/News/Technical_Program | CVPR 2026 press release (submissions, acceptances) |
| RG25 | https://cvpr.thecvf.com/Conferences/2025/ReviewerGuidelines | CVPR 2025 reviewer guidelines |
| CH25 | https://cvpr.thecvf.com/Conferences/2025/CVPRChanges | CVPR 2025 policy changes (irresponsible reviewers, LLM, 25-paper cap) |
| AG25 | https://cvpr.thecvf.com/Conferences/2025/AuthorGuidelines | CVPR 2025 author guidelines |
| TP25 | https://cvpr.thecvf.com/Conferences/2025/News/Technical_Program | CVPR 2025 press release |
| RG24 | https://cvpr.thecvf.com/Conferences/2024/ReviewerGuidelines | CVPR 2024 reviewer guidelines (incl. old LLM policy) |
| SL24 | https://docs.google.com/presentation/d/e/2PACX-1vT8bmHIEI3fBLTqSJpTV41mSAkf8_Y-yxahXokAaa4KnqfOuFHFvNYtSzyheoh_wiwEebz_YbQV2ivN/pub | "How to be a good reviewer? Reviewer Tutorial for CVPR 2024" (CVPR 2024 PCs), linked from RG24 |
| OR24 | https://docs.google.com/document/d/e/2PACX-1vTUNtouz7HlmxX_J7AZvGKC0sdgReV7rnmvCv1OtJQnvymKsf8eTruF2O8v-3B8ef8Cc4enPP8MOKpq/pub | CVPR 2024 OpenReview instructions for reviewers, linked from RG24 |
| AG24 | https://cvpr.thecvf.com/Conferences/2024/AuthorGuidelines | CVPR 2024 author guidelines |
| WR24 | https://cvpr.thecvf.com/Conferences/2024/News/Wrap_Release | CVPR 2024 wrap press release |
| BL23 | https://cvpr.thecvf.com/Conferences/2023/BlogPaperSubmissions | CVPR 2023 submissions blog |
| AP23 | https://cvpr.thecvf.com/Conferences/2023/AcceptedPapers | CVPR 2023 accepted papers page |
| CFP27 | https://cvpr.thecvf.com/Conferences/2027/CallForPapers | CVPR 2027 call for papers (dates, contemporaneous rule, LLM notice) |
| D27 | https://cvpr.thecvf.com/Conferences/2027/Dates | CVPR 2027 dates |
| ORG | https://api2.openreview.net/groups?id=thecvf.com/CVPR/{2024,2025,2026,2027}/Conference | OpenReview venue configuration (public JSON): review field ids, decision options |
| ORS | https://api2.openreview.net/invitations?id=thecvf.com/CVPR/{2025,2026}/Conference/-/Submission&expired=true | OpenReview submission-form fields (public JSON) |
| IRG25 | https://iccv.thecvf.com/Conferences/2025/ReviewerGuidelines | ICCV 2025 reviewer guidelines |
| ICH25 | https://iccv.thecvf.com/Conferences/2025/Changes | ICCV 2025 changes |
| IAG25 | https://iccv.thecvf.com/Conferences/2025/AuthorGuidelines | ICCV 2025 author guidelines |
| ERG26 | https://eccv.ecva.net/Conferences/2026/ReviewerGuide | ECCV 2026 reviewer guidelines |
| ECT26 | https://eccv.ecva.net/Conferences/2026/ReviewerContributionTypes | ECCV 2026 guidance to reviewers on contribution types |
| EAC26 | https://eccv.ecva.net/Conferences/2026/ACGuideLines | ECCV 2026 AC guidelines |
| ESP26 | https://eccv.ecva.net/Conferences/2026/SubmissionPolicies | ECCV 2026 submission policies (page limit, rebuttal) |
| ESL26 | https://docs.google.com/presentation/d/19xM-6GBNyW9t3RNF7A-2huH9wfybTMXxl2-csM_MNSs | ECCV 2026 reviewer tutorial slides, linked from ERG26 |

Pages checked that do not exist yet (404 "Page not found" on 2026-10-13): `cvpr.thecvf.com/Conferences/2027/{ReviewerGuidelines, AuthorGuidelines, ACGuides, SACGuides, ReviewerTrainingMaterial, CVPRChanges}`. The 2027 site currently has only Dates, Call for Papers, Call for Workshops, Organizers, Program Committee. CVPR 2025 has no public AC guide or training page (404).

---

## 1. Review form fields

### Bottom line

The live OpenReview review form is not public (guest access to `thecvf.com/CVPR/{2024,2025,2026}/Conference/-/Official_Review` returns `403 ForbiddenError`). Field **content** is verified from official guidance; exact on-screen field **titles** are verified only where noted.

### 1.1 CVPR 2026: VERIFIED structure (RT26, RG26, ORG)

RT26, "Step 3: Writing the Review", **VERIFIED**:
> "Your review should include:
> 1. Concise summary (2-4 sentences covering what the paper does and claims)
> 2. Strengths (specific, evidence-based points)
> 3. Weaknesses (specific, evidence-based concerns)
> 4. Constructive suggestions (how authors could address weaknesses)
> 5. Justified recommendation (clearly connecting your assessment to your rating)"

Post-rebuttal fields, **VERIFIED**:
- RG26 process step 9: "Reviewers update their ratings and justification."
- RT26 Step 5: "Submit your final rating and well-justified final recommendation by the deadline" / "Your final justification should be specific, evidence-based, and clearly connected to your rating".

OpenReview field ids, **VERIFIED (ORG 2026 JSON)**:
- `"review_rating": "preliminary_recommendation"`
- `"review_confidence": "confidence_level"`
- `"meta_review_recommendation": "final_recommendation"`
- `"rebuttal_name": "Rebuttal"`
- `"accept_decision_options": ["Accept (Oral)", "Accept (Highlight)", "Accept (Poster)"]`
- `"decision_heading_map": {"CVPR 2026": "Main Conference", "CVPR 2026 Findings": "Findings Workshop"}`

Other form elements whose existence is **VERIFIED**, with exact titles NOT FOUND:
- Data-asset attribution field. RG26: "please carefully check if a paper has adequately cited data assets used in the paper, and comment in the corresponding field in the review form."
- Withdrawn-dataset flag. RG26: "Reviewers should flag such cases in the review form for further consideration by the Area Chair and the Program Chairs."
- Ethics flag. AG26: "reviewers will have the ability to flag papers with significant ethical concerns. These will be referred to an ethics committee".
- Confidential channel to the AC. AC26: "As an AC, you may receive confidential comments from authors and reviewers during the review, rebuttal and discussion process." AG26: "Authors also have the possibility to submit a separate confidential comment to the area chair. Please do so only in exceptional circumstances."

### 1.2 CVPR 2025: VERIFIED field ids and content requirements (ORG, RG25)

- ORG 2025 JSON, **VERIFIED**: `"review_rating": "overall_recommendation"`, `"review_confidence": "confidence_level"`, `"meta_review_recommendation": "recommendation"`, `"rebuttal_name": "Rebuttal"`, `"accept_decision_options": ["Accept (Oral)", "Accept (Highlight)", "Accept (Poster)"]`, `"reviewers_conflict_policy": "NeurIPS"`, `"reviewers_conflict_n_years": 5`.
- RG25, **VERIFIED**: "Be specific about novelty... for a positive review, be sure to summarize what novel aspects are most interesting in the Strengths section." This confirms a Strengths field.
- Final rating: NOT FOUND as a named 2025 field. RG25 does have "February 6th, 2025: Final reviewer recommendations due".

### 1.3 CVPR 2024: VERIFIED form outline (SL24, OR24, ORG)

SL24 slide "Review form outline", **VERIFIED**, from the CVPR 2024 PCs (Akata, Crandall, Farhadi, Pless, Sato, Wu):

> **Summary:** "Explain the key ideas, contributions, and their significance. This is your abstract of the paper. The summary helps the AC and the authors understand the rest of your review and be confident that you understand the paper."
>
> **Strengths:** "What about the paper provides value? -- interesting ideas that are experimentally validated, an insightful organization of related work, new tools, impressive results, something else? Most importantly, what can someone interested in the topic learn from the paper?"
>
> **Weaknesses:** "What detracts from the contributions? Does the paper lack controlled experiments to validate the contributions? Are there misleading claims or technical errors? Is it possible to understand (and ideally reproduce) the method and experimental setups by reading the paper?"
>
> **Rating and Justification:** "Carefully explain why the paper should be accepted or not. This section should make clear which of the strengths and weaknesses you consider most significant."
>
> **Additional comments:** "Minor suggestions, questions, corrections, etc. that can help the authors improve the paper. Not crucial for the overall recommendation."

- OR24, **VERIFIED**: "To edit your final rating, click on the button 'Show Revisions' in your review. Next, click the edit button to edit the final rating and the final rating justification." So the 2024 form had **final rating** and **final rating justification** fields, edited after the rebuttal.
- ORG 2024 JSON, **VERIFIED**: `"review_rating": "overall_recommendation"`, `"review_confidence": "confidence"`.

### 1.4 CVPR 2027

- Review form: **NOT FOUND**. Reviewer guidelines are not published yet (404).
- ORG 2027 JSON currently shows `"review_rating": "rating"`, `"review_confidence": "confidence"`, `"rebuttal_name": "Author_Rebuttal"`, `"accept_decision_options": ["Accept (Oral)", "Accept (Poster)"]`. **Caution:** these look like OpenReview defaults before configuration. Do not treat them as the 2027 form.
- CFP27, **VERIFIED**: "CVPR 2027 will make use of large language models (LLMs) in selected parts of the conference and reviewing process. The exact scope, permitted uses, and associated guidelines are currently being finalized. This section will be updated with further details before the submission deadline."

### 1.5 Comparison venues

- **ECCV 2026**, **VERIFIED** (ESL26 slide "REVIEW FORM OVERVIEW"): SUMMARY / STRENGTHS / WEAKNESSES / RATING AND JUSTIFICATION / ADDITIONAL COMMENTS.
  - Strengths/Weaknesses: "Short bullet lists are not acceptable here."
  - Summary: "You must NOT use an LLM to write the summary."
  - ECT26: a reviewer who disagrees with the author-selected Contribution Type must explain it "in the 'Justification of Rating' section of the review".
  - ERG26: "describe the potential policy violation in the confidential comments field."
- **ICCV 2025**, **VERIFIED** (OpenReview group JSON for `thecvf.com/ICCV/2025/Conference`):
  - `"review_rating": "final_recommendation"`, `"review_confidence": "confidence_level"`, `"meta_review_recommendation": "preliminary_recommendation"`.
  - So ICCV 2025 forms carry both `preliminary_recommendation` and `final_recommendation` fields. The mapping in the config looks swapped.
  - IRG25 timeline: "Final ratings due by reviewers after discussions: May 27, 2025".

### 1.6 INFERRED simulator form (CVPR 2026/2027)

Built from 1.1 and 1.3. Field order follows RT26 and SL24.

1. Summary (2-4 sentences, own words)
2. Strengths
3. Weaknesses
4. Preliminary recommendation (rating)
5. Justification of the recommendation / suggestions for the rebuttal
6. Additional comments (minor)
7. Confidence level
8. Flags: data-asset attribution, withdrawn dataset, ethics
9. Confidential comment to AC (optional)

After the rebuttal:

10. Final rating
11. Final justification

The exact on-screen titles of fields 4–11 are **NOT FOUND**.

---

## 2. Rating scale and confidence scale

### 2.1 Exact rating-scale wording: NOT FOUND (all years 2024–2027)

No official CVPR page lists the rating levels. The OpenReview form is login-gated.

**Best secondary evidence (SECONDARY; do not quote as official):**

| Year | Evidence | Implied scale |
|---|---|---|
| CVPR 2024 | ORG field id `overall_recommendation` (primary, ids only). A CSDN/Zhihu summary in search snippets says "5 = accept, 4 = weakly accept, 3 = borderline" | 5-point scale, Borderline at the midpoint |
| CVPR 2025 | Paper Copilot https://papercopilot.com/statistics/cvpr-statistics/cvpr-2025-statistics/ reports reviewer-average range "1.00 to 5.00" | 5-point scale: 1 Reject(?), 2 Weak Reject, 3 Borderline, 4 Weak Accept, 5 Accept/Strong Accept(?) |
| CVPR 2026 | RT26 (**primary**) final-justification examples are labelled "Strong Accept", "Weak Accept", "Borderline", "Weak Reject", "Reject". Zhihu https://www.zhihu.com/question/1926956004710548595 (search snippet only; page blocked) reports scores "2、2、3 (weak reject, weak reject, borderline reject)" with confidence "4、5、5". Zhihu column https://zhuanlan.zhihu.com/p/2016597893688099115 (snippet) reports a reviewer moving "from borderline accept to weak accept" | **Conflicting.** RT26 labels imply a 5-level scale with a "Borderline" midpoint. The Zhihu reports imply an ICCV-2025-style 6-level scale with Borderline Reject/Accept. Unresolved |
| ICCV 2025 | r/MachineLearning "[D] ICCV 2025 reviews are out" (search snippet): "Reject (1), Weak Reject (2), Borderline Reject (3), Borderline Accept (4), Weak Accept (5), Accept (6)" | 6-level scale, no midpoint |
| ECCV 2026 | NOT FOUND | n/a |

**Recommendation for the simulator:** make the scale a config parameter. Default to the RT26 label set (Reject / Weak Reject / Borderline / Weak Accept / Strong Accept), because it is the only label set on an official 2026 page. Keep an ICCV-2025-style 6-level variant switchable.

### 2.2 Confidence scale

- Exact wording: **NOT FOUND** (all years). VERIFIED only that the field exists (`confidence` 2024; `confidence_level` 2025/2026; ORG).
- SECONDARY: Zhihu (2026) reports confidence values 4, 5, 5, so the scale has at least 5 levels.
- Official guidance on how to use confidence: EAC26 (ECCV 2026, **VERIFIED**): "Judge the quality of the review rather than taking note of the reviewer's confidence score; the latter may be more a measure of personality."

### 2.3 Decision categories: VERIFIED

- ORG 2025/2026: `"Accept (Oral)", "Accept (Highlight)", "Accept (Poster)"`. 2026 adds the "CVPR 2026 Findings" → "Findings Workshop" heading.
- AC26 acceptance criteria, **VERIFIED**:
  > "Award: major advances that will heavily impact the field; will be used by many people, create new capabilities, etc.
  > Oral: potential to be very significant; worthwhile for the whole community to hear about.
  > Poster: incremental steps that expand the sum of the community's knowledge or add bricks to the cathedral of knowledge; papers introducing useful tools; papers of interest to a subcommunity. Also, creative ideas that are hard to judge but could be promising -- no one knows the future, so we should give the benefit of the doubt to plausible ideas.
  > Reject: unlikely to be significant or already known. Provide clear evidence."
- SL24 (2024) has the same wording, with "Highlight Paper or Best Paper Award" at the top.

---

## 3. Reviewer guidelines: DOs, DON'Ts, policies

All items are **VERIFIED** from RG26 unless another source is named.

### 3.1 Core evaluation stance

- **SOTA.** "the fact that a proposed method does not exceed the state-of-the-art accuracy on an existing benchmark dataset is not grounds for rejection by itself. Rather, it is important to weigh both the novelty and potential impact of the work alongside the reported performance." The same text appears in RG24, RG25, IRG25 and ERG26.
- **Brave ideas.** "We recommend that you embrace novel, brave concepts, even if they have not been tested on many datasets."
- **Minor flaws.** "Minor flaws that can be easily corrected should not be a reason to reject a paper."
- RT26: "Do not over-weight SOTA tables alone—consider experimental design, insights, and broader contributions".
- RT26 "What Should Be Accepted?": "Recommend acceptance for papers that will interest CVPR attendees, are technically sound, and contribute meaningfully (methodologically, empirically, or conceptually). Balance novelty with significance and potential impact." Also: "A paper doesn't need to be perfect to be accepted—it needs to advance the field and meet quality standards."
- SL24, on different evidence bars: "Potentially transformative idea: basic proof-of-concept. Established problem, plausible idea: benchmark results. Weird, overly complex, implausible, and/or seemingly incremental: extraordinary results (which need to be scrutinized carefully). Position piece or theory paper: no experiments."

### 3.2 Novelty and prior-work claims

- "Claims in a review that the submitted work 'has been done before' MUST be backed up with specific references and an explanation of how closely they are related."
- "simply saying 'this is well known' or 'this has been common practice in the industry for years' is not sufficient: cite specific publications".

### 3.3 Detail, length, and tone

- **Detail.** "Bullet lists with one short phrase per bullet are NOT a detailed review." RG25 has "one short sentence per bullet".
- **Length.** "While length does not make a review good, short reviews tend to be enigmatic and so unhelpful". No numeric minimum length for reviews was found (**NOT FOUND**).
- **Address.** "Avoid referring to the authors in the second person ('you'). It is best to avoid the term 'the authors' as well... use the third person ('the paper')."
- **Tone.** "Belittling or sarcastic comments have no place in the reviewing process."
- **Out of scope.** "unless the area mismatch is extreme, you should keep an open mind".
- **Self-citation.** RG24/RG25 (dropped from RG26): "Do not give away your identity by asking the authors to cite several of your own papers."
- **No quota.** "Do NOT assume that your stack of papers necessarily should have the same acceptance rate as the entire conference ultimately will."

### 3.4 arXiv, concurrent and contemporaneous work

RG26 FAQ:
> "Authors are not required to discuss and compare their work with recent arXiv reports, although they should properly acknowledge those that directly and obviously inspired them. / Failing to cite an arXiv paper or failing to beat its performance SHOULD NOT be the SOLE grounds for rejection. / Reviewers SHOULD NOT reject a paper solely because another paper with a similar idea has already appeared on arXiv."

Also: "Do not reject papers solely because they are missing citations or comparisons to prior work that has only been published without review (e.g., arXiv or technical reports)."

AG26: "a technical report (departmental, arXiv, etc.) version of the submission that is put up without any form of direct peer-review is NOT considered prior art and does NOT NEED to be cited in the submission".

**2026 cutoff, VERIFIED (AC26 FAQ):** "We consider papers contemporaneous if they are published within the last four months." Also: "they may be excused for not knowing about papers not published in peer-reviewed conference proceedings or journals."

**2027 cutoff, VERIFIED (CFP27). This is a rule change.**
> "papers that appeared online after September 15th, 2026 will generally be considered 'contemporaneous' in the sense that the submission will not be rejected on the basis of the comparison to contemporaneous work. Authors are still expected to cite and discuss contemporaneous work and perform empirical comparisons to the degree feasible. Any paper that influenced the submission is considered prior work and must be cited and discussed as such... We do not distinguish arxiv papers and other published (conference & journal) papers, and the Contemporaneous-Work rule applies in the same way. More nuanced judgements, including how to determine the date of publication, will be made by the area chair handling the submission."

Implication: for 2027, arXiv papers posted on or before 2026-09-15 count as prior work. The old rule that arXiv is not prior art is replaced by a single date cutoff.

### 3.5 New experiments in rebuttal (PAMI-TC 2018 motion)

RG26 FAQ:
> "you may request clarifications, additional illustrations, or small experiments that could be reasonably run within the rebuttal phase with academic resources. Per a passed 2018 PAMI-TC motion, reviewers should not request substantial additional experiments for the rebuttal, or penalize for lack of additional experiments. 'Substantial' refers to what would be needed in a major revision of a paper. However, papers should also not be penalized for supplying extra results. The rebuttal may include figures with illustrations or comparison tables of results reported in the submission/supplemental material or in other papers."

RT26: "Evaluate based on what the rebuttal actually demonstrates, not what it promises for the camera-ready version. Promises without evidence should not change your assessment."

### 3.6 Closed-source comparisons (PAMI-TC 2024 motion)

RG26:
> "whenever a comparison of published research without publicly available code / data / pretrained models is requested (i.e., requiring re-implementation), it should be appropriately justified if used as a basis for a paper decision... comparisons should only be requested if the publication and / or code has been available sufficiently ahead of the submission deadline."

### 3.7 Datasets, ethics, limitations, reproducibility

- **Withdrawn datasets.** "not in itself grounds for rejection, should invite very close scrutiny". Also: "It is a violation of policy for a reviewer or Area Chair to require comparison on a dataset that has been withdrawn."
- **Dataset contributions.** These must be public "no later than the camera-ready deadline". "The use of private or otherwise restricted datasets... DOES NOT constitute grounds for rejection. However, private or otherwise restricted datasets cannot be claimed as contributions".
- **Limitations.** "Reviewers should weigh the inclusion of an honest discussion POSITIVELY, instead of penalizing the papers for including it... it cannot be the sole factor for rejection."
- **Negative societal impact.** "Reviewers should NOT reject a paper solely based on that the paper has not included such a discussion".
- **Code.** "Reviewers may optionally check this code... but are not required to."
- **Supplementary material.** "the supplementary material MAY NOT include results obtained with an improved version of the method (e.g., following additional parameter tuning or training), or an updated or corrected version of the submission PDF." AG26: "Reviewers will be encouraged to look at it, but are not obligated to do so."

### 3.8 Common reviewer errors (RT26 table, VERIFIED)

1. Ignorance / Inaccuracy
2. Pure Opinion
3. Novelty Fallacy ("It must be accepted because it's novel." / "It's just a small tweak, so it shouldn't be accepted.")
4. Blank Assertions
5. Policy Entrepreneurism ("You must beat SOTA on all benchmarks." / "You must release code to be accepted.")
6. Intellectual Laziness ("Beats SOTA ⇒ accept." / "Fails SOTA ⇒ reject." / "The result difference is small, so it's not worth publishing.")

RT26: "Almost all reviewing errors stem from a combination of laziness... and self-importance". The same six categories appear in SL24, "Developed from Reviewer Slides for CVPR'21".

### 3.9 Unacceptable and good final justifications (RT26, VERIFIED)

Unacceptable final justifications:
- "The paper is good overall."
- "The paper is technically sound, but I recommend reject."
- "The rebuttal addresses my concerns, so I increase my score." (What concerns? How?)
- "The rebuttal doesn't change my opinion, so I keep my score." (Why not? What was unconvincing?)

Good examples are given for Strong Accept, Weak Accept, Borderline, Weak Reject and Reject. Each one cites specific sections, tables or equations, names prior work, says what the rebuttal fixed or did not fix, and ends with "I maintain my rating of X". Use these as few-shot templates for the simulator.

### 3.10 Final checklist and effort (RT26, VERIFIED)

- **Checklist:** "Brief, accurate paper summary present? / Has the paper been checked for standard errors? Incorrect mathematics; Omitted material (experiments, context, citations); Done before / Strengths and weaknesses stated with specific evidence? / Is the review too short? / Tone professional and constructive throughout? / ... Policy compliance (LLM use, confidentiality, conflicts) checked?"
- **Time:** "Plan for 4-6 hours per paper total... 1-2 hours for reading, 2-3 hours for writing the review, and 1-2 hours for rebuttal response and discussion."
- **Expertise:** if a paper is outside the reviewer's expertise, "clearly state your expertise limitations in your review."

### 3.11 LLM policy for reviewers (by year, VERIFIED)

- **2024 (RG24):** "Referees may use any device, including an LLM, to polish their review wording, but must vouch for... the accuracy of the review. It is a significant act of referee misconduct to allow an LLM to see a submission... This would allow PCs to move to exclude the relevant referee from submitting to CVPR for up to two years."
- **2025 (RG25 / CH25):** "Large language models (LLMs) are NOT allowed to be used for writing the reviews nor the meta-reviews at any step." Allowed: "background research or to check short phrases for clarity. Grammar checker softwares that may have used LLMs are allowed." Enforcement: oversight process; papers "desk rejected per discretion of the PCs".
- **2026 (RG26):** same rules. LLM-assisted reviews are listed explicitly as "highly irresponsible". Prompt injection was added: "such prompt injections are considered a collusion attempt"; a reviewer swayed by one "may face consequences, including the desk rejection of their own submissions."
  - RT26 is stricter. Grammar checks are allowed only for "short phrases you have already written (under ~50 words, containing no submission-specific content)".
  - RT26 enforcement: "Reviewers who violate this policy may be barred from submitting to CVPR for two years." This differs from RG26's "desk rejected" wording; both are official.
- **2027 (CFP27):** "will make use of large language models (LLMs) in selected parts of the conference and reviewing process"; details "being finalized".

### 3.12 Irresponsible-reviewer and deadline policies

- **2026 (RG26), VERIFIED:**
  > "Highly irresponsible reviewing includes: unreasonably short reviews that fail to reference specific technical content from the paper; reviews containing only generic comments that could apply to any submission without addressing the paper's actual contribution; reviews with demonstrable factual errors about the paper's methodology or results that indicate superficial reading; and reviews generated by or substantially assisted by Large Language Models. This policy does not penalize reviewers for holding different technical opinions, missing minor details, writing concise but substantive reviews, or having legitimate disagreements... Any reviewer whose review is deemed to be 'highly irresponsible' will face a desk rejection of all papers on which they are an author at the discretion of the PCs."

  Deadline: "Any reviewer who fails to submit their assigned reviews by the deadline will face a desk rejection of all papers on which they are an author at the discretion of the PCs." Review metadata is shared with future venues.
- **2025 (CH25), VERIFIED:** ACs could flag "highly irresponsible" "in addition to the 'not met expectations' as in the past". Examples: "one-sentence reviews, reviews generated by Large Language Models (LLMs), reviews not relevant to the paper or that miss a substantial portion of the paper."
- **2025 outcome, SECONDARY** (PC email quoted at https://iplab.dmi.unict.it/news/cvpr-2025/): "the Program Chairs (PCs) decided to desk-reject 19 papers authored by confirmed highly irresponsible reviewers... which would have been accepted otherwise".

### 3.13 Reviewer load

- **2026:** **NOT FOUND** as a number. RG26 says only that assignment "takes into account AC suggestions, paper load, and conflict constraints". AC26: "We are looking for 3 quality reviews per paper."
- **2024 (SL24), VERIFIED:** "Papers are assigned to reviewers (3 per paper)"; "Reviewers submit initial reviews, typically handling 4-6 papers each"; ACs get "usually not more than 30 papers per AC".
- **2025 (CH25), VERIFIED:** all authors are obliged to review; "the number of reviews will depend on the level of seniority".
- **2027 (CFP27), VERIFIED:** "All authors commit to serve as reviewers, area chairs, or senior area chairs when invited".

---

## 4. Rebuttal, discussion, decision process, acceptance rates, timelines

### 4.1 Rebuttal format (VERIFIED)

- **AG26:** "The rebuttal is limited to a one-page PDF file using the rebuttal template included in the CVPR 2026 Submission Template. Responses longer than one page will simply not be reviewed. This includes responses where the margins and formatting are deemed to have been significantly altered". Also: "The rebuttal must maintain anonymity. It cannot include links to external material such as code, videos, etc." And: "Authors should refrain from including new contributions or experimental results in the rebuttal, especially when not specifically requested to do so by the reviewers. Reviewers are instructed to disregard any such contributions."
- **AG25:** same, plus "It cannot include links, even anonymous ones".
- **AG24:** same one-page rule.
- **Tension (VERIFIED, both official):** RG26 says "papers should also not be penalized for supplying extra results" and allows "small experiments". AG26 tells authors to refrain from new results unless requested.

### 4.2 Discussion and final recommendation (VERIFIED, RG26 steps 7–13)

> "7. Authors receive reviews and have the option of submitting a rebuttal... 8. Reviewers and ACs discuss, based on all reviews, rebuttal, and paper. 9. Reviewers update their ratings and justification. 10. ACs draft meta-reviews. 11. ACs discuss their meta-reviews and tentative decisions with two other ACs in an 'AC Triplet'. They discuss borderline papers and check meta-reviews for their quality. In addition to accept/reject decisions, AC triplets provide nominations for spotlights, orals, and awards to the PCs. 12. PCs and SACs check meta-reviews, decisions, and nominations. 13. PCs make the final determination".

- **2024 (SL24), VERIFIED:** AC **pairs** (primary + secondary AC), not triplets.
- **2025, SECONDARY** (UNICT quoting the PC email): "a triplet of three ACs reviewed each paper holistically". "All but 4 papers were initially evaluated by at least three independent reviewers... the AC served as the third reviewer."
- **2026 roles (AC26), VERIFIED:** "Secondary ACs need to approve the decision and meta review of the primary AC".
- **Findings track 2026 (AG26), VERIFIED:** "a venue for technically sound papers with solid experimental validation, even if their novelty is more incremental. Area Chairs will recommend papers to the Findings Track... Findings papers will appear in the workshop proceedings."
- **Decision wording 2026, SECONDARY** (https://m.sohu.com/a/989252364_114760/): the decision email was titled "Preliminary Paper Decision"; acceptance stays conditional on plagiarism, dual-submission and conduct checks.

### 4.3 Acceptance statistics

| Year | Submissions | Accepted | Rate | Label / source |
|---|---|---|---|---|
| 2023 | 9,155 | 2,359 | 25.8% | VERIFIED, BL23: "accepted just 2,359 papers, an acceptance rate of only 25.8 percent"; AP23 |
| 2024 | 11,532 | 2,719 | 23.6% (computed) | VERIFIED, WR24: "11,532, a 26% increase over 2023" / "from the 2,719 accepted papers" |
| 2025 | 13,008 | 2,872 (TP25) or 2,878 (PC email) | ~22.1% | VERIFIED TP25: "13,008 paper submissions—a 13% increase over 2024—but only 2,872 were accepted". SECONDARY (UNICT, PC email): "recommended 2878 papers for acceptance, resulting in an acceptance rate of 22.1%". Breakdown (Paper Copilot, SECONDARY): 2,468 Poster / 388 Highlight / 15 Award Candidate |
| 2026 | 16,092 | 4,089 presentations (TP26) / 4,090 recommended | ~25.4% | VERIFIED TP26: "16,092, a 24% increase over 2025... about one-quarter were accepted to the program, resulting in 4,089 paper presentations". SECONDARY (CVPR X post via search snippet; sohu): "recommended 4,090 papers... 25.42%", plus 1,717 recommended to the Findings workshop (opt-in) |

Desk rejections and withdrawals are excluded from the 2025/2026 denominators (SECONDARY: "this number excludes papers withdrawn or desk-rejected during the review process").

### 4.4 Timelines (VERIFIED)

- **CVPR 2026 (RG26 / D26):**
  - Abstract Nov 6–7, 2025 (RG26 says Nov 6; D26 and CFP26 say Nov 07 AoE)
  - Paper Nov 13, 2025; supplementary Nov 20, 2025
  - Papers assigned Dec 15; reviews due Jan 12, 2026; emergency reviews Jan 12–22
  - Reviews released Jan 22; rebuttals due Jan 29
  - AC–reviewer discussion Jan 30–Feb 5; final reviewer recommendations Feb 5
  - AC consolidation report Feb 11; triplet week Feb 6–16; meta-review Feb 17
  - Decisions Feb 20; oral/spotlight/award decisions Feb 21–26
- **CVPR 2025 (RG25):** assigned Dec 12, 2024; reviews due Jan 13, 2025 (moved from Jan 9); rebuttal Jan 23–30; discussion Jan 30–Feb 6; final recommendations Feb 6.
- **CVPR 2024 (RG24):** assigned Dec 3, 2023; reviews due Jan 9, 2024; rebuttal Jan 23–30; discussion Jan 30–Feb 6; final recommendations Feb 7.
- **CVPR 2027 (D27 + CFP27):**
  - Paper registration Nov 10, 2026 (11:59 PM AoE); submission Nov 16, 2026 AoE; supplementary Nov 23, 2026 AoE
  - Reviews released Jan 25, 2027; rebuttal period Jan 25 – Feb 1, 2027
  - Final decisions Feb 25, 2027; conference June 20–25, 2027, Seattle
  - Dual-submission window "November 16, 2026 – February 22, 2027"
  - Review-period dates: **NOT FOUND**
  - Program Chairs: Alexander Berg, Vicky Kalogeiton, Nicu Sebe, Humphrey Shi, Angela Yao

---

## 5. Area Chair guidelines (CVPR 2026, AC26, VERIFIED)

**Weighing reviews:**
- "Follow reviewer consensus for unanimous decisions, unless there are extraordinary unusual circumstances — For example, to accept a paper with unanimously negative reviews, there should be significant referee error, or a very convincing rebuttal; to reject a paper with unanimously positive reviews, there should be exceptional circumstances such as significant previously undetected technical errors, or undetected fraud or plagiarism."
- "For mixed reviews, you should analyze all reviews critically, and see if you agree with their claims."
- "Among the important responsibilities of ACs is to ensure reviewers' judgments are in line with the CVPR 2026 reviewer guidelines."

**Borderline papers and calibration:**
- "We'll primarily use the spread of the review scores to identify borderline papers."
- "We do not plan to share the rating curve. The goal of CVPR is to accept quality papers, and not be constrained by review scores."
- "Do NOT normalize decisions within your own batch... a batch of 30 papers represents just 0.2% of the total".

**Low-quality reviews:**
- "read all reviews to ensure they are high-quality reviews... If you want reviewers to expand on their arguments, share your feedback with reviewers early on."
- "flag extremely delayed reviews, low-quality reviews, or papers with significant LLM usage not disclosed in the paper."
- "You should be checking reviews as they are submitted, and catching fundamental errors at that time".
- Emergency reviewers "should be assigned no later than Jan 14".

**Discussion:**
- "summarize the critical concerns and ask reviewers to comment on whether they share the concern".
- "encourage reviewers to comment specifically on which of their concerns were addressed, and which ones were not."
- Example prompt: "R2 mentioned unclear novelty. Could R2 point to the most relevant works that overlap?"

**Meta-review content:**
- "A good meta-review summarizes the paper's contribution, highlights the main points of the reviewers' initial assessment, discusses the arguments of the rebuttal, summarizes the reviewers' reason for their final recommendation, and concludes with the recommendation of the AC and its underlying rationale."
- "Aim to write a meta-review of at least 60 words."
- "Write a standalone meta-review — This is a decision rationale... Avoid: 'all reviewers said reject, so the paper is rejected' - this is not acceptable if a rebuttal was provided".
- "Authors may not agree with your decision, but they should understand it".

**Triplet and Findings:**
- "We recommend that every AC prepare a spreadsheet... For each paper, summarize its contributions, the reviewer assessments, and your recommendation."
- "aim to find a consensus recommendation among the ACs in the triplet. If a consensus is not possible, involve your senior area chair".
- Findings recommendations go to "technically sound papers with solid experimental validation and contributing valuable insights, even if their technical novelty is more incremental."

**Desk-reject flags:**
- "if papers exceed the length restrictions even by a single character, or if an incorrect template was used".

**SAC role (SAC26):**
- "calibrating decisions across ACs, and discussing and deciding borderline papers"
- ~24 ACs per SAC

**ECCV 2026 comparison (EAC26, VERIFIED):**
- "Don't focus too much on the scores. Instead, look carefully at the comments."
- "Indicate that you have read the author's response".
- "If you find yourself wanting to overrule a unanimous opinion of the referees, the standards for your summary should be at the level of a full review."
- "Please attempt to take a decisive stand on borderline papers."
- "encourage risk and recognize that new approaches can't initially yield state-of-the-art competitive results."

---

## 6. What CVPR values; format and supplementary rules (VERIFIED)

**Values:**
- Technical soundness plus contribution.
- Novelty weighed with impact and alongside performance.
- SOTA is not required.
- Brave ideas are welcome.
- Reproducibility is encouraged but not required.
- Honest limitations count as a plus.
- See 3.1. SL24: "Each weak or mediocre paper we accept hurts the conference a little (though not as much as rejecting a good paper)."

**Page limit:**
- AG26: "Papers are limited to eight pages, including figures and tables, in the CVPR style. Additional pages containing only cited references are allowed."
- "Papers that are not properly anonymized, or do not use the template, or have more than eight pages (excluding references) will be rejected without review."
- The same rule appears in AG24, AG25 and IAG25. ECCV 2026: 14 pages LNCS (ESP26).

**External links (AG26):**
- "Authors are not allowed to include external links (e.g., to webpages, images, or videos) in submissions, supplementary material, and rebuttal, when the links expand content and subvert the reviewing process."
- The 2026 submission form requires the confirmation: "I confirm that the paper submission and supplementary material contain no external links intended to expand content and circumvent review limitations, and no prompt injection or similar attempts to manipulate reviews." (ORS 2026)

**Supplementary material:**
- Single ZIP or PDF, ≤200 MB (ORS 2026); paper PDF ≤50 MB.
- Deadline one week after the paper (2026: Nov 20; 2027: Nov 23, 2026).
- Contents may include "videos, proofs, additional figures or tables, more detailed analysis of experiments presented in the paper, or a concurrent submission to another conference."
- No improved-method results and no corrected PDF (RG26 FAQ).

**Authors' LLM policy (AG26):**
- "Papers containing citations of non-existent material will be rejected when found, and may be rejected without review."
- "papers containing obvious factual inaccuracies will be rejected when found".
- "It is not a defense... to argue that 'an LLM did it'."
- Prompt injection: "may be desk-rejected without review".

**Other:**
- Compute reporting 2026 (AG26): "reports are not visible to reviewers and will not influence acceptance decisions."
- Dual submission (AG26): "substantially similar in content (defined as having 20 percent or more overlap)" counts as dual submission. A prior publication is ">four pages... accepted"; arXiv is not a publication.
- Max 25 submissions per author (AG26, CH25).

---

## 7. Cross-venue notes (VERIFIED unless marked)

- **ICCV 2025:**
  - Same reviewer-guideline text as CVPR 2026 (SOTA, arXiv, rebuttal) and the same one-page rebuttal (IAG25).
  - Final ratings due May 27, 2025.
  - Reviewer names visible to co-reviewers after decisions (ICH25 item 6; CVPR 2025 withdrew this policy, CH25).
  - Single deadline for paper and supplementary (ICH25 item 8: "some submissions squeezed in new critical experiments into the supplementary material").
  - Rating scale: SECONDARY 6-level (see 2.1).
- **ECCV 2026:**
  - Authors choose one Contribution Type (Algorithms/General, Theory/Foundational, Applied/Systems, Datasets/Benchmarks, Concept & Feasibility). Reviewers must judge through that lens (ECT26).
  - Algorithms/General reminder: "Do not penalize these submissions for: Lack of new datasets / Absence of real-world deployment / Limited theoretical analysis."
  - Rebuttal: one page, two-column, including references (ESP26).
  - Reviews due Apr 21, 2026; final recommendations May 20, 2026 (ERG26).

---

## 8. NOT FOUND summary

1. Exact CVPR rating-scale wording and number of levels for 2024, 2025, 2026 and 2027 (preliminary and final). See 2.1 for secondary evidence.
2. Exact confidence-scale wording for any year.
3. Exact on-screen titles of CVPR 2025/2026 review-form fields beyond what is quoted above. The form sits behind an OpenReview login; the guest API returns 403.
4. CVPR 2026/2027 reviewer load (papers per reviewer) as a number.
5. Minimum review length for reviewers. None is stated; only the AC meta-review target of 60 words exists.
6. CVPR 2027 reviewer/AC guidelines, review-period dates, and LLM-use details. These are announced as forthcoming in CFP27.
7. ICCV 2025 / ECCV 2026 official scale wording.

---

## What the simulator must replicate

1. Each paper gets ≥3 independent reviewers, an AC, a secondary AC, an AC triplet, then SAC/PC sign-off. Decision labels: Reject / Accept (Poster / Highlight / Oral), plus a Findings recommendation (2026+).
2. Each review contains: 2–4 sentence summary in own words, evidence-based strengths, evidence-based weaknesses, constructive suggestions, preliminary recommendation + justification, confidence, optional confidential note to the AC.
3. After the rebuttal, each reviewer gives a final rating and a final justification that names which concerns were or were not resolved.
4. Make the rating scale configurable. Default to Reject / Weak Reject / Borderline / Weak Accept / Strong Accept (RT26 labels); include a 6-level ICCV-style variant. The exact scale is NOT VERIFIED.
5. Not beating SOTA is never sufficient grounds for rejection. Weigh novelty and impact alongside performance. Minor fixable flaws do not justify rejection.
6. Every "done before" or "well known" claim needs specific citations and an explanation of how close the prior work is. Otherwise flag the review as a "blank assertion".
7. Check each review against the six RT26 errors: ignorance/inaccuracy, pure opinion, novelty fallacy, blank assertion, policy entrepreneurism, intellectual laziness.
8. Prior-work cutoff for 2027: work online after 2026-09-15 is contemporaneous and cannot be a basis for rejection. Earlier arXiv work counts as prior work, the same as published papers.
9. Reviewers may request only small experiments that can be run in the rebuttal window with academic resources. No major-revision requests. Comparisons with closed-source work need justification.
10. Rebuttal: one-page PDF, anonymous, no external links. Promises without evidence do not move scores. New results are disregarded unless requested, and authors are not penalized for adding them.
11. AC behavior: follow a unanimous verdict unless there is referee error or a convincing rebuttal. Find borderline papers by score spread. Do not normalize decisions within a batch. Push reviewers on specific unresolved concerns.
12. Meta-review: standalone, at least 60 words. Cover contribution, initial assessments, rebuttal arguments, final reviewer reasons, and the AC recommendation with its rationale. "All reviewers said reject" alone is invalid.
13. Positives to credit: honest limitations, a societal-impact discussion, released code, cited data assets. Never require code release, a limitations section, or comparison on a withdrawn dataset.
14. Desk-reject triggers: more than 8 pages excluding references, wrong template, broken anonymity, prompt injection, hallucinated citations, or content-expanding external links.
15. Calibration: CVPR acceptance is about 22–26% (2023: 25.8%, 2024: 23.6%, 2025: ~22.1%, 2026: ~25.4%). Do not force any per-reviewer acceptance quota.
