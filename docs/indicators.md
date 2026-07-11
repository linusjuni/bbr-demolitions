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

**The demolition fields are not in the public Datafordeler feed.** The distributed
`Bygning` object carries construction/renovation attributes (`byg026Opførelsesår`,
`byg027OmTilbygningsår`, …) but **no felt 294/295 and no plain demolition date.**
Worse, once felt 295 is reported the building is *deleted from the live register* —
so in standard public BBR a demolished building simply **disappears** rather than
carrying a "demolished" flag you can filter on.

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

### The indicator I'd propose

- **If you can obtain the historical register / a KMD-style extract:** use **felt
  295 "Gennemført nedrivning" as the event, restricted to Sagstype=3 cases.** This
  is as close to ground truth as BBR structurally allows. Decide explicitly whether
  to keep partial demolitions (felt 295 fires for "hel *eller delvis*"). This makes
  our indicator *reproducible* where the KMD extract is not — same signal, our own
  documented recipe.
- **If you only have public snapshots:** use **status 10 Historisk ∩ a Sagstype=3
  demolition case** — the intersection strips the non-demolition status-10 causes
  that make raw `Status=10` overcount, and requires the completion side that raw
  `Business Process=3` lacks.

### What a full Datafordeler extract actually gives you (verified against the model)

We are pulling a full BBR from Datafordeler. Checked against the distributed
grunddatamodel, here is what that extract does and does not contain for demolition:

- ✅ **`Bygning.status` = 10 Historisk** — the register-exit signal, with temporal
  registration timestamps. **Registration history floor: `2017-06-02`** (BBR 1.8
  conversion); pre-2017 demolitions were deleted at conversion and are mostly
  unrecoverable here. So this extract is effectively a **2017→now** source.
- ✅ **`BBRSag.sag012Byggesagskode`** = the demolition case. Clean current code is
  **`6` "BR – Tilladelsessag Nedrivning"**. Legacy `2` "(UDFASES) Anmeldelsessag
  (garager, carporte, udhuse og nedrivning)" and `5` "(UDFASES) øvrige" also cover
  demolition but are noisy (code 2 mixes demolition with sheds/carports). Case is
  dated by `sag002Byggesagsdato`.
- ❌ **felt 294/295 (Anmeldelse / Gennemført nedrivning) are NOT distributed** —
  absent from both `Bygning` and `BBRSag`. The felt-295 "gold" completion date is
  not obtainable from Datafordeler. It lives only in the operational/historical
  register → a KMD-style special extract, or DST microdata (forskerordning).

**Best signal buildable from this extract:** `Bygning.status = 10 Historisk` ∩
`BBRSag.sag012Byggesagskode = 6`, dated by the status-10 registration timestamp or
`sag002Byggesagsdato`. Status-10 alone overcounts (re-registration/merge/error);
a demolition case alone overcounts intent (no completion visible without felt 295);
their intersection is the closest completion-proxy this dataset allows.

**Sources:** BBR Teknik kodelister (Livscyklus; Byggesagskode); BBR Instruks §3.2.2
Bygningsniveau, felt 290/292/294/295, §7.6.10 Indberetning ved nedrivning, §2.1.3
BBR-historisk register; Datafordeler grunddatamodel `Bygning` + `BBRSag`
objekttyper; Datafordeler Bitemporalitet (2017-06-02 floor); Datafordeler Hændelser
(BBR).

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
