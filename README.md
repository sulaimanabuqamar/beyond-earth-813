# Beyond Earth — telling harvest from stress

**A cycle-aware irrigation screening tool for centre-pivot farms, built on open Sentinel-2
data: it ranks fields by how far each one has fallen behind its *own* cutting rhythm, so a
field that was simply mown last week never reaches the top of an irrigation queue.**

Arab Youth Space Hackathon 2026 · 813 Challenge · Theme 02, Precision Agriculture & Crop
Intelligence · Team Beyond Earth · Proof of Concept.

---

## 1 · Business use case

Who uses this, and what they decide with it.

| User | The decision this changes |
|---|---|
| **Pivot operators** | which fields to send a scout or a water truck to this week, when scouting time is the scarce resource |
| **Water regulators** | where fossil groundwater is being spent on crop that is already lost, with per-field evidence instead of an aggregate |
| **Lenders and insurers** | crop condition across a portfolio without a site visit |
| **Farm-management software** | an integration: they own the customer, this owns the cycle model, and the API is the seam |

The economics are unusual and favourable: the input imagery is free and open, the whole
area-season for this run is 518 fields across 82 dates, and the marginal cost of adding one
more field is effectively zero. Cost scales with area, not with customers. We have
deliberately **not** set a price per hectare — what one avoided inspection is worth is the
first question a pilot answers, and inventing the number would be the weakest part of the
submission. `docs/business-case.md` sets out the model with its assumptions named.

---

## 2 · The problem

**We want to identify irrigated fodder fields that are failing, in the Tabarjal / Wadi
as-Sirhan centre-pivot belt of Al Jouf, Saudi Arabia, across a full growing season, so that
farm operators and groundwater regulators can decide which fields to inspect and irrigate
first.**

Wadi as-Sirhan is one of the most documented fossil-groundwater depletion cases in the
world: thousands of centre pivots drawing on an aquifer that does not recharge. Water, not
land, is the binding constraint, so anything that misdirects irrigation is expensive in the
one input that cannot be replaced.

The obvious remote-sensing answer is to rank fields by NDVI decline and attend to the ones
falling fastest. **On this landscape that answer is wrong, and we can show it with numbers.**

The crop is alfalfa, cut about every month. Every cut drops a field from roughly 0.90 NDVI
to roughly 0.35 within ten days, then it regrows. A season of per-field NDVI here is not a
trend, it is a **sawtooth**, and on any given date a large share of fields are mid-cut and
read exactly like a field in severe water stress.

Measured on our own 518 detected pivots, on every one of the 69 observation dates with
enough history to model:

- a decline ranking's top twenty contains a **median of 14 fields that had simply been mown**;
- from 16 April onward the count never falls below **7**, reaches **20 out of 20** at worst,
  and is ten or more on **56 of 61** dates;
- on 22 July 2026, **57 of the 518 fields** were mid-cut;
- at season end, the decline ranking's top twenty and this tool's queue agree on
  **1 field out of 20**. They are very nearly disjoint rankings.

This is precisely the failure the challenge's own onboarding guide names — *reporting an
index as ground truth* — and it is the failure this tool exists to avoid.

---

## 3 · Data used

| Dataset | Role | Access | Licence |
|---|---|---|---|
| **Copernicus Sentinel-2 L2A** | field detection and the season-long NDVI series | Element 84 Earth Search *or* Microsoft Planetary Computer — same product, two hosts, switchable in one constant | © European Union, Copernicus. Free and open, **no credentials** |
| **NASA EMIT L2A Reflectance** (`EMITL2ARFL`) | optional hyperspectral section only | NASA Earthdata via `earthaccess` | NASA, open, free Earthdata login |

Area of interest: `38.15, 29.75, 38.85, 30.30` (WGS84), a 67 × 61 km box, projected to
EPSG:32637. Season observed **2026-02-07 to 2026-09-08**, 82 dates that passed a 20 % cloud
filter, mosaicked by solar day, SCL classes 0/1/3/8/9/10/11 removed. 20 m for detection,
60 m for the time series.

**Field boundaries were not supplied and none were drawn by hand.** They are detected: NDVI
above 0.30 on the greenest fully covered day of the season, then a shape test — 10–400 ha,
eccentricity at most 0.75, solidity at least 0.85. For this run the algorithm chose
**2026-04-13** (95th-percentile NDVI 0.887, 3063 × 3389 px, 100 % clear) and found **518
pivots covering 24,038 ha**, median field 47.8 ha.

No credentials, keys or restricted imagery are stored in this repository. Earthdata
credentials, when used at all, are read from the environment and never written to disk.

---

## 4 · Technical approach

The model is four steps, and it is deliberately explainable — no deep learning, no
black box.

1. **Find the cuts.** A regrowth peak counts only if it stands `0.20` NDVI above the low
   points on both sides. That prominence test separates a real cut from a cloudy pixel.
2. **Measure the field's own cycle.** The median spacing between that field's peaks,
   bounded to 18–60 days. Fewer than two clean peaks and the field is flagged as such
   rather than given an invented cycle. Measured on **493 of the 518** fields; median
   **30.5 days**.
3. **Expect a value.** What did *this field* read this many days after each of *its*
   previous cuts? The expectation is the median of its own history at the same phase ± 3
   days, so a low-vigour field is judged against itself.
4. **Rank the deficit.** `priority = (expected − observed) × hectares`, and exactly zero
   when a field is on schedule — so a freshly cut field can never enter the queue. That is
   the entire design.

Each field gets one of five statuses and a sentence a farm manager can act on. The wording
below is copied from `results/priority_queue_2026-09-08.csv`; it is what the tool wrote, not
prose for this README.

| Status | Example reason | Enters queue |
|---|---|---|
| `healthy` | "Tracking its own cycle within tolerance." | no |
| `recently_cut` | "Cut 45 days ago on a 45-day cycle. The drop is on schedule — this is harvest, not stress." | no |
| `overdue` | "Cut 47 days ago on a 32-day cycle and still at NDVI 0.19. It should have regrown by now — inspect." | **yes** |
| `off_cycle` | "NDVI 0.49 against 0.84 typical for day 34 of its own cycle — 0.35 below where this field normally sits." | **yes** |
| `dormant` | "Down for 138 days — more than three of its own 22-day cycles — with no regrowth. This field is out of rotation, not late." | no |

The `dormant` status came out of checking our own first result. The season-end queue was 273
fields and 12,146 ha, which was implausibly large; 228 of those had sat near NDVI 0.11 for
months. That is summer fallow, not stress. Adding the status took the queue to **45 fields
and 1,954 ha** — 8 % of the irrigated area rather than half of it.

Three things are shipped, each usable on its own: a **notebook** that rebuilds every number
from open archives, a **dashboard** (map, ranked queue, each field's history with its cuts
marked, and a side-by-side against the naive ranking), and a read-only **API** so the
ranking can feed software a farm already runs. `docs/methodology.md` is the full method.

---

## 5 · Installation

Python **3.11** (3.11.15 is what everything here was verified against). The pins in
`requirements.txt` are exact, and a clean install of them passes the full test suite.

```bash
git clone <this repository>
cd beyond-earth
python3.11 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

Optional, and only for the two browser-side checks in the test suite:

```bash
cd tests && npm install && cd ..
```

Nothing else is required. **No credentials are needed** for anything in section 6 except
the optional hyperspectral section.

---

## 6 · How to run

### a · The thirty-second check — no network, no credentials

Score the twelve sample fields and compare against the committed answer:

```bash
python3 tools/score.py \
  --fields data/sample_input/fields_sample.csv \
  --series data/sample_input/ndvi_series_sample.csv \
  --out    /tmp/check.csv
diff /tmp/check.csv results/sample_output_queue.csv && echo "identical"
```

### b · The dashboard

```bash
cd dashboard && python3 -m http.server 8000
```

`dashboard/tabarjal.json` is committed — a copy of `results/tabarjal.json` placed where the
page fetches it — so there is nothing to copy first.

Then open <http://127.0.0.1:8000>. Opening `index.html` with `file://` will not work — the
page fetches its data.

### c · The API

```bash
uvicorn api.service:app --reload
```

Then <http://127.0.0.1:8000/docs> for the generated OpenAPI page. It reads
`results/tabarjal.json.gz`, which is committed, so there is nothing to copy and nothing to
download. Point `BEYOND_EARTH_DATA` at another `.json.gz` to serve a different run.

| Endpoint | Returns |
|---|---|
| `GET /meta` | dataset description and method summary |
| `GET /fields` | every detected pivot as GeoJSON (`?bbox=` to filter) |
| `GET /fields/{id}` | one field, its assessment and full NDVI history |
| `GET /priority?as_of=YYYY-MM-DD` | the inspection queue for a date |
| `GET /comparison?as_of=…` | cycle-aware queue vs naive decline ranking |
| `GET /hyperspectral/{id}` | EMIT narrow-band indices where a scene covers the field |

### d · The whole thing, from the archives

Open `notebooks/beyond_earth_tabarjal.ipynb` and run it top to bottom. It is committed
**with the outputs of the run described here still in it**, so you can read what happened
before deciding to spend the download.

NASA Earthdata credentials are optional. Supply `EARTHDATA_USERNAME` and
`EARTHDATA_PASSWORD` as environment variables, Kaggle Secrets or Colab Secrets and the
hyperspectral section runs; leave them out and it is skipped cleanly. Sentinel-2 needs none.

Expect roughly 7 minutes on a datacentre connection without the hyperspectral section — that
figure is from an earlier run and the job is bound by download speed, not compute, so a home
connection will take considerably longer. Add about 15 minutes and 3 GB per EMIT granule.

**If the run stalls with no output and no CPU**, the host is blocking the imagery bucket
rather than running slowly. Test it:

```bash
curl -s -o /dev/null -w "%{http_code} %{speed_download}\n" --max-time 20 -r 0-1000000 \
  "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/37/R/DP/2026/2/S2C_37RDP_20260207_0_L2A/B04.tif"
```

An immediate `000` is a refusal, not a slow link. Set `SOURCE = "planetary"` in the constants
cell to read the same Copernicus product from Microsoft Planetary Computer instead. That is
what the committed run did.

### e · Verify it before you trust it

```bash
python3 tests/verify.py
```

Two to three minutes, no network. It executes the whole notebook against synthetic imagery
twice — once with no credentials and once with the hyperspectral branch active against a
miniature but structurally faithful EMIT granule — holds the Python model and the
dashboard's JavaScript model to identical output across 540 field-dates, renders the page
headlessly against eight datasets including the degenerate ones, and exercises every API
endpoint and its error paths. Checks needing Node are skipped, not failed, when Node is
absent. `tests/README.md` says what each check is for.

---

## 7 · Example input and output

**Input** — the model's input is one NDVI series per field. `data/sample_input/` holds
twelve of the 518 fields across all 82 dates, chosen so every status appears:

```
fields_sample.csv          ndvi_series_sample.csv
field_id,area_ha           field_id,date,ndvi
85,78.4                    85,2026-02-07,0.237
86,76.6                    85,2026-02-12,0.321
130,139.3                  85,2026-02-15,0.335
...  (12 rows)             ...  (984 rows)
```

`data/sample_input/` also holds `aoi.geojson` and `run_config.json` — the area and the exact
constants the committed run used. Those two files are the notebook's real input; change the
bbox and the season and the method runs somewhere else.

**Output** — `results/sample_output_queue.csv`, produced by the command in section 6a:

```
rank,field_id,area_ha,status,ndvi,expected_ndvi,deficit,cycle_days,days_since_peak,cycles_observed,priority,reason
1,392,57.2,overdue,0.194,0.8045,0.6105,32.5,47,2,34.92,Cut 47 days ago on a 32-day cycle and still at NDVI 0.19. It should have regrown by now — inspect.
2,138,49.0,overdue,0.131,0.7225,0.5915,37.5,57,2,28.98,Cut 57 days ago on a 38-day cycle and still at NDVI 0.13. It should have regrown by now — inspect.
...
,85,78.4,healthy,...,0.0,Tracking its own cycle within tolerance.
```

12 fields assessed as of 2026-09-08; 4 in the queue totalling 214.2 ha; everything else
carries priority 0 and a reason saying why it is not a problem.

The full-scale equivalents are in `results/`: `priority_queue_2026-09-08.csv` (all 518
fields), `comparison_naive_vs_cycle.csv` (69 dates against the ranking this replaces), and
`tabarjal.json` / `.geojson` / `_ndvi_series.csv`, which are what the dashboard and API read.

---

## 8 · Results and limitations

### What the run found

| | |
|---|---|
| Pivots detected | **518**, 24,038 ha, median 47.8 ha |
| Season observed | 2026-02-07 → 2026-09-08, 82 cloud-screened dates, **33,078 field-days** |
| Cutting cycle | median **30.5 days**, measured on 493 of 518 fields |
| Status at season end | 190 on schedule · 228 out of rotation · 52 freshly cut · 32 overdue · 16 off-cycle |
| Inspection queue at season end | **45 fields, 1,954 ha** — 8 % of the irrigated area |
| Against the naive ranking | median **14 of its top 20** had simply been mown; **1 of 20** overlap with our queue at season end |

### On hyperspectral — the finding we overturned ourselves

We tested whether EMIT's narrow bands (PRI at 531/570 nm, red-edge position, the 970 nm
water-absorption depth) beat NDVI at separating a cut field from a failing one, set up as a
prediction contest with labels taken from what each field did 15–45 days later.

Random folds said yes: **+0.122 AUC, better in 20 of 20 repeats.** Holding out a *whole
scene* said no — the narrow bands made prediction **worse** on a scene the model had not
seen, in one case worse than a coin flip. The gain was the model recognising which
acquisition a row came from. Only 2 of 60 EMIT granules over this area matched a Sentinel-2
day within ±2 days, and two scenes cannot separate plant physiology from acquisition
conditions.

So we report the narrow-band indices as **measurement**, clearly labelled, and rank nothing
with them. `docs/methodology.md` §5 has the full test. The `emit` array is empty in the
committed `tabarjal.json` because this run supplied no credentials; the hyperspectral result
above comes from an earlier run over the same area with Earthdata credentials present, and
is labelled as such wherever it appears. Nothing in the headline numbers depends on it.

### Limitations — what this is not

- **Not validated against ground truth.** No field visit, no irrigation log, no yield
  record. Every status is a **screening result**. The tool says "look at this field first",
  never "this field is water-stressed".
- **Needs two cuts.** A field with fewer than two clean peaks falls back to a regional
  30-day default and is flagged as doing so. Newly planted fields are the weak case.
- **Relative, not absolute.** A field declining slowly across several cycles is judged
  against its own already-degraded history and will under-flag.
- **One area, one season.** 518 fields in one 67 × 61 km box over seven months. Nothing here
  establishes that the thresholds transfer to another crop or another region.
- **The hyperspectral question is open, not answered.** Six to eight matched acquisitions
  would settle it. That is upside, not a dependency.

---

## 9 · Repository layout

```
README.md                         this file
requirements.txt                  exact pins, verified on Python 3.11.15
LICENSE                           MIT for the code; data licences noted inside

notebooks/
  beyond_earth_tabarjal.ipynb     rebuilds every number from open archives, outputs committed
data/
  sample_input/                   the run's real inputs, plus a 12-field offline sample
results/                          everything the committed run produced
api/
  priority.py                     the cycle model — peaks, phase, deficit, ranking
  service.py                      FastAPI service over the same model
dashboard/index.html              the working interface
tools/score.py                    CSV in, ranked queue out, no network
docs/
  methodology.md                  full method, results and limitations
  business-case.md                who buys it, what it costs to run
  slides.pdf                      the pitch deck, with speaker notes
  findings.html                   the hyperspectral write-up
  deck/                           the slide sources slides.pdf is built from
tests/                            run tests/verify.py — six checks, offline
```

---

## 10 · Team, licence and attribution

**Team Beyond Earth**, Khalifa University, United Arab Emirates — five members.
Lead and contact: **Sulaiman AbuQamar**.

Code in this repository is released under the **MIT Licence** (see `LICENSE`). The analysis,
the model, the dashboard and the API are our own work.

The satellite data is not ours and carries its own terms:

- **Copernicus Sentinel-2 L2A** — © European Union, Copernicus Sentinel data 2026. Free and
  open under the Copernicus Data Licence. Accessed through
  [Element 84 Earth Search](https://earth-search.aws.element84.com/v1) and
  [Microsoft Planetary Computer](https://planetarycomputer.microsoft.com/).
- **NASA EMIT L2A Reflectance** (`EMITL2ARFL`) — NASA Jet Propulsion Laboratory, distributed
  by the NASA LP DAAC. Open, requires a free NASA Earthdata login.

Built for the **Arab Youth Space Hackathon 2026 — 813 Challenge**, run by the National Space
Academy under the UAE Space Agency, with Space42 as executive strategic partner.

> Every status this tool produces is a screening result, not a diagnosis.
