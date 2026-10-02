# Telling harvest from stress

### A cycle-aware irrigation screening tool for centre-pivot farms in Wadi as-Sirhan

**Team Beyond Earth** · Arab Youth Space Hackathon 2026, 813 Challenge
Theme 02 — Precision Agriculture & Crop Intelligence
Proof of Concept · 27 September 2026

---

## 1. The problem, and why the obvious answer is wrong

**We want to identify irrigated fodder fields that are failing** in **the Tabarjal / Wadi as-Sirhan centre-pivot belt, Al Jouf, Saudi Arabia** across **a full growing season** so that **farm operators and groundwater regulators** can decide **which fields to inspect and irrigate first, and where fossil groundwater is being spent on crop that is already lost.**

Wadi as-Sirhan is one of the most documented fossil-groundwater depletion cases in the world: thousands of centre pivots drawing on an aquifer that does not recharge. Water, not land, is the binding constraint. Anything that misdirects irrigation is expensive in the one input that cannot be replaced.

The obvious remote-sensing answer is to rank fields by NDVI decline and send water to the fields falling fastest.

**On this landscape that answer is wrong, and we can show it with numbers.**

The crop is alfalfa, cut roughly every 30 days. Every cut drops a field's NDVI from around 0.90 to around 0.35 within ten days, then it regrows. A season of per-field NDVI here is not a trend, it is a **sawtooth**. On any given date a large fraction of fields are mid-cut and read exactly like a field in severe water stress.

Measured across the season on 518 detected pivots, on **every one of the 69 observation dates with enough history to model**: a decline ranking's top twenty contains a median of **14 fields that were simply cut**. From 16 April onward — once every field has shown at least one cut — the count never falls below **7** and reaches **20 out of 20**, and it is 10 or more on 56 of those 61 dates. The one date in the whole season where the naive ranking is clean is 27 March, before the cutting rhythm has established itself. On 22 July 2026, **57 of the 518 fields were mid-cut**. A decline ranking would have put every one of them at the top of an irrigation queue. They needed nothing. They had just been mown.

The full per-date sweep is committed at `results/comparison_naive_vs_cycle.csv`; the table below is a sample of it. Its *genuinely overdue* column counts the `overdue` status only, which is why it does not sum with the mown count to twenty — the remainder are fields the naive ranking picked that were healthy, out of rotation, or off-cycle.

| Date | Of the naive ranking's top 20, simply mown | Genuinely overdue |
|---|---|---|
| 2026-04-28 | 11 | 5 |
| 2026-05-18 | 17 | 0 |
| 2026-06-07 | 13 | 7 |
| 2026-06-25 | 11 | 2 |
| 2026-07-12 | 12 | 4 |
| 2026-07-30 | 11 | 2 |
| 2026-08-18 | 15 | 0 |
| 2026-09-07 | 15 | 1 |

At season end the naive top twenty and this tool's queue overlap on **one field out of twenty**. They are very nearly disjoint rankings.

This is precisely the failure the challenge's own onboarding guide names — *reporting an index as ground truth* — and it is the failure our tool exists to avoid.

---

## 2. What we built

A per-field screening tool that models **each field's own cutting rhythm from its own history**, then asks a different question:

> Is this field lower than **it** should be at **this** point in **its** cycle, and has it failed to come back when it was due?

The output is an inspection queue: which fields to look at first, why, and how many hectares are behind. It runs on free Sentinel-2 and needs no hyperspectral data.

Three artefacts make up the PoC:

| Artefact | What it is |
|---|---|
| **Dashboard** | A working web interface over all detected fields: map, ranked queue, per-field history, and a side-by-side comparison against the naive decline ranking. |
| **API** | A read-only HTTP service exposing the same assessment — `/priority`, `/fields/{id}`, `/comparison` — so the ranking can feed an existing farm-management system rather than requiring a new one. |
| **Notebook** | One reproducible notebook that rebuilds every number in this report from open archives. |

---

## 3. Study area and data

### 3.1 Area of interest

| | |
|---|---|
| Region | Tabarjal / Wadi as-Sirhan, Al Jouf Province, Saudi Arabia |
| Bounding box | 38.15, 29.75, 38.85, 30.30 (W, S, E, N; EPSG:4326) |
| Working projection | EPSG:32637 (UTM 37N) |
| Extent | roughly 67 × 61 km |

The area was chosen by measurement, not assumption. Our first candidate was the Liwa / Al Dhafra belt in the UAE, picked on the premise that centre pivots there would make field delineation nearly free. We tested that premise before building on it: of 227 vegetated patches ≥ 5 ha in the Liwa box, **exactly one** was circular (median eccentricity ≈ 0.90, median solidity ≈ 0.50). The scene was rectangular smallholdings 50–100 m across — smaller than a single 60 m EMIT pixel. We moved, and verified the replacement the same way before adopting it.

Saudi Arabia is an Arab League state, so the challenge's "Arab agricultural zones" framing is satisfied; the eligibility rules govern participants, not study-area location.

### 3.2 Sentinel-2 surface reflectance

| | |
|---|---|
| Collection | `sentinel-2-l2a`. Two interchangeable hosts: Earth Search v1 (`earth-search.aws.element84.com/v1`) and Microsoft Planetary Computer. **The dataset shipped with this submission was built from Planetary Computer**, because the network the final run executed on refuses the AWS bucket Earth Search points at. |
| Season | 2026-02-07 → 2026-09-08 |
| Scene filter | `eo:cloud_cover < 20%` |
| Items | grouped into **82 usable solar days**, 2026-02-07 to 2026-09-08 |
| Bands used | red (B04), NIR (B08), SCL |
| Resolution | 20 m for field detection, 60 m for the season-long series |
| Licence | Copernicus, free and open |

### 3.3 EMIT hyperspectral

| | |
|---|---|
| Collection | `EMITL2ARFL`, NASA CMR via `earthaccess` |
| Scenes used | 2 — 2026-02-18 and 2026-07-22 |
| Selection rule | cloud ≤ 20% **and** within ±2 days of a Sentinel-2 day, so the two instruments describe the same crop |
| Cube | 285 bands, 380.9–2492.8 nm, median spacing 7.44 nm, 60 m |
| Licence | NASA, open |

Named granule for the July scene: `EMIT_L2A_RFL_001_20260722T113527_2620308_031` (1% cloud).

### 3.4 Two runs, and which numbers come from which

This matters for reading every figure below, so it is stated plainly rather than buried.

| | Earlier run | The run behind the shipped dataset |
|---|---|---|
| Sentinel-2 host | Earth Search (AWS) | **Planetary Computer (Azure)** |
| Hyperspectral | EMIT, with Earthdata credentials | not run — no credentials on that machine |
| Fields | 511 | **518** |
| Usable days | 85 | **82** |
| Field-days | 34,741 | **33,078** |

The two catalogues serve the same Copernicus L2A product but do not hold an identical set of items, and they screen cloud slightly differently, so the detection day and the usable dates move. The second run happened on Planetary Computer because the network it executed on refuses the AWS bucket outright.

**Everything about the product — the field set, the season series, every status, every queue, the dashboard and the API — comes from the second run.** The hyperspectral results in §5 come from the first, on its 511-field set, and are reported as measurement rather than folded into the ranking. Nothing in the product depends on them, which is the same conclusion §5.4 reaches on the evidence. Re-running the hyperspectral section against the current field set would cost two EMIT granules and an Earthdata login; it would not change what the tool does.

---

## 4. Method

### 4.1 Reflectance and cloud screening

Three details here each cost us a run when we got them wrong, and each is a place another team can quietly go wrong too.

**Nodata is discarded, never converted.** Sentinel-2 nodata is stored as 0. Applying the BOA offset to it produces −0.1 reflectance and drives the NDVI denominator toward zero. Before the offset, `DN ≤ 0` is masked to NaN. Left in, it produced an observed NDVI range of −9.09 to +4.35.

**The BOA offset is read from the item, not assumed.** Processing baseline ≥ 04.00 carries a −1000 radiometric offset, but Earth Search publishes `earthsearch:boa_offset_applied`, and for this collection it is already applied. Subtracting it a second time gave an NDVI 99th percentile of 1.256 and a red-band reflectance 1st percentile of −0.0548 — both physically impossible. The flag is read per item.

**Days are mosaicked, not sampled.** A single STAC item covered 9.5% of our bounding box. Items are grouped by `solar_day` and loaded together, which takes coverage to 100%.

Cloud, shadow and snow are removed using the scene classification layer, dropping SCL classes 0, 1, 3, 8, 9, 10 and 11 (nodata, saturated, cloud shadow, cloud medium and high probability, thin cirrus, snow). A day is kept for a field only when more than 60% of that field's pixels survive screening; otherwise the field has a gap on that date rather than a wrong number.

A hard assertion on every run refuses to continue if NDVI falls outside [−1, 1]. Observed after correction: min 0.041, max 0.984.

### 4.2 Detecting the pivots

Field boundaries are not supplied; they are derived.

Detection runs at 20 m on the **greenest fully covered day of the season** — chosen automatically by probing 14 dates spread across the season at 120 m, discarding any with less than 90% valid coverage, and taking the highest 95th-percentile NDVI.

For the shipped dataset that day is **2026-04-13**: p95 NDVI **0.887**, scene 3063 × 3389 px, **100% clear**. The coverage filter does real work — eight of the fourteen probed dates were discarded, at 12%, 14%, 15%, 59%, 64%, 66%, 67% and 67% valid coverage, because a partial mosaic would have made a partial field set.

Detecting at peak greenness is not a detail. An earlier run over the same area, built from the Earth Search catalogue, chose 2026-04-28 (p95 NDVI 0.806) and found **511** fields; detecting in July instead found only **328**, because fields that happened to be mid-cut that day fell below the vegetation threshold. The same confound this tool exists to correct also attacks the step that builds the field set, which is why the date is chosen by the algorithm rather than by us.

The detector is deliberately simple and explainable:

1. Threshold NDVI > 0.30.
2. Morphological closing with a 2-pixel disk, then remove objects below 10 ha.
3. Label connected components and keep only those that are **shaped like a centre pivot**: area 10–400 ha, eccentricity ≤ 0.75, solidity ≥ 0.85.

**Result: 518 pivots, 24,038 ha, median field 47.8 ha.** Polygons are vectorised and written as GeoJSON in EPSG:4326.

The percentile choice carries an assumption worth stating: the 95th percentile of the whole AOI only describes the crop because the irrigated fields occupy more than 5% of this box. The p95 measured on the chosen day — **0.887** here, 0.806 on the earlier run — is unambiguously canopy, not bare ground. Ported to a sparser region the same statistic would land on desert and the detection day would be chosen by haze; there, rank the days by the area above a fixed NDVI instead.

The shape filter is doing real work. It is what separates an irrigated circle from a wadi, a road verge, or a rectangular block, and it is why the field set needs no manual drawing.

### 4.3 The per-field time series

Per-field mean NDVI on every usable day, sampled at **60 m**. A 48-hectare circle is still hundreds of 60 m pixels, and the coarser grid makes a whole season affordable.

Zonal means are computed with a labelled-mask reduction and corrected for partial validity, so a field that is 70% cloud-free on a date returns the mean of its clear pixels, not a mean diluted by zeros.

**Result: 33,078 field-days across 518 fields and 82 dates**, 2026-02-07 to 2026-09-08. Median per-field date coverage is 90%; the worst-covered field carries 44% of the dates.

### 4.4 The cycle model

For each field, from that field's own series:

**Peaks.** A local maximum counts as a regrowth peak only if it stands at least 0.20 NDVI above the lowest point on both sides. That prominence test is what separates a real cut-and-regrow cycle from a cloudy pixel. Peaks closer together than 18 days are merged, keeping the higher.

**Cycle length.** The median spacing between consecutive peaks, constrained to 18–60 days. A field with fewer than two clean peaks is assigned the regional default of 30 days and flagged as having no observed cycle, so the interface can say so rather than implying a confidence it does not have.

**Expected value at phase.** For a field *d* days past its last cut, the expected NDVI is the median of what **that same field** read *d* ± 3 days after each of its *previous* cuts. A genuinely low-vigour field is therefore judged against itself, not against a regional average it was never going to meet.

**Deficit** = expected − observed.

### 4.5 Classification and ranking

| Status | Rule | What it means |
|---|---|---|
| **Healthy** | NDVI ≥ 0.70 | Full canopy. Nothing to do. |
| **On cycle** | NDVI < 0.45 and days since cut ≤ 1.3 × cycle | The drop is on schedule. **This is harvest, not stress.** |
| **Overdue** | NDVI < 0.45 and days since cut > 1.3 × cycle, up to 3 × cycle | Should have regrown and has not. Inspect. |
| **Out of rotation** | NDVI < 0.45 and days since cut > 3 × cycle, no regrowth | Not being farmed. Zero priority. |
| **Off cycle** | NDVI mid-range and deficit > 0.15 | Behind where this field normally sits at this phase. |
| **No data** | no clear observation | Stated, never imputed. |

#### Why "out of rotation" exists, and what it cost us to find out

The first complete run over Tabarjal returned **260 of 518 fields as "overdue" on the last date of the season** — half the farm, a queue of 273 fields and 12,146 hectares. No operator can act on that.

Breaking the set down by how long each field had been down settled it:

| Days since last peak | Fields | Area | Median NDVI |
|---|---|---|---|
| 31–45 — plausibly late | 2 | 126 ha | 0.31 |
| 46–60 — very late | 12 | 541 ha | 0.18 |
| 61–90 — two cycles missed | 17 | 735 ha | 0.12 |
| **90+ — not in production** | **229** | **10,221 ha** | **0.11** |

229 fields had sat at NDVI ≈ 0.11 for a median of 120 days and as long as 200. That is bare ground, not a crop in trouble. The status mix across the season shows why: 449 fields healthy in late March, then a steady collapse from mid-May as the summer sets in. These fields are **fallowed through the hottest months**, which is ordinary practice in Al Jouf.

So the tool, run on the last date of the season, was about to tell a farm manager to inspect 229 fields that nobody is farming. That is this submission's own thesis turned against it: mistaking a normal agronomic state for distress is exactly the error we exist to correct, and we had reproduced it one level up.

A field below 0.45 for more than **three** of its own cycles with no regrowth at all is therefore reported as out of rotation and carries zero priority. Three consecutive missed cycles is not a late field. The threshold is not tuned: the break in the data is wide — 17 fields between two and three cycles, 229 beyond three — and any cut inside that gap gives the same answer.

The effect on the season-end queue: **273 fields and 12,146 ha becomes 45 fields and 1,954 ha.** The headline comparison is untouched — the naive ranking still puts 16 of its top 20 on fields that were simply mown.

**Priority = deficit × area_ha** — hectares of crop underperforming its own history — and is exactly zero unless the field is genuinely behind. A freshly cut field can never enter the queue, which is the entire point.

The unit is chosen so the number means something operationally: it is hectares weighted by how far behind they are, and it sorts a queue that a farm manager can work down in order.

---

## 5. Does hyperspectral help? We tested it properly, and the answer is no

Criterion 3 rewards effective hyperspectral use, and our original pitch was that narrow bands could tell a cut field from a stressed one where NDVI cannot. We tested that claim on our own data. It did not survive.

### 5.1 The test

Not a significance test on one scene — a **prediction contest** with the labels taken from the future:

- **Labels come from 15–45 days after** each hyperspectral measurement: did the field recover to NDVI ≥ 0.70, or stay below 0.45? Nothing in the predictor set can see that.
- **Only the hard cases**: rows restricted to fields already below 0.45 on the measurement day — the ones a farmer genuinely cannot call. Separating a green field from a bare one is not a skill worth paying for.
- **Folds split by field**, so no field trains and tests at once.
- **20 repeats** with different seeds.
- Compared: NDVI alone, versus NDVI plus PRI (531/570 nm), red-edge position, the continuum-removed 970 nm water absorption depth, NDWI (860/1240 nm) and EMIT's own NDVI.

Sample: **286 rows, 286 fields, 2 scenes, 22 recover, 264 stay low.**

### 5.2 The headline, which looked excellent

| Feature set | AUC | vs NDVI |
|---|---|---|
| NDVI only | 0.781 (sd 0.013) | — |
| NDVI + narrow bands (excluding EMIT NDVI) | 0.897 | **+0.116** |
| NDVI + all EMIT features | 0.903 (sd 0.008) | **+0.122**, better in 20 of 20 repeats |

It even survives dropping EMIT's own NDVI, so it is not merely "a second NDVI measurement".

### 5.3 The leakage check, which overturns it

Only two EMIT scenes cleared the ±2-day matching rule, so **scene identity is a confound**: absolute reflectance differs between a February and a July acquisition, and each scene carries its own base rate. Training on one scene and testing on the other removes any way for the model to exploit that.

| Held-out scene | n | recover | NDVI | NDVI + narrow | NDVI + all |
|---|---|---|---|---|---|
| 2026-02-18 | 29 | 3 | **0.962** | 0.372 | 0.436 |
| 2026-07-22 | 257 | 19 | **0.793** | 0.629 | 0.655 |

**Adding the narrow bands makes prediction worse on a scene the model has not seen — in one case worse than a coin flip.** The +0.122 was the model learning *which scene a row came from*, not *what state the field was in*.

### 5.4 What we conclude, and what we do not

We conclude that **on this dataset, with two scenes, hyperspectral adds no transferable predictive signal over NDVI.** We do not conclude that it never could. The bottleneck is scene count, not field count: **2 of 60 EMIT granules** over this AOI matched a Sentinel-2 day within ±2 days. Leave-one-scene-out needs six to eight scenes before it has any power.

We report the narrow-band indices per field in the dashboard and API as **measurement**, clearly labelled, and we do not use them to rank anything.

This is the result we would want a judge to see us handle correctly. A random-fold comparison would have let us publish +0.12 AUC and a confident claim. The check that overturned it took four lines of code and is the difference between a finding and an artefact.

---

## 6. Limitations

**Two EMIT scenes.** Stated above. Everything hyperspectral in this PoC is descriptive.

**No ground truth.** No field visit, no irrigation log, no yield record. Every status is a **screening result**, not a diagnosis. The tool says "look at this field first", never "this field is water-stressed". Validation would need irrigation scheduling records or farm inspection reports from one operator for one season; we name this as the first thing to acquire, not as something we have done.

**The cycle model needs two cuts.** A field with fewer than two clean peaks in the observed window gets the regional default and is flagged as such. Early-season and newly planted fields are the weak case.

**Cloud gaps propagate.** A field with a long clear-sky gap can have its last peak misplaced, which shifts its phase estimate. Al Jouf is dry enough that this is rare — 82 usable days in a seven-month window, median per-field coverage 90% — but it is not zero, and the worst-covered field in this set carries only 44% of the dates.

**Detection is at one date.** Fields that were bare on 13 April are not in the set at all. The 328-versus-511 difference between a July and an April detection, measured on the earlier run, is the size of that effect.

**Deficit is relative, not absolute.** A field that has been declining for several cycles is judged against its own recent, already-degraded history and will under-flag. A longer baseline would fix this and is a straightforward extension.

---

## 7. Reproducibility

One notebook rebuilds everything from open archives: STAC search, mosaicking, screening, detection, the season series, EMIT download and orthorectification, the prediction contest and the leakage check.

With no credentials it writes these five, and all five are committed under `results/`:

| File | Contents |
|---|---|
| `tabarjal.json` / `.json.gz` | everything the dashboard and the API read |
| `tabarjal_fields.geojson` | 518 pivot polygons, EPSG:4326, with area |
| `tabarjal_ndvi_series.csv` | 33,078 field-days |
| `tabarjal_sawtooth.png` | the measured cut-and-regrow figure |

With NASA Earthdata credentials present it writes three more, which the shipped run does **not** contain because no credentials were supplied to it. These are the files the §5 hyperspectral analysis ran on, produced by the earlier Earth Search run:

| File | Contents |
|---|---|
| `tabarjal_emit_pooled.csv` | 803 field-level EMIT measurements |
| `tabarjal_model_table.csv` | the joined prediction table |
| `tabarjal_hard_set.csv` | the 286 rows the contest ran on |

No credentials are in the notebook. NASA Earthdata credentials are read from the environment — from Kaggle Secrets, Colab Secrets, or `~/.netrc`, whichever the host provides — and are never written to disk by this code. The notebook never calls a blocking prompt, because inside a Run All a prompt is indistinguishable from a hang.

**The hyperspectral section is optional and fails soft.** Sentinel-2 is served anonymously; EMIT is not. With no Earthdata credentials the notebook prints what it is skipping, runs the whole Sentinel-2 pipeline, and still writes every file the dashboard and API consume. Nothing the product does depends on the hyperspectral section — which is consistent with §5.4, where it earns no place in the ranking.

**Two interchangeable Sentinel-2 hosts.** `SOURCE = "earthsearch"` reads from Element 84's AWS bucket; `SOURCE = "planetary"` reads the same Copernicus L2A product from Microsoft Planetary Computer. Band naming and the BOA offset differ between them and the notebook handles both — Earth Search states `earthsearch:boa_offset_applied` outright, Planetary Computer does not, so there the offset is inferred from `s2:processing_baseline`. The switch exists because a network that blocks one host usually does not block the other.

### What has been verified, and how

`python3 tests/verify.py` runs five checks offline in two to three minutes. They exist because the claims below are easy to assert and easy to get wrong.

| Check | What it establishes |
|---|---|
| Notebook dry run | Every cell executes in order against synthetic imagery with no credentials present, and `tabarjal.json` is written. The no-Earthdata path is exercised, not assumed. |
| Notebook dry run, hyperspectral branch | The same run with the EMIT section executing against a miniature granule carrying the real product's groups, variable names, 285-band wavelength axis and fill-valued geometry lookup table — download loop, lazy band selection, orthorectification, zonal reduction, join and prediction contest. |
| Model parity | `api/priority.py` and the JavaScript model inside `dashboard/index.html` return identical status, NDVI, cycle length, days-since-cut, expected value, deficit and priority for all 60 test fields at nine positions of the date scrubber — 540 field-dates. |
| Dashboard render | The page renders headlessly against eight datasets, including every-value-null, a single field with two dates, and hyperspectral rows carrying nulls. No thrown errors, and no `NaN`, `undefined` or `[object Object]` reaching the screen. |
| API smoke | Every endpoint answers, error paths included. Nothing returns 5xx. |

The hyperspectral dry run earned its place immediately: it failed on an `ImportError` for `dask`, which `xr.open_dataset(..., chunks=...)` needs and which `requirements.txt` had never listed, along with `h5py` behind `h5netcdf`. A clean install from that file would have failed on the EMIT section — on a machine, and at a moment, of the reader's choosing rather than ours.

The parity check earned its place on first run. The report already claimed the JavaScript was a line-for-line port of the Python; it was not quite. The Python rounds the deficit to 4 dp before using it and the JavaScript did not, and the two languages break exact halves in opposite directions. Both differences were under 0.01 of a priority score and neither could have changed a status or a rank — but "the dashboard and the API cannot disagree" is either true or it is not. It is now true, and there is a command that demonstrates it.

### Traps worth naming, for anyone repeating this

1. **Nodata converted instead of discarded** → NDVI −9.09 to +4.35.
2. **Single tile instead of a mosaic** → 9.5% coverage.
3. **BOA offset applied twice** → NDVI p99 of 1.256.
4. **EMIT asset filtering on the full URL** downloads the cloud mask: all three assets sit in a directory whose name contains `_RFL_`. Filter on the **file name**.
5. **`hypercoast.read_emit()` orthorectifies all 285 bands at once** — about 2.9 GB — and kills a free Colab runtime. Open the netCDF lazily, select the 12 bands you need, then orthorectify: 2.9 GB becomes 122 MB.
6. **The EMIT geometry lookup table carries a fill value**, so `glt_x` / `glt_y` arrive as floats and cannot index. Cast to int and bound-check against the cube shape.
7. **A blocking `input()` looks exactly like a crashed run.** `earthaccess.login()` prompts on stdin; if the browser tab has disconnected the prompt is invisible and the notebook appears dead for hours. Put credentials in the environment.
8. **Random folds across acquisition dates leak scene identity.** Split by scene, or you will publish an artefact. See §5.3.
9. **GDAL has no HTTP timeout by default.** If the far end accepts a connection and then stops answering, `rasterio` waits on that socket indefinitely: zero CPU, no error, no output, for hours. It is indistinguishable from slow work. Set `GDAL_HTTP_TIMEOUT`, `GDAL_HTTP_CONNECTTIMEOUT`, `GDAL_HTTP_MAX_RETRY` and `GDAL_HTTP_RETRY_DELAY` before the first read. Diagnose it with `lsof -nP -a -p <pid> -i`: a single connection in `CLOSE_WAIT` and a `TIME` column in `ps` that does not advance means a dead socket, not a slow one.
10. **Some networks block the imagery host outright.** A university or corporate network may permit the STAC API and refuse the bucket the imagery actually lives in, which looks like a broken notebook rather than a firewall. One `curl` against a single band settles it in under a second: an immediate `000` is a refusal, not a timeout. Have a second host ready.

---

## 8. What this is worth, and what comes next

At the scale measured here — 518 pivots, 24,038 hectares in one 67 × 61 km box — a screening queue that does not confuse harvest with stress is the difference between inspecting the right ten fields and inspecting ten fields that were mown last week.

The next three steps, in order:

1. **Ground truth from one operator.** One season of irrigation records against our queue turns a screening tool into a validated one.
2. **More hyperspectral scenes.** Relaxing the match window to ±5 days, or widening the AOI, gets scene count to the six-to-eight needed to answer §5 properly. Worth doing; not worth blocking on.
3. **A longer baseline.** Two or three seasons of NDVI history would let the deficit be measured against a healthy baseline rather than a recent one, closing the under-flagging case in §6.

---

*Sentinel-2 data: Copernicus Sentinel data 2026, processed by ESA, accessed via Earth Search. EMIT data: NASA Jet Propulsion Laboratory, accessed via NASA Earthdata. Both open. All analysis code is our own.*
