# Demolition indicators across the papers

BBR has no clean "demolished" flag, and there is no canonical demolition signal —
confirmed in our own dialogue with BBR staff, who could not point to a single
authoritative field. **Every method below is a proxy.** Each paper picks a
register event (or receives a pre-made extract) and adds filters to remove false
positives. The "official extracts" are *not* an exception: it is different organisationss own proxies, built on the same ambiguous register events, with a filtering recipe they never
published — opaque rather than authoritative. So this document is a comparison of
proxies, not proxies-versus-truth. Below is exactly what each paper used, quoting
the explicit method where they state one.

## Full table

| # | Paper | Demolition indicator (explicit method) | Filters added | Notes |
|---|-------|----------------------------------------|---------------|-------|
| 1 | **Andersen & Negendahl (2022)** — *Adaptation of circular design strategies…* (SBE22-Delft, IOP 1085) | **Pre-made KMD extract.** The BBR administrator (KMD) produced an extract of "all demolition cases reported by municipalities." 152,300 demolition cases, Feb 2000 – Jun 2020. | Discard pre-2011 (too many registration errors before then) | **Not ground truth — an opaque proxy.** KMD's extract rests on the same register events (`Status=10`/`udgået`/`Business Process=3`) as the transparent proxies, but its filtering recipe is unpublished, so it can't be reproduced or audited. Both #2 and #3 inherit this dataset. |
| 2 | **Droob & Nybroe (2024 thesis → 2026 IOP paper)** — *Building Service Life Revised* | **`Business Process (Forretningshændelse) = 3`** = "update due to demolition." *(Stated in the 2024 thesis and attributed to them by paper #4; the 2026 conference paper only says "BBR demolitions 2017–2024" + Andersen's dataset.)* | Remove outbuildings | Merges Andersen's dataset (#1) with public BBR 2017–2024. Real novelty is left-censoring, not the indicator. |
| 3 | **When Buildings Die** (DTU thesis) | **`Status = 10`** ("historisk"). Demolition year = `Effect From` of first `Status=10` record. Tried `Business Process=3` and `Status=10 AND Business Process=3` first, rejected both for undercounting. | Remove discontinued/outdated use-codes (re-registration artefacts, gave >90% fake demolition rates) | Also merges Andersen's dataset (#1) as a supplementary source. Prefers slight overcount over undercount. |
| 4 | **Omfanget af nedrivning 2012–2023** (AAU/BUILD 2025) | **`"udgået"`** (retired from BBR, field `ObjStatus`). | Only buildings built before 1999 (newer "udgået" were mostly status errors) | ~2.2 mio m²/yr ≈ 0.3% of stock. Assumes "udgået" ≈ demolished. |
| 5 | **Nedrivning af enfamiliehuse** (BUILD 2022:36) | **"Riv-ned-byg-nyt" change detection**, two methods: (D1) building code 120 changes construction year to a recent year AND changes living area; (D2) building marked "udgået" AND a new building built after 2010 on the same matrikel. | code 120 only; same-matrikel; rebuild after 2010 | Only catches demolition *with* a rebuild. Two methods converge at ~1,000 houses/yr. |
| 6 | **Vurdering af landsbyfornyelse** (SBI 2019) | **Two sources:** (a) **BOSSINF** = official register of grant-funded demolitions (ground truth, but only subsidised cases); (b) **`"udgået"`** in BBR (fields `ObjStatus` + `Ophoert_ts` for date). | Residential codes only (stuehus/parcelhus); 54 eligible municipalities | Uses BOSSINF to cross-check BBR. 193,326 "udgået" in BBR total; 19,640 residential. |
| 7 | **Østergaard et al. (2018)** — *Data driven quantification of the temporal scope of building LCAs* (DTU/AAU, Procedia CIRP) | **BBR extract of "buildings demolished 2009–2015."** Method *not* explicitly stated — records were simply "collected by BBR." Reason for demolition explicitly noted as not recorded in BBR. ~26,320 records. | Drop missing/duplicate records; lifespan < 5 yrs; built before 1800 → 20,999 kept | Administrative extract (unspecified how the extract was made). Earliest and vaguest of the extract papers. |
| 8 | **Andersen & Negendahl (2023)** — *Lifespan prediction of existing building typologies* (J. Building Eng.) | **Reported-demolition list merged with historical BBR.** Owner reports demolition to municipality → building is deleted from BBR → merge the annually-reported demolition list with the stored historical BBR records for those buildings. 124,096 cases 2007–2020. | Drop missing demolition-date/area/use; drop pre-2010 (BBR restructuring); strip auto-generated GIS/satellite buildings (construction year = "1000") → 104,927 (2010–2019) | Administrative extract — **same family as #1** (sibling paper, same author, spells out the merge recipe #1 uses). |
| 9 | **Marc Lund Andersen / Boligøkonomisk Videncenter (2023)** — *Karakteristika for huse der rives ned med henblik på nybyggeri* (teardowns) | **Property-transaction change-detection.** From OIS sales data: a *sale* of a single-family house (code 120) where a new single-family house appears on the plot within 0–3 years of the sale. | Arms-length "frie handler" only (exclude forced auctions, family transfers); plot 500–2,000 m²; price 15–15,000 kr/m²; matrikel created ≥20 yrs before sale (kills subdivisions/development projects); regional price-outlier removal → 7,311 → 3,025 teardowns (2013–2020) | Catches teardown-with-rebuild only, and requires a sale. Same idea as #5 but triggered by a transaction, not a BBR flag. |
| 10 | **Aagaard, Brandt, Aggerholm & Haugbølle / SBi (2013)** — *Levetider af bygningsdele ved vurdering af bæredygtighed og totaløkonomi* | **Not a demolition-detection method.** Uses an assumed aggregate demolition *rate* (~0.3 %/yr, ≈ the 1994–2012 average) derived from construction-cost statistics (Dansk Byggeri: demolition ≈ 2–4 % of building spend → ~2 mio m²/yr on 660 mio m² stock), fed into a mean-time-to-failure/survival model to set "standard" lifespans (e.g. housing 120 yr). | n/a | Not a proxy signal — a rate assumption. This is the "Danish standard lifespan" **baseline** that #2, #7, #8 benchmark against. |

## The kinds of indicator

1. **Pre-made / opaque extract (a proxy, not truth):** Andersen/KMD extract (#1, national), the reported-demolition-list-merged-with-historical-BBR recipe (#8, same family as #1; #7 is the same idea but doesn't say how the extract was made). These rest on the same register events as categories 2–3, but with someone else's undocumented filtering. **BOSSINF (#6) is the one genuine ground truth here — but only for grant-funded demolitions**, so it can't stand in for the national picture.
2. **Register-exit proxy:** `Status=10` (#3) and `"udgået"`/`ObjStatus` (#4, #6) — the same underlying signal, different field names across BBR versions.
3. **Event-code proxy:** `Business Process = 3` (#2).
4. **Change-detection proxy** — catches demolish-and-rebuild only, in two flavours by what triggers it:
   - **BBR-flag-based:** riv-ned-byg-nyt via a status/use-code change on the same matrikel (#5).
   - **Transaction-based:** a property *sale* followed by new construction within 0–3 years (#9, OIS data).

**Not an indicator — a baseline:** #10 (SBi 2013) detects no individual demolitions; it assumes an aggregate rate (~0.3 %/yr) from cost statistics to set the "standard" Danish lifespans. It's the fixed-lifespan reference the extract papers (#2, #7, #8) try to beat, not a competing signal.

## Tradeoff

- Register-exit (`Status=10` / `udgået`) **overcounts** — catches re-registrations and admin changes, not just physical demolitions.
- Event-code (`Business Process = 3`) **undercounts** — many real demolitions never get the code.
- Change-detection catches only **demolish-and-rebuild**, misses demolition-with-no-rebuild (rural depopulation, empty lots). The transaction-based variant (#9) misses further: it also requires a *sale* to have happened.
- Filters are the fix: drop discontinued codes (#3), pre-1999 only (#4), pre-2011 cutoff (#1), pre-2010 cutoff + strip "1000" auto-buildings (#8), residential-only (#6), matrikel age ≥20 yrs (#9).

## What BBR actually records (from BBR's own sources, not the papers)

Deep-diving BBR's own documentation (Instruks, Teknik kodelister, Datafordeler
grunddatamodel) reveals something the papers gloss over: **BBR *does* have a
purpose-built demolition mechanism.** The proxies aren't independent competing
definitions — they are different observable shadows of one underlying event chain.

The real chain, as BBR intends it:

1. **Demolition case opened** — a building-case (byggesag) with **Sagstype (felt
   290) = 3 "Nedrivning (hel eller delvis)"**; Byggesagskode (felt 292) = 2 for
   single-family (BR-S-anmeldelse) or 5 for other structures.
2. **Notification date** — **felt 294 "Anmeldelse af nedrivning, dato"**,
   generated automatically from the case date when the demolition case is created.
3. **Completion date** — **felt 295 "Gennemført nedrivning, dato"**: the date the
   owner/builder/authority states the building is *actually* (totally or partially)
   demolished. This is BBR's real "it happened" flag.
4. **Reporting felt 295 → the building is deleted from the master register
   (stamregister)** and removed from the change register, its lifecycle
   **status/livscyklus becomes 10 "Historisk"**, and it moves to the **BBR
   historical register**.

So the single cleanest indicator BBR offers is: **a demolition case (Sagstype=3)
that reached completion (felt 295 populated)** — equivalently, the status→10
Historisk transition that felt 295 triggers. That is a designed demolition flag,
not a proxy.

### The catch — and why every paper used a proxy instead

**The demolition *dates* are not in the public Datafordeler feed.** The distributed
`Bygning` object carries construction/renovation attributes (`byg026Opførelsesår`,
`byg027OmTilbygningsår`, …) but **no felt 294/295 and no plain demolition date.**

And a subtlety that trips people up: when felt 295 is reported the building exits the
**current-state view** (`stamregister` / "gældende") — so in a *current* snapshot a
demolished building **disappears**. But it is **not** purged from Datafordeler: in
the **bitemporal / temporal (all-status) view** it is retained as a record with
**`status = 10 Historisk`** plus registration/effect timestamps. So the building
leaves the *current* dataset, not the *temporal* one. Concretely: pull the
**temporal total download** (not a current snapshot), or demolished buildings won't
be there to detect at all. The old KMD-era operational register literally moved the
record to a separate historical register; Datafordeler grunddata instead models the
exit as a retained status transition — same concept, different plumbing.

That is the whole reason for the proxy zoo:

- **KMD/Andersen extract (#1/#8)** ≈ a compilation of the **historical register's
  completed-demolition records** — i.e. effectively felt 295 + Sagstype=3, but
  assembled by KMD with an unpublished recipe. This is *why* it feels closest to
  truth: it's the nearest thing to the real flag. It's opaque because KMD, not the
  researcher, did the felt-295 compilation.
- **`Status=10` / `udgået` (#3, #4, #6)** = the *downstream shadow* of felt 295 in
  a public all-status/historical snapshot — but status 10 is also reached by
  re-registration, merges and error-correction, hence the overcount.
- **`Business Process = 3` / Sagstype=3 (#2)** = the *upstream notification* side
  (the demolition case / felt 294), before completion — so it counts intent, not
  completed demolitions, hence mistiming/undercount. (Note: paper #2's
  "Forretningshændelse = 3" and BBR's Sagstype=3 "Nedrivning" share the code `3`;
  worth verifying against the thesis whether these are literally the same field.)

### How reliable is the KMD extract, really? (evidence, not vibes)

The KMD extract is **not** a curated quality-controlled dataset — it is the same
municipal-reported `udgået`/demolition-case data, compiled by the pre-Datafordeler
operator with an unpublished recipe. Authoritative sources say the underlying
signal is noisy and biased:

- **BUILD / Social- og Boligstyrelsen (2024–25)** state plainly that `udgået` is
  only *assumed* to mean demolition, and that the counts likely **overcount**:
  *"Udgået byggeri … betyder, at en given bygning … er udgået af BBR-registret,
  **formentlig** gennem nedrivning"*; *"det kan … **ikke udelukkes** at 'udgået' kan
  dække over andre årsager"*; and on the figures, *"de nedrevne arealer **formentlig
  er overvurderede** … data kan være **mangelfulde eller fejlbehæftede**."*
- **Rigsrevisionen (National Audit Office), *Beretning om BBR*** found BBR data
  quality **unsatisfactory** and **varying considerably between municipalities**,
  and told the ministry to map the errors and actively supervise operation/data
  quality. (Older report, ~2003 — the problem is structural and long-standing.)
- **The papers' own filtering is the tell:** #1 discards all pre-2011; #8 strips
  "1000" auto-buildings + pre-2010; #3 found discontinued use-codes gave **>90%
  fake demolition rates**; #4 found newer `udgået` was **mostly status errors**.

So the KMD extract's only real advantages over a fresh Datafordeler pull are
**national coverage** and **pre-2017 reach** — *not* accuracy. Treat it as a large,
opaquely-filtered proxy with error bars, not a gold label. A transparent
`status=10 ∩ sagstype∈{31,32}` signal we build and document ourselves is arguably no
less trustworthy.

### The demolition case: sagstype 31/32 (the current handle) vs felt 294/295 (gone from the feed)

Two register generations, easy to conflate:

- **Old BBR Instruks numbering:** felt 290 **Sagstype = 3 "Nedrivning (hel eller
  delvis)"** — a single code. Demolition dates were felt **294 "Anmeldelse af
  nedrivning"** and felt **295 "Gennemført nedrivning"**.
- **Current grunddata (what's distributed on Datafordeler):** the `Sagstype` code
  list renumbered and *split* it — **`Sagsniveau.sagstype = 31 "Nedrivning
  (delvis)"` and `32 "Nedrivning (hel)"`**. So paper #2's "Sagstype = 3" and the
  modern `31/32` are the *same concept* across register versions, not different
  signals.

**Do felt 294/295 still exist?** Yes in the *operational* register (still live in
the BBR Instruks, where caseworkers enter data) — but **no** in the distributed
grunddata: they are not exposed as attributes on `Bygning` or `BBRSag`. So you
**cannot** pull felt 295 from the Datafordeler extract. The demolition *case* is
still visible via **`Sagsniveau.sagstype ∈ {31, 32}`**; the completion *date* is not
a named field there.

### The indicator I'd propose

- **Datafordeler route (reproducible, 2017→now):** a building linked (via
  `Sagsniveau`) to a demolition case **`sagstype = 32` (hel/total)** that also went
  to **`Bygning.status = 10 Historisk`**. Add `sagstype = 31` (delvis/partial) only
  if you deliberately want partial demolitions. `sagstype 31/32` is cleaner than the
  older `byggesagskode` (2/5 `UDFASES`, 6) — it is directly semantic and splits
  partial vs total.
- **KMD / historical-register route (national, pre-2017):** the nearest thing to
  felt 295, but compiled opaquely by KMD — use as a caveated cross-check, not truth
  (see the reliability evidence above).

### What a full Datafordeler extract actually gives you (verified against the model)

We are pulling a full BBR from Datafordeler. Checked against the distributed
grunddatamodel, here is what that extract does and does not contain for demolition:

- ✅ **`Bygning.status` = 10 Historisk** — the register-exit signal, with temporal
  registration timestamps. **Registration history floor: `2017-06-02`** (BBR 1.8
  conversion); pre-2017 demolitions were deleted at conversion and are mostly
  unrecoverable here. So this extract is effectively a **2017→now** source.
- ✅ **`Sagsniveau.sagstype ∈ {31 delvis, 32 hel}`** = the demolition case, linked
  to the building. This is the primary handle. (`BBRSag.sag012Byggesagskode = 6`
  "Tilladelsessag Nedrivning" is a secondary/older regulatory categorisation; legacy
  `2`/`5` are `UDFASES` and noisy — code 2 mixes demolition with sheds/carports.)
- ❌ **felt 294/295 (Anmeldelse / Gennemført nedrivning) are NOT distributed** —
  absent from `Bygning`, `BBRSag` and `Sagsniveau`. The felt-295 "gold" completion
  *date* is not obtainable from Datafordeler; only the operational/historical
  register (KMD-style extract) or DST microdata has it.

**Best signal buildable from this extract:** `Bygning.status = 10 Historisk` ∩
`Sagsniveau.sagstype = 32`. Status-10 alone overcounts (re-registration/merge/error);
a demolition case alone overcounts intent (no completion visible without felt 295);
their intersection is the closest completion-proxy this dataset allows.

**RESOLVED against the extract (see implementation section below):** neither case
date is a usable completion date. `sag010FuldførelseAfByggeri` (the felt-295
candidate) is 65–95% null on demolition cases *and* semantically contaminated — the
case a 31/32 row links to is usually a co-filed `nybyggeri`/`til-ombygning`, so its
`sag010` is that rebuild's completion, not the demolition's. `sag002Byggesagsdato`
(≈ felt 294 notification) is the only well-populated date (~97% of linkable
buildings) but dates *notification*, not completion. So **felt 295 is not
reconstructable from this feed**; demolitions are dated either by `sag002`
(notification, our D7) or by the `status→10` `virkningFra` (register-exit, D1/D4–D6).

**Sources:** BBR Teknik kodelister (Livscyklus; **Sagstype 31/32**; Byggesagskode);
BBR Instruks §3.2.2 Bygningsniveau, felt 290/292/294/295, §7.6.10 Indberetning ved
nedrivning, §2.1.3 BBR-historisk register; Datafordeler grunddatamodel `Bygning` +
`BBRSag` + `Sagsniveau` objekttyper; Datafordeler Bitemporalitet (2017-06-02 floor).

## What to benchmark against

There is no gold label. We have Andersen's KMD extract on hand, but it is a proxy
with hidden filtering (see #1), so treating it as ground truth would just bake
KMD's undocumented choices into our "truth" and bias the ablation in its favour.

Better framing for the ablation:

- Compare the proxies **against each other** — where they agree, where they
  diverge, and *why* (what each over- or under-counts). The disagreements are the
  result, not noise to be resolved against a reference.
- Use the KMD extract (#1/#8) as **one transparent-ish reference point**, not the
  gold standard — useful because it's large and national, caveated because it's
  opaque.
- Use **BOSSINF (#6) as the only real ground truth**, on the slice where it
  exists (grant-funded demolitions). It's the one place we can actually measure a
  proxy's false-positive/false-negative rate against something authoritative.
- The **conceptual gold is felt 295 "Gennemført nedrivning"** (see section above).
  It's not in the public feed, but if we can get the historical register we should
  reconstruct it ourselves rather than trust KMD's opaque version — then all the
  public proxies can be scored against *our* reproducible felt-295 signal.

## Ablation scope

The point of the ablation is **not** to crown a single "best" indicator — there is
no gold label to crown it against. It is to make the **consequence of the choice
explicit**: swap only the demolition indicator, hold everything else fixed, and show
how the downstream results move. Disagreement between indicators is a result in
itself; the propagated effect on our actual output is the payload.

### Indicators to ablate

- **Single signals:** register-exit (`status = 10 Historisk`) alone · demolition
  case (`sagstype = 32` hel) alone · demolition case incl. partial
  (`sagstype ∈ {31, 32}`) · regulatory permit (`byggesagskode = 6`) alone.
- **Combinations:** `status = 10 ∩ sagstype = 32` (the recommended completion-proxy)
  · `status = 10 ∩ {31, 32}` · `status = 10 ∪ sagstype` (maximum recall).
- **Change-detection:** riv-ned-byg-nyt via BBR flags (#5) · teardown-by-transaction
  via OIS sales (#9, only if OIS is in scope).

### External anchors (references, not indicators)

- **KMD extract (#1/#8)** — a national, pre-2017 coverage cross-check, used with its
  reliability caveats, never as truth.
- **BOSSINF (#6)** — the one authoritative slice (grant-funded demolitions), used to
  read a real precision/recall on that subset.

### Confounds to hold fixed across every variant

If these vary they get confounded with the indicator choice, so freeze them (or make
one an explicit, separate axis):

- **Time window** — restrict to the shared 2017→now period (the Datafordeler
  registration-history floor); otherwise variants aren't comparable.
- **Partial vs total demolition** — decide whether `sagstype 31` is in or out once,
  or treat it as its own axis rather than letting it drift.
- **Pending vs completed cases** — *confirmed present*: the extract holds 547,844
  `sagstype 32` and 51,587 `sagstype 31` rows, so completed demolition cases are not
  purged from the temporal view. (Completion *dates* are still missing — see felt-295
  finding — but case *membership* is reliable.)
- **Building filters** — outbuildings, auto-generated "1000" buildings, and use-code
  restrictions applied identically everywhere.

### What the consequence is measured on

Propagate each indicator through to the outputs the analysis actually reports —
counts and demolished area, demolition rate relative to the stock, building
lifespan / survival estimates, and the breakdowns by typology and geography — and
report how each of these shifts as the indicator changes. Validate against BOSSINF
on its slice for at least one anchored accuracy read.

## Implementation: the D1–D7 indicator set and what the data showed

This is what we actually built (`src/indicators.py`) once the real Datafordeler
extract arrived, and the empirical findings that shaped it.

### The data

Three raw grunddata parquets, full temporal history, raw BBR column names:
`bygning.parquet` (33.8M rows over **6,250,075** distinct buildings, ~5.4 versions
each), `sagsniveau.parquet` (the case↔building join table), `bbrsag.parquet` (case
dates). Registration floor is **2017-06-02**, but `virkningFra` (effect date) is
backdated, so demolition years legitimately reach back to ~2000.

### Design principles

- **No opaque contract.** Each indicator is a self-contained function that reads the
  raw parquets and returns the set of demolished buildings, `LazyFrame[building_id,
  year]`. It spells out its whole recipe top-to-bottom — no pre-baked verdict column
  anywhere. This is the direct answer to the failure mode this document criticises in
  the KMD extract: every research judgment is visible where it is used.
- **Mechanical vs judgment.** The only shared code is three grain-reduction helpers
  (status-10 rollup, process-3 rollup, the case join) — pure many-rows→one-row
  plumbing with no demolition *decision* in them. Every decision (which codes, which
  date, partial vs total) lives inline in the indicator.
- **Held-fixed window.** All indicators are clipped to **2000–2025 inclusive**, a
  confound frozen in one place. Undated matches are *kept* (a building with a
  demolition case but no status-10 year still counts) — dropping them would collapse
  D4 into D6.
- **Contiguous numbering.** D1–D3 are register-exit signals; D4–D7 are
  demolition-case signals.

### The indicators (counts windowed to 2000–2025)

| ID | Signal | Definition | Count |
|----|--------|------------|------:|
| **D1** | status = 10 | ever Historisk — inclusive register-exit (overcounts on purpose) | 436,194 |
| **D2** | forretningsproces = 3 | ever "Opdateret grundet nedrivning" | 225,706 |
| **D3** | D1 ∩ D2 | status-10 **and** process-3 | 99,664 |
| **D4** | sagstype = 32 | linked total-demolition case (hel) | 237,012 |
| **D5** | sagstype ∈ {31, 32} | linked demolition case incl. partial | 249,152 |
| **D6** | D1 ∩ D4 | status-10 **and** total case — recommended completion-proxy | 200,634 |
| **D7** | case date present | dated by `sag002` notification ≈ felt 294 (felt-295 stand-in) | 243,691 |

Year source: D1/D3 status-10 `virkningFra`; D2 process-3 `virkningFra`; D4/D5/D6
status-10 year (null for case-buildings that never went Historisk); D7 the `sag002`
notification year.

### The discontinued-code exclusion — a contested on/off axis, not an indicator

The thesis "corrected" `status = 10` by removing buildings whose use-code is a
discontinued round-number code (`{130, 210, …, 530}`), on the theory that a
status-10 event on those is a re-registration artifact (it reported >90% fake rates).
We made this an **orthogonal on/off axis** (`exclude_discontinued`, composable with
*any* indicator) rather than baking it into one "corrected" indicator, because on
this extract its premise fails:

- It strips **~34% of every indicator's buildings** — that uniformity is a *base
  rate* (about a third of the stock carries these old agricultural/industrial codes),
  not evidence of artifacts.
- Of the status-10 buildings it removes, **50.7% also have a formal demolition case**
  (vs a 44.2% case-rate among the buildings it keeps) — so it removes *genuine*
  demolitions, over-correcting.

`all_variants()` enumerates the full **7 × 2 = 14-cell grid** (`D1` … `D7` and
`D1-exdisc` … `D7-exdisc`). `exclude_discontinued(D1)` reproduces the thesis's old
"corrected historical" exactly (302,261). Whether the exclusion helps is an empirical
question to settle against BOSSINF, not an assumption.

### Other empirical findings baked into the code

- **felt 295 is not reconstructable** (see the resolved TODO above): no usable
  completion date, so D7 is explicitly a *notification-dated activity* proxy, not a
  completed-demolition flag. `case_date_complete` (sag010) is carried but not used by
  default — it is the one-line swap for a strict, undercounting completion variant.
- **~82k demolition-case rows have a null `stamdataBygning`** and cannot be linked to
  a building — a documented undercount for the case indicators D4/D5/D7.
- **D2 is not a subset of D1** — 126,362 buildings are process-3 but never status-10,
  so D3 (their intersection) is far smaller than either. The proxies genuinely
  disagree; that disagreement is the result.
- **No collapse rule needed** — only ~2.7% of case-buildings carry both sagstype 31
  and 32, and the raw `sagstypes_seen` list handles them with zero judgment.

### Next step

Score the 14 variants against **BOSSINF** on its grant-funded-demolition slice — the
one place a real precision/recall can be read — then propagate each through to the
downstream outputs (counts, demolished area, rate-vs-stock, lifespans, typology/geo
breakdowns) per the ablation scope above.
