"""
Beyond Earth — irrigation priority API.

A small read-only service over the Tabarjal field set. It is deliberately thin:
the value is in `priority.py`, and this file only makes it reachable.

    uvicorn api.service:app --reload

Endpoints
    GET /health
    GET /meta                          what the dataset is and how it was built
    GET /fields                        every detected pivot, with geometry
    GET /fields/{field_id}             one field, with its full NDVI history
    GET /priority?as_of=YYYY-MM-DD     the inspection queue for a date
    GET /comparison?as_of=YYYY-MM-DD   cycle-aware queue vs naive decline ranking
    GET /hyperspectral/{field_id}      EMIT narrow-band indices where they exist
"""

from __future__ import annotations

import gzip
import json
import os
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query

from .priority import assess_field, rank, naive_decline_rank

# The dataset one notebook run produces. It is committed, so the API answers
# straight after a clone with nothing to copy and nothing to download. Point
# BEYOND_EARTH_DATA at another .json.gz to serve a different run or another AOI.
DEFAULT_DATA = Path(__file__).resolve().parent.parent / "results" / "tabarjal.json.gz"
DATA = Path(os.environ.get("BEYOND_EARTH_DATA") or DEFAULT_DATA)

app = FastAPI(
    title="Beyond Earth — Irrigation Priority API",
    version="1.0.0",
    description=(
        "Per-field irrigation screening for centre-pivot farms in Wadi as-Sirhan, "
        "Al Jouf, Saudi Arabia. Built on open Sentinel-2 surface reflectance. "
        "Ranks fields by how far each one has fallen behind its own cutting cycle, "
        "not by raw NDVI decline — because raw decline measures harvest."
    ),
)


@lru_cache(maxsize=1)
def load() -> dict:
    with gzip.open(DATA, "rt", encoding="utf-8") as fh:
        return json.load(fh)


@lru_cache(maxsize=1)
def _parsed() -> tuple[list[date], dict[int, list], dict[int, dict]]:
    d = load()
    dates = [datetime.strptime(s, "%Y-%m-%d").date() for s in d["dates"]]
    series = {int(k): [None if v is None else v / 1000.0 for v in vals]
              for k, vals in d["ndvi"].items()}
    fields = {f["id"]: f for f in d["fields"]}
    return dates, series, fields


def _as_of(value: str | None) -> date:
    dates, _, _ = _parsed()
    if value is None:
        return dates[-1]
    try:
        d = datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(422, "as_of must be YYYY-MM-DD")
    if d < dates[0] or d > dates[-1]:
        raise HTTPException(422, "as_of outside the observed season %s..%s"
                            % (dates[0], dates[-1]))
    return d


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/meta")
def meta() -> dict:
    d = load()
    m = dict(d["meta"])
    m["method"] = (
        "Sentinel-2 L2A, cloud < 20%, mosaicked by solar day, SCL classes "
        "0/1/3/8/9/10/11 dropped. Pivots detected at 20 m on the greenest fully "
        "covered day by NDVI > 0.30 plus a shape filter (eccentricity <= 0.75, "
        "solidity >= 0.85, 10-400 ha). Per-field NDVI sampled at 60 m."
    )
    m["licence"] = "Sentinel-2 data: Copernicus, free and open. EMIT: NASA, open."
    return m


@app.get("/fields")
def fields(bbox: str | None = Query(None, description="minlon,minlat,maxlon,maxlat")) -> dict:
    d = load()
    items = d["fields"]
    if bbox:
        try:
            x0, y0, x1, y1 = (float(v) for v in bbox.split(","))
        except ValueError:
            raise HTTPException(422, "bbox must be four comma-separated numbers")
        items = [f for f in items if x0 <= f["c"][0] <= x1 and y0 <= f["c"][1] <= y1]
    return {"type": "FeatureCollection",
            "features": [{"type": "Feature",
                          "id": f["id"],
                          "properties": {"field_id": f["id"], "area_ha": f["ha"]},
                          "geometry": {"type": "Polygon", "coordinates": [f["p"]]}}
                         for f in items]}


@app.get("/fields/{field_id}")
def field(field_id: int) -> dict:
    d = load()
    dates, series, fmap = _parsed()
    if field_id not in fmap:
        raise HTTPException(404, "no such field")
    f = fmap[field_id]
    obs = [{"date": ds.isoformat(), "ndvi": v}
           for ds, v in zip(dates, series[field_id]) if v is not None]
    a = assess_field(field_id, f["ha"], dates, series[field_id])
    return {"field_id": field_id, "area_ha": f["ha"], "centroid": f["c"],
            "geometry": {"type": "Polygon", "coordinates": [f["p"]]},
            "assessment": a.to_dict(), "observations": obs}


@app.get("/priority")
def priority(as_of: str | None = None,
             status: str | None = Query(None, description="filter: overdue, dormant, off_cycle, recently_cut, healthy"),
             limit: int = Query(50, ge=1, le=1000)) -> dict:
    dates, series, fmap = _parsed()
    day = _as_of(as_of)
    items = rank(assess_field(fid, f["ha"], dates, series[fid], as_of=day)
                 for fid, f in fmap.items())
    if status:
        items = [a for a in items if a.status == status]
    counts: dict[str, int] = {}
    for a in items:
        counts[a.status] = counts.get(a.status, 0) + 1
    queue = [a for a in items if a.priority > 0][:limit]
    return {"as_of": day.isoformat(), "counts": counts,
            "queue_length": sum(1 for a in items if a.priority > 0),
            "hectares_flagged": round(sum(a.area_ha for a in items if a.priority > 0), 1),
            "queue": [a.to_dict() for a in queue]}


@app.get("/comparison")
def comparison(as_of: str | None = None, top: int = Query(20, ge=5, le=100)) -> dict:
    """How many fields a plain decline ranking would send water to that were only mown."""
    dates, series, fmap = _parsed()
    day = _as_of(as_of)

    assessed = {a.field_id: a for a in
                (assess_field(fid, f["ha"], dates, series[fid], as_of=day)
                 for fid, f in fmap.items())}

    naive = naive_decline_rank(list(fmap), dates, series, day)[:top]
    ours = [a.field_id for a in rank(assessed.values()) if a.priority > 0][:top]

    mown = [fid for fid in naive if assessed[fid].status == "recently_cut"]
    return {
        "as_of": day.isoformat(),
        "top": top,
        "naive_decline_top": [assessed[f].to_dict() for f in naive],
        "cycle_aware_top": [assessed[f].to_dict() for f in ours],
        "naive_that_were_only_mown": len(mown),
        "overlap": len(set(naive) & set(ours)),
        "headline": ("%d of the top %d fields by NDVI decline were simply harvested "
                     "on schedule." % (len(mown), top)),
    }


@app.get("/hyperspectral/{field_id}")
def hyperspectral(field_id: int) -> dict:
    d = load()
    rows = [r for r in d["emit"] if r["id"] == field_id]
    if not rows:
        raise HTTPException(404, "no EMIT coverage for this field")
    return {
        "field_id": field_id,
        "scenes": rows,
        "bands": {"PRI": "531 / 570 nm", "NDVI": "800 / 670 nm",
                  "NDWI": "860 / 1240 nm", "REP": "red-edge position, 670-780 nm",
                  "D970": "continuum-removed 970 nm water absorption depth"},
        "caveat": (
            "Reported as measurement, not as a predictor. On this dataset the "
            "narrow bands did not add transferable predictive signal over NDVI: "
            "they improved a random-fold comparison by +0.12 AUC but made "
            "prediction worse on a held-out scene. Two EMIT scenes is too few to "
            "separate physiology from acquisition conditions."
        ),
    }
