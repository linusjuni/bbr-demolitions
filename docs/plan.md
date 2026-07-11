
# Project plan: Demolition indicators in the Danish BBR register

## 1. Overall objective

The purpose of the project is to investigate how different plausible definitions of building demolition in the Danish BBR register affect estimates of:

* the number of demolished buildings;
* the total demolished building area;
* annual demolition trends;
* demolition patterns across building uses, regions and construction periods.

The project will not attempt to establish a perfectly correct demolition indicator for every individual building. This is likely impossible using BBR data alone because the register records administrative objects and processes rather than directly observed physical events.

Instead, the project will:

1. define a set of reasonable demolition indicators;
2. calculate demolition estimates under each definition;
3. compare their agreement and disagreement;
4. identify systematic patterns that make each indicator appear unreliable in certain cases;
5. quantify how much the choice of indicator affects national demolition estimates;
6. provide recommendations for researchers using BBR data.

---

# 2. Central research questions

## Primary question

How sensitive are Danish demolition estimates to the choice of demolition indicator in BBR?

## Secondary questions

1. How much overlap is there between the different demolition-related fields and statuses?

2. Which types of buildings are most affected by disagreement between indicators?

3. Do some indicators produce implausible or suspicious patterns?

4. How much do estimates change when observations with discontinued building-use codes are included or excluded?

5. How sensitive are demolished-area estimates to the choice of area variable?

6. How do the resulting estimates compare with the BUILD estimates of “udgået byggeri”?

---

# 3. Candidate demolition indicators

The exact indicators should be confirmed once the new BBR dataset has been inspected.

## Indicator A: Historical status

A building is treated as demolished if:

```text
Status = 10
```

or the equivalent lifecycle value `Historisk`.

### Motivation

A fully demolished building is expected to leave the active building stock and become historical in the BBR lifecycle.

### Potential problems

* `Historisk` describes the state of a BBR object, not necessarily direct physical destruction.
* Administrative corrections or re-registration may also create historical objects.
* Some buildings have previously been observed with `Status = 10` and later return to an active status.
* Discontinued codes have shown implausibly high historical shares.
* Partial demolition or incorrectly processed cases could theoretically create misleading status histories.

---

## Indicator B: Demolition-related business process

A building is treated as demolished if:

```text
ForretningsProcess = 3
```

### Motivation

The official meaning is that the record was updated because of demolition.

### Potential problems

* It may indicate a demolition-related administrative update rather than a completed demolition.
* It may miss completed demolitions that were registered through another workflow.
* Previous analysis found that this indicator identified considerably fewer demolitions than `Status = 10`.
* It appeared to have lower overlap with the external Andersen and Negendahl dataset.

---

## Indicator C: Historical status and demolition business process

A building is treated as demolished if:

```text
Status = 10
AND
ForretningsProcess = 3
```

### Motivation

This is a stricter indicator requiring both evidence that the object became historical and that the update was associated with demolition.

### Potential problems

* It may be overly restrictive.
* Previous analysis suggested that it produces results similar to using `ForretningsProcess = 3` alone.
* It may therefore exclude many plausible demolitions.

---

## Indicator D: Completed demolition date

A building is treated as having a demolition event if field 295 is present:

```text
Gennemført nedrivning, dato != null
```

### Motivation

Field 295 is the most directly demolition-related field in the official BBR workflow and records that a full or partial demolition has been completed.

### Potential problems

* It includes both full and partial demolitions.
* A partial demolition should not remove the entire building from the building stock.
* Historical coverage and completeness may vary.
* It may be stored in building-case data rather than the simplified building extract.
* A non-null value does not alone identify how much of the building was demolished.

---

## Indicator E: Completed demolition and historical status

A building is treated as fully demolished if:

```text
Field 295 is present
AND
Status = 10
```

### Motivation

This combines a completed demolition event with the disappearance of the building object from the active stock.

### Potential problems

* Missing field-295 registrations may cause undercounting.
* Older demolitions or migrated records may not contain complete case data.
* Register errors may still occur.
* The precise temporal relationship between field 295 and status changes must be investigated.

---

## Indicator F: Corrected historical-status indicator

A building is treated as demolished if:

```text
Status = 10
AND
the observation is not classified as an ambiguous discontinued-code case
```

### Motivation

This corresponds closely to the approach developed in the bachelor thesis. The historical-status indicator had good coverage, but discontinued codes produced extremely high and implausible demolition rates.

### Potential problems

* Some excluded discontinued-code observations may represent real demolitions.
* It is not possible to determine the true status of every ambiguous observation.
* The filtering criteria must be transparent and tested through sensitivity analysis.

---

# 4. Treatment of discontinued codes

Discontinued-code buildings should not simply be removed from the full dataset.

Instead:

```text
Active building with discontinued code:
keep as part of the building stock.

Historical building with discontinued code:
flag as an ambiguous historical object.
```

The analysis should report at least three versions:

1. **Inclusive estimate**
   All `Status = 10` observations are counted as demolitions.

2. **Filtered estimate**
   Historical observations with discontinued codes are excluded.

3. **Ambiguous category**
   Historical discontinued-code observations are reported separately.

This allows the paper to quantify how strongly these cases affect the results without claiming that all of them are false demolitions.

---

# 5. Main hypotheses and possible explanations

These hypotheses should be treated as possible explanations rather than established facts.

## Hypothesis 1: Historical status is broader than physical demolition

`Status = 10` may indicate that a BBR object is no longer active, but not necessarily that the underlying physical building was destroyed.

Possible alternative explanations include:

* correction of an erroneous registration;
* administrative re-registration;
* replacement of one BBR object with another;
* splitting or restructuring of building objects;
* migration between BBR systems;
* inconsistent handling of demolition cases.

### Empirical signs supporting this hypothesis

* buildings that become historical and later active again;
* historical objects without a demolition-related business process;
* historical objects without field 295;
* implausibly high historical rates in specific codes;
* concentration of historical events around code-system changes.

---

## Hypothesis 2: Discontinued broad use codes were sometimes replaced by more granular registrations

Some discontinued building-use codes may have represented broad categories or aggregated registrations. When newer and more detailed codes were introduced, old objects may have become historical while one or more new objects were created.

For example, an old broad agricultural registration could potentially have been replaced by separate registrations for:

* a pig stable;
* a cattle or sheep stable;
* a poultry building;
* a machine shed;
* a barn.

### Existing evidence

The bachelor thesis found that discontinued code 210 had an apparent demolition rate of approximately 92.7%, whereas replacement agricultural codes 211–219 had much lower rates. The old and new code groups also had similar construction-year distributions.

### Important limitation

A new building object on the same property may also represent a genuine demolition followed by new construction. Therefore, object replacement cannot by itself prove administrative re-registration.

The analysis should refer to these observations as:

```text
patterns consistent with re-registration
```

rather than confirmed re-registration.

---

## Hypothesis 3: The business-process indicator undercounts demolitions

`ForretningsProcess = 3` may identify only records where the demolition workflow was registered in a specific way.

Potentially valid demolitions may be missed because:

* the process field is incomplete;
* historical records were migrated without the process information;
* municipalities used different administrative workflows;
* demolition was recorded through status or case changes without retaining business-process code 3.

The overlap with field 295 and `Status = 10` should be investigated.

---

## Hypothesis 4: Field 295 is closer to the official demolition event but cannot distinguish full and partial demolition alone

Field 295 may be the best direct evidence that demolition activity occurred.

However:

```text
Field 295 != proof that the entire building disappeared.
```

A completed partial demolition may reduce the building area while leaving the building active.

The combination of field 295, lifecycle status and changes in area should therefore be analysed.

---

## Hypothesis 5: Some historical-status transitions may reflect incorrectly processed partial demolitions

Officially, partial demolition should leave the building active and update its area. However, some cases may have been registered incorrectly, temporarily or permanently setting the building to historical.

Possible empirical evidence would include:

* field 295 followed by `Status = 10` and later reactivation;
* a substantial reduction in area when the building becomes active again;
* demolition-related business process without permanent object disappearance.

This should remain an exploratory hypothesis unless supported by the new data.

---

## Hypothesis 6: Indicator quality varies across periods and building categories

The quality of BBR registration may differ by:

* year;
* municipality;
* building use;
* construction period;
* changes in the BBR system;
* introduction or discontinuation of classification codes.

An indicator that performs reasonably at national level may still be problematic for agriculture or other specific categories.

---

# 6. Data to download

A new BBR extract should be downloaded to include the newest available year and the broader demolition workflow.

At minimum, retain:

* Bygning;
* BBRSag or equivalent building-case entities;
* building-case information connected to fields 294 and 295;
* relevant property or parcel relations;
* identifiers needed to connect building objects across entities;
* historical versions and lifecycle timestamps.

Do not initially discard columns. Create a raw archived copy and a separate analysis-ready version.

Important fields include:

```text
Building UUID
Case UUID
Property or parcel identifier
Status / lifecycle
ForretningsProcess
EffectFrom
EffectTo
Field 294
Field 295
Construction year
Building-use code
Byg041BebyggetAreal
Byg038SamletBygningsareal
Other residential/commercial area fields used by BUILD
Municipality
Coordinates or address identifiers
```

---

# 7. Initial data audit

Before deciding on the preferred indicator, produce a schema and coverage report.

## Field availability

For every relevant field, report:

* whether it exists;
* data type;
* number and percentage missing;
* first and last observed dates;
* whether it occurs in Bygning or a case-related entity.

## Demolition-field coverage

Produce counts for:

```text
Status = 10
ForretningsProcess = 3
Field 294 present
Field 295 present
```

Then produce all intersections.

Example:

| Combination           | Number of buildings | Area |
| --------------------- | ------------------: | ---: |
| Status 10 only        |                     |      |
| BP3 only              |                     |      |
| Field 295 only        |                     |      |
| Status 10 + BP3       |                     |      |
| Status 10 + field 295 |                     |      |
| BP3 + field 295       |                     |      |
| All three             |                     |      |

---

# 8. Main analyses

## Analysis 1: National estimates under each indicator

For each candidate indicator, calculate by year:

* number of demolitions;
* demolished area;
* average and median demolished area;
* demolition rate relative to the building stock, if a valid denominator can be constructed.

The same filters and aggregation logic should be used for all indicators.

---

## Analysis 2: Indicator agreement and disagreement

Compare which buildings are identified under each definition.

Key outputs:

* overlap table;
* Venn or UpSet plot;
* pairwise agreement rates;
* area contained in each overlap group;
* time trends for disagreement.

The analysis should focus not only on how many records disagree, but also how much building area they represent.

---

## Analysis 3: Potential error patterns

For each indicator, identify cases that make it appear questionable.

### For `Status = 10`

Investigate:

* later reactivation of the same UUID;
* missing field 295;
* missing BP3;
* discontinued codes;
* suspicious construction years;
* concentration around system changes;
* very short time between creation and historical status.

### For BP3

Investigate:

* buildings that remain active;
* missing field 295;
* lack of status transition;
* demolition dates outside the analysis period;
* low overlap with external demolition records.

### For field 295

Investigate:

* buildings that remain active;
* area reductions consistent with partial demolition;
* missing historical status;
* multiple completed-demolition dates;
* incomplete historical coverage.

---

## Analysis 4: Discontinued-code analysis

For every discontinued-code family:

1. calculate active and historical shares;
2. compare historical rates with replacement codes;
3. compare construction-year distributions;
4. compare area distributions;
5. compare timing of historical events with introduction of replacement codes;
6. calculate overlap with BP3 and field 295;
7. quantify their contribution to national demolition totals.

The main output should be:

> How much do national demolition counts and areas change when ambiguous discontinued-code observations are included or excluded?

---

## Analysis 5: Lifecycle histories

Reconstruct histories for buildings with multiple records.

Classify common patterns:

```text
Active → Historical
Active → Historical → Active
Active → demolition process → Active with lower area
Active → field 295 → Historical
Field 295 → Active
Historical old object → new object on same property
```

Do not attempt to assign a definitive physical interpretation to every sequence.

Instead, report:

* how common each sequence is;
* which indicators it affects;
* which use codes and years dominate;
* whether the sequence is consistent with the intended BBR workflow.

---

## Analysis 6: Area-definition sensitivity

Run each demolition indicator using:

1. `Byg041BebyggetAreal`;
2. `Byg038SamletBygningsareal`;
3. a clearly documented hybrid definition;
4. the closest possible reconstruction of the BUILD area definition.

Investigate:

* overall missingness;
* missingness by building use and year;
* ratio between area variables where both exist;
* how national and category-level estimates change.

---

## Analysis 7: Comparison with BUILD

Attempt to reproduce the BUILD analysis as closely as possible.

Questions:

* Does their “udgået byggeri” correspond approximately to `Status = 10`?
* Can their reported national area totals be reproduced?
* How much of their estimate comes from discontinued codes?
* How does the result change under stricter or alternative indicators?
* Does the agricultural share remain similar after filtering ambiguous cases?

The purpose is not to show that BUILD is incorrect.

The purpose is to:

> validate and stress-test the assumption that “udgået” BBR objects predominantly represent physically demolished buildings.

---

## Analysis 8: Comparison with Andersen and Negendahl data

Treat their dataset as an external comparison source, not perfect ground truth.

Calculate:

* overlap with `Status = 10`;
* overlap with BP3;
* overlap with field 295;
* agreement between their demolition date and BBR event dates;
* differences by building use and year;
* whether their observations contain discontinued-code cases.

This may also provide clues about how their externally supplied demolition dataset was constructed.

---

# 9. Suggested output tables and figures

The first version of the paper probably needs around six to eight central outputs:

1. Diagram of the official BBR demolition workflow and candidate indicators.
2. Indicator overlap or UpSet plot.
3. Annual demolished area by indicator.
4. Annual demolished building count by indicator.
5. Historical rates for discontinued versus replacement codes.
6. Area estimates including and excluding ambiguous discontinued codes.
7. Sensitivity to area definition.
8. Comparison with BUILD estimates.

Additional lifecycle plots can go in an appendix.

---

# 10. Proposed interpretation framework

The analysis should avoid using “correct” and “incorrect” too strongly.

Instead, observations can be grouped into:

| Category                            | Interpretation                                                          |
| ----------------------------------- | ----------------------------------------------------------------------- |
| High-confidence full demolition     | Multiple demolition signals and permanent historical status             |
| Likely full demolition              | Historical status without obvious contradictory evidence                |
| Demolition activity, extent unclear | Field 295 or BP3, but building remains active                           |
| Ambiguous historical object         | Historical status with discontinued code or missing demolition evidence |
| Lifecycle inconsistency             | Historical status followed by reactivation                              |
| Unresolved                          | Insufficient evidence to interpret confidently                          |

The exact classification should be defined only after inspecting the new data.

---

# 11. Expected contribution

The paper should not claim to identify the definitive demolition status of every BBR building.

Its contribution should be:

1. a systematic comparison of plausible BBR demolition indicators;
2. a quantitative assessment of how indicator choice changes demolition estimates;
3. documentation of systematic failure modes and ambiguities;
4. a detailed analysis of discontinued-code effects;
5. a comparison with the BUILD proxy and external demolition records;
6. recommendations for transparent and reproducible use of BBR data.

A suitable core conclusion would be:

> BBR lifecycle status, demolition-related process fields and completed-demolition dates capture different administrative aspects of demolition. None should automatically be interpreted as perfect evidence of full physical demolition. National estimates should therefore state their operational definition explicitly and report sensitivity to alternative indicators, area definitions and ambiguous historical object transitions.
