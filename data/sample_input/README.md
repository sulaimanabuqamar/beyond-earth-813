# Sample input

This project's real input is an **area and a season**. The imagery is not shipped and
is not meant to be: the notebook queries open archives at run time, which is what makes
the result reproducible anywhere rather than only from our copy of the pixels.

So there are two kinds of input here, and they serve two different purposes.

## 1 · The input the notebook takes — an area and a season

| File | What it is |
|---|---|
| `aoi.geojson` | the bounding polygon the run searched, EPSG:4326 |
| `run_config.json` | every constant the notebook used: season, cloud limit, resolutions, field-size bounds, model thresholds |

These two files record the exact run that produced everything in `results/`. They are
readable, editable, and the only things you need to change to point the method at a
different irrigation scheme: edit the bbox and the season, and run the notebook.

Nothing else is required. Sentinel-2 L2A needs no credentials at all.

## 2 · The input the model takes — one NDVI series per field

| File | What it is |
|---|---|
| `fields_sample.csv` | `field_id,area_ha` — 12 of the 518 detected pivots |
| `ndvi_series_sample.csv` | `field_id,date,ndvi` — those 12 fields across all 82 observed dates, 984 rows |

This is the small, offline, no-download path. The 12 fields were chosen so that every
status the model can return appears in the answer: three that are on schedule, three
freshly cut, three genuinely behind their own rhythm, two out of rotation, and one whose
rhythm the model could not establish.

Score them with no network and no credentials:

```
python3 tools/score.py \
  --fields data/sample_input/fields_sample.csv \
  --series data/sample_input/ndvi_series_sample.csv \
  --out    results/sample_output_queue.csv
```

It finishes in under a second. The expected answer is committed at
`results/sample_output_queue.csv`, and `results/README.md` says what it should say.
