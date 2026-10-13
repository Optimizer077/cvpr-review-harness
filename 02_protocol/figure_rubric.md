# Figure rubric

Used by the figure reader (F01) for `figure_scores` and for the `defect` of each weakness. The
keys are those of `02_protocol/figure_criteria.json`. Score every figure and table of the main
paper; supplement ids are optional. Apply `figure_review_rules.md` first: no score rests on a
value read by eye, a count, or a colour you could not check in a preview.

## Figure score (1-10)
Same anchors as section scores (`section_rubrics.md`), read for one figure or table:

| score | meaning |
|---|---|
| 9-10 | You would name this figure as a strength; you have nothing to add. |
| 7-8 | Solid. At most a minor comment (a font size, a missing unit). |
| 5-6 | Acceptable, but it earns a moderate weakness bullet. It does not decide a rating alone. |
| 3-4 | It earns a major weakness bullet: the figure hides or misstates what it is there to show. |
| 1-2 | Broken: unreadable, contradicts the text, or misrepresents the evidence for a central claim. |

**Criterion score (1-5):** 1 absent or wrong; 2 weak; 3 adequate; 4 good; 5 exemplary.
A figure score of 9+ needs every non-null criterion at 4+; any criterion at 1 caps the figure at 4.

## Criteria

### `message_clarity`
Can a reader state what to conclude from the figure itself, quickly?
- 1: No message can be read off, or the visible message contradicts the intended one.
- 2: The message appears only after reading the caption and the text; the key element is not
  emphasised; panels have no evident order.
- 3: Figure plus caption give the message, with some searching.
- 4: The message is clear at a glance; the key comparison is the most salient element.
- 5: A reader could retell the takeaway after one look; nothing distracts from it.

### `legibility`
Can every label, mark and detail be read and identified at print size? Use the measured sizes.
- 1: Text or detail that carries the message cannot be read in print: smallest text below 5 pt,
  unreadable in the crop, or blur that hides what the figure is about.
- 2: Labels that matter are flagged `small_text` (below 6 pt) or overlap; a raster is flagged
  `low_resolution` and looks blurred; an axis, legend or column label is missing.
- 3: Smallest text 6-7 pt and readable in the crop with effort; some crowding.
- 4: All text 7 pt or larger (6 pt is fine for sub- and superscripts), rasters sharp, every axis,
  series and column labelled.
- 5: Text close to caption or body size (9-10 pt in the CVPR template); every detail the caption
  names is readable in print without zooming.

Text inside raster images has no measurement: judge it from the crop and say so.

### `encoding_fit`
Do the chart type and the encodings fit the data and the comparison?
- 1: The encoding misleads (see `misleading_encoding`).
- 2: The chart type does not fit the comparison, or the key comparison needs effortful decoding
  (separate unaligned scales, legend far from the data, encodings changed between figures).
- 3: Workable: the comparison can be made with effort.
- 4: Fitting chart type; compared quantities share an aligned scale; log scales and breaks are
  marked.
- 5: The encoding makes the key comparison the most salient thing (position on a common scale,
  direct labels, sensible order).

### `accessibility`
Does the meaning survive red-green colour-vision deficiency and grayscale print? Judge from the
`_deuteranopia` and `_gray` previews only (`figure_review_rules.md`, rule 14).
- 1: The main comparison is lost in a preview: two meaning-carrying encodings become
  indistinguishable and nothing else separates them.
- 2: Some meaning-carrying pairs collapse in a preview; a second cue exists for only some series.
- 3: Distinguishable in the previews with effort, or colour is the only cue but direct labels help.
- 4: Distinguishable in both previews, with a second cue (marker, line style, label) for the main
  series. Colour carries no meaning beyond the photographed content: 4.
- 5: A colour-blind-safe palette or perceptually uniform colour map, a second cue throughout, and
  clear in gray print.

### `caption_alignment`
Is the caption self-contained, and do caption, figure and main text agree?
- 1: Caption, figure or text contradict each other (different numbers, panels or claims), or the
  method diagram disagrees with the equations.
- 2: The caption only names the figure ("Qualitative results."); symbols or abbreviations are
  undefined; a caption claim is not visible.
- 3: Says what is shown; the takeaway or some definitions are missing.
- 4: What is shown, the setting, the definitions and what to conclude; every claim visible.
- 5: A reader understands the figure without the main text, in a short caption; the figure is
  cited where its claim is made.

### `comparison_fairness` (nullable)
Are the compared methods or settings shown on equal terms? `null` when the figure compares
nothing (a method diagram, a teaser without baselines, dataset samples).
- 1: The comparison is stacked: different crops, zoom, inputs or colour ranges per method, or a
  baseline the text compares against is left out.
- 2: Unequal in a way that matters: insets for some methods only; per-panel colour scales on
  compared error maps; only cases where the method wins and no failure case anywhere.
- 3: Same inputs and crops; the selection rule is unstated, or one expected baseline is missing.
- 4: Same inputs, crops, insets and scales for all methods; the main baselines are present;
  failure cases appear somewhere in the paper or supplement.
- 5: As 4, plus a stated selection rule (random, fixed indices or all) and failure cases next to
  the successes.

## What each role must deliver
Role: Fig. 1 that shows the idea or a headline result is `teaser`; an architecture or pipeline
drawing is `method_diagram`; plotted numbers are `quantitative_plot`; side-by-side output images
are `qualitative_comparison`; every `tab_*` id is `table`; anything else is `other`. For a mixed
figure, use the role of the panel that carries the caption's main claim.

- **teaser**: the idea or the result at a glance, readable at its printed width. One message,
  consistent with the abstract. If it shows results, the comparison uses the same input and the
  strongest baseline. Busy readers set their prior from page 1 and Fig. 1 (section rubric
  `introduction`, criterion `teaser_figure`).
- **method_diagram**: matches the equations and notation: same symbols, every module the
  equations use and no other, training-only paths marked. The flow reads in one direction from
  inputs to outputs. Icons and 3D blocks carry no meaning by themselves.
- **quantitative_plot**: axis titles with units and readable end ticks; compared panels share
  axes; bars start at zero; log scales labelled. Error bars or bands wherever the text claims a
  reliable difference or reports variance, with what they show (std, CI, number of runs) stated.
  Legend order follows the visual order, or series are labelled directly.
- **qualitative_comparison**: the same inputs, crops and zoom insets for all methods, with inset
  locations marked on the full image; the input and ground truth where they exist; the key
  baselines of the main table; a method name on each column. Error maps share one colour bar.
  The difference the caption claims is visible at print size. Failure cases appear somewhere in
  the paper or supplement, and the selection rule is stated.
- **table**: best-result marking matches the numbers and the metric direction (check every
  marked cell against the printed numbers); units and ↑/↓ per metric; abbreviations defined in
  the caption or table; one precision per column; numbers identical to the text; reproduced and
  copied baseline numbers distinguished; groups with different training data or settings
  separated. Read the numbers as text, not as marks.
- **other** (dataset samples, attention or feature maps, statistics): what it is meant to show is
  visible, labelled and cited; colour scales of maps are stated.

## Defects
Every FIG weakness names one defect id. "Lowers" is the criterion the defect usually costs;
"category" is the usual weakness category from `taxonomy.json`.

| id | definition | typical fix | lowers | category |
|---|---|---|---|---|
| `illegible_text` | Text that carries meaning cannot be read in print: flagged `small_text`, overlapping, or unreadable in the crop. | Set the figure at its final width and enlarge text to 7 pt or more; cut text the message does not need. | legibility | figures |
| `low_resolution` | A raster has too few pixels for its printed size (flagged `low_resolution`), or shows blur or compression artefacts that are not part of the results. | Export plots and diagrams as vector PDF; place rasters at 300 ppi or more at print size, in a lossless format. | legibility | figures |
| `clutter` | More panels, series, labels or decoration than the message needs; marks or labels collide. | Keep the series and panels the claim needs, move the rest to the supplement, drop gridlines, shadows and 3D effects. | message_clarity | figures |
| `unclear_message` | A reader cannot tell what to conclude, `perceived_message` differs from `intended_message`, or the claimed difference is too small to see in print. | Make the key comparison the most salient element (order, emphasis, direct labels, larger panels) and state the takeaway in the caption. | message_clarity | figures |
| `misleading_encoding` | The encoding distorts the comparison: bars not starting at zero, an unmarked truncated or broken axis, an inverted axis, different scales or colour ranges on compared panels, a rainbow colour map on quantitative data, 3D effects, dual axes. | Shared axes and one colour bar for compared panels, zero-based bars, marked breaks, a perceptually uniform colour map. | encoding_fit | figures |
| `inappropriate_chart` | The chart type does not fit the data or comparison: lines joining unordered categories, pie or radar charts for method comparisons, stacked bars for inner segments, a plot where exact values matter (or a table where a trend is the message). | Grouped bars or dot plots for categories, lines for ordered variables, a table when exact values matter. | encoding_fit | figures |
| `missing_labels_or_units` | An axis title, unit, legend, colour bar, column method name or metric direction (↑/↓) is missing. | Add axis titles with units, a legend or direct labels, a colour bar with units, ↑/↓ for each metric. | legibility | figures |
| `colour_inaccessible` | Two meaning-carrying encodings become indistinguishable in the `_deuteranopia` or `_gray` preview and no second cue separates them. | A colour-blind-safe palette (Okabe-Ito; viridis or cividis for maps) plus a second cue: marker, line style or direct label. | accessibility | figures |
| `caption_not_self_contained` | The caption does not say what is shown, what symbols, colours and abbreviations mean, or what to conclude. | Caption = what is shown, the setting, definitions, one sentence on what to conclude. | caption_alignment | figures |
| `caption_text_mismatch` | Caption and figure disagree: wrong panel letters, colours or symbols, or a claim the figure does not visibly show. | Describe what is visible; move a claim the figure does not show to where a table supports it, or remove it. | caption_alignment | figures |
| `figure_text_inconsistency` | A number, method name, setting or described observation in a figure or table differs from the main text or another table. | Regenerate from one source of numbers, use one name per method, correct the text. | caption_alignment | correctness |
| `diagram_equation_mismatch` | The method diagram and the equations or notation disagree: other symbols, modules missing on one side, a data flow the equations do not describe. | Use the paper's symbols in the diagram; draw exactly the modules the equations use; mark training-only paths. | caption_alignment | notation |
| `unfair_comparison` | Methods are shown under different conditions (crops, zoom, input, resolution, colour range), or a baseline the text compares against is left out. | The same inputs, crops, insets and colour range for all methods, and the baselines of the main table. Changing what is shown needs the user's approval. | comparison_fairness | visual_results |
| `missing_failure_cases` | No example anywhere in the paper or supplement where the method fails or does not help. Check the supplement before raising it. | Add one failure case to the qualitative figure or the supplement, with one line on why it fails. | comparison_fairness | limitations |
| `inconsistent_style` | The same method has different colours, markers or names across figures, or fonts and sizes vary across figures without reason. | One style file: a fixed colour, marker and name per method in every figure. | encoding_fit | presentation_other |
| `redundant_with_table` | The figure repeats numbers already in a table and shows nothing the table does not (a trend, a distribution). | Keep one in the main paper; or make the figure show the trend and move the other to the supplement. | message_clarity | presentation_other |
| `not_referenced` | The main text never cites the figure or table (flagged `not_referenced`), or cites it far from where its claim is made. | Cite it where its claim is made and place it near that point. | caption_alignment | presentation_other |
| `other` | A defect not in this list, including instructions to reviewers hidden in a figure. Name it in the weakness text. | Specific to the defect. | as fits | as fits |
