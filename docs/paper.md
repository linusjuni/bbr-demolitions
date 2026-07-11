# Paper plan — what to put in the article (not the article itself)

Target journal: **Journal of Building Engineering (JOBE)**, Elsevier. This file is a
build-list for the manuscript: the framing, the claims, the sections, and what still has
to be computed before each can be written. It is guidance, not prose.

Companion docs: `docs/indicators.md` (the D1–D7 definitions + KMD reproduction),
`docs/ablation.md` (the pipeline), `docs/plan.md` (the original research plan).

## Scope & positioning (settle first, it drives everything)

The paper is an **ablation / sensitivity study**: enumerate the defensible ways to define
a demolition in BBR, hold everything else fixed, swap only the indicator, and report the
consequence for national estimates — then discuss. It is **not** a "best indicator" paper
(there is no gold label) and **not** a reproducibility note about KMD (that is one
supporting result, not the thesis).

**JOBE fit is proven, not assumed.** Andersen & Negendahl (2023), *Lifespan prediction of
existing building typologies*, was published in JOBE and *used* the opaque KMD demolition
indicator. So building-stock / service-life / demolition work is in scope, and this paper
positions directly against an in-journal paper whose input it stress-tests.

**JOBE's gate — two risks to neutralize on page 1:**
- *"significant scientific novelty clearly demonstrated"* → sell the **finding** (the
  sensitivity magnitude), not the method. An ablation reads as routine unless the headline
  number is up front.
- *"a validation anchor"* → this is a descriptive study, not a model, so name the anchors
  explicitly: KMD (reproduced reference) and BOSSINF (authoritative truth slice). Without a
  truth anchor a reviewer will call every indicator an unvalidated proxy.

## Novelty positioning — verified against the literature (12-query search + the PhD)

The novelty claim survived a deep literature check (English + Danish; adjacent registers
Finnish BDR / Dutch BAG / Zurich; the method literature; 2025–26 papers). **No published
study systematically quantifies how the choice of BBR demolition indicator propagates to
national estimates.** Every prior study commits to a *single* indicator and never tests
sensitivity to it:

- **BUILD (2025)** *Omfanget* / *Analyse af BBR-data for udgået byggeri* — `udgået` only.
- **Andersen & Negendahl (2022 / 2023 JOBE)** — the KMD extract, taken as given.
- **Rune Andersen PhD (DTU 2023)** — *confirmed by reading its demolition chapter*: uses the
  **single** KMD "registered as demolished" annual list; the three demolition dates (applied
  / approved / completed) are used only for *dating*, never as competing indicators. No
  `status=10` vs `process=3` vs `sagstype` comparison, no sensitivity test.
- **Cross-city lifetime studies** (Berglund-Brown et al. 2025 *Buildings & Cities*;
  Cord'homme 2025 *JIE*) — demolition register data, lifetime = one value, no indicator axis.

Three facts nail the gap: (1) the **multiverse / specification-curve** method has never been
applied to building stock / demolition / MFA — so the *framing* is new to the field; (2)
register work that "compares" compares *sources* (Huuhka: Finnish national vs local), not
*indicator definitions* within one register; (3) **Danmarks Statistik states there is no
official Danish demolition statistic** — the definitional question is officially unsettled.

**The one precedent to cite and distinguish:** the DTU thesis "When Buildings Die" (#3)
informally tried `Business Process=3` and `status=10 ∩ BP3` and rejected them before settling
on `status=10` — a within-study *justification* of one choice, not a systematic, downstream-
propagated sensitivity study. So "first" holds for *published, systematic quantification*.

**Reviewer-proof wording (use verbatim in the intro):**
> "To our knowledge, no published study has **systematically quantified** how the choice of
> demolition indicator in BBR propagates to national demolition estimates. Prior work each
> adopts a **single** indicator — `udgået`, `status=10`, or the pre-made KMD extract — without
> testing the sensitivity of results to that choice."

Do **not** write a bald "first"; the scoped wording above is what the evidence supports.

## The contribution — three claims, in this order

State these explicitly in the introduction and mirror them in the conclusion. Framed as
consequence + decision rule, not "we did an analysis."

1. **Quantified sensitivity (headline / novelty).** First systematic quantification of how
   the choice of BBR demolition indicator changes national demolition estimates — an
   **[X]-fold** range in annual demolished area (and demolition rate) over the shared
   window from seven defensible, transparent definitions. *The number is the novelty; the
   contribution paragraph cannot be written until it exists (see "Blocking analysis").*
2. **A transparent, reproducible indicator set** (D1–D7 + the discontinued-code axis) that
   replaces the opaque KMD extract the field currently reuses — including the demonstration
   that KMD is itself reproducible (`sagstype = 32`) and marginally noisier than a
   documented case-based alternative. Supporting result, not the thesis.
3. **A practitioner decision framework** — when each indicator is appropriate, and the
   standing recommendation to report indicator sensitivity rather than a single number.

## Practitioner impact (the section generic papers fail)

Audience: **LCA analysts, building-stock / material-flow modelers, municipal & BBR data
users.** Put implications *before* recommendations, at the **end of the Discussion**, ahead
of the conclusion. Be specific; ban "more research is needed."

Implications to state:
- Picking `status=10` vs a demolition-case indicator changes the demolition **rate by ~2×**,
  which **propagates into building-lifespan / survival and embodied-carbon estimates** — the
  JOBE-relevant downstream consequence, and exactly what paper #8 computed from KMD.
- The widely-reused KMD/Andersen extract is a `sagstype=32` proxy with **unpublished
  filtering**; anyone inheriting it inherits ~0.3% register-exit noise and a fixed
  2000–2020 window.
- Area estimates are **doubly sensitive** — to indicator *and* to area column — and the
  column the field reports (etageareal / total floor area) is missing for ~54% of
  demolished buildings, so a bare national m² total silently covers ~46% of buildings.

Recommendations to state:
- Report results under **≥2 indicators** (one over-counting, one under-counting) as a
  sensitivity band; never a single headline number.
- State the **operational definition explicitly** (which field, which window).
- Prefer the **documented case-based indicator** (`sagstype=32`) over the opaque extract;
  report **area coverage %** alongside any m² total.

## Suggested manuscript structure

Standard JOBE research-article shape; map our assets onto it.

1. **Introduction** — BBR has no clean demolition flag; the field reuses proxies (esp. the
   opaque KMD extract, incl. in JOBE); state the three contribution claims + the headline
   number.
2. **Background / the register mechanism** — from `indicators.md`: the real Sagstype-31/32
   + felt 294/295 chain, and why felt 295 is absent from the public feed (this is *why* a
   proxy zoo exists — it motivates the whole study).
3. **Data** — the Datafordeler extract (6.25M buildings, temporal history, 2017 floor,
   backdated virkningFra), plus the KMD extract and BOSSINF as external anchors.
4. **Methods — the indicator set** — D1–D7 + discontinued-code axis; the held-fixed
   confounds (window, partial-vs-total, building filters); the area definitions + coverage
   reporting; complete-case handling matched to the papers.
5. **Results**
   - Indicator overlap / disagreement (overlap heatmap; D1↔D2 = 0.18).
   - **Outcome × indicator range — the headline** (counts, demolished m² under 3 area
     defs, demolition rate vs stock; the [X]-fold spread).
   - Annual trends by indicator.
   - The discontinued-code axis: 31% of count but 80% of area.
   - External-anchor validation: KMD reproduction (`sagstype=32`, ~99% window-matched) and,
     if obtained, BOSSINF precision/recall.
6. **Discussion** — what the disagreements mean; which indicator fails where; the area
   sensitivity; then **implications → recommendations** (above).
7. **Conclusion** — restate the three claims and the headline number.

## Figures / tables (the 6–8 core outputs)

Have already (from `results/`): overlap heatmap; annual counts by indicator; annual
demolished floor area by indicator; area-definition sensitivity bars; per-variant summary
table; KMD comparison + disagreement profile tables.
Still to build: **outcome × indicator range table/figure** (the headline); demolition-rate-
vs-stock figure; BOSSINF precision/recall (if data obtained); typology/region breakdown.

## The rate-vs-stock benchmark to reproduce (from the Rune PhD)

The Rune PhD hands us the exact anchor for the headline. Reproduce it, then show the
indicator band around it:

- **Denominator: Statistics Denmark BYGB34** — annual existing-stock floor area by
  municipality × building use × construction period. This is the stock denominator to use
  (same as the PhD and Andersen 2023), so our rate is directly comparable to theirs.
- **Benchmark figure: ~0.26% of stock floor area demolished/yr (2010–2019)** under the KMD
  indicator (housing lowest ~0.11%, manufacturing/childcare highest ~0.4–0.57%; agriculture
  ≈ a third of demolished m²). BUILD's `udgået` gives ~0.3%. These are the reference points.
- **The headline sentence writes itself:** "under the KMD / `sagstype=32` indicator we
  replicate ~0.26%; swapping to `status=10` gives ~X%, to `process=3` gives ~Y%" — an
  [X]-fold spread around a number a JOBE reviewer already trusts.
- **Bonus — KMD's filtering is now partly de-opaqued** (from the PhD funnel): 152,288
  (2000–2020) → drop 28,204 undatable → 124,084 → window 2010–2019 → 117,694. So the recipe
  is "drop undatable + window 2010–2019"; the datability rule is still fuzzy and explains
  part of the ~1% D4-vs-KMD gap. State this in the KMD section.
- **Provenance confirmed:** the PhD's 152,288 cases = our `andersen_raw.csv` (152,300) — same
  file, so "the Andersen & Negendahl / KMD extract" can be stated as fact, not inference.

## Blocking analysis (must exist before the contribution can be written)

1. **Outcome × indicator range** — reduce the per-variant outputs to a min–max spread for
   (a) national demolished m²/yr and (b) demolition rate vs building stock, over the shared
   window. This produces the "[X]-fold" novelty sentence. **Highest priority.**
2. **Demolition rate vs stock** — needs the **BYGB34** denominator (above); target is to
   reproduce the PhD's **~0.26%** under the KMD/`sagstype=32` indicator, then report the
   spread across the other indicators.
3. **BOSSINF acquisition + scoring** — the only authoritative precision/recall; the JOBE
   validation anchor. Data-acquisition task, likely lead time — start now.

## Explicitly out of scope (say so, to pre-empt reviewers)

Not a "correct demolition status per building" claim; not a new demolition-detection model;
not a critique that BUILD/Andersen are "wrong" — the point is that indicator choice is
consequential and must be reported, not that any prior number is invalid.
