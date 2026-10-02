# Results

Everything here came out of one run of `notebooks/beyond_earth_tabarjal.ipynb` over
Tabarjal, Wadi as-Sirhan, Al Jouf, Saudi Arabia, on 27 September 2026. The notebook in
this repository is committed **with that run's outputs still in it**, so you can read
what happened before you decide to spend the download yourself.

| File | What it is |
|---|---|
| `tabarjal.json` | everything the dashboard and the API read: 518 fields, 82 dates, 33,078 NDVI observations |
| `tabarjal.json.gz` | the same, gzipped — the API reads this one |
| `tabarjal_fields.geojson` | the 518 detected pivot polygons, EPSG:4326 |
| `tabarjal_ndvi_series.csv` | `field_id,date,ndvi` — all 33,078 field-days |
| `tabarjal_sawtooth.png` | the figure the whole project rests on: the cut-and-regrow sawtooth |
| `priority_queue_2026-09-08.csv` | the full ranked assessment of all 518 fields on the last observed date |
| `comparison_naive_vs_cycle.csv` | per-date comparison against the ranking this tool replaces, 69 dates |
| `sample_output_queue.csv` | the expected answer for `data/sample_input/` — the offline check |

## What the run found

**The scene.** 518 centre-pivot fields detected, 24,038 ha in total, median field 47.8 ha.
Detection ran on 2026-04-13, the greenest fully-covered day in the season (95th-percentile
NDVI 0.887, 3063 × 3389 px at 20 m, 100 % clear). Season observed 2026-02-07 to 2026-09-08,
82 dates that passed the cloud filter.

**The problem, measured.** Alfalfa here is cut roughly every month — a median cycle of
**30.5 days**, measured on 493 of the 518 fields; the remaining 25 never showed a clean
peak and are modelled on the 30-day default. Every cut drops a field from about 0.90 NDVI to
about 0.35 within ten days. On 22 July 2026, **57 of the 518 fields were mid-cut**. A
ranking built on NDVI decline puts exactly those fields at the top.

**The cost of getting it wrong.** Across the 61 dates from 16 April onward — once every
field has shown at least one cut — the naive decline ranking's top 20 contained between
**7 and 20 fields that had simply been mown**, median 14, and 10 or more on 56 of those 61
dates. On the last observed date, 16 of the naive top 20 had just been cut, and the naive
top 20 and this tool's queue agree on **1 field out of 20**.

**What the tool says instead.** On 2026-09-08, of 518 fields: 190 on schedule, 228 out of
rotation (summer fallow), 52 freshly cut, 32 genuinely behind their own rhythm, 16 whose
cycle could not be established. The inspection queue is **45 fields, 1,954 ha** — 8.1 % of
the irrigated area, not 518 fields to walk.

**Hyperspectral.** `emit` is empty in `tabarjal.json`: this run supplied no NASA Earthdata
credentials, so the hyperspectral section was skipped, cleanly and by design. The EMIT
finding reported in `docs/methodology.md` §5 comes from an earlier run over the same area
with credentials present, and is labelled as such there. Nothing in the numbers above
depends on it.

## Reproducing the small one in a second

```
python3 tools/score.py \
  --fields data/sample_input/fields_sample.csv \
  --series data/sample_input/ndvi_series_sample.csv \
  --out    /tmp/check.csv
diff /tmp/check.csv results/sample_output_queue.csv && echo "identical"
```

Expected: 12 fields assessed as of 2026-09-08, 4 in the queue totalling 214.2 ha, ranked
392, 138, 404, 511. No network, no credentials, no downloads.
