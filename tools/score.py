#!/usr/bin/env python3
"""Score a set of fields from their NDVI history and write the inspection queue.

This is the whole model with nothing around it: no network, no imagery, no
credentials. It reads two CSVs, runs api/priority.py over them and writes the
ranked queue. It is the shortest path from an input you can read to an output
you can check.

    python3 tools/score.py \
        --fields data/sample_input/fields_sample.csv \
        --series data/sample_input/ndvi_series_sample.csv \
        --out    results/sample_output_queue.csv

Both input CSVs are plain text:

    fields_sample.csv        field_id,area_ha
    ndvi_series_sample.csv   field_id,date,ndvi        (date as YYYY-MM-DD)

--as-of defaults to the last date present in the series, which is how the
dashboard and the API behave when no date is given.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.priority import assess_field, rank  # noqa: E402

COLUMNS = ["rank", "field_id", "area_ha", "status", "ndvi", "expected_ndvi", "deficit",
           "cycle_days", "days_since_peak", "cycles_observed", "priority", "reason"]


def _date(s: str):
    return datetime.strptime(s.strip(), "%Y-%m-%d").date()


def read_inputs(fields_csv: str, series_csv: str):
    areas: dict[int, float] = {}
    with open(fields_csv, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            areas[int(row["field_id"])] = float(row["area_ha"])

    dates: list = []
    seen: set = set()
    raw: dict[int, dict] = {}
    with open(series_csv, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            fid = int(row["field_id"])
            d = _date(row["date"])
            if d not in seen:
                seen.add(d)
                dates.append(d)
            v = (row["ndvi"] or "").strip()
            raw.setdefault(fid, {})[d] = None if v == "" else float(v)

    dates.sort()
    missing = sorted(set(raw) - set(areas))
    if missing:
        raise SystemExit("series has field ids absent from the fields file: %s" % missing[:10])

    series = {fid: [raw[fid].get(d) for d in dates] for fid in sorted(raw)}
    return dates, series, areas


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fields", required=True, help="CSV: field_id,area_ha")
    ap.add_argument("--series", required=True, help="CSV: field_id,date,ndvi")
    ap.add_argument("--out", required=True, help="where to write the ranked queue CSV")
    ap.add_argument("--as-of", default=None, help="YYYY-MM-DD; defaults to the last date in the series")
    a = ap.parse_args(argv)

    dates, series, areas = read_inputs(a.fields, a.series)
    as_of = _date(a.as_of) if a.as_of else dates[-1]
    if as_of < dates[0] or as_of > dates[-1]:
        raise SystemExit("--as-of %s is outside the observed season %s..%s"
                         % (as_of, dates[0], dates[-1]))

    queued = rank(assess_field(fid, areas[fid], dates, series[fid], as_of)
                  for fid in sorted(series))

    os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
    with open(a.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(COLUMNS)
        for x in queued:
            d = x.to_dict()
            w.writerow(["" if d["rank"] is None else d["rank"]] +
                       ["" if d[c] is None else d[c] for c in COLUMNS[1:]])

    in_queue = [x for x in queued if x.priority > 0]
    print("%d fields assessed as of %s" % (len(queued), as_of))
    print("%d in the inspection queue, %.1f ha" % (len(in_queue), sum(x.area_ha for x in in_queue)))
    for x in queued:
        print("  %-4s field %-5d %-13s %7.1f ha  priority %8.2f"
              % (x.rank or "-", x.field_id, x.status, x.area_ha, x.priority))
    print("\nwrote %s" % a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
