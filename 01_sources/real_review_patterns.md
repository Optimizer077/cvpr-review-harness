# Real CV peer-review patterns: evidence corpus for simulated CVPR reviewers

Built 2026-10-13. Corpus: **184 real reviews of 46 computer-vision papers** from ICLR 2024/2025/2026 and NeurIPS 2024/2025, with 25 accepted and 21 rejected papers. Rebuttal threads are included for 144 of the reviews (36 papers).

Every number below is a count over these 184 reviews unless it is labelled **[estimate]** or **[supplementary scan]**. Percentages carry 95% Wilson intervals where the sample is small.

---

## 0. How this was built (read before using the numbers)

**Sources.** openreview.net and api2.openreview.net returned a bot challenge (HTTP 403), so all data comes from public HuggingFace mirrors of OpenReview. Raw files are in `01_sources/raw_reviews/`.

| Venue | Mirror | What it contains |
|---|---|---|
| ICLR 2024, ICLR 2025, NeurIPS 2024 | `Jasonpicky/openreview_raw` (6 parquet shards) | Full threads: reviews, author responses, reviewer follow-ups, AC decision (no decision note for ICLR 2025) |
| NeurIPS 2025 | `ulab-ai/ResearchArcade-openreview-reviews` + `-papers` | Full threads, including the reviewer `final_justification` field. Rejected papers are public only if the authors opted in. |
| ICLR 2026 | `JerMa88/ICLR_Peer_Reviews_2026` (reviews + decisions), `davidheineman/iclr-2026` (ratings snapshot of 2025-11-21), `3Liz22/iclr2026_real_reviews` (Pangram AI-text labels) | Reviews only. No rebuttal or discussion text is available. |
| CVPR/ICCV/ECCV | none found | One web search found no author-posted CVPR/ICCV/ECCV review dumps. |

**ICLR 2026 caveat (verified).** On 2025-11-27 an OpenReview API bug exposed reviewer identities. ICLR then reverted reviews and scores to their pre-discussion state and froze the discussion ([ICLR blog](https://blog.iclr.cc/iclr-2026-response-to-security-incident/), [retrospective](https://blog.iclr.cc/2026/03/31/a-retrospective-on-the)). The data matches this:
- Our 40 ICLR 2026 reviews: 0 rating changes between the 2025-11-21 snapshot and the final record.
- All 75,840 matched ICLR 2026 reviews: 625 changes (0.8%), of which 531 were down and 94 up. Most reviewers who had raised a score by Nov 21 were reverted.

ICLR 2026 is therefore used only for review text, scores and the AI-text analysis. It is not used for rebuttal dynamics.

**Selection.** Papers were picked by title keyword across four computer-vision subareas, preferring forums with an author response and a mix of decisions and score spreads. This is purposive, not random, so frequencies describe this corpus. NeurIPS rejected papers are opt-in, which biases them toward authors willing to publish their reviews.

**Coding.** Seven parallel annotation agents (LLM subagents) coded every review with a fixed codebook: `01_sources/raw_reviews/coding/CODEBOOK.txt`, 20 weakness codes, tone, reviewer type, rebuttal fields. Outputs are `coding/batch_*.json`, aggregated with machine checks.

| Check | Result |
|---|---|
| Coverage | 184/184 reviews coded, 0 duplicates |
| Quote verification | 524 coder quotes and 897 code-evidence snippets were matched as substrings of the raw notes (whitespace-normalised). 521 quotes match the review itself; 3 match the same reviewer's follow-up comment. 0 unverified. |
| Manual spot-check | I coded 7 reviews of two papers independently (4 + 3 reviews). The coders recovered 34/35 of my codes and added 6 more (Jaccard 0.83), so code frequencies may run about 10–15% high relative to a stricter coder **[estimate]**. |
| External check of the "LLM-sounding" flag (ICLR 2026, n=40) | All 8 reviews Pangram labels *Fully AI-generated* were flagged. 0 of 15 *Fully human-written* were flagged. 4 more flags fell on *Heavily* (2) or *Lightly* (2) AI-edited reviews. |

**Where the derived files are.**
- Review-level table: `01_sources/raw_reviews/review_table.csv`.
- Per-forum transcripts: `forums_txt/`, `forums_json/`.

---

## 1. Corpus

Summary:
- **46 papers / 184 reviews.**
- By venue: ICLR 2024 11/43, ICLR 2025 10/41, ICLR 2026 10/40, NeurIPS 2024 8/31, NeurIPS 2025 7/29.
- Four computer-vision subareas with 40–60 reviews each.
- Decisions: 25 accepted (3 oral, 2 spotlight, 20 poster) and 21 rejected.

**Rating scales.**
- ICLR 2024/25: 1/3/5/6/8/10, where 5 = marginally below and 6 = marginally above.
- ICLR 2026: 0/2/4/6/8/10.
- NeurIPS 2024: 1–10, where 4 = borderline reject and 5 = borderline accept.
- NeurIPS 2025: 1–6, where 3 = borderline reject and 4 = borderline accept.

*Final ratings: these are post-rebuttal for ICLR 2024/25 and NeurIPS 2024/25, and pre-rebuttal (reverted) for ICLR 2026.

The per-paper list (titles, forum ids, subareas, decisions and ratings) is withheld from this public copy. Quotes in §3 and cases in §6 keep their OpenReview forum ids.

**Rating distribution (counts):**

| Venue | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 10 |
|---|---|---|---|---|---|---|---|---|
| ICLR 2024 | 0 | 8 | 0 | 7 | 13 | 0 | 14 | 1 |
| ICLR 2025 | 0 | 4 | 0 | 10 | 20 | 0 | 7 | 0 |
| ICLR 2026 | 8 | 0 | 17 | 0 | 11 | 0 | 3 | 1 |
| NeurIPS 2024 | 0 | 0 | 0 | 12 | 11 | 6 | 2 | 0 |
| NeurIPS 2025 (1–6) | 4 | 11 | 8 | 5 | 1 | – | – | – |

**Reviewers disagree, and decisions do not follow the mean.**
- 17 of 21 rejected papers had at least one accept-side review.
- 9 of 25 accepted papers had at least one reject-side review.
- Within-paper rating spread, as max − min in raw points: 0 (6 papers), 1 (8), 2 (13), 3 (9), 4 (6), 5 (3), 6 (1).
- 19/25 accepted papers had at least one "clear accept" score (ICLR ≥8, NeurIPS 2024 ≥7, NeurIPS 2025 ≥5). Only 8/21 rejected papers had one.
- Examples of decisions against the mean:
  - One paper was accepted with 3/5/8/5/6.
  - Another was accepted with 3/4/5/3. The AC wrote that "one reviewer was willing to champion the paper, reviews are overall leaning positive".
  - Three papers with 6/6/6/5, 6/5/6/6 and 6/5/6/6/6 were all rejected at ICLR 2025.

---

## 2. Weakness taxonomy with frequencies (n = 184 reviews)

**How a code was counted.** A code counts once per review if the weaknesses, questions or limitations contain an explicit criticism or request of that type. Each coded instance carries a verbatim evidence snippet in `coding/batch_*.json`.

**Column definitions.**
- "Reject-side" means the reviewer's *final* rating is ICLR ≤5 (ICLR 2026 ≤4), NeurIPS 2024 ≤4 or NeurIPS 2025 ≤3. That gives n=69 reject-side and n=115 accept-side reviews.
- p is a Fisher exact test of reject-side vs accept-side frequency.

| Rank | Code | Weakness type | Reviews | % (95% CI) | Reject-side % | Accept-side % | p |
|---|---|---|---|---|---|---|---|
| 1 | CLAR | Unclear writing, notation or missing method/implementation details | 94 | **51.1** (44–58) | 43 | 56 | 0.13 |
| 2 | GEN | Limited generalization or scope: one task/domain, synthetic data only, unclear real-world use | 87 | **47.3** (40–54) | 52 | 44 | 0.36 |
| 3 | BASE | Missing baselines or comparisons to named methods | 77 | **41.8** (35–49) | 43 | 41 | 0.76 |
| 4 | NOV | Limited novelty, "combination of existing techniques", incremental | 72 | **39.1** (32–46) | **64** | **24** | <0.0001 |
| 5 | ABL | Missing or insufficient ablations; component contribution unclear | 62 | 33.7 (27–41) | 32 | 35 | 0.75 |
| 6 | THEO | Theory gaps: unjustified claims, loose derivations, "why does it work" | 57 | 31.0 (25–38) | 33 | 30 | 0.62 |
| 7 | EFF | No or insufficient efficiency analysis (wall-clock, FLOPs, memory, FPS) | 52 | 28.3 (22–35) | 28 | 29 | 1.0 |
| 8 | OVER | Overclaiming: claims, title or abstract stronger than the evidence | 51 | 27.7 (22–35) | **42** | **19** | 0.001 |
| 9 | BENCH | Small, old, few or synthetic benchmarks; asks for harder data | 45 | 24.5 (19–31) | 32 | 20 | 0.08 |
| 10 | RW | Missing related or concurrent work | 44 | 23.9 (18–31) | 22 | 25 | 0.72 |
| 11 | FAIR | Unfair comparison: budgets, tuning, training data, GPUs, iterations | 40 | 21.7 (16–28) | 25 | 20 | 0.47 |
| 12 | VIS | Insufficient or unconvincing visual results; artifacts; hallucinated detail | 37 | 20.1 (15–26) | 19 | 21 | 0.85 |
| 13 | METRIC | Questionable metrics or protocol (PSNR-only, no LPIPS/user study, overfitting-only eval, convergence) | 31 | 16.8 (12–23) | 17 | 17 | 1.0 |
| 14 | MOT | Unclear motivation or practical need | 31 | 16.8 (12–23) | 23 | 13 | 0.10 |
| 15 | HYP | Hyperparameter sensitivity or robustness not analysed | 30 | 16.3 (12–22) | 14 | 17 | 0.68 |
| 16 | FIG | Figure/table presentation quality | 24 | 13.0 (9–19) | 12 | 14 | 0.82 |
| 17 | LIM | Limitations or failure cases not discussed | 23 | 12.5 (8–18) | 12 | 13 | 0.82 |
| 18 | MARG | Improvement margins too small | 22 | 12.0 (8–17) | **23** | **5** | 0.0006 |
| 19 | REPRO | Reproducibility or code availability | 14 | 7.6 (5–12) | 12 | 5 | 0.15 |
| 20 | VAR | No variance, seeds or significance tests | 4 | **2.2** (1–5) | 3 | 2 | 0.63 |

**What the table says**

1. **Most criticism does not separate rejecters from accepters.** Only 3 codes differ significantly between reject-side and accept-side reviews:
   - NOV: 64% vs 24%.
   - OVER: 42% vs 19%.
   - MARG: 23% vs 5%.

   Clarity, baselines, ablations, efficiency and scope are raised at about the same rate by reviewers who end up accepting. A simulated reviewer should list these weaknesses *and still score 6/8*. A low score should be driven by novelty, overclaiming or small gains.
2. **Clarity is the most common complaint, and it is more common on the accept side (56% vs 43%).** Positive reviewers fill their weakness list with presentation points.
3. **Seeds and variance are almost never requested (4/184 = 2.2%).** Two of the four requests came on one paper. CV reviewers ask for more datasets, baselines and visual comparisons, not error bars. When it is raised, it is phrased as "statistical significance" or "confidence intervals", not as "seeds".
4. **Efficiency is requested in 28% of reviews.** The request is usually for *wall-clock or inference time in addition to FLOPs/params* (see EFF quotes in §3).
5. **Codes per review:** mean 4.9, median 5, IQR 3–6, max 15. Length predicts code count (Spearman ρ=0.54 between word count and code count).

### Which baselines reviewers name (70/184 reviews name at least one)

Names are almost never repeated across papers: the most frequent single name appears in 4 reviews. Reviewers ask for **the most recent same-family method, or the method the submission is built on**.

### By venue (% of that venue's reviews)

| Code | ICLR 2024 (43) | ICLR 2025 (41) | ICLR 2026 (40) | NeurIPS 2024 (31) | NeurIPS 2025 (29) |
|---|---|---|---|---|---|
| NOV | 23 | 44 | 38 | 42 | 55 |
| BASE | 37 | 46 | 35 | 52 | 41 |
| CLAR | 53 | 56 | 45 | 61 | 38 |
| GEN | 35 | 56 | 42 | 48 | 59 |
| ABL | 33 | 32 | 30 | 48 | 28 |
| THEO | 21 | 34 | 38 | 39 | 24 |
| EFF | 23 | 27 | 28 | 39 | 28 |
| OVER | 23 | 32 | 32 | 19 | 31 |
| BENCH | 23 | 44 | 20 | 6 | 24 |
| FAIR | 14 | 32 | 15 | 29 | 21 |
| MARG | 7 | 7 | 20 | 10 | 17 |
| VIS | 21 | 15 | 12 | 29 | 28 |

NOV rises from 23% in ICLR 2024 to 55% in NeurIPS 2025 in this sample. With 29–43 reviews per venue this is a hint, not a trend claim.

---

## 3. Verbatim phrase bank

All quotes are copied exactly from the raw OpenReview text. They were machine-checked as substrings of the forum and are at most 30 words. Typos are the reviewers' own.

**Format:** `[tone] "quote" — forum (venue, reviewer suffix)`. Tone codes: [D] dismissive, [C] constructive, [H] hedged, [E] enthusiastic. [AC] marks an area-chair or decision text. ⚑ marks a review that Pangram labels *Fully AI-generated* (ICLR 2026) or that our coder flagged as LLM-sounding.

### 3.1 By weakness type

**Limited novelty / "combination of existing techniques" (NOV)**
- [C] "The proposed AdaIR appears to be a straightforward combination of existing techniques, such as Restormer [3] and CBAM [4]." — `M5t0WvjfCg` (ICLR25, FFqs)
- [D] "making this work seem more like a combination of existing methods (A+B stitching) rather than presenting original contributions or theoretical derivations." — `NU3tE3lIqf` (NeurIPS24, nPTW)
- [D] "The paper is a direct combination of these previous works (pose-free feed-forward NVS from sparse-views + feed-forward 3DGS prediction)." — `P4o9akekdf` (ICLR25, tg6H; this reviewer later raised to 8)
- [D] "The novelty of this work is very limited. I cannot see the technique novelty." — `AQqOC3FKPO` (ICLR25, 224k)
- [D] "The tree-path KL loss is trivial." — `7HEMpBTb3R` (ICLR25, khL4)
- [D] "Direct extension of Bökman et al. (2025) from D2 to D8" — `9zVPsVWUY1` (ICLR26, PPBJ ⚑)
- [D] "Main issue: This paper is more of a position, benchmarking, tutorial, and/or a survey paper" — `OZljvntsto` (NeurIPS25, xxwx)
- [D] "The proposed method is overly simplistic, as it merely concatenates the low-quality image to the input of FLUX and applies LoRA for fine-tuning, without any technical innovation." — `9D5ryI7now` (ICLR26, zDzX)
- [D] "offers no new fundamental principles for representation learning, which is the focus of ICLR." — `9D5ryI7now` (ICLR26, uxXd)
- [C] "The core concept of this paper shares similarities with "One-step Diffusion with Distribution Matching Distillation"." — `TPtXnpRvur` (NeurIPS24, KDhM)
- [H] "Nevertheless, I would also admit that these novelty issues are not critical as each of them is not trivial in the task." — `DS5qRs0tQz` (ICLR24, sRML)
- [H] "the methodological contribution may be seen as incremental rather than innovative." — `RKOgWtrWPe` (NeurIPS25, zhcb)

**Missing baselines (BASE)**
- [C] "I find the use of FFN (Tancik, 2020) as the only baseline in the image task disappointing." — `4UiLqimGm5` (ICLR24, DCsj)
- [C] "In particular, DVGO was explicitly designed to address this same issue of capturing sharp boundaries in 3D, so this method should also be compared against." — `jWxrIeWgir` (ICLR24, VTh6)
- [D] "All the competing baselines in Section 4.2 are not SOTA methods any more, as they were published at least 3 years ago." — `OKOjkFrhSs` (ICLR24, WtP4)
- [D] "As a submission to ICLR, it's not reasonable to only include 3DGS and Mip-Splatting for comparison." — `R9lgWYE508` (ICLR25, gqEX)
- [C] "The architecture is mainly based on Restormer. However, Tab. 1 does not include Restormer's performance." — `M5t0WvjfCg` (ICLR25, K6x2)
- [C] "why do you take 3DGS-accel as the baseline instead of the latest SOTA DashGaussian?" — `5PXMoN8e2W` (ICLR26, 1HVJ)
- [C] "We are not looking for state of the art here, but to have an idea of whether the proposed setup is close or far from that." — `uZfjFyPAvn` (ICLR24, ksCd)
- [D] "comparison with Finite-Difference (which is already built-in inside Instant NGP) and AD is like a typical strawman approach" — `HxHrRUHMOD` (ICLR24, DXqV)

**Small / old benchmarks (BENCH)**
- [C] "It is hard to gain generalizable insights from five toy images on a single task." — `muN3B40keb` (ICLR25, r32t)
- [C] "I am very surprised there are no NeRF results as this a big experiment that requires hours to train" — `Sr5XaZzirA` (ICLR25, jBfM)
- [D] "Finally, the experimental section of the work is severely lacking." — `uZfjFyPAvn` (ICLR24, 3UQT)

**Efficiency / wall-clock (EFF)**
- [C] "In addition to FLOPs, there should also be comparison between inference time of different models." — `M5t0WvjfCg` (ICLR25, Jdae)
- [C] "Lastly, the FLOPs seems to decrease but the wall clock time is higher for all variants." — `9zVPsVWUY1` (ICLR26, 5pGM)
- [C] "total parameters instead of the training parameters are expected to be compared in the Table 2, which is more closely related to the deployment." — `TPtXnpRvur` (NeurIPS24, 4vqL)
- [C] "Missing bits of context information - How much does it cost?" — `UyNXMqnN3c` (ICLR24, E7Ru)

**Unfair comparison / tuning (FAIR)**
- [C] "Otherwise, we cannot tell whether the performance gain comes from better model design or using larger and high-quality data" — `P4o9akekdf` (ICLR25, tg6H)
- [C] "The choice of number of training iterations to report performance is arbitrary and could reflect unfairly on the baselines." — `Sr5XaZzirA` (ICLR25, 3nXe)
- [C] "In table 4, the runtime for some baselines are evaluated with different GPU models." — `4voMNlRWI7` (ICLR26, uR7S)
- [H] "The numbers of the baseline models seem to be from the authors' own implementation, which makes it less appealing" — `4UiLqimGm5` (ICLR24, kCkz)
- [D] "Clearly, there is an unfair comparison in your experiments." — `NU3tE3lIqf` (NeurIPS24, BAXf)

**Missing ablations (ABL)**
- [C] "I suggest to add the missing ablations to better understand how much improvement each contribution brings separately" — `4voMNlRWI7` (ICLR26, uR7S)
- [C] "It’s unclear how much improvement comes from the GAN refinement versus the soft-embedding relaxation itself." — `83pHDDmkXt` (ICLR26, jPZF)
- [C] "Moreover, the ablation study in Figure 6 only provides a single example, which weakens the overall argument." — `84Hk01tFKq` (ICLR24, VyWD)
- [C] "The ablations in table 6 and 7 do not show strong contribution of individual modeling choices except tight fusion. The authors dont explain this" — `DS5qRs0tQz` (ICLR24, jXst)

**Clarity / writing (CLAR)**
- [D] "Concretely, the paper looks and reads like a draft that is 80-90% complete." — `0Lqyut1y7M` (ICLR24, REJk)
- [C] "The Prompt Guided DCM module section is just 6 lines long, where it is one of the two claims of this paper!" — `OKOjkFrhSs` (ICLR24, axMK)
- [C] "Are the proposed frequency multipliers applied only to the first layer, or to all hidden layers? This is not clearly specified in the paper." — `ZXJ74KEVUu` (ICLR26, zW1b)
- [H] "As someone whose primary area of research or background is not in classical signal processing, I found the paper quite confusing." — `uZfjFyPAvn` (ICLR24, 3UQT)
- [C] "the work reads more like a paper written for a computer vision conference without providing sufficient background to a broader audience at the ICLR community." — `UyNXMqnN3c` (ICLR24, L9mE)
- [C] "Why not be clear and up front that the architecture is essentially just a transformer?" — `LDkyhsiCZQ` (NeurIPS25, avfu)

**Overclaiming (OVER)**
- [D] "The paper's core flaw is over-packaging." — `9D5ryI7now` (ICLR26, uxXd)
- [D] "Absent these, “efficient” remains asserted, not demonstrated." — `2XP4HD0NBy` (ICLR26, 2JaX ⚑)
- [D] "Contribution no. 4 is not a contribution." — `P4o9akekdf` (ICLR25, wkJy)
- [C] "claiming that training GAN-based models for ISR does not face instability issues is quite a bold claim" — `46mbA3vu25` (ICLR25, cAL4)
- [C] "Clearly, in terms of stone carvings, wall details, and water surface textures, the original 3DGS appears sharper." — `NU3tE3lIqf` (NeurIPS24, nPTW)
- [C] "There is no clear evidence that viewing MLP as a fully connected graph may help to improve the reconstruction and classification ability." — `A8Vuf2e8y6` (ICLR25, UBft)
- [D] "The paper further tries to avoid making this connection to general transformers as much as possible, which feels very misleading" — `LDkyhsiCZQ` (NeurIPS25, avfu)

**Theory gaps (THEO)**
- [C] "are a bit handwavy, in the sense that they make a series of approximations that end up in a nice PDE that one can call a diffusion equation" — `muN3B40keb` (ICLR25, LUop)
- [C] "The Discrete Sine Transform (DST) assumes the odd symmetry at the boundaries: How do you confirm that these datasets satisfy these assumptions?" — `ZXJ74KEVUu` (ICLR26, JJrD)
- [C] "A theoretical argument (despite any assumptions made) would help the reader to appreciate the idea proposed more than an empirical hack" — `83pHDDmkXt` (ICLR26, rzsv)
- [D] "The provable statements in the paper are not in any way non-obvious." — `uZfjFyPAvn` (ICLR24, ksCd)
- [C] "The theoretical results are quite limited." — `Sr5XaZzirA` (ICLR25, svcN)

**Marginal improvements (MARG)**
- [D] "in this paper, the baseline PSNR is already above 40, making the improvement very marginal." — `RKOgWtrWPe` (NeurIPS25, umq2)
- [D] "Bring 0.5-1min acceleration to existing SOTA, so what?" — `5PXMoN8e2W` (ICLR26, 1HVJ)
- [C] "The downstream task performance improvement in Table 2 is marginal, although the reconstruction quality is high." — `A8Vuf2e8y6` (ICLR25, ewZN)
- [C] "A closer look into Table 4 would also reveal that the performance on ODinW is actually on par with GLIPv2 if given the same pertaining data." — `DS5qRs0tQz` (ICLR24, sRML)

**Generalization / scope (GEN)**
- [C] "there are no experiments on real out-of-distribution images." — `M5t0WvjfCg` (ICLR25, Jdae)
- [H] "Blind deconvolution, when limited to the uniform case, may not be particularly useful for real-world problems." — `CFez7MFUFd` (NeurIPS24, QZrB)

**Metrics / protocol (METRIC)**
- [C] "A fairer evaluation would follow the protocol of [1], where models are assessed on held-out subsets of pixel coordinates." — `ZXJ74KEVUu` (ICLR26, 6yc9)
- [C] "The comparisons using only PSNR/SSIM seem insufficient to measure the quality of the resulting images." — `M5t0WvjfCg` (ICLR25, K6x2)
- [C] "A simple way to game the metric (i.e. achieving low training CA) is to simply duplicate each Gaussian N times with opacities scaled" — `GrPo8NTtzK` (NeurIPS25, jvpz)
- [D] "The current way of stopping and evaluating seems incredibly arbitrary and subjective." — `46mbA3vu25` (ICLR25, euHF)

**Visual results (VIS)**
- [C] "In Figure 7 (first and second scenarios), some generated details and textures appear to be creatively added rather than strictly reconstructed from the LQ input." — `TPtXnpRvur` (NeurIPS24, KDhM)
- [C] "I also tried experimenting with the code (great codebase!) and observed that, for text to 3D, the texture in most cases was very saturated." — `UyNXMqnN3c` (ICLR24, MZY6)
- [D] "There is a noticeable disparity in quality when compared to state-of-the-art techniques." — `84Hk01tFKq` (ICLR24, VyWD)

**Related work (RW)**
- [D] "The references are obviously inadequate, as no 2023 papers are included and cited in the paper." — `OKOjkFrhSs` (ICLR24, WtP4)
- [D] "While the authors may and probably will try to defend the paper saying that these papers are not relevant, I would argue that they are." — `HxHrRUHMOD` (ICLR24, DXqV)
- [H] "I recall some works a few years ago that applied similar ideas to arbitrary-scale super-resolution, but I forgot the names" — `SZvhmFntRA` (ICLR26, Jk3f)
- [H] "Note there are also several relevant concurrent works that have since appeared (but which would be unreasonable to call out as a weakness)." — `NU3tE3lIqf` (NeurIPS24, 5zzk)

**Motivation (MOT)**
- [C] "I don’t see a compelling situation where the 3DGS optimizer must be initialized from a random 3D point cloud when accurate camera poses are already available." — `R9lgWYE508` (ICLR25, y9Vo)
- [H] "I am not sure why the model should be croppable for such applications." — `jrVoZLF20h` (NeurIPS24, 45rR)
- [C] "Combining them together without clear motivation make this paper like a technical report." — `6AeIDnrTN2` (NeurIPS24, bxja)

**Variance, reproducibility, limitations, figures, hyperparameters (VAR / REPRO / LIM / FIG / HYP)**
- [C] "Why omit statistical significance tests? Even simple bootstrapped confidence intervals would strengthen claims." — `13xP0J2d6E` (NeurIPS25, zo6q ⚑)
- [C] "Would it be possible to include some measure of variance for some key results?" — `7HEMpBTb3R` (ICLR25, d3Ey)
- [C] "The anonymous link provided by the author is empty, which cannot support reviewing the paper." — `9q4L2odBPh` (NeurIPS25, qds6)
- [C] "The paper's primary limitation is the insufficient exploration of the failure modes of the sinc activation function." — `0Lqyut1y7M` (ICLR24, 9zZJ)
- [C] "Figure 7 is a pastel, set of 3D overlapping bars with partial transparency that make the plot overly artistic and hard to read." — `25Zlvl7JxW` (ICLR25, s4XL)
- [C] "Too much hyperparameter tuning to be generalizable (i.e. all of Appendix B). Authors should defend why this is ok." — `A8Vuf2e8y6` (ICLR25, GNWA)
- [C] "Why does the method's performance degrade in networks deeper than three layers?" — `ZXJ74KEVUu` (ICLR26, JXTJ)

### 3.2 By tone: verdicts, hedges, praise, and rebuttal-phase language

**Dismissive verdicts**
- [D] "I believe the current version of this paper falls far below the NeurIPS standard in both novelty and rigor." — `OZljvntsto` (NeurIPS25, 4qxt)
- [D] "For a top-tier conference with <10% acceptance, matching performance with some efficiency gains is insufficient" — `9zVPsVWUY1` (ICLR26, PPBJ ⚑; the acceptance-rate claim is wrong)
- [D] "I believe the contribution is not enough." — `AQqOC3FKPO` (ICLR25, 224k)
- [D] "In conclusion, the paper is not significantly better than the 3DGS compression baselines." — `6AeIDnrTN2` (NeurIPS24, yR9d; later raised 4→6)

**Hedged (expertise disclaimers, venue doubts)**
- [H] "I'm not an expert in hierarchical classification, so I may have missed some key parts of the problem, modeling, and overall reflection." — `7HEMpBTb3R` (ICLR25, YARY)
- [H] "I do not see any clear weaknesses. However, I acknowledge that I am not familiar with hyperspherical theorems." — `8Hy3KMZTL5` (NeurIPS24, YGpA)
- [H] "I might have missed it, but for me, the paper does not sufficiently discuss/explain the reasoning behind the choice of coordinates" — `4UiLqimGm5` (ICLR24, DCsj)
- [H] "I'm not sure ICLR is a suitable venue for submitting this work, because it lean toward to more empirical side." — `46mbA3vu25` (ICLR25, cAL4)
- [H] "while the idea is interesting and certainly worthy of further investigation, it seems the paper is not quite ready for publication in my opinion." — `A8Vuf2e8y6` (ICLR25, ewZN)

**Enthusiastic**
- [E] "It is a pleasure to read - in fact it reads a bit like an advanced chapter of a wavelet applications textbook." — `uZfjFyPAvn` (ICLR24, ksCd)
- [E] "I checked all proofs in detail and believe they are correct; they follow elegantly from reasonably elementary results from functional analysis." — `0Lqyut1y7M` (ICLR24, REJk)
- [E] "The biggest strength of CAM is its simplicity and its plug-and-play nature." — `4UiLqimGm5` (ICLR24, 7EJV)
- [E] "Overall maturity of the submitted package, which makes it very reasonably within camera ready territory." — `UyNXMqnN3c` (ICLR24, E7Ru)

**Constructive conditional offers (a very common closing move)**
- [C] "I will give a reject first but I can raise the score to 5 if the author can differentiate their work from the missing related works and rephrase their contribution." — `P4o9akekdf` (ICLR25, tg6H)
- [C] "I will consider raising my score if the author can provide experiments with half-image test-time optimization." — `NU3tE3lIqf` (NeurIPS24, BAXf)
- [C] "If the authors improve the writing by the end of the rebuttal period, I will be happy to recommend acceptance for the paper." — `0Lqyut1y7M` (ICLR24, REJk)
- [C] "the list of weaknesses is much longer than the list of strengths not because it is a bad paper, but because the weaknesses are "actionable,"" — `muN3B40keb` (ICLR25, LUop)

**Post-rebuttal: raise, keep, lower, admit a misreading**
- [C] "Despite my reservations regarding the novelty and contribution of this paper, I have decided to raise my rating." — `HKGQDDTuvZ` (ICLR24, fcgY)
- [C] "I have moved my rating up by one as they have put a lot of effort into producing a variety of experiments." — `Sr5XaZzirA` (ICLR25, jBfM)
- [C] "I agree with the performance of LightGaussian, thanks to detailed experiments, and all my concerns have been tackled. I will raise my score to 6." — `6AeIDnrTN2` (NeurIPS24, TPCr)
- [D] "Consequently, I have only increased my score to 3 and still recommend against accepting the paper." — `OZljvntsto` (NeurIPS25, xxwx)
- [C] "I appreciate the additional comparisons, I believe they increase the strength of the paper. However, I am not inclined to change my score." — `jWxrIeWgir` (ICLR24, Tuj3)
- [H] "I find the comments provided by Reviewer AVfU to be important and well-considered, and I will therefore maintain my original score." — `LDkyhsiCZQ` (NeurIPS25, 52s2)
- [D] "I kept my rating, since my concerns were not addressed." — `ZfNeovqQkn` (NeurIPS25, ugec)
- [D] "Thus, I am lowering my score." — `AQqOC3FKPO` (ICLR25, 224k)
- [H] "I would be willing to increase my rating slightly but would still not argue for acceptance given the concerns about technical contributions." — `ZfNeovqQkn` (NeurIPS25, s4ch)
- [C] "I am impressed by the experiments on the RealEstate-10K dataset (I'm sorry to overlook this part)" — `R9lgWYE508` (ICLR25, pLoa)
- [C] "I may have missed section 4.6. Thank you for pointing this out." — `jrVoZLF20h` (NeurIPS24, 45rR)

**Area-chair language**
- [AC] "While agglomeration of design is a fine contribution when it bring about new insights, it is hard to draw such insights from the proposed design in the paper." — `DS5qRs0tQz` (ICLR24, reject)
- [AC] "Reviewers were also lukewarm about the paper, with none of them willing to argue for accepting the paper." — `8Hy3KMZTL5` (NeurIPS24, reject)
- [AC] "The major weakness is the limited novelty, as all the components and ideas were introduced before. However, the overall architecture and solution is non-trivial novel." — `HKGQDDTuvZ` (ICLR24, accept)
- [AC] "the AC agrees that each individual component is not novel on its own, but the significant effectivity of the proposed component marriage is novel." — `6AeIDnrTN2` (NeurIPS24, spotlight)
- [AC] "the claims are too strong given the evidence, since the claimed advantages/competitiveness do not extend to stronger baselines." — `9q4L2odBPh` (NeurIPS25, reject)

---

## 4. Structure statistics

### 4.1 Length (words, n=184 reviews)

| Field | n | Median | IQR | Range |
|---|---|---|---|---|
| Summary | 184 | 86 | 64–104 | 17–532 |
| Strengths | 155 | 65 | 44–92 | 1–332 |
| Weaknesses | 155 | 164 | 102–264 | 15–1292 |
| Strengths+weaknesses (NeurIPS 2025, merged field) | 29 | 228 | 135–290 | 59–692 |
| Questions | 184 | 62 | 16–126 | 1–673 |
| NeurIPS 2025 `final_justification` (when filled) | 25 | 48 | 18–89 | 6–336 |
| **Total review** | 184 | **400** | **293–593** | 147–1495 |

- Median total length by venue: ICLR 2024 415, ICLR 2025 496, ICLR 2026 358, NeurIPS 2024 423, NeurIPS 2025 337.
- The weaknesses section is about 2.5× the strengths section.
- The questions field is a bare pointer in 36/184 reviews (20%): 6 words or fewer, e.g. "See the Weakness" (ZXJ74KEVUu). Elsewhere it often restates the weaknesses.
- **Weakness points per review** (coder count): median 3.5, mean 4.1, IQR 3–5. 16 reviews list 8 or more; the maximum is 21.
- The rating is not predicted by length: Spearman ρ=0.06 between word count and normalised rating.

### 4.2 Confidence and harshness

**Confidence distribution:**

| Confidence | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| Reviews | 2 (1%) | 8 (4%) | 39 (21%) | **99 (54%)** | 36 (20%) |

The modal value is 4 in every venue.

- **Confidence does not predict the score.**
  - Rating vs confidence: ρ=0.02 (p=0.75) using within-venue normalised ratings.
  - Reject-side vs confidence: ρ≈0.00 (p=0.97).
  - The share of reject-side reviews is 43–50% at confidence 2–5.
- **Confidence weakly predicts the volume and register of criticism.**
  - Codes per review vs confidence: ρ=0.15 (p=0.048). The mean is 4.5 codes at confidence 3, 4.9 at 4 and 5.4 at 5.
  - Dismissive tone appears in 6/36 confidence-5 reviews (17%) vs 3/148 at confidence ≤4 (2%); Fisher p=0.002, odds ratio 9.7.
  - So the confident-and-curt reviewer is real, but they are not systematically lower scorers.
- **Sub-scores:** Contribution correlates most with the overall rating (ρ=0.58), ahead of soundness (0.45) and presentation (0.34). The mean sub-scores are soundness 2.82, presentation 2.83 and contribution 2.61 (1–4 scales).

### 4.3 Tone (primary, coder-assigned)

| Tone | Reviews | Share | Notes |
|---|---|---|---|
| Constructive | 146 | 79% | |
| Enthusiastic | 20 | 11% | All on the accept side |
| Hedged | 9 | 5% | |
| Dismissive | 9 | 5% | All on the reject side; 5 of the 9 are in ICLR 2026 |

Even rejecting reviews are mostly written in a constructive register: 57 of 69 reject-side reviews are coded constructive.

### 4.4 Rebuttal dynamics (144 reviews with threads; ICLR 2026 excluded)

**Engagement.**
- Authors responded to 144/144 reviews.
- The reviewer posted anything after the rebuttal in 110/144 (76%) reviews. By venue: ICLR 2024 20/43, ICLR 2025 36/41, NeurIPS 2024 27/31, NeurIPS 2025 27/29.

**Explicit score statements (coded):**

| Statement | Reviews | Share |
|---|---|---|
| Up | 42 | **29.2%** |
| Down | 1 | 0.7% |
| Explicitly kept | 38 | 26.4% |
| No statement | 63 | 43.8% |

- Raise rate by venue: ICLR 2024 5/43 (12%), ICLR 2025 20/41 (49%), NeurIPS 2024 10/31 (32%), NeurIPS 2025 7/29 (24%).
- Among reviewers who replied, 42/110 (38%) raised.

**Size of a raise.**
- Where both scores are stated (n=9), raises are +1 (3 cases) or +2 (6 cases).
- 20 of the 42 raises end exactly at the lowest accept-side score: 6 at ICLR, 5 at NeurIPS 2024, 4 at NeurIPS 2025.
- 8 raises still end on the reject side.
- 8 raises reach a clear-accept score:
  - ICLR 8: 4UiLqimGm5 DCsj, P4o9akekdf tg6H and wkJy, AQqOC3FKPO LUqD.
  - NeurIPS 2024 7: two reviewers.
  - NeurIPS 2025 ≥5: OZljvntsto y2xa, GrPo8NTtzK jews.

**Direction asymmetry.** There was 1 explicit lowering: AQqOC3FKPO 224k, who lowered because a *different* reviewer's questions were unanswered. One more is author-alleged and silent: jWxrIeWgir, where the authors say the rating went 8→5 and the reviewer never mentions it.

**Supplementary scan [estimate].** A regex over all 1,206 keyword-matched CV forums (4,795 reviews) at ICLR 2024/25 and NeurIPS 2024 found an explicit score-raise statement for:
- ICLR 2024: 120/1,469 reviews (8.2%).
- ICLR 2025: 332/2,217 (15.0%).
- NeurIPS 2024: 348/1,109 (31.4%).
- Explicit lowering statements: 22 in total.

Validated against the coded corpus, the regex has precision 39/40 and recall 39/42. The coded corpus over-samples forums with active discussion, so its 29% raise rate is higher than the population rate at ICLR.

**Paper level.**
- 28/36 threaded papers had at least one explicit raise; 18 of those 28 were accepted.
- Of the 8 papers with no raise, 2 were accepted (both had uniformly high initial scores: DreamGaussian and Registers).

**Which complaints are "fixable"?** Raise rate among replying reviewers, with the code vs without it:

| Code | Raise rate with code | Raise rate without |
|---|---|---|
| BASE | 49% (n=47) | 30% |
| BENCH | 52% (n=29) | 33% |
| EFF | 50% (n=28) | 34% |
| OVER | 50% (n=32) | 33% |
| NOV | 48% (n=48) | 31% |
| MOT | 25% (n=20) | 41% |
| LIM | 24% (n=17) | 41% |

- Concrete missing-evidence complaints (baselines, benchmarks, efficiency, overclaim) are the ones authors fix with new experiments or rewording. Motivation and limitation complaints rarely flip.
- Novelty-skeptics raise by one step but seldom to acceptance. Examples:
  - fcgY: "Despite my reservations regarding the novelty and contribution of this paper, I have decided to raise my rating."
  - FFqs: raised to 5 but wrote it "does not indicate support for acceptance of this paper".
  - xxwx: "only increased my score to 3".

**Misreadings (144 threaded reviews):**

| Category | Reviews | Share |
|---|---|---|
| Authors claim a misreading or point to existing content | 58 | **40.3%** |
| Reviewer acknowledges the misreading (confirmed) | 9 | **6.3%** |
| None | 77 | 53.5% |

- Confirmed misreadings by venue: ICLR 2024 1/43, ICLR 2025 3/41, NeurIPS 2024 1/31, NeurIPS 2025 4/29.
- Typical confirmed cases:
  - Overlooked an experiment: R9lgWYE508 pLoa, jrVoZLF20h 45rR, OZljvntsto y2xa.
  - Misunderstood a loss: ZfNeovqQkn s4ch.
  - Missed a stated advantage: 46mbA3vu25 cAL4.
- In 5 of the 9 confirmed cases the reviewer also explicitly raised the score.

---

## 5. Reviewer types observed

Each review has one primary type assigned by the coder with the codebook definitions. These are **coded judgments, not ground truth**. "Any" counts include secondary types.

| Type | Primary n (%) | Any n | Reject-side share | Median words | Mean codes | Mean confidence | What it looks like |
|---|---|---|---|---|---|---|---|
| Expert-constructive | 50 (27%) | 69 | 10/50 | 568 | 5.4 | 3.9 | Specific, domain-informed, cites tables/equations, proposes the exact fix |
| Terse | 34 (18%) | 43 | 10/34 | 241 | 3.3 | 3.6 | 2–3 one-line weaknesses, "See weaknesses" in questions |
| Novelty-skeptic | 23 (12.5%) | 46 | **18/23** | 449 | 5.2 | **4.3** | Names the 1–2 prior works the paper "combines", keeps the score after rebuttal |
| Benchmark-table | 19 (10%) | 32 | 11/19 | 427 | 5.6 | 3.9 | Lists missing SOTA rows, datasets, metrics |
| Checklist | 17 (9%) | 33 | 6/17 | 462 | **6.8** | 3.9 | Long numbered list of small requests, typos, figure fixes |
| Champion | 14 (8%) | 17 | 0/14 | 392 | 3.1 | 4.1 | High score, few weaknesses, sometimes argues with other reviewers |
| Theory-checker | 12 (6.5%) | 18 | 6/12 | 375 | 4.5 | 3.6 | Assumptions, derivations, "why does it work" |
| LLM-generic | 10 (5%) | 21 | 6/10 | 343 | 5.3 | 3.4 | Bold "Title: sentence" bullets, generic asks that fit any paper |
| Practitioner | 4 (2%) | 12 | 1/4 | 346 | 4.0 | 4.0 | Deployment, real data, wall-clock |
| Hostile | 1 (0.5%) | 2 | 1/1 | 230 | 4.0 | 5.0 | Sweeping, accusatory |

Novelty-skeptic reviews are reject-side 18 of 23 times, against 51 of 161 for all other types (Fisher p<0.0001, odds ratio 7.8).

**Example quotes per type**
- **Expert-constructive:** "A closer look into Table 4 would also reveal that the performance on ODinW is actually on par with GLIPv2 if given the same pertaining data." — `DS5qRs0tQz` (sRML)
- **Terse:** "The writing needs improvement." — `8Hy3KMZTL5` (zhUR)
- **Novelty-skeptic:** "Applying variants of previous contributions to 3DGS is thus quite incremental." — `NU3tE3lIqf` (5zzk); "the contribution here is to merely apply these to the NoPoSplat framework." — `ZfNeovqQkn` (s4ch)
- **Benchmark-table:** "The benchmark models referenced are somewhat outdated." — `M5t0WvjfCg` (FFqs)
- **Checklist:** "I have a series of things to point out about the paper, which are the reason for the current score assigned to the paper." — `92d74WdgtG` (1Ux1, 21 bullets)
- **Champion:** "The paper is a strong contribution and is ready for acceptance." — `yGJrvSU6wK` (7JKP); "Regarding the concerns about novelty raised by other reviewers, I believe that leveraging existing methodologies does not diminish the significance of the contribution" — `9q4L2odBPh` (fyfz)
- **Theory-checker:** "Matching entrywise Jacobian variance does not ensure favorable singular-value spectra of end-to-end Jacobians (dynamical isometry)." — `92d74WdgtG` (s653 ⚑)
- **LLM-generic:** "SOTA Validation: Validated at scale on SOTA training recipes, proving practical utility." — `9zVPsVWUY1` (EBbD ⚑)
- **Hostile:** "I doubt the contribution of this paper beyond a published one [1] in NeurIPS 2023. The paper fails to cite it and may intend to mislead the readers." — `7HEMpBTb3R` (uxN6)

**LLM-sounding reviews.**
- Flagged in 25/184 reviews (13.6%), most heavily in ICLR 2026: 12/40, against 5/43 in ICLR 2024, 1/41 in ICLR 2025, 2/31 in NeurIPS 2024 and 5/29 in NeurIPS 2025.
- Pangram labels for our 40 ICLR 2026 reviews: 8 *Fully AI-generated* (20%), 5 *Heavily AI-edited*, 2 *Moderately AI-edited*, 10 *Lightly AI-edited* and 15 *Fully human-written*. Across all 75,800 ICLR 2026 reviews in that dataset, 21.0% are *Fully AI-generated*, so our 20% matches.
- Compared with human-written reviews in this sample, AI-generated ones raised more weakness codes (5.9 vs 4.1) and gave slightly higher ratings (4.5 vs 3.9) **[small n=8 vs 15; estimate]**.
- Observable signs:
  - Bold "Title: sentence" bullets mirrored between weaknesses and questions.
  - A LaTeX `\paragraph{Summary}` left in the text (92d74WdgtG s653).
  - Internal contradictions: SZvhmFntRA hqg6 claims "~0.8–0.9 dB" in its strengths and "≈0.08–0.18 dB" in its weaknesses.
  - Factual slips about the venue: "<10% acceptance" for ICLR.

---

## 6. What moves a paper from reject to accept in rebuttal (observed cases)

### Clear conversions

| Paper | Before → after | What moved the reviewer |
|---|---|---|
| **P4o9akekdf** (NoPoSplat, ICLR25 oral) | tg6H opened at "reject"; raised to 8 | Rewrote contributions and related work to differentiate PF-LRM/LEAP; added an object-level comparison vs LEAP (PSNR 20.559→28.378 on Objaverse); weight-initialization ablation; showed training data matched pixelSplat/MVSplat. The reviewer's own condition was: "I can raise the score to 5 if the author can differentiate their work from the missing related works and rephrase their contribution." |
| **6AeIDnrTN2** (LightGaussian, NeurIPS24 spotlight) | TPCr and yR9d 4→6 | Re-ran the *exact baselines the reviewers named* (Compact/Compressed 3D-GS) on the same GPU with FPS and training time; applied the method to Scaffold-GS with HAC numbers. |
| **NU3tE3lIqf** (WildGaussians, NeurIPS24) | BAXf and bi9Y raised; AC: initially "BA, WA, BA and R" | Showed the evaluation already used the NeRF-W half-image protocol and that GS-W's code did not, so the "unfair comparison" charge was turned around; added SWAG/GS-W under the common protocol. |
| **jrVoZLF20h** (NeurIPS24) | XqfY raised to 6; 45rR "no longer against acceptance" | Extended the partition-factor ablation the reviewer specified, added pseudocode, and pointed to an existing Section 4.6 the reviewer had missed (confirmed misread). |
| **1jG5ngXVs3** (FlowTurbo, NeurIPS24) | yH4R to 5, RYd7 to 6 | New results on SD3/FLUX (scalability) and distillation baselines *with training costs*; block-order ablation. |
| **wWguwYhpAY** (Neural Experts, NeurIPS24) | VtKc 5→6 | InstantNGP comparison, requested by the reviewer *and the AC*. AC: "AC appreciates the authors' efforts and quick response to the request for additional evidence demonstrating the broad impact of their work by providing InstantNGP results". |
| **13xP0J2d6E** (BlurDM, NeurIPS25) | a5f6 raised; accepted with 2/4/5/4/4 | Stage-wise ablation plus a derivation justifying the latent-space assumption. The AC cited "confidence interval analyses, and perceptual metrics during the rebuttal". |
| **OZljvntsto** (NeurIPS25) | y2xa raised to accept (5); accepted at 3/4/5/3 | New CT task (AAPM), results for the named baseline, offer to narrow the overclaiming title. One champion was enough for the AC. |
| **M5t0WvjfCg** (AdaIR, ICLR25) | FFqs 3→5 | Recent all-in-one baselines with parameter counts, plus an attention-type ablation. The reviewer still disclaimed support, but the paper was accepted. |
| **25Zlvl7JxW** (HQGS, ICLR25) | cE6C and rTVv raised | Robustness table vs NeRF/3DGS/SRGS across noise and downsampling levels; ablation averaged over all scenes instead of one. |

### Raises that did not convert (ICLR 2025: borderline-6 papers still rejected)

- **R9lgWYE508**: three reviewers raised to 6 (final 6/6/6/5) after extensive new experiments. Rejected.
- **46mbA3vu25**: three raised (final 6/5/6/6). Rejected.
- **muN3B40keb**: three raised (final 6/5/6/6/6). Rejected.
- **HxHrRUHMOD** (ICLR24): a champion at 8 plus a raise to 6. The AC said "I am leaning towards rejection since there seems to be no consensus but I wouldn't mind if the paper would get accepted". Rejected.
- **DS5qRs0tQz** (Grounding DINO, ICLR24): 5/8/5. The rebuttal addressed sRML's points, but the two 5s never replied. Rejected on "agglomeration of design".
- **ZfNeovqQkn**, **RKOgWtrWPe** (NeurIPS25): novelty and marginal-gain objections. In each, one reviewer moved one step (to borderline reject and borderline accept respectively) and the rest kept. Both rejected.
- **LDkyhsiCZQ** (NeurIPS25 resubmission of an ICLR25 paper): no score moved. The AC called the framing "over-interpretating and over-claiming".

### Patterns (counts are from the 36 threaded papers)

1. **Add the comparison the reviewer named, ideally re-run under the same protocol or hardware** (6AeIDnrTN2, NU3tE3lIqf). This is the most common driver of a raise **[coder-extracted from the rebuttal drivers]**:
   - It appears in 15 of the 18 accepted papers that had a raise.
   - It also appears in 9 of the 10 *rejected* papers that had a raise.
   - It buys points, not acceptance.
2. **Turn a fairness or misreading complaint around with a pointer.** Authors claim misreadings in 40% of reviews, but reviewers concede only 6%. When they do concede, an explicit raise followed in 5 of 9 cases.
3. **Differentiate from the one prior work the skeptic names, and rewrite the contribution list.** This is the only observed way a novelty-based reject flipped (P4o9akekdf). Most novelty-skeptics move one step and stop.
4. **Narrow the claim.** Examples: retitling (OZljvntsto, HxHrRUHMOD); conceding a scope error (2dnO3LLiJ1, where the "all models" claim was corrected for OpenCLIP). Overclaiming is one of the 3 codes that predict rejection.
5. **A champion matters more than the mean.** 19/25 accepted papers had a clear-accept score, against 8/21 rejected papers. Raises to the borderline level without a champion often end in rejection, as in the ICLR 2025 cases above.
6. **Silence after the rebuttal is common and costly.** 34/144 reviewers never replied: ICLR 2024 23/43, other venues 2–5 each. In Grounding DINO and 8Hy3KMZTL5 the non-replying borderline reviewers' scores stood. The 8Hy3KMZTL5 AC wrote: "none of them willing to argue for accepting the paper".

---

## 7. Calibration targets for the simulated reviewer panel (derived from §1–§6)

| Property | Target from real reviews |
|---|---|
| Review length | Median 400 words (IQR 293–593). Weaknesses about 164 words, strengths about 65, summary about 86. |
| Weakness bullets | Median 3–4 (IQR 3–5); occasional 8–21-item checklist reviewers (about 9%). |
| Codes per review | Mean 4.9. Clarity 51%, scope 47%, baselines 42%, novelty 39%, ablations 34%, theory 31%, efficiency 28%, overclaim 28%. |
| What drives a low score | Novelty (64% of reject-side vs 24% of accept-side), overclaiming (42 vs 19), marginal gains (23 vs 5). The other complaints appear equally in positive reviews. |
| Rare asks | Seeds/variance 2%, code 8%. Do not make every simulated reviewer ask for seeds. |
| Confidence | 4 in 54% of reviews, 5 in 20%, 3 in 21%. Uncorrelated with the score. Confidence-5 reviewers are more often dismissive (17% vs 2%). |
| Tone mix | 79% constructive, 11% enthusiastic, 5% hedged, 5% dismissive. |
| Panel disagreement | A within-paper spread of 2+ points on 10-point scales is typical (32/46 papers have spread ≥2). |
| Rebuttal | About 76% of reviewers reply (only 47% in ICLR 2024). About 29–38% raise, by +1/+2. About half of the raises stop at the lowest accept-side score, and 8/42 stay on the reject side. Lowering is about 1%. |
| Misreads | Authors will claim one in about 40% of reviews; only about 6% are conceded. |
| LLM-style reviews | About 20% of ICLR 2026 reviews are fully AI-generated (Pangram). If simulated, they should show bold "Title: sentence" bullets and generic NeRF/efficiency asks. |
