# Figure review: evidence notes

Compiled 2026-10-13 for the figure review in the harness: the figure snapshot every reviewer sees, the opt-in figure job (F01), and blind pairwise comparison of changed figures.
Purpose: ground what the harness measures, what it asks a model to judge, and what it forbids, in perception research, venue guidance, real CV reviews and studies of how vision-language models read figures.

**Labels** (as in `reviewer_behavior_literature.md`, plus three)
- `VERIFIED [full]`: I read the full text (HTML, PDF text, or full web page) and the numbers come from it.
- `VERIFIED [abs]`: I read the official abstract, landing page or publisher summary; the numbers come from it. Details beyond it are not checked.
- `VERIFIED [page]`: an official template, author guideline or style page, read in full. Quotes are exact.
- `METADATA ONLY`: title, authors and venue confirmed from an index; the content was not opened. Not used for any rule.
- `UNVERIFIED`: I could not open the paper or its abstract. Not used for any rule.
- `Inference:` marks my own reading of a result. It is not a claim the cited authors make.

Each entry ends with **Design rule derived**. Section 5 lists the rules and the files that implement them.

---

## 1. Graphical perception and figure design

### 1.1 Which encodings people read accurately
- **Cleveland & McGill 1984**, "Graphical Perception: Theory, Experimentation, and Application to the Development of Graphical Methods", *JASA* 79(387):531-554; https://doi.org/10.1080/01621459.1984.10478080. `METADATA ONLY` (Semantic Scholar record; JSTOR, Taylor & Francis and a course mirror were unreachable). The ranking is taken from the two entries below, not from this paper.
- **Cleveland & McGill 1986**, "An experiment in graphical perception", *Int. J. Man-Machine Studies* 25:491-500 (PDF copy: https://vis.arc.vt.edu/~npolys/projects/safas/science.pdf). `VERIFIED [full]`
  - Abstract: "Two types of position judgments were found to be the most accurate, length judgments were second, angle and slope judgments were third, and area judgments were last."
  - "Distance between judged objects was found to be a factor in the accuracy of the basic judgments."
  - 127 subjects (24 high-school students, 60 college students, 43 technically trained professionals); the error distributions of the three groups were nearly the same, so technical training was not a factor.
  - **Design rule derived:** the comparison a figure exists to show should be encoded by position on a shared axis, with the compared items next to each other. Pie, area, bubble and 3D encodings of a key comparison are an `inappropriate_chart` / `encoding_fit` issue.
- **Heer & Bostock 2010**, "Crowdsourcing Graphical Perception: Using Mechanical Turk to Assess Visualization Design", CHI 2010, pp. 203-212; https://doi.org/10.1145/1753326.1753357 (author PDF https://homes.cs.washington.edu/~jheer/files/2010-MTurk-CHI.pdf). `VERIFIED [full]`
  - Replication of Cleveland & McGill with N=50 subjects per chart: "the rough shape and ranking of judgment types by accuracy (T1-5) are preserved"; "position encoding still significantly outperformed length encoding". New angle and circular-area judgments: area worse than angle, "both ... significantly worse than position".
  - Chart size and gridlines (2,880 responses): charts 40 px tall gave significantly more error (p < 0.001); "little benefit for increasing chart height beyond 80 pixels" on a 0-100 scale; "gridlines be separated by at least 8 pixels".
  - 186 workers in total; the crowdsourced studies cost $367.77 against an estimated $2,190 in the lab.
  - *Inference:* the pixel thresholds come from screens and do not transfer directly to print. The part that transfers is that accuracy drops when the plot area becomes very small or gridlines are packed densely.
  - **Design rule derived:** judge encodings by the Cleveland-McGill ranking (`encoding_fit`), and treat a plot shrunk until its marks and gridlines crowd together as a legibility problem, not a style choice.

### 1.2 Design guidance and how readers take in a figure
- **Rougier, Droettboom & Bourne 2014**, "Ten Simple Rules for Better Figures", *PLoS Comput Biol* 10(9):e1003833; https://doi.org/10.1371/journal.pcbi.1003833. `VERIFIED [full]`
  - The rules include "Identify Your Message", "Adapt the Figure to the Support Medium", "Captions Are Not Optional", "Do Not Trust the Defaults", "Use Color Effectively", "Do Not Mislead the Reader", "Avoid 'Chartjunk'" and "Message Trumps Beauty".
  - Defaults are "good enough for any plot but they are best for none". "Do not use the default colormap (e.g., jet or rainbow) unless there is an explicit reason to do so."
  - "message and readability of the figure is the most important aspect while beauty is only an option."
  - **Design rule derived:** score the message first (`message_clarity`) and never reward decoration. A missing or empty caption is a defect (`caption_not_self_contained`).
- **Franconeri, Padilla, Shah, Zacks & Hullman 2021**, "The Science of Visual Data Communication: What Works", *Psychological Science in the Public Interest* 22(3):110-161; https://doi.org/10.1177/15291006211051956 (publisher summary https://www.psychologicalscience.org/publications/visual-data-communication.html). `VERIFIED [abs]` (Europe PMC abstract and the APS summary page; the full text is paywalled)
  - Abstract: extracting global statistics is fast, comparing subsets of values is slow; effective graphics avoid overloading working memory, guide attention and follow familiar conventions.
  - Summary page: "Comparisons between sets of values are slow"; "Transform legends into labels embedded in the figures"; "starting axes at zero might not always be the best option".
  - **Design rule derived:** a figure should make its one intended comparison easy (grouping, direct labels instead of distant legends). Axis truncation is judged case by case (see Correll et al., 1.3), not by a blanket zero-baseline rule.
- **Borkin, Vo, Bylinskii, Isola, Sunkavalli, Oliva & Pfister 2013**, "What Makes a Visualization Memorable?", *IEEE TVCG* (InfoVis 2013); https://vcg.seas.harvard.edu/publications/20130101-what-makes-a-visualization-memorable. `VERIFIED [abs]`
  - 2,070 single-panel visualizations from news, government reports, journals and infographics; "observers are consistent in which visualizations they find memorable and forgettable". Colour and a human-recognizable object raise memorability; common chart types are less memorable than unusual ones.
  - *Inference:* memorability rewards exactly the features that Cleveland-McGill accuracy does not (unusual forms, pictorial content). The two goals belong to different figure roles.
  - **Design rule derived:** judge figures by role. A teaser may legitimately be pictorial and memorable; a quantitative plot is judged on accurate reading. Neither earns credit for decoration alone.
- **Borkin, Bylinskii, Kim, Bainbridge, Yeh, Borkin, Pfister & Oliva 2016**, "Beyond Memorability: Visualization Recognition and Recall", *IEEE TVCG* (online 2015); https://doi.org/10.1109/TVCG.2015.2467732 (lab page https://vcg.seas.harvard.edu/publications/20150101-beyond-memorability-visualization-recognition-and-recall). `VERIFIED [abs]`
  - 393 labelled visualizations, eye movements of 33 participants, thousands of written descriptions. Titles and supporting text "should convey the message of a visualization"; redundancy helps; visualizations memorable "at-a-glance" also convey their message well.
  - **Design rule derived:** the caption (the title of a paper figure) should state the message, and a teaser should deliver its idea or result at a glance (role `teaser`).
- **Lee, West & Howe**, "Viziometrics: Analyzing Visual Information in the Scientific Literature", arXiv 2016; https://arxiv.org/abs/1605.04951. `VERIFIED [abs]`
  - More than 8 million PubMed figures classified into 5 types. "higher impact papers tend to include more diagrams", and to a lesser extent more plots and photographs. Correlational.
  - **Design rule derived:** method diagrams are a first-class figure role (`method_diagram`), checked against the equations and notation (`diagram_equation_mismatch`). The correlation is not a reason to penalise a paper without one.
- **Lundgard & Satyanarayan 2022**, "Accessible Visualization via Natural Language Descriptions: A Four-Level Model of Semantic Content", *IEEE TVCG* (Proc. InfoVis); https://arxiv.org/abs/2110.04406. `VERIFIED [full]` (ar5iv HTML)
  - Four levels of description content: L1 construction (marks, encodings), L2 statistics (extrema, correlations), L3 perceptual and cognitive patterns (trends), L4 domain insight. Built from 2,147 sentences; evaluated with 30 blind and 90 sighted readers.
  - Sighted readers ranked L3 and L4 most useful and L1 and L2 least useful. Blind readers ranked L2 and L3 most useful. 63% of blind readers wanted no subjective interpretation (L4).
  - **Design rule derived:** a caption that only states construction ("PSNR versus iterations for four methods") is not self-contained. It should state the comparison or trend the reader is meant to see (L2/L3), and any L4 conclusion must be visible in the figure or in a table (`caption_text_mismatch`).

### 1.3 Showing data honestly
- **Weissgerber, Milic, Winham & Garovic 2015**, "Beyond Bar and Line Graphs: Time for a New Data Presentation Paradigm", *PLoS Biol* 13(4):e1002128; https://doi.org/10.1371/journal.pbio.1002128. `VERIFIED [full]`
  - 703 physiology articles (Jan-Mar 2014): 85.6% had at least one bar graph; 77.6% used mean ± SE bars against 15.3% mean ± SD; univariate scatterplots appeared in 13.4%.
  - In 75% of papers the smallest group shown had 2-6 observations (median 4). "many different data distributions can lead to the same bar or line graph."
  - Recommendation: "Univariate scatterplots are the best choice for showing the distribution of the data in these small samples".
  - *Inference:* CV results with few runs, scenes or user-study participants are the same small-n case. CV reviewers rarely ask for variance (VAR 4/184 = 2.2%, `real_review_patterns.md` §2), so this is a quality criterion, not a common reject reason.
  - **Design rule derived:** for small-n summaries, the quantitative-plot role expects points or a distribution and error bars whose meaning (SD, SE, CI) is stated. Unlabelled error bars are `missing_labels_or_units`.
- **Correll, Bertini & Franconeri 2020**, "Truncating the Y-Axis: Threat or Menace?", CHI 2020; https://doi.org/10.1145/3313831.3376222 (https://arxiv.org/abs/1907.02035). `VERIFIED [full]` (ar5iv HTML)
  - Three crowdsourced experiments (40, 32 and 25 participants). Truncation level strongly affected perceived severity (Exp. 1: F(2,76) = 89, p < 0.0001); starting the y-axis at 25% raised ratings by 0.36 on a 1-5 scale. Bar and line charts were affected alike.
  - Broken-axis and gradient designs did not remove the effect: "neither intervention had a consistent impact on perceived severity".
  - "There is therefore not a clear binary distinction between 'deceptive' versus 'truthful' y-axis presentations." The authors recommend matching the axis to the size of the effects that matter.
  - **Design rule derived:** a non-zero baseline is not automatically a defect. `misleading_encoding` applies when the visual size of a difference is out of proportion to its meaningful size, and the reviewer must quote the tick labels that show it. Because annotations do not undo the effect, the fix is to change the axis or add the absolute numbers, not to add a break symbol.
- **Pandey, Rall, Satterthwaite, Nov & Bertini 2015**, "How Deceptive are Deceptive Visualizations?", CHI 2015, pp. 1469-1478; https://doi.org/10.1145/2702123.2702608. `UNVERIFIED` (ACM page returned 403; the Semantic Scholar record has no abstract). Not used; Correll et al. cover truncated axes.
- **Jambor et al. 2021**, "Creating clear and informative image-based figures for scientific publications", *PLoS Biol* 19(3):e3001161; https://doi.org/10.1371/journal.pbio.3001161. `VERIFIED [full]`
  - 580 papers with image-based figures from the top 15 journals in each of three biology fields (April 2018).
  - Complete scale information: 28-55% of papers by field. Inset use not adequately explained: 47-58%. Papers with some images inaccessible to deuteranopes: 21-45%; colour annotations invisible to deuteranopes: 17-34%. All criteria met: 2-16%.
  - "Inset positions should be clearly marked by lines or regions of interest in a high-contrast color"; "Encourage authors to explain labels or annotations in the figure, rather than in the legend".
  - *Inference:* the fields differ from CV, but the figure type is the same as a CV qualitative grid: image panels, zoom insets and colour overlays. Scale bars rarely apply to CV images; inset marking and colour overlays do.
  - **Design rule derived:** in qualitative comparisons, zoom insets are marked on the full image and identical across methods, overlay colours survive the deuteranopia preview, and labels are explained in the figure.

### 1.4 Colour and colour-vision deficiency (CVD)
- **Crameri, Shephard & Heron 2020**, "The misuse of colour in science communication", *Nat. Commun.* 11:5444; https://doi.org/10.1038/s41467-020-19160-7 (https://pmc.ncbi.nlm.nih.gov/articles/PMC7595127). `VERIFIED [full]`
  - "worldwide 0.5% of women and 8% of men are subject to a colour-vision deficiency."
  - A non-uniform colour map "adds artificial boundaries to some parts of the data range, hiding small-scale variations elsewhere"; it "can diverge from an objective representation by more than seven percent of the displayed data variation".
  - Scientific colour maps are perceptually uniform and ordered; a map with a monotonic lightness gradient "remains readable ... even after a conversion to grey scale".
  - **Design rule derived:** heat, error, depth and attention maps use perceptually uniform maps (the viridis family or equivalent), not jet or rainbow. The grayscale preview is the check: if the ordering disappears in gray, the map is not ordered in lightness.
- **Machado, Oliveira & Fernandes 2009**, "A Physiologically-based Model for Simulation of Color Vision Deficiency", *IEEE TVCG* 15(6):1291-1298; https://doi.org/10.1109/TVCG.2009.113 (project page with matrices https://www.inf.ufrgs.br/~oliveira/pubs_files/CVD_Simulation/CVD_Simulation.html). `VERIFIED [abs]` (abstract and matrix table on the project page)
  - CVD "affects approximately 200 million people worldwide". The model handles normal vision, anomalous trichromacy and dichromacy in one framework and was validated with CVD and normal-vision observers.
  - The severity-1.0 deuteranomaly matrix on the page is (0.367322, 0.860646, -0.227968; 0.280085, 0.672501, 0.047413; -0.011820, 0.042940, 0.968881). `figure_render.py` uses exactly these nine values.
  - The page does not say whether the matrix applies to linear or gamma-encoded RGB. The harness applies it in linear RGB; that is the harness's choice, not a claim of the source.
  - **Design rule derived:** colour figures get a simulated deuteranopia preview, and colour claims are made from the preview, not from the reviewer's impression of the colours.
- **Okabe & Ito**, "Color Universal Design (CUD): How to make figures and presentations that are friendly to Colorblind people"; https://jfly.uni-koeln.de/color/. `VERIFIED [page]`
  - "One in twelve Caucasian (8%), one in 20 Asian (5%), and one in 25 African (4%) males are so-called 'red-green' colorblind."
  - "Avoid the situation where important information is conveyed only in the form of color." Solid and dotted lines "look different even without color". For two-channel images, use magenta and green, not red and green.
  - **Design rule derived:** a figure that separates methods or classes by hue alone needs a second cue (marker, line style, direct label). The Okabe-Ito palette is the default fix.
- **Matplotlib documentation**, "Choosing Colormaps in Matplotlib"; https://matplotlib.org/stable/users/explain/colors/colormaps.html. `VERIFIED [page]`
  - Perceptually uniform sequential maps (viridis, plasma, inferno, magma, cividis): "equal steps in data are perceived as equal steps in the color space". For jet, "the L* values vary widely throughout the colormap".
  - "The most common form of color vision deficiency involves differentiating between red and green." "It is important to pay attention to conversion to grayscale for color plots, since they may be printed on black and white printers."
  - **Design rule derived:** as for Crameri et al.; viridis and cividis are the default fixes for continuous maps.

---

## 2. Venue and publisher guidance on figures

The page limit, supplementary-material rules and external-link ban for CVPR are already quoted in `cvpr_official_process.md` §6. Only the figure-specific guidance is added here.

- **CVPR / ICCV / 3DV author kit**, `sec/2_formatting.tex`; https://github.com/cvpr-org/author-kit (README: "Official LaTeX template for CVPR/ICCV/3DV"). `VERIFIED [page]`
  - "Please ensure that any point you wish to make is resolvable in a printed copy of the paper."
  - "Resize fonts in figures to match the font in the body text, and choose line widths that render effectively in print."
  - Readers and reviewers may print the paper; authors "must not assume that they can zoom in to see tiny details on a graphic."
  - Columns are 3¼ in (8.25 cm) wide; the text area is 6⅞ in (17.46 cm) wide. Figure captions are 9-point and go below figures; table captions go above tables.
  - Colour: "a significant subset of reviewers and readers may have a color vision deficiency"; "avoid relying only on color as the discriminative feature in plots"; "add a second discriminative feature to ease disambiguation."
- **CVPR 2026 Author Guidelines**; https://cvpr.thecvf.com/Conferences/2026/AuthorGuidelines. `VERIFIED [page]`
  - "Papers are limited to eight pages, including figures and tables, in the CVPR style."
  - "Supplementary material may include videos, proofs, additional figures or tables". "Reviewers will be encouraged to look at it, but are not obligated to do so." "A link to additional videos is not allowed because it expands contributed content."
- **NeurIPS 2026 formatting instructions** (Overleaf copy of the official template; https://www.overleaf.com/latex/templates/formatting-instructions-for-neurips-2026/bjdwqfdkyftc). `VERIFIED [page]`
  - Text block 5.5 in wide. "All artwork must be neat, clean, and legible. Lines should be dark enough for reproduction purposes."
  - "You may use color figures. However, it is best for the figure captions and the paper body to be legible if the paper is printed in either black/white or in color."
  - The sample captions read: "Explain what the figure shows and add a key take-away message to the caption." (the table sample says the same).
- **ICLR 2026 template**, `iclr2026/iclr2026_conference.tex`; https://github.com/ICLR/Master-Template. `VERIFIED [page]`
  - "All artwork must be neat, clean, and legible." "Always specify the figure width as a multiple of the line width". Text block 5.5 in. Captions and body should "make sense if the paper is printed either in black/white or in color."
- **Nature, "Preparing figures - our specifications"**; https://research-figure-guide.nature.com/figures/preparing-figures-our-specifications/. `VERIFIED [page]`
  - "Maximum text size for all other text is 7-pt and the minimum is 5-pt." Sans-serif fonts; "export figure panels as vector artwork"; "Do not outline text".
  - "All photographic images must be supplied at a minimum of 300 dpi" (the export section says 450 dpi for images). "An accessible colour palette to be used". "Scale bars should be used rather than magnification factors."
- **IEEE Author Center, "Resolution and Size"**; https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/create-graphics-for-your-article/resolution-and-size/. `VERIFIED [page]`
  - "IEEE standards for non-vector graphics for color and grayscale images are >300dpi." "IEEE standards for black and white line art are >600dpi." One column 3.5 in (88.9 mm); two columns 7.16 in (182 mm). The page gives no font size.

**What the guidance agrees on**
- Figures must be readable at final print size, without zoom, and in black and white. CVPR says this most strongly.
- Colour must not be the only cue (CVPR kit, Nature, plus Okabe & Ito in 1.4).
- Captions state the take-away (NeurIPS 2026 sample caption; Rougier rule 4; Freeman 2014 in `reviewer_behavior_literature.md` §2.2: captions should "tell the reader what to notice").

**Thresholds the harness uses.** *Inference:* the venues do not give one number, so the harness separates a defect flag from a fix target.
- Text size: `figure_render.py` flags vector text below 6 pt (between Nature's 5 pt floor and CVPR's "match the font in the body text"). `writer_rules.md` targets about 7 pt or more at print size.
- Raster images: the flag is below 150 ppi (clearly low under any venue's rule); the fix target is ≥300 ppi (Nature, IEEE).
- Measuring in the PDF measures the printed size, because the PDF page is the print page. That is why the measured pt values are authoritative and the reviewer is told not to estimate them.

---

## 3. Real CV review complaints about figures (harness corpus)

Source: `real_review_patterns.md`, 184 public OpenReview reviews of 46 computer-vision papers at ICLR 2024-2026 and NeurIPS 2024-2025. No CVPR/ICCV/ECCV review dumps were found (§0), so this is the closest public evidence. Coding was done by LLM annotators with machine-checked quotes; codes may run about 10-15% high (§0).

- **Frequency (§2 table).**
  - FIG (figure or table presentation quality): 24/184 = 13.0% (95% CI 9-19). Reject-side 12% vs accept-side 14%, p = 0.82.
  - VIS (insufficient or unconvincing visual results, artifacts, hallucinated detail): 37/184 = 20.1% (15-26). Reject-side 19% vs accept-side 21%, p = 0.85.
  - VIS by venue (§2): 12-29% (lowest ICLR 2026, highest NeurIPS 2024).
- **They do not drive the decision (§2, "What the table says", point 1).** Only novelty, overclaiming and marginal gains separate reject-side from accept-side reviews. Figure complaints appear equally in positive reviews.
- **What the complaints look like (§3.1).**
  - Plot design: a 3D chart of overlapping semi-transparent bars called "overly artistic and hard to read" (`25Zlvl7JxW`, FIG).
  - Qualitative results: details that look "creatively added rather than strictly reconstructed" (`TPtXnpRvur`), over-saturated textures (`UyNXMqnN3c`), visible quality gap to the state of the art (`84Hk01tFKq`) (all VIS).
  - Figures as evidence: an ablation shown on "a single example" (`84Hk01tFKq`, ABL); a visual comparison in which the baseline "appears sharper" than the method (`NU3tE3lIqf`, OVER).
- **Who raises them (§5).** The checklist reviewer type (17/184, 9%) writes long numbered lists that include figure fixes.
- *Inference:* in CV reviews, figures matter most as evidence (qualitative comparisons, visual ablations), less as graphic design. A figure that contradicts the text becomes an overclaiming complaint, and overclaiming is one of the three codes that predict rejection.
- **Design rules derived:**
  1. Figure issues are feedback, not verdict drivers. The figure job is opt-in, section-only (`overall: null`), and its persona is never drawn into a sampled panel.
  2. Weight the evidence role of figures: the `qualitative_comparison` role and the `comparison_fairness` criterion (same crops and insets for all methods, all key baselines, failure cases somewhere), with the defects `unfair_comparison` and `missing_failure_cases`.
  3. Cross-check what a figure shows against the text and tables (`figure_text_inconsistency`, `caption_text_mismatch`), because that is where a figure problem turns into an overclaim.

---

## 4. How reliably vision-language models read and judge figures

This section condenses a separate literature pass made for this design (68 entries: 63 verified on a primary page, 5 partial, i.e. paper confirmed but venue or some detail only from search results). Labels below come from that pass: `[full]` where it read the HTML or PDF text, `[abs]` where it read only the abstract page. I re-opened three sources (CharXiv abstract, VisJudge-Bench abstract, SciFigQual-Bench v3 full text) and their numbers matched.

- **4.1 Text-only reviewers cannot see figures.** Liang et al., "Can large language models provide useful feedback on research papers?", arXiv 2023 (*NEJM AI* 2024, venue `SECONDARY`); https://arxiv.org/abs/2310.01783. `VERIFIED [full]` The pipeline used the title, abstract, captions and main text; the paper notes GPT-4 "does not possess the capability to understand or interpret visual data such as tables, graphs, and figures". The AI Scientist reviewer also cannot see figures (`reviewer_behavior_literature.md` §3.1).
  - **Design rule derived:** every reviewer receives figure crops and page images, not only captions.
- **4.2 Chart question answering is not figure critique.** CharXiv (Wang et al., NeurIPS 2024; https://arxiv.org/abs/2406.18521; `VERIFIED [full]`): 2,323 real arXiv charts; reasoning accuracy GPT-4o 47.1% and the best open model 29.2%, against 80.5% for humans. Counting labelled ticks: humans 92.9%, GPT-4o 59.8%; 20 of 24 models below 10%. With 6+ subplots, proprietary models lose 10-30%. Open models answered nearly 90% of unanswerable questions instead of declining. Google reports Gemini 3 Pro at 80.5% on CharXiv reasoning (https://blog.google/technology/developers/gemini-3-pro-vision/). ChartQAPro (Masry et al. 2025; https://arxiv.org/abs/2504.05506; `VERIFIED [abs]`): Claude 3.5 Sonnet scored 90.5% on ChartQA but 55.81% on ChartQAPro.
  - **Design rule derived:** the reviewer never counts marks or reads precise unlabelled values; "cannot determine" is a valid answer. High chart-QA scores are not evidence that a model judges figure quality well.
- **4.3 Much of a "figure reading" can come from text.** SciFIBench (Roberts et al., NeurIPS 2024 D&B; https://arxiv.org/abs/2405.08807; `VERIFIED [full]`): an OCR-text-only baseline scored 51.0% against 65.8% with images; labelling a wrong caption as "correct" lowered accuracy for all models. MMStar (Chen et al. 2024; https://arxiv.org/abs/2403.20330; `VERIFIED [abs]`): many benchmark questions can be answered without the image. SPIQA (Pramanick et al., NeurIPS 2024 D&B; https://arxiv.org/abs/2407.09413; `VERIFIED [full]`): removing captions lowered every Gemini and GPT variant, and full-paper text helped further.
  - **Design rule derived:** describe each figure before reading the caption's claims, then compare. Give the caption and the referencing text as context, but a finding that the caption alone would produce is not a visual finding.
- **4.4 Fine visual detail fails.** BlindTest (Rahmanzadehgervi et al. 2024; https://arxiv.org/abs/2407.06581; `VERIFIED [abs]`): on 7 simple tasks (overlapping circles, line crossings), four frontier VLMs averaged 58.07% against an expected 100% for humans; accuracy drops when shapes overlap or sit close together.
  - **Design rule derived:** overlap, collisions and text size are measured or shown in crops, not judged from the full figure.
- **4.5 Crops help; resolution limits are real.** Zhang et al., "MLLMs Know Where to Look", ICLR 2025 (https://arxiv.org/abs/2502.17422; `VERIFIED [full]`): adding a crop around the answer region raised small-subject accuracy (GPT-4o 65.76 to 75.63; LLaVA-1.5 39.38 to 69.95). Anthropic's vision documentation (https://platform.claude.com/docs/en/build-with-claude/vision; `VERIFIED [page]`): images are downscaled to a 1568 px long edge (2576 px on newer models), and requests with more than 20 images get a stricter per-image limit.
  - **Design rule derived:** one crop per figure including its caption, sized to about 1600 px on the long side so small text survives the model's resizing, plus the page image for layout and size in the column.
- **4.6 Colour, axes and titles are weak spots.** Bendeck & Stasko, IEEE VIS 2024 (https://faculty.cc.gatech.edu/~john.stasko/papers/vis24-llm.pdf; `VERIFIED [full]`): GPT-4 scored 19.67 on VLAT against a human mean of 28.82; it "could not even provide ballpark values" at times; it could not reliably distinguish colours; a truncated axis fooled it (difference rated 1/5 in the control, 5/5 in the deceptive version); it ignored an inverted axis even when asked to look for misleading tactics; it flagged even control titles as inappropriate. ChartMimic (Yang et al., ICLR 2025; https://arxiv.org/abs/2406.09961; `VERIFIED [full]`): colour was GPT-4o's weakest element (67.2, against layout 89.8).
  - **Design rule derived:** colour claims are made only from the grayscale and deuteranopia previews; claims about axes must quote the visible tick labels.
- **4.7 Misleading-chart detection over-flags unless defects are defined.** Lo & Qu, IEEE VIS 2024 (https://arxiv.org/abs/2407.17291; `VERIFIED [full]`): most models called most charts misleading; ChatGPT correctly identified only 3 of 12 valid charts; a 21-issue prompt caused skipped reasoning and repetition. Alexander et al., IEEE VIS 2024 (https://arxiv.org/abs/2408.12617; `VERIFIED [full]`): supplying defect definitions gave the best AUC, 0.821, against 0.788 for naive few-shot.
  - **Design rule derived:** a fixed, defined defect list; every weakness names one defect and quotes visible evidence; at most about 8 weaknesses, ranked.
- **4.8 Extract, then verify, then critique.** Charts-of-Thought (Das et al., IEEE VIS 2025; https://arxiv.org/abs/2508.04842; `VERIFIED [abs]`): prompting the model to extract the data, verify it, then analyse raised VLAT scores by 21.8% (GPT-4.5), 9.4% (Gemini 2.0) and 13.5% (Claude 3.7).
  - **Design rule derived:** per figure, describe (panels, axes, encodings, perceived message), check against the text and tables, then critique. `perceived_message` is written before `intended_message`.
- **4.9 Absolute quality scores are inflated and weakly valid.** VisJudge-Bench (Xie et al., ICLR 2026; https://arxiv.org/abs/2510.22373; `VERIFIED [full]`): 3,090 expert-annotated samples across 32 chart types; GPT-5 had MAE 0.553 and correlation 0.428 with experts; data-fidelity correlations were about 0.18-0.39 across GPT-5, Claude and Gemini; Claude-3.5-Sonnet averaged 3.87 against a human mean of 3.13; a chaotic treemap rated 1.67 by humans got 3.08 from Claude-4-Sonnet.
  - **Design rule derived:** figure scores are feedback for ranking which figures to fix first. They never decide whether a revision is accepted, and decoration, density or saturation earn no credit.
- **4.10 Even humans agree only moderately; measured facts help.** SciFigQual-Bench (Deng et al. 2026; https://arxiv.org/abs/2607.27084; `VERIFIED [full]`): 7,609 figures from 1,144 ACL/EMNLP/ICML/NeurIPS papers. Human agreement: Krippendorff's alpha 0.51 overall; caption consistency the weakest dimension (alpha 0.49). A constant predictor at the mean gives MAE 0.565; the best direct judge 0.443 and the best staged agent 0.418. An OCR/CV sidecar lowered MAE on every backend where it was run (nine backends; small gains).
  - **Design rule derived:** measured facts (text size, resolution, where a figure is first referenced) go to the reviewer as a sidecar (`FIGURES.md`) and override its estimates. Caption-alignment judgements carry lower confidence and must quote both the caption and the visible content.
- **4.11 Pairwise beats absolute scoring.** MLLM-as-a-Judge (Chen et al., ICML 2024; https://arxiv.org/abs/2402.04788; `VERIFIED [full]`): GPT-4V agreed with humans at 0.773 on pair comparison against Pearson 0.490 on absolute scores; lengthening answers without changing meaning raised scores by about 0.6 (GPT-4V) and 0.75 (Gemini).
  - **Design rule derived:** a changed figure is judged by blind pairwise comparison of the old and new crops, in random order. This matches the harness's existing pairwise rule (`reviewer_behavior_literature.md` §4.3).
- **4.12 Critics drift to cosmetic advice.** VIS-Shepherd (Pan et al. 2025; https://arxiv.org/abs/2506.13326; `VERIFIED [full]`, qualitative results): in a worked example GPT-4o missed a truncated legend and offered "less urgent suggestions such as adding annotations or more prominent borders"; long critiques often missed key defects.
  - **Design rule derived:** rank weaknesses by severity, give each one concrete fix (`one_point_fix`), and do not count cosmetic suggestions as defects.
- **4.13 Visual feedback loops help, but mostly by their own judge.** MatPlotAgent (Yang et al., Findings of ACL 2024; https://arxiv.org/abs/2402.11453; `VERIFIED [full]`): visual feedback raised GPT-4 from 53.44 to 61.16 on MatPlotBench, scored by a GPT-4V auto-scorer; it lowered CodeLlama-34B (16.54 to 14.18). PlotGen (Goswami et al. 2025; https://arxiv.org/abs/2502.00988; `VERIFIED [full]`): removing the visual feedback agent cost 10-15%, again judged by GPT-4V. Without external feedback, self-correction can make results worse (Huang et al., ICLR 2024; https://arxiv.org/abs/2310.01798; `VERIFIED [abs]`), and RLHF made models more persuasive but not more correct (Wen et al. 2024; https://arxiv.org/abs/2409.12822; `VERIFIED [abs]`).
  - **Design rule derived:** the writer may improve figures, but a fix counts only when a separate blind pairwise judge prefers it, and the data shown is locked (no changes to plotted values, axis limits or direction, baselines shown or crop locations without the user's approval).
- **4.14 Images do not make the reviewer injection-proof.** MMReview (Gao et al. 2025; https://arxiv.org/abs/2508.14146; `VERIFIED [full]`): multimodal input reduced the effect of prompt injection in every model-size group (e.g. a PI score of 0.67 to 0.42 for tiny models), but did not remove it. Hidden-prompt cases in real manuscripts are in `reviewer_behavior_literature.md` §3.3.
  - **Design rule derived:** text inside figures and the PDF is data; the figure reader ignores instructions found there.

---

## 5. Rules the harness implements, and where

File names follow the figure design. "(new)" marks files added by the figure-review change set, which may not exist at the commit that adds this note.

1. **Every reviewer sees figure images.** Each reviewer's reading block points to `FIGURES.md`, the crops and the page images, filtered by reading view. Evidence: 4.1; CVPR kit "resolvable in a printed copy" (2); reviewers "first look at the pictures" (Kajiya, `reviewer_behavior_literature.md` §2.2). Where: `06_scripts/hxlib/prompts.py` (`_reading_block`), `06_scripts/hxlib/dialogue.py` (`satisfy_prompt`).
2. **Measure what can be measured, and treat it as authoritative.** Smallest vector text in pt, lowest raster ppi, first text reference; flags below 6 pt, below 150 ppi, and for unreferenced main-paper figures. Evidence: 2 (venue sizes and resolutions); 4.4, 4.10. Where: `06_scripts/hxlib/figure_locate.py`, `06_scripts/hxlib/figure_render.py` (`SMALL_TEXT_PT`, `LOW_PPI`, `_flags`), `FIGURES.md`; authority stated in `02_protocol/figure_review_rules.md` (new).
3. **One crop per figure with its caption, about 1600 px on the long side, plus page images.** Crop resolution is clamped to 150-300 dpi. Evidence: 4.5. Where: `figure_render.py` (`CROP_LONG_SIDE_PX`, `CROP_DPI_RANGE`, `PAGE_DPI`).
4. **Colour claims only from previews.** Grayscale preview for every figure; deuteranopia preview (Machado matrix, linear RGB) for colour figures. A colour defect means two meaning-carrying encodings become indistinguishable in a preview. Evidence: 1.4; CVPR kit colour sentences (2); Jambor (1.3); 4.6. Where: `figure_render.py` (`DEUTERANOPIA`, preview step), `figure_review_rules.md` (new), defect `colour_inaccessible`.
5. **Describe, check, critique; quote visible evidence; say "cannot determine".** No precise reading of unlabelled values, no counting marks, no mapping colours to legends by eye. Evidence: 4.2, 4.3, 4.6, 4.8. Where: `figure_review_rules.md` (new), `05_templates/figure_schema.md` (new; `perceived_message`, `visible_evidence`), `06_scripts/hxlib/validate.py` (non-empty evidence fields).
6. **Fixed defect list with definitions; at most about 8 ranked weaknesses.** Evidence: 4.7, 4.12; generic-comment rates in MARG (`reviewer_behavior_literature.md` §3.1). Where: `02_protocol/figure_criteria.json` (new; `defects`), `02_protocol/figure_rubric.md` (new; definitions and typical fixes), `validate.py` (`defect` and `figure_id` checks).
7. **Six criteria judged by role.** `message_clarity`, `legibility`, `encoding_fit`, `accessibility`, `caption_alignment`, `comparison_fairness` (null when nothing is compared); roles teaser, method diagram, quantitative plot, qualitative comparison, table. Evidence: 1.1 (encoding ranking), 1.2 (message first; memorable teasers vs accurate plots; diagrams), 1.3, 1.4, 3. Where: `figure_criteria.json` (new), `figure_rubric.md` (new).
8. **Captions state what is shown and what to conclude, and every claim in them is visible.** Evidence: Rougier rule 4 and Borkin 2016 (1.2); Lundgard L2/L3 (1.2); NeurIPS 2026 sample caption (2); Freeman 2014 (`reviewer_behavior_literature.md` §2.2); 4.10 (low agreement, so quote both sides). Where: `figure_rubric.md` (`caption_alignment`; defects `caption_not_self_contained`, `caption_text_mismatch`), `02_protocol/writer_rules.md` (Figures section).
9. **Qualitative comparisons are fair.** Same crops and marked zoom insets for all methods, all key baselines, failure cases somewhere. Evidence: 3 (VIS 20%, ABL and OVER examples); Jambor insets (1.3). Where: `figure_rubric.md` (role `qualitative_comparison`, `comparison_fairness`; defects `unfair_comparison`, `missing_failure_cases`).
10. **Quantitative plots: right encoding, honest axes, labelled uncertainty.** Position on a common scale for the key comparison; truncation judged by meaningful effect size with quoted tick labels; small-n results shown as points or distributions; error-bar type stated. Evidence: 1.1, 1.3 (Weissgerber, Correll), 1.2 (Franconeri). Where: `figure_rubric.md` (role `quantitative_plot`; defects `misleading_encoding`, `inappropriate_chart`, `missing_labels_or_units`).
11. **Cross-check figures against text and tables.** Evidence: 3 (figure-text conflicts become overclaims); 4.3; 4.6. Where: `figure_review_rules.md` (new), `06_scripts/hxlib/figure_prompts.py` (new; supplies the main-text view), defects `figure_text_inconsistency`, `diagram_equation_mismatch`.
12. **No credit for decoration, density or saturation.** Evidence: Rougier "Message Trumps Beauty" (1.2); 4.9; 4.12. Where: `figure_review_rules.md` (new), `02_protocol/pairwise_rules.md` (Figures block).
13. **Figure issues inform; they do not decide.** The figure job is opt-in, section-only (`overall: null`), in the feedback group; persona F01 has `draw_weight` 0 and role `figure_reviewer`, so sampled panels and the gauntlet never include it. Evidence: 3 (FIG and VIS do not separate accept from reject). Where: `06_scripts/hx.py` (`--figures`), `06_scripts/hxlib/panel.py` (`build_jobs`, `draw_panel`), `03_personas/personas.json`, `03_personas/F01_figure_reader.md` (new).
14. **Changed figures are judged blind and pairwise.** Only figures whose crop hash changed; copies named A/B in random order; decoded from the key afterwards. Evidence: 4.11, 4.13; `reviewer_behavior_literature.md` §4.3 and §6 rule 5. Where: `figure_render.py` (`crop_sha256` in `figures.json`), `06_scripts/hxlib/prompts_stages.py` (`pairwise_prompt`), `06_scripts/hxlib/aggregate.py` (`_decode_pairwise`), `pairwise_rules.md`.
15. **Data lock.** The writer never changes plotted values, axis limits or direction, baselines shown or crop locations to make a figure look better; such changes are evidence edits that need the user's approval. In pairwise comparison, a version that changes what data is shown loses unless the change is neutral. Evidence: 1.3 (Correll: truncation changes perceived effects and annotations do not undo it); 4.6 (models are fooled by truncated and inverted axes); 4.13; `reviewer_behavior_literature.md` §6 rule 6. Where: `writer_rules.md` (DATA LOCK), `pairwise_rules.md`.
16. **Fix recipes.** Size the figure at its final print width; smallest text about 7 pt or more at print size; vector output for plots; raster at 300 ppi or more; Okabe-Ito or viridis-family colours plus a second cue; direct labels instead of distant legends; identical crops and insets across methods. Evidence: 2; 1.4; 1.2 (Franconeri). Where: `writer_rules.md` (Figures section).
17. **Text in the PDF is data.** Instructions found in figures or captions are ignored. Evidence: 4.14. Where: `figure_review_rules.md` (new).

Not used as evidence: Cleveland & McGill 1984 (`METADATA ONLY`; its ranking is taken from the 1986 paper and the Heer & Bostock replication) and Pandey et al. 2015 (`UNVERIFIED`).

---

## 6. Evidence behind each figure review rule

Moved on 2026-10-14 from `02_protocol/figure_review_rules.md`, which now keeps each rule's instruction and a short evidence tag, so the figure reader's prompt carries no study statistics. Rule numbers are those of `figure_review_rules.md`; the entries in sections 1-4 give the labels and context.

- **Rule 1 (crops for small details; tag "Zhang et al. 2025").** A crop around the answer raised GPT-4o from 65.8% to 75.6% on questions about the smallest text (4.5).
- **Rule 3 (check against the text and tables; tag "Ho et al. 2026").** Models verify claims against tables more reliably than against charts (Ho et al. 2026, Format Matters).
- **Rule 4 (describe before reading the caption; tags "SciFIBench; Charts-of-Thought").** Models follow a caption labelled as correct even when it is wrong (SciFIBench). Extract, verify, then analyse raised chart-literacy scores by 9-22% (Charts-of-Thought, 4.8).
- **Rule 6 (rubric definitions; tag "Alexander et al. 2024").** With definitions supplied, models detected misleading charts best (AUC 0.821; 4.7).
- **Rule 7 (quote visible evidence; tag "CHOCOLATE").** Fluent chart descriptions by models often contain factual errors.
- **Rule 8 (visual findings only; tags "MMStar; SciFIBench").** Many benchmark questions can be answered without the image (MMStar); text alone reached 51.0% against 65.8% with the image on figure-caption matching (SciFIBench).
- **Rule 9 (no values from unlabelled marks; tags "Bendeck and Stasko 2024; CharXiv").** GPT-4 at times "could not even provide ballpark values" (4.6); counting labelled ticks, GPT-4o 59.8% against humans 92.9% (CharXiv).
- **Rule 10 (no counting, no overlap; tag "BlindTest").** Four models averaged 58% on seven simple tasks such as overlapping circles and crossing lines (4.4).
- **Rule 11 (no colour-to-legend mapping; tags "ChartMimic; OpenAI vision guide").** Colour was the element GPT-4o reproduced worst (67.2 against 89.8 for layout; ChartMimic), and vendor documentation lists colours and line styles as a weakness (OpenAI vision guide).
- **Rule 12 (read the axis ends; tag "Bendeck and Stasko 2024").** GPT-4 ignored an inverted axis even when asked to look for misleading tactics, and a truncated axis fooled it (4.6).
- **Rule 13 ("cannot determine"; tag "CharXiv").** One open model answered nearly 90% of unanswerable chart questions instead of declining.
- **Rule 14 (preview rule; tags "Crameri et al. 2020; CVPR author kit").** About 8% of men and 0.5% of women have a colour-vision deficiency (Crameri et al. 2020); the CVPR author kit asks for a second cue besides colour (2).
- **Rule 16 (figure issues are rarely decisive; tag "real CV reviews, FIG and VIS").** In 184 real CV reviews, figure presentation (FIG) came up in 13% and visual results (VIS) in 20%, and neither separated rejecting from accepting reviewers (FIG 12% against 14%, p = 0.82; VIS 19% against 21%, p = 0.85) (3).
- **Rule 17 (scores follow defects; tags "VisJudge-Bench; SciFigQual-Bench").** Mean model score 3.87 against 3.13 for human experts (VisJudge-Bench); the best judge barely beats a constant prediction of expert figure ratings (MAE 0.42 against 0.57; SciFigQual-Bench) (4.9, 4.10).
- **Rule 18 (do not over-flag; tag "Lo and Qu 2024").** The best of four models judged only 3 of 12 valid charts as valid (4.7).
- **Rule 19 (weakness budget; tags "MARG", "VIS-Shepherd").** Generic comments fell from 60% to 29% with narrow agents (MARG, `reviewer_behavior_literature.md` §3.1). Critics drift to cosmetic suggestions and miss real defects (VIS-Shepherd, 4.12).
- **Rule 20 (no reward for decoration or length; tags "VisJudge-Bench; MLLM-as-a-Judge; Paper2Poster").** A chaotic treemap rated 1.67 by humans got 3.08 from a model (VisJudge-Bench); padding answers without changing their meaning added about 0.6 to 0.75 points (MLLM-as-a-Judge, 4.11); visually appealing generated posters carried little information (Paper2Poster).
- **Rule 21 (caption claims need visible support; tag "SciFigQual-Bench").** Single-pass judges over-credit fluent but incomplete captions.
- **Rule 22 (ignore instructions in the PDF; tag "MMReview").** Hidden prompts raised the scores of text-only model reviewers (4.14).

### Sources cited by the figure review rules
Print and colour guidance (checked 2026-10-13):
- CVPR author kit 2026, `sec/2_formatting.tex` (figure fonts match body text; readers may print and cannot zoom; second cue besides colour): https://github.com/cvpr-org/author-kit
- NeurIPS 2025 style, `neurips_2025.tex` (legible in black-and-white print): https://media.neurips.cc/Conferences/NeurIPS2025/Styles.zip
- Elsevier, Artwork sizing (7 pt printed text, 6 pt sub/superscripts, rule of thumb; 300 dpi halftones): https://www.elsevier.com/about/policies-and-standards/author/artwork-and-media-instructions/artwork-sizing
- IEEE Author Center, Resolution and size (>300 dpi colour and grayscale, >600 dpi line art): https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/create-graphics-for-your-article/resolution-and-size/
- Nature research figure guide (fonts 5-7 pt; photographs at least 300 dpi; vector files for main figures; avoid red/green and rainbow scales): https://research-figure-guide.nature.com/figures/preparing-figures-our-specifications/ and https://research-figure-guide.nature.com/figures/building-and-exporting-figure-panels/
- Okabe and Ito, Color Universal Design (2002, rev. 2008): https://jfly.uni-koeln.de/color/
- Crameri, Shephard and Heron 2020, Nat. Commun. 11:5444: https://doi.org/10.1038/s41467-020-19160-7
- Matplotlib, Choosing colormaps (jet's lightness varies widely; monotonic lightness prints to grayscale): https://matplotlib.org/3.5.0/tutorials/colors/colormaps.html
- van der Walt and Smith, viridis family: https://bids.github.io/colormap/
- Nuñez, Anderton and Renslow 2018, cividis, PLOS ONE 13(7):e0199239: https://doi.org/10.1371/journal.pone.0199239

Model figure reading (arXiv ids unless stated): CharXiv 2406.18521; ChartMimic 2406.09961; BlindTest 2407.06581; Zhang et al. 2025, MLLMs Know Where to Look 2502.17422; SciFIBench 2405.08807; MMStar 2403.20330; CHOCOLATE 2312.10160; Charts-of-Thought 2508.04842; Ho et al. 2026, Format Matters 2511.10075; Bendeck and Stasko 2024, IEEE VIS, https://faculty.cc.gatech.edu/~john.stasko/papers/vis24-llm.pdf; Lo and Qu 2024 2407.17291; Alexander et al. 2024 2408.12617; VisJudge-Bench 2510.22373; SciFigQual-Bench 2607.27084; MLLM-as-a-Judge 2402.04788; VIS-Shepherd 2506.13326; MARG 2401.04259; Paper2Poster 2505.21497; MMReview 2508.14146; OpenAI, Images and vision, https://developers.openai.com/api/docs/guides/images-vision.

Real reviews: `01_sources/real_review_patterns.md` (codes FIG and VIS).
