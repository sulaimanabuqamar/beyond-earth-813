# Verification

```
cd tests && npm install     # once, for jsdom
cd .. && python3 tests/verify.py
```

Five checks, no network, two to three minutes. They exist because three of the
claims in the methodology report are the kind that are easy to assert and
easy to get wrong.

### 1 · Notebook dry run — `notebook_dryrun.py`

Executes every code cell of `notebook/beyond_earth_tabarjal.ipynb` in order
with the network replaced by `offline_stubs.py`: synthetic circular pivots on
a desert background, cut on a ~30-day cycle, served through a fake STAC
catalogue and a fake `odc.stac.load`.

It answers one question: **does the notebook run to completion and write
`tabarjal.json` when no Earthdata credentials are present?** The hyperspectral
section needs NASA Earthdata; everything the dashboard consumes does not, and
a missing login must degrade rather than abort.

This proves nothing about Tabarjal. The imagery is invented, and the synthetic
pivots cover well under 1% of the box against roughly 6% in reality — so the
detection day the dry run picks is meaningless. Everything downstream of that
choice is still exercised, which is the point.

### 1b · Notebook dry run, hyperspectral branch active — `DRYRUN_EMIT=1`

The same run with the EMIT section executing for real against
`emit_fixture.py`: a miniature granule with the same groups, the same variable
names, the same 285-band wavelength axis and the same geometry lookup table
carrying its fill value. It exercises the download loop, lazy band selection,
GLT orthorectification, the zonal reduction, the join, the hard set and the
prediction contest — the code path a run *with* Earthdata credentials takes.

This is what caught `dask` and `h5py` missing from `requirements.txt`:
`xr.open_dataset(..., chunks=...)` needs a chunk manager, and a clean install
from that file would have failed on the EMIT section with an `ImportError`.

### 2 · Model parity — `parity_python.py` + `parity_js.js`

The cycle model exists twice: in `api/priority.py` and again in JavaScript
inside `dashboard/index.html`. The report claims the second is a line-for-line
port of the first. This check holds them to it — every field, at nine
positions of the date scrubber, comparing status, NDVI, cycle length, days
since cut, expected value, deficit and priority.

The first run of this harness found two real disagreements: the JavaScript
did not round the deficit to 4 dp before using it, and used a different
rounding rule at exact halves. Both are now fixed, and the two agree on all
540 field-dates.

### 3 · Dashboard render — `dashboard_render.js`

Renders the page headlessly (jsdom) against eight datasets and fails on any
thrown error, any `NaN`, any `undefined` or `[object Object]` reaching the
screen:

- the baseline, with the hyperspectral block empty
- every NDVI value null, so every field is `no_data`
- one field and two dates, the smallest input that is still valid
- hyperspectral rows present
- hyperspectral rows carrying nulls, which real granules do produce
- the scrubber dragged to the earliest date
- a status filter chip clicked
- a field selected from the map

`scrollIntoView` and `getBBox` are shimmed: jsdom does not implement them and
every real browser does.

### 4 · API smoke — `api_smoke.py`

Every endpoint of `api/service.py`, including the error paths, against the
synthetic dataset. Nothing may return 5xx. The file restores any real
`data/tabarjal.json.gz` it displaces.

---

`synthetic_data.py` writes `synthetic.json`, which has the exact shape of the
real export. It is test scaffolding and is never shipped as data.
