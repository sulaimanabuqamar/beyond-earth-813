"""Parity across the whole date scrubber, not just the final day."""
import json, sys, os
from datetime import date
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
HERE = os.path.dirname(os.path.abspath(__file__))
from api.priority import assess_field

D=json.load(open(os.path.join(HERE, "synthetic.json")))
dates=[date.fromisoformat(s) for s in D["dates"]]
checks=list(range(12, len(dates), 7)) + [len(dates)-1]

py={}
for ui in checks:
    row={}
    for f in D["fields"]:
        ser=[None if v is None else v/1000.0 for v in D["ndvi"][str(f["id"])]]
        a=assess_field(f["id"], f["ha"], dates, ser, as_of=dates[ui])
        row[str(f["id"])]={"status":a.status,"priority":a.priority,"ndvi":a.ndvi,
                           "since":a.days_since_peak,"cycle":a.cycle_days,
                           "expected":a.expected_ndvi,"deficit":a.deficit}
    py[str(ui)]=row
json.dump({"checks":checks,"py":py}, open(os.path.join(HERE, "sweep_py.json"), "w"))
print("python sweep over %d dates" % len(checks))
