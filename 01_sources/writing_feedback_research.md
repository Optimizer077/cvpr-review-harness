# Writing feedback and revision coaching: evidence notes

Compiled 2026-10-14 for the revision coach (`hx.py stage <session> coach`, which turns one round of simulated reviews into `REVISION_PLAN.md` and `revision_plan.json`) and for the writer.
Purpose: ground how the coach phrases, ranks and limits its advice, and how the writer is told to write, in feedback research, peer-review studies, writing research, advice from experienced CV/ML authors, and studies of LLM-generated feedback.

**Labels** (as in `reviewer_behavior_literature.md` and `figure_research.md`)
- `Verified: yes [full]`: I read the full text (HTML, PDF text or full web page). Numbers and quotes come from it.
- `Verified: yes [abs]`: I read the official abstract or a publisher or institute landing page. Details beyond it are not checked.
- `Verified: yes [page]`: an official guideline, checklist or the author's own page, read in full. Quotes are exact.
- `Verified: no`: I could not open it. Not used for any rule.
- `Inference:` marks my own reading of a result. It is not a claim the cited authors make.

Each entry ends with **Design rule derived**. "Coach" is the agent that writes the revision plan; "writer" is the agent that edits the paper. Section 7 lists the rules and the files that implement them.

---

## 1. Feedback science: when feedback improves performance

### 1.1 Feed up, feed back, feed forward
- **Hattie & Timperley 2007**, "The Power of Feedback", *Review of Educational Research* 77(1):81-112; https://doi.org/10.3102/003465430298487 (the publisher page returned 403; I read the published version hosted at https://www.uky.edu/~gmswan3/575/Hattie_Timperly_2007.pdf). `Verified: yes [full]`
  - Feedback is "information provided by an agent ... regarding aspects of one's performance or understanding". Across 12 earlier meta-analyses (196 studies, 6,972 effect sizes) the average effect was 0.79, "twice the average effect".
  - Effects vary by type (Table 2): cues 1.10, corrective feedback 0.37, praise 0.14 (11 meta-analyses, 4,410 effects), programmed instruction -0.04. "Those studies showing the highest effect sizes involved students receiving information feedback about a task and how to do it more effectively."
  - Effective feedback answers three questions, "Where am I going? ... How am I going? ... and Where to next?", which "correspond to notions of feed up, feed back, and feed forward". The "Where to next?" question "can have some of the most powerful impacts on learning".
  - Four levels: task, process, self-regulation and self. "We argue that FS [feedback about the self] is the least effective". Praise "carries little information"; the meta-analyses cited give 0.12 (Wilkinson) and 0.09 (Kluger & DeNisi).
  - Feedback "is most powerful when it addresses faulty interpretations, not a total lack of understanding"; "If students lack necessary knowledge, further instruction is more powerful than feedback information." "Too much feedback within a level may even detract from performance."
  - *Inference:* for a paper, feed up is what a reviewer must understand and believe after reading; feed back is where the draft stands with the reviewers; feed forward is the concrete edit.
  - **Design rule derived:** every plan item states the target (what a reviewer must understand or believe), the gap (what the reviews show), and the next step (the action and the proposed text). Comments stay at the level of the paper's text and evidence, never the authors. When a needed element is missing entirely (no limitations paragraph, no ablation table), the item supplies a draft or an outline, not only a critique.

### 1.2 Feedback can lower performance
- **Kluger & DeNisi 1996**, "The effects of feedback interventions on performance: A historical review, a meta-analysis, and a preliminary feedback intervention theory", *Psychological Bulletin* 119(2):254-284; https://doi.org/10.1037/0033-2909.119.2.254 (abstract read on the university research portal, https://cris.huji.ac.il/en/publications/the-effects-of-feedback-interventions-on-performance-a-historical/). `Verified: yes [abs]`
  - 607 effect sizes, 23,663 observations. The average effect was positive (d = 0.41), but "over 1/3 of the FIs [feedback interventions] decreased performance".
  - Feedback shifts attention among task learning, task motivation and meta-task (self-related) processes. Its effect falls as attention moves toward the self and away from the task.
  - **Design rule derived:** because feedback can do harm, the plan never comments on the authors (competence, effort, language background) and never grades the paper. Each sentence points at a passage, a claim or a result.

### 1.3 Guidelines for formative feedback
- **Shute 2008**, "Focus on Formative Feedback", *Review of Educational Research* 78(1):153-189; https://doi.org/10.3102/0034654307313795 (the publisher page returned 403; I read the published version on the author's site, https://myweb.fsu.edu/vshute/pdf/shute%202008_b.pdf). `Verified: yes [full]`
  - Formative feedback is "information communicated to the learner that is intended to modify his or her thinking or behavior to improve learning"; it "should be nonevaluative, supportive, timely, and specific".
  - Things to do (Table 2): "Focus feedback on the task, not the learner"; "Provide elaborated feedback" that describes "the what, how, and why of a given problem"; "Present elaborated feedback in manageable units", because too much information may "invoke cognitive overload"; "Be specific and clear"; "Keep feedback as simple as possible but no simpler"; "Reduce uncertainty between performance and goals".
  - Things to avoid (Table 3): normative comparisons; overall grades (feedback "should note areas of strength and provide information on how to improve, as warranted and without overall grading"; summarizing Wiliam 2007, students given "just comments showed large gains" while those "with grades and comments showed no gains"); feedback that "discourages the learner or threatens the learner's self-esteem"; praise, to be used "sparingly, if at all".
  - **Design rule derived:** the plan is a short list of elaborated items (what is wrong, how to fix it, why it matters), each small enough to act on alone. It names strengths to keep and contains no scores, ratings or comparisons with other papers, because a grade next to comments can cancel the comments.

### 1.4 Information content decides the effect
- **Wisniewski, Zierer & Hattie 2020**, "The Power of Feedback Revisited: A Meta-Analysis of Educational Feedback Research", *Frontiers in Psychology* 10:3087; https://doi.org/10.3389/fpsyg.2019.03087. `Verified: yes [full]`
  - 435 studies, 994 effect sizes, more than 61,000 participants. Average d = 0.48 (95% CI 0.44-0.51) after removing 35 extreme values (0.55 before). Heterogeneity was high (I² 83-86%).
  - By information content: reinforcement or punishment d = 0.24; corrective feedback d = 0.46; high-information feedback (task and process information, sometimes self-regulation) d = 0.99. "Feedback, on average, is powerful, but some feedback is more powerful."
  - **Design rule derived:** an item that only says "unclear" or "weak" is low-information feedback. Each item names the passage, the likely misreading or doubt, the replacement, and why the replacement answers the reviewer.

---

## 2. Constructive and destructive peer review

### 2.1 Unprofessional reviews and who they harm
- **Silbiger & Stubler 2019**, "Unprofessional peer reviews disproportionately harm underrepresented groups in STEM", *PeerJ* 7:e8247; https://doi.org/10.7717/peerj.8247 (the journal page returned 403; I read the PMC copy, https://pmc.ncbi.nlm.nih.gov/articles/PMC6911688/). `Verified: yes [full]`
  - Survey of 1,106 researchers in 46 countries and more than 14 STEM fields. An unprofessional review was defined as "any statement that is unethical or irrelevant to the nature of the work".
  - 58% (642) had received at least one; 70% of those had received more than one.
  - Harm differed by group. The probability of reporting no doubt at all about one's scientific aptitude after such a review was 0.40 for white men and 0.20 for white women and white non-binary respondents.
  - The authors ask reviewers to "interrogate whether comments are constructive and impartial".
  - **Design rule derived:** the coach restates harsh or sarcastic review text as its substantive point and drops the rest. A remark with no substantive point (about the authors, their language or their presumed experience) is deferred with the reason "not about the paper".

### 2.2 How common unsupported critiques are
- **Gerwing, Allen Gerwing, Avery-Gomm, Choi, Clements & Rash 2020**, "Quantifying professionalism in peer review", *Research Integrity and Peer Review* 5:9; https://doi.org/10.1186/s41073-020-00096-x (PMC: https://pmc.ncbi.nlm.nih.gov/articles/PMC7379804/). `Verified: yes [full]`
  - 1,491 reviewer comment sets (ecology and evolution; behavioural medicine). 12% (179) contained at least one unprofessional comment; 41% (611) at least one "incomplete, inaccurate or unsubstantiated critique" (IIUC); 57% contained neither.
  - IIUC types included superficial review (19%), arguments from authority (27%), claimed missing literature with no citation (19%), attacks on common, well-supported methods (14%), and inaccurate statements about clearly stated information (22%, case studies only).
  - The authors say reviewers "must be specific when providing criticism, as well as provide references to support their points".
  - *Inference:* the fields differ from CV, but the categories match the lazy-review heuristics in `reviewer_behavior_literature.md` §1.10, which some simulated personas produce on purpose.
  - **Design rule derived:** not every review point deserves an edit. The coach checks each point against the paper. If the paper states the answer clearly where a reader would look, the point is deferred with that quote. If the answer is buried or ambiguous, it becomes a writing item (rule 10). A "missing related work" claim that names no paper is deferred unless another reviewer names one.

### 2.3 What the venues ask of reviewers
- **CVPR 2026 Reviewer Guidelines**; https://cvpr.thecvf.com/Conferences/2026/ReviewerGuidelines. `Verified: yes [page]`
  - "Please include specific feedback on ways the authors can improve their papers." "Be generous about giving the authors new ideas for how they can improve their work."
  - "If there is a particular section that is unclear, point it out and give suggestions for how it can be clarified." "Be specific when you suggest that the writing needs to be improved."
  - "A harshly written review will be resented by the authors, regardless of whether your criticisms are true." "Belittling or sarcastic comments have no place in the reviewing process."
  - "Look for what is good or stimulating in the paper, and what knowledge advance it has made."
- **NeurIPS 2025 Reviewer Guidelines**; https://neurips.cc/Conferences/2025/ReviewerGuidelines. `Verified: yes [page]`
  - "Do not make vague statements in your review, as they are unfairly difficult for authors to address." "Try to keep your feedback constructive when possible."
  - Reviewers should "state the clear criteria under which your evaluation score could increase or decrease."
  - On limitations: "authors should be rewarded rather than punished for being up front about the limitations of their work".
- **ICLR 2026 Reviewer Guide**; https://iclr.cc/Conferences/2026/ReviewerGuide. `Verified: yes [page]`
  - Reviewers "Provide additional feedback with the aim to improve the paper" and "Make it clear that these points are here to help, and not necessarily part of your decision assessment."
  - Requests for more experiments "should be limited in scope and serve to more thoroughly validate existing results".
- **Design rule derived:** (a) the plan uses the tone the venues ask of reviewers, even when the simulated reviews do not; (b) every item says what would change the reviewer's assessment, which is the plan's `verification` field; (c) the plan separates changes that move decisions from optional polish; (d) experiment items are scoped to validating the paper's existing claims.

---

## 3. Scientific writing structure

### 3.1 Reader expectations at the sentence level
- **Gopen & Swan 1990**, "The Science of Scientific Writing", *American Scientist* 78(6):550-558; https://www.jstor.org/stable/29774235 (the American Scientist page returned 503; I read the full reprint distributed with the journal's permission, https://www.cs.columbia.edu/~djhsu/coms6998-f17/science-of-writing.pdf, which reproduces https://www.e-education.psu.edu/styleforstudents/c10_p1.html). `Verified: yes [full]`
  - Premise: "readers make many of their most important interpretive decisions about the substance of prose based on clues they receive from its structure."
  - Principles: "Follow a grammatical subject as soon as possible with its verb." "Place in the stress position the 'new information' you want the reader to emphasize"; the stress position "coincides with the moment of syntactic closure". "Place the person or thing whose 'story' a sentence is telling at the beginning of the sentence, in the topic position", with the "old information" that links backward. "Articulate the action of every clause or sentence in its verb." "In general, provide context for your reader before asking that reader to consider anything new." Each unit of discourse should "serve a single function or make a single point". "Readers expect a unit of discourse to be a story about whoever shows up first."
  - Against fixed limits: "A sentence is too long when it has more viable candidates for stress positions than there are stress positions available." "None of these reader-expectation principles should be considered 'rules.'"
  - The authors claim the results "are substantive, not merely cosmetic: Improving the quality of writing actually improves the quality of thought." *Inference:* the evidence is worked revisions of real passages, not an experiment.
  - **Design rule derived:** sentence-level guidance is checkable sentence by sentence: subject and verb close together; the sentence starts from something already introduced; the new claim or number comes last; the action is a verb ("improves", not "yields an improvement in"). The coach's proposed text follows the same principles. There is no sentence-length or readability-score target.

### 3.2 Paper structure
- **Mensh & Kording 2017**, "Ten simple rules for structuring papers", *PLoS Comput Biol* 13(9):e1005619; https://doi.org/10.1371/journal.pcbi.1005619. `Verified: yes [full]`
  - Rules include "Focus your paper on a central contribution, which you communicate in the title"; "Write for flesh-and-blood human beings who do not know your work"; "Stick to the context-content-conclusion (C-C-C) scheme"; "Tell a complete story in the abstract"; "Communicate why the paper matters in the introduction"; "Deliver the results as a sequence of statements, supported by figures, that connect logically to support the central contribution"; "Discuss how the gap was filled, the limitations of the interpretation, and the relevance to the field"; "Allocate time where it matters: Title, abstract, figures, and outlining".
  - "The title, abstract, and figures are viewed by far more people than the rest of the paper." "The introduction highlights the gap that exists in current knowledge or methods and why it is important."
  - **Design rule derived:** section guidance follows C-C-C at every scale. The abstract gives context, gap, approach, main result and meaning; each results paragraph opens with the claim it supports; the discussion says which gap was filled and where the interpretation stops. Among writing items of similar weight, the coach ranks title, abstract, Fig. 1 and the contribution list first.

### 3.3 Readability is falling, driven by jargon
- **Plavén-Sigray, Matheson, Schiffler & Thompson 2017**, "The readability of scientific texts is decreasing over time", *eLife* 6:e27725; https://doi.org/10.7554/eLife.27725 (read via PMC, https://pmc.ncbi.nlm.nih.gov/articles/PMC5584989/). `Verified: yes [full]`
  - 709,577 abstracts from 123 journals in 12 fields, 1881-2015. Yearly mean Flesch Reading Ease fell with year (r = -0.93). The share of abstracts scoring below 0 rose from 14% in 1960 to 22% in 2015.
  - General scientific jargon (a 2,138-word list) rose with year (r = 0.96), as did syllables per word and the share of difficult words.
  - The study does not test a link to citations; its concern for reproducibility is argued, not measured.
  - **Design rule derived:** the playbook targets the measured cause (jargon and undefined terms), not a readability score: define each technical term at first use, prefer the plain word when it means the same, and do not use readability formulas as a revision target.

### 3.4 Writing style and citations: two correlational studies that disagree
- **Freeling, Doubleday & Connell 2019**, "Opinion: How can we boost the impact of publications? Try better writing", *PNAS* 116(2):341-343; https://doi.org/10.1073/pnas.1819937116 (PMC: https://pmc.ncbi.nlm.nih.gov/articles/PMC6329950/). `Verified: yes [full]`
  - 130 abstracts from 2012-2013 in three fields, sampled by citation band (100-1000 citations vs fewer than 100) and scored on 11 components such as setting, first-person narration, conjunctions, signposts, consistent language, parallel phrasing, hedging, acronyms and noun chunks.
  - Highly cited abstracts "were short; used first-person narration; placed findings in context by providing a setting", used consistent terminology and "avoided excessive acronyms and awkward noun chunks". But "there is no single formula for writing better", and the authors call the results "preliminary". The main text gives no effect sizes.
- **Weinberger, Evans & Allesina 2015**, "Ten Simple (Empirical) Rules for Writing Science", *PLoS Comput Biol* 11(4):e1004205; https://doi.org/10.1371/journal.pcbi.1004205. `Verified: yes [full]`
  - More than one million abstracts from eight disciplines over 17 years. Most common advice was not supported by citation counts: shorter abstracts were cited less ("Keep It Short" contradicted), while "Signal Novelty and Importance" and "Be Bold" (superlatives) went with more citations. The authors suggest retrievability by search engines as one explanation.
- *Inference:* both studies are correlational, they disagree on length, and neither measures reviewer judgement. For review, the CV corpus points the other way on boldness: overclaiming is one of three weakness codes that separate reject-side from accept-side reviews (OVER 42% vs 19%, `real_review_patterns.md` §2).
- **Design rule derived:** the playbook keeps only low-risk, checkable features that agree with the structure literature (consistent terms, few acronyms, no stacked nouns, context before results). It does not import citation-correlated rhetoric (superlatives, novelty adjectives, a length target); claims are calibrated to evidence.

---

## 4. CV and ML paper-writing advice

### 4.1 Freeman: write for a reviewer in a hurry
- **Bill Freeman**, "How to write a good CVPR submission", slides, MIT CSAIL, 6 Nov 2014; listed on the author's talks page https://billf.mit.edu/talks/ as https://billf.mit.edu/wp-content/uploads/2014/02/cvprPapers.pdf. `Verified: yes [full]` (also read through a mirror for `reviewer_behavior_literature.md` §2.2)
  - "It should be easy to read the paper in a big hurry and still learn the main points." Captions should be self-contained, and "the caption should tell the reader what to notice about the figure."
  - Quoting Kajiya: "The most dangerous mistake you can make when writing your paper is assuming that the reviewer will understand the point of your paper." Make clear "what is really new in your paper (and what isn't)".
  - Adelson's order: the problem and why readers should care; other solutions and why they fall short; your solution, compared with them; related work on other problems at the end.
  - Rewriting exercise: "The underlying assumption of this work is that the estimate of a given node will only depend on nodes within a patch" becomes "We assume local influence--that nodes only depend on other nodes within a patch."
  - "Quick and easy reasons to reject a paper": "Do the authors promise more than they deliver?", missing important references, main idea done before, incremental, results not believable, poorly written, incorrect statements. The borderline "Puppy with 6 toes" has "some easy-to-point-to flaw" that "makes it easy to kill the paper".
  - On endings and honesty: "You get no 'partial credit' from reviewers and readers for neat things you wanted to do, but didn't." "Promise only what you deliver." "There are perceived pressures to over-sell, hide drawbacks, and disparage others' work. Don't succumb." "Good writing is re-writing."
  - **Design rule derived:** the coach ranks first the items that remove an easy-to-point-to reason to reject (an overclaim, a missing key comparison, an incorrect statement), even when the fix is small. Proposed text follows the rewrite pattern above: shorter, active, the claim stated directly. A future-work list is never the fix for a missing result.

### 4.2 Durand: motivate, prioritize, show evidence
- **Frédo Durand**, "Notes on writing", MIT CSAIL (undated; "a document in progress"); https://people.csail.mit.edu/fredo/PUBLI/writing.pdf. `Verified: yes [full]`
  - "Assume reviewers/readers don't know much." "Make clear what's new, what's different about your technique." "Don't introduce two ideas in one sentence."
  - Summarize contributions at the end of the introduction because "it helps reviewers identify and praise your contributions"; "contribution summary is different from method summary".
  - Related work: "Avoid laundry list, compare, organize"; instead of listing other methods' flaws, "say how you improve them".
  - Method: "Justify choices and technical points"; say which choices are essential and which are arbitrary; an overview "is about providing a high-level view of the technique, not a table of content".
  - Results: "If you claim you do something better than brand X, the expectation is that you will have a figure or numbers showing that this is the case." Ablate: "Show just with component #1 of your approach, just with #2 and with both".
  - "Make sure that one can get the full story just by looking at the figures and their captions." Keep a glossary to "unambiguously define terms and to be precise and consistent."
  - **Design rule derived:** method guidance asks for the reason before the mechanism ("we need X because Y"), an explicit split between essential and incidental design choices, and one name per concept across text, figures and tables. A "better than" claim with no figure or number pointer is an overclaim item.

### 4.3 Peyton Jones: one idea, refutable contributions, listen to readers
- **Simon Peyton Jones**, "How to write a great research paper", talk and slides, Microsoft Research; https://www.microsoft.com/en-us/research/academic-program/write-great-research-paper/ (slides https://www.microsoft.com/en-us/research/wp-content/uploads/2016/07/How-to-write-a-great-research-paper.pdf). `Verified: yes [full]` (slides)
  - Seven suggestions: "Don't wait: write", "Identify your key idea", "Tell a story", "Nail your contributions", "Related work: later", "Put your readers first (examples)", "Listen to your readers".
  - "Your paper should have just one 'ping': one clear, sharp idea." Contributions "should be refutable": "Check each claim in the introduction, identify the evidence, and forward-reference it from the claim."
  - "Introduce the problem, and your idea, using EXAMPLES and only then present the general case." "Conveying the intuition is primary, not secondary".
  - "Giving credit to others does not diminish the credit you get from your paper." "Acknowledge weaknesses in your approach."
  - On reviews: "Read every criticism as a positive suggestion for something you could explain more clearly"; instead of replying "I meant X", "fix the paper so that X is apparent". From readers, "'I got lost here' is much more important than 'Jarva is mis-spelt'."
  - **Design rule derived:** a misreading the paper invites is a writing item. The coach proposes text that makes the intended reading unmissable where the reviewer looked, instead of arguing that the reviewer was wrong. Contribution bullets in proposed text are refutable claims with a section, table or figure pointer. "Got lost here" items outrank typo items.

### 4.4 Huang: no correspondence problems, positioned related work
- **Jia-Bin Huang**, writing tips in the awesome-tips repository; https://github.com/jbhuang0604/awesome-tips (pages read: https://github.com/jbhuang0604/awesome-tips/blob/main/paper-writing.md and https://github.com/jbhuang0604/awesome-tips/blob/main/related-work.md). `Verified: yes [page]` for these two pages. The X/Twitter threads the repository links to (introduction, overview figure, tables, math) were not opened: `Verified: no`, not used.
  - "Do NOT ask people to solve correspondence problems." "Give specific, meaningful names to your math notations." Use "self-contained" captions; "each table conveys exactly one thing."
  - Related work: "Connect existing work into a clear research trajectory"; "In each topic, articulate the relationship between prior work and yours"; "Try finding ONE key contrastive concept to separate your work from others"; "Do not trash prior work."
  - **Design rule derived:** related-work items are about positioning, not coverage: organize by topic, end each topic with how this paper differs, and name one key contrast. Notation and figure references let a reader match symbols, figure parts and text without searching.

### 4.5 Lipton & Steinhardt: speculation, sources of gains, mathiness, language
- **Lipton & Steinhardt 2018**, "Troubling Trends in Machine Learning Scholarship", ICML 2018 Machine Learning Debates workshop; https://arxiv.org/abs/1807.03341 (read via https://ar5iv.labs.arxiv.org/html/1807.03341). `Verified: yes [full]`
  - Four trends: failure to distinguish explanation from speculation ("speculation in the guise of explanations"); failure to identify the sources of empirical gains ("authors propose many tweaks absent proper ablation studies, obscuring the source of empirical gains"); mathiness ("Spurious theorems are common culprits"); misuse of language (suggestive definitions, overloaded technical terms, "suitcase words").
  - Authors should ask "what worked?" and "why?", not only "how well?", and use "error analysis, ablation studies, and robustness checks". A test for an explanation: "Would I rely on this explanation for making predictions or for getting a system to work?"
  - **Design rule derived:** the playbook asks authors to label speculation ("we hypothesize"), tie each claimed mechanism to an ablation or analysis, use each technical term in one precise sense, and keep equations the method needs rather than ones that only signal depth. The coach turns an unsupported explanatory claim into a `writing` item (narrow the claim) or an `existing_evidence` item (point to the ablation).

### 4.6 Venue author guidance on claims and limitations
- **NeurIPS Paper Checklist** (2026 page); https://neurips.cc/public/guides/PaperChecklist. `Verified: yes [page]`
  - Claims: "The paper's contributions should be clearly stated in the abstract and introduction." Aspirational goals are acceptable "as motivation" if it is clear "these goals are not attained by the paper".
  - Limitations: "Reviewers will be specifically instructed to not penalize honesty concerning limitations." Authors "should point out any strong assumptions and how robust the results are to violations of these assumptions" and "should reflect on the scope of the claims made".
  - Error bars: "It should be clear whether the error bar is the standard deviation or the standard error of the mean."
- **CVPR 2026 Author Guidelines**; https://cvpr.thecvf.com/Conferences/2026/AuthorGuidelines. `Verified: yes [page]`
  - "Papers are limited to eight pages, including figures and tables, in the CVPR style." The rebuttal is one page; "Authors should refrain from including new contributions or experimental results in the rebuttal", and reviewers "should refrain from requesting significant additional experiments for the rebuttal".
  - "Failing to cite an arXiv paper or failing to beat its performance SHOULD NOT be the sole grounds for rejection."
- **Design rule derived:** an experiment the authors cannot run gets honest limitation wording instead (`if_not_possible`), scoped to the claim it affects. Proposed text fits the page budget. A request to compare with recent arXiv-only work ranks low unless that work is the closest prior method.

---

## 5. LLM-generated feedback: what it is good for and where it fails

### 5.1 GPT-4 feedback on research papers
- **Liang, Zhang, Cao, Wang, Ding, Yang, Vodrahalli, He, Smith, Yin, McFarland & Zou 2024**, "Can Large Language Models Provide Useful Feedback on Research Papers? A Large-Scale Empirical Analysis", *NEJM AI* 1(8); https://doi.org/10.1056/AIoa2400196 (preprint https://arxiv.org/abs/2310.01783, read via ar5iv). `Verified: yes [full]` (preprint; journal volume and DOI from the publication record)
  - Overlap with individual human reviewers: GPT-4 30.85% (Nature family journals, 3,096 papers) and 39.23% (ICLR, 1,709 papers), against human-human 28.58% and 35.25%. Paired with a different paper's feedback, overlap fell below 4%. Overlap was higher for weaker papers (rejected ICLR papers about 44-47%, orals about 24-31%).
  - Aspect bias: GPT-4 commented on implications 7.27 times more often than humans and on novelty 10.69 times less often; humans asked for ablations 6.71 times more often; GPT-4 asked for more datasets 2.19 times more often.
  - User study with 308 researchers: 57.4% found the feedback helpful or very helpful; 82.4% found it more beneficial than at least some human reviewers; 50.5% would use it again.
  - Limits stated by the authors: GPT-4 "often struggles to provide in-depth critique of method design"; the feedback sometimes "feels 'generic' to the authors"; "the current LLM feedback cannot substitute specific and thoughtful human feedback by domain experts". The pipeline did not read figures or tables.
  - **Design rule derived:** the coach's value is merging, ranking and drafting, not judging the science. It adds no criticisms of its own; every item traces to review ids (`from`). Novelty and ablation points, which LLMs under-produce, must survive merging. The plan ends with "Generated from simulated reviews; verify every suggestion against your own evidence."

### 5.2 LLM reviews are less specific and accept the paper's claims
- **Du, Wang, Zhao, et al. 2024** (ReviewCritique), "LLMs Assist NLP Researchers: Critique Paper (Meta-)Reviewing", EMNLP 2024; https://arxiv.org/abs/2406.16253 (read https://arxiv.org/html/2406.16253v3). `Verified: yes [full]`
  - Experts labelled review segments as deficient or not. Every LLM-generated review (100%) had at least one deficient segment, against 71.57% of human reviews; at segment level, 13.97% against 6.27%.
  - The largest LLM deficiency type was out-of-scope requests (30.49% of deficient LLM segments, 4.35% for humans). The authors call LLM reviews often "paper-unspecific and superficial".
  - 53.2% of LLM strength segments were rephrased from the submission, and experts questioned 34.5% (accepted papers) and 51.9% (rejected papers) of them: "LLMs often accept authors' claims without thorough verification." LLMs praised the writing in every review, although 15% of the papers were judged unclear by human reviewers and meta-reviewers.
  - Specificity (ITF-IDF, higher is more paper-specific): humans 6.04, Claude Opus 4.09, Gemini 3.82, GPT-4 3.34. LLM reviews of different papers resembled each other more (BERTScore about 70-71) than human reviews did (59.15).
  - As meta-reviewers, the best LLM setup found deficient segments with F1 21.99, and recall exceeded precision (over-flagging).
  - **Design rule derived:** strengths to keep are ones the reviewers named and the paper supports, with a location; restating the abstract's claims is not a strength. Each item names something only this paper has (a passage, a number, a figure). Deferrals are conservative and carry a quoted reason, because LLM judgements of which review points are deficient are weak.

### 5.3 LLM edits written from reviewer comments
- **D'Arcy, Ross, Bransom, Kuehl, Bragg, Hope & Downey 2024**, "ARIES: A Corpus of Scientific Paper Edits Made in Response to Peer Reviews", ACL 2024; https://arxiv.org/abs/2306.12587 (read https://arxiv.org/html/2306.12587v2). `Verified: yes [full]`
  - Real OpenReview comment-edit pairs from computer science (test set: 42 papers, 196 comments, 131 aligned edits). Matching comments to the edits that answer them: best model 27.0 micro-F1, human expert 70.7.
  - GPT-4 edits written from a comment, against the authors' real edits: highly compliant 94% vs 68%; reused the comment's wording 48% vs 4%; promised future work or information 21% vs 6%; included technical details 38% vs 53%. When the comment needed data not in the paper, real edits were judged more comprehensive 40% vs 19%. GPT-4 "almost never makes edits that suggest the feedback is mistaken."
  - **Design rule derived:** proposed text does not paraphrase the reviewer or promise future work; it states concrete technical content from the paper (setting, number, condition, pointer). Because the model defaults to compliance, the coach must decide whether each point is correct before planning an edit.

### 5.4 LLM feedback that makes reviews specific
- **Thakkar, Yuksekgonul, Silberg, Garg, Peng, Sha, Yu, Vondrick & Zou 2025**, "Can LLM feedback enhance review quality? A randomized study of 20K reviews at ICLR 2025", arXiv; https://arxiv.org/abs/2504.09737. `Verified: yes [full]`
  - 18,946 ICLR 2025 reviews received LLM feedback on the review itself. 26.6% of them were updated, against 9.4% of controls; 12,222 suggestions were incorporated. Updated reviews grew by 80.3 words on average. In a blinded comparison of 100 updated reviews (a selected subset), two researchers preferred the revised version 89% of the time.
  - Nearly half of all feedback asked reviewers to "clarify methodological concerns to make their request specific and actionable". Author rebuttals in the feedback group were about 6% longer; acceptance rates did not differ significantly (32.3% vs 30.8%).
  - **Design rule derived:** turning a vague concern into a specific, actionable request is the kind of LLM feedback with randomized evidence behind it. It is the coach's core job: restate each review point as a concrete problem with a location and a check.

### 5.5 LLM feedback on student writing: quality and effect on revision
- **Steiss, Tate, Graham, Cruz, Hebert, Wang, Moon, Tseng, Warschauer & Olson 2024**, "Comparing the quality of human and ChatGPT feedback of students' writing", *Learning and Instruction* 91:101894; https://doi.org/10.1016/j.learninstruc.2024.101894 (read the author manuscript, https://par.nsf.gov/servlets/purl/10524947). `Verified: yes [full]` (manuscript; volume and article number from the DOI record)
  - 200 human and 200 ChatGPT (3.5) feedback texts on the same history essays (grades 6-12), rated 1-5 on five criteria. Humans scored higher on four: prioritization of essential features 3.92 vs 3.09 (d = 0.82, the largest gap), accuracy 4.55 vs 4.0 (d = 0.61), clear directions for improvement 3.65 vs 3.27 (d = 0.41), supportive tone 4.28 vs 4.02 (d = 0.32). ChatGPT scored higher on criteria-based feedback, 3.64 vs 3.40.
  - The authors define the criterion this way: effective feedback "prioritizes essential features of writing that are attainable and reasonable for a student to focus on next".
- **Meyer, Jansen, Schiller, Liebenow, Steinbach, Horbach & Fleckenstein 2024**, "Using LLMs to bring evidence-based feedback into the classroom: AI-generated feedback increases secondary students' text revision, motivation, and positive emotions", *Computers and Education: Artificial Intelligence* 6:100199; https://doi.org/10.1016/j.caeai.2023.100199 (institute landing page https://leibniz-ipn.de/en/research/publications/using-llms-to-bring-evidence-based-feedback-into-the-classroom-ai-generated-feedback-increases-secondary-students-text-revision-motivation-and-positive-emotions). `Verified: yes [abs]`
  - Randomized study with 459 upper-secondary students of English as a foreign language: revising with GPT-3.5 feedback against revising without feedback. Revision performance d = 0.19, task motivation d = 0.36, positive emotions d = 0.34.
- *Inference:* school essays are not research papers, but the largest gaps fall on the parts of the coach's job that matter most: choosing what to fix first and being correct.
- **Design rule derived:** prioritization and accuracy get explicit structure: a cap on items, a forced top 3-5, and a `from` trace so every item can be checked against the reviews. LLM feedback improves revisions only modestly, so the plan is presented as a draft for the authors, not as a verdict.

---

## 6. Not used, or read through another route
- Jia-Bin Huang's X/Twitter threads indexed in awesome-tips: not opened (`Verified: no`). Not used.
- Publisher pages that refused access: SAGE (Hattie & Timperley; Shute), PeerJ (Silbiger & Stubler), American Scientist (Gopen & Swan). The full texts were read through the hosted copies named in each entry.
- Kluger & DeNisi 1996 and Meyer et al. 2024 were read at abstract level only. The rules that cite them are also supported by full-text sources (Hattie & Timperley; Shute; Steiss et al.).

---

## 7. Rules the harness implements, and where

"(new)" marks files added by the coach change set (`02_protocol/coach_rules.md`, `02_protocol/writing_playbook.md`, `05_templates/revision_plan_schema.md`); they may not exist at the commit that adds this note. `02_protocol/writer_rules.md` exists; the coach change set adds a pointer from it to the playbook.

1. **Feed up, feed back, feed forward in every item.** The summary says where the paper stands; each item gives the problem (gap), why it matters to reviewers (target), the action and proposed text (next step), and how to check the fix. Evidence: 1.1; 1.3 ("Reduce uncertainty between performance and goals"); 2.3 (NeurIPS "clear criteria"). Where: `coach_rules.md` (new), `revision_plan_schema.md` (new; `summary`, `problem`, `why_it_matters`, `action`, `proposed_text`, `verification`).
2. **About the paper, never the authors; no scores or grades.** Evidence: 1.1 (self-level feedback least effective; praise 0.14); 1.2 (over a third of feedback interventions lowered performance); 1.3 (grades next to comments cancel the comments). Where: `coach_rules.md` (new; tone and the REVISION_PLAN format without scores).
3. **Few, merged, prioritized items.** At most about 12 items, 3-5 marked most important; duplicates across reviewers merged into one item that lists every source id. Evidence: 1.3 ("manageable units"; "as simple as possible but no simpler"); 1.1 (too much feedback can detract); 5.5 (prioritization is where LLM feedback trails humans most, d = 0.82). Where: `coach_rules.md` (new), `revision_plan_schema.md` (new; unique `priority`, item count).
4. **Rank by effect on reviewer decisions.** Novelty framing, overclaiming and small-gain framing first; clarity, baselines and ablations are frequent but rarely decisive; easy-to-point-to flaws before cosmetic ones. Evidence: `real_review_patterns.md` §2 (NOV, OVER, MARG separate reject from accept); 4.1 (quick reasons to reject; the "Puppy with 6 toes"); 2.3 (ICLR: decision points vs help). Where: `coach_rules.md` (new; ranking), `revision_plan_schema.md` (new; `why_it_matters`, `priority`, `effort`).
5. **Keep strengths, grounded in reviews and the paper.** Strengths come from reviewer strength ids and a paper location, never from the paper's own claims restated. Evidence: 1.3 (note strengths with how to improve); 2.3 (CVPR "Look for what is good"); 5.2 (53.2% of LLM strengths rephrase the submission). Where: `coach_rules.md` (new), `revision_plan_schema.md` (new; `strengths_to_keep` with `location` and `from`).
6. **Specific and located.** Every item names a location and a problem that would not fit another paper; no generic advice. Evidence: 1.4 (high-information feedback d = 0.99 vs 0.24 for reinforcement); 2.3 (CVPR "point it out and give suggestions"; NeurIPS "Do not make vague statements"); 5.1 (generic feedback); 5.2 (specificity 3.3-4.1 for LLMs vs 6.04 for humans); 5.4. Where: `coach_rules.md` (new), `revision_plan_schema.md` (new; non-empty `location` and `problem`).
7. **Proposed text for every writing item: in the paper's voice and page budget, not echoing the reviewer, no promises.** Evidence: 5.3 (GPT-4 edits reuse the comment's wording 48% vs 4%, promise future work 21% vs 6%, include technical details 38% vs 53%); 4.1 (rewrite pattern; no "partial credit"); 4.6 (page limits). Where: `coach_rules.md` (new), `revision_plan_schema.md` (new; `proposed_text` required for `writing`), `writer_rules.md` (pointer to the playbook).
8. **No invented results, numbers or citations.** Proposed text uses only facts in the paper or the project's evidence; a missing number is a marked placeholder for the authors, and the item becomes `existing_evidence` or `new_experiment`. Evidence: 5.3 (real edits beat GPT-4 when new data is needed, 40% vs 19%); 5.5 (accuracy gap, d = 0.61); 4.5 (speculation vs explanation). Where: `coach_rules.md` (new), `writer_rules.md` (hard rule 1, existing).
9. **Experiment requests get a minimum version and honest fallback wording.** Evidence: 2.3 (ICLR: experiments "limited in scope"); 4.6 (NeurIPS: honesty about limitations not penalized; CVPR: no new results in the rebuttal); 4.1 ("Promise only what you deliver"). Where: `revision_plan_schema.md` (new; `experiment_requests[].minimum_version`, `if_not_possible`), `coach_rules.md` (new), `writing_playbook.md` (new; limitations).
10. **Fix misreadings in the text; do not argue.** When the paper invites a misreading, the item rewrites the passage where the reviewer looked (earlier, plainer, in the caption or abstract). Evidence: 4.3 ("fix the paper so that X is apparent"); 4.1 (Kajiya: never assume the reviewer will understand); 1.1 (feedback works best on faulty interpretations). Where: `coach_rules.md` (new), `writer_rules.md` (`contest` decision, existing).
11. **Defer wrong, lazy or out-of-scope points with a quoted reason, conservatively.** Evidence: 2.2 (41% of comment sets contain incomplete, inaccurate or unsubstantiated critiques); 5.2 (LLM out-of-scope requests; F1 about 22 at spotting deficient review segments); 5.3 (LLMs rarely say feedback is mistaken); 2.1 (remarks about the authors). Where: `coach_rules.md` (new), `revision_plan_schema.md` (new; `deferred[].reason`).
12. **Resolve reviewer conflicts explicitly.** Say which reviewer to satisfy and why, or how to satisfy both (for example, detail moved to the supplement with a one-line pointer). Evidence: 2.3 (decision points vs help); `writer_rules.md` Priorities item 4; `reviewer_behavior_literature.md` §1.2 (independent panels disagree on 23-26% of decisions). Where: `revision_plan_schema.md` (new; `conflicts[].advice`), `coach_rules.md` (new).
13. **Constructive, plain tone, whatever the reviews' tone.** No persona voice, no sarcasm, no blame. Evidence: 2.1 (58% received unprofessional reviews, with harm concentrated in some groups); 2.2 (12% of comment sets unprofessional); 2.3 (CVPR: harsh reviews are resented "regardless of whether your criticisms are true"); 1.3 (do not discourage); 5.5 (supportive tone). Where: `coach_rules.md` (new; tone and REVISION_PLAN format).
14. **The coach drafts; the authors decide.** No criticisms beyond the reviews; every item traces to review ids; the plan ends with the verification line. Evidence: 5.1 ("cannot substitute ... domain experts"); 5.5 (trained humans give better feedback; LLM feedback helps revisions modestly, d = 0.19); 5.2. Where: `coach_rules.md` (new), `revision_plan_schema.md` (new; `from` validation and coverage).
15. **Section structure for CV/ML papers.** One central contribution in title and abstract; an abstract with context, gap, approach, main result and meaning; an introduction with the problem, why it matters, why current approaches fall short, the key idea, and refutable contributions with forward pointers; a Fig. 1 that conveys the idea or result at a glance; related work by topic with one key contrast and no disparagement; a method with intuition or a toy example first, motivated choices, essential vs incidental choices marked, consistent notation; experiments where every claim has a table or figure pointer; ablations as evidence for the claimed mechanism; captions that say what to notice; honest limitations; a conclusion without a future-work wish list. Evidence: 3.2, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6; captions also `figure_research.md` §5 rule 8. Where: `writing_playbook.md` (new; section guidance).
16. **Sentence-level clarity from reader expectations.** Subject and verb close; old information first (topic position), the new claim or number last (stress position); one point per sentence and paragraph; action in the verb; context before new information; one term per concept; no readability-score or sentence-length target. Evidence: 3.1; 3.3; 3.4 (consistent language, few acronyms, no noun stacks); 4.2 (one idea per sentence; glossary); 4.5 (misuse of language). Where: `writing_playbook.md` (new; sentence-level section), `coach_rules.md` (new; proposed text follows it).
17. **Calibrated claims, not citation-style rhetoric.** No superlatives or novelty adjectives in place of evidence; speculation labelled; aspirational goals marked as not attained. Evidence: 3.4 (bold wording correlates with citations, but OVER separates reject from accept in CV reviews); 4.1 ("Promise only what you deliver"); 4.5; 4.6 (NeurIPS claims item). Where: `writing_playbook.md` (new; claims calibration), `writer_rules.md` (hard rule 2, existing).
18. **Front matter first among equals.** When two writing items carry similar decision weight, the one in the title, abstract, Fig. 1, contribution list or main table ranks higher, because every reviewer reads those and many read little else. Evidence: 3.2 ("viewed by far more people than the rest of the paper"); 4.1 ("read the paper in a big hurry"); `reviewer_behavior_literature.md` §2.3 (one-pass reading). Where: `coach_rules.md` (new; ranking tie-break).

Not used as evidence: Jia-Bin Huang's X/Twitter threads (`Verified: no`).
